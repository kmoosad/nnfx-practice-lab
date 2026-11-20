"""M06 A03/A05/A06/A12: controlled candidate execution, never practice evidence."""

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict, replace
from decimal import Decimal, localcontext
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

from nnfx_practice.broker import BrokerError, PracticeBroker
from nnfx_practice.config import ConfigurationError
from nnfx_practice.entry import enter_candidate
from nnfx_practice.evidence import redact
from nnfx_practice.notebook import finish_pair, open_readonly, pair_is_available, prepare_attempt, reserve_set, transaction
from nnfx_practice.reconciliation import import_through, reconcile_snapshot
from nnfx_practice.sizing import levels, margin_requirement, size_candidate
from strategies import t3_bandpass_v1 as selected

from .support import ACCOUNT, TOKEN, Call, Interrupted, NotebookCase, ScriptedTransport, interrupt_commit
from . import test_m02 as m02
from .test_m02 import ROOT, STAMP, account, event, history, open_trade, order_fill, protection, reply
from .test_m03 import daily_body
from .test_m04 import instruments_body, pricing_body


class SizingChecks(NotebookCase):
    def inputs(self, **changes):
        values = dict(balance="1000", atr="0.001", direction="long", pair="EUR-USD", home="USD",
                      instruments=instruments_body(), pricing=pricing_body(), account=account(100)["account"], pricing_at=STAMP)
        values.update(changes)
        return values

    def test_a05_both_directions_use_loss_not_gain_or_position(self):
        for direction in ("long", "short"):
            data = self.inputs(direction=direction, home="AUD", pricing=pricing_body("AUD"))
            plan = size_candidate(**data)
            self.assertEqual(plan["accountLoss"], "0.89")
            self.assertEqual(Decimal(plan["units"]), Decimal("7490"))
            self.assertLessEqual(Decimal(plan["risk_per_leg"]), Decimal("10"))
            self.assertEqual(Decimal(plan["margin"]["required"]), Decimal("7490") * 2 * Decimal("0.90") * Decimal("0.05"))
            self.assertEqual(Decimal(plan["signed_units"]) > 0, direction == "long")

    def test_a05_home_quote_uses_returned_factor_even_if_not_identity(self):
        data = self.inputs()
        next(row for row in data["pricing"]["homeConversions"] if row["currency"] == "USD")["accountLoss"] = "1.2"
        plan = size_candidate(**data)
        self.assertEqual(plan["accountLoss"], "1.2")
        self.assertEqual(plan["units"], "5555")  # Identity validation belongs to preflight, never a local fallback.

    def test_a05_invalid_or_missing_loss_in_both_currency_cases(self):
        for home in ("USD", "AUD"):
            for bad in (None, "0", "-1", "NaN", "Infinity", "oops", 1):
                with self.subTest(home=home, bad=bad):
                    data = self.inputs(home=home)
                    row = next(r for r in data["pricing"]["homeConversions"] if r["currency"] == "USD")
                    if bad is None:
                        del row["accountLoss"]
                    else:
                        row["accountLoss"] = bad
                    with self.assertRaises(BrokerError):
                        size_candidate(**data)
            for duplicate in (False, True):
                data = self.inputs(home=home)
                rows = data["pricing"]["homeConversions"]
                usd = next(r for r in rows if r["currency"] == "USD")
                rows.append(usd) if duplicate else rows.remove(usd)
                with self.assertRaises(BrokerError):
                    size_candidate(**data)

    def test_a05_fractional_units_and_distance_half_away_rounding(self):
        data = self.inputs(atr="0.00003")
        data["instruments"]["instruments"][0]["tradeUnitsPrecision"] = 2
        plan = size_candidate(**data)
        self.assertEqual(plan["raw_stop_distance"], "0.000045")
        self.assertEqual(plan["stop_distance"], "0.00005")
        self.assertEqual(plan["units"], "200000.00")
        self.assertEqual(plan["risk_per_leg"], "10.000000000000000")
        self.assertEqual(levels("1.10000", "0.000015", "0.00002", "long", 5)["target"], "1.10002")
        self.assertEqual(levels("1.10000", "0.000015", "0.00002", "short", 5)["target"], "1.09999")

    def test_a05_order_and_remaining_combined_position_limits(self):
        for order_max, position_max, occupied, expected in (("123.9", "0", "0", "123"),
                ("999", "201", "0", "100"), ("999", "201", "40", "80")):
            data = self.inputs(existing_units=occupied)
            data["instruments"]["instruments"][0].update(maximumOrderUnits=order_max, maximumPositionSize=position_max)
            self.assertEqual(size_candidate(**data)["units"], expected)

    def test_a05_minimum_and_invalid_precision_limits(self):
        for changes in ({"minimumTradeSize": "7000"}, {"displayPrecision": 19}, {"tradeUnitsPrecision": -1},
                        {"maximumPositionSize": "1"}, {"maximumOrderUnits": "0"}, {"marginRate": "NaN"}):
            data = self.inputs()
            data["instruments"]["instruments"][0].update(changes)
            with self.assertRaises(BrokerError):
                size_candidate(**data)

    def test_a05_invalid_balance_atr_and_executable_levels(self):
        for key in ("balance", "atr"):
            for value in ("0", "-1", "NaN", "Infinity", "bad", 1.0):
                with self.assertRaises(BrokerError):
                    size_candidate(**self.inputs(**{key: value}))
        for atr in ("0.0000001", "1"):
            with self.assertRaises(BrokerError):
                size_candidate(**self.inputs(atr=atr))
        with self.assertRaises(BrokerError):
            levels("1.100001", "0.001", "0.00150", "long", 5)

    def test_a05_jpy_precision_and_wrong_side_target(self):
        plan = size_candidate(**self.inputs(pair="USD-JPY", atr="0.123", home="JPY", pricing=pricing_body("JPY")))
        self.assertEqual(plan["stop_distance"], "0.185")
        self.assertEqual(plan["quote_currency"], "JPY")
        with self.assertRaises(BrokerError):
            levels("1.10000", "0.000001", "0.00150", "long", 5)

    def test_a05_base_home_margin_identity_and_optional_account_override(self):
        data = self.inputs(home="EUR")
        data["pricing"]["homeConversions"] = [r for r in data["pricing"]["homeConversions"] if r["currency"] != "EUR"]
        for override, expected in ((None, "0.05"), ("0.02", "0.02"), ("0.08", "0.05")):
            if override:
                data["account"]["marginRate"] = override
            plan = size_candidate(**data)
            self.assertEqual(plan["margin"]["positionValue"], "1")
            self.assertEqual(plan["margin"]["rate"], expected)
        data["account"]["marginRate"] = "bad"
        with self.assertRaises(BrokerError):
            size_candidate(**data)

    def test_a05_missing_invalid_base_position_value_has_no_quote_fallback(self):
        for value in (None, "0", "-1", "bad", "NaN"):
            data = self.inputs()
            next(r for r in data["pricing"]["homeConversions"] if r["currency"] == "EUR")["positionValue"] = value
            with self.assertRaises(BrokerError):
                size_candidate(**data)

    def test_a05_unavailable_prices_and_required_guaranteed_stops(self):
        for changes in ({"tradeable": False}, {"bids": []}, {"asks": [{"price": "0"}]}):
            data = self.inputs()
            data["pricing"]["prices"][0].update(changes)
            with self.assertRaises(BrokerError):
                size_candidate(**data)
        data = self.inputs()
        data["account"]["guaranteedStopLossOrderMode"] = "REQUIRED"
        with self.assertRaises(BrokerError):
            size_candidate(**data)

    def test_a05_decimal_context_does_not_change_risk(self):
        with localcontext(prec=4):
            plan = size_candidate(**self.inputs(balance="1234567.89", atr="0.00123456789"))
        self.assertLessEqual(Decimal(plan["risk_per_leg"]), Decimal(plan["budget_per_leg"]))


