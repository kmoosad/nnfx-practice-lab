"""Offline native-wire schedule/activation cases. All broker/systemd calls are mocked."""

from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from unittest.mock import Mock, patch

from nnfx_practice import qualification as q, ordinary, qualification_review as review
from nnfx_practice.broker import PracticeBroker
from nnfx_practice.config import ConfigurationError
from nnfx_practice.control import maintenance
from nnfx_practice.host import SystemdService
from nnfx_practice.ledger import account_report
from nnfx_practice.lifecycle import activate_ordinary, require_invocation
from nnfx_practice.master import run_master
from strategies import t3_bandpass_v1 as selected
from .m07_support import M07Case
from . import test_m10_integration as integration


class AutomaticCase(integration.PermitCase):
    def setUp(self):
        super().setUp()
        self.plan.update(version=2, mode='qualification', schedule=q.SCHEDULE, run_id='campaign')
        self.documents['m09_controller_controls']['results']['dual_timer_maintenance'] = [
            dict(ordinary=a, qualification=b, failed=c, outcome=dict(
                uid=os.getuid(), outcome='intentional_failure' if c else 'completed'))
            for a, b, c in ((False, True, False), (False, True, True), (True, False, False), (False, False, True))]
        self.schedule = self.enterContext(patch.object(q, 'schedule_controls'))
        authority = dict(controller_id='controller-a', notebook_id='notebook-a', account_binding_sha256=self.digest,
                         schedule=q.SCHEDULE, statement='Offline automatic qualification authority',
                         ordinary_activation_authorized=False, ordinary_scheduled_trading_authorized=False)
        path = self.protected/'automatic-authority.json'
        raw = json.dumps(authority).encode()
        path.write_bytes(raw)
        self.plan['automatic_schedule_authority'] = dict(path=str(path), sha256=sha256(raw).hexdigest())
        self.save()

    def scheduled(self):
        permit = self.permit()
        self.run_id = permit.run_id
        self.native(permit)
        directory = self.claim(permit)
        with q.RetainedBroker(permit, directory / (permit.run_id + '.jsonl')) as broker:
            broker._now = self.clock.now
            with patch.object(selected, 'observe_c1', side_effect=self.world.observe), \
                    patch.object(selected, 'observe_exit', return_value=selected.EventObservation(
                        'no_event', selected.EXIT_RULE_ID, selected.EXIT_OUTPUTS)), \
                    patch.object(selected, 'sizing_atr', return_value=selected.AtrObservation(self.world.atr)):
                run_master(self.root, 'controller-a', broker, mode='qualification', evidence=permit.references,
                           run_id=permit.run_id, config_hash=self.plan['config_sha256'], code_hash=self.plan['code_sha256'],
                           elapsed=self.clock.monotonic)
        return permit

    def next_day(self):
        self.clock.advance(86400)


