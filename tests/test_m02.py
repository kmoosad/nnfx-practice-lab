"""M02 acceptance checks using account-scoped, broker-shaped fixtures only."""

from copy import deepcopy
from decimal import Decimal
from http.client import HTTPException
import json
import sqlite3
from unittest.mock import Mock, call, patch

from nnfx_practice.broker import BrokerError, HTTPReply, PRACTICE_HOST, PracticeBroker
from nnfx_practice.config import ConfigurationError
from nnfx_practice.ledger import account_report, trade_journal
from nnfx_practice.notebook import open_readonly, pair_is_available, prepare_attempt, reserve_set, transaction, utc_text
from nnfx_practice.reconciliation import import_through, reconcile_snapshot, record_confirmed_transactions

from .support import ACCOUNT, TOKEN, Call, Interrupted, NotebookCase, ScriptedTransport, interrupt_commit


STAMP = "2026-11-16T21:50:00.123456789Z"
ROOT = f"/v3/accounts/{ACCOUNT}"


def reply(body, status=200, request_id="fixture-request-id"):
    return HTTPReply(status, body, request_id)


def account(boundary, balance="1000.00", *, account_id=ACCOUNT, currency="USD", trades=(), orders=(), unrealised="0"):
    return {
        "lastTransactionID": str(boundary),
        "account": {"id": account_id, "currency": currency, "balance": balance, "unrealizedPL": unrealised,
                    "marginUsed": "1.00", "marginAvailable": "900.00", "trades": list(trades), "orders": list(orders)},
    }


def event(identifier, kind, **data):
    return {"id": str(identifier), "type": kind, "time": STAMP, "accountID": ACCOUNT,
            "batchID": str(identifier), "requestID": f"request-{identifier}", **data}


def order_fill(identifier, trade_id, *, units="1000", price="1.10000", pl="0", reason="STOP_LOSS_ORDER",
               effect="close", financing="0", commission="0", fee="0", name="EUR_USD", order_id=None, **details):
    detail = {"tradeID": str(trade_id), "units": units, "price": price, "realizedPL": pl,
              "financing": financing, "guaranteedExecutionFee": fee}
    key, value = {
        "open": ("tradeOpened", detail), "reduce": ("tradeReduced", detail), "close": ("tradesClosed", [detail]),
    }[effect]
    return event(identifier, "ORDER_FILL", orderID=str(order_id if order_id is not None else identifier - 1),
                 instrument=name, reason=reason, price="1.01000", pl=pl, financing=financing, commission=commission,
                 guaranteedExecutionFee=fee, **{key: value}, **details)


def open_trade(trade_id, *, units="1000", initial="1000", name="EUR_USD", price="1.10000", leg=2,
               stop_id="51", stop_price="1.09000"):
    trade = {"id": str(trade_id), "instrument": name, "state": "OPEN", "initialUnits": initial,
             "currentUnits": units, "price": price, "openTime": STAMP,
             "stopLossOrder": protection(stop_id, trade_id, "STOP_LOSS", stop_price)}
    if leg == 1:
        trade["takeProfitOrder"] = protection("52", trade_id, "TAKE_PROFIT", "1.12000")
    return trade


def protection(order_id, trade_id, kind, price, **data):
    return {"id": str(order_id), "tradeID": str(trade_id), "type": kind, "state": "PENDING", "price": price, **data}


def history(boundary, *records):
    return {"lastTransactionID": str(boundary), "transactions": list(records)}


def with_zero_conversion_costs(fill):
    """History-only fields observed on Python 01 fill 2251 (20 Nov 2026)."""
    result = deepcopy(fill)
    result.update(baseFinancingHomeConversionCost="0.0000000",
                  guaranteedExecutionFeeHomeConversionCost="0.00000000000000",
                  homeConversionCost="0.00000000000000", plHomeConversionCost="0.00000000000000")
    result["tradeOpened"]["guaranteedExecutionFeeHomeConversionCost"] = "0.00000000000000"
    return result


