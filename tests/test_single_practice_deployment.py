"""Broker-free upgrade guards: no actual services, plans or private files accessed."""

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from deploy import single_practice_mode as upgrade


class UpgradeGuards(unittest.TestCase):
    def test_plan_refresh_preserves_authority_identity_schedule_claims_and_unknown_fields(self):
        for controller in upgrade.CONTROLLERS:
            old = dict(controller_id=controller, version=2, enabled=True, mode='qualification',
                       code_sha256='old', config_sha256='same', manifest_sha256='strategy',
                       run_id='existing-prefix', dispatch_at='original-start', schedule='same-calendar',
                       automatic_schedule_authority={'sha256': 'same', 'path': '/protected/authority'},
                       evidence={'m09_controller_controls': {'path': '/old'}, 'execution_authority': {'path': '/unchanged'}},
                       future_metadata={'keep': [1, 2, 3]})
            before = deepcopy(old)
            result = upgrade.updated_plan(old, controller, 'new', {'path': '/new'})
            self.assertEqual(old, before)
            self.assertEqual(result.pop('code_sha256'), 'new')
            self.assertEqual(result['evidence'].pop('m09_controller_controls'), {'path': '/new'})
            before.pop('code_sha256')
            before['evidence'].pop('m09_controller_controls')
            self.assertEqual(result, before)
        for field, value in [('mode', 'ordinary'), ('enabled', False), ('controller_id', 'other'), ('version', 1)]:
            wrong = dict(old, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                upgrade.updated_plan(wrong, controller, 'new', {})

    def test_running_controllers_and_altered_triggers_defer_without_commands(self):
        services = {'a': dict(LoadState='loaded', ActiveState='inactive', MainPID='0', Job='', DropInPaths='')}
        timers = {'a': dict(LoadState='loaded', ActiveState='active', SubState='waiting',
                            UnitFileState='enabled', Job='', DropInPaths='')}
        legacy = {'a': dict(LoadState='loaded', ActiveState='inactive', UnitFileState='disabled', Job='', DropInPaths='')}
        upgrade.require_idle(services, timers, legacy)
        for collection, field, value in [(services, 'MainPID', '10'), (services, 'Job', '12'),
                                         (services, 'ActiveState', 'activating'), (timers, 'UnitFileState', 'disabled'),
                                         (timers, 'DropInPaths', '/changed'), (legacy, 'ActiveState', 'active')]:
            changed = deepcopy(collection)
            changed['a'][field] = value
            args = [changed if value is collection else value for value in (services, timers, legacy)]
            with self.subTest(field=field), patch.object(upgrade, 'command') as command, self.assertRaises(ValueError):
                upgrade.require_idle(*args)
            command.assert_not_called()

    def test_restore_requires_identical_schedule_and_no_new_controller_invocation(self):
        before = {'a': {key: 'original' for key in upgrade.SERVICE_KEYS}}
        after = deepcopy(before)
        for key in ('InvocationID', 'ExecMainStartTimestamp', 'ExecMainExitTimestamp'):
            after['a'][key] = ''
        timers = {'a': {'next': 'original-date', 'enabled': True}}
        upgrade.require_restored(before, after, timers, timers)
        for key in ('InvocationID', 'ExecMainStartTimestamp', 'MainPID', 'Job'):
            wrong = deepcopy(after)
            wrong['a'][key] = 'new'
            with self.subTest(key=key), self.assertRaises(ValueError):
                upgrade.require_restored(before, wrong, timers, timers)
        with self.assertRaises(ValueError):
            upgrade.require_restored(before, after, timers, {'a': {'next': 'changed'}})


class ReleaseGuards(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.root = self.base / 'release'
        self.root.mkdir()
        (self.root / 'nnfx_practice').mkdir()
        self.source = self.root / 'nnfx_practice/host.py'
        self.source.write_text('# offline source\n')
        (self.base / 'suite.log').write_text('test_fixture ... ok\nRan 1 tests in 0.1s\n\nOK\n')
        self.wheel = self.base / 'fixture.whl'
        with zipfile.ZipFile(self.wheel, 'w') as package:
            package.write(self.source, 'nnfx_practice/host.py')
        self.record = dict(release_files={'nnfx_practice/host.py': sha256(self.source.read_bytes()).hexdigest()},
                           code_files={'nnfx_practice/host.py': sha256(self.source.read_bytes()).hexdigest()},
                           offline_suite={'path': 'suite.log', 'sha256': sha256((self.base / 'suite.log').read_bytes()).hexdigest()},
                           wheel={'path': 'fixture.whl', 'sha256': sha256(self.wheel.read_bytes()).hexdigest()})
        self.save()
        self.enterContext(patch.object(upgrade, 'ROOT', self.root))

    def save(self):
        (self.base / 'release.json').write_text(json.dumps(self.record))

    def test_complete_matching_package_and_suite_are_required(self):
        self.assertEqual(upgrade.verify_release(self.base)[1], self.wheel)
        self.source.write_text('# changed source\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            upgrade.verify_release(self.base)

    def test_failed_suite_cannot_be_approved_by_rehashing_it(self):
        log = self.base / 'suite.log'
        log.write_text('Ran 1 tests in 0.1s\nFAILED (failures=1)\n')
        self.record['offline_suite']['sha256'] = sha256(log.read_bytes()).hexdigest()
        self.save()
        with self.assertRaisesRegex(ValueError, 'complete passing'):
            upgrade.verify_release(self.base)

    def test_extra_retired_module_in_rehashed_wheel_is_rejected(self):
        with zipfile.ZipFile(self.wheel, 'a') as package:
            package.writestr('nnfx_practice/ordinary.py', '# retired adapter\n')
        self.record['wheel']['sha256'] = sha256(self.wheel.read_bytes()).hexdigest()
        self.save()
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            upgrade.verify_release(self.base)

    def test_fixture_rerun_must_pass_the_exact_failed_case_and_preserve_original_log(self):
        log = self.base / 'suite.log'
        original = ('test_history (tests.fixture.Checks.test_history) ... FAIL\n'
                    'FAIL: test_history (tests.fixture.Checks.test_history)\n'
                    'Ran 1 tests in 0.1s\nFAILED (failures=1)\n')
        log.write_text(original)
        self.record['offline_suite']['sha256'] = sha256(log.read_bytes()).hexdigest()
        rerun = self.base / 'rerun.log'
        for method, accepted in [('test_unrelated', False), ('test_history', True)]:
            rerun.write_text(f'{method} (tests.fixture.Checks.{method}) ... ok\nRan 1 tests in 0.1s\nOK\n')
            self.record['offline_suite']['reruns'] = [{'path': 'rerun.log', 'sha256': sha256(rerun.read_bytes()).hexdigest()}]
            self.save()
            if accepted:
                upgrade.verify_release(self.base)
            else:
                with self.assertRaises(ValueError):
                    upgrade.verify_release(self.base)
        self.assertEqual(log.read_text(), original)


class PackageDirectoryGuards(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in ('nnfx_practice', 'strategies'):
            (self.root / name).mkdir()
            (self.root / name).chmod(0o775)
        self.kwargs = dict(owner_uid=os.getuid(), owner_gid=os.getgid())

    def test_only_package_roots_lose_group_write_and_repeating_is_safe(self):
        child = self.root / 'nnfx_practice/nested'
        child.mkdir()
        child.chmod(0o750)
        source = child / 'module.py'
        source.write_bytes(b'# retained executable source\n')
        source.chmod(0o640)
        before = (source.read_bytes(), source.stat().st_ino, source.stat().st_mode)
        with patch.object(upgrade, 'command') as command:
            observed = upgrade.tighten_code_directories(self.root, **self.kwargs)
            again = upgrade.tighten_code_directories(self.root, **self.kwargs)
        self.assertEqual({row['mode'] for row in observed.values()}, {0o775})
        self.assertEqual({row['mode'] for row in again.values()}, {0o755})
        self.assertEqual(stat.S_IMODE(child.stat().st_mode), 0o750)
        self.assertEqual((source.read_bytes(), source.stat().st_ino, source.stat().st_mode), before)
        command.assert_not_called()

    def test_unexpected_mode_or_owner_refuses_before_either_directory_changes(self):
        for mode in (0o777, 0o770):
            (self.root / 'strategies').chmod(mode)
            with self.assertRaises(ValueError):
                upgrade.tighten_code_directories(self.root, **self.kwargs)
            self.assertEqual(stat.S_IMODE((self.root / 'nnfx_practice').stat().st_mode), 0o775)
        (self.root / 'strategies').chmod(0o775)
        with self.assertRaises(ValueError):
            upgrade.tighten_code_directories(self.root, owner_uid=os.getuid()+1, owner_gid=os.getgid())
        self.assertEqual(stat.S_IMODE((self.root / 'nnfx_practice').stat().st_mode), 0o775)

    def test_symlink_is_rejected_without_changing_its_target_or_other_package(self):
        target = self.root / 'outside'
        target.mkdir()
        target.chmod(0o775)
        (self.root / 'strategies').rmdir()
        (self.root / 'strategies').symlink_to(target)
        with self.assertRaises(OSError):
            upgrade.tighten_code_directories(self.root, **self.kwargs)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o775)
        self.assertEqual(stat.S_IMODE((self.root / 'nnfx_practice').stat().st_mode), 0o775)


class DashboardBaselineGuards(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / 'config.json'
        self.config = dict(trading_files={'code.py': 'older-pin'}, security={'User': 'nnfx-view'},
                           unit_sha256='same', override_sha256='same', base_files={'view.py': 'same'})
        self.path.write_text(json.dumps(self.config))
        self.dashboard = SimpleNamespace(CONFIG=self.path, RELEASES=self.root,
            active_release=Mock(return_value='dashboard-existing'),
            file_map=Mock(return_value={'view.py': b'unchanged view'}),
            hashes=lambda files: {name: sha256(raw).hexdigest() for name, raw in files.items()},
            verify_host=Mock())
        self.expected = dict(config_sha256=sha256(self.path.read_bytes()).hexdigest(),
            release='dashboard-existing', files={'view.py': sha256(b'unchanged view').hexdigest()})

    def test_full_upgrade_checks_current_plan_baseline_without_changing_helper_config(self):
        raw = self.path.read_bytes()
        original = deepcopy(self.config)
        installed = {'code.py': 'current-protected-plan-pin'}
        self.assertEqual(upgrade.verify_dashboard_before(self.dashboard, self.config, installed, self.expected),
                         'dashboard-existing')
        self.dashboard.verify_host.assert_called_once_with({**original, 'trading_files': installed})
        self.assertEqual(self.config, original)
        self.assertEqual(self.path.read_bytes(), raw)

    def test_changed_configuration_release_or_contents_refuses_before_host_check(self):
        for field in ('config_sha256', 'release', 'files'):
            wrong = deepcopy(self.expected)
            wrong[field] = {} if field == 'files' else 'changed'
            with self.subTest(field=field), self.assertRaises(ValueError):
                upgrade.verify_dashboard_before(self.dashboard, self.config, {}, wrong)
        self.dashboard.verify_host.assert_not_called()