class AutomaticChecks(AutomaticCase):
    def test_automatic_authority_must_cover_same_account_and_exclude_ordinary(self):
        path = Path(self.plan['automatic_schedule_authority']['path'])
        original = json.loads(path.read_bytes())
        for field,value in (('account_binding_sha256','a'*64),('ordinary_activation_authorized',True),
                            ('schedule','daily'),('statement','')):
            raw = json.dumps(dict(original,**{field:value})).encode()
            path.write_bytes(raw)
            self.plan['automatic_schedule_authority']['sha256'] = sha256(raw).hexdigest()
            self.plan_path.write_text(json.dumps(self.plan))
            with self.subTest(field=field),self.assertRaises(ConfigurationError): self.permit()

    def test_idle_sessions_repeat_without_new_plans_and_preserve_q0_and_history(self):
        self.initialize()
        baseline = dict(self.db.execute('SELECT * FROM notebook').fetchone())
        first = self.scheduled()
        claim = self.root / 'var/qualification/controller-a' / (first.slot.date().isoformat() + '.claim')
        original = claim.read_bytes()
        self.next_day()
        second = self.scheduled()
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual(claim.read_bytes(), original)
        self.assertEqual(self.db.execute('SELECT count(*) FROM runs').fetchone()[0], 2)
        self.assertEqual(dict(self.db.execute('SELECT * FROM notebook').fetchone()), baseline)
        self.assertFalse(self.world.trades)

    def test_same_day_restart_replacement_and_legacy_claim_never_replay(self):
        self.initialize()
        first = self.scheduled()
        self.plan['run_id'] = 'new-campaign'
        self.save()
        with self.assertRaisesRegex(ConfigurationError, 'already attempted'):
            self.claim(self.permit())
        self.assertEqual(self.db.execute('SELECT count(*) FROM runs').fetchone()[0], 1)

    def test_late_weekend_and_before_start_are_rejected(self):
        base = datetime(2026, 11, 20, 21, 50, tzinfo=UTC)
        plan = dict(self.plan, dispatch_at=base.isoformat())
        for at in (base-timedelta(seconds=1), base+timedelta(minutes=1), base+timedelta(days=1)):
            with self.subTest(at=at), self.assertRaises(ConfigurationError):
                q.dispatch_slot(plan, 'run', at)
        self.assertEqual(q.dispatch_slot(plan, 'run', base+timedelta(days=3)), base+timedelta(days=3))

    def test_new_york_dst_slots_and_no_daily_rearm(self):
        plan = dict(self.plan, dispatch_at='2026-03-06T21:50:00+00:00')
        for at in ('2026-03-06T21:50:00+00:00', '2026-03-09T20:50:00+00:00',
                   '2026-10-30T20:50:00+00:00', '2026-11-02T21:50:00+00:00'):
            instant = datetime.fromisoformat(at)
            self.assertEqual(q.dispatch_slot(plan, 'run', instant), instant)
        with self.assertRaises(ConfigurationError):
            q.dispatch_slot(plan, 'run', datetime.fromisoformat('2026-03-09T21:50:00+00:00'))

    def test_same_kernel_reboot_keeps_schedule_but_changed_kernel_stops(self):
        with patch.object(q, 'host_identity', return_value=('new-boot', 'fixture-kernel')):
            self.permit()
        with patch.object(q, 'host_identity', return_value=('new-boot', 'new-kernel')), self.assertRaises(ConfigurationError):
            self.permit()

    def test_dual_timer_fixture_evidence_required(self):
        del self.documents['m09_controller_controls']['results']['dual_timer_maintenance']
        self.save()
        with self.assertRaisesRegex(ConfigurationError, 'dual-timer'):
            self.permit()

    def test_open_trades_receive_next_scheduled_tp_stop_management(self):
        self.initialize()
        self.world.signals = {'EUR-USD': 'long'}
        first = self.scheduled()
        leg = self.db.execute('SELECT * FROM trade_legs WHERE leg_no=1').fetchone()
        self.world.add_fill(self.world.trades[leg['broker_trade_id']], reason='TAKE_PROFIT_ORDER', pl='10')
        self.next_day()
        self.world.signals = {}
        second = self.scheduled()
        survivor = self.db.execute('SELECT * FROM trade_legs WHERE leg_no=2').fetchone()
        self.assertEqual(survivor['stop_to_entry_status'], 'confirmed')
        self.assertEqual(survivor['current_stop'], survivor['entry_price'])
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertEqual(self.db.execute('SELECT count(*) FROM trade_sets').fetchone()[0], 1)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])

    def test_prior_failed_stop_is_not_reissued_by_automatic_schedule(self):
        self.initialize()
        self.world.signals = {'EUR-USD': 'long'}
        self.scheduled()
        leg = self.db.execute('SELECT * FROM trade_legs WHERE leg_no=1').fetchone()
        self.world.add_fill(self.world.trades[leg['broker_trade_id']], reason='TAKE_PROFIT_ORDER', pl='10')
        self.next_day()
        self.world.signals = {}
        original = self.world.request
        # Native transport uncertainty is retained; later sessions reconcile without retry.
        self.world.on_call = lambda call: (_ for _ in ()).throw(TimeoutError()) if call.method == 'PUT' else None
        self.scheduled()
        self.world.on_call = None
        self.next_day()
        self.scheduled()
        attempts = self.db.execute("SELECT * FROM broker_attempts WHERE purpose='stop_to_entry'").fetchall()
        self.assertEqual(len(attempts), 1)
        self.assertTrue(self.db.execute("SELECT 1 FROM issues WHERE status='open'").fetchone())

    def test_readonly_collection_preserves_history_and_orphan_claim_without_observer(self):
        from . import collect_m10_automatic as collector
        from nnfx_practice.notebook import open_readonly
        self.initialize()
        self.scheduled()
        self.next_day()
        self.claim(self.permit())  # A crash before creating the master row.
        before='\n'.join(self.db.iterdump())
        output=self.root/'collected'
        with patch.object(collector,'DATA',self.root), \
                patch('nnfx_practice.notebook.open_readonly', wraps=open_readonly) as opened, \
                patch('nnfx_practice.config.load_binding',side_effect=AssertionError('private load')):
            result=collector.collect(output,'controller-a')
        self.assertNotEqual(opened.call_args.args[0], self.root)
        exported=json.loads((output/'progress.json').read_bytes())
        self.assertEqual(result['ordinary_activated'],False)
        self.assertEqual(exported['broker_requests'],0)
        self.assertEqual(sum(name.endswith('.claim') for name in exported['session_artifacts']),2)
        self.assertEqual(before,'\n'.join(self.db.iterdump()))
        self.assertTrue(exported['notebook_files_unchanged'])
        self.assertTrue(exported['notebook_data_files_unchanged'])
        self.assertEqual(len(exported['tables']['runs']), 1)
        self.assertFalse(list(output.glob('.notebook-*')))
        self.assertIn('long_sets',exported['facts']['missing'])

    def test_collection_distinguishes_shm_changes_and_retains_failed_data_export(self):
        from . import collect_m10_automatic as collector
        self.initialize()
        self.scheduled()
        source = self.bound.experiment.notebook_path(self.root)
        original = Path.read_bytes
        for index, suffix in enumerate(('-shm', '-wal', '')):
            with self.subTest(suffix=suffix):
                output = self.root / f'collected-{index}'
                changed = Path(str(source) + suffix)
                reads = 0
                def read_bytes(path):
                    nonlocal reads
                    raw = original(path)
                    if path == changed:
                        reads += 1
                        if reads > 1:
                            return raw + b'changed-by-another-process'
                    return raw
                with patch.object(collector, 'DATA', self.root), patch.object(Path, 'read_bytes', read_bytes):
                    if suffix == '-shm':
                        collector.collect(output, 'controller-a')
                    else:
                        with self.assertRaisesRegex(ValueError, str(output / 'progress.json')):
                            collector.collect(output, 'controller-a')
                exported = json.loads((output / 'progress.json').read_bytes())
                self.assertFalse(exported['notebook_files_unchanged'])
                self.assertEqual(exported['notebook_data_files_unchanged'], suffix == '-shm')
                self.assertEqual(exported['notebook_changed_files'], [str(changed)])
                self.assertTrue(exported['session_artifacts'])
                self.assertEqual((output / 'progress.json').stat().st_uid, collector.ROOT.stat().st_uid)
                self.assertFalse(list(output.glob('.notebook-*')))

    def test_collection_reads_retained_wal_after_last_writer_without_touching_source(self):
        from . import collect_m10_automatic as collector
        self.initialize()
        self.scheduled()
        source = self.bound.experiment.notebook_path(self.root)
        self.db.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        self.db.close()
        files = [Path(str(source) + suffix) for suffix in ('', '-wal', '-shm')]
        before = [path.read_bytes() for path in files]
        self.assertGreater(len(before[1]), 32)
        output = self.root / 'collected'
        with patch.object(collector, 'DATA', self.root):
            collector.collect(output, 'controller-a')
        exported = json.loads((output / 'progress.json').read_bytes())
        self.assertEqual(len(exported['tables']['runs']), 1)
        self.assertTrue(exported['notebook_files_unchanged'])
        self.assertEqual([path.read_bytes() for path in files], before)


