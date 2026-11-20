"""Offline checks of disabled-plan preparation; no real account access."""

from argparse import Namespace
import io
import os
from pathlib import Path
from unittest.mock import Mock, patch

from nnfx_practice.broker import BrokerError
from nnfx_practice.control import MaintenanceDeferred
from nnfx_practice.qualification import account_identity
from . import check_m10_preparation as prep
from .m07_support import M07Case
from .support import ACCOUNT, TOKEN
from .test_m02 import open_trade


class PreparationChecks(M07Case):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(prep, 'DATA', self.root))
        self.enterContext(patch.object(prep.pwd, 'getpwnam', return_value=Mock(pw_uid=os.getuid(), pw_gid=os.getgid())))
        self.enterContext(patch('nnfx_practice.config.load_binding', return_value=self.bound))
        self.enterContext(patch('nnfx_practice.host.SystemdService', return_value=self.service))
        self.enterContext(patch('nnfx_practice.broker.PracticeBroker', return_value=self.broker))
        self.service.timer = False
        self.settings = dict(account_binding_sha256=account_identity(self.bound), manifest_sha256=self.bound.manifest.hash,
                             transaction_boundary=str(self.world.cursor), balance=self.world.balance)

    def test_fresh_unchanged_clear_account_uses_one_get_and_does_not_initialize_notebook(self):
        result = prep.read_clearance(self.settings)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['source'], 'fixture')
        self.assertEqual([call.method for call in self.world.calls], ['GET'])
        self.assertEqual(self.service.events, ['pause', 'restore:False'])
        self.assertFalse(self.service.timer)
        self.assertFalse(list(self.root.rglob('*.sqlite3')))
        self.assertNotIn(TOKEN, str(result))
        self.assertNotIn(ACCOUNT, str(result))

    def test_changed_transaction_boundary_or_balance_remains_pending(self):
        for settings in (dict(self.settings, transaction_boundary='99'), dict(self.settings, balance='900')):
            with self.subTest(settings=settings):
                result = prep.read_clearance(settings)
                self.assertEqual(result['status'], 'pending')
                self.assertFalse(result['unchanged_since_preflight'])
        self.assertTrue(all(call.method == 'GET' for call in self.world.calls))
        self.assertFalse(self.service.timer)

    def test_existing_trade_requires_review_without_closing_or_adopting_it(self):
        self.world.trades['41'] = open_trade(41)
        result = prep.read_clearance(self.settings)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['open_trade_count'], 1)
        self.assertIn('41', self.world.trades)
        self.assertEqual(len(self.world.calls), 1)
        self.assertEqual(self.world.calls[0].method, 'GET')
        self.assertFalse(list(self.root.rglob('*.sqlite3')))

    def test_wrong_binding_stops_before_broker_or_maintenance(self):
        with self.assertRaisesRegex(ValueError, 'no broker request'):
            prep.read_clearance(dict(self.settings, account_binding_sha256='a' * 64))
        self.assertEqual(self.world.calls, [])
        self.assertEqual(self.service.events, [])
        self.assertFalse((self.root / 'var').exists())

    def test_failed_read_restores_the_initially_paused_timer(self):
        def unavailable(call):
            raise BrokerError('Offline unavailable account')
        self.world.on_call = unavailable
        result = prep.read_clearance(self.settings)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['evidence']['http_status'], None)
        self.assertEqual(self.service.events, ['pause', 'restore:False'])
        self.assertFalse(self.service.timer)
        self.assertFalse(list(self.root.rglob('*.sqlite3')))

    def test_nonadministrator_cannot_prepare_or_contact_an_account(self):
        with patch('sys.argv', ['prep']), patch.object(prep.os, 'geteuid', return_value=1001), \
                patch.object(prep, 'prepare') as prepare, patch('sys.stderr', new_callable=io.StringIO), \
                self.assertRaises(SystemExit) as error:
            prep.main()
        self.assertEqual(error.exception.code, 2)
        prepare.assert_not_called()
        self.assertEqual(self.world.calls, [])

    def test_maintenance_restoration_failure_keeps_the_fresh_read_pending(self):
        with patch.object(self.service, 'restore_timer', side_effect=MaintenanceDeferred('Offline restore failure')):
            result = prep.read_clearance(self.settings)
        self.assertEqual(result['status'], 'pending')
        self.assertIn('restore failure', result['maintenance_error'])
        self.assertEqual(len(self.world.calls), 1)
        self.assertEqual(self.world.calls[0].method, 'GET')

    def test_exclusive_report_creation_preserves_prior_evidence_and_explicit_permissions(self):
        path = self.root / 'report.json'
        prior_umask = os.umask(0o077)
        try:
            prep.write_new(path, dict(status='pending'), mode=0o640)
        finally:
            os.umask(prior_umask)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            prep.write_new(path, dict(status='passed'))
        self.assertEqual(path.read_bytes(), original)
        link = self.root / 'link.json'
        link.symlink_to(path)
        with self.assertRaises(FileExistsError):
            prep.write_new(link, {})
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_or_past_schedule_stops_before_plan_or_broker_operations(self):
        for instant in ('2026-11-16T21:50:00+00:00', '2030-01-05T21:50:00+00:00',
                        '2030-01-07T21:49:00+00:00', '2030-01-07T21:50:00'):
            with self.subTest(instant=instant), self.assertRaises(ValueError):
                prep.prepare(Namespace(dispatch_at=instant))
        self.assertEqual(self.world.calls, [])
        self.assertFalse((self.root / 'var').exists())

    def test_changed_boot_kernel_reports_or_application_do_not_inherit_host_qualification(self):
        hashes = {'fixture.py': 'a' * 64}
        receipt = dict(system_report={'sha256': 'system'}, deployment_report={'sha256': 'deployment'},
                       application_hashes=hashes, host_context={'boot_id': 'boot', 'kernel': 'kernel'})
        with patch('nnfx_practice.qualification.host_identity', return_value=('boot', 'kernel')):
            prep.verify_host_receipt(receipt, 'system', 'deployment', hashes)
            for key in ('boot_id', 'kernel'):
                changed = dict(receipt, host_context={**receipt['host_context'], key: 'changed'})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    prep.verify_host_receipt(changed, 'system', 'deployment', hashes)
            with self.assertRaises(ValueError):
                prep.verify_host_receipt(receipt, 'other report', 'deployment', hashes)
            with self.assertRaises(ValueError):
                prep.verify_host_receipt(receipt, 'system', 'deployment', {})
        self.assertEqual(self.world.calls, [])
