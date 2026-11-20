"""A14–A16 dashboard checks. Every broker fact here is an offline fixture."""

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch

from nnfx_practice.broker import BrokerError
from nnfx_practice.dashboard import create_app, latest_launch, ny_time, read_view
from nnfx_practice.ledger import account_report
from nnfx_practice.notebook import finish_pair, open_readonly, prepare_attempt, utc_text
from nnfx_practice.reconciliation import import_through, reconcile_snapshot, record_confirmed_transactions

from .support import ACCOUNT, TOKEN, Call, NotebookCase
from . import test_m02 as m02
from .test_m02 import ROOT, STAMP, account, event, open_trade, order_fill, reply


class DashboardChecks(NotebookCase):
    opening = m02.ReconciliationChecks.opening
    register = m02.ReconciliationChecks.register
    script = m02.ReconciliationChecks.script
    snapshot = m02.ReconciliationChecks.snapshot

    def setUp(self):
        super().setUp()
        self.bound, self.other_bound = self.binding(), self.binding('controller-b')
        self.db = self.notebook(self.bound)
        self.opening(self.db)
        self.app = create_app(self.root, now=self.clock.now)
        self.app.testing = True
        self.client = self.app.test_client()
        self.responses = []

    def get(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.responses.append((path, text))
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(ACCOUNT, text)
        return text

    def model(self, detail=True):
        result = read_view(self.root, self.bound.experiment, self.clock.now(), detail=detail)
        self.assertIsNone(result['error'])
        return result

    def metadata(self, pair='EUR-USD', location=-4):
        self.db.execute('''UPDATE pair_decisions SET sizing_json = ? WHERE pair = ? AND stage = 'manage_new' ''',
                        (json.dumps({'reads': [{'purpose': 'instrument_limits', 'body': {'instruments': [
                            {'name': pair.replace('-', '_'), 'pipLocation': location}]}}]}), pair))

    def close(self, *, pair='EUR-USD', direction='long', price='1.1', exit='1.11', pl='100', location=-4):
        self.register(pair=pair, direction=direction, price=price, trade_ids=('40', None),
                      units='-1000' if direction == 'short' else '1000')
        self.metadata(pair, location)
        self.snapshot(account(101, str(1000 + Decimal(pl))), order_fill(101, 40, price=exit, pl=pl,
                      units='-1000' if direction == 'short' else '1000', name=pair.replace('-', '_')))

    def tearDown(self):
        destination = os.environ.get('NNFX_M08_EVIDENCE_DIR')
        if destination:
            target = Path(destination) / self.id().split('.')[-1]
            target.mkdir(parents=True, exist_ok=True)
            for index, (path, body) in enumerate(self.responses):
                (target / f'{index:02}.html').write_text(body)
            data = {'classification': 'offline', 'test': self.id(),
                    'controller_id': self.bound.experiment.controller_id, 'notebook_id': self.bound.experiment.notebook_id,
                    'manifest_hash': self.bound.manifest.hash, 'config_hash': sha256((self.root / 'config.toml').read_bytes()).hexdigest(),
                    'responses': [{'path': path, 'sha256': sha256(body.encode()).hexdigest()} for path, body in self.responses],
                    'tables': {table: [dict(r) for r in self.db.execute('SELECT ' + columns + ' FROM ' + table)]
                               for table, columns in [('runs', 'run_id,strategy_hash,config_hash,code_hash,status,started_at,ended_at,refresh_error'),
                                                      ('pair_decisions', 'run_id,stage,pair,outcome'),
                                                      ('account_snapshots', 'snapshot_id,last_transaction_id,balance,reconciliation_status'),
                                                      ('ledger_entries', 'transaction_id,amount,category,posted,broker_trade_id')]},
                    'integrity': self.db.execute('PRAGMA integrity_check').fetchone()[0],
                    'foreign_keys': [list(r) for r in self.db.execute('PRAGMA foreign_key_check')]}
            (target / 'records.json').write_text(json.dumps(data, indent=2) + '\n')
        super().tearDown()

    def test_a14_long_eur_signed_pips_and_profit(self):
        self.close()
        leg = self.model()['journal'][0]
        self.assertEqual((leg['pips'], leg['trading_pl']), (Decimal(100), Decimal(100)))
        html = self.get('/notebooks/notebook-a')
        self.assertIn('class="win">+100', html)
        self.assertIn('Trading result (USD)', html)
        for column in ('Set ID', 'Broker trade ID', 'Leg', 'Pair', 'Direction', 'Initial / current units',
                       'Entry time', 'Status', 'Actual entry', 'Original stop', 'Current stop',
                       'Trade 1 target', 'Final exit time', 'Exit price', 'Exit reason', 'Signed pips',
                       'Financing (USD)', 'Other charges (USD)'):
            self.assertIn(column, html)

    def test_a14_short_eur_signed_pips_and_loss(self):
        self.close(direction='short', exit='1.103', pl='-3')
        self.assertEqual(self.model()['journal'][0]['pips'], Decimal('-30'))
        self.assertIn('class="loss">-30', self.get('/notebooks/notebook-a'))

    def test_a14_long_jpy_uses_recorded_pip_location(self):
        self.close(pair='USD-JPY', price='150', exit='150.03', pl='3', location=-2)
        self.assertEqual(self.model()['journal'][0]['pips'], Decimal('3'))
        self.assertIn('class="win">+3', self.get('/notebooks/notebook-a'))

    def test_a14_short_jpy_uses_recorded_pip_location(self):
        self.close(pair='USD-JPY', direction='short', price='150', exit='150.03', pl='-3', location=-2)
        self.assertEqual(self.model()['journal'][0]['pips'], Decimal('-3'))
        self.assertIn('class="loss">-3', self.get('/notebooks/notebook-a'))

    def test_a14_recorded_nonstandard_pip_location_is_not_inferred_from_pair(self):
        self.close(location=-3)
        self.assertEqual(self.model()['journal'][0]['pips'], Decimal(10))
        self.get('/notebooks/notebook-a')

    def test_a14_missing_pip_metadata_is_unknown(self):
        self.close()
        self.db.execute('UPDATE pair_decisions SET sizing_json = NULL')
        self.assertIsNone(self.model()['journal'][0]['pips'])
        self.assertIn('Pip metadata unavailable', self.get('/notebooks/notebook-a'))

    def test_a14_missing_unrealised_result_stays_unavailable(self):
        self.close()
        self.db.execute("UPDATE account_snapshots SET unrealised_pl = NULL WHERE snapshot_id='snapshot'")
        self.assertIsNone(self.model()['report'].unrealised_pl)
        html = self.get('/notebooks/notebook-a')
        self.assertIn('Unrealised result (USD)</dt><dd><span class="">Unavailable', html)

    def test_a14_split_reductions_charges_and_weighted_exit(self):
        self.register(trade_ids=('40', None))
        self.metadata()
        reduce = order_fill(101, 40, effect='reduce', units='400', price='1.10500', pl='10', financing='-1', commission='2', fee='0.5')
        finance = event(102, 'DAILY_FINANCING', financing='-0.5', positionFinancings=[{'openTradeFinancings': [{'tradeID': '40', 'financing': '-0.5'}]}])
        deposit = event(103, 'TRANSFER_FUNDS', amount='50')
        self.snapshot(account(103, '1056', trades=[open_trade(40, units='600', leg=1)]), reduce, finance, deposit)
        model = self.model()
        leg = model['journal'][0]
        self.assertEqual((leg['exit_price'], leg['pips'], leg['trading_pl']), (None, None, None))
        report = model['report']
        self.assertEqual((report.realised_profit, report.financing, report.commission, report.other_charges,
                          report.cash_adjustments, report.net_posted), tuple(map(Decimal, ('10', '-1.5', '-2', '-.5', '50', '56'))))
        self.get('/notebooks/notebook-a')
        final = order_fill(104, 40, units='600', price='1.11300', pl='100', reason='MARKET_ORDER_TRADE_CLOSE')
        final['time'] = '2026-11-16T21:50:01.123456789Z'
        self.snapshot(account(104, '1156'), final, cursor=103, name='final')
        leg = self.model()['journal'][0]
        self.assertEqual((leg['exit_price'], leg['pips'], leg['trading_pl'], leg['exit_at']),
                         ('1.10980', Decimal(98), Decimal(110), final['time']))
        self.assertEqual(len(leg['fills']), 2)
        html = self.get('/notebooks/notebook-a')
        self.assertIn('1.10980', html)
        self.assertIn('Informational allocation', html)
        self.assertIn('Unallocated account posting', html)
        self.assertIn('class="loss">-2', html)
        self.assertIn('.123456789 EST -0500', html)
        # Duplicate import does not add either aggregate postings or allocations.
        before = self.model()['report']
        import_through(self.db, self.script(), '104')
        self.assertEqual(self.model()['report'], before)

    def test_a14_snapshot_s_plus_100_failed_then_covering_refresh(self):
        self.register(trade_ids=('40', None))
        self.metadata()
        self.clock.advance(2)
        self.snapshot(account(101, trades=[open_trade(40, leg=1)]), event(101, 'CLIENT_CONFIGURE'), name='S')
        before = self.model()['report']
        self.clock.advance(1)
        close = order_fill(102, 40, price='1.11', pl='100')
        close['time'] = utc_text(self.clock.now())
        record_confirmed_transactions(self.db, self.script(), [close])
        self.clock.advance(1)
        with self.assertRaises(BrokerError):
            reconcile_snapshot(self.db, self.script((Call('GET', ROOT), reply({}, 503))), snapshot_id='failed-final')
        failed = self.model()
        self.assertEqual(failed['report'], before)
        self.assertTrue(failed['stale'])
        self.assertFalse(failed['schedule_stale'])
        self.assertEqual((before.balance, before.realised_profit), (Decimal(1000), Decimal(0)))
        self.assertTrue(failed['journal'][0]['after_snapshot'])
        self.assertEqual(failed['journal'][0]['trading_pl'], Decimal(100))
        html = self.get('/notebooks/notebook-a')
        self.assertIn('After account snapshot', html)
        self.assertIn('Refresh failed', html)
        self.assertIn('retaining the preceding reconciled snapshot', html)
        self.assertIn('class="win">+1000.00', html)
        self.get('/notebooks')
        self.clock.advance(1)
        self.snapshot(account(102, '1100'), close, cursor=101, name='covering')
        model = self.model()
        self.assertEqual((model['report'].realised_profit, model['report'].balance), (Decimal(100), Decimal(1100)))
        self.assertIsNone(model['refresh_problem'])
        self.assertFalse(model['journal'][0]['after_snapshot'])
        self.get('/notebooks/notebook-a')

    def test_a14_newer_allocated_financing_labels_the_leg_without_changing_summary(self):
        self.register(trade_ids=('40', None))
        self.snapshot(account(101, trades=[open_trade(40, leg=1)]), event(101, 'CLIENT_CONFIGURE'), name='S')
        finance = event(102, 'DAILY_FINANCING', financing='-5', positionFinancings=[
            {'openTradeFinancings': [{'tradeID': '40', 'financing': '-5'}]}])
        record_confirmed_transactions(self.db, self.script(), [finance])
        view = self.model()
        leg = view['journal'][0]
        self.assertEqual(leg['financing'], Decimal('-5'))
        self.assertTrue(leg['after_snapshot'])
        self.assertEqual(view['report'].financing, Decimal(0))
        self.assertEqual(leg['broker_state_transaction_id'], '101')
        html = self.get('/notebooks/notebook-a')
        self.assertIn('After account snapshot', html)
        self.assertIn('class="loss">-5', html)

    def test_a14_q0_plus_100_a0_then_ordinary_plus_20(self):
        self.register()
        self.metadata()
        self.db.execute("INSERT INTO run_invocations VALUES ('run-a','qualification','{}')")
        self.snapshot(account(101, '1100', trades=[open_trade(41)]), order_fill(101, 40, pl='100'), name='qual')
        html = self.get('/notebooks/notebook-a')
        self.assertIn('notebook unactivated', html)
        self.assertIsNone(self.model()['reports']['ordinary'])
        self.snapshot(account(102, '1100'), order_fill(102, 41), cursor=101, name='a0')
        self.db.execute('''UPDATE notebook SET activation_snapshot_id = 'a0', activation_transaction_id = '102',
            activation_evidence_json = '["offline-a0"]', activated_at = ?''', (utc_text(self.clock.now()),))
        self.register(set_id='ordinary-set', pair='GBP-USD', trade_ids=('61', None), run_id='run-b')
        self.db.execute("INSERT INTO run_invocations VALUES ('run-b','ordinary',NULL)")
        self.metadata('GBP-USD')
        ordinary = order_fill(103, 61, name='GBP_USD', pl='20')
        ordinary['time'] = '2026-11-17T21:50:00Z'
        self.snapshot(account(103, '1120'), ordinary, cursor=102, name='ordinary')
        model = self.model()
        qual, live = model['reports']['qualification'], model['reports']['ordinary']
        self.assertEqual((qual.opening_snapshot_id, qual.snapshot_id, qual.realised_profit), ('q0', 'a0', Decimal(100)))
        self.assertEqual((live.opening_balance, live.realised_profit, live.balance), (Decimal(1100), Decimal(20), Decimal(1120)))
        self.assertEqual({r['period'] for r in model['activity'] if r['transaction_id'] == '103'}, {'Ordinary'})
        self.assertEqual({r['period'] for r in model['journal'] if r['set_id'] == 'ordinary-set'}, {'Ordinary'})
        self.assertEqual({r['period'] for r in model['journal'] if r['set_id'] == 'set-a'}, {'Qualification'})
        html = self.get('/notebooks/notebook-a')
        self.assertIn('Qualification (capped at A0 after activation)', html)
        self.assertIn('Q0 q0 / 0100 · A0 a0 / 102', html)
        self.assertIn('class="win">+20', html)
        self.get('/notebooks')

    def test_a14_missing_allocated_amounts_are_unavailable_not_zero(self):
        self.register(trade_ids=('40', None))
        self.metadata()
        close = order_fill(101, 40, price='1.11', pl='100')
        del close['tradesClosed'][0]['realizedPL']
        self.snapshot(account(101, '1100'), close)
        self.assertIsNone(self.model()['journal'][0]['trading_pl'])
        self.assertIn('Unavailable', self.get('/notebooks/notebook-a'))

    def test_a15_committed_outcomes_exclude_unfinished_and_show_children(self):
        self.start_run(self.db)
        self.db.execute("INSERT INTO run_invocations VALUES ('run-a','qualification','{}')")
        for i, (pair, outcome) in enumerate([('EUR-USD', 'completed'), ('GBP-USD', 'skipped'), ('AUD-USD', 'failed'), ('NZD-USD', None)], 1):
            self.add_decision(self.db, pair, i)
            if outcome:
                finish_pair(self.db, self.bound, run_id='run-a', stage='manage_new', pair=pair,
                            ended_at=self.clock.now(), outcome=outcome, reason='fixture ' + outcome)
        self.db.execute("UPDATE stages SET status='running',started_at=?,current_step='4.3',current_pair='NZD-USD' WHERE stage='manage_new'", (STAMP,))
        self.db.execute("UPDATE stages SET status='completed',started_at=?,ended_at=?,expected_pair_count=0,reconciliation_progress_json=? WHERE stage='manage_open'", (STAMP, STAMP, '{"due_stops":1}'))
        stages = self.model()['runs'][0]['stages']
        self.assertEqual([s['stage'] for s in stages], ['manage_open', 'manage_new'])
        stage = stages[1]
        self.assertEqual((stage['finished'], stage['skipped'], stage['failed']), (3, 1, 1))
        html = self.get('/controllers')
        for expected in ('3 / 28 pairs', '1 skipped · 1 failed', 'Unfinished decision', 'NZD-USD', '4.3',
                         'Reconciliation:', 'due_stops', 'surviving pairs', 'Unfinished', 'fixture failed'):
            self.assertIn(expected, html)

    def test_a15_completed_failed_and_unfinished_runs_remain_visible(self):
        for i, state in enumerate(('completed', 'failed', 'completed_with_errors', 'running')):
            self.start_run(self.db, f'run-{i}')
            if state != 'running':
                self.db.execute('UPDATE runs SET status=?,ended_at=?,duration_seconds=12.5,refresh_error=? WHERE run_id=?',
                                (state, STAMP, 'unavailable refresh' if state == 'failed' else None, f'run-{i}'))
        html = self.get('/controllers')
        for state in ('completed', 'failed', 'completed_with_errors', 'Unfinished', '12.5 seconds', 'unavailable refresh'):
            self.assertIn(state, html)

    def test_a15_missing_baseline_and_missing_database_are_visible(self):
        other = self.notebook(self.other_bound)
        html = self.get('/notebooks/notebook-b')
        self.assertIn('Account figures unavailable', html)
        self.assertIn('Unavailable', html)
        html = self.get('/notebooks')
        self.assertIn('Fixture B', html)
        self.assertIsNone(account_report(other, 'ordinary'))
        # Registered but absent files never get created by GET.
        self.write_registry(notebook_b='absent')
        client = create_app(self.root, now=self.clock.now).test_client()
        self.assertIn(b'Notebook unavailable', client.get('/notebooks/absent').data)
        self.assertFalse((self.root / 'var/notebooks/absent.sqlite3').exists())

    def test_a15_pending_refresh_ignores_sizing_snapshot(self):
        self.db.execute("INSERT INTO account_snapshots(snapshot_id,purpose,requested_at,reconciliation_status) VALUES('sizing','sizing_balance',?,'pending')", (STAMP,))
        self.assertIsNone(self.model()['refresh_problem'])
        self.db.execute("INSERT INTO account_snapshots(snapshot_id,purpose,requested_at,reconciliation_status) VALUES('refresh','reporting',?,'pending')", (STAMP,))
        self.assertIn('Refresh pending', self.get('/notebooks/notebook-a'))

    def test_a15_failed_refresh_preserves_snapshot_age_and_unrealised(self):
        self.register(trade_ids=('40', None))
        self.snapshot(account(101, trades=[open_trade(40, leg=1)], unrealised='-7.25'), event(101, 'CLIENT_CONFIGURE'))
        self.clock.advance(30)
        with self.assertRaises(BrokerError):
            reconcile_snapshot(self.db, self.script((Call('GET', ROOT), reply({}, 503))), snapshot_id='failed')
        model = self.model()
        self.assertEqual(model['report'].unrealised_pl, Decimal('-7.25'))
        self.assertIn('30s', model['refresh_age'])
        html = self.get('/notebooks/notebook-a')
        self.assertIn('class="loss">-7.25', html)
        self.assertIn('Refresh failed', html)

    def test_a15_missed_weekday_launch_is_stale_without_catchup(self):
        self.clock.current = datetime(2026, 11, 17, 21, 51, tzinfo=UTC)
        self.assertTrue(self.model()['stale'])
        html = self.get('/controllers')
        self.assertIn('Stale:', html)
        self.assertIn('2026-11-17 16:50:00 EST -0500', html)
        self.assertEqual(self.db.execute('SELECT count(*) FROM runs').fetchone()[0], 0)

    def test_a15_dst_offsets_weekends_and_nanoseconds(self):
        self.assertEqual(ny_time('2026-03-06T21:50:00.123456789Z'), '2026-03-06 16:50:00.123456789 EST -0500')
        self.assertEqual(ny_time('2026-03-09T20:50:00Z'), '2026-03-09 16:50:00 EDT -0400')
        self.assertEqual(ny_time('2026-10-30T20:50:00Z'), '2026-10-30 16:50:00 EDT -0400')
        self.assertEqual(ny_time('2026-11-02T21:50:00Z'), '2026-11-02 16:50:00 EST -0500')
        for stamp, expected in [('2026-03-08T22:00:00Z', '2026-03-06T21:50:00+00:00'),
                                ('2026-03-09T20:49:59Z', '2026-03-06T21:50:00+00:00'),
                                ('2026-03-09T20:50:00Z', '2026-03-09T20:50:00+00:00'),
                                ('2026-11-01T22:00:00Z', '2026-10-30T20:50:00+00:00')]:
            self.assertEqual(latest_launch(datetime.fromisoformat(stamp)).astimezone(UTC).isoformat(), expected)

    def test_a15_gets_without_credentials_broker_or_controller_access(self):
        (self.root / '.env').unlink()
        with patch('nnfx_practice.config.read_private_settings', side_effect=AssertionError('private read')), \
             patch('nnfx_practice.broker.PracticeBroker.__init__', side_effect=AssertionError('broker created')), \
             patch('nnfx_practice.master.run_master', side_effect=AssertionError('master called')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            self.client = create_app(self.root, now=self.clock.now).test_client()
            for path in ('/controllers', '/notebooks', '/notebooks/notebook-a'):
                self.get(path)

    def test_a15_local_command_disables_dotenv_debug_and_reloader(self):
        from nnfx_practice.dashboard import main
        (self.root / '.env').unlink()
        with patch('sys.argv', ['dashboard', '--root', str(self.root)]), patch('flask.Flask.run') as run:
            main()
        run.assert_called_once_with(host='127.0.0.1', port=8878, debug=False, use_reloader=False, load_dotenv=False)

    def test_a15_readonly_files_and_rejected_mutation_requests(self):
        self.register(trade_ids=(None, None), status='pending')
        prepare_attempt(self.db, self.bound, attempt_id='attempt', run_id='run-a', stage='manage_new',
                        purpose='entry', method='POST', path='/orders', prepared_at=self.clock.now(),
                        pair='EUR-USD', set_id='set-a', leg_no=1)
        path = self.bound.experiment.notebook_path(self.root)
        files = [path, Path(str(path) + '-wal'), Path(str(path) + '-shm')]
        prior = {p: p.stat().st_mode & 0o777 for p in files}
        parent_mode = path.parent.stat().st_mode & 0o777
        before = list(self.db.iterdump())
        try:
            for p in files:
                p.chmod(0o400)
            path.parent.chmod(0o500)
            (self.root / '.env').unlink()
            for route in ('/controllers', '/notebooks', '/notebooks/notebook-a'):
                self.get(route)
                for method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                    self.assertEqual(self.client.open(route, method=method, json={'action': 'activate'}).status_code, 405)
            for route in ('/runs', '/activate', '/disposition', '/notebooks/notebook-a/activate'):
                self.assertEqual(self.client.post(route).status_code, 404)
            with open_readonly(self.root, self.bound.experiment) as reader:
                reader.execute('PRAGMA query_only=OFF')
                with self.assertRaises(sqlite3.OperationalError):
                    reader.execute("UPDATE runs SET status='failed'")
            self.assertEqual(before, list(self.db.iterdump()))
        finally:
            path.parent.chmod(parent_mode)
            for p, mode in prior.items():
                p.chmod(mode)

    def test_a15_reads_committed_wal_and_hides_uncommitted_then_observes_commit(self):
        self.start_run(self.db)
        self.db.execute('BEGIN IMMEDIATE')
        self.db.execute("UPDATE runs SET refresh_error='wal-committed-marker' WHERE run_id='run-a'")
        self.assertNotIn('wal-committed-marker', self.get('/controllers'))
        self.db.commit()
        self.assertIn('wal-committed-marker', self.get('/controllers'))
        self.assertGreater(Path(str(self.bound.experiment.notebook_path(self.root)) + '-wal').stat().st_size, 0)

    def test_a15_consistent_read_transaction_does_not_mix_commit_boundaries(self):
        self.start_run(self.db)
        from nnfx_practice import dashboard
        original = dashboard.account_report
        changed = False

        def interleave(reader, period):
            nonlocal changed
            result = original(reader, period)
            if not changed:
                changed = True
                self.db.execute("UPDATE runs SET refresh_error='later-commit' WHERE run_id='run-a'")
            return result

        with patch.object(dashboard, 'account_report', interleave):
            html = self.get('/controllers')
            self.assertNotIn('later-commit', html)
        self.assertIn('later-commit', self.get('/controllers'))

    def test_a15_escape_stored_text_and_show_issues_and_request_outcomes(self):
        self.register(trade_ids=(None, None), status='pending')
        self.db.execute("INSERT INTO issues(issue_id,pair,code,first_observed_at,last_observed_at,status) VALUES('issue','EUR-USD',?, ?, ?, 'open')", ('<script>alert(1)</script>', STAMP, STAMP))
        prepare_attempt(self.db, self.bound, attempt_id='unknown-attempt', run_id='run-a', stage='manage_new',
                        purpose='entry', method='POST', path='/orders', prepared_at=self.clock.now(),
                        pair='EUR-USD', set_id='set-a', leg_no=1)
        self.db.execute("UPDATE broker_attempts SET outcome='unknown',error='uncertain broker response' WHERE attempt_id='unknown-attempt'")
        html = self.get('/notebooks/notebook-a')
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('uncertain broker response', html)
        self.assertIn('Unconfirmed / planned', html)
        self.assertNotIn('<form', html)
        self.assertIn('&lt;script&gt;', self.get('/controllers'))

    def test_a16_independent_notebooks_do_not_mix_currency_totals_or_journals(self):
        other = self.notebook(self.other_bound)
        self.opening(other, balance='900', currency='EUR')
        self.close()
        first = self.get('/notebooks/notebook-a')
        second = self.get('/notebooks/notebook-b')
        self.assertIn('set-a', first)
        self.assertNotIn('set-a', second)
        self.assertIn('class="win">+900', second)
        self.assertIn('Balance (EUR)', second)
        self.assertNotIn('Balance (USD)', second)
        self.get('/notebooks')

    def test_a16_selected_manifest_displays_indicator_names_outputs_and_rules(self):
        self.write_registry(strategy_b='t3_bandpass_v1')
        source = Path(__file__).resolve().parents[1] / 'strategies/t3_bandpass_v1/manifest.json'
        target = self.root / 'strategies/t3_bandpass_v1/manifest.json'
        target.parent.mkdir()
        target.write_bytes(source.read_bytes())
        private = self.root / '.env'
        private.write_text(private.read_text().replace('PRACTICE_B_LOOKBACK_CANDLES=50', 'PRACTICE_B_LOOKBACK_CANDLES=386'))
        self.other_bound = self.binding('controller-b')
        other = self.notebook(self.other_bound)
        self.opening(other, currency='EUR')
        self.client = create_app(self.root, now=self.clock.now).test_client()
        for path in ('/notebooks', '/notebooks/notebook-b'):
            html = self.get(path)
            for text in ('STD-Adaptive T3 Channel', 'L2 Ehlers Bandpass Filter', 'goLong', 'goShort',
                         'longEntry', 'shortEntry', '386 candles', 'paired_directional_events', 'Rule a53e86e2'):
                self.assertIn(text, html)

    def test_a16_unknown_ids_paths_and_queries_cannot_select_a_database(self):
        for path in ('/notebooks/unknown', '/notebooks/..%2Fnotebook-a', '/notebooks/%2Ftmp%2Fnotebook-a'):
            self.assertEqual(self.client.get(path).status_code, 404)
        html = self.get('/notebooks/notebook-a?path=/tmp/other.sqlite3&action=activate')
        self.assertIn('Fixture A', html)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        self.assertFalse(Path('/tmp/other.sqlite3').exists())

    def test_a16_registry_binding_mismatch_is_unavailable_and_other_notebook_survives(self):
        other = self.notebook(self.other_bound)
        self.opening(other, currency='EUR')
        registry = self.root / 'config.toml'
        registry.write_text(registry.read_text().replace('strategy_version = "fixture-v1"', 'strategy_version = "changed"', 1))
        self.client = create_app(self.root, now=self.clock.now).test_client()
        self.assertIn('Notebook unavailable', self.get('/notebooks/notebook-a'))
        self.assertIn('Balance (EUR)', self.get('/notebooks/notebook-b'))

    def test_a16_registry_symlink_and_unknown_schema_never_write_or_migrate(self):
        self.db.execute('PRAGMA user_version=1')
        self.assertIn('Notebook unavailable', self.get('/notebooks/notebook-a'))
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0], 1)
        self.db.execute('PRAGMA user_version=2')
        path = self.root / 'var/notebooks/notebook-b.sqlite3'
        path.symlink_to(self.bound.experiment.notebook_path(self.root))
        with self.assertRaises(ValueError):
            create_app(self.root)


if __name__ == '__main__':
    import unittest
    unittest.main()