class BrokerReads(NotebookCase):
    def test_a16_exact_account_scoped_read_paths_and_daily_parameters(self):
        bound = self.binding()
        scripted = ScriptedTransport(
            (Call("GET", ROOT), reply(account(100))),
            (Call("GET", ROOT + "/summary"), reply(account(100))),
            (Call("GET", ROOT + "/instruments?instruments=EUR_USD%2CUSD_JPY"),
             reply({"instruments": [{"name": "EUR_USD", "pipLocation": -4}]})),
            (Call("GET", ROOT + "/pricing?instruments=EUR_USD&includeHomeConversions=true"),
             reply({"prices": [{"instrument": "EUR_USD", "tradeable": True}], "homeConversions": []})),
            (Call("GET", ROOT + "/instruments/EUR_USD/candles?price=M&granularity=D&count=50"
                                "&smooth=false&dailyAlignment=17&alignmentTimezone=America%2FNew_York"),
             reply({"instrument": "EUR_USD", "granularity": "D", "candles": []})),
            (Call("GET", ROOT + "/trades/10"), reply({"trade": {"id": "10", "state": "CLOSED"}})),
            (Call("GET", ROOT + "/orders/20"), reply({"order": {"id": "20", "state": "CANCELLED"}})),
            (Call("GET", ROOT + "/transactions/30"), reply({"transaction": event(30, "ORDER_CANCEL", orderID="20")})),
        )
        broker = PracticeBroker(bound, transport=scripted, now=self.clock.now)
        self.assertEqual(broker.account().boundary, "100")
        self.assertEqual(broker.summary().evidence()["path"], "/summary")
        self.assertEqual(broker.instruments(["EUR-USD", "USD-JPY"]).body["instruments"][0]["pipLocation"], -4)
        self.assertTrue(broker.pricing("EUR-USD").body["prices"][0]["tradeable"])
        self.assertEqual(broker.candles("EUR-USD").body["granularity"], "D")
        self.assertEqual(broker.trade("10").body["trade"]["state"], "CLOSED")
        self.assertEqual(broker.order("20").body["order"]["state"], "CANCELLED")
        self.assertEqual(broker.transaction("30").body["transaction"]["orderID"], "20")
        with self.assertRaises(ValueError):
            broker.trade("10/close")
        scripted.assert_consumed()

    def test_a12_connection_reuse_timeouts_redirects_and_private_errors(self):
        bound = self.binding()
        conn = Mock()
        conn.sock = None
        socket = Mock()
        conn.connect.side_effect = lambda: setattr(conn, "sock", socket)
        first = Mock(status=200)
        first.read.return_value = json.dumps(account(100)).encode()
        first.getheader.return_value = "read-1"
        redirect = Mock(status=302)
        redirect.read.return_value = json.dumps({"url": f"https://elsewhere/{ACCOUNT}", "token": TOKEN}).encode()
        redirect.getheader.return_value = "read-2"
        conn.getresponse.side_effect = (first, redirect, TimeoutError(TOKEN), HTTPException(ACCOUNT))
        with patch("nnfx_practice.broker.HTTPSConnection", return_value=conn) as factory:
            with PracticeBroker(bound, now=self.clock.now, connect_timeout=3, read_timeout=7) as broker:
                self.assertEqual(broker.account().request_id, "read-1")
                with self.assertRaises(BrokerError) as error:
                    broker.summary()
                self.assertEqual(error.exception.status, 302)
                self.assertNotIn(ACCOUNT, repr(error.exception.evidence))
                self.assertNotIn(TOKEN, repr(error.exception.evidence))
                self.assertEqual(conn.connect.call_count, 1)
                self.assertEqual(socket.settimeout.call_args_list, [call(7), call(7)])
                self.assertEqual(conn.request.call_args_list, [
                    call("GET", ROOT, headers={"Authorization": f"Bearer {TOKEN}"}),
                    call("GET", ROOT + "/summary", headers={"Authorization": f"Bearer {TOKEN}"}),
                ])
                for _ in range(2):
                    with self.assertRaisesRegex(BrokerError, "connection or read failed") as failure:
                        broker.account()
                    self.assertNotIn(TOKEN, repr(failure.exception.evidence))
                    self.assertIsNone(failure.exception.evidence["http_status"])
        factory.assert_called_once_with(PRACTICE_HOST, timeout=3)
        self.assertEqual(conn.close.call_count, 3)


class ReconciliationChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.db = self.notebook(self.bound)
        self.opening(self.db)

    def opening(self, db, *, boundary="0100", balance="1000.00", currency="USD"):
        with transaction(db):
            db.execute("""
                INSERT INTO account_snapshots (snapshot_id, purpose, requested_at, responded_at, last_transaction_id,
                    balance, unrealised_pl, home_currency, reconciliation_status)
                VALUES ('q0', 'qualification', ?, ?, ?, ?, '0', ?, 'reconciled')
            """, (STAMP, STAMP, boundary, balance, currency))
            db.execute("""
                UPDATE notebook SET qualification_snapshot_id = 'q0', qualification_transaction_id = ?,
                    qualification_evidence_json = '["offline-q0"]', imported_through_transaction_id = ?
            """, (boundary, boundary))
        self.clock.advance(1)

    def script(self, *script, binding=None):
        broker = PracticeBroker(binding or self.bound, transport=ScriptedTransport(*script), now=self.clock.now)
        self.addCleanup(broker._transport.assert_consumed)
        return broker

    def snapshot(self, snapshot_body, *records, cursor=100, name="snapshot", extra=()):
        steps = [(Call("GET", ROOT), reply(snapshot_body))]
        if records:
            steps.append((Call("GET", ROOT + f"/transactions/sinceid?id={cursor}"),
                          reply(history(max(int(snapshot_body["lastTransactionID"]), *(int(row["id"]) for row in records)), *records))))
        steps.extend(extra)
        return reconcile_snapshot(self.db, self.script(*steps), snapshot_id=name)

    def cursor(self, db=None):
        return (self.db if db is None else db).execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0]

    def register(self, *, set_id="set-a", pair="EUR-USD", direction="long", trade_ids=("40", "41"),
                 units="1000", price="1.10000", stop_ids=("50", "51"), status="complete", run_id="run-a"):
        if not self.db.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone():
            self.start_run(self.db, run_id)
        self.add_decision(self.db, pair, run_id=run_id)
        reserve_set(self.db, set_id=set_id, run_id=run_id, pair=pair, direction=direction,
                    entry_atr="0.001", stop_distance="0.0015", planned_units=str(abs(Decimal(units))))
        if status != "pending":
            self.db.execute("UPDATE trade_sets SET establishment_status = ? WHERE set_id = ?", (status, set_id))
        for number, (identifier, stop) in enumerate(zip(trade_ids, stop_ids), start=1):
            if identifier is not None:
                self.db.execute("""
                    UPDATE trade_legs SET broker_trade_id = ?, broker_state = 'open', broker_state_transaction_id = '100',
                        current_units = ?, initial_units = ?, entry_price = ?, entry_at = ?, original_stop = '1.09000',
                        original_stop_order_id = ?, current_stop = '1.09000', current_stop_order_id = ?
                    WHERE set_id = ? AND leg_no = ?
                """, (identifier, units, units, price, STAMP, stop, stop, set_id, number))

    def test_a11_both_missing_legs_keep_their_actual_causes_and_clear_occupancy(self):
        self.register()
        one = order_fill(101, 40, pl="9", price="1.10100", order_id=52, reason="TAKE_PROFIT_ORDER")
        two = order_fill(109, 41, pl="-3", price="1.09900", order_id=51)
        two["time"] = "2026-11-16T21:50:00.123456799Z"
        self.snapshot(account(109, "1006.00"), two, one)
        self.assertTrue(pair_is_available(self.db, "EUR-USD"))
        legs = self.db.execute("SELECT broker_state, exit_reason, exit_at, exit_price FROM trade_legs ORDER BY leg_no")
        self.assertEqual([tuple(row) for row in legs], [
            ("closed", "TAKE_PROFIT_ORDER", STAMP, "1.10100"),
            ("closed", "STOP_LOSS_ORDER", two["time"], "1.09900"),
        ])
        self.assertEqual(self.cursor(), "109")
        self.assertEqual(self.db.execute("SELECT count(*) FROM issues").fetchone()[0], 0)

    def test_a11_missing_or_404_closing_evidence_keeps_last_confirmed_state(self):
        self.register()
        self.snapshot(account(100, trades=[open_trade(41)]), extra=(
            (Call("GET", ROOT + "/trades/40"), reply({"errorCode": "NO_SUCH_TRADE"}, status=404)),
            (Call("GET", ROOT + "/orders/50"), reply({"errorCode": "NO_SUCH_ORDER"}, status=404)),
        ))
        missing = self.db.execute("SELECT broker_state, current_units, exit_at FROM trade_legs WHERE leg_no = 1").fetchone()
        self.assertEqual(tuple(missing), ("open", "1000", None))
        self.assertEqual(self.db.execute("SELECT code FROM issues").fetchone()[0], "missing_closing_evidence")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a11_targeted_trade_and_stop_references_recover_prebaseline_closing_fill_once(self):
        self.register(trade_ids=("40", None))
        self.db.execute("UPDATE trade_legs SET broker_state_transaction_id = '90' WHERE leg_no = 1")
        close = order_fill(95, 40, pl="7", price="1.10100", order_id=50)
        self.snapshot(account(100), extra=(
            (Call("GET", ROOT + "/trades/40"),
             reply({"trade": {"id": "40", "state": "CLOSED", "closingTransactionIDs": ["95"]}})),
            (Call("GET", ROOT + "/orders/50"),
             reply({"order": {"id": "50", "tradeID": "40", "state": "FILLED", "fillingTransactionID": "95"}})),
            (Call("GET", ROOT + "/transactions/95"), reply({"transaction": close})),
        ))
        self.assertEqual(trade_journal(self.db, "40", -4)["trading_pl"], Decimal("7"))
        self.assertEqual(account_report(self.db, "qualification").realised_profit, Decimal(0))
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transactions").fetchone()[0], 1)

    def test_a12_sparse_paged_import_and_duplicate_postings(self):
        first = event(101, "TRANSFER_FUNDS", amount="20.00", accountBalance="1020.00")
        final = event(2300, "TRANSFER_FUNDS", amount="-5", accountBalance="1015.00")
        broker = self.script(
            (Call("GET", ROOT), reply(account(2300, "1015.00"))),
            (Call("GET", ROOT + "/transactions/idrange?from=101&to=1100"), reply(history(2300, first, first))),
            (Call("GET", ROOT + "/transactions/idrange?from=1101&to=2100"), reply(history(2300))),
            (Call("GET", ROOT + "/transactions/idrange?from=2101&to=2300"), reply(history(2300, final))),
        )
        reconcile_snapshot(self.db, broker)
        import_through(self.db, self.script(), "2300")
        self.assertEqual(self.cursor(), "2300")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transactions").fetchone()[0], 2)
        self.assertEqual(account_report(self.db, "qualification").cash_adjustments, Decimal("15"))

    def test_a12_gapped_history_does_not_advance_or_publish_snapshot(self):
        for n, (payload, message) in enumerate((
            (history(108, event(108, "CLIENT_CONFIGURE")), "behind"),
            (history(109, event(108, "CLIENT_CONFIGURE")), "missing the requested boundary"),
            ({**history(109), "pages": ["https://wrong-host/page"]}, "incomplete"),
        )):
            with self.subTest(message=message):
                broker = self.script(
                    (Call("GET", ROOT), reply(account(109))),
                    (Call("GET", ROOT + "/transactions/sinceid?id=100"), reply(payload)),
                )
                with self.assertRaisesRegex(BrokerError, message):
                    reconcile_snapshot(self.db, broker, snapshot_id=f"gap-{n}")
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(account_report(self.db, "qualification").snapshot_id, "q0")
        self.assertEqual(self.db.execute("SELECT count(*) FROM account_snapshots WHERE reconciliation_status = 'failed'")
                         .fetchone()[0], 3)
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transactions").fetchone()[0], 0)

    def test_a12_history_must_echo_already_confirmed_transactions_before_advancing(self):
        record_confirmed_transactions(self.db, self.script(), [event(102, "CLIENT_CONFIGURE")])
        with self.assertRaisesRegex(BrokerError, "previously confirmed"):
            self.snapshot(account(109), event(109, "CLIENT_CONFIGURE"))
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(self.db.execute("SELECT transaction_id FROM broker_transactions").fetchone()[0], "102")

    def test_a12_late_transaction_cannot_silently_change_an_existing_snapshots_ledger(self):
        self.snapshot(account(109), event(109, "CLIENT_CONFIGURE"))
        with self.assertRaisesRegex(BrokerError, "Previously imported history omitted"):
            record_confirmed_transactions(self.db, self.script(), [event(102, "TRANSFER_FUNDS", amount="20")])
        self.assertEqual(account_report(self.db, "qualification").cash_adjustments, Decimal(0))
        self.assertEqual(self.cursor(), "109")

    def test_a12_deferred_observation_is_not_posted_and_must_be_in_later_history(self):
        configure = event(101, "CLIENT_CONFIGURE")
        transfer = event(104, "TRANSFER_FUNDS", amount="20")
        self.snapshot(account(101), configure, transfer)
        self.assertEqual(self.cursor(), "101")
        self.assertEqual(account_report(self.db, "qualification").cash_adjustments, Decimal("0"))
        self.assertEqual(self.db.execute("SELECT transaction_id FROM broker_transactions").fetchone()[0], "101")
        later = event(105, "CLIENT_CONFIGURE")
        with self.assertRaisesRegex(BrokerError, "previously observed"):
            self.snapshot(account(105, "1020"), later, cursor=101, name="truncated")
        self.assertEqual(self.cursor(), "101")
        self.snapshot(account(105, "1020"), transfer, later, cursor=101, name="complete")
        self.assertEqual(account_report(self.db, "qualification").cash_adjustments, Decimal("20"))

    def test_a12_conflicting_duplicate_history_is_rejected(self):
        transfer = event(105, "TRANSFER_FUNDS", amount="20")
        with self.assertRaisesRegex(BrokerError, "Conflicting transactions"):
            self.snapshot(account(105, "1020"), transfer, {**transfer, "amount": "21"})
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transactions").fetchone()[0], 0)

    def test_a12_changed_saved_transaction_identifies_conflict_without_advancing(self):
        transfer = event(105, "TRANSFER_FUNDS", amount="20", accountBalance="1020")
        record_confirmed_transactions(self.db, self.script(), [transfer])
        saved = self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0]
        ledger = [tuple(row) for row in self.db.execute("SELECT * FROM ledger_entries")]
        with self.assertRaisesRegex(BrokerError, "Imported broker transaction changed.*105") as failure:
            self.snapshot(account(105, "1021"), {**transfer, "amount": "21", "accountBalance": "1021"})
        self.assertEqual(failure.exception.evidence,
                         {"transaction_id": "105", "changed_fields": ["accountBalance", "amount"]})
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0], saved)
        self.assertEqual([tuple(row) for row in self.db.execute("SELECT * FROM ledger_entries")], ledger)
        self.assertEqual(account_report(self.db, "qualification").snapshot_id, "q0")
        evidence = self.db.execute("SELECT broker_state_json FROM account_snapshots WHERE snapshot_id = 'snapshot'")
        self.assertEqual(json.loads(evidence.fetchone()[0])["failure"], failure.exception.evidence)

    def test_a12_history_zero_cost_enrichment_imports_stop_once_and_preserves_raw_response(self):
        self.register(trade_ids=("102", None), stop_ids=(None, None), status="incomplete")
        fill = order_fill(102, 102, effect="open", reason="MARKET_ORDER")
        expanded = with_zero_conversion_costs(fill)
        record_confirmed_transactions(self.db, self.script(), [fill])
        saved = self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0]
        stop = event(103, "STOP_LOSS_ORDER", tradeID="102", price="1.09000", timeInForce="GTC")
        broker = self.script((Call("GET", ROOT + "/transactions/sinceid?id=100"), reply(history(103, expanded, stop))))
        import_through(self.db, broker, "103")
        for bodies in ([expanded, stop], [fill, stop]):
            record_confirmed_transactions(self.db, self.script(), bodies)
        self.assertEqual(self.cursor(), "103")
        self.assertIn(saved, [r[0] for r in self.db.execute(
            "SELECT body_json FROM broker_transaction_observations WHERE transaction_id='102'")])
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transaction_observations WHERE transaction_id='102'").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM ledger_entries WHERE posted=1").fetchone()[0], 4)
        leg = self.db.execute("SELECT current_units,current_stop,current_stop_order_id FROM trade_legs WHERE leg_no=1").fetchone()
        self.assertEqual(tuple(leg), ("1000", "1.09000", "103"))
        self.assertEqual(self.db.execute("SELECT establishment_status FROM trade_sets").fetchone()[0], "incomplete")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_sparse_response_after_richer_history_preserves_original_record(self):
        fill = order_fill(102, 102, effect="open", reason="MARKET_ORDER")
        expanded = with_zero_conversion_costs(fill)
        record_confirmed_transactions(self.db, self.script(), [expanded])
        saved = self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0]
        record_confirmed_transactions(self.db, self.script(), [fill])
        self.assertEqual(self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0], saved)
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 1)

    def test_a12_enrichment_never_hides_changed_trade_facts_or_unqualified_fields(self):
        fill = order_fill(102, 102, effect="open", reason="MARKET_ORDER")
        record_confirmed_transactions(self.db, self.script(), [fill])
        cases = []
        for value in ("0.01", "-0.01", None, 0, "NaN", "bad", "0" * 39):
            for nested in (False, True):
                changed = with_zero_conversion_costs(fill)
                target = changed["tradeOpened"] if nested else changed
                target["guaranteedExecutionFeeHomeConversionCost"] = value
                cases.append(changed)
        for field, value in (("price", "1.20000"), ("requestID", "another-request"),
                             ("pl", "1"), ("unqualifiedCost", "0"), ("commission", "0.01")):
            cases.append({**with_zero_conversion_costs(fill), field: value})
        for field, value in (("units", "2000"), ("tradeID", "999"), ("price", "1.20000"),
                             ("unknownConversionCost", "0")):
            changed = with_zero_conversion_costs(fill)
            changed["tradeOpened"][field] = value
            cases.append(changed)
        for index, changed in enumerate(cases):
            with self.subTest(index=index), self.assertRaisesRegex(BrokerError, "Imported broker transaction changed"):
                record_confirmed_transactions(self.db, self.script(), [changed])
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 1)
        self.assertEqual(json.loads(self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0]),
                         {key:value for key,value in fill.items() if key != "accountID"})

    def test_a12_reduction_waits_for_contiguous_history_before_applying_remaining_units(self):
        self.register(trade_ids=("40", None))
        earlier = order_fill(101, 40, units="100", effect="reduce")
        later = order_fill(103, 40, units="200", effect="reduce")
        record_confirmed_transactions(self.db, self.script(), [later])
        self.assertEqual(trade_journal(self.db, "40", -4)["current_units"], "1000")
        broker = self.script((Call("GET", ROOT + "/transactions/sinceid?id=100"),
                              reply(history(103, later, earlier))))
        import_through(self.db, broker, "103")
        self.assertEqual(trade_journal(self.db, "40", -4)["current_units"], "700")

    def test_a12_newer_confirmed_drive_journal_and_older_snapshots_cannot_rewind(self):
        self.register()
        close = order_fill(105, 40, price="1.11000", pl="100")
        stop = event(104, "STOP_LOSS_ORDER", tradeID="41", price="1.10000")
        record_confirmed_transactions(self.db, self.script(), [close, stop, close])
        self.snapshot(account(103, trades=[open_trade(40, leg=1), open_trade(41)]),
                      event(103, "CLIENT_CONFIGURE"), close)
        report = account_report(self.db, "qualification")
        self.assertEqual((report.boundary, report.realised_profit), ("103", Decimal(0)))
        journal = trade_journal(self.db, "40", -4, boundary=report.boundary)
        self.assertEqual(journal["broker_state"], "closed")
        self.assertTrue(journal["after_snapshot"])
        self.assertEqual(journal["pips"], Decimal("100"))
        self.assertTrue(journal["fills"][0]["after_snapshot"])
        self.assertEqual(self.db.execute("SELECT current_stop FROM trade_legs WHERE leg_no = 2").fetchone()[0], "1.10000")
        evidence = self.db.execute("SELECT broker_state_json FROM account_snapshots WHERE snapshot_id = 'snapshot'").fetchone()[0]
        self.assertEqual(json.loads(evidence)["deferred_transaction_ids"], ["105"])
        self.snapshot(account(105, "1100.00", trades=[open_trade(41, stop_id="104", stop_price="1.10000")]),
                      stop, close, cursor=103, name="newer")
        with self.assertRaisesRegex(BrokerError, "predates imported"):
            self.snapshot(account(103), name="older")
        self.assertEqual(self.cursor(), "105")
        self.assertEqual(account_report(self.db, "qualification").realised_profit, Decimal("100"))

    def test_a12_atomic_write_and_restart_cover_transactions_fills_ledger_and_cursor(self):
        self.register(trade_ids=("40", None))
        fill = order_fill(110, 40, pl="10", price="1.10100", accountBalance="1010.00")

        def while_unlocked():
            self.assertFalse(self.db.in_transaction)
            with open_readonly(self.root, self.bound.experiment) as reader:
                self.assertEqual(self.cursor(reader), "0100")
                self.assertEqual(reader.execute("SELECT broker_state FROM trade_legs WHERE leg_no = 1").fetchone()[0], "open")
            return reply(history(110, fill))

        for after in (False, True):
            broker = self.script((Call("GET", ROOT + "/transactions/sinceid?id=100"), while_unlocked))
            with self.assertRaises(Interrupted if after else sqlite3.DatabaseError), interrupt_commit(self.db, after=after):
                import_through(self.db, broker, "110")
            for table in ("broker_transactions", "fills"):
                self.assertEqual(self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], int(after))
            self.assertEqual(self.db.execute("SELECT count(*) FROM ledger_entries WHERE posted = 1").fetchone()[0],
                             4 if after else 0)
            self.assertEqual(self.cursor(), "110" if after else "0100")
        import_through(self.db, self.script(), "110")
        self.assertEqual(trade_journal(self.db, "40", -4)["trading_pl"], Decimal("10"))
        self.assertFalse(self.db.execute("PRAGMA foreign_key_check").fetchall())

    def test_a12_unfinished_entry_is_reconciled_by_client_and_order_identity(self):
        self.register(trade_ids=(None, None), status="pending")
        prepare_attempt(self.db, self.bound, attempt_id="attempt", run_id="run-a", stage="manage_new",
                        purpose="entry", method="POST", path="/orders", prepared_at=self.clock.now(), pair="EUR-USD",
                        set_id="set-a", leg_no=1, client_id="fixture-client")
        order = event(101, "MARKET_ORDER", instrument="EUR_USD", clientExtensions={"id": "fixture-client"})
        fill = order_fill(104, 104, effect="open", order_id=101, reason="MARKET_ORDER")
        self.snapshot(account(104, trades=[open_trade(104, leg=1)]), fill, order)
        self.assertEqual(tuple(self.db.execute("SELECT outcome, broker_trade_id FROM broker_attempts").fetchone()),
                         ("confirmed", "104"))
        self.assertEqual(self.db.execute("SELECT establishment_status FROM trade_sets").fetchone()[0], "incomplete")
        self.assertEqual(self.db.execute("SELECT code FROM issues").fetchone()[0], "interrupted_set")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a14_reductions_postings_and_failed_refresh_share_snapshot_boundary(self):
        self.register(trade_ids=("40", None))
        self.register(set_id="set-b", pair="USD-JPY", direction="short", trade_ids=("60", None),
                      units="-1000", price="150.000")
        reduce = order_fill(101, 40, units="400", effect="reduce", price="1.10500", pl="10.00",
                            financing="-1", commission="2", fee="0.50", accountBalance="1006.50")
        finance = event(102, "DAILY_FINANCING", financing="-0.50", accountBalance="1006.00",
                        positionFinancings=[{"instrument": "EUR_USD", "financing": "-0.50",
                                             "openTradeFinancings": [{"tradeID": "40", "financing": "-0.50"}]}])
        deposit = event(103, "TRANSFER_FUNDS", amount="50.00", accountBalance="1056.00")
        yen = order_fill(104, 60, units="-1000", price="150.030", pl="-6.00", name="USD_JPY", accountBalance="1050.00")
        self.snapshot(account(104, "1050.00", trades=[open_trade(40, units="600", leg=1)], unrealised="3.00"),
                      reduce, finance, deposit, yen)
        report = account_report(self.db, "qualification")
        self.assertEqual((report.balance, report.unrealised_pl, report.realised_profit, report.realised_loss,
                          report.financing, report.commission, report.other_charges, report.cash_adjustments,
                          report.net_posted), tuple(map(Decimal, ("1050", "3", "10", "-6", "-1.5", "-2", "-.5", "50", "50"))))
        open_leg = trade_journal(self.db, "40", -4, boundary=report.boundary)
        self.assertEqual((open_leg["exit_price"], open_leg["pips"], open_leg["trading_pl"]), (None, None, None))
        self.assertEqual(trade_journal(self.db, "60", -2)["pips"], Decimal("-3"))
        self.assertEqual([row["posted"] for row in open_leg["ledger"]], [0, 0, 0, 0])

        final = order_fill(105, 40, units="600", price="1.11300", pl="100", accountBalance="1150.00")
        final["time"] = "2026-11-16T21:50:01.000000001Z"
        import_through(self.db, self.script((Call("GET", ROOT + "/transactions/sinceid?id=104"), reply(history(105, final)))), "105")
        with self.assertRaisesRegex(BrokerError, "HTTP 503"):
            reconcile_snapshot(self.db, self.script((Call("GET", ROOT), reply({"errorMessage": "unavailable"}, 503))),
                               snapshot_id="failed-final")
        self.assertEqual(account_report(self.db, "qualification"), report)
        journal = trade_journal(self.db, "40", -4, boundary=report.boundary)
        self.assertEqual((journal["exit_price"], journal["exit_at"], journal["pips"], journal["trading_pl"]),
                         ("1.10980", final["time"], Decimal("98"), Decimal("110")))
        self.assertEqual([fill["after_snapshot"] for fill in journal["fills"]], [False, True])
        self.snapshot(account(105, "1150.00"), name="successful-final")
        updated = account_report(self.db, "qualification")
        self.assertEqual((updated.realised_profit, updated.balance), (Decimal("110"), Decimal("1150")))

    def test_a14_unexplained_balances_are_visible_without_balancing_adjustments(self):
        for name, body, message in (
            ("transaction", event(105, "UNKNOWN_CHARGE", accountBalance="995.00"), "broker transaction balance"),
            ("summary", event(105, "CLIENT_CONFIGURE"), "broker snapshot balance"),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(BrokerError, message):
                self.snapshot(account(105, "995.00"), body, name=name)
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(account_report(self.db, "qualification").balance, Decimal("1000.00"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM ledger_entries").fetchone()[0], 0)
        self.assertIn("995.00", self.db.execute("SELECT broker_state_json FROM account_snapshots WHERE snapshot_id = 'summary'").fetchone()[0])

    def test_a14_and_a16_qualification_q0_and_ordinary_a0_are_distinct(self):
        original = self.db.execute("SELECT manifest_hash, account_id, controller_id FROM notebook").fetchone()
        self.register()
        first = order_fill(101, 40, pl="100")
        self.snapshot(account(101, "1100", trades=[open_trade(41)]), first, name="qualification-result")
        self.assertIsNone(account_report(self.db, "ordinary"))
        self.assertEqual(account_report(self.db, "qualification").realised_profit, Decimal("100"))
        # M07 owns the activation operation. Seed its already-committed records here.
        self.clock.advance(1)
        closed = order_fill(102, 41)
        self.snapshot(account(102, "1100"), closed, cursor=101, name="a0")
        with transaction(self.db):
            self.db.execute("""
                UPDATE notebook SET activation_snapshot_id = 'a0', activation_transaction_id = '102',
                    activation_evidence_json = '["offline-a0"]', activated_at = ?
            """, (utc_text(self.clock.now()),))
        self.clock.advance(1)
        self.register(set_id="ordinary-set", pair="GBP-USD", trade_ids=("61", None))
        ordinary = order_fill(103, 61, pl="20", name="GBP_USD")
        self.snapshot(account(103, "1120"), ordinary, cursor=102, name="ordinary-result")
        with open_readonly(self.root, self.bound.experiment) as reader:
            qualification = account_report(reader, "qualification")
            ordinary_report = account_report(reader, "ordinary")
            self.assertEqual((qualification.opening_snapshot_id, qualification.snapshot_id, qualification.balance,
                              qualification.realised_profit), ("q0", "a0", Decimal("1100"), Decimal("100")))
            self.assertEqual((ordinary_report.opening_snapshot_id, ordinary_report.snapshot_id, ordinary_report.opening_balance,
                              ordinary_report.balance, ordinary_report.realised_profit),
                             ("a0", "ordinary-result", Decimal("1100"), Decimal("1120"), Decimal("20")))
        self.assertEqual(self.db.execute("SELECT manifest_hash, account_id, controller_id FROM notebook").fetchone(), original)

    def test_a16_account_identity_currency_and_cross_account_transactions_are_isolated(self):
        other = self.binding("controller-b")
        other_db = self.notebook(other)
        other_id = other.connection.account_id
        other_root = f"/v3/accounts/{other_id}"
        self.opening(other_db, currency="EUR")
        broker = self.script(
            (Call("GET", other_root), reply(account(105, "1007", account_id=other_id, currency="EUR"))),
            (Call("GET", other_root + "/transactions/sinceid?id=100"),
             reply(history(105, event(105, "TRANSFER_FUNDS", accountID=other_id, amount="7")))),
            binding=other,
        )
        with self.assertRaises(ConfigurationError):
            reconcile_snapshot(self.db, broker)
        reconcile_snapshot(other_db, broker)
        self.assertEqual((self.cursor(), self.cursor(other_db)), ("0100", "105"))
        self.assertEqual(account_report(other_db, "qualification").home_currency, "EUR")
        for name, snapshot in (("wrong-id", account(105, account_id=other_id)), ("wrong-currency", account(105, currency="EUR"))):
            snapshot["account"]["token"] = TOKEN
            with self.subTest(name=name), self.assertRaisesRegex(BrokerError, "identity or currency"):
                self.snapshot(snapshot, name=name)
            evidence = self.db.execute("SELECT broker_state_json FROM account_snapshots WHERE snapshot_id = ?", (name,)).fetchone()[0]
            self.assertTrue(all(secret not in evidence for secret in (ACCOUNT, other_id, TOKEN)))
        with self.assertRaisesRegex(BrokerError, "transaction account"):
            self.snapshot(account(105), event(105, "CLIENT_CONFIGURE", accountID=other_id), name="foreign-history")
        self.assertEqual(self.cursor(), "0100")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_transactions").fetchone()[0], 0)

    def test_a16_unexpected_trades_orders_and_unattributable_activity(self):
        unknown = open_trade(70, name="GBP_USD")
        order = {"id": "80", "type": "LIMIT", "state": "PENDING", "instrument": "AUD_USD"}
        self.snapshot(account(100, trades=[unknown], orders=[order]))
        self.assertFalse(pair_is_available(self.db, "GBP-USD"))
        self.assertFalse(pair_is_available(self.db, "AUD-USD"))
        self.assertTrue(pair_is_available(self.db, "EUR-USD"))
        with self.assertRaisesRegex(BrokerError, "cannot be isolated"):
            self.snapshot(account(100, orders=[{"id": "90", "type": "STOP_LOSS", "tradeID": "999"}]), name="unattributed")
        self.assertEqual(account_report(self.db, "qualification").snapshot_id, "snapshot")

    def test_a16_transaction_evidence_redacts_private_values_at_rest(self):
        configuration = event(101, "CLIENT_CONFIGURE", authorization=f"Bearer {TOKEN}",
                              details={"password": "fixture-extra-secret", "note": f"{TOKEN} at {ROOT}"})
        self.snapshot(account(101), configuration)
        raw = self.db.execute("SELECT body_json FROM broker_transactions").fetchone()[0]
        for private in (TOKEN, ACCOUNT, "fixture-extra-secret", "authorization"):
            self.assertNotIn(private, raw)
        self.assertEqual(json.loads(raw)["details"]["note"], "[redacted] at /v3/accounts/[redacted]")
        observations = [row[0] for row in self.db.execute("SELECT body_json FROM broker_transaction_observations")]
        self.assertEqual(observations, [raw])
