"""Offline isolation checks for the opt-in administrator fixture harness."""

import io
import configparser
import os
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from . import check_m09_system as harness
from . import m09_system_worker as worker
from . import m09_dashboard_worker as dashboard_worker
from .support import NotebookCase
from .m07_support import Service
from nnfx_practice.notebook import open_notebook


class SystemHarnessChecks(unittest.TestCase):
    def test_staged_workers_are_readable_with_private_administrator_umask(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'source'
            source.mkdir()
            for name in ('m09_system_worker.py','m09_dashboard_worker.py'):
                (source/name).write_text('print("synthetic fixture")\n')
            prior=os.umask(0o077)
            try:
                staged=root/'staged'
                harness.stage_workers(source,staged)
            finally:
                os.umask(prior)
            self.assertEqual(staged.stat().st_mode & 0o777,0o755)
            for path in staged.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777,0o644)

    def templates(self):
        return [(harness.ROOT / 'deploy' / name).read_text() for name in harness.UNIT_NAMES]

    def options(self, prefix='nnfx-m09-system-0123456789ab'):
        return dict(prefix=prefix, fixture=Path('/var/lib/nnfx-practice/var/verification') / prefix,
                    worker=Path('/opt/nnfx-practice/verification') / prefix / 'worker.py',
                    dashboard_worker=Path('/opt/nnfx-practice/verification') / prefix / 'dashboard.py', port=18878)

    def test_unprivileged_rejection_precedes_any_host_read_or_mutation(self):
        with patch('sys.argv', ['check']), patch.object(harness.os, 'geteuid', return_value=1001), \
                patch.object(harness, 'read_registry') as registry, \
                patch.object(harness.subprocess, 'run') as command, \
                patch.object(harness.Path, 'mkdir') as mkdir, \
                patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            harness.main()
        self.assertEqual(error.exception.code, 2)
        registry.assert_not_called()
        command.assert_not_called()
        mkdir.assert_not_called()

    def test_fixture_units_retain_service_hardening_and_calendar(self):
        source_service, source_timer, source_dashboard = self.templates()
        service, timer, dashboard = harness.fixture_definition(*self.templates(), **self.options())
        for line in ('User=nnfx-run', 'Group=nnfx-read', 'Type=oneshot', 'Restart=no',
                     'NoNewPrivileges=yes', 'ProtectSystem=strict', 'ProtectHome=yes',
                     'ReadWritePaths=/var/lib/nnfx-practice/var'):
            self.assertIn(line, service.splitlines())
        for line in ('OnCalendar=Mon..Fri *-*-* 16:50:00 America/New_York',
                     'Persistent=false', 'AccuracySec=1s', 'RandomizedDelaySec=0'):
            self.assertIn(line, timer.splitlines())
        self.assertIn('Unit=nnfx-m09-system-0123456789ab@%i.service', timer)
        for line in ('User=nnfx-view', 'ProtectSystem=strict', 'ProtectHome=yes',
                     'SystemCallFilter=~@mount @reboot @swap connect', 'CapabilityBoundingSet='):
            self.assertIn(line, dashboard.splitlines())
        self.assertIn('/run/systemd /run/dbus /usr/bin/systemctl /usr/bin/sudo', dashboard)
        self.assertNotIn('ordinary %i', service)
        self.assertNotIn('--root /var/lib/nnfx-practice --host', dashboard)
        self.assertIn('InaccessiblePaths=-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks', service)
        self.assertIn('IPAddressDeny=any', service)
        self.assertIn('InaccessiblePaths=-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks', dashboard)

    def test_real_unit_names_and_nonfixture_privilege_grants_are_rejected(self):
        for prefix in ('nnfx-practice', 'nnfx-m09-system-../unsafe', 'nnfx-m09-system-not-a-hash'):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                harness.fixture_definition(*self.templates(), **self.options(prefix))
            with self.assertRaises(ValueError):
                harness.fixture_policy(prefix)
        policy = harness.fixture_policy(self.options()['prefix'])
        self.assertNotIn('nnfx-practice@', policy)
        self.assertNotIn('*', policy)
        self.assertNotIn(' enable ', policy)
        self.assertEqual(policy.count('/usr/bin/systemctl'), 6)
        self.assertIn(self.options()['prefix'] + '-qualification@a.timer', policy)

    def test_dashboard_command_and_restrictions_use_one_fixture_root(self):
        options = self.options()
        _, _, dashboard = harness.fixture_definition(*self.templates(), **options)
        lines = dashboard.splitlines()
        fixture = options['fixture']
        self.assertIn(f'ExecStart={harness.PYTHON} {options["dashboard_worker"]} {fixture} {options["port"]}', lines)
        self.assertIn(f'ReadOnlyPaths={fixture}', lines)
        self.assertIn(f'InaccessiblePaths=-{fixture}/.env /run/systemd /run/dbus /usr/bin/systemctl /usr/bin/sudo', lines)
        duplicated = str(fixture) + '/var/verification/' + options['prefix']
        self.assertNotIn(duplicated, dashboard)

    def test_unreviewed_deployed_commands_are_rejected(self):
        service, timer, dashboard = self.templates()
        with self.assertRaises(ValueError):
            harness.fixture_definition(service.replace('dispatch %i', 'something-else %i'), timer,
                                       dashboard, **self.options())
        with self.assertRaises(ValueError):
            harness.fixture_definition(service, timer, dashboard.replace(f'--port {harness.DASHBOARD_PORT}', '--port 9000'),
                                       **self.options())

    def test_production_binding_and_fixture_bind_restriction_use_the_same_available_port(self):
        dashboard = self.templates()[2]
        self.assertIn('--port 8879', dashboard)
        self.assertIn('SocketBindAllow=tcp:8879', dashboard)
        self.assertNotIn('tcp:8878', dashboard)
        _, _, isolated = harness.fixture_definition(*self.templates(), **self.options())
        self.assertIn('SocketBindAllow=tcp:18878', isolated)

    def test_actual_path_denials_are_in_service_sections_and_not_install_metadata(self):
        service, _, dashboard = harness.fixture_definition(*self.templates(), **self.options())
        for text in (service, dashboard):
            profile = configparser.ConfigParser(strict=False, interpolation=None)
            profile.read_string(text)
            self.assertEqual(profile['Service']['InaccessiblePaths'],
                             '-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks')
            self.assertNotIn('InaccessiblePaths', profile['Install'] if 'Install' in profile else {})


