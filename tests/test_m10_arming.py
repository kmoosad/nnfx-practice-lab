"""Offline initial-session arming checks. No systemd or broker is contacted."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from nnfx_practice.notebook import start_run
from nnfx_practice.qualification import account_identity
from . import arm_m10_qualification as arm
from .m07_support import EVIDENCE, M07Case, record_legacy_activation


SLOT = datetime(2030, 1, 7, 21, 50, tzinfo=UTC)
NOW = SLOT - timedelta(hours=1)


def plan_fixture():
    return dict(enabled=False, controller_id='practice-a', run_id='m10-offline', dispatch_at=SLOT.isoformat(),
                account_binding_sha256='a' * 64, manifest_sha256='b' * 64,
                evidence={'initial_account_resolution': {'path': 'placeholder'}})


def initialization_fixture(plan, digest):
    return dict(status='passed', source='practice_get', actual_notebook_initialized=True,
                matches_reviewed_clearance=True, disabled_plan_restored=True,
                ordinary_controls_verified_inactive=True, ordinary_activation_performed=False,
                ordinary_trading_enabled=False, qualification_enabled=False, timer_created=False,
                mutations_sent=0, q0_snapshot_id='offline-q0', transaction_boundary='100',
                imported_through_transaction_id='100', account_binding_sha256=plan['account_binding_sha256'],
                manifest_sha256=plan['manifest_sha256'], disabled_plan_sha256=digest)


def waiting_fixture(plan):
    _, body = arm.timer_definition(plan)
    calendar = next(line.removeprefix('OnCalendar=') for line in body.splitlines() if line.startswith('OnCalendar='))
    return dict(LoadState='loaded', ActiveState='active', SubState='waiting', Unit=arm.SERVICE,
                Triggers=arm.SERVICE, Persistent='no', AccuracyUSec='1s', RandomizedDelayUSec='0',
                UnitFileState='static', DropInPaths='', Job='', TimersCalendar='{ OnCalendar=' + calendar + ' }',
                NextElapseUSecRealtime='Mon 2030-01-07 21:50:00 UTC')


class TimerChecks(unittest.TestCase):
    def test_dated_timer_follows_ny_dst_and_has_no_boot_or_recurring_activation(self):
        for utc, date in (('2030-01-07T21:50:00+00:00', '2030-01-07'),
                          ('2030-07-08T20:50:00+00:00', '2030-07-08')):
            plan = dict(plan_fixture(), dispatch_at=utc)
            arm.future_slot(plan, now=datetime(2029, 1, 1, tzinfo=UTC))
            name, body = arm.timer_definition(plan)
            self.assertTrue(name.startswith('nnfx-m10-qualify-'))
            self.assertIn('OnCalendar=' + date + ' 16:50:00 America/New_York', body)
            self.assertIn('Unit=' + arm.SERVICE, body)
            self.assertIn('Persistent=false', body)
            self.assertIn('AccuracySec=1s', body)
            self.assertNotIn('[Install]', body)
            self.assertNotIn('Mon..Fri', body)
            self.assertNotIn('ExecStart=', body)

    def test_past_weekend_or_wrong_minute_cannot_arm_catch_up(self):
        for instant in (NOW.isoformat(), '2030-01-05T21:50:00+00:00',
                        '2030-01-07T21:49:00+00:00', '2030-01-07T21:50:00'):
            with self.subTest(instant=instant), self.assertRaises(ValueError):
                arm.future_slot(dict(plan_fixture(), dispatch_at=instant), now=NOW)

    def test_effective_timer_must_wait_for_exact_instant_and_service_without_recurrence(self):
        plan = plan_fixture()
        state = waiting_fixture(plan)
        arm.validate_waiting_timer(state, plan, now=NOW)
        for key, value in (('Persistent', 'yes'), ('AccuracyUSec', '1min'), ('UnitFileState', 'enabled'),
                           ('Unit', 'other.service'), ('SubState', 'elapsed'), ('DropInPaths', '/override'),
                           ('NextElapseUSecRealtime', 'Mon 2030-01-07 21:51:00 UTC'), ('Job', '12')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                arm.validate_waiting_timer(dict(state, **{key:value}), plan, now=NOW)

    def test_fixture_pending_activated_or_wrong_q0_metadata_cannot_authorize_arming(self):
        plan = plan_fixture(); prepared = {'plan_sha256':'digest'}
        report = initialization_fixture(plan, 'digest')
        arm.validate_initialization(report, plan, prepared)
        for key, value in (('source', 'fixture'), ('status', 'pending'), ('disabled_plan_restored', False),
                           ('actual_notebook_initialized', False), ('ordinary_activation_performed', True),
                           ('timer_created', True), ('account_binding_sha256', 'other'),
                           ('imported_through_transaction_id', '99')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                arm.validate_initialization(dict(report, **{key:value}), plan, prepared)

    def test_nonadministrator_stops_before_any_read_or_mutation(self):
        with patch('sys.argv', ['arm', '--initialization', '/not-read']), \
                patch.object(arm.os, 'geteuid', return_value=1001), patch.object(arm, 'arm') as action, \
                patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            arm.main()
        self.assertEqual(error.exception.code, 2)
        action.assert_not_called()


class NotebookAuditChecks(M07Case):
    def setUp(self):
        super().setUp()
        self.initialize()
        self.enterContext(patch.object(arm, 'DATA', self.root))
        self.enterContext(patch.object(arm.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())))
        folder = self.root / 'var/notebooks'
        folder.chmod(0o2750)
        for item in folder.iterdir():
            if item.name.endswith(('.sqlite3', '-wal', '-shm')):
                item.chmod(0o640)
        row = self.db.execute('SELECT * FROM notebook').fetchone()
        self.plan = dict(plan_fixture(), controller_id='controller-a', account_binding_sha256=account_identity(self.bound),
                         manifest_sha256=self.bound.manifest.hash)
        self.report = dict(q0_snapshot_id=row['qualification_snapshot_id'],
                           transaction_boundary=row['qualification_transaction_id'])
        self.resolution = dict(transaction_boundary='100', evidence={'body':{'account':{'balance':self.world.balance}}})
        self.world.calls.clear()

    def test_current_q0_audit_reads_without_changing_notebook_or_contacting_broker(self):
        before = '\n'.join(self.db.iterdump())
        result = arm.audit_notebook(self.plan, self.report, self.resolution)
        self.assertTrue(result['cursor_matches_q0'])
        self.assertTrue(result['query_only'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        self.assertEqual(self.world.calls, [])

    def test_current_activation_supersedes_old_unactivated_report(self):
        record_legacy_activation(self)
        before = '\n'.join(self.db.iterdump())
        with self.assertRaises(ValueError):
            arm.audit_notebook(self.plan, self.report, self.resolution)
        self.assertEqual('\n'.join(self.db.iterdump()), before)

    def test_existing_qualification_history_is_preserved_instead_of_rearmed_as_initial(self):
        start_run(self.db, run_id='previous', started_at=self.clock.now(), config_hash='c' * 64, code_hash='d' * 64)
        before = '\n'.join(self.db.iterdump())
        with self.assertRaisesRegex(ValueError, 'Existing qualification activity'):
            arm.audit_notebook(self.plan, self.report, self.resolution)
        self.assertEqual('\n'.join(self.db.iterdump()), before)

    def test_new_run_id_cannot_bypass_an_existing_session_claim(self):
        folder = self.root / 'var/qualification/practice-a'
        folder.mkdir(parents=True)
        target = arm.claim_path(self.plan)
        target.write_text('preserve prior attempt')
        with self.assertRaisesRegex(ValueError, 'already attempted'):
            arm.claim_path(dict(self.plan, run_id='new-offline-id'))
        self.assertEqual(target.read_text(), 'preserve prior attempt')

    def test_actual_notebook_permissions_are_checked_before_sql_audit(self):
        path = self.root / 'var/notebooks/notebook-a.sqlite3'
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'ownership or permissions'):
            arm.audit_notebook(self.plan, self.report, self.resolution)
        self.assertEqual(self.world.calls, [])


class ArmingWorkflowChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.units = self.root / 'units'; self.units.mkdir()
        self.protected = self.root / 'protected'; self.protected.mkdir()
        self.enterContext(patch.object(arm, 'ROOT', self.root))
        self.enterContext(patch.object(arm, 'CODE', self.root / 'code'))
        self.enterContext(patch.object(arm, 'DATA', self.root))
        self.enterContext(patch.object(arm, 'UNITS', self.units))
        self.enterContext(patch.object(arm.os, 'fchown'))
        from nnfx_practice import qualification as q
        self.enterContext(patch.object(q, 'PLAN_DIRECTORY', self.protected))
        self.enterContext(patch.object(q, 'sealed_bytes', side_effect=lambda p:Path(p).read_bytes()))
        self.enterContext(patch.object(q, 'code_hashes', return_value={}))
        self.inspect = self.enterContext(patch.object(q, 'load_permit', return_value={}))
        self.enterContext(patch.object(q, 'host_controls'))
        self.enterContext(patch.object(q, '_command', return_value={'TriggeredBy':arm.ORDINARY_TIMER}))
        self.enterContext(patch.object(arm, 'audit_notebook', return_value={'q0_snapshot_id':'offline-q0'}))
        self.plan = plan_fixture()
        resolution = self.protected / 'resolution.json'; resolution.write_text('{}')
        self.plan['evidence']['initial_account_resolution']['path'] = str(resolution)
        self.path = self.protected / 'practice-a.json'; self.path.write_text(json.dumps(self.plan))
        self.original = self.path.read_bytes(); digest = sha256(self.original).hexdigest()
        prepared = self.root / 'prepared.json'; prepared.write_text(json.dumps({'plan_sha256':digest}))
        (self.root / 'tests').mkdir()
        source = self.root / 'tests/initialize_m10_qualification.py'; source.write_text('# offline source')
        (self.root / 'config.toml').write_text('# offline ownership metadata')
        (self.root / 'var/verification').mkdir(parents=True)
        report = initialization_fixture(self.plan, digest)
        report.update(prepared=str(prepared), source_sha256=sha256(source.read_bytes()).hexdigest())
        self.report = self.root / 'initialized.json'; self.report.write_text(json.dumps(report))
        self.started = False
        self.calls = []

        def command(*args):
            self.calls.append(args)
            if args[:2] == ('systemctl','start'):
                self.started = True
            return ''
        self.command = self.enterContext(patch.object(arm, 'command', side_effect=command))

        def properties(unit):
            if unit == arm.SERVICE or unit == arm.ORDINARY_TIMER:
                return dict(ActiveState='inactive', Job='')
            state = waiting_fixture(self.plan)
            if not self.started:
                state.update(ActiveState='inactive',SubState='dead')
            return state
        self.enterContext(patch.object(arm, 'properties', side_effect=properties))
        self.output = self.enterContext(patch('sys.stdout', new_callable=io.StringIO))

    def test_only_new_dated_timer_is_started_and_ordinary_is_never_enabled(self):
        self.assertEqual(arm.arm(self.report), 0)
        name, body = arm.timer_definition(self.plan)
        self.assertEqual((self.units / name).read_text(), body)
        self.assertTrue(json.loads(self.path.read_text())['enabled'])
        starts = [call for call in self.calls if call[:2] == ('systemctl','start')]
        self.assertEqual(starts, [('systemctl','start',name)])
        self.assertFalse(any('enable' in call or 'stop' in call for call in self.calls))
        result = json.loads(self.output.getvalue())
        self.assertEqual(result['status'], 'armed')
        self.assertEqual(result['broker_requests_sent_by_armer'], 0)
        self.assertFalse(result['ordinary_trading_enabled'])
        self.assertFalse(result['practice_execution_qualified'])

    def test_failure_after_plan_enable_restores_disabled_state_before_timer_start(self):
        self.inspect.side_effect = [{}, ValueError('offline gate failed after flag update')]
        self.assertEqual(arm.arm(self.report), 1)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(list(self.units.iterdir()), [])
        self.assertFalse(self.started)
        self.assertTrue(json.loads(self.output.getvalue())['pre_dispatch_cleanup_completed'])

    def test_uncertain_timer_start_preserves_state_and_never_stops_a_possible_run(self):
        original = self.command.side_effect
        def uncertain(*args):
            if args[:2] == ('systemctl','start'):
                self.calls.append(args)
                raise ValueError('offline start outcome unknown')
            return original(*args)
        self.command.side_effect = uncertain
        self.assertEqual(arm.arm(self.report), 1)
        result = json.loads(self.output.getvalue())
        self.assertTrue(result['timer_start_attempted'])
        self.assertEqual(result['status'], 'pending')
        self.assertTrue(json.loads(self.path.read_text())['enabled'])
        self.assertTrue(list(self.units.iterdir()))
        self.assertFalse(any('stop' in call or 'enable' in call for call in self.calls))

    def test_existing_arming_state_is_not_overwritten_or_retried(self):
        name, _ = arm.timer_definition(self.plan)
        existing = self.units / name; existing.write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'Existing qualification timer'):
            arm.arm(self.report)
        self.assertEqual(existing.read_text(), 'preserve')
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(self.calls, [])