class OrdinaryChecks(AutomaticCase):
    def write_artifact(self, name, data):
        raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        path = self.protected / name
        path.write_bytes(raw)
        return dict(path=str(path), sha256=sha256(raw).hexdigest())

    def completed_history(self):
        self.initialize()
        self.world.signals = {'EUR-USD': 'long', 'GBP-USD': 'short', 'EUR-GBP': 'long'}
        permits = [self.scheduled()]
        leg = self.db.execute("SELECT l.* FROM trade_legs l JOIN trade_sets s USING(set_id) WHERE s.pair='EUR-USD' AND l.leg_no=1").fetchone()
        self.world.add_fill(self.world.trades[leg['broker_trade_id']], reason='TAKE_PROFIT_ORDER', pl='10')
        self.world.add('DAILY_FINANCING', financing='0.00', positionFinancings=[])
        self.next_day()
        self.world.signals = {}
        self.world.open_signal = 'long'
        permits.append(self.scheduled())
        self.next_day()
        self.world.open_signal = 'short'
        permits.append(self.scheduled())
        self.assertFalse(self.world.trades)
        found = review.facts(self.db, self.plan)
        self.assertEqual(found['missing'], [])
        packet = {key: self.plan[key] for key in ('account_binding_sha256', 'manifest_sha256', 'config_sha256',
                                                 'code_sha256', 'kernel', 'controller_id', 'notebook_id')}
        offline = '\n'.join(f'test_fixture_{i} (tests.offline_fixture.Case) ... ok' for i in range(427))
        packet.update(record_sha256=review.record_hash(self.db), final_run_id=permits[-1].run_id,
                      offline_suite=self.write_artifact('offline.txt', (offline+'\nRan 427 tests in 1.0s\n\nOK\n').encode()))
        packet['owner_authorization'] = dict(ordinary_activation=True, ordinary_scheduling=True,
            statement='OFFLINE TEST AUTHORITY ONLY', reviewer='fixture', at=self.clock.now().isoformat(),
            reviewed_record_sha256=packet['record_sha256'])
        facts_ref = self.write_artifact('observations.json', found)
        packet['acceptance'] = {f'A{i:02}': dict(conclusion='accepted', explanation='Offline evidence-review fixture',
            offline_tests=[f'test_fixture_{i} (tests.offline_fixture.Case)'],
            observations=[dict(artifact=facts_ref, pointer=['sets', 0, 'trade_ids'], observed=found['sets'][0]['trade_ids'])]) for i in range(1, 17)}
        packet['startup'] = self.write_artifact('startup.json', {'rows': [dict(phase='boot_marker', kernel='fixture-kernel',
            invocation_id='fixture', logins=dict(known=True, user_sessions=0))]})
        start = permits[-1].slot
        packet['scheduled_window'] = self.write_artifact('window.json', {'rows': [dict(
            at=(start + timedelta(seconds=s)).isoformat(), kernel='fixture-kernel', boot_id='fixture-boot',
            invocation_id='fixture', suspend_offset=0, clock_uncertainty=0.001, logins=dict(known=True, user_sessions=0))
            for s in range(-600, 901, 30)]})
        report = review.report_values(self.db)
        html = '\n'.join([permits[-1].run_id, report['balance'], *[t for s in found['sets'] for t in s['trade_ids']]])
        packet['dashboard_comparison'] = self.write_artifact('dashboard.json', dict(account_report=report,
            run_id=permits[-1].run_id, method='GET', http_status=200, owner_lan_confirmation='Offline fixture',
            html=self.write_artifact('dashboard.html', html.encode())))
        packet['runs'] = {}
        for permit in permits:
            directory = self.root / 'var/qualification/controller-a'
            packet['runs'][permit.run_id] = dict(
                claim=self.write_artifact(permit.run_id+'.claim', (directory/(permit.slot.date().isoformat()+'.claim')).read_bytes()),
                captures=self.write_artifact(permit.run_id+'.jsonl', (directory/(permit.run_id+'.jsonl')).read_bytes()))
        self.packet = packet
        self.ordinary_plan = dict(self.plan, mode='ordinary', run_id='ordinary',
            qualification_plan=self.write_artifact('qualified-plan.json', self.plan),
            activation_review=self.write_artifact('final-review.json', packet))
        self.plan_path.write_text(json.dumps(self.ordinary_plan))
        return permits

    def ordinary_permit(self, operation='activate'):
        with patch.object(q, 'host_service'):
            return ordinary.load_permit(self.root, 'controller-a', operation, now=self.clock.now())

    def activation_broker(self):
        permit = self.ordinary_permit()
        self.native(permit)
        broker = PracticeBroker(self.bound, ordinary=permit, now=self.clock.now)
        return permit, broker

    def test_completed_native_evidence_activates_atomically_and_repeats_without_replacing_a0(self):
        self.completed_history()
        permit, broker = self.activation_broker()
        before = self.db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0]
        first = activate_ordinary(self.root, 'controller-a', broker, service=self.service, evidence=permit.references)
        second = activate_ordinary(self.root, 'controller-a', broker, service=self.service, evidence=permit.references)
        self.assertEqual(first, second)
        self.assertEqual(self.db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0], before)
        self.assertNotEqual(first, before)
        self.assertEqual(asdict(account_report(self.db, 'ordinary'))['opening_snapshot_id'], first)
        with self.assertRaises(ConfigurationError):
            broker.change_trade('42')

    def test_missing_fills_cannot_activate_with_reviewed_flags(self):
        self.initialize()
        self.scheduled()
        result = review.facts(self.db, self.plan)
        self.assertIn('long_sets', result['missing'])
        self.assertIn('scheduled_stop_to_entry', result['missing'])
        with self.assertRaises(ConfigurationError):
            ordinary.load_permit(self.root, 'controller-a', 'activate', now=self.clock.now())
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])

    def test_changed_records_or_simulated_captures_prevent_a0(self):
        self.completed_history()
        self.db.execute("UPDATE runs SET duration_seconds=9999 WHERE run_id=?", (self.packet['final_run_id'],))
        permit, broker = self.activation_broker()
        with self.assertRaisesRegex(ConfigurationError, 'records changed'):
            activate_ordinary(self.root, 'controller-a', broker, service=self.service, evidence=permit.references)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])

    def test_pass_flags_and_missing_acceptance_or_owner_authority_are_rejected(self):
        self.completed_history()
        original = deepcopy(self.packet)
        variants = [dict(original, acceptance={}), dict(original, owner_authorization={})]
        flagged = deepcopy(original)
        ref = self.write_artifact('flag.json', {'status': 'passed'})
        flagged['acceptance']['A01']['observations'] = [dict(artifact=ref, pointer=['status'], observed='passed')]
        variants.append(flagged)
        for packet in variants:
            with self.subTest(packet=packet.keys()):
                self.ordinary_plan['activation_review'] = self.write_artifact('final-review.json', packet)
                self.plan_path.write_text(json.dumps(self.ordinary_plan))
                with self.assertRaises(ConfigurationError):
                    self.ordinary_permit()

    def test_native_ordinary_run_requires_committed_a0_and_shared_day_claim(self):
        self.completed_history()
        self.next_day()
        permit = self.ordinary_permit('run')
        self.native(permit)
        broker = PracticeBroker(self.bound, ordinary=permit, now=self.clock.now)
        with self.assertRaisesRegex(ConfigurationError, 'committed activation'):
            require_invocation(self.db, broker, 'ordinary', None)
        activation, activation_broker = self.activation_broker()
        activate_ordinary(self.root, 'controller-a', activation_broker, service=self.service, evidence=activation.references)
        require_invocation(self.db, broker, 'ordinary', None)
        self.claim(permit)
        self.world.signals = {'EUR-USD': 'long'}
        self.world.open_signal = 'no_event'
        self.run_id = permit.run_id
        with patch.object(selected, 'observe_c1', side_effect=self.world.observe), \
                patch.object(selected, 'sizing_atr', return_value=selected.AtrObservation(self.world.atr)):
            run_master(self.root, 'controller-a', broker, mode='ordinary', run_id=permit.run_id,
                       code_hash=permit.plan['code_sha256'], config_hash=permit.plan['config_sha256'])
        self.assertEqual(self.db.execute('SELECT mode FROM run_invocations WHERE run_id=?', (permit.run_id,)).fetchone()[0], 'ordinary')
        self.assertTrue(self.world.trades)
        with self.assertRaisesRegex(ConfigurationError, 'already attempted'):
            self.claim(self.ordinary_permit('run'))

    def revise_packet(self):
        self.ordinary_plan['activation_review'] = self.write_artifact('final-review.json', self.packet)
        self.plan_path.write_text(json.dumps(self.ordinary_plan))

    def test_fixture_capture_source_and_missing_actual_response_block_activation(self):
        self.completed_history()
        run_id = next(iter(self.packet['runs']))
        original = review.artifact(self.packet['runs'][run_id]['captures'])
        rows = [json.loads(line) for line in original.splitlines()]
        for variant in ([dict(r, source='fixture') for r in rows], [r for r in rows if r['method']=='GET']):
            self.packet['runs'][run_id]['captures'] = self.write_artifact('changed.jsonl',
                ('\n'.join(json.dumps(r) for r in variant)+'\n').encode())
            self.revise_packet()
            permit, broker = self.activation_broker()
            with self.assertRaises(ConfigurationError):
                activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
            self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])

    def test_old_kernel_window_and_unknown_unattended_context_block_final_only(self):
        self.completed_history()
        window = json.loads(review.artifact(self.packet['scheduled_window']))
        old = deepcopy(window)
        for row in old['rows']:
            row['kernel'] = 'previous-kernel'
        unknown = deepcopy(window)
        for row in unknown['rows']:
            row['logins'] = dict(known=True,user_sessions=4)
        for variant in (old, unknown, dict(window, rows=window['rows'][::4])):
            self.packet['scheduled_window'] = self.write_artifact('bad-window.json',variant)
            self.revise_packet()
            permit,broker=self.activation_broker()
            with self.assertRaises(ConfigurationError):
                activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)

    def test_fresh_a0_reconciliation_failure_does_not_commit_activation(self):
        from nnfx_practice.broker import BrokerError
        self.completed_history()
        permit,broker=self.activation_broker()
        original=self.db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0]
        self.world.balance='999999'
        with self.assertRaises(BrokerError):
            activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
        row=self.db.execute('SELECT * FROM notebook').fetchone()
        self.assertIsNone(row['activated_at'])
        self.assertEqual(row['qualification_snapshot_id'],original)

    def test_interrupted_a0_commit_rolls_back_activation_snapshot(self):
        import sqlite3
        self.completed_history()
        permit,broker=self.activation_broker()
        self.db.execute("CREATE TRIGGER fixture_activation_failure BEFORE UPDATE OF activated_at ON notebook BEGIN SELECT RAISE(ABORT,'fixture interruption'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        self.assertIsNone(self.db.execute("SELECT 1 FROM account_snapshots WHERE purpose='activation'").fetchone())

    def test_qualification_claim_blocks_ordinary_dispatch_on_activation_day(self):
        self.completed_history()
        permit,broker=self.activation_broker()
        activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
        with self.assertRaisesRegex(ConfigurationError,'already attempted'):
            self.claim(self.ordinary_permit('run'))

    def test_new_review_cannot_silently_replace_existing_a0_authority(self):
        self.completed_history()
        permit,broker=self.activation_broker()
        first=activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
        self.packet['owner_authorization']['statement']='A different offline review'
        self.revise_packet()
        new,broker=self.activation_broker()
        with self.assertRaises(ConfigurationError):
            activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=new.references)
        self.assertEqual(self.db.execute('SELECT activation_snapshot_id FROM notebook').fetchone()[0],first)

    def test_revocation_during_fresh_account_read_prevents_a0_commit(self):
        self.completed_history()
        permit,broker=self.activation_broker()
        def revoke(call):
            if call.method=='GET':
                self.plan_path.write_text(json.dumps(dict(self.ordinary_plan,enabled=False)))
        self.world.on_call=revoke
        with self.assertRaisesRegex(ConfigurationError,'revoked'):
            activate_ordinary(self.root,'controller-a',broker,service=self.service,evidence=permit.references)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        self.assertIsNone(self.db.execute("SELECT 1 FROM account_snapshots WHERE purpose='activation'").fetchone())

    def test_scripted_activation_cannot_enable_native_ordinary_dispatch(self):
        self.completed_history()
        permit=self.ordinary_permit()
        # The offline lifecycle remains useful, but its fixture source is not native evidence.
        activate_ordinary(self.root,'controller-a',self.broker,service=self.service,evidence=permit.references)
        self.next_day()
        native=self.ordinary_permit('run')
        self.native(native)
        broker=PracticeBroker(self.bound,ordinary=native,now=self.clock.now)
        with self.assertRaisesRegex(ConfigurationError,'reviewed, committed activation'):
            require_invocation(self.db,broker,'ordinary',None)


