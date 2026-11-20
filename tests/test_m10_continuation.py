"""Offline no-entry continuation checks; never invoke a real broker/systemd."""

from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from nnfx_practice import qualification as q
from nnfx_practice.config import PERMITTED_PAIRS
from . import continue_m10_qualification as tool
from .m07_support import M07Case
from .test_m10_arming import waiting_fixture


def fixtures():
    old = dict(version=1, enabled=True, host=q.PRACTICE_HOST, controller_id='practice-a', notebook_id='notebook-a',
               run_id='offline-old', dispatch_at='2026-11-19T21:50:00+00:00', account_binding_sha256='a'*64,
               manifest_sha256='b'*64, code_sha256='c'*64, config_sha256='d'*64,
               boot_id='old-boot', kernel='old-kernel', evidence={'m09_controller_controls':{}})
    tables = dict(notebook=[dict(manifest_hash='b'*64, qualification_snapshot_id='offline-q0',
        qualification_transaction_id='100', imported_through_transaction_id='100',
        activated_at=None, activation_snapshot_id=None, activation_transaction_id=None)],
        runs=[dict(run_id='offline-old', status='completed', ended_at='2026-11-19T21:50:15Z',
                   code_hash='c'*64, config_hash='d'*64, strategy_hash='b'*64,
                   final_snapshot_id='offline-final',sizing_balance='1000')],
        run_invocations=[dict(mode='qualification',evidence_json={'source':'practice_execution'})],
        stages=[dict(status='completed'),dict(status='completed')],
        pair_decisions=[dict(pair=pair,stage='manage_new',outcome='skipped',atr_valid=1,
                            c1_json={'direction':'no_event'},capture_json={'validation':'valid'}) for pair in PERMITTED_PAIRS],
        **{name:[] for name in ('trade_sets','trade_legs','broker_attempts','issues','broker_transactions','fills','ledger_entries')})
    review = dict(classification='protected read-only evidence collection',status='collected',collection_errors=[],
        notebook_files_unchanged=True,notebook=dict(query_only=True, account_binding_sha256='a'*64,
        ordinary_account_report_available=False,tables=tables, qualification_account_report={
            'period':'qualification','opening_snapshot_id':'offline-q0','snapshot_id':'offline-final','boundary':'100','balance':'1000'}),
        broker_captures=dict(malformed_lines=[],rows=[dict(method='GET',http_status=200,source='practice_execution')]))
    return old,review


