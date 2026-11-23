"""Incident maintenance guards; no broker or privileged host operations."""

from copy import deepcopy
from contextlib import nullcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from deploy import reconcile_gbpcad as action


class ReconciliationGuards(unittest.TestCase):
    def baseline(self):
        issue = dict(issue_id=action.ISSUE, status='open', pair='GBP-CAD', code='incomplete_entry',
                     set_id=action.SET, leg_no=None, attempt_id=None, first_observed_at='original',
                     broker_evidence_json='{"reason":"original failure"}')
        before = dict(schema=2, notebook=dict(imported_through_transaction_id='2249',
                      qualification_snapshot_id=action.Q0, activated_at=None),
                      immutable_hashes={'runs':'original-run', 'broker_attempts':'original-attempt'},
                      q0_sha256='original-q0', issues=[issue])
        after = deepcopy(before)
        after['schema'] = 3
        after['notebook']['imported_through_transaction_id'] = '2259'
        after['issues'][0].update(status='resolved', operator_id='owner-via-codex')
        return before, after

    def test_only_cursor_schema_and_evidenced_disposition_may_change(self):
        before, after = self.baseline()
        action.verify_preserved(before, after)
        for change in ('q0','run','attempt','activation','additional-issue','open-issue','original-evidence'):
            with self.subTest(change=change):
                altered = deepcopy(after)
                if change == 'q0':
                    altered['q0_sha256'] = 'replaced'
                elif change in ('run','attempt'):
                    altered['immutable_hashes']['runs' if change == 'run' else 'broker_attempts'] = 'replaced'
                elif change == 'activation':
                    altered['notebook']['activated_at'] = 'new activation'
                elif change == 'additional-issue':
                    altered['issues'].append(dict(issue_id='another', status='open'))
                elif change == 'open-issue':
                    altered['issues'][0]['status'] = 'open'
                else:
                    altered['issues'][0]['broker_evidence_json'] = '{}'
                with self.assertRaises(ValueError):
                    action.verify_preserved(before, altered)

    def test_unrelated_issue_cannot_be_resolved_by_the_incident_action(self):
        before, after = self.baseline()
        before['issues'].append(dict(issue_id='other', status='open'))
        after['issues'].append(dict(issue_id='other', status='resolved'))
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            action.verify_preserved(before, after)

    def test_plan_refresh_preserves_prefix_authority_schedule_and_enabled_state(self):
        old = dict(version=2, enabled=True, run_id='original-prefix', schedule='original-schedule',
                   automatic_schedule_authority={'sha256':'original-authority'}, code_sha256='old',
                   evidence={'m09_controller_controls':{'sha256':'old'}, 'other':{'sha256':'preserved'}})
        saved = deepcopy(old)
        reference = {'path':'protected/new-controls.json', 'sha256':'new-controls'}
        updated = action.replacement_plan(old, 'new-code', reference)
        self.assertEqual(old, saved)
        self.assertEqual(updated['run_id'], old['run_id'])
        self.assertEqual(updated['automatic_schedule_authority'], old['automatic_schedule_authority'])
        for key in ('schedule','enabled','version'):
            self.assertEqual(updated[key], old[key])
        self.assertEqual(updated['evidence']['other'], old['evidence']['other'])
        self.assertEqual(updated['evidence']['m09_controller_controls'], reference)

    def test_active_pending_masked_or_enabled_ordinary_controls_defer(self):
        original = {action.SERVICE:dict(LoadState='loaded',ActiveState='failed',Job=''),
                    action.TIMERS[0]:dict(ActiveState='inactive',UnitFileState='disabled',Job=''),
                    action.TIMERS[1]:dict(ActiveState='active',UnitFileState='enabled',Job='')}
        action.idle(original)
        for unit,key,value in ((action.SERVICE,'ActiveState','activating'),
                               (action.SERVICE,'LoadState','masked'),
                               (action.TIMERS[0],'UnitFileState','enabled'),
                               (action.TIMERS[1],'Job','123')):
            with self.subTest(unit=unit,key=key):
                changed = deepcopy(original)
                changed[unit][key] = value
                with self.assertRaises(ValueError):
                    action.idle(changed)

    def test_installed_files_replace_contents_and_remove_group_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary)/'source', Path(temporary)/'target'
            source.mkdir()
            target.mkdir()
            (source/'module.py').write_text('new verified contents')
            (target/'module.py').write_text('old contents')
            (target/'module.py').chmod(0o664)
            action.install_files(source,target,['module.py'])
            self.assertEqual((target/'module.py').read_text(),'new verified contents')
            self.assertEqual((target/'module.py').stat().st_mode & 0o777,0o644)

    def test_public_child_umask_does_not_change_private_parent_umask(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            prior=os.umask(0o077)
            try:
                action.run(sys.executable,'-I','-B','-c',
                    'from pathlib import Path; import sys; p=Path(sys.argv[1]); '
                    'p.mkdir(); (p/"module.py").write_text("public code")',root/'public',child_umask=0o022)
                (root/'private-evidence').write_text('private evidence')
            finally:
                os.umask(prior)
            self.assertEqual((root/'public').stat().st_mode & 0o777,0o755)
            self.assertEqual((root/'public/module.py').stat().st_mode & 0o777,0o644)
            self.assertEqual((root/'private-evidence').stat().st_mode & 0o777,0o600)

    def test_permission_repair_is_bounded_to_verified_public_wheel_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('nnfx_practice','strategies','nnfx_practice-0.1.0.dist-info','other-dependency'):
                (root/name).mkdir(mode=0o700)
                (root/name/'module.py').write_text('unchanged contents')
                (root/name/'module.py').chmod(0o600)
            hashes={name+'/module.py':sha256((root/name/'module.py').read_bytes()).hexdigest()
                    for name in ('nnfx_practice','strategies')}
            changes=action.repair_package_permissions(root,hashes,expected_uid=os.getuid())
            self.assertEqual(len(changes),6)
            for name in ('nnfx_practice','strategies','nnfx_practice-0.1.0.dist-info'):
                self.assertEqual((root/name).stat().st_mode & 0o777,0o755)
                self.assertEqual((root/name/'module.py').stat().st_mode & 0o777,0o644)
                self.assertEqual((root/name/'module.py').read_text(),'unchanged contents')
            self.assertEqual((root/'other-dependency').stat().st_mode & 0o777,0o700)
            self.assertEqual((root/'other-dependency/module.py').stat().st_mode & 0o777,0o600)
            self.assertEqual(action.repair_package_permissions(root,hashes,expected_uid=os.getuid()),[])

    def test_permission_repair_checks_all_paths_before_touching_any_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('nnfx_practice','strategies','nnfx_practice-0.1.0.dist-info'):
                (root/name).mkdir(mode=0o700)
            (root/'nnfx_practice/public.py').write_text('verified')
            (root/'nnfx_practice/public.py').chmod(0o600)
            hashes={'nnfx_practice/public.py':sha256(b'verified').hexdigest()}
            (root/'strategies/linked').symlink_to(root/'nnfx_practice/public.py')
            with self.assertRaises(ValueError):
                action.repair_package_permissions(root,hashes,expected_uid=os.getuid())
            self.assertEqual((root/'nnfx_practice').stat().st_mode & 0o777,0o700)
            self.assertEqual((root/'nnfx_practice/public.py').stat().st_mode & 0o777,0o600)

    def test_diagnostic_export_keeps_private_worker_files_out_and_tolerates_partial_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive,output=Path(temporary)/'archive',Path(temporary)/'output'
            archive.mkdir()
            output.mkdir()
            (archive/'host-fixture-command.json').write_text('{"returncode":1}')
            (archive/'controller-controls.json').write_text('{partial')
            (archive/'worker').mkdir()
            (archive/'worker/private-read.json').write_text('{"private":"not for diagnostic export"}')
            action.export_diagnostics(archive,output,SimpleNamespace(st_uid=os.getuid(),st_gid=os.getgid()))
            self.assertEqual(json.loads((output/'host-fixture-command.json').read_text()),{'returncode':1})
            self.assertEqual(json.loads((output/'diagnostic-export-errors.json').read_text())[0]['file'],
                             'controller-controls.json')
            self.assertFalse((output/'worker').exists())

    def admin_flow(self, fail_fixture=False, continuation=False, installed_checkpoint=False):
        """Exercise the actual administrative ordering with no privileged calls."""
        from contextlib import ExitStack
        from deploy import dashboard_deploy as dashboard
        from deploy import continue_gbpcad_reconciliation as followup
        from nnfx_practice import qualification as q
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            base = Path(temporary)
            root, code, data, plans = [base/name for name in ('frozen','installed','data','plans')]
            for path in (root,code,data,plans,plans/'evidence'):
                path.mkdir()
            relative = 'nnfx_practice/notebook.py'
            for directory,body in ((root,'verified new reader'),(code,'old reader')):
                (directory/'nnfx_practice').mkdir()
                (directory/relative).write_text(body)
                (directory/'strategies').mkdir()
            old_hashes={relative:sha256((code/relative).read_bytes()).hexdigest()}
            new_hashes={relative:sha256((root/relative).read_bytes()).hexdigest()}
            wheel=root/action.WHEEL_NAME
            with zipfile.ZipFile(wheel,'w') as package:
                package.writestr(relative,(root/relative).read_bytes())
            suite=root/'suite.log'
            suite.write_text('Ran 555 tests in 1.000s\n\nOK\n')
            (root/'operation-verification.json').write_text(json.dumps(dict(source_hashes=new_hashes,
                operation_hashes={},wheel=dict(path=wheel.name,sha256=sha256(wheel.read_bytes()).hexdigest()),
                suite=dict(path=suite.name,sha256=sha256(suite.read_bytes()).hexdigest()))))
            old=dict(version=2,mode='qualification',enabled=True,run_id='same-run-prefix',kernel='test-kernel',
                     code_sha256=action.OLD_CODE,account_binding_sha256=action.ACCOUNT,
                     evidence={'m09_controller_controls':{'path':'old-controls'}})
            plan_path=plans/'practice-a.json'
            plan_path.write_text(json.dumps(old))
            releases=base/'releases'
            releases.mkdir()
            previous=releases/'dashboard-previous'
            (previous/'nnfx_practice').mkdir(parents=True)
            previous.chmod(0o755)
            (previous/'nnfx_practice').chmod(0o755)
            (previous/relative).write_text('old reader')
            current=releases/'current'
            current.symlink_to(previous.name)
            config=base/'dashboard-config.json'
            config.write_text(json.dumps(dict(trading_files=old_hashes,base_files=old_hashes)))
            states={action.SERVICE:dict(LoadState='loaded',ActiveState='failed',UnitFileState='static',Job=''),
                    action.TIMERS[0]:dict(LoadState='loaded',ActiveState='inactive',UnitFileState='disabled',Job=''),
                    action.TIMERS[1]:dict(LoadState='loaded',ActiveState='active',UnitFileState='enabled',Job='')}
            events=[]
            before,after=self.baseline()
            completed=False
            checkpoint_bytes=None
            purelib=base/'purelib'
            purelib.mkdir()
            if continuation:
                (code/relative).write_text((root/relative).read_text())
                (previous/relative).write_text((root/relative).read_text())
                config.write_text(json.dumps(dict(trading_files=old_hashes,base_files=new_hashes)))
                checkpoint=plans/'evidence'/followup.CHECKPOINT
                checkpoint.mkdir()
                original_controls=deepcopy(states)
                states[action.SERVICE]['LoadState']='masked'
                states[action.TIMERS[1]]['ActiveState']='inactive'
                saved=dict(status='inspection_required',phase='compatible_reader_deployed',broker_mutations=0,
                           ordinary_activated=False,before=before,before_controls=original_controls,
                           archive=str(checkpoint),release=previous.name)
                checkpoint_bytes=(json.dumps(saved)+'\n').encode()
                (checkpoint/'receipt.json').write_bytes(checkpoint_bytes)
                (checkpoint/'previous-plan.json').write_bytes(plan_path.read_bytes())
                original_verification=json.dumps({'source_hashes':new_hashes}).encode()
                (checkpoint/'operation-verification.json').write_bytes(original_verification)
                manifest=json.loads((root/'operation-verification.json').read_text())
                manifest.update(checkpoint_receipt_sha256=sha256(checkpoint_bytes).hexdigest(),
                                original_verification_sha256=sha256(original_verification).hexdigest())
                (root/'operation-verification.json').write_text(json.dumps(manifest))
                backup_checkpoint=checkpoint
                if installed_checkpoint:
                    original_checkpoint=checkpoint
                    checkpoint=plans/'evidence'/'gbpcad-continue-6a8d0b04c443'
                    checkpoint.mkdir()
                    saved.update(phase='checking_host_controls',archive=str(checkpoint),
                                 original_archive=str(original_checkpoint))
                    checkpoint_bytes=(json.dumps(saved)+'\n').encode()
                    (checkpoint/'receipt.json').write_bytes(checkpoint_bytes)
                    (checkpoint/'operation-verification.json').write_bytes(original_verification)
                    failure=dict(cleanup_errors=[],deployed_source_hashes=new_hashes,results=dict(
                        actual_notebook_files_preserved=True,fixture_checks_passed=False))
                    (checkpoint/'controller-controls.json').write_text(json.dumps(failure))
                    manifest.update(checkpoint_receipt_sha256=sha256(checkpoint_bytes).hexdigest(),
                        backup_archive=str(original_checkpoint),
                        backup_receipt_sha256=sha256((original_checkpoint/'receipt.json').read_bytes()).hexdigest(),
                        failed_controls_sha256=sha256((checkpoint/'controller-controls.json').read_bytes()).hexdigest())
                    (root/'operation-verification.json').write_text(json.dumps(manifest))
                    config.write_text(json.dumps(dict(trading_files=new_hashes,base_files=new_hashes)))
                    for name in ('nnfx_practice','strategies','nnfx_practice-0.1.0.dist-info'):
                        (purelib/name).mkdir(mode=0o700)
                    (purelib/relative).write_bytes((root/relative).read_bytes())
                    (purelib/relative).chmod(0o600)

            def fake_run(*args,**kwargs):
                nonlocal completed
                args=[str(x) for x in args]
                events.append(args)
                if args[0]=='systemctl':
                    if args[1] in ('mask','unmask'):
                        states[action.SERVICE]['LoadState']='masked' if args[1]=='mask' else 'loaded'
                    else:
                        states[args[-1]]['ActiveState']='active' if args[1]=='start' else 'inactive'
                elif args[0]=='/usr/sbin/runuser':
                    self.assertEqual(states[action.SERVICE]['LoadState'],'masked')
                    self.assertTrue(all(states[unit]['ActiveState']=='inactive' for unit in action.TIMERS))
                    if '-c' in args:
                        self.assertEqual((purelib/'nnfx_practice').stat().st_mode & 0o777,0o755)
                        return json.dumps(dict(code='new-code',schema=3))
                    directory=Path(args[-1])
                    (directory/'result.json').write_text(json.dumps(dict(outcome='reconciled_and_resolved')))
                    completed=True
                elif any(x.endswith('check_m09_system.py') for x in args):
                    self.assertEqual(states[action.SERVICE]['LoadState'],'loaded')
                    if fail_fixture:
                        raise RuntimeError('fixture failed')
                    Path(args[-1]).write_text(json.dumps(dict(cleanup_errors=[],results=dict(
                        fixture_checks_passed=True,actual_notebook_files_preserved=True))))
                elif '-c' in args and 'dict(code=' in args[-1]:
                    return json.dumps(dict(code='new-code' if installed_checkpoint else action.OLD_CODE,
                                           hashes=new_hashes if installed_checkpoint else old_hashes))
                elif '-c' in args and 'q.code_hashes()' in args[-1]:
                    return json.dumps(new_hashes)
                elif '-c' in args and 'sysconfig' in args[-1]:
                    return str(purelib)
                return ''

            def replace(path,expected,body):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(),expected)
                path.write_bytes(body)

            for name,value in dict(ROOT=root,CODE=code,DATA=data,PYTHON=code/'python',run=fake_run,
                                   state=lambda unit:deepcopy(states[unit]),claims=lambda:{'existing.claim':'untouched'},
                                   copied_state=lambda _:deepcopy(after if completed else before),
                                   exclusion=nullcontext).items():
                stack.enter_context(patch.object(action,name,value))
            for name,value in dict(RELEASES=releases,CURRENT=current,CONFIG=config,locked=nullcontext,
                                   active_release=lambda:os.readlink(current),
                                   protected=lambda *a,**k:None,protected_parents=lambda *a:None,
                                   quiet_window=lambda:None,verify_host=lambda _:None,
                                   health=lambda:events.append(['dashboard_health']),
                                   command=lambda *a:events.append(['dashboard',*a])).items():
                stack.enter_context(patch.object(dashboard,name,value))
            for name,value in dict(PLAN_DIRECTORY=plans,code_hashes=lambda:new_hashes,
                                   code_identity=lambda:'new-code',host_identity=lambda:('boot','test-kernel'),
                                   sealed_bytes=lambda path:Path(path).read_bytes(),validate_evidence=lambda *a:None,
                                   _evidence=lambda _: {},automatic_authority=lambda _:None,
                                   host_controls=lambda *a:None,schedule_controls=lambda *a:None).items():
                stack.enter_context(patch.object(q,name,value))
            stack.enter_context(patch('nnfx_practice.config.read_registry',return_value={'practice-a':object()}))
            stack.enter_context(patch('tests.arm_m10_qualification.replace_plan',side_effect=replace))
            stack.enter_context(patch('os.geteuid',return_value=0))
            stack.enter_context(patch('os.chown'))
            stack.enter_context(patch('sys.argv',[str(root/'deploy/reconcile_gbpcad.py')]))
            stack.enter_context(patch.object(followup,'ROOT',root))
            if installed_checkpoint:
                repair=action.repair_package_permissions
                stack.enter_context(patch.object(action,'repair_package_permissions',
                    side_effect=lambda directory,hashes:repair(directory,hashes,expected_uid=os.getuid())))
            notebook=data/'var/notebooks/notebook-a.sqlite3'
            notebook.parent.mkdir(parents=True)
            for suffix in ('','-wal','-shm'):
                Path(str(notebook)+suffix).write_bytes(b'original notebook file')
            if continuation:
                backup=backup_checkpoint/'notebook-before'
                backup.mkdir()
                for suffix in ('','-wal','-shm'):
                    (backup/(notebook.name+suffix)).write_bytes(Path(str(notebook)+suffix).read_bytes())
            prior_umask=os.umask(0o077)
            try:
                result=(followup.main(checkpoint_id=checkpoint.name,installed_checkpoint=installed_checkpoint)
                        if continuation else action.main())
            finally:
                os.umask(prior_umask)
            diagnostic = dict(receipts=[json.loads(path.read_text()) for path in plans.rglob('receipt.json')],events=events)
            if fail_fixture:
                self.assertEqual(result,2)
                self.assertFalse(completed)
                self.assertEqual(json.loads(plan_path.read_text()),old)
                self.assertEqual(states[action.SERVICE]['LoadState'],'masked',diagnostic)
                self.assertTrue(all(states[unit]['ActiveState']=='inactive' for unit in action.TIMERS))
            else:
                self.assertEqual(result,0,diagnostic)
                self.assertTrue(completed)
                self.assertEqual(states[action.SERVICE]['LoadState'],'loaded')
                self.assertEqual(states[action.TIMERS[1]]['ActiveState'],'active')
                updated=json.loads(plan_path.read_text())
                self.assertEqual(updated['run_id'],old['run_id'])
                self.assertTrue(updated['enabled'])
                self.assertEqual(current.resolve().stat().st_mode & 0o777,0o755)
                self.assertEqual((current.resolve()/'nnfx_practice').stat().st_mode & 0o777,0o755)
                health=events.index(['dashboard_health'])
                disposition=next(i for i,x in enumerate(events) if x[0]=='/usr/sbin/runuser' and '--worker' in x)
                if installed_checkpoint:
                    self.assertFalse(any('pip' in x for x in events))
                    self.assertEqual(len([x for x in events if x[0]=='/usr/sbin/runuser' and '-c' in x]),2)
                    fixtures=next(i for i,x in enumerate(events) if any(v.endswith('check_m09_system.py') for v in x))
                    self.assertLess(health,fixtures)
                    self.assertLess(fixtures,disposition)
                else:
                    install=next(i for i,x in enumerate(events) if 'pip' in x and '--dry-run' not in x)
                    self.assertLess(health,install)
                    self.assertLess(install,disposition)
                if continuation:
                    self.assertEqual((checkpoint/'receipt.json').read_bytes(),checkpoint_bytes)
                    self.assertEqual(current.resolve(),previous)
                    self.assertFalse(any(x[:2]==['dashboard','restart'] for x in events))

    def test_administrator_flow_orders_reader_host_checks_disposition_and_schedule_restore(self):
        self.admin_flow()

    def test_failed_host_fixture_withholds_actual_notebook_write_and_leaves_triggers_excluded(self):
        self.admin_flow(fail_fixture=True)

    def test_invalid_renamed_wheel_is_rejected_before_administrative_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            wheel=root/'package.whl'
            wheel.write_bytes(b'not reached: filename validation precedes archive inspection')
            verification={'wheel':{'path':wheel.name,'sha256':sha256(wheel.read_bytes()).hexdigest()}}
            with self.assertRaisesRegex(ValueError,'valid distribution wheel filename'):
                action.verified_wheel(root,verification,{})

    def test_continuation_preserves_completed_reader_and_original_failure_archive(self):
        self.admin_flow(continuation=True)

    def test_continuation_host_failure_keeps_both_schedules_excluded(self):
        self.admin_flow(continuation=True,fail_fixture=True)

    def test_installed_package_recovery_repairs_permissions_without_reinstalling_or_redeploying_reader(self):
        self.admin_flow(continuation=True,installed_checkpoint=True)

    def test_installed_package_recovery_withholds_disposition_after_host_failure(self):
        self.admin_flow(continuation=True,installed_checkpoint=True,fail_fixture=True)

    def test_continuation_refuses_any_checkpoint_after_a_notebook_write_or_package_install(self):
        from deploy.continue_gbpcad_reconciliation import verify_checkpoint
        before,_=self.baseline()
        receipt=dict(status='inspection_required',phase='compatible_reader_deployed',broker_mutations=0,
                     ordinary_activated=False,before=before,before_controls={
                         action.TIMERS[0]:{'UnitFileState':'disabled'},action.TIMERS[1]:{'UnitFileState':'enabled'}})
        states={action.SERVICE:dict(LoadState='masked',ActiveState='failed',Job=''),
                action.TIMERS[0]:dict(ActiveState='inactive',UnitFileState='disabled',Job=''),
                action.TIMERS[1]:dict(ActiveState='inactive',UnitFileState='enabled',Job='')}
        verify_checkpoint(receipt,states,action.OLD_CODE)
        for change in ('new-code','advanced-cursor','begun-worker','different-phase','active-timer','unmasked'):
            with self.subTest(change=change):
                altered,controls=deepcopy(receipt),deepcopy(states)
                code=action.OLD_CODE
                if change=='new-code':
                    code='new-code'
                elif change=='advanced-cursor':
                    altered['before']['notebook']['imported_through_transaction_id']='2259'
                elif change=='begun-worker':
                    altered['result']={'proof':'already written'}
                elif change=='different-phase':
                    altered['phase']='ready_for_evidenced_disposition'
                elif change=='active-timer':
                    controls[action.TIMERS[1]]['ActiveState']='active'
                else:
                    controls[action.SERVICE]['LoadState']='loaded'
                with self.assertRaises(ValueError):
                    verify_checkpoint(altered,controls,code)


if __name__ == '__main__':
    unittest.main()
