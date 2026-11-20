"""Offline checks of the unqualified live boundary and broker-free survey.

These tests never contact a broker or systemd and never qualify host/execution.
"""

import json
import subprocess
from unittest.mock import Mock, patch

from nnfx_practice.broker import PracticeBroker
from nnfx_practice.lifecycle import activate_ordinary, initialize_qualification
from .check_m10_prerequisites import collect, observe_command, observe_path, save_report
from .m07_support import EVIDENCE, M07Case
from .support import NotebookCase, TOKEN


class LiveBoundaryChecks(M07Case):
    def live(self):
        connection = self.enterContext(patch('nnfx_practice.broker.HTTPSConnection'))
        broker = self.enterContext(PracticeBroker(self.bound))
        return broker, connection.return_value

    def test_initialization_rejects_before_configuration_service_or_q0_creation(self):
        broker, connection = self.live()
        with patch('nnfx_practice.lifecycle.bound_broker', side_effect=AssertionError('private configuration')):
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                initialize_qualification(self.root, 'controller-a', broker, service=self.service, evidence=EVIDENCE)
        self.assertEqual(self.service.events, [])
        self.assertFalse((self.root / 'var').exists())
        connection.connect.assert_not_called()
        connection.request.assert_not_called()

    def test_live_reopen_and_activation_cannot_change_q0_cursor_or_history(self):
        self.initialize()
        before = '\n'.join(self.db.iterdump())
        broker, connection = self.live()
        for action in (initialize_qualification, activate_ordinary):
            with self.subTest(action=action.__name__), self.assertRaisesRegex(ValueError, 'not enabled'):
                action(self.root, 'controller-a', broker, service=self.service, evidence=EVIDENCE)
            self.assertEqual('\n'.join(self.db.iterdump()), before)
        self.assertEqual(self.service.events, ['pause', 'restore:True'])
        connection.connect.assert_not_called()
        connection.request.assert_not_called()

    def test_all_candidate_live_mutations_reject_before_network(self):
        broker, connection = self.live()
        for action in (
            lambda: broker.enter_trade('EUR-USD', units='10', distance='0.00150', client_id='fixture'),
            lambda: broker.set_target('42', '1.10100'),
            lambda: broker.change_trade('42', stop_price='1.10000'),
            lambda: broker.change_trade('42'),
        ):
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                action()
        connection.connect.assert_not_called()
        connection.request.assert_not_called()

    def test_get_transport_rejects_mutations_payloads_and_other_accounts(self):
        broker, connection = self.live()
        base = '/v3/accounts/' + self.bound.connection.account_id
        for method, path, body in (
            ('POST', base + '/orders', {}), ('PUT', base + '/trades/42/close', {}),
            ('GET', base, {}), ('GET', '/v3/accounts/other-account', None),
            ('GET', base + '-other/summary', None),
        ):
            with self.subTest(method=method, path=path), self.assertRaisesRegex(ValueError, 'read-only'):
                broker._transport.request(method, path, body)
        connection.connect.assert_not_called()
        connection.request.assert_not_called()


class SurveyChecks(NotebookCase):
    def test_missing_host_tools_are_unavailable_without_private_or_notebook_access(self):
        with patch('nnfx_practice.config.read_private_settings', side_effect=AssertionError('private access')):
            report = collect(self.root, runner=Mock(side_effect=FileNotFoundError))
        self.assertTrue(all(not row['available'] for row in report['commands']))
        self.assertFalse((self.root / 'var').exists())
        self.assertNotIn(TOKEN, json.dumps(report))
        self.assertFalse(report['qualification_established'])

    def test_inspection_success_never_becomes_qualification_or_dispatch(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, 'LoadState=loaded\n', ''))
        report = collect(self.root, runner=runner)
        self.assertFalse(report['qualification_established'])
        self.assertTrue(report['source_hashes'])
        for row in report['commands']:
            self.assertFalse(set(row['command']) & {'start', 'stop', 'enable', 'restart', 'mask', 'unmask'})
            self.assertNotIn('--user', row['command'])
        self.assertFalse((self.root / 'var').exists())

    def test_timeout_does_not_serialize_arbitrary_private_exception_output(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(TOKEN, 15, output=TOKEN)
        row = observe_command(['sudo', '-n', 'true'], timeout)
        self.assertFalse(row['available'])
        self.assertNotIn(TOKEN, json.dumps(row))

    def test_report_creation_preserves_existing_evidence_and_rejects_symlinks(self):
        path = self.root / 'report.json'
        original = dict(classification='offline', value='first')
        save_report(path, original)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            save_report(path, dict(value='replacement'))
        self.assertEqual(json.loads(path.read_text()), original)
        alias = self.root / 'alias.json'
        alias.symlink_to(path)
        with self.assertRaises(FileExistsError):
            save_report(alias, {})
        self.assertTrue(observe_path(alias)['symlink'])
        self.assertEqual(json.loads(path.read_text()), original)
