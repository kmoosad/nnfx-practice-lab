"""A14–A16 dashboard checks. Every broker fact here is an offline fixture."""

from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch
from urllib.parse import urlencode

from nnfx_practice.broker import BrokerError
from nnfx_practice.config import PERMITTED_PAIRS
from nnfx_practice.dashboard import age, create_app, duration, latest_launch, ny_short, ny_time, read_run, read_view
from nnfx_practice.ledger import account_report
from nnfx_practice.notebook import finish_pair, open_readonly, prepare_attempt, utc_text
from nnfx_practice.reconciliation import import_through, reconcile_snapshot, record_confirmed_transactions

from .support import ACCOUNT, TOKEN, Call, NotebookCase
from . import test_m02 as m02
from .test_m02 import ROOT, STAMP, account, event, open_trade, order_fill, reply


class TradeRows(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.rows = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'tr' and attrs.get('class') == 'leg-summary':
            self.rows.append((attrs['data-set-id'], int(attrs['data-leg'])))


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

    def filtered(self, **args):
        return self.get('/notebooks/notebook-a?' + urlencode(args))

    def filter_fixture(self):
        self.register()
        self.metadata()
        self.register(set_id='finished-set', pair='GBP-USD', trade_ids=('60', '61'), run_id='run-b')
        self.metadata('GBP-USD')
        self.snapshot(account(103, '1030', trades=[open_trade(40, leg=1)]),
                      order_fill(101, 41, pl='10', reason='TAKE_PROFIT_ORDER'),
                      order_fill(102, 60, name='GBP_USD', pl='10'),
                      order_fill(103, 61, name='GBP_USD', pl='10'))
        self.register(set_id='pending-set', pair='USD-JPY', direction='short',
                      trade_ids=(None, None), status='pending', run_id='run-c')
        self.db.execute("INSERT INTO run_invocations VALUES ('run-a','qualification','{}')")
        self.db.execute("INSERT INTO run_invocations VALUES ('run-b','ordinary','{}')")
        self.db.execute("INSERT INTO run_invocations VALUES ('run-c','qualification','{}')")

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
        self.assertIn('Profit / loss (USD)', html)
        for column in ('Trade set ID', 'Broker trade ID', 'Pair / trade', 'Direction', 'Units: entry / current',
                       'Entry date/time', 'Trade status', 'Entry price', 'Original stop-loss', 'Stop-loss price',
                       'Take-profit price', 'Exit date/time', 'Exit price', 'Exit reason', 'Result (pips)',
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
        self.assertIn('Pip size not recorded', self.get('/notebooks/notebook-a'))

    def test_a14_missing_unrealised_result_stays_unavailable(self):
        self.close()
        self.db.execute("UPDATE account_snapshots SET unrealised_pl = NULL WHERE snapshot_id='snapshot'")
        self.assertIsNone(self.model()['report'].unrealised_pl)
        html = self.get('/notebooks/notebook-a')
        self.assertIn('Unrealised profit / loss (USD)</dt><dd><span class="">Unavailable', html)

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
        html = self.get('/notebooks/notebook-a')
        trade = html.split('class="leg-summary"', 1)[1].split('</tr>', 1)[0]
        self.assertIn('Not closed yet', trade)
        self.assertNotIn('class="win">+10', trade)
        final = order_fill(104, 40, units='600', price='1.11300', pl='100', reason='MARKET_ORDER_TRADE_CLOSE')
        final['time'] = '2026-11-16T21:50:01.123456789Z'
        self.snapshot(account(104, '1156'), final, cursor=103, name='final')
        leg = self.model()['journal'][0]
        self.assertEqual((leg['exit_price'], leg['pips'], leg['trading_pl'], leg['exit_at']),
                         ('1.10980', Decimal(98), Decimal(110), final['time']))
        self.assertEqual(len(leg['fills']), 2)
        html = self.get('/notebooks/notebook-a')
        self.assertIn('1.10980', html)
        self.assertIn('Trade breakdown only', html)
        self.assertIn('Account-level entry', html)
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
        self.assertIn('Newer than account update', html)
        self.assertIn('Refresh failed', html)
        self.assertIn('showing the last confirmed account figures', html)
        self.assertIn('<span>1,000.00</span>', html)
        self.assertIn('class="journal-disclosure ledger-records" open', html)
        overview = self.get('/notebooks')
        self.assertIn('Refresh failed', overview)
        self.assertIn('<span>1,000.00</span>', overview)
        self.assertNotIn('<span class="win">+100</span>', overview)
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
        self.assertIn('Newer than account update', html)
        self.assertIn('class="loss">-5', html)

    def test_a14_q0_plus_100_a0_then_ordinary_plus_20(self):
        self.register()
        self.metadata()
        self.db.execute("INSERT INTO run_invocations VALUES ('run-a','qualification','{}')")
        self.snapshot(account(101, '1100', trades=[open_trade(41)]), order_fill(101, 40, pl='100'), name='qual')
        html = self.get('/notebooks/notebook-a')
        self.assertIn('Ordinary trading has not been activated.', html)
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
        self.assertIn('Qualification results before activation', html)
        self.assertIn('Qualification starting record (Q0)</dt><dd>Account record q0 · Transaction 0100', html)
        self.assertIn('Ordinary trading starting record (A0)</dt><dd>Account record a0 · Transaction 102', html)
        self.assertIn('class="win">+20', html)
        overview = self.get('/notebooks')
        ordinary = overview.split('aria-label="Ordinary results"', 1)[1].split('</section>', 1)[0]
        qualification = overview.split('class="notebook-details qualification-history"', 1)[1].split('</details>', 1)[0]
        self.assertIn('<span class="win">+20</span>', ordinary)
        self.assertNotIn('<span class="win">+100</span>', ordinary)
        self.assertIn('<span class="win">+100</span>', qualification)
        self.assertNotIn('<span class="win">+20</span>', qualification)

    def test_notebook_overview_keeps_exact_neutral_balance_and_qualification_context(self):
        self.snapshot(account(101, '50000.1007'), event(101, 'TRANSFER_FUNDS', amount='49000.1007'))
        self.db.execute("INSERT INTO issues(issue_id,pair,code,first_observed_at,last_observed_at,status) VALUES('overview-issue','EUR-USD','missing_protection',?,?,'open')", (STAMP, STAMP))
        html = self.get('/notebooks')
        self.assertIn('<span>50,000.1007</span>', html)
        self.assertNotIn('+50,000.1007', html)
        self.assertNotIn('50,000.10<', html)
        self.assertIn('Ordinary trading has not been activated.', html)
        self.assertIn('These are qualification results.', html)
        self.assertIn('1 open issue', html)
        self.assertLess(html.index('1 open issue'), html.index('Qualification results'))
        self.assertEqual(self.model()['report'].balance, Decimal('50000.1007'))
        self.assertIsNone(self.model()['reports']['ordinary'])
        self.assertIn('Open trading journal', html)
        self.assertNotIn('<table', html)

    def test_journal_shows_all_sets_in_one_table_with_paired_legs_adjacent(self):
        self.register()
        self.metadata()
        self.register(set_id='finished-set', pair='GBP-USD', trade_ids=('60', '61'), run_id='run-b')
        self.metadata('GBP-USD')
        self.snapshot(account(103, '1030', trades=[open_trade(40, leg=1)]),
                      order_fill(101, 41, pl='10'),
                      order_fill(102, 60, name='GBP_USD', pl='10'),
                      order_fill(103, 61, name='GBP_USD', pl='10'))
        groups = self.model()['journal_groups']
        self.assertEqual([(g['set_id'], g['finished']) for g in groups],
                         [('finished-set', True), ('set-a', False)])
        self.assertEqual([[leg['leg_no'] for leg in g['legs']] for g in groups], [[1, 2], [1, 2]])
        self.assertEqual([leg['broker_state'] for leg in groups[1]['legs']], ['open', 'closed'])
        html = self.get('/notebooks/notebook-a')
        self.assertEqual(html.count('<table class="trade-table">'), 1)
        self.assertEqual(TradeRows(html).rows, [('finished-set', 1), ('finished-set', 2), ('set-a', 1), ('set-a', 2)])
        self.assertIn('Showing 4 of 4 trade records', html)
        self.assertNotIn('class="trade-set"', html)

    def test_journal_combines_filters_and_keeps_totals_and_filter_choices(self):
        self.filter_fixture()
        before = self.model()['report']
        html = self.filtered(pair='EUR-USD', status='closed', direction='long', period='Qualification',
                             entry_from='2026-11-16', entry_to='2026-11-16', q='SET-A eur-usd')
        self.assertEqual(TradeRows(html).rows, [('set-a', 2)])
        self.assertIn('Showing 1 of 6 trade records', html)
        self.assertIn('<option>GBP-USD</option>', html)
        self.assertIn('<span>1,030</span>', html)
        self.assertEqual(self.model()['report'], before)
        self.assertEqual(TradeRows(self.filtered(q='60')).rows, [('finished-set', 1)])
        self.assertEqual(TradeRows(self.filtered(q='take_profit_order')).rows, [('set-a', 2)])
        self.assertEqual(TradeRows(self.filtered(q='take-profit order')).rows, [('set-a', 2)])
        empty = self.filtered(pair='GBP-USD', direction='short')
        self.assertEqual(TradeRows(empty).rows, [])
        self.assertIn('No trade records match these filters.', empty)
        self.assertEqual(len(TradeRows(self.get('/notebooks/notebook-a')).rows), 6)

    def test_journal_filters_open_closed_not_opened_and_unconfirmed_individually(self):
        self.filter_fixture()
        self.db.execute("UPDATE trade_legs SET broker_state='not_opened' WHERE set_id='pending-set' AND leg_no=2")
        for status, expected in (
                ('open', [('set-a', 1)]),
                ('closed', [('finished-set', 1), ('finished-set', 2), ('set-a', 2)]),
                ('not_opened', [('pending-set', 2)]),
                ('unconfirmed', [('pending-set', 1)])):
            with self.subTest(status=status):
                self.assertEqual(TradeRows(self.filtered(status=status)).rows, expected)
        self.assertEqual(TradeRows(self.filtered(direction='short')).rows, [('pending-set', 1), ('pending-set', 2)])
        self.assertEqual(TradeRows(self.filtered(period='Ordinary')).rows, [('finished-set', 1), ('finished-set', 2)])

    def test_journal_entry_dates_use_new_york_days_and_validate_ranges(self):
        self.filter_fixture()
        self.db.execute("UPDATE trade_legs SET entry_at='2026-11-17T04:59:59Z' WHERE set_id='set-a' AND leg_no=1")
        self.db.execute("UPDATE trade_legs SET entry_at='2026-11-17T05:00:00Z' WHERE set_id='set-a' AND leg_no=2")
        html = self.filtered(entry_from='2026-11-16', entry_to='2026-11-16')
        self.assertEqual(TradeRows(html).rows, [('finished-set', 1), ('finished-set', 2), ('set-a', 1)])
        self.assertIn('<span class="trade-date">16 Nov 2026</span>', html)
        self.assertIn('<small class="trade-clock">23:59:59 EST -0500</small>', html)
        self.assertEqual(TradeRows(self.filtered(entry_from='2026-11-17', entry_to='2026-11-17')).rows, [('set-a', 2)])
        for query, message in ((dict(entry_from='bad'), 'Enter valid entry dates'),
                               (dict(entry_from='2026-11-17', entry_to='2026-11-16'), 'must be on or before'),
                               (dict(status='invalid'), 'Choose an available')):
            with self.subTest(query=query):
                html = self.filtered(**query)
                self.assertEqual(TradeRows(html).rows, [])
                self.assertIn(message, html)
        self.db.execute("UPDATE trade_legs SET entry_at='2026-07-01T03:59:59Z' WHERE set_id='set-a' AND leg_no=1")
        self.db.execute("UPDATE trade_legs SET entry_at='2026-07-01T04:00:00Z' WHERE set_id='set-a' AND leg_no=2")
        summer = self.filtered(entry_from='2026-06-30', entry_to='2026-06-30')
        self.assertEqual(TradeRows(summer).rows, [('set-a', 1)])
        self.assertIn('<span class="trade-date">30 Jun 2026</span>', summer)
        self.assertIn('<small class="trade-clock">23:59:59 EDT -0400</small>', summer)
        self.assertEqual(TradeRows(self.filtered(entry_from='2026-07-01', entry_to='2026-07-01')).rows, [('set-a', 2)])

    def test_journal_record_links_preserve_filters_and_stay_in_the_selected_notebook(self):
        self.filter_fixture()
        html = self.filtered(status='closed', record_set='set-a', record_leg='2')
        self.assertIn('id="trade-record"', html)
        self.assertIn('class="leg-records" open', html)
        self.assertIn('href="/notebooks/notebook-a?status=closed#trades">Hide trade details', html)
        self.assertEqual(TradeRows(html).rows, [('finished-set', 1), ('finished-set', 2), ('set-a', 2)])
        self.assertIn('Trade record unavailable in this notebook.', self.filtered(record_set='absent', record_leg='1'))
        self.opening(self.notebook(self.other_bound), currency='EUR')
        other = self.get('/notebooks/notebook-b?record_set=set-a&record_leg=2')
        self.assertIn('Trade record unavailable in this notebook.', other)
        self.assertNotIn('id="trade-record"', other)
        self.assertNotIn('TAKE_PROFIT_ORDER', other)

    def test_journal_search_is_escaped_and_only_reads_records(self):
        self.filter_fixture()
        before = self.db.total_changes
        html = self.filtered(q='<script>alert(1)</script>')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertEqual(TradeRows(html).rows, [])
        self.assertEqual(self.db.total_changes, before)

    def test_closed_protection_is_inactive_while_unconfirmed_open_targets_stay_visible(self):
        self.filter_fixture()
        self.db.execute("UPDATE trade_legs SET intended_target='1.12000',confirmed_target=NULL WHERE leg_no=1")
        html = self.get('/notebooks/notebook-a')
        rows = html.split('class="leg-summary"')[1:]
        closed = next(row.split('</tr>',1)[0] for row in rows if 'data-set-id="finished-set" data-leg="1"' in row)
        opened = next(row.split('</tr>',1)[0] for row in rows if 'data-set-id="set-a" data-leg="1"' in row)
        self.assertIn('Inactive (trade closed)', closed)
        self.assertIn('Planned 1.12000', closed)
        self.assertNotIn('(not confirmed)', closed)
        self.assertIn('Planned 1.12000 (not confirmed)', opened)
        detail = self.filtered(record_set='finished-set',record_leg='1').split('id="trade-record"',1)[1]
        detail = detail.split('</section>',1)[0]
        self.assertIn('Planned take-profit price</dt><dd>1.12000', detail)
        self.assertNotIn('(not confirmed)', detail)
        self.assertIn('Original stop-loss</dt><dd>1.09000', detail)

    def test_a14_missing_allocated_amounts_are_unavailable_not_zero(self):
        self.register(trade_ids=('40', None))
        self.metadata()
        close = order_fill(101, 40, price='1.11', pl='100')
        del close['tradesClosed'][0]['realizedPL']
        self.snapshot(account(101, '1100'), close)
        self.assertIsNone(self.model()['journal'][0]['trading_pl'])
        self.assertIn('Not recorded', self.get('/notebooks/notebook-a'))

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
        for expected in ('3 / 28 pairs checked', '1 with no entry · 1 failed', 'Check unfinished', 'NZD-USD', '4.3',
                         'Reconciliation:', 'due_stops', 'No open trades to manage', 'Unfinished', 'fixture failed'):
            self.assertIn(expected, html)
        # Missing exit inputs are not a successful hold or a new-entry outcome.
        self.db.execute("UPDATE pair_decisions SET stage='manage_open',reason='Indicator input unavailable; no eligible opposite event' WHERE pair='GBP-USD'")
        self.db.execute("UPDATE stages SET expected_pair_count=1 WHERE stage='manage_open'")
        html = self.get('/controllers')
        self.assertIn('1 / 1 pairs with open trades checked', html)
        self.assertIn('1 exit check unavailable · 0 failed', html)
        self.assertIn('Reason: Indicator input unavailable; no eligible opposite event', html)
        self.assertNotIn('No action required', html)

    def completed_no_entry_run(self, run_id='run-a', reason='No fresh C1 event with valid entry ATR'):
        self.start_run(self.db, run_id)
        self.db.execute("INSERT INTO run_invocations VALUES (?,'qualification','{}')", (run_id,))
        for order, pair in enumerate(PERMITTED_PAIRS, 1):
            self.add_decision(self.db, pair, order, run_id=run_id)
            finish_pair(self.db, self.bound, run_id=run_id, stage='manage_new', pair=pair,
                        ended_at=self.clock.now(), outcome='skipped', reason=reason)
        self.db.execute("UPDATE runs SET status='completed',ended_at=?,duration_seconds=14.112094281008467 WHERE run_id=?", (STAMP, run_id))
        self.db.execute("UPDATE stages SET status='completed',started_at=?,ended_at=?,duration_seconds=12.721595722949132 WHERE run_id=?", (STAMP, STAMP, run_id))
        self.db.execute("UPDATE stages SET expected_pair_count=0,duration_seconds=0.8197008711285889,reconciliation_progress_json=? WHERE run_id=? AND stage='manage_open'", ('{"snapshot_id":"q0","registered_sets":[],"stop_adjustments":[]}', run_id))

    def test_controller_no_entry_summary_keeps_exact_records_and_reconciled_state(self):
        self.completed_no_entry_run()
        run = self.model()['latest_run']
        self.assertTrue(run['no_new_entries'])
        self.assertFalse(run['needs_attention'])
        self.assertTrue(run['stages'][0]['reconciled'])
        html = self.get('/controllers')
        for text in ('No new entries', '28 / 28 pairs checked', '28 with no entry · 0 failed',
                     'Reason: No fresh C1 event with valid entry ATR', 'Account records matched to broker', '14.1 s',
                     '14.112094281008467 seconds', 'Last transaction included', 'Run and reconciliation details'):
            self.assertIn(text, html)
        self.assertEqual(html.count('Latest run ·'), 1)
        self.assertNotIn('<table', html)
        self.assertLess(html.index('Account data updated'), html.index('Latest run ·'))
        self.assertLess(html.index('Latest run ·'), html.index('Run ID'))

    def test_controller_skips_do_not_invent_a_signal_reason_or_hide_uncertain_entry(self):
        self.completed_no_entry_run(reason='Pair is occupied or blocked')
        html = self.get('/controllers')
        self.assertIn('Pair is occupied or blocked', html)
        self.assertNotIn('No fresh C1', html)
        # A reserved or unresolved set means the page cannot assert no new entry.
        self.register(set_id='uncertain-set', pair='EUR-USD', trade_ids=(None, None), status='pending', run_id='run-b')
        self.db.execute("UPDATE trade_sets SET run_id='run-a' WHERE set_id='uncertain-set'")
        self.assertFalse(read_run(self.root, self.bound.experiment, 'run-a')['run']['no_new_entries'])
        self.assertNotIn('No new entries', self.get('/controllers'))

    def test_controller_incomplete_pairs_and_unconfirmed_reconciliation_stay_explicit(self):
        self.completed_no_entry_run()
        self.db.execute("UPDATE pair_decisions SET outcome=NULL,ended_at=NULL WHERE pair='EUR-USD'")
        self.db.execute("UPDATE stages SET reconciliation_progress_json='{}' WHERE stage='manage_open'")
        run = self.model()['latest_run']
        self.assertFalse(run['no_new_entries'])
        self.assertTrue(run['needs_attention'])
        self.assertFalse(run['stages'][0]['reconciled'])
        html = self.get('/controllers')
        for text in ('27 / 28 pairs checked', 'Account reconciliation unconfirmed', 'EUR-USD · Check unfinished'):
            self.assertIn(text, html)
        self.assertNotIn('run-success">Completed', html)

    def test_controller_old_problem_runs_expand_and_completed_history_collapses(self):
        self.start_run(self.db, 'interrupted')
        html = self.get('/controllers')
        self.assertIn('Previous run history (0)', html)
        self.assertIn('No previous runs recorded.', html)
        self.clock.advance(1)
        self.completed_no_entry_run('latest')
        html = self.get('/controllers')
        self.assertIn('Previous run history (1)', html)
        self.assertLess(html.index('Run and reconciliation details'), html.index('Previous run history'))
        self.assertLess(html.index('Previous run history'), html.index('Account data details'))
        self.assertEqual(html.count('<dd>latest</dd>'), 1)
        self.assertNotIn('<dd>interrupted</dd>', html)
        self.assertIn('href="/controllers/controller-a/runs/interrupted" target="_blank" rel="noopener noreferrer"', html)
        self.assertIn('<details class="run-history" open>', html)
        self.assertIn('Running · Unfinished', html)
        self.db.execute("UPDATE runs SET status='failed',ended_at=?,refresh_error='old-refresh-failure' WHERE run_id='interrupted'", (STAMP,))
        html = self.get('/controllers')
        self.assertIn('<details class="run-history" open>', html)
        self.assertNotIn('old-refresh-failure', html)
        self.assertIn('Refresh failed', html)
        self.assertIn('old-refresh-failure', self.get('/controllers/controller-a/runs/interrupted'))
        self.db.execute("UPDATE runs SET status='completed',refresh_error=NULL WHERE run_id='interrupted'")
        self.db.execute("UPDATE stages SET status='completed',ended_at=? WHERE run_id='interrupted'", (STAMP,))
        self.assertIn('<details class="run-history">', self.get('/controllers'))

    def test_controller_history_details_are_read_only_when_selected(self):
        self.completed_no_entry_run('older', reason='older-skip-detail')
        self.db.execute("UPDATE stages SET reconciliation_progress_json=? WHERE run_id='older' AND stage='manage_open'", ('{"snapshot_id":"q0","detail":"older-reconciliation-detail"}',))
        self.clock.advance(1)
        self.completed_no_entry_run('latest')
        queries = []

        @contextmanager
        def traced_reader(root, experiment):
            with open_readonly(root, experiment) as db:
                db.set_trace_callback(queries.append)
                yield db

        with patch('nnfx_practice.dashboard.open_readonly', side_effect=traced_reader):
            html = self.get('/controllers')
        self.assertNotIn('older-skip-detail', html)
        self.assertNotIn('older-reconciliation-detail', html)
        self.assertNotIn('stages', self.model()['runs'][1])
        detail_queries = [q for q in queries if 'reconciliation_progress_json' in q or 'SELECT reason, count(*)' in q]
        self.assertTrue(detail_queries)
        self.assertTrue(all("'latest'" in q and "'older'" not in q for q in detail_queries))
        queries.clear()
        with patch('nnfx_practice.dashboard.open_readonly', side_effect=traced_reader):
            html = self.get('/controllers/controller-a/runs/older')
        self.assertIn('older-skip-detail', html)
        self.assertIn('older-reconciliation-detail', html)
        self.assertIn('<dd>older</dd>', html)
        self.assertNotIn('<dd>latest</dd>', html)
        self.assertNotIn('Previous run history', html)
        self.assertFalse(any("'latest'" in q for q in queries))
        self.assertEqual(self.client.get('/controllers/controller-a/runs/older').headers['Cache-Control'], 'no-store')

    def test_controller_run_links_remain_bound_to_the_registered_notebook(self):
        self.completed_no_entry_run('run-a')
        absent = self.root / 'var/notebooks/notebook-b.sqlite3'
        self.assertFalse(absent.exists())
        response = self.client.get('/controllers/controller-b/runs/run-a')
        self.assertEqual(response.status_code, 503)
        self.assertIn(b'Notebook unavailable', response.data)
        self.assertFalse(absent.exists())
        other = self.notebook(self.other_bound)
        self.opening(other)
        self.start_run(other, 'foreign-only')
        for path in ('/controllers/unknown/runs/run-a', '/controllers/controller-a/runs/foreign-only',
                     '/controllers/controller-a/runs/unknown', '/controllers/controller-a/runs/..%2Frun-a',
                     '/controllers/controller-a/runs/run-a%27%20OR%201=1--'):
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.db.execute("UPDATE pair_decisions SET reason='<script>history-xss</script>' WHERE run_id='run-a'")
        html = self.get('/controllers/controller-a/runs/run-a?path=/tmp/other.sqlite3')
        self.assertIn('&lt;script&gt;history-xss&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('foreign-only', html)

    def test_controller_open_issues_and_failed_refresh_precede_latest_run(self):
        self.completed_no_entry_run()
        self.db.execute("INSERT INTO issues(issue_id,pair,code,first_observed_at,last_observed_at,status) VALUES('layout-issue','EUR-USD','missing_protection',?,?,'open')", (STAMP, STAMP))
        self.db.execute("UPDATE runs SET refresh_error='final-refresh-failed' WHERE run_id='run-a'")
        html = self.get('/controllers')
        self.assertLess(html.index('missing_protection'), html.index('Latest run ·'))
        self.assertLess(html.index('Final account update failed:'), html.index('Latest run ·'))
        self.assertNotIn('No recorded issues.', html)
        self.db.execute("UPDATE issues SET status='resolved',resolved_at=?", (STAMP,))
        html = self.get('/controllers')
        self.assertIn('No open issues.', html)
        self.assertIn('Resolved issues (1)', html)
        self.assertIn('layout-issue', html)

    def test_controller_readable_times_keep_new_york_dst_and_exact_values(self):
        self.assertEqual(ny_short('2026-03-09T20:50:00.123456789Z'), '09 Mar 2026 · 16:50:00 EDT -0400')
        self.assertEqual(ny_short('2026-11-19T21:50:15.315793Z'), '19 Nov 2026 · 16:50:15 EST -0500')
        self.assertEqual(ny_short(None), 'Unavailable')
        self.assertEqual(duration(None), 'Unavailable')
        self.assertEqual(duration(0.02), '<0.1 s')
        stamp = utc_text(self.clock.now())
        self.clock.advance(1)
        self.assertEqual(age(stamp, self.clock.now(), compact=True), '1s')
        self.clock.advance(5 * 3600 + 48 * 60)
        self.assertEqual(age(stamp, self.clock.now(), compact=True), '5h 48m')
        self.assertIn('48m 1s', age(stamp, self.clock.now()))

    def test_a15_completed_failed_and_unfinished_runs_remain_visible(self):
        for i, state in enumerate(('completed', 'failed', 'completed_with_errors', 'running')):
            self.start_run(self.db, f'run-{i}')
            if state != 'running':
                self.db.execute('UPDATE runs SET status=?,ended_at=?,duration_seconds=12.5,refresh_error=? WHERE run_id=?',
                                (state, STAMP, 'unavailable refresh' if state == 'failed' else None, f'run-{i}'))
        html = self.get('/controllers')
        for state in ('Completed', 'Failed', 'Completed with errors', 'Unfinished', '12.5 s', 'Refresh failed'):
            self.assertIn(state, html)
        self.assertIn('unavailable refresh', self.get('/controllers/controller-a/runs/run-1'))

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
        self.assertIn('Account data may be out of date:', html)
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
        self.start_run(self.db)
        (self.root / '.env').unlink()
        with patch('nnfx_practice.config.read_private_settings', side_effect=AssertionError('private read')), \
             patch('nnfx_practice.broker.PracticeBroker.__init__', side_effect=AssertionError('broker created')), \
             patch('nnfx_practice.master.run_master', side_effect=AssertionError('master called')), \
             patch('socket.socket.connect', side_effect=AssertionError('network')):
            self.client = create_app(self.root, now=self.clock.now).test_client()
            for path in ('/controllers', '/controllers/controller-a/runs/run-a', '/notebooks', '/notebooks/notebook-a',
                         '/notebooks/notebook-a?status=closed&record_set=absent&record_leg=1'):
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
            for route in ('/controllers', '/controllers/controller-a/runs/run-a', '/notebooks', '/notebooks/notebook-a'):
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
        self.assertIn('Unconfirmed', html)
        self.assertFalse(self.model()['journal_groups'][0]['finished'])
        self.assertIn('class="journal-disclosure request-records" open', html)
        self.assertIn('<form class="trade-filters" method="get"', html)
        self.assertNotIn('method="post"', html)
        self.assertIn('&lt;script&gt;', self.get('/controllers'))

    def test_a16_independent_notebooks_do_not_mix_currency_totals_or_journals(self):
        other = self.notebook(self.other_bound)
        self.opening(other, balance='900', currency='EUR')
        self.close()
        first = self.get('/notebooks/notebook-a')
        second = self.get('/notebooks/notebook-b')
        self.assertIn('set-a', first)
        self.assertNotIn('set-a', second)
        self.assertIn('<span>900</span>', second)
        self.assertIn('Account balance (EUR)', second)
        self.assertNotIn('Account balance (USD)', second)
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
        self.assertIn('Account balance (EUR)', self.get('/notebooks/notebook-b'))

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
