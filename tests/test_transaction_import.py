"""Offline field-aware reconciliation, accounting and source-evidence regressions."""

from copy import deepcopy
from decimal import Decimal
import json
from unittest.mock import patch

from nnfx_practice.broker import BrokerError
from nnfx_practice.ledger import account_report
from nnfx_practice.notebook import SCHEMA_VERSION, open_notebook, open_readonly
from nnfx_practice.reconciliation import import_through, record_confirmed_transactions
from nnfx_practice.qualification_review import record_tables
from . import test_m02 as m02
from .support import Call, Interrupted, NotebookCase
from .test_m02 import ROOT, account, event, history, order_fill, reply


class TransactionImportChecks(NotebookCase):
    opening = m02.ReconciliationChecks.opening
    script = m02.ReconciliationChecks.script
    snapshot = m02.ReconciliationChecks.snapshot
    cursor = m02.ReconciliationChecks.cursor
    register = m02.ReconciliationChecks.register

    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.db = self.notebook(self.bound)
        self.opening(self.db)

    def save(self, *bodies):
        record_confirmed_transactions(self.db, self.script(), bodies)

    def rows(self, table):
        return [tuple(row) for row in self.db.execute('SELECT * FROM ' + table)]

    def observations(self, identifier):
        return [json.loads(row[0]) for row in self.db.execute(
            'SELECT body_json FROM broker_transaction_observations WHERE transaction_id=?', (str(identifier),))]

    def test_numeric_spellings_and_zero_costs_for_open_reduce_and_close(self):
        for identifier, effect, key in ((101, 'open', 'tradeOpened'), (102, 'reduce', 'tradeReduced'),
                                         (103, 'close', 'tradesClosed')):
            with self.subTest(effect=effect):
                original = order_fill(identifier, 40, effect=effect, units='200', pl='0', commission='0.00')
                self.save(original)
                expanded = deepcopy(original)
                expanded['commission'] = '0.000000'
                expanded['price'] = '1.0100'
                expanded['plHomeConversionCost'] = '0.0000'
                detail = expanded[key][0] if effect == 'close' else expanded[key]
                detail.update(units='200.000', price='1.1000000', guaranteedExecutionFeeHomeConversionCost='0.000')
                before = deepcopy(expanded)
                ledger, fills = self.rows('ledger_entries'), self.rows('fills')
                self.save(expanded)
                self.save(original)
                self.save(expanded)
                self.assertEqual(expanded, before)
                self.assertEqual(self.rows('ledger_entries'), ledger)
                self.assertEqual(self.rows('fills'), fills)
                self.assertEqual(len(self.observations(identifier)), 2)
                for source in (original, expanded):
                    self.assertIn({k:v for k,v in source.items() if k != 'accountID'}, self.observations(identifier))

    def test_metadata_additions_are_retained_without_becoming_account_charges(self):
        original = order_fill(101, 40, effect='open')
        original['tradeOpened']['clientExtensions'] = {'id': 'same-client'}
        self.save(original)
        expanded = deepcopy(original)
        expanded['halfSpreadCost'] = '2.50'
        expanded['tradeOpened'].update(halfSpreadCost='2.50', initialMarginRequired='50.00')
        expanded['tradeOpened']['clientExtensions'].update(tag='experiment', comment='broker note')
        before = self.rows('ledger_entries')
        self.save(expanded)
        self.save(original)
        merged = json.loads(self.db.execute('SELECT body_json FROM broker_transactions').fetchone()[0])
        self.assertEqual(merged['tradeOpened']['clientExtensions']['comment'], 'broker note')
        self.assertEqual(merged['halfSpreadCost'], '2.50')
        self.assertEqual(self.rows('ledger_entries'), before)
        self.assertEqual(len(self.observations(101)), 2)

    def test_nested_known_numbers_are_normalized_without_relaxing_client_ids(self):
        original = order_fill(101, 40, effect='open',
            fullPrice={'closeoutBid':'1.0', 'bids':[{'price':'1.00', 'liquidity':'200'}]},
            homeConversionFactors={'gainQuoteHome':{'factor':'1.00'}})
        original['tradeOpened']['clientExtensions'] = {'id':'001'}
        self.save(original)
        equivalent = deepcopy(original)
        equivalent['fullPrice'] = {'closeoutBid':'1.000', 'bids':[{'price':'1.0000', 'liquidity':'200.00'}]}
        equivalent['homeConversionFactors']['gainQuoteHome']['factor'] = '1.000000'
        self.save(equivalent)
        equivalent['tradeOpened']['clientExtensions']['id'] = '1'
        with self.assertRaises(BrokerError):
            self.save(equivalent)
        self.assertEqual(len(self.observations(101)), 2)

    def test_new_commission_reconciles_once_before_history_is_complete(self):
        self.register(trade_ids=('40', None))
        complete = order_fill(101, 40, pl='10', commission='2', accountBalance='1008')
        sparse = {key:value for key,value in complete.items() if key != 'commission'}
        self.save(sparse)
        self.snapshot(account(101, '1008'), complete)
        self.save(sparse, complete)
        report = account_report(self.db, 'qualification')
        self.assertEqual((report.balance, report.realised_profit, report.commission),
                         (Decimal('1008'), Decimal('10'), Decimal('-2')))
        self.assertEqual(self.db.execute("SELECT count(*) FROM ledger_entries WHERE component_key='commission'").fetchone()[0], 1)
        self.assertEqual(len(self.observations(101)), 2)

    def test_new_charge_with_unexplained_balance_rolls_back_the_whole_import(self):
        self.register(trade_ids=('40', None))
        sparse = order_fill(101, 40, pl='10', accountBalance='1008')
        del sparse['commission']
        self.save(sparse)
        before = {name:self.rows(name) for name in ('broker_transactions', 'broker_transaction_observations', 'ledger_entries', 'fills')}
        with self.assertRaisesRegex(BrokerError, 'Unexplained broker transaction balance'):
            self.snapshot(account(101, '1008'), {**sparse, 'commission': '3'})
        self.assertEqual(self.cursor(), '0100')
        for name, rows in before.items():
            self.assertEqual(self.rows(name), rows)
        self.assertEqual(account_report(self.db, 'qualification').snapshot_id, 'q0')

    def test_new_nonzero_charge_without_balance_evidence_is_not_assumed_safe(self):
        sparse = order_fill(101, 40)
        del sparse['commission']
        self.save(sparse)
        with self.assertRaisesRegex(BrokerError, 'lacks broker balance evidence'):
            self.save({**sparse, 'commission': '2'})
        self.assertEqual(len(self.observations(101)), 1)
        self.assertFalse(self.db.execute("SELECT 1 FROM ledger_entries WHERE component_key='commission'").fetchone())

    def test_compatible_variants_in_one_history_page_retain_both_sources(self):
        self.register(trade_ids=('40', None))
        original = order_fill(101, 40, pl='10', commission='0.00', accountBalance='1010')
        expanded = deepcopy(original)
        expanded['commission'] = '0.000'
        expanded['tradesClosed'][0]['plHomeConversionCost'] = '0.0000'
        self.snapshot(account(101, '1010'), original, expanded)
        self.assertEqual(len(self.observations(101)), 2)
        self.assertEqual(len(self.rows('fills')), 1)
        self.assertEqual(account_report(self.db, 'qualification').realised_profit, Decimal('10'))

    def test_late_nonzero_charge_cannot_rewrite_a_reconciled_snapshot(self):
        self.register(trade_ids=('40', None))
        sparse = order_fill(101, 40, pl='10', accountBalance='1010')
        del sparse['commission']
        self.snapshot(account(101, '1010'), sparse)
        before = {name:self.rows(name) for name in ('broker_transactions', 'broker_transaction_observations', 'ledger_entries')}
        with self.assertRaisesRegex(BrokerError, 'already imported history'):
            self.save({**sparse, 'commission': '2'})
        for name, rows in before.items():
            self.assertEqual(self.rows(name), rows)
        self.assertEqual(account_report(self.db, 'qualification').balance, Decimal('1010'))
        self.assertEqual(self.cursor(), '101')

    def test_later_trade_allocation_does_not_post_the_account_profit_twice(self):
        self.register(trade_ids=('40', None))
        sparse = order_fill(101, 40, pl='10', accountBalance='1010')
        del sparse['tradesClosed'][0]['realizedPL']
        self.snapshot(account(101, '1010'), sparse)
        expanded = deepcopy(sparse)
        expanded['tradesClosed'][0]['realizedPL'] = '10'
        self.save(expanded)
        self.save(sparse)
        report = account_report(self.db, 'qualification')
        self.assertEqual(report.realised_profit, Decimal('10'))
        allocation = self.db.execute("SELECT amount,posted FROM ledger_entries WHERE component_key='close.40.realizedPL'").fetchall()
        self.assertEqual([tuple(row) for row in allocation], [('10', 0)])

    def test_added_trade_allocation_requires_consistent_account_total(self):
        sparse = order_fill(101, 40, pl='10', accountBalance='1010')
        del sparse['tradesClosed'][0]['realizedPL']
        del sparse['commission']
        self.save(sparse)
        for field, value in (('realizedPL', '12'), ('commission', '2')):
            expanded = deepcopy(sparse)
            expanded['tradesClosed'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(BrokerError, 'matching transaction total'):
                self.save(expanded)
        self.assertEqual(len(self.observations(101)), 1)
        self.assertFalse(self.db.execute("SELECT 1 FROM ledger_entries WHERE component_key='close.40.realizedPL'").fetchone())
        first = order_fill(102, 41, pl='10', accountBalance='1010')
        del first['tradesClosed'][0]['realizedPL']
        conflicting = deepcopy(first)
        conflicting['tradesClosed'][0]['realizedPL'] = '12'
        with self.assertRaisesRegex(BrokerError, 'matching transaction total'):
            self.save(first, conflicting)
        self.assertEqual(self.observations(102), [])

    def test_reducing_then_closing_uses_enriched_history_without_repeating_effects(self):
        self.register(trade_ids=('40', None))
        reduction = order_fill(101, 40, effect='reduce', units='200', pl='2', accountBalance='1002')
        self.save(reduction)
        enriched = deepcopy(reduction)
        enriched['tradeReduced']['plHomeConversionCost'] = '0.000'
        broker = self.script((Call('GET', ROOT + '/transactions/sinceid?id=100'), reply(history(101, enriched))))
        import_through(self.db, broker, '101')
        self.assertEqual(self.db.execute('SELECT current_units FROM trade_legs WHERE leg_no=1').fetchone()[0], '800')
        close = order_fill(102, 40, units='800', pl='8', accountBalance='1010')
        self.save(close)
        expanded = deepcopy(close)
        expanded['tradesClosed'][0]['plHomeConversionCost'] = '0.0000'
        self.snapshot(account(102, '1010'), expanded, cursor=101)
        self.save(reduction, enriched, close, expanded)
        leg = self.db.execute('SELECT current_units,broker_state,exit_price FROM trade_legs WHERE leg_no=1').fetchone()
        self.assertEqual(tuple(leg), ('0', 'closed', '1.10000'))
        self.assertEqual(len(self.rows('fills')), 2)
        self.assertEqual(account_report(self.db, 'qualification').realised_profit, Decimal('10'))

    def test_closed_trade_list_matches_by_id_and_rejects_changed_membership(self):
        fill = order_fill(101, 40, units='100')
        fill['tradesClosed'].append(dict(fill['tradesClosed'][0], tradeID='41'))
        self.save(fill)
        reordered = deepcopy(fill)
        reordered['tradesClosed'].reverse()
        reordered['tradesClosed'][0]['units'] = '100.00'
        self.save(reordered)
        self.assertEqual(len(self.rows('fills')), 2)
        for bad in (fill['tradesClosed'][:1], [fill['tradesClosed'][0]] * 2):
            with self.subTest(bad=bad), self.assertRaises(BrokerError):
                self.save({**fill, 'tradesClosed': bad})

    def test_protection_price_formatting_is_equivalent_but_level_changes_fail(self):
        self.register()
        stop = event(101, 'STOP_LOSS_ORDER', tradeID='40', price='1.09000', timeInForce='GTC')
        self.save(stop)
        self.save({**stop, 'price': '1.090000'})
        self.assertEqual(self.db.execute('SELECT current_stop FROM trade_legs WHERE leg_no=1').fetchone()[0], '1.09000')
        for change in ({'price': '1.08000'}, {'tradeID': '41'}, {'timeInForce': 'GTD'}):
            with self.subTest(change=change), self.assertRaises(BrokerError):
                self.save({**stop, **change})

    def test_missing_core_or_unknown_financial_fields_remain_conflicts(self):
        original = order_fill(101, 40, effect='open')
        self.save(original)
        for key in ('orderID', 'instrument', 'reason', 'requestID', 'tradeOpened'):
            bad = {name:value for name,value in original.items() if name != key}
            with self.subTest(key=key), self.assertRaises(BrokerError):
                self.save(bad)
        for value in ('1.00', '0.00', None):
            with self.subTest(value=value), self.assertRaises(BrokerError):
                self.save({**original, 'unknownCharge': value})
        self.assertEqual(len(self.observations(101)), 1)

    def test_schema_two_migration_retains_sources_and_rolls_back_on_interruption(self):
        original = event(101, 'TRANSFER_FUNDS', amount='20')
        self.save(original)
        before = {name:self.rows(name) for name in ('notebook', 'broker_transactions', 'ledger_entries', 'issues')}
        self.db.execute('DROP TABLE broker_transaction_observations')
        self.db.execute('PRAGMA user_version=2')
        with open_readonly(self.root, self.bound.experiment) as reader:
            self.assertNotIn('broker_transaction_observations', record_tables(reader))
        from nnfx_practice import notebook
        original_script = notebook._schema_script
        def interrupted(db, name):
            original_script(db, name)
            if name == 'schema_transactions.sql':
                raise Interrupted()
        with patch.object(notebook, '_schema_script', interrupted), self.assertRaises(Interrupted):
            with open_notebook(self.root, self.bound):
                pass
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0], 2)
        self.assertFalse(self.db.execute("SELECT 1 FROM sqlite_schema WHERE name='broker_transaction_observations'").fetchone())
        with open_notebook(self.root, self.bound) as upgraded:
            self.assertEqual(upgraded.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
        for name, rows in before.items():
            self.assertEqual(self.rows(name), rows)
        self.assertEqual(self.observations(101), [{k:v for k,v in original.items() if k != 'accountID'}])
        with open_notebook(self.root, self.bound):
            pass
        self.assertEqual(len(self.observations(101)), 1)
