"""Integrated M07 acceptance variations. All broker activity is scripted offline."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
import json
import sqlite3
from unittest.mock import patch

from nnfx_practice.broker import BrokerError, PracticeBroker
from nnfx_practice.config import ConfigurationError, PERMITTED_PAIRS
from nnfx_practice.control import MaintenanceDeferred, controller_exclusion, maintenance
from nnfx_practice.disposition import DispositionRequired, record_disposition
from nnfx_practice.ledger import account_report
from nnfx_practice.lifecycle import activate_ordinary, initialize_qualification
from nnfx_practice.master import run_master
from nnfx_practice.notebook import open_notebook, pair_is_available, pair_progress, transaction
from nnfx_practice.reconciliation import _issue, reconcile_snapshot
from strategies import t3_bandpass_v1 as selected
from .m07_support import EVIDENCE, M07Case, Service, World
from .support import Interrupted, ScriptedTransport, interrupt_commit
from . import test_m02 as m02
from .test_m02 import account, event, order_fill, reply


class MasterChecks(M07Case):
    register = m02.ReconciliationChecks.register

    def setUp(self):
        super().setUp()
        self.initialize()
        self.world.calls.clear()

    def run_master(self, *, real=False, mode='qualification', evidence=EVIDENCE):
        with ExitStack() as stack:
            if not real:
                stack.enter_context(patch.object(selected, 'observe_c1', side_effect=self.world.observe))
                stack.enter_context(patch.object(selected, 'observe_exit', side_effect=lambda _: selected.EventObservation(
                    self.world.exit_signal, selected.EXIT_RULE_ID, selected.EXIT_OUTPUTS)))
                stack.enter_context(patch.object(selected, 'sizing_atr', side_effect=lambda _: selected.AtrObservation(self.world.atr)))
            return run_master(self.root, 'controller-a', self.broker, mode=mode, evidence=evidence,
                              run_id=self.run_id, config_hash='c' * 64, code_hash='d' * 64, elapsed=self.clock.monotonic)

    def row(self, table='runs'):
        return self.db.execute(f'SELECT * FROM {table} WHERE run_id = ?', (self.run_id,)).fetchone()

    def new_decision(self, pair='EUR-USD'):
        return self.db.execute("SELECT * FROM pair_decisions WHERE run_id=? AND stage='manage_new' AND pair=?", (self.run_id, pair)).fetchone()

    def seed_set(self):
        self.register()
        from .test_m02 import open_trade
        self.world.trades = {str(i): open_trade(i, leg=leg, stop_id=str(i + 10)) for leg, i in enumerate((40, 41), 1)}

    def test_a02_a03_a04_a06_real_strategy_first_run_order_and_commits(self):
        self.run_master(real=True)
        self.assertEqual(self.row()['status'], 'completed')
        calls = self.world.calls
        self.assertEqual(calls[0].path, '/v3/accounts/fixture-account-a')
        self.assertTrue(calls[1].path.endswith('/summary'))
        pairs = [c.path.split('/instruments/')[1].split('/')[0].replace('_', '-') for c in calls if '/candles?' in c.path]
        self.assertEqual(pairs, list(PERMITTED_PAIRS))
        self.assertEqual(len(calls), 31)
        for trace in self.world.traces:
            path = trace['call']['path']
            if '/candles?' in path:
                pair = path.split('/instruments/')[1].split('/')[0].replace('_', '-')
                done = [d for d in trace['committed_decisions'] if d['stage'] == 'manage_new' and d['outcome'] is not None]
                self.assertEqual(len(done), PERMITTED_PAIRS.index(pair))
        self.assertEqual(pair_progress(self.db, self.run_id, 'manage_new')['finished'], 28)
        self.assertEqual(self.row()['lookback_candles'], 386)
        self.assertEqual(self.row('run_invocations')['mode'], 'qualification')

    def test_a04_a05_a06_multiple_sets_use_fixed_balance_and_fresh_margin(self):
        self.world.signals = {'EUR-USD': 'long', 'GBP-USD': 'short'}
        self.world.summary_balances = ['1000', '8000', '9000', '11000', '12000']
        self.run_master()
        self.assertEqual(self.row()['status'], 'completed')
        self.assertEqual(self.row()['sizing_balance'], '1000')
        for pair in self.world.signals:
            plan = json.loads(self.new_decision(pair)['sizing_json'])['sizing']
            self.assertEqual(Decimal(plan['budget_per_leg']), Decimal('10'))
            self.assertLessEqual(Decimal(plan['risk_per_leg']), Decimal('10'))
        self.assertEqual(len([c for c in self.world.calls if c.path.endswith('/summary')]), 5)
        self.assertEqual(self.db.execute('SELECT count(*) FROM trade_sets WHERE establishment_status="complete"').fetchone()[0], 2)
        purposes = [r[0] for r in self.db.execute('SELECT purpose FROM account_snapshots')]
        self.assertEqual(purposes.count('sizing_balance'), 1)
        self.assertEqual(purposes[-1], 'reporting')
        self.assertEqual(account_report(self.db, 'qualification').balance, Decimal('1000'))

    def test_a06_blocked_pair_silence_and_committed_skip(self):
        with transaction(self.db):
            _issue(self.db, 'fixture_block', 'gbp', self.broker.now(), {}, pair='GBP-USD')
        self.seed_set()
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertEqual(self.new_decision('GBP-USD')['outcome'], 'skipped')
        self.assertEqual(len([c for c in self.world.calls if '/EUR_USD/candles' in c.path]), 1)  # Stage 1 only.
        self.assertFalse(any('GBP_USD' in c.path for c in self.world.calls))
        self.assertEqual(self.row()['status'], 'completed_with_errors')

    def test_a07_a08_fresh_entry_independent_after_c1_close(self):
        self.seed_set()
        self.world.open_signal = 'short'
        self.world.signals['EUR-USD'] = 'long'
        self.run_master()
        self.assertEqual(self.row()['status'], 'completed')
        self.assertEqual(self.new_decision()['outcome'], 'completed')
        self.assertEqual(json.loads(self.new_decision()['c1_json'])['direction'], 'long')
        self.assertEqual([r[0] for r in self.db.execute('SELECT exit_reason FROM trade_legs WHERE set_id="set-a"')],
                         ['MARKET_ORDER_TRADE_CLOSE'] * 2)
        self.assertEqual(len([c for c in self.world.calls if '/EUR_USD/candles' in c.path]), 2)

    def test_a08_opposite_entry_after_c1_close(self):
        self.seed_set()
        self.world.open_signal = 'short'
        self.world.signals['EUR-USD'] = 'short'
        self.run_master()
        self.assertEqual(json.loads(self.new_decision()['c1_json'])['direction'], 'short')
        self.assertEqual(self.new_decision()['outcome'], 'completed')

    def test_a08_close_without_fresh_event_does_not_enter(self):
        self.seed_set()
        self.world.open_signal = 'short'
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))

    def test_a09_exit_close_uses_only_entry_signal(self):
        self.seed_set()
        self.world.exit_signal = 'short'
        self.world.signals['EUR-USD'] = 'short'
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'completed')
        self.assertEqual(json.loads(self.new_decision()['c1_json'])['direction'], 'short')

    def test_a09_a11_mixed_price_closures_and_same_direction_entry(self):
        self.seed_set()
        self.world.add_fill(self.world.trades['40'], reason='TAKE_PROFIT_ORDER')
        self.world.add_fill(self.world.trades['41'], reason='STOP_LOSS_ORDER')
        self.world.signals['EUR-USD'] = 'long'
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'completed')
        self.assertEqual([r[0] for r in self.db.execute('SELECT exit_reason FROM trade_legs WHERE set_id="set-a"')],
                         ['TAKE_PROFIT_ORDER', 'STOP_LOSS_ORDER'])

    def test_a10_tp_adjustment_then_entry_skip(self):
        self.seed_set()
        self.world.add_fill(self.world.trades['40'], reason='TAKE_PROFIT_ORDER')
        self.run_master()
        changes = [c for c in self.world.calls if c.method == 'PUT']
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].payload['stopLoss']['price'], '1.10000')
        self.assertEqual(self.new_decision()['outcome'], 'skipped')

    def test_a04_unresolved_close_allows_other_pairs_not_retry(self):
        self.seed_set()
        self.world.open_signal = 'short'
        def uncertain(call):
            if call.method == 'PUT' and '/40/close' in call.path:
                return reply({})
        self.world.on_call = uncertain
        self.run_master()
        self.assertEqual(self.row()['status'], 'completed_with_errors')
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertEqual(pair_progress(self.db, self.run_id, 'manage_new')['finished'], 28)
        first = len([c for c in self.world.calls if c.method == 'PUT'])
        self.run_id = 'master-2'
        self.clock.advance(86400)
        self.run_master()
        self.assertEqual(len([c for c in self.world.calls if c.method == 'PUT']), first)

    def test_a04_fatal_management_blocks_sizing_and_entry(self):
        self.world.on_call = lambda call: reply({'errorMessage': 'bad auth'}, 401)
        with self.assertRaises(BrokerError):
            self.run_master()
        self.assertEqual(len(self.world.calls), 1)
        self.assertEqual(self.row()['status'], 'failed')
        self.assertEqual(self.db.execute("SELECT status FROM stages WHERE stage='manage_new'").fetchone()[0], 'blocked')

    def test_a04_failed_balance_has_no_entry_or_final_requests(self):
        self.world.on_call = lambda call: reply({}, 503) if call.path.endswith('/summary') else None
        with self.assertRaises(BrokerError):
            self.run_master()
        self.assertEqual(len(self.world.calls), 2)
        self.assertIsNone(self.row()['sizing_balance'])
        self.assertEqual(self.row()['status'], 'failed')
        self.assertIn('Broker', self.row()['refresh_error'])

    def test_a03_a13_unavailable_window_continues_and_never_queues(self):
        self.world.candle_count['EUR-USD'] = 385
        self.world.signals['EUR-USD'] = 'long'
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))
        self.run_id = 'master-2'
        self.clock.advance(86400)
        self.world.candle_count.clear()
        self.world.signals.clear()
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertEqual(self.row()['session_date'], '2026-11-17')
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))

    def test_a13_untradeable_price_skips_and_advances(self):
        self.world.signals['EUR-USD'] = 'long'
        from .test_m04 import pricing_body
        body = pricing_body()
        body['prices'][0]['tradeable'] = False
        self.world.on_call = lambda call: reply(body) if '/pricing?' in call.path else None
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))
        self.assertEqual(pair_progress(self.db, self.run_id, 'manage_new')['finished'], 28)

    def test_a12_isolated_rejection_continues_without_reservation(self):
        self.world.signals['EUR-USD'] = 'long'
        def reject(call):
            if call.method == 'POST':
                order = call.payload['order']
                body = self.world.add('MARKET_ORDER_REJECT', instrument=order['instrument'], clientExtensions=order['clientExtensions'])
                return self.world.response(body)
        self.world.on_call = reject
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'failed')
        self.assertTrue(pair_is_available(self.db, 'EUR-USD'))
        self.assertEqual(self.row()['status'], 'completed_with_errors')
        self.assertEqual(pair_progress(self.db, self.run_id, 'manage_new')['finished'], 28)

    def test_a12_interruption_after_fill_no_replay_next_run(self):
        self.world.signals['EUR-USD'] = 'long'
        def crash(call):
            if '/trades/' in call.path and call.method == 'GET':
                raise Interrupted()
        self.world.on_call = crash
        with self.assertRaises(Interrupted):
            self.run_master()
        self.assertEqual(self.row()['status'], 'running')
        self.assertIsNone(self.row()['ended_at'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM trade_legs WHERE broker_state="open"').fetchone()[0], 1)
        self.world.on_call = None
        self.run_id = 'master-2'
        self.clock.advance(86400)
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertEqual(len([c for c in self.world.calls if c.method == 'POST']), 1)
        self.assertTrue(self.db.execute("SELECT 1 FROM issues WHERE status='open'").fetchone())

    def test_a12_same_run_identifier_cannot_resume(self):
        self.run_master()
        before = len(self.world.calls)
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_master()
        self.assertEqual(len(self.world.calls), before)

    def test_a12_write_failure_after_send_stops_all_requests(self):
        self.world.signals['EUR-USD'] = 'long'
        from nnfx_practice import entry
        original = entry._Candidate.response
        def denied(candidate, *args, **kwargs):
            with interrupt_commit(candidate.db):
                return original(candidate, *args, **kwargs)
        with patch.object(entry._Candidate, 'response', denied), self.assertLogs('nnfx_practice.master', level='ERROR'):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_master()
        self.assertEqual(self.world.calls[-1].method, 'POST')
        self.assertEqual(self.db.execute('SELECT outcome FROM broker_attempts').fetchone()[0], 'prepared')
        self.assertIsNone(self.row()['ended_at'])

    def test_a12_failure_committing_pair_outcome_never_advances(self):
        import nnfx_practice.entry as entry
        original = entry.finish_pair
        def denied(db, *args, **kwargs):
            with interrupt_commit(db):
                return original(db, *args, **kwargs)
        with patch.object(entry, 'finish_pair', denied), self.assertLogs('nnfx_practice.master', level='ERROR'):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_master()
        self.assertEqual(pair_progress(self.db, self.run_id, 'manage_new')['finished'], 0)
        self.assertEqual(len([c for c in self.world.calls if '/candles?' in c.path]), 1)

    def test_a15_final_refresh_failure_preserves_sizing_and_previous_snapshot(self):
        def failed(call):
            if call.path.endswith('fixture-account-a') and len(self.world.calls) > 2:
                return reply({}, 503)
        self.world.on_call = failed
        self.run_master()
        self.assertEqual(self.row()['status'], 'completed_with_errors')
        self.assertIsNotNone(self.row()['refresh_error'])
        report = account_report(self.db, 'qualification')
        self.assertEqual(report.balance, Decimal('1000'))
        snapshot = self.db.execute('SELECT purpose FROM account_snapshots WHERE snapshot_id=?', (report.snapshot_id,)).fetchone()
        self.assertEqual(snapshot[0], 'manage_open')
        self.assertEqual(self.row()['sizing_balance'], '1000.00')

    def test_a16_ordinary_rejects_unactivated_and_live_execution_stays_disabled(self):
        with self.assertRaises(ConfigurationError):
            self.run_master(mode='ordinary')
        self.assertEqual(self.world.calls, [])
        with PracticeBroker(self.bound) as live:
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                run_master(self.root, 'controller-a', live, mode='qualification', evidence=EVIDENCE,
                           config_hash='c'*64, code_hash='d'*64)
        self.assertEqual(self.db.execute('SELECT count(*) FROM runs').fetchone()[0], 0)


class LifecycleChecks(M07Case):
    def activate(self, evidence=EVIDENCE):
        return activate_ordinary(self.root, 'controller-a', self.broker, service=self.service, evidence=evidence)

    def test_a12_repeated_initialization_keeps_q0_and_imports_forward(self):
        q0 = self.initialize()
        self.world.add('TRANSFER_FUNDS', amount='20')
        self.world.balance = '1020'
        self.assertEqual(self.initialize(), q0)
        row = self.db.execute('SELECT * FROM notebook').fetchone()
        self.assertEqual(row['qualification_transaction_id'], '100')
        self.assertEqual(row['imported_through_transaction_id'], '101')
        self.assertIsNone(row['activated_at'])

    def test_a12_initialization_commit_failure_retries_without_partial_baseline(self):
        import nnfx_practice.lifecycle as lifecycle
        original = lifecycle._save_snapshot
        def fail(db, *args, **kwargs):
            original(db, *args, **kwargs)
            raise Interrupted()
        with patch.object(lifecycle, '_save_snapshot', fail), self.assertRaises(Interrupted):
            self.initialize()
        with open_notebook(self.root, self.bound) as db:
            self.assertIsNone(db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0])
            self.assertEqual(db.execute('SELECT count(*) FROM account_snapshots').fetchone()[0], 0)
        self.initialize()
        self.assertEqual(self.db.execute('SELECT count(*) FROM account_snapshots').fetchone()[0], 1)

    def test_a12_initialization_after_commit_interruption_preserves_baseline(self):
        original = self.service.restore_timer
        def crash(prior):
            original(prior)
            raise Interrupted()
        with patch.object(self.service, 'restore_timer', side_effect=crash), self.assertRaises(Interrupted):
            self.initialize()
        with open_notebook(self.root, self.bound) as db:
            q0 = db.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0]
        self.assertEqual(self.initialize(), q0)

    def test_a12_initialization_rejects_existing_broker_trades(self):
        from .test_m02 import open_trade
        self.world.trades['40'] = open_trade(40)
        with self.assertRaises(ConfigurationError):
            self.initialize()
        self.assertTrue(self.service.timer)

    def test_a12_a16_activation_atomic_interruption_before_commit(self):
        self.initialize()
        before = dict(self.db.execute('SELECT * FROM notebook').fetchone())
        import nnfx_practice.lifecycle as lifecycle
        original = lifecycle.require_clear
        def crash(db, snapshot):
            original(db, snapshot)
            raise Interrupted()
        with patch.object(lifecycle, 'require_clear', crash), self.assertRaises(Interrupted):
            self.activate()
        self.assertEqual(dict(self.db.execute('SELECT * FROM notebook').fetchone()), before)
        self.assertEqual(self.db.execute("SELECT count(*) FROM account_snapshots WHERE purpose='activation'").fetchone()[0], 0)
        self.activate()

    def test_a12_activation_after_commit_interruption_and_repeat(self):
        self.initialize()
        original = self.service.restore_timer
        def crash(prior):
            original(prior)
            raise Interrupted()
        with patch.object(self.service, 'restore_timer', crash), self.assertRaises(Interrupted):
            self.activate()
        before = dict(self.db.execute('SELECT * FROM notebook').fetchone())
        calls = len(self.world.calls)
        self.assertEqual(self.activate(), before['activation_snapshot_id'])
        self.assertEqual(dict(self.db.execute('SELECT * FROM notebook').fetchone()), before)
        self.assertEqual(len(self.world.calls), calls)

    def test_a12_activation_unresolved_issue_stays_unactivated(self):
        self.initialize()
        with transaction(self.db):
            _issue(self.db, 'fixture', '1', self.broker.now(), {}, pair='EUR-USD')
        with self.assertRaises(ConfigurationError):
            self.activate()
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        self.assertEqual(self.db.execute("SELECT status FROM issues").fetchone()[0], 'open')

    def test_a12_activation_requires_every_acceptance_reference(self):
        self.initialize()
        for key in EVIDENCE:
            refs = dict(EVIDENCE)
            del refs[key]
            with self.subTest(missing=key), self.assertRaises(ConfigurationError):
                self.activate(refs)
        self.assertEqual(len(self.world.calls), 1)

    def test_a14_qualification_100_ordinary_20_exactly_once(self):
        self.initialize()
        # Actual ledger imports, with an operator-owned issue for an unregistered
        # fixture fill explicitly disposed before the baseline transition.
        trade = {'id': '40', 'instrument': 'EUR_USD', 'currentUnits': '1000'}
        self.world.add_fill(trade, pl='100')
        with controller_exclusion(self.root, self.bound):
            reconcile_snapshot(self.db, self.broker, purpose='qualification_report')
        self.assertIsNone(account_report(self.db, 'ordinary'))
        self.assertEqual(account_report(self.db, 'qualification').realised_profit, Decimal('100'))
        issue = self.db.execute('SELECT issue_id FROM issues').fetchone()[0]
        record_disposition(self.root, 'controller-a', self.broker, service=self.service,
                           issue_id=issue, operator_id='fixture-owner', explanation='Confirmed fixture closure')
        history_before = [tuple(r) for r in self.db.execute('SELECT * FROM broker_transactions')]
        a0 = self.activate()
        self.world.add_fill({'id': '41', 'instrument': 'EUR_USD', 'currentUnits': '1000'}, pl='20')
        with controller_exclusion(self.root, self.bound):
            reconcile_snapshot(self.db, self.broker)
            reconcile_snapshot(self.db, self.broker)
        qualification = account_report(self.db, 'qualification')
        ordinary = account_report(self.db, 'ordinary')
        self.assertEqual(qualification.realised_profit, Decimal('100'))
        self.assertEqual(qualification.snapshot_id, a0)
        self.assertEqual(ordinary.opening_balance, Decimal('1100'))
        self.assertEqual(ordinary.realised_profit, Decimal('20'))
        self.assertEqual(ordinary.balance, Decimal('1120'))
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM broker_transactions')][:1], history_before)

    def test_a16_changed_binding_and_count_fail_before_broker_reads(self):
        self.initialize()
        initial = len(self.world.calls)
        for field, value in (('lookback_candles', 385), ('account_id', 'wrong-account'), ('home_currency', 'EUR')):
            bound = replace(self.bound, connection=replace(self.bound.connection, **{field: value}))
            broker = PracticeBroker(bound, transport=ScriptedTransport())
            with self.assertRaises(ConfigurationError):
                initialize_qualification(self.root, 'controller-a', broker, service=self.service, evidence=EVIDENCE)
        self.assertEqual(len(self.world.calls), initial)

    def test_a16_baselines_and_original_binding_are_immutable(self):
        q0 = self.initialize()
        original = tuple(self.db.execute('SELECT controller_id,notebook_id,account_id,home_currency,manifest_hash FROM notebook').fetchone())
        a0 = self.activate()
        self.assertEqual(tuple(self.db.execute('SELECT controller_id,notebook_id,account_id,home_currency,manifest_hash FROM notebook').fetchone()), original)
        for sql, params in (
            ('UPDATE notebook SET qualification_snapshot_id=NULL', ()),
            ('UPDATE notebook SET activated_at=NULL', ()),
            ('UPDATE notebook SET manifest_hash=?', ('f'*64,)),
            ('UPDATE account_snapshots SET balance=? WHERE snapshot_id=?', ('0', q0)),
            ('DELETE FROM account_snapshots WHERE snapshot_id=?', (a0,)),
        ):
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql, params)

    def test_a16_post_activation_qualification_rejected_ordinary_allowed(self):
        self.initialize()
        self.activate()
        with self.assertRaises(ConfigurationError):
            run_master(self.root, 'controller-a', self.broker, mode='qualification', evidence=EVIDENCE,
                       config_hash='c'*64, code_hash='d'*64)
        # Real selected calculation on flat 386-candle windows.
        run_master(self.root, 'controller-a', self.broker, mode='ordinary', run_id=self.run_id,
                   config_hash='c'*64, code_hash='d'*64)
        self.assertEqual(self.db.execute('SELECT mode FROM run_invocations').fetchone()[0], 'ordinary')
        self.assertTrue(self.service.timer)  # Prior state restored, never newly enabled.


class ExclusionChecks(M07Case):
    def test_a12_a16_active_service_pending_launch_or_unpaused_timer_defers(self):
        for state in ('active', 'pending', 'pause_fails'):
            setattr(self.service, state, True)
            with self.subTest(state=state), self.assertRaises(MaintenanceDeferred):
                self.initialize()
            setattr(self.service, state, False)
            self.assertEqual(self.world.calls, [])
            self.assertTrue(self.service.timer)

    def test_a16_broker_reads_and_notebook_commit_exclude_launches(self):
        self.initialize()  # World checks exclusion at every broker request.
        with maintenance(self.root, self.bound, self.service):
            with self.assertRaises(MaintenanceDeferred):
                with controller_exclusion(self.root, self.bound):
                    self.fail('Concurrent launch')
            self.assertFalse(self.service.timer)
        self.assertTrue(self.service.timer)

    def test_a12_a16_failed_read_restores_initially_paused_timer(self):
        self.service.timer = False
        self.world.on_call = lambda _: reply({}, 503)
        with self.assertRaises(BrokerError):
            self.initialize()
        self.assertFalse(self.service.timer)
        self.assertEqual(self.service.events, ['pause', 'restore:False'])

    def test_a16_active_launch_defers_maintenance_before_reads(self):
        with controller_exclusion(self.root, self.bound):
            with self.assertRaises(MaintenanceDeferred):
                self.initialize()
        self.assertEqual(self.world.calls, [])
        self.assertEqual(self.service.events, [])


class DispositionChecks(M07Case):
    register = m02.ReconciliationChecks.register

    def setUp(self):
        super().setUp()
        self.initialize()

    def issue(self, code='incomplete_entry', **kwargs):
        with transaction(self.db):
            _issue(self.db, code, 'fixture-issue', self.broker.now(), {}, **kwargs)
        return self.db.execute('SELECT issue_id FROM issues ORDER BY rowid DESC').fetchone()[0]

    def dispose(self, issue):
        return record_disposition(self.root, 'controller-a', self.broker, service=self.service,
                                  issue_id=issue, operator_id='fixture-owner', explanation='Inspected matching broker records')

    def closed_set(self):
        self.register()
        from .test_m02 import open_trade
        for leg, identifier in enumerate((40, 41), 1):
            trade = open_trade(identifier, leg=leg, stop_id=str(identifier + 10))
            self.world.add_fill(trade)
        return self.issue(pair='EUR-USD', set_id='set-a')

    def test_a12_reconciliation_never_clears_operator_issue_disposition_does(self):
        issue = self.closed_set()
        with controller_exclusion(self.root, self.bound):
            reconcile_snapshot(self.db, self.broker)
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))
        proof = self.dispose(issue)
        self.assertEqual(proof['trade_ids'], ['40', '41'])
        self.assertEqual(proof['transaction_ids'], ['101', '102'])
        self.assertTrue(pair_is_available(self.db, 'EUR-USD'))
        self.assertTrue(all(c.method == 'GET' for c in self.world.calls))
        saved = dict(self.db.execute('SELECT * FROM issues WHERE issue_id=?', (issue,)).fetchone())
        self.assertEqual(saved['operator_id'], 'fixture-owner')
        self.assertEqual(saved['status'], 'resolved')
        self.assertEqual(self.dispose(issue), proof)
        self.assertEqual(dict(self.db.execute('SELECT * FROM issues WHERE issue_id=?', (issue,)).fetchone()), saved)

    def test_a12_disposition_does_not_resolve_other_issues(self):
        issue = self.closed_set()
        other = self.issue('second_problem', pair='EUR-USD', set_id='set-a')
        self.dispose(issue)
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))
        self.assertEqual(self.db.execute('SELECT status FROM issues WHERE issue_id=?', (other,)).fetchone()[0], 'open')

    def test_a12_missing_closure_or_incomplete_survivor_cannot_be_acknowledged(self):
        self.register()
        from .test_m02 import open_trade
        self.world.trades = {str(i): open_trade(i, leg=leg, stop_id=str(i+10)) for leg, i in enumerate((40, 41), 1)}
        issue = self.issue(pair='EUR-USD', set_id='set-a')
        with self.assertRaises(DispositionRequired):
            self.dispose(issue)
        self.assertEqual(self.db.execute('SELECT status FROM issues WHERE issue_id=?', (issue,)).fetchone()[0], 'open')
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))

    def test_a12_unsent_planned_legs_can_be_disposed_but_prepared_attempt_cannot(self):
        self.register(status='pending', trade_ids=(None, None))
        issue = self.issue(pair='EUR-USD', set_id='set-a')
        from nnfx_practice.notebook import prepare_attempt
        prepare_attempt(self.db, self.bound, attempt_id='unknown', run_id='run-a', stage='manage_new',
                        pair='EUR-USD', set_id='set-a', leg_no=1, purpose='entry', method='POST', path='/orders',
                        client_id='client-unknown', prepared_at=self.clock.now())
        with self.assertRaises(DispositionRequired):
            self.dispose(issue)
        self.assertEqual(self.db.execute('SELECT outcome FROM broker_attempts').fetchone()[0], 'prepared')
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))

    def test_a12_unsent_reservation_release_preserves_incomplete_history(self):
        self.register(status='pending', trade_ids=(None, None))
        issue = self.issue(pair='EUR-USD', set_id='set-a')
        self.dispose(issue)
        # Reconciliation creates its own interrupted-set issue, also operator-owned.
        other = self.db.execute("SELECT issue_id FROM issues WHERE status='open'").fetchone()[0]
        self.dispose(other)
        self.assertTrue(pair_is_available(self.db, 'EUR-USD'))
        self.assertEqual(self.db.execute('SELECT establishment_status FROM trade_sets').fetchone()[0], 'incomplete')
        self.assertEqual([r[0] for r in self.db.execute('SELECT broker_state FROM trade_legs')], ['not_opened']*2)

    def test_a10_restored_stop_disposition_keeps_survivor_occupied(self):
        self.register()
        from .test_m02 import open_trade
        self.world.add_fill(open_trade(40, leg=1), reason='TAKE_PROFIT_ORDER')
        self.world.trades['41'] = open_trade(41, stop_id='51', stop_price='1.10000')
        issue = self.issue('stop_to_entry', pair='EUR-USD', set_id='set-a')
        self.dispose(issue)
        self.assertEqual(self.db.execute('SELECT status FROM issues WHERE issue_id=?', (issue,)).fetchone()[0], 'resolved')
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))
        self.assertTrue(all(c.method == 'GET' for c in self.world.calls))

    def test_a10_wrong_restored_stop_remains_operator_owned(self):
        self.register()
        from .test_m02 import open_trade
        self.world.add_fill(open_trade(40, leg=1), reason='TAKE_PROFIT_ORDER')
        self.world.trades['41'] = open_trade(41, stop_id='51', stop_price='1.09000')
        issue = self.issue('stop_to_entry', pair='EUR-USD', set_id='set-a')
        with self.assertRaises(DispositionRequired):
            self.dispose(issue)
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))

    def test_a12_disposition_commit_failure_preserves_issue_and_restores_timer(self):
        issue = self.closed_set()
        import nnfx_practice.reconciliation as reconciliation
        original = reconciliation.transaction
        @contextmanager
        def denied(db):
            with interrupt_commit(db), original(db):
                yield
        with patch.object(reconciliation, 'transaction', denied), self.assertRaises(sqlite3.DatabaseError):
            self.dispose(issue)
        self.assertEqual(self.db.execute('SELECT status FROM issues WHERE issue_id=?', (issue,)).fetchone()[0], 'open')
        self.assertTrue(self.service.timer)
        self.assertTrue(all(c.method == 'GET' for c in self.world.calls))

    def test_a12_disposition_service_exclusion_precedes_evidence_reads(self):
        issue = self.closed_set()
        before = len(self.world.calls)
        self.service.active = True
        with self.assertRaises(MaintenanceDeferred):
            self.dispose(issue)
        self.assertEqual(len(self.world.calls), before)

    def test_a12_unregistered_order_needs_matching_cancel_record(self):
        created = self.world.add('LIMIT_ORDER', instrument='EUR_USD', units='1000')
        with controller_exclusion(self.root, self.bound):
            reconcile_snapshot(self.db, self.broker)
        issue = self.db.execute('SELECT issue_id FROM issues').fetchone()[0]
        cancel = self.world.add('ORDER_CANCEL', orderID=created['id'])
        # Targeted terminal order is separate from the account's pending list.
        def order_read(call):
            if '/orders/' in call.path:
                return reply({'order': {'id': created['id'], 'state': 'CANCELLED', 'cancellingTransactionID': cancel['id']},
                              'lastTransactionID': str(self.world.cursor)})
        self.world.on_call = order_read
        proof = self.dispose(issue)
        self.assertEqual(proof['order_ids'], [created['id']])
        self.assertEqual(self.db.execute('SELECT status FROM issues').fetchone()[0], 'resolved')

    def test_a12_closed_trade_resolves_uncertain_target_with_terminal_proof(self):
        issue = self.closed_set()
        from nnfx_practice.notebook import prepare_attempt
        prepare_attempt(self.db, self.bound, attempt_id='target-unknown', run_id='run-a', stage='manage_new',
                        pair='EUR-USD', set_id='set-a', leg_no=1, purpose='entry_target', method='PUT',
                        path='/trades/40/orders', broker_trade_id='40', prepared_at=self.clock.now())
        proof = self.dispose(issue)
        self.assertEqual(proof['terminal_targets'], [{'attempt_id': 'target-unknown', 'prior_outcome': 'prepared',
                                                    'closing_transaction_id': '101'}])
        self.assertEqual(self.db.execute('SELECT outcome FROM broker_attempts').fetchone()[0], 'cancelled')
        self.assertFalse(pair_is_available(self.db, 'EUR-USD'))  # Separate interrupted-attempt issue remains.
        other = self.db.execute("SELECT issue_id FROM issues WHERE status='open'").fetchone()[0]
        self.dispose(other)
        self.assertTrue(pair_is_available(self.db, 'EUR-USD'))
        self.assertTrue(all(c.method == 'GET' for c in self.world.calls))

    def test_a12_closed_legs_with_pending_order_cannot_be_disposed(self):
        issue = self.closed_set()
        self.world.orders['99'] = {'id': '99', 'type': 'TAKE_PROFIT', 'tradeID': '40', 'state': 'PENDING', 'price': '1.2'}
        with self.assertRaises(DispositionRequired):
            self.dispose(issue)
        self.assertEqual(self.db.execute('SELECT status FROM issues WHERE issue_id=?', (issue,)).fetchone()[0], 'open')

    def test_a12_unsupported_account_issue_stays_open(self):
        issue = self.issue('account_uncertainty')
        before = len(self.world.calls)
        with self.assertRaises(DispositionRequired):
            self.dispose(issue)
        self.assertEqual(len(self.world.calls), before)
        self.assertEqual(self.db.execute('SELECT status FROM issues').fetchone()[0], 'open')


class MasterEdgeChecks(M07Case):
    def setUp(self):
        super().setUp()
        self.initialize()
        self.world.calls.clear()

    register = MasterChecks.register
    seed_set = MasterChecks.seed_set
    run_master = MasterChecks.run_master
    row = MasterChecks.row
    new_decision = MasterChecks.new_decision

    def test_a10_rejected_stop_not_retried_and_later_confirmation_keeps_issue(self):
        self.seed_set()
        self.world.add_fill(self.world.trades['40'], reason='TAKE_PROFIT_ORDER')
        def reject(call):
            if call.method == 'PUT':
                body = self.world.add('STOP_LOSS_ORDER_REJECT', tradeID='41')
                return self.world.response(body)
        self.world.on_call = reject
        self.run_master()
        self.assertEqual(self.row()['status'], 'completed_with_errors')
        first = len([c for c in self.world.calls if c.method == 'PUT'])
        self.world.on_call = None
        self.run_id = 'master-2'
        self.clock.advance(86400)
        self.run_master()
        self.assertEqual(len([c for c in self.world.calls if c.method == 'PUT']), first)
        self.world.trades['41']['stopLossOrder']['price'] = '1.10000'
        self.run_id = 'master-3'
        self.clock.advance(86400)
        self.run_master()
        self.assertEqual(len([c for c in self.world.calls if c.method == 'PUT']), first)
        self.assertTrue(self.db.execute("SELECT 1 FROM issues WHERE status='open'").fetchone())
        self.assertEqual(self.new_decision()['outcome'], 'skipped')

    def test_a04_unexplained_sizing_balance_is_fatal(self):
        self.world.summary_balances = ['9999']
        with self.assertRaises(BrokerError):
            self.run_master()
        self.assertEqual(len(self.world.calls), 2)
        self.assertIsNone(self.row()['sizing_balance'])

    def test_a12_sizing_commit_failure_leaves_no_entry_requests(self):
        import nnfx_practice.master as master
        original = master._save_snapshot
        def interrupted(*args, **kwargs):
            original(*args, **kwargs)
            raise sqlite3.OperationalError('injected write failure')
        with patch.object(master, '_save_snapshot', interrupted), self.assertLogs('nnfx_practice.master', level='ERROR'):
            with self.assertRaises(sqlite3.OperationalError):
                self.run_master()
        self.assertEqual(len(self.world.calls), 2)
        self.assertIsNone(self.row()['sizing_balance'])
        self.assertEqual(self.row()['status'], 'running')

    def test_a12_interrupt_before_first_send_keeps_prepared_intent_and_no_retry(self):
        self.world.signals['EUR-USD'] = 'long'
        with patch.object(self.broker, 'enter_trade', side_effect=Interrupted()), self.assertRaises(Interrupted):
            self.run_master()
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))
        self.assertEqual(self.db.execute('SELECT outcome FROM broker_attempts').fetchone()[0], 'prepared')
        self.run_id = 'master-2'
        self.clock.advance(86400)
        self.run_master()
        self.assertEqual(self.new_decision()['outcome'], 'skipped')
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))

    def test_a12_mid_entry_history_failure_stops_other_pairs(self):
        self.world.signals['EUR-USD'] = 'long'
        self.world.on_call = lambda c: reply({}, 503) if '/transactions/sinceid' in c.path else None
        with self.assertRaises(BrokerError):
            self.run_master()
        self.assertEqual(len([c for c in self.world.calls if '/candles?' in c.path]), 1)
        self.assertEqual(len([c for c in self.world.calls if c.method == 'POST']), 1)
        self.assertEqual(self.row()['status'], 'failed')
        self.assertEqual(self.db.execute('SELECT imported_through_transaction_id FROM notebook').fetchone()[0], '100')

    def test_a03_invalid_atr_does_not_suppress_required_exit(self):
        self.seed_set()
        self.world.open_signal = 'short'
        self.world.signals['EUR-USD'] = 'long'
        self.world.atr = None
        self.run_master()
        self.assertEqual(len([c for c in self.world.calls if c.method == 'PUT']), 2)
        self.assertFalse(any(c.method == 'POST' for c in self.world.calls))
        self.assertEqual(self.new_decision()['atr_valid'], 0)

    def test_a12_lifecycle_activation_rejects_unresolved_qualification_set(self):
        self.register(status='pending', trade_ids=(None, None))
        with self.assertRaises(ConfigurationError):
            activate_ordinary(self.root, 'controller-a', self.broker, service=self.service, evidence=EVIDENCE)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM trade_legs').fetchone()[0], 2)

    def test_a12_qualification_invocation_requires_initialized_notebook_and_all_refs(self):
        for key in ('account_preflight', 'candle_preflight', 'm09_controller_controls', 'execution_authority'):
            refs = dict(EVIDENCE)
            refs.pop(key)
            with self.assertRaises(ConfigurationError):
                self.run_master(evidence=refs)
        self.assertEqual(self.world.calls, [])

    def test_a16_separate_controller_runs_keep_bindings_records_and_locks_independent(self):
        self.run_master()
        first = dict(self.row())
        path = self.root / '.env'
        path.write_text(path.read_text().replace('PRACTICE_B_LOOKBACK_CANDLES=50', 'PRACTICE_B_LOOKBACK_CANDLES=386'))
        bound = self.binding('controller-b')
        second = World(self)
        second.known_binding = bound
        broker = PracticeBroker(bound, transport=second, now=self.clock.now)
        with controller_exclusion(self.root, self.bound):
            initialize_qualification(self.root, 'controller-b', broker, service=Service(), evidence=EVIDENCE)
            with open_notebook(self.root, bound) as db:
                old = self.db
                self.db = db
                try:
                    run_master(self.root, 'controller-b', broker, mode='qualification', evidence=EVIDENCE,
                               run_id=self.run_id, config_hash='e'*64, code_hash='d'*64)
                    self.assertEqual(db.execute('SELECT count(*) FROM runs').fetchone()[0], 1)
                    self.assertEqual(db.execute('SELECT home_currency FROM notebook').fetchone()[0], 'EUR')
                    self.second_notebook_evidence = {name: [dict(r) for r in db.execute(f'SELECT * FROM {name}')]
                        for name in ('notebook', 'runs', 'run_invocations', 'stages', 'pair_decisions', 'account_snapshots')}
                finally:
                    self.db = old
        self.transports.append(second)
        self.assertEqual(dict(self.row()), first)
        self.assertTrue(all('/fixture-account-b' in c.path for c in second.calls))
        self.assertTrue(all('/fixture-account-a' in c.path for c in self.world.calls))


def _closure_variation(cause, fresh, former):
    def check(self):
        from .test_m02 import open_trade
        units = '1000' if former == 'long' else '-1000'
        self.register(direction=former, units=units)
        self.world.trades = {str(i): open_trade(i, leg=leg, units=units, initial=units, stop_id=str(i+10))
                             for leg, i in enumerate((40, 41), 1)}
        opposite = 'short' if former == 'long' else 'long'
        if cause == 'c1':
            self.world.open_signal = opposite
        elif cause == 'exit':
            self.world.exit_signal = opposite
        else:
            reasons = {'tp': ('TAKE_PROFIT_ORDER', 'TAKE_PROFIT_ORDER'),
                       'sl': ('STOP_LOSS_ORDER', 'STOP_LOSS_ORDER'),
                       'mixed': ('TAKE_PROFIT_ORDER', 'STOP_LOSS_ORDER')}[cause]
            for identifier, reason in zip(('40', '41'), reasons):
                self.world.add_fill(self.world.trades[identifier], reason=reason)
        self.world.signals['EUR-USD'] = fresh
        self.run_master()
        decision = self.new_decision()
        self.assertEqual(json.loads(decision['c1_json'])['direction'], fresh)
        self.assertEqual(decision['atr'], '0.001')
        self.assertEqual(decision['outcome'], 'skipped' if fresh == 'no_event' else 'completed')
        self.assertEqual(len([c for c in self.world.calls if c.method == 'POST']), 0 if fresh == 'no_event' else 2)
    return check


# Named cases retain a separate request/committed-state export for every variation.
for _cause in ('c1', 'exit', 'tp', 'sl', 'mixed'):
    for _fresh in ('long', 'short', 'no_event'):
        for _former in ('long', 'short'):
            _name = f'test_a02_a08_a09_{_cause}_former_{_former}_fresh_{_fresh}'
            setattr(MasterEdgeChecks, _name, _closure_variation(_cause, _fresh, _former))


class LifecycleCommitChecks(M07Case):
    activate = LifecycleChecks.activate

    def test_a12_q0_sqlite_commit_denied_is_atomic(self):
        import nnfx_practice.lifecycle as lifecycle
        original = lifecycle.transaction
        @contextmanager
        def denied(db):
            with interrupt_commit(db), original(db):
                yield
        with patch.object(lifecycle, 'transaction', denied), self.assertRaises(sqlite3.DatabaseError):
            self.initialize()
        self.initialize()
        self.assertEqual(self.db.execute('SELECT count(*) FROM account_snapshots').fetchone()[0], 1)

    def test_a12_a0_sqlite_commit_denied_rolls_back_snapshot_cursor_and_activation(self):
        self.initialize()
        self.world.add('TRANSFER_FUNDS', amount='100')
        self.world.balance = '1100'
        import nnfx_practice.reconciliation as reconciliation
        original = reconciliation.transaction
        @contextmanager
        def denied(db):
            with interrupt_commit(db), original(db):
                yield
        with patch.object(reconciliation, 'transaction', denied), self.assertRaises(sqlite3.DatabaseError):
            self.activate()
        row = self.db.execute('SELECT * FROM notebook').fetchone()
        self.assertIsNone(row['activated_at'])
        self.assertEqual(row['imported_through_transaction_id'], '100')
        self.assertEqual(self.db.execute('SELECT count(*) FROM broker_transactions').fetchone()[0], 0)
        self.activate()
        self.assertEqual(account_report(self.db, 'ordinary').opening_balance, Decimal('1100'))

    def test_a12_uninitialized_explicit_qualification_invocation_rejected(self):
        with open_notebook(self.root, self.bound, create=True):
            pass
        with self.assertRaises(ConfigurationError):
            run_master(self.root, 'controller-a', self.broker, mode='qualification', evidence=EVIDENCE,
                       config_hash='c'*64, code_hash='d'*64)
        self.assertEqual(self.world.calls, [])

    def test_a16_migrate_v1_atomically_preserving_history_and_binding(self):
        from nnfx_practice.notebook import _binding_values, _schema_script
        path = self.bound.experiment.notebook_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, isolation_level=None)
        with transaction(db):
            _schema_script(db, 'schema.sql')
            db.execute('''INSERT INTO notebook (singleton,controller_id,notebook_id,account_id,home_currency,
                          strategy_version,manifest_json,manifest_hash,lookback_candles) VALUES (1,?,?,?,?,?,?,?,?)''',
                       _binding_values(self.bound))
            db.execute('PRAGMA user_version=1')
        db.close()
        import nnfx_practice.notebook as notebook
        original = notebook._schema_script
        def interrupted(connection, name):
            original(connection, name)
            if name == 'schema_m07.sql':
                raise Interrupted()
        with patch.object(notebook, '_schema_script', interrupted), self.assertRaises(Interrupted):
            with open_notebook(self.root, self.bound):
                pass
        legacy = sqlite3.connect(path)
        self.assertEqual(legacy.execute('PRAGMA user_version').fetchone()[0], 1)
        self.assertFalse(legacy.execute("SELECT 1 FROM sqlite_schema WHERE name='run_invocations'").fetchone())
        legacy.close()
        self.initialize()
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertEqual(tuple(self.db.execute('SELECT controller_id,notebook_id,account_id,home_currency,strategy_version,manifest_json,manifest_hash,lookback_candles FROM notebook').fetchone()), _binding_values(self.bound))