class ExistingNotebookPreservationChecks(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'actual.sqlite3'

    def fingerprint(self, allow=True):
        return harness.notebook_fingerprints([self.path], allow_existing=allow, uid=os.getuid(), gid=os.getgid())

    def create(self, suffix='', body=b'existing Q0 and history'):
        path = Path(str(self.path) + suffix)
        path.write_bytes(body)
        path.chmod(0o640)
        return path

    def test_absent_notebook_and_sidecars_are_not_created(self):
        records = self.fingerprint(False)
        self.assertTrue(all(value is None for value in records[str(self.path)].values()))
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_explicit_preserve_mode_hashes_existing_history_without_sqlite_or_writes(self):
        self.create()
        self.create('-wal', b'committed existing history')
        self.create('-shm', b'existing index')
        before = {path: path.read_bytes() for path in Path(self.directory.name).iterdir()}
        with patch('sqlite3.connect', side_effect=AssertionError('Actual SQLite opened')):
            first = self.fingerprint()
            self.assertEqual(first, self.fingerprint())
        self.assertEqual(before, {path: path.read_bytes() for path in Path(self.directory.name).iterdir()})

    def test_default_retains_rejection_of_actual_history(self):
        self.create()
        with self.assertRaisesRegex(ValueError, 'preserve-existing-notebooks'):
            self.fingerprint(False)

    def test_changed_history_or_metadata_is_detected_without_repair(self):
        self.create()
        before = self.fingerprint()
        self.create(body=b'changed outside the probe')
        self.assertNotEqual(before, self.fingerprint())
        self.path.chmod(0o600)
        with self.assertRaises(ValueError):
            self.fingerprint()
        self.assertEqual(self.path.read_bytes(), b'changed outside the probe')

    def test_orphan_sidecars_symlinks_and_hardlinks_are_rejected(self):
        orphan = self.create('-wal')
        with self.assertRaisesRegex(ValueError, 'Orphan'):
            self.fingerprint()
        orphan.unlink()
        target = Path(self.directory.name) / 'target'
        target.write_bytes(b'preserve')
        self.path.symlink_to(target)
        with self.assertRaises(OSError):
            self.fingerprint()
        self.path.unlink()
        os.link(target, self.path)
        self.path.chmod(0o640)
        with self.assertRaises(ValueError):
            self.fingerprint()

    def test_worker_rejects_actual_data_root_before_opening_any_notebook(self):
        with patch('sys.argv', ['worker', '/var/lib/nnfx-practice', 'initialize']), \
                patch.object(worker, 'initialize') as initialize, self.assertRaises(ValueError):
            worker.main()
        initialize.assert_not_called()


class SyntheticBindingChecks(NotebookCase):
    def test_worker_binding_ignores_private_connection_and_never_opens_notebook(self):
        with patch('nnfx_practice.config.read_private_settings', side_effect=AssertionError('private read')):
            binding = worker.fixture_binding(self.root, 'controller-a')
        self.assertEqual(binding.connection.account_id, 'synthetic-account-controller-a')
        self.assertEqual(binding.connection.token, 'synthetic-not-a-token')
        self.assertEqual(binding.connection.lookback_candles, 386)
        self.assertFalse((self.root / 'var').exists())


class DashboardCommandChecks(unittest.TestCase):
    def test_present_but_inaccessible_control_binaries_are_accepted(self):
        for error in (PermissionError, FileNotFoundError):
            runner = Mock(side_effect=error)
            with self.subTest(error=error.__name__), patch.object(Path, 'exists', return_value=True):
                checks = dashboard_worker.check_control_commands(runner)
            self.assertEqual(checks, dict(systemctl_inaccessible=True, sudo_inaccessible=True))
            self.assertEqual([call.args[0] for call in runner.call_args_list],
                             [['/usr/bin/systemctl', '--version'], ['/usr/bin/sudo', '--version']])

    def test_executable_control_binary_is_a_failed_isolation_check(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, '', ''))
        with self.assertRaisesRegex(AssertionError, 'could execute systemctl'):
            dashboard_worker.check_control_commands(runner)
        self.assertEqual(runner.call_count, 1)


class SyntheticMaintenanceChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        registry = self.root / 'config.toml'
        registry.write_text(registry.read_text().replace('controller-a', 'a').replace('controller-b', 'b')
                            .replace('fixture-v1', 't3_bandpass_v1'))
        self.enterContext(patch.dict(os.environ, NNFX_NOTEBOOK_READ_GROUP=''))
        worker.initialize(self.root)

    def test_fixture_initialization_does_not_create_q0_a0_or_broker_history(self):
        for identifier in ('a', 'b'):
            with open_notebook(self.root, worker.fixture_binding(self.root, identifier)) as db:
                row = db.execute('SELECT * FROM notebook').fetchone()
                self.assertIsNone(row['qualification_snapshot_id'])
                self.assertIsNone(row['activation_snapshot_id'])
                self.assertIsNone(row['imported_through_transaction_id'])
                self.assertEqual(db.execute('SELECT count(*) FROM broker_transactions').fetchone()[0], 0)
                self.assertTrue(row['account_id'].startswith('synthetic-account-'))

    def test_fixture_maintenance_success_failure_and_paused_restoration(self):
        for active, failed in ((True, False), (True, True), (False, False), (False, True)):
            service = Service()
            service.timer = active
            tag = f'{active}-{failed}'
            with patch.object(worker, 'SystemdService', return_value=service), patch.object(worker, 'release'):
                worker.maintain(self.root, 'unused-fixture-prefix', tag, failed)
            self.assertEqual(service.timer, active)
            self.assertEqual(service.events, ['pause', 'restore:' + str(active)])
            with open_notebook(self.root, worker.fixture_binding(self.root)) as db:
                self.assertEqual(db.execute("SELECT code FROM issues WHERE issue_id='fixture'").fetchone()[0], 'maintenance-' + tag)
                self.assertIsNone(db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0])
