"""Offline host-adapter failures, exclusion, deployment permissions and live gate.

Real systemd dispatch evidence is collected separately by check_m09_host.py.
"""

from contextlib import contextmanager
import grp
import io
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from deploy import install as installer
from nnfx_practice.config import ConfigurationError
from nnfx_practice.control import MaintenanceDeferred, controller_exclusion, maintenance
from nnfx_practice.host import SystemdService, main
from nnfx_practice.notebook import open_notebook, open_readonly, transaction
from .support import NotebookCase


class InstallerPreflightChecks(unittest.TestCase):
    def test_missing_ensurepip_rejects_before_registry_reads_or_deployment_changes(self):
        with patch('sys.argv', ['install', '--registry', '/unused/config.toml']), \
                patch.object(installer.os, 'geteuid', return_value=0), \
                patch.object(installer.importlib.util, 'find_spec', return_value=None), \
                patch.object(installer, 'run') as mutation, \
                patch.object(installer.subprocess, 'run') as process, \
                patch.object(installer.shutil, 'copytree') as copy, \
                patch('nnfx_practice.config.read_registry') as registry, \
                patch('sys.stderr', new_callable=io.StringIO) as stderr, \
                self.assertRaises(SystemExit) as error:
            installer.main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn(f'python{sys.version_info.major}.{sys.version_info.minor}-venv', stderr.getvalue())
        self.assertIn('No deployment changes', stderr.getvalue())
        registry.assert_not_called()
        process.assert_not_called()
        mutation.assert_not_called()
        copy.assert_not_called()


class Manager:
    def __init__(self):
        self.timer = 'active'
        self.active, self.masked = False, False
        self.pending = ''
        self.missing = False
        self.calls = []
        self.fail = None

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        operation = next(a for a in args if a in ('show', 'stop', 'start', 'mask', 'unmask'))
        result = subprocess.CompletedProcess(args, 0, '', '')
        if operation == self.fail:
            result.returncode = 1
            result.stderr = 'private subprocess detail must never be logged'
            return result
        if operation == 'show':
            timer = args[args.index(operation) + 1].endswith('.timer')
            load = 'not-found' if self.missing else 'masked' if self.masked and not timer else 'loaded'
            active = self.timer if timer else 'active' if self.active else 'inactive'
            result.stdout = f'LoadState={load}\nActiveState={active}\nJob={self.pending}\n'
        elif operation == 'stop':
            self.timer = 'inactive'
        elif operation == 'start':
            self.timer = 'active'
        elif operation == 'mask':
            self.masked = True
        elif operation == 'unmask':
            self.masked = False
        return result


class AdapterChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.manager = Manager()
        self.service = SystemdService('controller-a', runner=self.manager)

    def test_reads_and_writes_are_excluded_then_notebook_released_before_restore(self):
        original = self.service.restore_timer
        notebook_closed = False

        def restore(prior):
            self.assertTrue(notebook_closed)
            self.assertEqual(self.manager.timer, 'inactive')
            self.assertTrue(self.manager.masked)
            original(prior)

        self.service.restore_timer = restore
        with maintenance(self.root, self.bound, self.service):
            self.assertTrue(self.manager.masked)
            # Model both broker read and notebook-write phases under one lock.
            for phase in ('read', 'write'):
                with self.subTest(phase=phase), self.assertRaises(MaintenanceDeferred):
                    with controller_exclusion(self.root, self.bound):
                        self.fail('Launch overlapped maintenance')
            with open_notebook(self.root, self.bound, create=True) as db:
                db.execute('SELECT * FROM notebook').fetchone()
            notebook_closed = True
        self.assertFalse(self.manager.masked)
        self.assertEqual(self.manager.timer, 'active')

    def test_body_failure_restores_after_notebook_closes(self):
        with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
            with maintenance(self.root, self.bound, self.service):
                with open_notebook(self.root, self.bound, create=True):
                    raise RuntimeError('fixture failure')
        self.assertEqual(self.manager.timer, 'active')
        self.assertFalse(self.manager.masked)

    def test_base_exception_restores(self):
        with self.assertRaises(KeyboardInterrupt):
            with maintenance(self.root, self.bound, self.service):
                raise KeyboardInterrupt()
        self.assertEqual(self.manager.timer, 'active')
        self.assertFalse(self.manager.masked)

    def test_initially_paused_timer_stays_paused_on_success_and_failure(self):
        self.manager.timer = 'inactive'
        for fail in (False, True):
            try:
                with maintenance(self.root, self.bound, self.service):
                    if fail:
                        raise RuntimeError('fixture')
            except RuntimeError:
                pass
            self.assertEqual(self.manager.timer, 'inactive')
            self.assertFalse(self.manager.masked)
        self.assertFalse(any('start' in call for call in self.manager.calls))

    def test_active_service_defers_without_stopping_service(self):
        self.manager.active = True
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Active service admitted maintenance')
        self.assertTrue(self.manager.active)
        stops = [call for call in self.manager.calls if 'stop' in call]
        self.assertTrue(all(self.service.timer in call for call in stops))
        self.assertEqual(self.manager.timer, 'active')

    def test_job_queued_during_pause_defers_before_reads(self):
        original = self.manager.__call__

        def pending(args, **kw):
            result = original(args, **kw)
            if 'mask' in args:
                self.manager.pending = '123'
            return result

        self.service.runner = pending
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Pending launch admitted maintenance')
        self.assertEqual(self.manager.timer, 'active')

    def test_existing_mask_is_preserved(self):
        self.manager.masked = True
        self.manager.timer = 'inactive'
        with maintenance(self.root, self.bound, self.service):
            pass
        self.assertTrue(self.manager.masked)
        self.assertFalse(any('unmask' in call for call in self.manager.calls))

    def test_external_timer_change_cannot_override_initially_paused_state(self):
        self.manager.timer = 'inactive'
        with maintenance(self.root, self.bound, self.service):
            self.manager.timer = 'active'
        self.assertEqual(self.manager.timer, 'inactive')

    def test_stop_failure_defers_and_restores(self):
        self.manager.fail = 'stop'
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Stop failure admitted maintenance')
        self.assertEqual(self.manager.timer, 'active')

    def test_mask_failure_defers_and_restores(self):
        self.manager.fail = 'mask'
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Mask failure admitted maintenance')
        self.assertFalse(self.manager.masked)
        self.assertEqual(self.manager.timer, 'active')

    def test_unmask_failure_keeps_timer_stopped(self):
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.manager.fail = 'unmask'
        self.assertEqual(self.manager.timer, 'inactive')
        self.assertTrue(self.manager.masked)

    def test_start_failure_is_visible(self):
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.manager.fail = 'start'
        self.assertEqual(self.manager.timer, 'inactive')

    def test_missing_unit_fails_closed(self):
        self.manager.missing = True
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Missing unit admitted maintenance')
        self.assertFalse(any('stop' in call for call in self.manager.calls))

    def test_unstable_timer_fails_closed(self):
        self.manager.timer = 'activating'
        with self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Unstable timer admitted maintenance')

    def test_busy_local_lock_does_not_touch_systemd(self):
        with controller_exclusion(self.root, self.bound), self.assertRaises(MaintenanceDeferred):
            with maintenance(self.root, self.bound, self.service):
                self.fail('Busy lock admitted maintenance')
        self.assertEqual(self.manager.calls, [])

    def test_two_controllers_have_independent_locks_and_exact_units(self):
        other = self.binding('controller-b')
        with maintenance(self.root, self.bound, self.service):
            with controller_exclusion(self.root, other):
                pass
        for args in self.manager.calls:
            units = [arg for arg in args if arg.endswith(('.timer', '.service'))]
            self.assertTrue(all('@controller-a.' in unit for unit in units))

    def test_untrusted_unit_names_rejected(self):
        for name in ('a/b', 'a.service', '../x', 'a;true', ''):
            with self.subTest(name=name), self.assertRaises(ConfigurationError):
                SystemdService(name)

    def test_subprocess_output_is_not_exposed(self):
        self.manager.fail = 'show'
        with self.assertRaises(MaintenanceDeferred) as raised:
            self.service.timer_active()
        self.assertNotIn('private', str(raised.exception))

    def test_timeout_fails_closed(self):
        self.service.runner = lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired('systemctl', 30))
        with self.assertRaises(MaintenanceDeferred):
            self.service.timer_active()


class PermissionChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.directory = self.root / 'var/notebooks'
        self.directory.mkdir(parents=True, mode=0o2750)
        self.directory.chmod(0o2750)
        self.group = grp.getgrgid(os.getgid()).gr_name

    def test_shared_database_and_wal_are_group_read_only_and_private_env_stays_private(self):
        with patch.dict(os.environ, NNFX_NOTEBOOK_READ_GROUP=self.group):
            with open_notebook(self.root, self.bound, create=True) as db:
                db.execute('PRAGMA wal_autocheckpoint=0')
                with transaction(db):
                    db.execute("INSERT INTO issues(issue_id, code, first_observed_at, last_observed_at, status) "
                               "VALUES('fixture', 'committed', '2026-11-19T00:00:00Z', '2026-11-19T00:00:00Z', 'open')")
                for suffix in ('', '-wal', '-shm'):
                    path = Path(str(self.bound.experiment.notebook_path(self.root)) + suffix)
                    self.assertEqual(path.stat().st_mode & 0o777, 0o640)
                with open_readonly(self.root, self.bound.experiment) as reader:
                    self.assertEqual(reader.execute('SELECT code FROM issues').fetchone()[0], 'committed')
                    with self.assertRaises(sqlite3.OperationalError):
                        reader.execute('DELETE FROM issues')
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)

    def test_default_private_notebook_stays_private(self):
        with open_notebook(self.root, self.bound, create=True):
            self.assertEqual(self.bound.experiment.notebook_path(self.root).stat().st_mode & 0o777, 0o600)

    def test_readonly_dashboard_reads_retained_wal_between_writer_runs(self):
        from nnfx_practice.dashboard import create_app
        with patch.dict(os.environ, NNFX_NOTEBOOK_READ_GROUP=self.group):
            with open_notebook(self.root, self.bound, create=True) as db:
                with transaction(db):
                    db.execute("INSERT INTO issues(issue_id, code, first_observed_at, last_observed_at, status) "
                               "VALUES('fixture', 'between-runs', '2026-11-19T00:00:00Z', '2026-11-19T00:00:00Z', 'open')")
        path = self.bound.experiment.notebook_path(self.root)
        files = [Path(str(path) + suffix) for suffix in ('', '-wal', '-shm')]
        self.assertGreater(files[1].stat().st_size, 0)
        for item in files:
            item.chmod(0o400)
        self.directory.chmod(0o500)
        try:
            for _ in range(2):
                page = create_app(self.root).test_client().get('/notebooks/notebook-a')
                self.assertEqual(page.status_code, 200)
                self.assertIn('between-runs', page.get_data(as_text=True))
        finally:
            self.directory.chmod(0o2750)

    def test_unsafe_reader_directory_is_rejected(self):
        self.directory.chmod(0o2770)
        with patch.dict(os.environ, NNFX_NOTEBOOK_READ_GROUP=self.group), self.assertRaises(ConfigurationError):
            with open_notebook(self.root, self.bound, create=True):
                self.fail('Group-writable directory was shared')

    def test_unknown_reader_group_is_rejected(self):
        with patch.dict(os.environ, NNFX_NOTEBOOK_READ_GROUP='nnfx-missing-fixture-group'), self.assertRaises(ConfigurationError):
            with open_notebook(self.root, self.bound, create=True):
                self.fail('Missing group was shared')

    def test_ordinary_command_rejects_before_private_load_or_notebook_creation(self):
        with patch('sys.argv', ['host', '--root', str(self.root), 'ordinary', 'controller-a']), \
                patch('nnfx_practice.config.load_binding', side_effect=AssertionError('Private access')), \
                patch('sys.stderr', new_callable=io.StringIO) as stderr, self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        self.assertIn('disabled', stderr.getvalue())
        self.assertFalse(self.bound.experiment.notebook_path(self.root).exists())
