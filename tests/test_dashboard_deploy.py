"""Deployment boundary tests: temporary releases and simulated services, no broker."""

from contextlib import ExitStack, redirect_stdout
from datetime import datetime
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from deploy import dashboard_deploy as d
from deploy import install_dashboard_deployer as installer


class DeploymentChecks(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.callback(os.umask, os.umask(0o022))
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temp)
        for key, suffix in dict(RELEASES='releases', CURRENT='releases/current', CONFIG='config.json',
                                STATE='state', HELPER='bin/nnfx-dashboard-deploy', UNIT_FILE='dashboard.service',
                                DROPIN='dashboard.service.d/layout.conf', CODE='trading').items():
            self.stack.enter_context(patch.object(d, key, self.root / suffix))
        self.stack.enter_context(patch.object(installer, 'POLICY', self.root / 'sudoers.d/deployer'))
        self.stack.enter_context(patch.object(d, 'ADMIN_UID', os.geteuid()))
        # The fixture root represents the protected filesystem; /tmp itself is intentionally shared.
        def parents(path):
            for parent in reversed(path.parents):
                if parent == self.root or self.root in parent.parents:
                    d.protected(parent, directory=True)
        self.stack.enter_context(patch.object(d, 'protected_parents', side_effect=parents))
        for path in (d.RELEASES, d.STATE, d.HELPER.parent, d.DROPIN.parent, d.CODE/'nnfx_practice',
                     d.CODE/'strategies', installer.POLICY.parent):
            path.mkdir(parents=True, exist_ok=True, mode=0o755)
            path.chmod(0o755)
        self.previous = 'dashboard-original-1234'
        release = d.RELEASES / self.previous
        release.mkdir(mode=0o755)
        self.base = {name: b'original dashboard' for name in d.ALLOWED}
        self.base['nnfx_practice/entry.py'] = b'protected trading code'
        for name, body in self.base.items():
            target = release / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.write_bytes(body)
            target.chmod(0o644)
        for path in release.rglob('*'):
            if path.is_dir():path.chmod(0o755)
        d.CURRENT.symlink_to(self.previous)
        d.UNIT_FILE.write_bytes(b'fixed service definition')
        d.DROPIN.write_text('[Service]\nWorkingDirectory='+str(d.CURRENT)+'\n')
        self.trade = d.CODE/'nnfx_practice/entry.py'
        self.trade.write_bytes(b'protected trading code')
        for path in (d.UNIT_FILE,d.DROPIN,self.trade):path.chmod(0o644)
        self.settings = {key: 'same' for key in d.SECURITY}
        self.settings.update(User='nnfx-view', Group='nnfx-read', SystemCallFilter='~connect mount')
        self.config = dict(unit_sha256=d.digest(d.UNIT_FILE.read_bytes()), override_sha256=d.digest(d.DROPIN.read_bytes()),
                           security=d.security(self.settings),base_files=d.hashes(self.base),
                           trading_files={'nnfx_practice/entry.py':d.digest(self.trade.read_bytes())})
        d.CONFIG.write_text(json.dumps(self.config))
        d.CONFIG.chmod(0o644)
        self.controls = {name:dict(ActiveState='inactive',MainPID='0',Job='',UnitFileState='disabled',NextElapseUSecRealtime='') for name in d.CONTROLS}
        self.controls[d.CONTROLS[2]].update(ActiveState='active',UnitFileState='enabled',NextElapseUSecRealtime='future')
        self.service = dict(ActiveState='active',WorkingDirectory=str(d.CURRENT),DropInPaths=str(d.DROPIN),**self.settings)
        self.stack.enter_context(patch.object(d,'properties',side_effect=lambda unit,keys:{k:self.service[k] for k in keys}))
        self.stack.enter_context(patch.object(d,'control_state',side_effect=lambda:json.loads(json.dumps(self.controls))))
        self.command = self.stack.enter_context(patch.object(d,'command',return_value=''))
        self.health = self.stack.enter_context(patch.object(d,'health'))
        self.window = self.stack.enter_context(patch.object(d,'quiet_window'))
        self.output = self.stack.enter_context(redirect_stdout(StringIO()))
        self.raw = json.dumps({'expected_release':self.previous,'files':{'nnfx_practice/templates/controllers.html':'new wording'}}).encode()

    def test_success_changes_only_allowed_files_and_restarts_only_dashboard(self):
        before=d.file_map(d.RELEASES/self.previous)
        result=d.deploy(self.raw)
        current=d.file_map(d.RELEASES/d.active_release())
        self.assertEqual(result['status'],'deployed')
        self.assertEqual({p for p in current if current[p]!=before[p]}, {'nnfx_practice/templates/controllers.html'})
        self.assertEqual(d.file_map(d.RELEASES/self.previous),before)
        self.assertEqual(self.trade.read_bytes(),b'protected trading code')
        self.command.assert_called_once_with('restart',d.UNIT)
        self.assertEqual(d.DROPIN.read_text(),'[Service]\nWorkingDirectory='+str(d.CURRENT)+'\n')
        self.assertEqual(json.loads(next(d.STATE.glob('*.json')).read_text())['status'],'deployed')

    def test_submitted_python_is_saved_but_never_executed_by_privileged_helper(self):
        marker=self.root/'must-not-exist'
        body=f'from pathlib import Path\nPath({str(marker)!r}).write_text("root execution")\n'
        raw=json.dumps({'expected_release':self.previous,'files':{'nnfx_practice/dashboard.py':body}}).encode()
        d.deploy(raw)
        self.assertFalse(marker.exists())
        self.command.assert_called_once_with('restart',d.UNIT)

    def test_trading_paths_traversal_absolute_paths_and_extra_fields_are_rejected(self):
        for name in ('nnfx_practice/entry.py','strategies/c1.py','/etc/sudoers','../etc/sudoers',
                     'nnfx_practice/templates/../../entry.py','nnfx_practice/serve.py','deploy.py'):
            with self.subTest(name=name),self.assertRaises(d.Refused):
                d.deploy(json.dumps({'expected_release':self.previous,'files':{name:'untrusted'}}).encode())
        with self.assertRaises(d.Refused):
            d.deploy(json.dumps({'expected_release':self.previous,'files':{},'command':'sh'}).encode())
        self.command.assert_not_called()
        self.assertEqual(d.active_release(),self.previous)

    def test_duplicate_json_fields_oversized_data_and_nontext_are_rejected(self):
        for raw in (b'{"files":{},"files":{}}', b' '* (d.MAX_INPUT+1),
                    json.dumps({'expected_release':self.previous,'files':{'nnfx_practice/dashboard.py':3}}).encode(),
                    json.dumps({'expected_release':'../other','files':{'nnfx_practice/dashboard.py':'x'}}).encode()):
            with self.subTest(raw=raw[:60]),self.assertRaises((ValueError,TypeError)):
                d.deploy(raw)
        self.command.assert_not_called()

    def test_stale_update_is_rejected_before_restart(self):
        d.CURRENT.unlink();d.CURRENT.symlink_to('dashboard-other-5678')
        with self.assertRaisesRegex(d.Refused,'changed since preparation'):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_active_controller_or_trading_window_defers_without_service_changes(self):
        self.controls[d.CONTROLS[0]]['ActiveState']='active'
        with self.assertRaisesRegex(d.Refused,'controller is idle'):d.deploy(self.raw)
        self.controls[d.CONTROLS[0]]['ActiveState']='inactive'
        self.window.side_effect=d.Refused('scheduled trading window')
        with self.assertRaisesRegex(d.Refused,'trading window'):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_changed_unit_security_or_trading_source_is_rejected(self):
        for path in (d.UNIT_FILE,self.trade):
            original=path.read_bytes();path.write_bytes(b'changed')
            with self.assertRaises(d.Refused):d.deploy(self.raw)
            path.write_bytes(original)
        self.service['NoNewPrivileges']='no'
        with self.assertRaisesRegex(d.Refused,'restrictions changed'):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_unapproved_base_file_change_and_extra_release_file_are_rejected(self):
        path=d.RELEASES/self.previous/'nnfx_practice/entry.py'
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(d.Refused,'outside the dashboard'):d.deploy(self.raw)
        path.write_bytes(self.base['nnfx_practice/entry.py'])
        path.with_name('extra.py').write_bytes(b'extra')
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_symlink_writable_and_hardlinked_files_are_rejected(self):
        path=d.RELEASES/self.previous/'nnfx_practice/dashboard.py'
        original=path.read_bytes()
        path.unlink();path.symlink_to(self.trade)
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        path.unlink();path.write_bytes(original);path.chmod(0o666)
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        path.unlink();os.link(self.trade,path)
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_failed_health_restores_previous_release_and_records_failure(self):
        self.health.side_effect=[d.Refused('bad page'),None]
        with self.assertRaisesRegex(d.Refused,'bad page'):d.deploy(self.raw)
        self.assertEqual(d.active_release(),self.previous)
        self.assertEqual(self.command.call_args_list, [unittest.mock.call('restart',d.UNIT)]*2)
        receipt=json.loads(next(d.STATE.glob('*.json')).read_text())
        self.assertEqual(receipt['status'],'failed')
        self.assertEqual(receipt['rollback'],'previous dashboard restored')

    def test_failed_restart_restores_previous_release(self):
        self.command.side_effect=[RuntimeError('restart failure'), '']
        with self.assertRaises(RuntimeError):d.deploy(self.raw)
        self.assertEqual(d.active_release(),self.previous)
        self.assertEqual(self.command.call_count,2)

    def test_failed_rollback_is_recorded_without_touching_trading_controls(self):
        self.health.side_effect=d.Refused('bad page')
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        receipt=json.loads(next(d.STATE.glob('*.json')).read_text())
        self.assertEqual(receipt['rollback'],'failed; administrator attention required')
        self.assertTrue(all(call.args==('restart',d.UNIT) for call in self.command.call_args_list))

    def test_deployments_are_serialized(self):
        with d.locked(),self.assertRaises(BlockingIOError):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_retry_preserves_and_reuses_matching_release(self):
        self.health.side_effect=[d.Refused('bad page'),None]
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        candidate=next(d.RELEASES.glob('dashboard-deploy-*'))
        before=(candidate/'nnfx_practice/dashboard.py').stat().st_ino
        self.health.side_effect=None
        d.deploy(self.raw)
        self.assertEqual((candidate/'nnfx_practice/dashboard.py').stat().st_ino,before)

    def test_changed_existing_release_is_never_overwritten(self):
        self.health.side_effect=[d.Refused('bad page'),None]
        with self.assertRaises(d.Refused):d.deploy(self.raw)
        candidate=next(d.RELEASES.glob('dashboard-deploy-*'))
        (candidate/'nnfx_practice/dashboard.py').write_text('unexpected')
        self.command.reset_mock()
        with self.assertRaisesRegex(d.Refused,'does not match'):d.deploy(self.raw)
        self.command.assert_not_called()

    def test_installer_grants_only_fixed_no_argument_command_after_checks(self):
        d.CONFIG.unlink();d.CURRENT.unlink()
        self.service['WorkingDirectory']=str(d.RELEASES/self.previous)
        original=('[Service]\nWorkingDirectory='+self.service['WorkingDirectory']+'\n').encode()
        d.DROPIN.write_bytes(original)
        def command(*args):
            if args==('restart',d.UNIT):
                self.service['WorkingDirectory']=d.DROPIN.read_text().split('WorkingDirectory=')[1].strip()
        self.command.side_effect=command
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.pwd,'getpwnam'),patch.object(installer.subprocess,'run') as run:
            installer.install(d,b'reviewed helper',b'fixed service definition')
        self.assertEqual(installer.POLICY.read_text(),installer.POLICY_TEXT)
        self.assertTrue(installer.POLICY_TEXT.endswith('nnfx-dashboard-deploy ""\n'))
        self.assertNotIn('systemctl',installer.POLICY_TEXT)
        self.assertNotIn('*',installer.POLICY_TEXT)
        self.assertEqual(d.HELPER.read_bytes(),b'reviewed helper')
        self.assertEqual(d.active_release(),self.previous)
        self.assertEqual(run.call_count,2)

    def test_installer_tightens_only_observed_directory_modes_and_preserves_code(self):
        packages=(d.CODE/'nnfx_practice',d.CODE/'strategies')
        for path in packages:path.chmod(0o775)
        original_lstat=Path.lstat
        def root_group(path):
            info=original_lstat(path)
            if path in packages:
                fields=list(info);fields[5]=0
                return os.stat_result(fields)
            return info
        with patch.object(Path,'lstat',root_group):
            hashes,repairs=installer.inspect_trading_files(d)
            self.assertEqual(repairs,list(packages))
            self.assertTrue(all(p.stat().st_mode & 0o777 == 0o775 for p in packages))
            self.test_installer_grants_only_fixed_no_argument_command_after_checks()
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o755 for p in packages))
        self.assertEqual(hashes,installer.inspect_trading_files(d)[0])
        self.assertEqual(self.trade.read_bytes(),b'protected trading code')

    def test_installer_refuses_other_unsafe_modes_and_writable_descendants(self):
        package=d.CODE/'nnfx_practice'
        for mode in (0o777,0o2775):
            package.chmod(mode)
            with self.subTest(mode=mode),self.assertRaises(d.Refused):installer.inspect_trading_files(d)
            self.assertEqual(package.stat().st_mode & 0o7777,mode)
        package.chmod(0o755)
        self.trade.chmod(0o664)
        with self.assertRaises(d.Refused):installer.inspect_trading_files(d)
        self.assertEqual(self.trade.stat().st_mode & 0o777,0o664)
        self.command.assert_not_called()

    def test_installer_does_not_repair_group_writable_directory_owned_by_another_group(self):
        package=d.CODE/'nnfx_practice';package.chmod(0o775)
        original_lstat=Path.lstat
        def other_group(path):
            info=original_lstat(path)
            if path==package:
                fields=list(info);fields[5]=12345
                return os.stat_result(fields)
            return info
        with patch.object(Path,'lstat',other_group),self.assertRaises(d.Refused):installer.inspect_trading_files(d)
        self.assertEqual(package.stat().st_mode & 0o777,0o775)

    def test_installer_failed_health_restores_override_and_does_not_grant_permission(self):
        d.CONFIG.unlink();d.CURRENT.unlink()
        self.service['WorkingDirectory']=str(d.RELEASES/self.previous)
        original=('[Service]\nWorkingDirectory='+self.service['WorkingDirectory']+'\n').encode()
        d.DROPIN.write_bytes(original)
        self.health.side_effect=[None,d.Refused('bad page'),None]
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.pwd,'getpwnam'),patch.object(installer.subprocess,'run'),self.assertRaises(d.Refused):
            installer.install(d,b'reviewed helper',b'fixed service definition')
        self.assertEqual(d.DROPIN.read_bytes(),original)
        self.assertFalse(installer.POLICY.exists())
        self.assertFalse(d.HELPER.exists())
        self.assertFalse(d.CURRENT.exists())

    def test_invalid_combined_sudo_policy_revokes_grant_and_restores_service(self):
        d.CONFIG.unlink();d.CURRENT.unlink()
        self.service['WorkingDirectory']=str(d.RELEASES/self.previous)
        original=('[Service]\nWorkingDirectory='+self.service['WorkingDirectory']+'\n').encode()
        d.DROPIN.write_bytes(original)
        def command(*args):
            if args==('restart',d.UNIT):
                self.service['WorkingDirectory']=d.DROPIN.read_text().split('WorkingDirectory=')[1].strip()
        self.command.side_effect=command
        with patch.object(installer.os,'geteuid',return_value=0),patch.object(installer.pwd,'getpwnam'), \
                patch.object(installer.subprocess,'run',side_effect=[None,subprocess.CalledProcessError(1,'visudo')]), \
                self.assertRaises(subprocess.CalledProcessError):
            installer.install(d,b'reviewed helper',b'fixed service definition')
        self.assertFalse(installer.POLICY.exists())
        self.assertEqual(d.DROPIN.read_bytes(),original)

    def test_second_update_keeps_previous_dashboard_changes_and_excludes_trading(self):
        d.deploy(self.raw)
        next_request=json.dumps({'expected_release':d.active_release(),
                                 'files':{'nnfx_practice/templates/base.html':'updated header'}}).encode()
        d.deploy(next_request)
        files=d.file_map(d.RELEASES/d.active_release())
        self.assertEqual(files['nnfx_practice/templates/controllers.html'],b'new wording')
        self.assertEqual(files['nnfx_practice/templates/base.html'],b'updated header')
        self.assertEqual(files['nnfx_practice/entry.py'],b'protected trading code')


