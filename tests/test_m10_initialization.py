"""Offline Q0 helper checks; no real plan, systemd or account access."""

from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nnfx_practice.broker import PracticeBroker
from nnfx_practice.qualification import account_identity
from . import initialize_m10_qualification as tool
from .m07_support import EVIDENCE, M07Case


class InitializationChecks(M07Case):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(tool, 'DATA', self.root))
        self.enterContext(patch.object(tool, 'CONTROLLER', 'controller-a'))
        self.path = self.root / 'plan.json'
        self.original = b'{"enabled": false, "run_id": "offline-original"}\n'
        self.path.write_bytes(self.original)
        self.digest = sha256(self.original).hexdigest()
        self.enterContext(patch('nnfx_practice.qualification.sealed_bytes', side_effect=lambda p: Path(p).read_bytes()))
        self.enterContext(patch.object(tool.os, 'fchown'))

    def test_temporary_initialization_flag_restores_exact_original_bytes(self):
        with tool.initialization_plan(self.path, self.digest) as active:
            self.assertTrue(json.loads(self.path.read_text())['enabled'])
            self.assertEqual(sha256(self.path.read_bytes()).hexdigest(), active)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(list(self.root.glob('.q0-*')), [])

    def test_flag_is_restored_after_worker_failure_without_resetting_history(self):
        evidence = self.root / 'existing-evidence'
        evidence.write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'offline interruption'):
            with tool.initialization_plan(self.path, self.digest):
                raise RuntimeError('offline interruption')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(evidence.read_text(), 'keep')

    def test_changed_or_already_enabled_plan_is_preserved(self):
        for body in (b'{"enabled":true}', b'{"enabled":false,"changed":true}'):
            self.path.write_bytes(body)
            with self.subTest(body=body), self.assertRaises(ValueError):
                with tool.initialization_plan(self.path, self.digest):
                    self.fail('Changed plan accepted')
            self.assertEqual(self.path.read_bytes(), body)

    def test_concurrent_root_plan_change_is_not_overwritten(self):
        other = b'{"enabled":false,"external":"offline-review"}'
        with self.assertRaisesRegex(ValueError, 'Concurrent'):
            with tool.initialization_plan(self.path, self.digest):
                self.path.write_bytes(other)
        self.assertEqual(self.path.read_bytes(), other)

    def test_existing_notebook_sidecars_and_symlinks_block_initial_path(self):
        folder = self.root / 'var/notebooks'
        folder.mkdir(parents=True)
        for suffix in ('', '-wal', '-shm', '-journal'):
            path = folder / ('notebook-a.sqlite3' + suffix)
            path.write_text('preserve')
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'preserved'):
                tool.require_empty_notebook()
            self.assertEqual(path.read_text(), 'preserve')
            path.unlink()
        (folder / 'notebook-a.sqlite3').symlink_to(folder / 'missing')
        with self.assertRaises(ValueError):
            tool.require_empty_notebook()

    def worker(self, *, boundary=None):
        digest = account_identity(self.bound)
        permit = SimpleNamespace(binding=self.bound, digest='a' * 64, plan={'account_binding_sha256':digest},
                                 references=EVIDENCE)
        settings = dict(initialization_plan_sha256=permit.digest, account_binding_sha256=digest,
                        transaction_boundary=boundary or str(self.world.cursor), balance=self.world.balance)
        original_init = PracticeBroker.__init__
        instances = []
        def fixture_broker(instance, binding, **_kwargs):
            original_init(instance, binding, transport=self.world, now=self.clock.now)
            instances.append(instance)
        self.service.timer = False
        with patch('nnfx_practice.qualification.load_permit', return_value=permit), \
                patch('nnfx_practice.host.SystemdService', return_value=self.service), \
                patch.object(PracticeBroker, '__init__', fixture_broker):
            result = tool.initialize_worker(settings)
        return result, instances[0]

    def test_q0_uses_existing_lifecycle_and_keeps_ordinary_activation_unset(self):
        result, broker = self.worker()
        self.assertEqual(result['source'], 'fixture')
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['broker_requests'], 1)
        self.assertEqual(result['transaction_boundary'], result['imported_through_transaction_id'])
        self.assertFalse(result['ordinary_activation_performed'])
        self.assertEqual([call.method for call in self.world.calls], ['GET'])
        self.assertEqual(self.service.events, ['pause', 'restore:False'])
        with self.assertRaisesRegex(ValueError, 'GET-only'):
            broker.change_trade('42')
        self.assertEqual(len(self.world.calls), 1)

    def test_changed_clearance_boundary_leaves_q0_pending_and_preserved(self):
        result, _ = self.worker(boundary='99')
        self.assertEqual(result['status'], 'pending')
        self.assertFalse(result['matches_reviewed_clearance'])
        self.assertTrue(result['actual_notebook_initialized'])
        self.assertTrue((self.root / 'var/notebooks/notebook-a.sqlite3').exists())
        self.assertFalse(self.service.timer)
        self.assertTrue(all(call.method == 'GET' for call in self.world.calls))

    def test_nonadministrator_refuses_before_plan_or_account_access(self):
        with patch('sys.argv', ['initialize']), patch.object(tool.os, 'geteuid', return_value=1001), \
                patch.object(tool, 'initialize') as initialize, patch('sys.stderr', new_callable=io.StringIO), \
                self.assertRaises(SystemExit) as error:
            tool.main()
        self.assertEqual(error.exception.code, 2)
        initialize.assert_not_called()
        self.assertEqual(self.world.calls, [])

    def test_fixture_or_changed_q0_facts_do_not_become_actual_initialization_evidence(self):
        result, _ = self.worker()
        plan = dict(account_binding_sha256=result['account_binding_sha256'], manifest_sha256=result['manifest_sha256'])
        with self.assertRaisesRegex(ValueError, 'actual GET-only'):
            tool.verify_q0_result(result, plan, result['transaction_boundary'])
        candidate = dict(result, source='practice_get')  # Offline validator input, not actual evidence.
        tool.verify_q0_result(candidate, plan, result['transaction_boundary'])
        for key, value in (('ordinary_activation_performed', True), ('matches_reviewed_clearance', False),
                           ('imported_through_transaction_id', '99'), ('q0_snapshot_id', None),
                           ('broker_requests', 0), ('account_binding_sha256', 'wrong')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                tool.verify_q0_result(dict(candidate, **{key:value}), plan, result['transaction_boundary'])