class CandidateChecks(NotebookCase):
    opening = m02.ReconciliationChecks.opening

    def setUp(self):
        self.fresh()

    def fresh(self, direction="long"):
        super().setUp()
        registry = self.root / "config.toml"
        registry.write_text(registry.read_text().replace('"fixture-v1"', '"t3_bandpass_v1"'))
        manifest = self.root / "strategies/t3_bandpass_v1/manifest.json"
        manifest.parent.mkdir()
        manifest.write_bytes(Path(selected.__file__).with_name("manifest.json").read_bytes())
        self.write_private(count=386)
        self.bound = self.binding()
        self.db = self.notebook(self.bound)
        self.opening(self.db)
        self.run_id = "entry-1"
        self.start_run(self.db, self.run_id)
        self.balance()
        self.direction = direction
        self.units = "6666" if direction == "long" else "-6666"
        self.stop = "1.09850" if direction == "long" else "1.10150"
        self.target = "1.10100" if direction == "long" else "1.09900"
        self.steps, self.records, self.cursor = [], [], 100
        self.transport = None

    def balance(self, value="1000.00"):
        self.db.execute("UPDATE runs SET sizing_balance = ?, sizing_balance_at = ?, sizing_transaction_id = '100' WHERE run_id = ?",
                        (value, STAMP, self.run_id))

    def candle(self, count=386, flat=False):
        body = daily_body(self.clock.now().date(), count=count)
        if flat:
            for row in body["candles"]:
                row["mid"] = dict.fromkeys(("o", "h", "l", "c"), "1.10000")
        self.steps.append((Call("GET", ROOT + "/instruments/EUR_USD/candles?price=M&granularity=D&count=386"
                                "&smooth=false&dailyAlignment=17&alignmentTimezone=America%2FNew_York"), reply(body)))

    def inputs(self, *, margin="900", pricing=None, instruments=None):
        self.candle()
        self.steps.append((Call("GET", ROOT + "/instruments?instruments=EUR_USD"), reply(instruments or instruments_body())))
        self.price(pricing)
        self.summary(margin)

    def price(self, body=None):
        self.steps.append((Call("GET", ROOT + "/pricing?instruments=EUR_USD&includeHomeConversions=true"), reply(body or pricing_body())))

    def summary(self, margin="900", balance="1000", records=()):
        boundary = max([self.cursor, *(int(r["id"]) for r in records)])
        body = account(boundary, balance)
        body["account"]["marginAvailable"] = margin
        self.steps.append((Call("GET", ROOT + "/summary"), reply(body)))
        self.history(records, boundary)

    def history(self, records, boundary=None):
        records = list(records)
        boundary = boundary or max([self.cursor, *(int(r["id"]) for r in records)])
        self.records.extend(records)
        if boundary != self.cursor:
            self.steps.append((Call("GET", ROOT + f"/transactions/sinceid?id={self.cursor}"), reply(history(boundary, *records))))
        self.cursor = boundary

    def entry(self, number=1, *, reject=False, cancel=False, pending=False, empty=False, timeout=False,
              wrong_units=False, missing_stop=False, wrong_stop=False, reduce=False, extra=(), duplicate=False,
              fill_price="1.10000", callback=None):
        order_id = 101 if number == 1 else 106
        trade_id = "102" if number == 1 or duplicate else "107"
        stop_id = "103" if number == 1 else "108"
        client_id = "entry-" + ("one" if number == 1 else "two")
        create = event(order_id, "MARKET_ORDER_REJECT" if reject else "MARKET_ORDER", instrument="EUR_USD",
                       units=self.units, clientExtensions={"id": client_id}, timeInForce="FOK", positionFill="OPEN_ONLY")
        bodies = [create]
        if cancel:
            bodies.append(event(order_id + 1, "ORDER_CANCEL", orderID=str(order_id), reason="INSUFFICIENT_MARGIN"))
        if not (reject or cancel or pending or empty or timeout):
            fill = order_fill(order_id + 1, trade_id, effect="reduce" if reduce else "open", units="2" if wrong_units else self.units,
                              price=fill_price, reason="MARKET_ORDER", order_id=order_id)
            bodies.append(fill)
            if not missing_stop and not reduce:
                stop = str(Decimal(fill_price) + (Decimal("-0.00150") if self.direction == "long" else Decimal("0.00150")))
                bodies.append(event(int(stop_id), "STOP_LOSS_ORDER", tradeID=trade_id, price="1.00000" if wrong_stop else stop,
                                    timeInForce="GTC"))
            for body in bodies:
                body["batchID"] = str(order_id)
        bodies.extend(extra)
        if empty or timeout:
            bodies = []
        boundary = max([self.cursor, *(int(row["id"]) for row in bodies)])
        payload = {"order": {"type": "MARKET", "instrument": "EUR_USD", "units": self.units,
                             "timeInForce": "FOK", "positionFill": "OPEN_ONLY", "clientExtensions": {"id": client_id},
                             "tradeClientExtensions": {"id": client_id},
                             "stopLossOnFill": {"distance": "0.00150", "timeInForce": "GTC"}}}
        response = reply({"lastTransactionID": str(boundary), **{f"t{i}Transaction": b for i, b in enumerate(bodies)}},
                         400 if reject else 201, request_id=f"request-entry-{number}")
        def failed():
            raise OSError("fixture timeout")
        self.steps.append((Call("POST", ROOT + "/orders", payload), callback or (failed if timeout else response)))
        if not timeout:
            self.history(bodies, boundary)
        return response

    def live(self, *, target=False, changes=None, records=()):
        trade = open_trade("102", units=self.units, initial=self.units, stop_id="103", stop_price=self.stop)
        trade["stopLossOrder"]["timeInForce"] = "GTC"
        if target:
            trade["takeProfitOrder"] = protection("104", "102", "TAKE_PROFIT", self.target, timeInForce="GTC")
        trade.update(changes or {})
        boundary = max([self.cursor, *(int(r["id"]) for r in records)])
        self.steps.append((Call("GET", ROOT + "/trades/102"), reply({"lastTransactionID": str(boundary), "trade": trade})))
        self.history(records, boundary)

    def target_order(self, *, reject=False, wrong=False, empty=False, extra=()):
        body = event(104, "TAKE_PROFIT_ORDER_REJECT" if reject else "TAKE_PROFIT_ORDER", tradeID="102",
                     price="1.20000" if wrong else self.target, timeInForce="GTC")
        bodies = [] if empty else [body, *extra]
        boundary = max([self.cursor, *(int(r["id"]) for r in bodies)])
        result = reply({"lastTransactionID": str(boundary), **{f"t{i}Transaction": b for i, b in enumerate(bodies)}},
                       400 if reject else 200, request_id="request-target")
        self.steps.append((Call("PUT", ROOT + "/trades/102/orders", {"takeProfit": {"price": self.target, "timeInForce": "GTC"}}), result))
        self.history(bodies, boundary)
        return result

    def through_target(self):
        self.inputs()
        self.entry()
        self.live()
        self.target_order()
        self.live(target=True)

    def through_margin(self, margin="900", balance="9000", records=()):
        self.through_target()
        self.price()
        self.summary(margin, balance, records)

    def run_candidate(self, *, real=False, c1=None, atr=0.001):
        self.transport = ScriptedTransport(*self.steps)
        broker = PracticeBroker(self.bound, transport=self.transport, now=self.clock.now)
        with ExitStack() as stack:
            stack.enter_context(patch("nnfx_practice.entry.uuid4", side_effect=[SimpleNamespace(hex=s) for s in ("set-a", "one", "target", "two")]))
            if not real:
                stack.enter_context(patch.object(selected, "observe_c1", return_value=selected.EventObservation(
                    c1 or self.direction, selected.C1_RULE_ID, selected.C1_OUTPUTS, (True, False), (False, False))))
                stack.enter_context(patch.object(selected, "sizing_atr", return_value=selected.AtrObservation(atr)))
            result = enter_candidate(self.db, broker, run_id=self.run_id, pair="EUR-USD")
        self.transport.assert_consumed()
        return result

    def row(self, table):
        return self.db.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()

    def assert_blocked(self):
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))
        self.assertEqual(self.row("trade_sets")["establishment_status"], "incomplete")
        self.assertTrue(self.db.execute("SELECT 1 FROM issues WHERE status = 'open'").fetchone())

    def test_a06_long_complete_set_retains_committed_facts(self):
        self.through_margin()
        self.entry(2)
        self.assertEqual(self.run_candidate(), "completed")
        self.assertEqual(self.row("trade_sets")["establishment_status"], "complete")
        self.assertEqual([r[0] for r in self.db.execute("SELECT broker_trade_id FROM trade_legs ORDER BY leg_no")], ["102", "107"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM issues").fetchone()[0], 0)
        self.assertEqual(self.row("runs")["sizing_balance"], "1000.00")
        self.assertEqual(self.row("trade_sets")["entry_atr"], "0.001")
        self.assertEqual(self.row("trade_legs")["original_stop"], self.stop)
        self.assertEqual([r[0] for r in self.db.execute("SELECT outcome FROM broker_attempts")], ["confirmed"] * 3)
        plan = json.loads(self.row("pair_decisions")["sizing_json"])
        self.assertEqual(plan["establishment"]["transaction_id"], "108")
        self.assertEqual(plan["sizing"]["units"], "6666")

    def test_a06_short_complete_set_uses_each_own_fill(self):
        self.fresh("short")
        self.through_margin()
        self.entry(2, fill_price="1.10020")
        self.assertEqual(self.run_candidate(), "completed")
        legs = self.db.execute("SELECT initial_units, entry_price, original_stop, intended_target FROM trade_legs ORDER BY leg_no").fetchall()
        self.assertEqual(tuple(legs[0]), ("-6666", "1.10000", "1.10150", "1.09900"))
        self.assertEqual(tuple(legs[1]), ("-6666", "1.10020", "1.10170", None))

    def test_a06_trade_2_has_no_target_level_requirement(self):
        self.fresh("short")
        self.through_margin()
        # Deliberately extreme fill isolates the contract: only its stop is required.
        self.entry(2, fill_price="0.00050")
        self.assertEqual(self.run_candidate(), "completed")
        leg = self.db.execute("SELECT * FROM trade_legs WHERE leg_no = 2").fetchone()
        self.assertEqual(leg["original_stop"], "0.00200")
        self.assertIsNone(leg["confirmed_target"])

    def test_a03_real_qualified_window_has_no_fresh_event_on_flat_candles(self):
        self.candle(flat=True)
        self.assertEqual(self.run_candidate(real=True), "skipped")
        row = self.row("pair_decisions")
        self.assertEqual(json.loads(row["capture_json"])["received_count"], 386)
        self.assertEqual(json.loads(row["c1_json"])["rule_id"], selected.C1_RULE_ID)
        self.assertIsNone(self.row("trade_sets"))

    def test_a03_wrong_window_never_sizes(self):
        for count in (385, 387):
            self.fresh()
            self.candle(count=count)
            self.assertEqual(self.run_candidate(), "skipped")
            self.assertIsNone(self.row("trade_sets"))
            self.assertEqual(len(self.transport.calls), 1)

    def test_a03_invalid_atr_and_continuing_state_never_enter(self):
        for c1, atr in (("long", 0), ("short", -1), ("long", float("nan")), ("long", None), ("no_event", 0.001)):
            self.fresh()
            self.candle()
            self.assertEqual(self.run_candidate(c1=c1, atr=atr), "skipped")
            self.assertEqual(len(self.transport.calls), 1)

    def test_a03_changed_binding_and_missing_balance_fail_before_requests(self):
        for bound in (replace(self.bound, connection=replace(self.bound.connection, lookback_candles=385)),
                      replace(self.bound, manifest=replace(self.bound.manifest, hash="f" * 64))):
            with self.assertRaises(ConfigurationError):
                enter_candidate(self.db, PracticeBroker(bound, transport=ScriptedTransport()), run_id=self.run_id, pair="EUR-USD")
        self.start_run(self.db, "no-balance")
        with self.assertRaises(ValueError):
            enter_candidate(self.db, PracticeBroker(self.bound, transport=ScriptedTransport()), run_id="no-balance", pair="EUR-USD")

    def test_a05_conversion_skip_retains_inputs_without_orders(self):
        prices = pricing_body()
        next(r for r in prices["homeConversions"] if r["currency"] == "USD").pop("accountLoss")
        self.inputs(pricing=prices)
        self.assertEqual(self.run_candidate(), "skipped")
        self.assertIn("decimal", self.row("pair_decisions")["reason"])
        self.assertIsNone(self.row("trade_sets"))
        self.assertEqual(len(json.loads(self.row("pair_decisions")["sizing_json"])["reads"]), 3)

    def test_a05_pre_set_margin_skip_does_not_reserve(self):
        self.inputs(margin="599.93999")
        self.assertEqual(self.run_candidate(), "skipped")
        self.assertIsNone(self.row("trade_sets"))
        self.assertTrue(pair_is_available(self.db, "EUR-USD"))

    def test_a05_trade_2_margin_failure_blocks_without_resizing(self):
        self.through_margin(margin="299.96999")
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(len([c for c in self.transport.calls if c.method == "POST"]), 1)
        self.assertEqual(self.row("runs")["sizing_balance"], "1000.00")
        self.assertEqual([r[0] for r in self.db.execute("SELECT planned_units FROM trade_legs")], ["6666", "6666"])

    def test_a12_wholly_rejected_first_entry_releases_cleanly(self):
        self.inputs()
        self.entry(reject=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assertTrue(pair_is_available(self.db, "EUR-USD"))
        self.assertEqual(self.row("trade_sets")["establishment_status"], "not_opened")
        self.assertEqual([r[0] for r in self.db.execute("SELECT broker_state FROM trade_legs")], ["not_opened"] * 2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM issues").fetchone()[0], 0)

    def test_a12_first_filled_second_rejected_remains_blocked_even_after_exit(self):
        self.through_margin()
        self.entry(2, reject=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        close = order_fill(110, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        transport = ScriptedTransport((Call("GET", ROOT + "/transactions/sinceid?id=106"), reply(history(110, close))))
        import_through(self.db, PracticeBroker(self.bound, transport=transport, now=self.clock.now), "110")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["broker_state"], "closed")
        self.assertEqual(self.row("trade_legs")["exit_price"], self.target)

    def test_a12_2xx_cancel_without_fill_releases_cleanly(self):
        self.inputs()
        self.entry(cancel=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assertEqual(self.row("broker_attempts")["outcome"], "cancelled")
        self.assertTrue(pair_is_available(self.db, "EUR-USD"))

    def test_a12_pending_empty_and_timeout_are_never_retried(self):
        for variation in ("pending", "empty", "timeout"):
            self.fresh()
            self.inputs()
            self.entry(**{variation: True})
            self.assertEqual(self.run_candidate(), "failed")
            self.assert_blocked()
            self.next_blocked_run()

    def next_blocked_run(self):
        self.run_id = "entry-2"
        self.start_run(self.db, self.run_id)
        self.balance()
        transport = ScriptedTransport()
        result = enter_candidate(self.db, PracticeBroker(self.bound, transport=transport), run_id=self.run_id, pair="EUR-USD")
        self.assertEqual(result, "skipped")
        self.assertEqual(transport.calls, [])

    def test_a12_target_rejection_preserves_fill_stop_and_operator_issue(self):
        self.inputs()
        self.entry()
        self.live()
        self.target_order(reject=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["original_stop"], self.stop)
        self.assertEqual(self.row("trade_legs")["intended_target"], self.target)
        self.assertIsNone(self.row("trade_legs")["confirmed_target"])
        self.next_blocked_run()

    def test_a12_target_wrong_price_and_empty_success_do_not_advance(self):
        for mode in ("wrong", "empty"):
            self.fresh()
            self.inputs()
            self.entry()
            self.live()
            self.target_order(**{mode: True})
            self.assertEqual(self.run_candidate(), "failed")
            self.assert_blocked()

    def test_a12_reduction_instead_of_new_trade_preserves_fill_effect(self):
        self.inputs()
        self.entry(reduce=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("fills")["effect"], "reduce")
        self.assertIsNone(self.row("trade_legs")["broker_trade_id"])

    def test_a12_wrong_units_preserves_actual_fill_without_target(self):
        self.inputs()
        self.entry(wrong_units=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["initial_units"], "2")
        self.assertEqual(self.row("trade_legs")["planned_units"], "6666")

    def test_a12_first_fill_precision_failure_is_not_rounded_away(self):
        self.inputs()
        self.entry(fill_price="1.100001")
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["entry_price"], "1.100001")

    def test_a12_missing_first_stop_never_requests_target(self):
        self.inputs()
        self.entry(missing_stop=True)
        self.live(changes={"stopLossOrder": None})
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertIsNone(self.row("trade_legs")["original_stop"])

    def test_a12_wrong_first_stop_preserves_original_actual_level(self):
        self.inputs()
        self.entry(wrong_stop=True)
        self.live(changes={"stopLossOrder": protection("103", "102", "STOP_LOSS", "1.00000", timeInForce="GTC")})
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["original_stop"], "1.00000")

    def test_a12_missing_second_stop_blocks_two_filled_legs(self):
        self.through_margin()
        self.entry(2, missing_stop=True)
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills WHERE effect = 'open'").fetchone()[0], 2)

    def test_a12_distinct_second_identity_required(self):
        self.through_margin()
        self.entry(2, duplicate=True)
        # Validation refuses the identity collision, retains the response, and ends the run.
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.assert_blocked()
        second = self.db.execute("SELECT * FROM broker_attempts WHERE leg_no = 2").fetchone()
        self.assertEqual(second["outcome"], "unknown")
        self.assertIn('"tradeID":"102"', second["response_json"])

    def test_a12_exit_before_target_stops_sequence(self):
        self.inputs()
        self.entry()
        close = order_fill(104, "102", units=self.units, price=self.stop, order_id=103)
        self.live(changes={"state": "CLOSED", "currentUnits": "0"}, records=[close])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(self.row("trade_legs")["exit_price"], self.stop)

    def test_a12_exit_during_target_confirmation_stops_trade_2(self):
        self.inputs()
        self.entry()
        self.live()
        self.target_order()
        close = order_fill(105, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        self.live(target=True, changes={"state": "CLOSED", "currentUnits": "0"}, records=[close])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()

    def test_a12_exit_during_second_margin_read_stops_trade_2(self):
        close = order_fill(105, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        self.through_margin(records=[close])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(len([c for c in self.transport.calls if c.method == "POST"]), 1)

    def test_a12_exit_before_second_fill_is_incomplete(self):
        self.through_margin()
        close = order_fill(105, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        self.entry(2, extra=[close])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()

    def test_a12_exit_in_establishment_batch_is_incomplete(self):
        self.through_margin()
        close = order_fill(109, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        close["batchID"] = "106"
        self.entry(2, extra=[close])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()

    def test_a12_exit_after_establishment_in_same_response_is_normal(self):
        self.through_margin()
        close = order_fill(109, "102", units=self.units, price=self.target, reason="TAKE_PROFIT_ORDER", order_id=104)
        self.entry(2, extra=[close])
        self.assertEqual(self.run_candidate(), "completed")
        self.assertEqual(self.row("trade_sets")["establishment_status"], "complete")
        self.assertEqual(self.row("trade_legs")["broker_state"], "closed")
        self.assertEqual(self.row("trade_legs")["exit_reason"], "TAKE_PROFIT_ORDER")
        self.assertEqual(self.db.execute("SELECT count(*) FROM issues").fetchone()[0], 0)

    def test_a12_live_mutations_remain_disabled(self):
        with PracticeBroker(self.bound) as broker:
            with self.assertRaises(ValueError):
                enter_candidate(self.db, broker, run_id=self.run_id, pair="EUR-USD")
            with self.assertRaises(ValueError):
                broker.enter_trade("EUR-USD", units="1", distance="0.00150", client_id="test")
            with self.assertRaises(ValueError):
                broker.set_target("102", "1.10100")
        self.assertIsNone(self.row("pair_decisions"))

    def test_a12_each_send_sees_committed_intent_and_prior_outcomes(self):
        self.through_margin()
        self.entry(2)
        sends = 0
        for index, (call, response) in enumerate(self.steps):
            if call.method == "GET":
                continue
            sends += 1
            def observed(response=response, expected=sends):
                self.assertFalse(self.db.in_transaction)
                with open_readonly(self.root, self.bound.experiment) as reader:
                    attempts = reader.execute("SELECT * FROM broker_attempts ORDER BY rowid").fetchall()
                    self.assertEqual(len(attempts), expected)
                    self.assertEqual(attempts[-1]["outcome"], "prepared")
                    self.assertEqual([r["outcome"] for r in attempts[:-1]], ["confirmed"] * (expected - 1))
                    self.assertEqual(reader.execute("SELECT count(*) FROM trade_legs").fetchone()[0], 2)
                    self.assertIsNone(reader.execute("SELECT outcome FROM pair_decisions").fetchone()[0])
                    if expected == 2:
                        self.assertEqual(reader.execute("SELECT entry_price FROM trade_legs WHERE leg_no = 1").fetchone()[0], "1.10000")
                        self.assertEqual(reader.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "103")
                    if expected == 3:
                        self.assertEqual(reader.execute("SELECT confirmed_target FROM trade_legs WHERE leg_no = 1").fetchone()[0], self.target)
                        self.assertEqual(reader.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "104")
                return response
            self.steps[index] = call, observed
        self.assertEqual(self.run_candidate(), "completed")

    def test_a12_reservation_commit_failure_prevents_all_sends(self):
        self.inputs()
        def fail(*args, **kwargs):
            with interrupt_commit(self.db):
                reserve_set(*args, **kwargs)
        with patch("nnfx_practice.entry.reserve_set", side_effect=fail):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertIsNone(self.row("trade_sets"))
        self.assertIsNone(self.row("trade_legs"))
        self.assertIsNone(self.row("broker_attempts"))

    def test_a12_prepare_commit_failure_leaves_reservation_without_send(self):
        self.inputs()
        def fail(*args, **kwargs):
            with interrupt_commit(self.db):
                prepare_attempt(*args, **kwargs)
        with patch("nnfx_practice.entry.prepare_attempt", side_effect=fail):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertIsNone(self.row("broker_attempts"))
        self.assertEqual(self.row("trade_sets")["establishment_status"], "pending")
        self.next_blocked_run()

    def test_a12_crash_after_prepare_before_send_keeps_uncertainty(self):
        self.inputs()
        with patch.object(PracticeBroker, "enter_trade", side_effect=Interrupted("before send")):
            with self.assertRaises(Interrupted):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("broker_attempts")["outcome"], "prepared")
        broker = PracticeBroker(self.bound, transport=ScriptedTransport((Call("GET", ROOT), reply(account(100)))))
        reconcile_snapshot(self.db, broker)
        self.assert_blocked()
        self.next_blocked_run()

    def test_a12_crash_after_fill_commit_never_creates_replacement_leg(self):
        self.inputs()
        self.entry()
        with patch.object(PracticeBroker, "trade", side_effect=Interrupted("after fill commit")):
            with self.assertRaises(Interrupted):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("trade_legs")["entry_price"], "1.10000")
        self.assertEqual(self.row("broker_attempts")["outcome"], "confirmed")
        self.next_blocked_run()

    def test_a12_crash_after_target_commit_never_sends_trade_2(self):
        self.inputs()
        self.entry()
        self.live()
        self.target_order()
        original = PracticeBroker.trade
        calls = 0
        def interrupt(broker, identifier):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise Interrupted("after target commit")
            return original(broker, identifier)
        with patch.object(PracticeBroker, "trade", new=interrupt):
            with self.assertRaises(Interrupted):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("trade_legs")["confirmed_target"], self.target)
        self.next_blocked_run()

    def test_a12_outcome_commit_failure_retains_prepared_attempt_for_reconciliation(self):
        self.inputs()
        response = self.entry()
        self.steps.pop()  # No history read is possible after an outcome write fails.
        call, _ = self.steps[-1]
        def sent():
            self.db.set_authorizer(lambda action, arg, *_: sqlite3.SQLITE_DENY
                                   if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK)
            return response
        self.steps[-1] = call, sent
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        finally:
            self.db.set_authorizer(None)
        self.transport.assert_consumed()
        self.assertEqual(self.row("broker_attempts")["outcome"], "prepared")
        self.assertIsNone(self.row("fills"))
        trade = open_trade("102", units=self.units, initial=self.units, stop_id="103", stop_price=self.stop)
        broker = PracticeBroker(self.bound, transport=ScriptedTransport(
            (Call("GET", ROOT), reply(account(103, trades=[trade]))),
            (Call("GET", ROOT + "/transactions/sinceid?id=100"), reply(history(103, *self.records))),
        ))
        reconcile_snapshot(self.db, broker)
        self.assertEqual(self.row("trade_legs")["entry_price"], "1.10000")
        self.assert_blocked()
        self.next_blocked_run()

    def test_a12_establishment_commit_failure_never_claims_completion(self):
        from nnfx_practice.entry import _Candidate
        self.through_margin()
        self.entry(2)
        original = _Candidate.establish
        def fail(candidate):
            with interrupt_commit(self.db):
                return original(candidate)
        with patch.object(_Candidate, "establish", new=fail):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("trade_sets")["establishment_status"], "pending")
        self.assertIsNone(self.row("pair_decisions")["outcome"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills WHERE effect = 'open'").fetchone()[0], 2)
        self.next_blocked_run()

    def test_a12_pair_outcome_commit_failure_preserves_complete_set(self):
        self.through_margin()
        self.entry(2)
        def fail(*args, **kwargs):
            with interrupt_commit(self.db):
                finish_pair(*args, **kwargs)
        with patch("nnfx_practice.entry.finish_pair", side_effect=fail):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("trade_sets")["establishment_status"], "complete")
        self.assertIsNone(self.row("pair_decisions")["outcome"])
        self.next_blocked_run()

    def test_a12_capture_commit_failure_prevents_sizing(self):
        self.candle()
        call, response = self.steps[-1]
        def fail():
            self.db.set_authorizer(lambda action, arg, *_: sqlite3.SQLITE_DENY
                                   if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK)
            return response
        self.steps[-1] = call, fail
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        finally:
            self.db.set_authorizer(None)
        self.transport.assert_consumed()
        self.assertIsNone(self.row("pair_decisions")["capture_json"])
        self.assertIsNone(self.row("trade_sets"))

    def test_a12_sizing_evidence_commit_failure_prevents_reservation(self):
        from nnfx_practice.entry import _Candidate
        self.inputs()
        original = _Candidate.save
        def fail(candidate):
            if candidate.plan:
                with interrupt_commit(self.db):
                    # save runs inside the caller's transaction; deny the pending commit.
                    original(candidate)
                    raise sqlite3.OperationalError("injected sizing evidence failure")
            else:
                original(candidate)
        with patch.object(_Candidate, "save", new=fail):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_candidate()
        self.transport.assert_consumed()
        self.assertIsNone(self.row("trade_sets"))
        self.assertNotIn("sizing", json.loads(self.row("pair_decisions")["sizing_json"]))

    def test_a12_response_history_failure_is_fatal_and_preserves_response(self):
        self.inputs()
        self.entry()
        call, _ = self.steps[-1]
        self.steps[-1] = call, reply({}, 503)
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.transport.assert_consumed()
        self.assert_blocked()
        self.assertEqual(self.row("runs")["status"], "failed")
        self.assertEqual(self.db.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "100")
        self.assertEqual(self.row("trade_legs")["entry_price"], "1.10000")
        self.assertIsNotNone(self.row("broker_attempts")["response_json"])

    def test_a12_trade_read_history_failure_is_also_fatal(self):
        self.inputs()
        self.entry()
        self.live(records=[event(104, "HEARTBEAT")])
        call, _ = self.steps[-1]
        self.steps[-1] = call, reply({}, 503)
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.transport.assert_consumed()
        self.assertEqual(self.row("runs")["status"], "failed")
        self.assert_blocked()

    def test_a12_authentication_and_account_failure_stop_run(self):
        for status in (401, 403):
            self.fresh()
            self.inputs()
            self.steps = self.steps[:2]
            call, _ = self.steps[-1]
            self.steps[-1] = call, reply({}, status)
            with self.assertRaises(BrokerError):
                self.run_candidate()
            self.assertEqual(self.row("runs")["status"], "failed")
        self.fresh()
        self.inputs()
        call, response = self.steps[-1]
        response.body["account"]["id"] = "wrong-account"
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.assertEqual(self.row("runs")["status"], "failed")

    def test_a12_wrong_account_mutation_retains_unknown_evidence(self):
        self.inputs()
        response = self.entry()
        self.steps.pop()
        for body in response.body.values():
            if isinstance(body, dict):
                body["accountID"] = "wrong-account"
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.assert_blocked()
        self.assertIsNone(self.row("fills"))
        self.assertEqual(self.row("broker_attempts")["outcome"], "unknown")
        self.assertIsNotNone(self.row("broker_attempts")["response_json"])

    def test_a12_second_wrong_units_and_reduction_never_complete(self):
        for mode in ("wrong_units", "reduce"):
            self.fresh()
            self.through_margin()
            self.entry(2, **{mode: True})
            self.assertEqual(self.run_candidate(), "failed")
            self.assert_blocked()

    def test_a12_target_cancellation_between_reads_blocks_trade_2(self):
        self.inputs()
        self.entry()
        self.live()
        self.target_order()
        cancel = event(105, "ORDER_CANCEL", orderID="104")
        self.live(target=True, changes={"takeProfitOrder": None}, records=[cancel])
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()

    def test_a12_wrong_second_stop_and_unwanted_second_target_block(self):
        for wrong_stop in (False, True):
            self.fresh()
            self.through_margin()
            extra = [] if wrong_stop else [event(109, "TAKE_PROFIT_ORDER", tradeID="107", price=self.target, timeInForce="GTC", batchID="106")]
            self.entry(2, wrong_stop=wrong_stop, extra=extra)
            self.assertEqual(self.run_candidate(), "failed")
            self.assert_blocked()

    def test_a06_same_pair_decision_cannot_be_resumed(self):
        self.inputs()
        self.entry(reject=True)
        self.run_candidate()
        with self.assertRaises(sqlite3.IntegrityError):
            enter_candidate(self.db, PracticeBroker(self.bound, transport=ScriptedTransport()), run_id=self.run_id, pair="EUR-USD")

    def test_a03_later_atr_cannot_change_frozen_entry_or_original_stop(self):
        self.through_margin()
        self.entry(2)
        self.run_candidate()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE trade_sets SET entry_atr = '0.002'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE trade_legs SET original_stop = '1.00000'")
        self.next_blocked_run()

    def test_a12_target_and_second_fill_outcome_commits_stop_on_failure(self):
        for mutation in (2, 3):
            self.fresh()
            self.through_margin()
            self.entry(2)
            indexes = [i for i, (call, _) in enumerate(self.steps) if call.method != "GET"]
            index = indexes[mutation - 1]
            call, response = self.steps[index]
            self.steps = self.steps[:index + 1]
            def sent():
                self.db.set_authorizer(lambda action, arg, *_: sqlite3.SQLITE_DENY
                                       if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK)
                return response
            self.steps[index] = call, sent
            try:
                with self.assertRaises(sqlite3.DatabaseError):
                    self.run_candidate()
            finally:
                self.db.set_authorizer(None)
            self.transport.assert_consumed()
            attempts = self.db.execute("SELECT * FROM broker_attempts ORDER BY rowid").fetchall()
            self.assertEqual(attempts[-1]["outcome"], "prepared")
            self.assertEqual(len(attempts), mutation)
            self.assertEqual(self.db.execute("SELECT count(*) FROM fills WHERE effect = 'open'").fetchone()[0], 1)
            self.next_blocked_run()

    def test_a12_clean_rejection_history_failure_does_not_release(self):
        self.inputs()
        self.entry(reject=True)
        call, _ = self.steps[-1]
        self.steps[-1] = call, reply({}, 503)
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.assert_blocked()
        self.assertIsNone(self.row("trade_sets")["terminal_at"])

    def test_a12_post_establishment_stop_cancellation_retains_historical_completion_and_issue(self):
        self.through_margin()
        self.entry(2, extra=[event(109, "ORDER_CANCEL", orderID="108")])
        self.assertEqual(self.run_candidate(), "failed")
        self.assertEqual(self.row("trade_sets")["establishment_status"], "complete")
        self.assertEqual(self.row("issues")["code"], "post_establishment_change")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a06_equivalent_decimal_protection_strings_are_accepted(self):
        self.through_margin()
        self.entry(2)
        for _, response in self.steps:
            if not hasattr(response, "body"):
                continue
            body = response.body
            def trim(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key == "price" and isinstance(item, str) and "." in item:
                            value[key] = item.rstrip("0").rstrip(".")
                        else:
                            trim(item)
                elif isinstance(value, list):
                    for item in value:
                        trim(item)
            trim(body)
        self.assertEqual(self.run_candidate(), "completed")

    def test_a05_missing_second_conversion_stops_without_fallback(self):
        self.through_target()
        prices = pricing_body()
        next(row for row in prices["homeConversions"] if row["currency"] == "EUR").pop("positionValue")
        self.price(prices)
        self.summary()
        self.assertEqual(self.run_candidate(), "failed")
        self.assert_blocked()
        self.assertEqual(len([c for c in self.transport.calls if c.method == "POST"]), 1)

    def test_a12_margin_unavailable_is_account_wide_failure(self):
        self.inputs()
        self.steps[-1][1].body["account"].pop("marginAvailable")
        with self.assertRaises(BrokerError):
            self.run_candidate()
        self.assertEqual(self.row("runs")["status"], "failed")
        self.assertIsNone(self.row("trade_sets"))

    def test_a06_no_combined_account_risk_cap(self):
        # Other instruments' open sets do not reduce this pair's fixed per-leg budget.
        self.db.execute("INSERT INTO pair_decisions (run_id, stage, pair, pair_order, started_at) VALUES (?, 'manage_new', 'GBP-USD', 2, ?)",
                        (self.run_id, STAMP))
        reserve_set(self.db, set_id="other-set", run_id=self.run_id, pair="GBP-USD", direction="long",
                    entry_atr="0.001", stop_distance="0.00150", planned_units="6666")
        self.through_margin()
        self.entry(2)
        self.assertEqual(self.run_candidate(), "completed")
        self.assertEqual(self.db.execute("SELECT planned_units FROM trade_legs WHERE set_id = 'set-a' LIMIT 1").fetchone()[0], "6666")

    def tearDown(self):
        directory = os.environ.get("NNFX_M06_EVIDENCE_DIR")
        if directory and getattr(self, "db", None) is not None:
            root = Path(directory)
            root.mkdir(parents=True, exist_ok=True)
            tables = ("runs", "pair_decisions", "trade_sets", "trade_legs", "broker_attempts", "broker_transactions", "fills", "issues")
            evidence = {"source": "offline-scripted", "test": self.id(), "manifest_hash": self.bound.manifest.hash,
                        "requests": [asdict(call) for call in self.transport.calls] if self.transport else [],
                        "committed": {table: [dict(r) for r in self.db.execute(f"SELECT * FROM {table}")] for table in tables},
                        "integrity": self.db.execute("PRAGMA integrity_check").fetchone()[0],
                        "foreign_key_violations": [tuple(r) for r in self.db.execute("PRAGMA foreign_key_check")]}
            (root / (self._testMethodName + ".json")).write_text(json.dumps(redact(evidence, (ACCOUNT, TOKEN)), indent=2) + "\n")
        super().tearDown()
