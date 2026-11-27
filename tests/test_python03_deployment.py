"""Fail-before-mutation checks for the administrator's scoped addition."""

from copy import deepcopy
from datetime import UTC, datetime
import fcntl
import io
import json
from hashlib import sha256
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from deploy import add_python03 as deployment
from deploy.python03_bootstrap import next_slot


class DeploymentChecks(unittest.TestCase):
    def test_bootstrap_uses_next_weekday_without_catching_up_or_trading_in_capture_window(self):
        friday = datetime(2026, 11, 27, 21, 49, tzinfo=UTC)
        capture = next_slot(friday)
        self.assertEqual(capture, datetime(2026, 11, 27, 21, 50, tzinfo=UTC))
        self.assertEqual(next_slot(capture), datetime(2026, 11, 30, 21, 50, tzinfo=UTC))
        self.assertEqual(next_slot(datetime(2026, 7, 1, 12, tzinfo=UTC)), datetime(2026, 7, 1, 20, 50, tzinfo=UTC))

    def test_registry_preserves_existing_experiment_exactly(self):
        old = {'experiments': [dict(controller_id='practice-a', notebook_name='Python 01'), dict(controller_id='practice-b', notebook_name='Python 02')]}
        new = {'experiments': [*old['experiments'], dict(controller_id='practice-c', notebook_id='notebook-c',
            notebook_name='Python 03', strategy_version='eye_age_supertrend_v1', connection_key='PRACTICE_C')]}
        deployment.registry_change(old, new)
        for change in ('existing', 'new', 'extra'):
            changed = deepcopy(new)
            if change == 'existing':
                changed['experiments'][0]['notebook_name'] = 'Changed'
            elif change == 'new':
                changed['experiments'][2]['strategy_version'] = 't3_bandpass_v1'
            else:
                changed['experiments'].append(dict(changed['experiments'][1]))
            with self.assertRaises(ValueError):
                deployment.registry_change(old, changed)

    def test_private_change_preserves_existing_values_and_requires_distinct_account(self):
        old = {'PRACTICE_A_ACCOUNT_ID': 'fixture-a', 'PRACTICE_A_TOKEN': 'fixture-secret', 'PRACTICE_B_ACCOUNT_ID': 'fixture-b'}
        new = {**old, 'PRACTICE_C_ACCOUNT_ID': 'fixture-c', 'PRACTICE_C_TOKEN': 'fixture-secret',
               'PRACTICE_C_HOME_CURRENCY': 'AUD', 'PRACTICE_C_LOOKBACK_CANDLES': '5000'}
        deployment.private_change(old, new)
        for key, value in (('PRACTICE_A_TOKEN', 'changed'), ('PRACTICE_C_ACCOUNT_ID', 'fixture-a'),
                           ('PRACTICE_C_ACCOUNT_ID', 'fixture-b'), ('PRACTICE_C_LOOKBACK_CANDLES', '386'), ('PRACTICE_C_TOKEN', ''), ('EXTRA', 'field')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                deployment.private_change(old, {**new, key: value})

    def test_private_parser_never_evaluates_shell_and_rejects_duplicates(self):
        self.assertEqual(deployment.private_fields(b"KEY='$(echo secret)'\n"), {'KEY': '$(echo secret)'})
        for raw in (b'KEY=x\nKEY=y\n', b'KEY=\"missing\n', b'lowercase=x\n'):
            with self.assertRaises(ValueError):
                deployment.private_fields(raw)

    def test_plan_update_preserves_schedule_authority_and_replay_identity(self):
        old = dict(version=2, enabled=True, controller_id='practice-a', notebook_id='notebook-a',
                   run_id='original-prefix', dispatch_at='original-date', schedule='original-schedule',
                   account_binding_sha256='account', manifest_sha256='manifest',
                   automatic_schedule_authority={'sha256': 'authority'},
                   evidence={'m09_controller_controls': {'sha256': 'old'}, 'account_preflight': {'sha256': 'account'}})
        baseline = deepcopy(old)
        plan = deployment.updated_plan(old, 'new-code', 'new-config', {'sha256': 'new-controls'})
        self.assertEqual(old, baseline)
        for key in ('run_id', 'dispatch_at', 'schedule', 'account_binding_sha256', 'manifest_sha256', 'automatic_schedule_authority'):
            self.assertEqual(plan[key], old[key])
        self.assertEqual(plan['evidence']['account_preflight'], old['evidence']['account_preflight'])
        self.assertTrue(plan['enabled'])
        for changes in ({'version': 1}, {'enabled': False}, {'controller_id': 'practice-c'}):
            with self.assertRaises(ValueError):
                deployment.updated_plan({**old, **changes}, 'code', 'config', {})

    def test_nonadministrator_refused_before_accessing_deployment(self):
        with (patch.object(deployment.os, 'geteuid', return_value=1000),
              patch.object(deployment.sys, 'argv', ['add-python03']),
              patch.object(deployment.sys, 'stderr', io.StringIO()),
              patch.object(deployment.Path, 'resolve', side_effect=AssertionError('Unexpected filesystem access'))):
            with self.assertRaises(SystemExit) as raised:
                deployment.main()
        self.assertEqual(raised.exception.code, 2)


class PendingPython02Checks(unittest.TestCase):
    def test_missing_lock_is_created_for_writer_and_reuses_the_exclusion_inode(self):
        writer = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notebook-b.lock'
            first = deployment.open_pending_notebook_lock(path, writer)
            try:
                info = os.fstat(first)
                self.assertEqual((info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)),
                                 (writer.pw_uid, writer.pw_gid, 0o600))
                os.write(first, b'preserved lock contents')
                fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
                second = deployment.open_pending_notebook_lock(path, writer)
                try:
                    self.assertEqual(os.fstat(second).st_ino, info.st_ino)
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    os.close(first)
                    first = None
                    fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.assertEqual(path.read_bytes(), b'preserved lock contents')
                finally:
                    os.close(second)
            finally:
                if first is not None:
                    os.close(first)

    def test_pending_lock_rejects_symlink_or_wrong_permissions_without_changing_target(self):
        writer = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_bytes(b'untouched')
            target.chmod(0o600)
            link = Path(directory) / 'notebook-b.lock'
            link.symlink_to(target)
            with self.assertRaises(OSError):
                deployment.open_pending_notebook_lock(link, writer)
            target.chmod(0o644)
            with self.assertRaises(ValueError):
                deployment.open_pending_notebook_lock(target, writer)
            self.assertEqual(target.read_bytes(), b'untouched')
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def test_pending_setup_update_changes_only_shared_identities_and_controls(self):
        original = dict(code_sha256='old-code', config_sha256='old-config', kernel='kernel',
            account_binding_sha256='account-b', manifest_sha256='manifest-b', bootstrap_sha256='helper',
            owner_statement='existing authority', evidence={'m09_controller_controls': {'sha256': 'old'},
                                                           'execution_authority': {'sha256': 'authority'}})
        baseline = deepcopy(original)
        updated = deployment.updated_bootstrap(original, 'new-code', 'new-config', {'sha256': 'new-controls'})
        self.assertEqual(original, baseline)
        for name in ('kernel', 'account_binding_sha256', 'manifest_sha256', 'bootstrap_sha256', 'owner_statement'):
            self.assertEqual(updated[name], original[name])
        self.assertEqual(updated['evidence']['execution_authority'], original['evidence']['execution_authority'])
        self.assertEqual(updated['code_sha256'], 'new-code')
        self.assertEqual(updated['evidence']['m09_controller_controls'], {'sha256': 'new-controls'})

    def test_attempted_or_changed_setup_cannot_be_rebound(self):
        context = dict(code_sha256='code', config_sha256='config', kernel='kernel', bootstrap_sha256='helper')
        raw = json.dumps(context).encode()
        inspection = dict(receipt_exists=False, context_sha256=sha256(raw).hexdigest(), helper_sha256='helper')
        deployment.validate_pending_bootstrap(inspection, raw, 'helper', 'code', 'config', 'kernel')
        for patch in ({'receipt_exists': True}, {'context_sha256': 'changed'}, {'helper_sha256': 'changed'}):
            with self.assertRaises(ValueError):
                deployment.validate_pending_bootstrap({**inspection, **patch}, raw, 'helper', 'code', 'config', 'kernel')
        for position in range(4):
            values = ['helper', 'code', 'config', 'kernel']
            values[position] = 'changed'
            with self.assertRaises(ValueError):
                deployment.validate_pending_bootstrap(inspection, raw, *values)