class DualMaintenanceChecks(M07Case):
    def test_two_timer_states_restore_independently_after_failure(self):
        states = {'nnfx-practice@controller-a.timer': 'inactive', 'nnfx-practice-qualification@controller-a.timer': 'active'}
        masked = False
        def runner(args, **kwargs):
            nonlocal masked
            operation = next(a for a in args if a in ('show','start','stop','mask','unmask'))
            unit = args[args.index(operation)+1] if operation == 'show' else args[-1]
            output = ''
            if operation == 'show':
                output = f"LoadState={'masked' if masked and unit.endswith('.service') else 'loaded'}\nActiveState={states.get(unit, 'inactive')}\nJob=\n"
            elif operation in ('start','stop'):
                states[unit] = 'active' if operation == 'start' else 'inactive'
            else:
                masked = operation == 'mask'
            return subprocess.CompletedProcess(args, 0, output, '')
        service = SystemdService('controller-a', runner=runner, extra_timers=('nnfx-practice-qualification@controller-a.timer',))
        with self.assertRaises(RuntimeError):
            with maintenance(self.root, self.bound, service):
                self.assertTrue(masked)
                self.assertEqual(set(states.values()), {'inactive'})
                raise RuntimeError('fixture')
        self.assertFalse(masked)
        self.assertEqual(list(states.values()), ['inactive','active'])