class BoundaryChecks(unittest.TestCase):
    def test_helper_ignores_pythonpath_and_sitecustomize(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            marker=root/'injected'
            (root/'sitecustomize.py').write_text(f'from pathlib import Path; Path({str(marker)!r}).touch()')
            helper=root/'deployer'
            helper.write_bytes(Path(d.__file__).read_bytes())
            helper.chmod(0o755)
            result=subprocess.run([str(helper),'forbidden-argument'],env={**os.environ,'PYTHONPATH':temp},
                                  cwd=temp,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('no arguments',result.stderr)
            self.assertFalse(marker.exists())

    def test_root_helper_rejects_arguments_and_unprivileged_execution_before_input(self):
        for uid,args in ((1001,['helper']),(0,['helper','/tmp/untrusted.py'])):
            with patch.object(d.os,'geteuid',return_value=uid),patch.object(d.sys,'argv',args),patch.object(d,'deploy') as deploy,self.assertRaises(SystemExit):
                d.main()
            deploy.assert_not_called()

    def test_system_commands_use_fixed_executable_clean_environment_and_no_shell(self):
        with patch.object(d.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'ok','')) as run:
            d.command('restart',d.UNIT)
        args,kwargs=run.call_args
        self.assertEqual(args[0],['/usr/bin/systemctl','--no-pager','--no-ask-password','restart',d.UNIT])
        self.assertEqual(kwargs['env'],d.ENV)
        self.assertEqual(kwargs['cwd'],'/')
        self.assertNotIn('shell',kwargs)
        self.assertNotIn('PYTHONPATH',kwargs['env'])

    def test_http_redirects_are_not_followed(self):
        self.assertIsNone(d.NoRedirect().redirect_request(None,None,302,'redirect',{},'http://example.invalid'))

    def test_real_calendar_window_excludes_scheduled_run(self):
        for timestamp in ('2026-11-20T21:35:00+00:00','2026-11-20T21:50:00+00:00','2026-11-20T22:10:00+00:00'):
            with patch.object(d,'datetime') as clock:
                clock.now.return_value=datetime.fromisoformat(timestamp)
                with self.assertRaises(d.Refused):d.quiet_window()
        with patch.object(d,'datetime') as clock:
            clock.now.return_value=datetime.fromisoformat('2026-11-20T05:00:00+00:00')
            d.quiet_window()

    def test_file_ownership_check_is_enforced(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'file';path.write_text('fixture');path.chmod(0o644)
            with patch.object(d,'ADMIN_UID',os.geteuid()+1),self.assertRaises(d.Refused):d.protected(path)


if __name__=='__main__':unittest.main()