class ReviewChecks(unittest.TestCase):
    def test_completed_clear_actual_envelope_keeps_prior_history(self):
        old,review=fixtures();before=deepcopy(review)
        tool.validate_review(review,old)
        self.assertEqual(review,before)

    def test_fixture_unfinished_or_different_identity_is_rejected(self):
        old,review=fixtures()
        for change in ('fixture','unfinished','code','mode','bad_capture'):
            changed=deepcopy(review)
            if change=='fixture':changed['broker_captures']['rows'][0]['source']='fixture'
            if change=='unfinished':changed['notebook']['tables']['runs'][0]['status']='running'
            if change=='code':changed['notebook']['tables']['runs'][0]['code_hash']='e'*64
            if change=='mode':changed['notebook']['tables']['run_invocations'][0]['mode']='ordinary'
            if change=='bad_capture':changed['broker_captures']['malformed_lines']=[1]
            with self.subTest(change=change),self.assertRaises(ValueError):tool.validate_review(changed,old)

    def test_activation_any_attempt_or_issue_is_preserved_and_blocks_narrow_continuation(self):
        old,review=fixtures()
        for change in ('activation','broker_attempts','issues','trade_sets','fills'):
            changed=deepcopy(review)
            if change=='activation':changed['notebook']['tables']['notebook'][0]['activated_at']='2030-01-01T00:00:00Z'
            else:changed['notebook']['tables'][change]=[{'retained':'offline activity'}]
            before=deepcopy(changed)
            with self.subTest(change=change),self.assertRaises(ValueError):tool.validate_review(changed,old)
            self.assertEqual(changed,before)

    def test_new_candidate_is_disabled_rehosted_and_keeps_original_evidence_and_identity(self):
        old,_=fixtures();before=deepcopy(old)
        candidate=tool.renewed_plan(old,slot='2030-01-07T21:50:00+00:00',run_id='offline-new',
                                  host=('new-boot','new-kernel'),controls=b'new actual report')
        self.assertEqual(old,before)
        self.assertFalse(candidate['enabled'])
        self.assertEqual(candidate['manifest_sha256'],old['manifest_sha256'])
        self.assertEqual(candidate['account_binding_sha256'],old['account_binding_sha256'])
        self.assertEqual(candidate['boot_id'],'new-boot')
        self.assertEqual(candidate['evidence']['m09_controller_controls']['sha256'],sha256(b'new actual report').hexdigest())

    def test_missing_or_misaligned_reporting_boundary_cannot_arm(self):
        old,review=fixtures()
        for report in (None,dict(review['notebook']['qualification_account_report'],boundary='99'),
                       dict(review['notebook']['qualification_account_report'],snapshot_id='unconfirmed')):
            changed=deepcopy(review);changed['notebook']['qualification_account_report']=report
            with self.subTest(report=report),self.assertRaisesRegex(ValueError,'reconciled'):
                tool.validate_review(changed,old)

    def test_active_trigger_is_rejected_and_elapsed_old_trigger_cannot_queue_another_run(self):
        old,_=fixtures();old_timer='nnfx-m10-qualify-'+old['run_id']+'.timer'
        service=dict(ActiveState='inactive',Job='')
        elapsed=dict(ActiveState='active',SubState='elapsed',NextElapseUSecRealtime='',Job='')
        with patch.object(q,'_command',return_value={'TriggeredBy':old_timer}), \
             patch.object(tool.arm,'properties',side_effect=[service,elapsed]):tool.check_triggers(old)
        with patch.object(q,'_command',return_value={'TriggeredBy':old_timer}), \
             patch.object(tool.arm,'properties',side_effect=[service,dict(elapsed,SubState='waiting')]), \
             self.assertRaises(ValueError):tool.check_triggers(old)

    def test_nonadministrator_or_missing_explicit_arm_refuses_before_any_action(self):
        for uid,arm_args in ((1001,['--arm']),(0,[])):
            with patch('sys.argv',['continue','--previous-review','unused','--system-report','unused',
                                   '--dispatch-at','2030-01-07T21:50:00+00:00',*arm_args]), \
                 patch.object(tool.os,'geteuid',return_value=uid),patch('sys.prefix',str(tool.CODE/'.venv')), \
                 patch.object(tool,'continue_session') as action,patch('sys.stderr',new_callable=io.StringIO), \
                 self.assertRaises(SystemExit):tool.main()
            action.assert_not_called()


class CurrentHistoryChecks(M07Case):
    def setUp(self):
        super().setUp();self.initialize()
        registry=self.root/'config.toml'
        registry.write_text(registry.read_text().replace('controller-a','practice-a'))
        self.enterContext(patch.object(tool,'DATA',self.root))
        self.enterContext(patch.object(tool.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())))
        folder=self.root/'var/notebooks';folder.chmod(0o2750)
        for path in folder.iterdir():
            if path.name.endswith(('.sqlite3','-wal','-shm')):path.chmod(0o640)
        source=tool.ROOT/'var/verification/m10-review-20261120/collect_review.py'
        collector=tool.helper('offline_readonly_collector',source)
        current,_=collector.notebook_export(self.bound.experiment.notebook_path(self.root))
        self.review={'notebook':current,'source_sha256':sha256(source.read_bytes()).hexdigest()}
        self.world.calls.clear()

    def test_current_reader_preserves_q0_and_cursor_without_any_broker_request(self):
        before='\n'.join(self.db.iterdump())
        tool.audit_current(self.review)
        self.assertEqual('\n'.join(self.db.iterdump()),before)
        self.assertEqual(self.world.calls,[])

    def test_new_local_history_or_missing_sidecar_is_not_erased_or_recreated(self):
        changed=deepcopy(self.review);changed['notebook']['tables']['notebook'][0]['imported_through_transaction_id']='99'
        with self.assertRaisesRegex(ValueError,'differs'):tool.audit_current(changed)
        path=self.bound.experiment.notebook_path(self.root)
        sidecar=Path(str(path)+'-shm');sidecar.unlink()
        with self.assertRaises(FileNotFoundError):tool.audit_current(self.review)
        self.assertFalse(sidecar.exists())


class ContinuationWorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory()))
        self.data=self.root/'data';self.code=self.root/'code';self.units=self.root/'units';self.protected=self.root/'protected'
        for path in (self.data,self.code/'verification',self.units,self.protected/'evidence',self.root/'var/verification',self.root/'tests'):
            path.mkdir(parents=True,exist_ok=True)
        (self.data/'config.toml').write_text('offline public registry')
        (self.root/'config.toml').write_text('offline public registry')
        (self.root/'tests/check_m10_preparation.py').write_text('# offline worker; never executed')
        self.old,self.review=fixtures()
        self.old['config_sha256']=sha256((self.data/'config.toml').read_bytes()).hexdigest()
        self.review['notebook']['tables']['runs'][0]['config_hash']=self.old['config_sha256']
        self.original=(json.dumps(self.old)+'\n').encode();self.plan=self.protected/'practice-a.json';self.plan.write_bytes(self.original)
        self.review['protected_plan']={'sha256':sha256(self.original).hexdigest()}
        directory=self.data/'var/qualification/practice-a';directory.mkdir(parents=True)
        self.old_claim=directory/'2026-11-19.claim';self.old_claim.write_text('offline old claim')
        self.review['session_claim']={'sha256':sha256(self.old_claim.read_bytes()).hexdigest()}
        previous=self.root/'review.json';previous.write_text(json.dumps(self.review))
        report=self.root/'system.json';report.write_text(json.dumps(dict(host_context={'boot_id':'new-boot','kernel':'new-kernel'},
            cleanup_errors=[],existing_notebooks_preserved_mode=True,source_hashes={},
            results={'fixture_checks_passed':True,'actual_notebook_files_preserved':True})))
        self.args=SimpleNamespace(previous_review=previous,system_report=report,dispatch_at='2030-01-07T21:50:00+00:00')
        for name,value in [('ROOT',self.root),('CODE',self.code),('DATA',self.data)]:self.enterContext(patch.object(tool,name,value))
        self.enterContext(patch.object(tool.arm,'UNITS',self.units));self.enterContext(patch.object(tool.arm,'DATA',self.data))
        self.enterContext(patch.object(q,'PLAN_DIRECTORY',self.protected))
        self.enterContext(patch.object(q,'sealed_bytes',side_effect=lambda path:Path(path).read_bytes()))
        self.enterContext(patch.object(q,'code_identity',return_value=self.old['code_sha256']))
        self.enterContext(patch.object(q,'code_hashes',return_value={}))
        self.enterContext(patch.object(q,'host_identity',return_value=('new-boot','new-kernel')))
        self.enterContext(patch.object(q,'host_controls'))
        self.enterContext(patch.object(q,'_command',return_value={'TriggeredBy':''}))
        self.enterContext(patch.object(q,'_evidence',return_value={}))
        self.enterContext(patch.object(q,'validate_evidence'))
        self.inspect=self.enterContext(patch.object(q,'load_permit',return_value={}))
        self.audit=self.enterContext(patch.object(tool,'audit_current',return_value=self.review['notebook']))
        self.worker=self.enterContext(patch.object(tool.prep,'run_worker',return_value=dict(status='passed',source='practice_get',mutations_sent=0)))
        self.enterContext(patch.object(tool.pwd,'getpwnam',return_value=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())))
        self.enterContext(patch.object(tool.prep,'root_directory',side_effect=lambda path,group:path.mkdir()))
        self.enterContext(patch.object(tool.prep,'write_new',side_effect=lambda path,body,**kw:path.write_text(json.dumps(body))))
        self.enterContext(patch.object(tool.arm,'write_new',side_effect=lambda path,body,**kw:path.write_bytes(body)))
        def replace(path,expected,body):
            self.assertEqual(sha256(path.read_bytes()).hexdigest(),expected);path.write_bytes(body)
        self.enterContext(patch.object(tool.arm,'replace_plan',side_effect=replace))
        self.calls=[];self.started=False;self.uncertain=False
        def command(*args):
            self.calls.append(args)
            if args[:2]==('systemctl','start'):
                self.started=True
                if self.uncertain:raise subprocess.TimeoutExpired(args,30)
            return ''
        self.enterContext(patch.object(tool.arm,'command',side_effect=command))
        def properties(unit):
            if unit==tool.SERVICE:return dict(ActiveState='inactive',Job='')
            if self.started:return waiting_fixture(json.loads(self.plan.read_text()))
            return dict(ActiveState='inactive',Job='')
        self.enterContext(patch.object(tool.arm,'properties',side_effect=properties))

    def invoke(self):
        with patch('sys.stdout',new_callable=io.StringIO) as stdout:code=tool.continue_session(self.args)
        return code,json.loads(stdout.getvalue())

    def test_one_future_timer_keeps_old_claim_history_and_archives_expired_plan(self):
        code,result=self.invoke();self.assertEqual(code,0);self.assertEqual(result['status'],'armed')
        self.assertEqual(self.old_claim.read_text(),'offline old claim')
        self.assertEqual(Path(result['archived_previous_plan']).read_bytes(),self.original)
        starts=[args for args in self.calls if args[:2]==('systemctl','start')]
        self.assertEqual(starts,[('systemctl','start',result['timer'])])
        self.assertNotIn(tool.SERVICE,starts[0]);self.assertNotIn('nnfx-practice@practice-a.timer',str(self.calls))
        self.assertFalse((self.data/'var/notebooks').exists())

    def test_changed_account_blocks_before_plan_or_timer_mutations(self):
        self.worker.return_value=dict(status='pending',source='practice_get',mutations_sent=0)
        code,result=self.invoke();self.assertEqual(code,1)
        self.assertEqual(self.plan.read_bytes(),self.original);self.assertEqual(list(self.units.iterdir()),[])
        self.assertFalse(self.started)

    def test_current_notebook_change_blocks_before_account_request(self):
        self.audit.side_effect=ValueError('Changed current history')
        with self.assertRaises(ValueError):self.invoke()
        self.worker.assert_not_called();self.assertEqual(self.plan.read_bytes(),self.original)

    def test_failure_before_start_restores_expired_plan_and_removes_only_unused_timer(self):
        self.inspect.side_effect=[{},ValueError('Offline final guard failure')]
        code,result=self.invoke();self.assertEqual(code,1)
        self.assertTrue(result['expired_original_plan_restored'])
        self.assertEqual(self.plan.read_bytes(),self.original);self.assertEqual(list(self.units.iterdir()),[])
        self.assertFalse(self.started)

    def test_uncertain_start_preserves_new_plan_timer_and_history_without_stopping_service(self):
        self.uncertain=True
        code,result=self.invoke();self.assertEqual(code,1)
        self.assertIn('no automatic retry',result['recovery'])
        self.assertNotEqual(self.plan.read_bytes(),self.original)
        self.assertEqual(len(list(self.units.iterdir())),1)
        self.assertFalse(any('stop' in args for args in self.calls))
        self.assertEqual(self.old_claim.read_text(),'offline old claim')
