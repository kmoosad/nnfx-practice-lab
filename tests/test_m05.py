"""M05 A03/A07/A10–A12: broker-shaped scripts, never practice execution."""

from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

from nnfx_practice.broker import BrokerError, PracticeBroker
from nnfx_practice.config import ConfigurationError
from nnfx_practice.manage_open import manage_open
from nnfx_practice.notebook import open_readonly, pair_is_available, pair_progress, prepare_attempt, transaction
from nnfx_practice.reconciliation import record_confirmed_transactions
from strategies import t3_bandpass_v1 as selected

from .support import ACCOUNT, TOKEN, Call, Interrupted, NotebookCase, ScriptedTransport, interrupt_commit
from . import test_m02 as m02
from .test_m02 import ROOT, account, event, history, open_trade, order_fill, reply
from .test_m03 import daily_body


class ManageOpenChecks(NotebookCase):
    opening = m02.ReconciliationChecks.opening
    register = m02.ReconciliationChecks.register

    def setUp(self):
        self.fresh()

    def fresh(self, *, direction="long", pairs=("EUR-USD",)):
        super().setUp()
        registry = self.root / "config.toml"
        registry.write_text(registry.read_text().replace('strategy_version = "fixture-v1"',
                                                      'strategy_version = "t3_bandpass_v1"'))
        manifest = self.root / "strategies/t3_bandpass_v1/manifest.json"
        manifest.parent.mkdir()
        manifest.write_bytes(Path(selected.__file__).with_name("manifest.json").read_bytes())
        self.write_private(count=386)
        self.bound = self.binding()
        self.db = self.notebook(self.bound)
        self.opening(self.db)
        units = "1000" if direction == "long" else "-1000"
        self.trades = []
        for index, pair in enumerate(pairs):
            ids = (str(40 + 20 * index), str(41 + 20 * index))
            self.register(set_id=f"set-{index}", pair=pair, direction=direction, trade_ids=ids,
                          units=units, stop_ids=(str(50 + 20 * index), str(51 + 20 * index)))
            for leg, identifier in enumerate(ids, 1):
                self.trades.append(open_trade(identifier, leg=leg, units=units, initial=units,
                                              name=pair.replace("-", "_"), stop_id=str(49 + 20 * index + leg)))
        self.cursor = 100
        self.steps = []
        self.run_id = "manage-1"
        self.start_run(self.db, self.run_id)

    def snapshot(self, trades=None, *records, boundary=None, extra=()):
        trades = self.trades if trades is None else trades
        boundary = boundary or (max(int(row["id"]) for row in records) if records else self.cursor)
        self.steps.append((Call("GET", ROOT), reply(account(boundary, trades=trades))))
        if boundary != self.cursor:
            self.steps.append((Call("GET", ROOT + f"/transactions/sinceid?id={self.cursor}"),
                               reply(history(boundary, *records))))
        self.steps.extend(extra)
        self.cursor = boundary

    def candles(self, pair="EUR-USD", *, count=386, callback=None, status=200, flat=False):
        body = daily_body(self.clock.now().date(), count=count)
        body["instrument"] = pair.replace("-", "_")
        if flat:
            for candle in body["candles"]:
                candle["mid"] = dict.fromkeys(("o", "h", "l", "c"), "1.10000")
        response = reply(body, status)
        self.steps.append((Call("GET", ROOT + f"/instruments/{pair.replace('-', '_')}/candles?price=M&granularity=D"
                                "&count=386&smooth=false&dailyAlignment=17&alignmentTimezone=America%2FNew_York"),
                           callback or response))
        return response

    def mutation(self, trade_id, *, stop=None, response=None, bodies=(), trades=None,
                 boundary=None, history_records=None, after_records=(), callback=None):
        boundary = boundary or (max(int(row["id"]) for row in bodies) if bodies else self.cursor)
        if response is None:
            fields = {"MARKET_ORDER": "orderCreateTransaction", "ORDER_FILL": "orderFillTransaction",
                      "MARKET_ORDER_REJECT": "orderRejectTransaction", "ORDER_CANCEL": "orderCancelTransaction",
                      "STOP_LOSS_ORDER": "stopLossOrderTransaction", "STOP_LOSS_ORDER_REJECT": "stopLossOrderRejectTransaction"}
            response = reply({"lastTransactionID": str(boundary), **{fields[row["type"]]: row for row in bodies}})
        payload = {"units": "ALL"} if stop is None else {"stopLoss": {"price": stop, "timeInForce": "GTC"}}
        suffix = "close" if stop is None else "orders"
        self.steps.append((Call("PUT", ROOT + f"/trades/{trade_id}/{suffix}", payload), callback or response))
        if response.body.get("lastTransactionID") is not None and int(response.body["lastTransactionID"]) != self.cursor:
            self.steps.append((Call("GET", ROOT + f"/transactions/sinceid?id={self.cursor}"),
                               reply(history(boundary, *(bodies if history_records is None else history_records)))))
            self.cursor = boundary
        self.snapshot(self.trades if trades is None else trades, *after_records)

    def observation(self, direction, role, error=None):
        return selected.EventObservation(direction, selected.C1_RULE_ID if role == "c1" else selected.EXIT_RULE_ID,
                                         selected.C1_OUTPUTS if role == "c1" else selected.EXIT_OUTPUTS,
                                         (direction == "long", direction == "short"), (False, False), error)

    def run_stage(self, *, c1="no_event", exit_signal="no_event", errors=(None, None), real=False):
        transport = ScriptedTransport(*self.steps)
        broker = PracticeBroker(self.bound, transport=transport, now=self.clock.now)
        self.transport = transport
        self.steps = []
        with ExitStack() as stack:
            if not real:
                stack.enter_context(patch.object(selected, "observe_c1", return_value=self.observation(c1, "c1", errors[0])))
                stack.enter_context(patch.object(selected, "observe_exit", return_value=self.observation(exit_signal, "exit", errors[1])))
            result = manage_open(self.db, broker, run_id=self.run_id, elapsed=self.clock.monotonic)
        transport.assert_consumed()
        return result

    def decision(self, pair="EUR-USD"):
        return self.db.execute("SELECT * FROM pair_decisions WHERE run_id = ? AND stage = 'manage_open' AND pair = ?",
                               (self.run_id, pair)).fetchone()

    def leg(self, number=2, set_id="set-0"):
        return self.db.execute("SELECT * FROM trade_legs WHERE set_id = ? AND leg_no = ?", (set_id, number)).fetchone()

    def next_run(self):
        self.clock.advance(86400)
        self.run_id = "manage-2"
        self.start_run(self.db, self.run_id)

    def take_profit(self, *, already=False):
        close = order_fill(101, 40, reason="TAKE_PROFIT_ORDER", order_id=52)
        if already:
            broker = PracticeBroker(self.bound, transport=ScriptedTransport(), now=self.clock.now)
            record_confirmed_transactions(self.db, broker, [close])
        self.snapshot([self.trades[1]], close)

    def stop_success(self):
        stop = event(102, "STOP_LOSS_ORDER", tradeID="41", price="1.10000")
        survivor = deepcopy(self.trades[1])
        survivor["stopLossOrder"].update(id="102", price="1.10000")
        self.mutation(41, stop="1.10000", bodies=[stop], trades=[survivor])
        return survivor

    def test_a07_long_short_independent_opposites_and_both_triggers(self):
        for direction in ("long", "short"):
            opposite = "short" if direction == "long" else "long"
            for c1, exit_signal, expected in ((opposite, "no_event", ["c1"]), ("no_event", opposite, ["exit"]),
                                              (opposite, opposite, ["c1", "exit"]),
                                              ("unavailable", opposite, ["exit"]), (opposite, "unavailable", ["c1"])):
                with self.subTest(direction=direction, c1=c1, exit_signal=exit_signal):
                    self.fresh(direction=direction)
                    self.snapshot()
                    self.candles()
                    for number in (1, 2):
                        close = order_fill(100 + number, 39 + number, reason="MARKET_ORDER_TRADE_CLOSE",
                                           units=self.trades[number - 1]["currentUnits"])
                        self.mutation(39 + number, bodies=[close], trades=self.trades[number:])
                    self.assertEqual(self.run_stage(c1=c1, exit_signal=exit_signal), "completed")
                    self.assertEqual(json.loads(self.decision()["triggers_json"])["reasons"], expected)
                    self.assertEqual(self.decision()["outcome"], "completed")
                    self.assertTrue(pair_is_available(self.db, "EUR-USD"))
                    self.assertEqual([row[0] for row in self.db.execute("SELECT outcome FROM broker_attempts")],
                                     ["confirmed", "confirmed"])

    def test_a07_same_direction_and_no_events_never_close(self):
        for direction in ("long", "short"):
            for signal in (direction, "no_event"):
                with self.subTest(direction=direction, signal=signal):
                    self.fresh(direction=direction)
                    self.snapshot()
                    self.candles()
                    self.assertEqual(self.run_stage(c1=signal, exit_signal=signal), "completed")
                    self.assertEqual(self.decision()["requested_action"], "hold")
                    self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)

    def test_a03_real_strategy_exact_window_without_recalculating_atr_or_levels(self):
        self.snapshot()
        self.candles(flat=True)
        frozen = [tuple(row) for row in self.db.execute("SELECT entry_atr, stop_distance FROM trade_sets")]
        with patch.object(selected, "sizing_atr", side_effect=AssertionError("Management must not calculate entry ATR")):
            self.assertEqual(self.run_stage(real=True), "completed")
        self.assertEqual(json.loads(self.decision()["capture_json"])["received_count"], 386)
        self.assertEqual(json.loads(self.decision()["c1_json"])["rule_id"], selected.C1_RULE_ID)
        self.assertEqual(self.leg()["original_stop"], "1.09000")
        self.assertEqual(frozen, [tuple(row) for row in self.db.execute("SELECT entry_atr, stop_distance FROM trade_sets")])

    def test_a03_invalid_atr_and_failed_c1_do_not_suppress_exit(self):
        self.snapshot()
        response = self.candles(flat=True)
        from nnfx_practice.candles import capture_daily_candles
        broker = PracticeBroker(self.bound, transport=ScriptedTransport((self.steps[-1][0], response)), now=self.clock.now)
        candles = capture_daily_candles(broker, "EUR-USD", session_date=self.clock.now().date()).candles
        self.assertEqual(selected.sizing_atr(candles).value, 0.0)
        for number in (1, 2):
            self.mutation(39 + number, bodies=[order_fill(100 + number, 39 + number)], trades=self.trades[number:])
        with (patch.object(selected.c1, "calculate", side_effect=ValueError("bad calculation")),
              patch.object(selected, "observe_exit", return_value=self.observation("short", "exit")),
              patch.object(selected, "sizing_atr", side_effect=AssertionError("ATR must not gate exits"))):
            self.assertEqual(self.run_stage(real=True), "completed_with_errors")
        self.assertEqual(json.loads(self.decision()["triggers_json"])["reasons"], ["exit"])
        self.assertEqual(self.leg()["broker_state"], "closed")
        self.assertIn("calculation failed", self.decision()["reason"])

    def test_a03_unavailable_candles_and_indicators_are_visible(self):
        for count, status in ((385, 200), (387, 200), (386, 503)):
            with self.subTest(count=count, status=status):
                self.fresh()
                self.snapshot()
                self.candles(count=count, status=status)
                self.run_stage(c1="short", exit_signal="short")
                self.assertEqual(self.decision()["outcome"], "skipped")
                self.assertIsNone(self.decision()["c1_json"])
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)
        self.fresh()
        self.snapshot()
        self.candles()
        self.run_stage(c1="unavailable", exit_signal="unavailable")
        self.assertEqual(self.decision()["outcome"], "skipped")

    def test_a03_changed_binding_rejected_before_broker_calls(self):
        from dataclasses import replace
        for bound in (replace(self.bound, connection=replace(self.bound.connection, lookback_candles=385)),
                      replace(self.bound, manifest=replace(self.bound.manifest, hash="f" * 64))):
            with self.subTest(bound=bound):
                with self.assertRaises(ConfigurationError):
                    manage_open(self.db, PracticeBroker(bound, transport=ScriptedTransport()), run_id=self.run_id)

    def test_a10_new_and_previously_recorded_tp_adjust_before_unavailable_candles(self):
        for already in (False, True):
            with self.subTest(already=already):
                self.fresh()
                self.take_profit(already=already)
                self.stop_success()
                self.candles(count=385)
                self.assertEqual(self.run_stage(), "completed")
                self.assertEqual(self.leg()["stop_to_entry_status"], "confirmed")
                self.assertEqual(self.leg()["current_stop"], "1.10000")
                self.assertEqual(self.leg()["original_stop"], "1.09000")
                self.assertEqual(self.leg()["current_stop_order_id"], "102")
                self.assertEqual(self.decision()["outcome"], "skipped")

    def test_a10_short_stop_uses_trade_twos_own_fill_and_zero_new_atr(self):
        self.fresh(direction="short")
        self.trades[1]["price"] = "1.10007"
        self.take_profit()
        stop = event(102, "STOP_LOSS_ORDER", tradeID="41", price="1.10007")
        survivor = deepcopy(self.trades[1])
        survivor["stopLossOrder"].update(id="102", price="1.10007")
        self.mutation(41, stop="1.10007", bodies=[stop], trades=[survivor])
        self.candles(flat=True)
        self.run_stage()
        self.assertEqual(self.leg()["current_stop"], "1.10007")
        self.assertEqual(self.leg()["original_stop"], "1.09000")

    def test_a10_already_equal_or_closed_never_changes_stop(self):
        self.trades[1]["stopLossOrder"]["price"] = "1.10000"
        self.take_profit()
        self.candles()
        self.run_stage()
        self.assertEqual(self.leg()["stop_to_entry_status"], "confirmed")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)
        self.fresh()
        self.snapshot([], order_fill(101, 40, reason="TAKE_PROFIT_ORDER"), order_fill(102, 41))
        self.run_stage()
        self.assertEqual(self.leg()["broker_state"], "closed")
        self.assertEqual(self.db.execute("SELECT expected_pair_count FROM stages WHERE run_id = ? AND stage = 'manage_open'",
                                         (self.run_id,)).fetchone()[0], 0)

    def test_a10_intervening_closure_is_not_a_confirmed_stop_adjustment(self):
        self.take_profit()
        close = order_fill(102, 41, reason="STOP_LOSS_ORDER")
        self.mutation(41, stop="1.10000", bodies=[close], trades=[])
        self.run_stage()
        self.assertEqual(self.leg()["broker_state"], "closed")
        self.assertNotEqual(self.leg()["stop_to_entry_status"], "confirmed")
        self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "cancelled")
        self.assertEqual(self.leg()["exit_reason"], "STOP_LOSS_ORDER")

    def test_a10_stop_rejection_does_not_suppress_valid_exit(self):
        self.take_profit()
        reject = event(102, "STOP_LOSS_ORDER_REJECT", tradeID="41", rejectReason="STOP_LOSS_ON_FILL_PRICE_DISTANCE_MAXIMUM_EXCEEDED")
        self.mutation(41, stop="1.10000", bodies=[reject], trades=[self.trades[1]])
        self.candles()
        self.mutation(41, bodies=[order_fill(103, 41, reason="MARKET_ORDER_TRADE_CLOSE")], trades=[])
        self.assertEqual(self.run_stage(exit_signal="short"), "completed_with_errors")
        self.assertEqual([row[0] for row in self.db.execute("SELECT outcome FROM broker_attempts ORDER BY rowid")],
                         ["rejected", "confirmed"])
        self.assertEqual(self.leg()["stop_to_entry_status"], "failed")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a11_missing_both_legs_preserves_individual_broker_causes(self):
        for reasons in (("STOP_LOSS_ORDER", "STOP_LOSS_ORDER"), ("TAKE_PROFIT_ORDER", "STOP_LOSS_ORDER"),
                        ("MARKET_ORDER_TRADE_CLOSE", "STOP_LOSS_ORDER")):
            with self.subTest(reasons=reasons):
                self.fresh()
                self.snapshot([], order_fill(101, 40, reason=reasons[0], price="1.10100"),
                              order_fill(102, 41, reason=reasons[1], price="1.09900"))
                self.run_stage()
                self.assertEqual((self.leg(1)["exit_reason"], self.leg(2)["exit_reason"]), reasons)
                self.assertEqual((self.leg(1)["exit_price"], self.leg(2)["exit_price"]), ("1.10100", "1.09900"))
                self.assertTrue(pair_is_available(self.db, "EUR-USD"))

    def test_a11_missing_without_closure_does_not_close_or_allow_entry(self):
        missing = ((Call("GET", ROOT + "/trades/40"), reply({}, 404)),
                   (Call("GET", ROOT + "/orders/50"), reply({}, 404)))
        self.snapshot([self.trades[1]], extra=missing)
        self.candles()
        self.mutation(41, bodies=[order_fill(101, 41)], trades=[])
        # Verification again has no closing evidence for Trade 1.
        self.steps.extend(missing)
        self.assertEqual(self.run_stage(c1="short"), "completed_with_errors")
        self.assertEqual(self.leg(1)["broker_state"], "open")
        self.assertIsNone(self.leg(1)["exit_at"])
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))
        self.assertEqual([call.path for call in self.transport.calls if call.method == "PUT"], [ROOT + "/trades/41/close"])

    def test_a07_intervening_second_leg_closure_avoids_second_request(self):
        self.snapshot()
        self.candles()
        first = order_fill(101, 40, reason="MARKET_ORDER_TRADE_CLOSE")
        second = order_fill(102, 41, reason="STOP_LOSS_ORDER")
        self.mutation(40, bodies=[first], trades=[], after_records=[second])
        self.run_stage(c1="short", exit_signal="short")
        self.assertEqual(self.leg()["exit_reason"], "STOP_LOSS_ORDER")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)
        self.assertEqual(json.loads(self.decision()["triggers_json"])["reasons"], ["c1", "exit"])

    def prior_attempt(self, purpose, outcome, *, leg=2):
        identifier = f"prior-{purpose}"
        if purpose == "signal_close":
            self.add_decision(self.db, stage="manage_open")
        prepare_attempt(self.db, self.bound, attempt_id=identifier, run_id="run-a", stage="manage_open",
                        purpose=purpose, method="PUT", path=f"/trades/{39 + leg}/" +
                        ("orders" if purpose == "stop_to_entry" else "close"),
                        prepared_at=self.clock.now(), set_id="set-0", leg_no=leg,
                        pair="EUR-USD" if purpose == "signal_close" else None,
                        broker_trade_id=str(39 + leg), payload=(
                            {"stopLoss": {"price": "1.10000", "timeInForce": "GTC"}}
                            if purpose == "stop_to_entry" else {"units": "ALL"}))
        self.db.execute("UPDATE broker_attempts SET outcome = ? WHERE attempt_id = ?", (outcome, identifier))
        # Failed requests have an issue; a crash before its response leaves only
        # the prepared attempt, which reconciliation must expose itself.
        if outcome != "prepared":
            self.db.execute("""
                INSERT INTO issues (issue_id, pair, code, first_observed_at, last_observed_at,
                                    set_id, leg_no, attempt_id, status)
                VALUES ('old-issue', 'EUR-USD', ?, ?, ?, 'set-0', ?, ?, 'open')
            """, (purpose, self.clock.now().isoformat(), self.clock.now().isoformat(), leg, identifier))
        return identifier

    def test_a10_prior_failed_and_uncertain_stops_guard_each_next_run(self):
        for outcome in ("prepared", "pending", "unknown", "rejected", "cancelled"):
            with self.subTest(outcome=outcome):
                self.fresh()
                self.prior_attempt("stop_to_entry", outcome)
                self.take_profit()
                self.candles()
                self.assertEqual(self.run_stage(), "completed_with_errors")
                self.next_run()
                self.snapshot([self.trades[1]])
                self.candles()
                self.assertEqual(self.run_stage(), "completed_with_errors")
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)
                self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a10_later_stop_confirmation_or_closure_keeps_operator_issue(self):
        for final in ("stop", "close"):
            with self.subTest(final=final):
                self.fresh()
                identifier = self.prior_attempt("stop_to_entry", "prepared")
                self.take_profit()
                self.candles()
                self.run_stage()
                self.next_run()
                if final == "stop":
                    survivor = deepcopy(self.trades[1])
                    survivor["stopLossOrder"].update(id="102", price="1.10000")
                    self.snapshot([survivor], event(102, "STOP_LOSS_ORDER", tradeID="41", price="1.10000"))
                    self.candles()
                else:
                    self.snapshot([], order_fill(102, 41))
                self.run_stage()
                self.assertFalse(pair_is_available(self.db, "EUR-USD"))
                self.assertGreater(self.db.execute("SELECT count(*) FROM issues WHERE status = 'open'").fetchone()[0], 0)
                self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts WHERE attempt_id = ?",
                                                 (identifier,)).fetchone()[0], "confirmed" if final == "stop" else "cancelled")
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)

    def test_a12_close_rejection_or_uncertainty_guards_only_its_leg_next_run(self):
        for outcome in ("prepared", "pending", "unknown", "rejected", "cancelled"):
            with self.subTest(outcome=outcome):
                self.fresh()
                self.prior_attempt("signal_close", outcome, leg=1)
                self.snapshot()
                self.candles()
                self.mutation(41, bodies=[order_fill(101, 41)], trades=[self.trades[0]])
                self.run_stage(c1="short")
                self.next_run()
                self.snapshot([self.trades[0]])
                self.candles()
                self.run_stage(exit_signal="short")
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 2)
                self.assertEqual(self.leg(1)["broker_state"], "open")
                self.assertEqual(self.leg(2)["broker_state"], "closed")

    def test_a12_http_success_cancel_pending_and_empty_body_do_not_confirm_close(self):
        for variant in ("cancel", "pending", "empty", "404", "reject"):
            with self.subTest(variant=variant):
                self.fresh()
                self.snapshot()
                self.candles()
                created = event(101, "MARKET_ORDER", instrument="EUR_USD", reason="TRADE_CLOSE",
                                tradeClose={"tradeID": "40", "units": "ALL"})
                bodies = [] if variant in ("empty", "404") else [created]
                if variant == "cancel":
                    bodies.append(event(102, "ORDER_CANCEL", orderID="101", reason="MARKET_HALTED"))
                if variant == "reject":
                    bodies = [event(101, "MARKET_ORDER_REJECT", instrument="EUR_USD", reason="TRADE_CLOSE",
                                    tradeClose={"tradeID": "40", "units": "ALL"}, rejectReason="MARKET_HALTED")]
                response = reply({}, 404) if variant == "404" else None
                self.mutation(40, bodies=bodies, response=response)
                self.mutation(41, bodies=[order_fill(self.cursor + 1, 41)], trades=[self.trades[0]])
                self.assertEqual(self.run_stage(c1="short"), "completed_with_errors")
                attempt = self.db.execute("SELECT * FROM broker_attempts ORDER BY rowid LIMIT 1").fetchone()
                self.assertEqual(attempt["outcome"], {"cancel": "cancelled", "pending": "pending",
                                                      "reject": "rejected"}.get(variant, "unknown"))
                self.assertEqual(self.leg(1)["broker_state"], "open")
                self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_timeout_after_fill_reconciles_evidence_without_replay(self):
        self.snapshot()
        self.candles()
        def timeout():
            raise TimeoutError(TOKEN)
        self.steps.append((Call("PUT", ROOT + "/trades/40/close", {"units": "ALL"}), timeout))
        self.snapshot([self.trades[1]], order_fill(101, 40, reason="MARKET_ORDER_TRADE_CLOSE"))
        self.mutation(41, bodies=[order_fill(102, 41)], trades=[])
        self.run_stage(c1="short")
        first = self.db.execute("SELECT * FROM broker_attempts ORDER BY rowid LIMIT 1").fetchone()
        self.assertEqual(first["outcome"], "confirmed")
        self.assertIsNone(first["http_status"])
        self.assertNotIn(TOKEN, first["response_json"])
        self.assertNotIn(ACCOUNT, first["response_json"])
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a10_empty_success_or_wrong_price_does_not_confirm_stop(self):
        for wrong_price in (False, True):
            with self.subTest(wrong_price=wrong_price):
                self.fresh()
                self.take_profit()
                bodies = [event(102, "STOP_LOSS_ORDER", tradeID="41", price="1.09500")] if wrong_price else []
                survivor = deepcopy(self.trades[1])
                if wrong_price:
                    survivor["stopLossOrder"].update(id="102", price="1.09500")
                self.mutation(41, stop="1.10000", bodies=bodies, trades=[survivor])
                self.candles()
                self.run_stage()
                self.assertEqual(self.leg()["stop_to_entry_status"], "unknown")
                self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "unknown")
                self.next_run()
                self.snapshot([survivor])
                self.candles()
                self.run_stage()
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)

    def test_a07_brief_order_and_durable_observation_attempt_outcome_boundaries(self):
        self.fresh(pairs=("GBP-USD", "EUR-USD"))
        self.snapshot()
        self.candles()
        def send_first():
            self.assertFalse(self.db.in_transaction)
            with open_readonly(self.root, self.bound.experiment) as reader:
                attempt = reader.execute("SELECT * FROM broker_attempts").fetchone()
                self.assertEqual((attempt["outcome"], attempt["broker_trade_id"]), ("prepared", "60"))
                observation = reader.execute("SELECT triggers_json FROM pair_decisions WHERE stage = 'manage_open'").fetchone()[0]
                self.assertEqual(json.loads(observation)["reasons"], ["c1", "exit"])
            return reply({"lastTransactionID": "101", "orderFillTransaction": order_fill(101, 60)})
        self.mutation(60, bodies=[order_fill(101, 60)], trades=[*self.trades[:2], self.trades[3]], callback=send_first)
        def send_second():
            with open_readonly(self.root, self.bound.experiment) as reader:
                self.assertEqual([row[0] for row in reader.execute("SELECT outcome FROM broker_attempts ORDER BY rowid")],
                                 ["confirmed", "prepared"])
                self.assertEqual(reader.execute("SELECT broker_state FROM trade_legs WHERE broker_trade_id = '60'").fetchone()[0], "closed")
                self.assertEqual(reader.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "101")
            return reply({"lastTransactionID": "102", "orderFillTransaction": order_fill(102, 61)})
        self.mutation(61, bodies=[order_fill(102, 61)], trades=self.trades[:2], callback=send_second)
        def next_pair():
            with open_readonly(self.root, self.bound.experiment) as reader:
                self.assertEqual(pair_progress(reader, self.run_id, "manage_open")["finished"], 1)
                self.assertEqual(reader.execute("SELECT outcome FROM pair_decisions WHERE stage = 'manage_open' AND pair = 'EUR-USD'").fetchone()[0], "completed")
            return response
        response = self.candles("GBP-USD", callback=next_pair)
        for number in (1, 2):
            close = order_fill(102 + number, 39 + number, name="GBP_USD")
            self.mutation(39 + number, bodies=[close], trades=self.trades[number:2])
        self.run_stage(c1="short", exit_signal="short")
        self.assertEqual(pair_progress(self.db, self.run_id, "manage_open")["finished"], 2)
        self.assertEqual(self.db.execute("SELECT expected_pair_count FROM stages WHERE run_id = ? AND stage = 'manage_open'",
                                         (self.run_id,)).fetchone()[0], 2)

    def test_a12_live_transport_cannot_be_used_for_stage_or_mutations(self):
        with PracticeBroker(self.bound, now=self.clock.now) as broker:
            with self.assertRaisesRegex(ValueError, "scripted transport"):
                manage_open(self.db, broker, run_id=self.run_id)
            with self.assertRaisesRegex(ValueError, "scripted transport"):
                broker.change_trade("40")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)

    def test_a12_authentication_failure_ends_stage_and_blocks_new_trades(self):
        self.snapshot()
        self.candles(status=401)
        with self.assertRaises(BrokerError):
            self.run_stage(c1="short")
        self.assertEqual([row[0] for row in self.db.execute("SELECT status FROM stages WHERE run_id = ? ORDER BY stage",
                                                          (self.run_id,))], ["blocked", "failed"])
        self.assertEqual(self.db.execute("SELECT status FROM runs WHERE run_id = ?", (self.run_id,)).fetchone()[0], "failed")

    def test_a12_failed_attempt_commit_prevents_send_and_old_stage_cannot_resume(self):
        self.snapshot()
        self.candles()
        def fail_prepare(*args, **kwargs):
            with interrupt_commit(self.db):
                prepare_attempt(*args, **kwargs)
        with patch("nnfx_practice.manage_open.prepare_attempt", side_effect=fail_prepare):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_stage(c1="short")
        self.transport.assert_consumed()
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)
        self.assertIsNone(self.decision()["outcome"])
        with self.assertRaisesRegex(ValueError, "cannot resume"):
            self.run_stage(c1="short")

    def test_a12_crash_after_prepare_before_send_leaves_guarded_intent(self):
        self.snapshot()
        self.candles()
        with patch.object(PracticeBroker, "change_trade", side_effect=Interrupted("before send")):
            with self.assertRaises(Interrupted):
                self.run_stage(c1="short")
        self.transport.assert_consumed()
        self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "prepared")
        self.next_run()
        self.snapshot()
        self.candles()
        self.mutation(41, bodies=[order_fill(101, 41)], trades=[self.trades[0]])
        self.run_stage(c1="short")
        self.assertEqual([call.path for call in self.transport.calls if call.method == "PUT"], [ROOT + "/trades/41/close"])

    def test_a12_failed_outcome_commit_stops_after_send_and_next_run_imports_fill(self):
        self.snapshot()
        self.candles()
        close = order_fill(101, 40, reason="MARKET_ORDER_TRADE_CLOSE")
        def sent():
            def deny_commit(action, arg, *_):
                return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK
            self.db.set_authorizer(deny_commit)
            return reply({"lastTransactionID": "101", "orderFillTransaction": close})
        self.steps.append((Call("PUT", ROOT + "/trades/40/close", {"units": "ALL"}), sent))
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_stage(c1="short")
        finally:
            self.db.set_authorizer(None)
        self.transport.assert_consumed()
        self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "prepared")
        self.assertEqual(self.leg(1)["broker_state"], "open")
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 0)
        self.next_run()
        self.snapshot([self.trades[1]], close)
        self.candles()
        self.mutation(41, bodies=[order_fill(102, 41)], trades=[])
        self.run_stage(exit_signal="short")
        self.assertEqual([row[0] for row in self.db.execute("SELECT outcome FROM broker_attempts ORDER BY rowid")],
                         ["confirmed", "confirmed"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 2)
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_failed_pair_commit_prevents_next_pair_capture(self):
        from nnfx_practice.notebook import finish_pair
        self.fresh(pairs=("GBP-USD", "EUR-USD"))
        self.snapshot()
        self.candles()
        def fail_finish(*args, **kwargs):
            with interrupt_commit(self.db):
                finish_pair(*args, **kwargs)
        with patch("nnfx_practice.manage_open.finish_pair", side_effect=fail_finish):
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_stage()
        self.transport.assert_consumed()
        self.assertEqual(pair_progress(self.db, self.run_id, "manage_open")["finished"], 0)
        self.assertIsNone(self.decision("GBP-USD"))

    def test_a12_failed_capture_commit_never_calculates_or_sends(self):
        self.snapshot()
        def captured():
            def deny_commit(action, arg, *_):
                return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK
            self.db.set_authorizer(deny_commit)
            return response
        response = self.candles(callback=captured)
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                self.run_stage(c1="short")
        finally:
            self.db.set_authorizer(None)
        self.assertIsNone(self.decision()["capture_json"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)

    def test_a12_history_failure_preserves_response_but_stops_mutations(self):
        self.snapshot()
        self.candles()
        close = order_fill(105, 40)
        self.steps.extend([
            (Call("PUT", ROOT + "/trades/40/close", {"units": "ALL"}),
             reply({"lastTransactionID": "105", "orderFillTransaction": close}, request_id="close-request-105")),
            (Call("GET", ROOT + "/transactions/sinceid?id=100"), reply({}, 503)),
        ])
        with self.assertRaises(BrokerError):
            self.run_stage(c1="short")
        self.transport.assert_consumed()
        attempt = self.db.execute("SELECT * FROM broker_attempts").fetchone()
        self.assertEqual((attempt["outcome"], attempt["request_id"]), ("confirmed", "close-request-105"))
        self.assertEqual(self.leg(1)["broker_state"], "closed")
        self.assertEqual(self.leg(2)["broker_state"], "open")
        self.assertEqual(self.db.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "100")
        self.assertIsNotNone(attempt["response_json"])

    def test_a12_wrong_account_transaction_is_retained_as_failure_not_confirmation(self):
        self.snapshot()
        self.candles()
        close = order_fill(101, 40)
        close["accountID"] = "wrong-account"
        self.steps.append((Call("PUT", ROOT + "/trades/40/close", {"units": "ALL"}),
                           reply({"lastTransactionID": "101", "orderFillTransaction": close})))
        with self.assertRaises(BrokerError):
            self.run_stage(c1="short")
        self.transport.assert_consumed()
        attempt = self.db.execute("SELECT * FROM broker_attempts").fetchone()
        self.assertEqual(attempt["outcome"], "unknown")
        self.assertNotIn("wrong-account", attempt["response_json"])
        self.assertEqual(self.leg(1)["broker_state"], "open")

    def test_a11_retrieve_both_absent_trade_and_stop_references(self):
        self.db.execute("UPDATE trade_legs SET broker_state_transaction_id = '90'")
        extra = []
        for trade, stop, identifier, cause in ((40, 50, 95, "TAKE_PROFIT_ORDER"), (41, 51, 96, "STOP_LOSS_ORDER")):
            extra.extend([
                (Call("GET", ROOT + f"/trades/{trade}"), reply({"trade": {
                    "id": str(trade), "state": "CLOSED", "closingTransactionIDs": [str(identifier)]}})),
                (Call("GET", ROOT + f"/orders/{stop}"), reply({"order": {
                    "id": str(stop), "tradeID": str(trade), "state": "FILLED", "fillingTransactionID": str(identifier)}})),
                (Call("GET", ROOT + f"/transactions/{identifier}"), reply({"transaction": order_fill(identifier, trade, reason=cause)})),
            ])
        self.snapshot([], extra=extra)
        self.run_stage()
        self.assertEqual((self.leg(1)["exit_reason"], self.leg(2)["exit_reason"]), ("TAKE_PROFIT_ORDER", "STOP_LOSS_ORDER"))
        self.assertEqual(self.db.execute("SELECT count(*) FROM fills").fetchone()[0], 2)

    def test_a10_all_pairs_stop_management_precedes_first_signal_capture(self):
        self.fresh(pairs=("EUR-USD", "GBP-USD"))
        tp = order_fill(101, 60, reason="TAKE_PROFIT_ORDER", name="GBP_USD")
        self.snapshot([*self.trades[:2], self.trades[3]], tp)
        changed = deepcopy(self.trades[3])
        changed["stopLossOrder"].update(id="102", price="1.10000")
        self.mutation(61, stop="1.10000", bodies=[event(102, "STOP_LOSS_ORDER", tradeID="61", price="1.10000")],
                      trades=[*self.trades[:2], changed])
        self.candles()
        self.candles("GBP-USD")
        self.run_stage()
        paths = [call.path for call in self.transport.calls]
        self.assertLess(paths.index(ROOT + "/trades/61/orders"), next(i for i, path in enumerate(paths) if "candles?" in path))

    def test_a12_missing_protection_blocks_repair_but_preserves_signal_exit(self):
        self.trades[1].pop("stopLossOrder")
        self.take_profit()
        self.candles()
        self.mutation(41, bodies=[order_fill(102, 41)], trades=[])
        self.run_stage(exit_signal="short")
        self.assertEqual([call.path for call in self.transport.calls if call.method == "PUT"], [ROOT + "/trades/41/close"])
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_failed_observation_commit_prevents_signal_close(self):
        self.snapshot()
        self.candles()
        def observed():
            def deny_commit(action, arg, *_):
                return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT" else sqlite3.SQLITE_OK
            self.db.set_authorizer(deny_commit)
            return self.observation("short", "exit")
        try:
            with patch.object(selected, "observe_exit", side_effect=lambda _: observed()):
                with self.assertRaises(sqlite3.DatabaseError):
                    self.run_stage(real=True)
        finally:
            self.db.set_authorizer(None)
        self.transport.assert_consumed()
        self.assertIsNotNone(self.decision()["capture_json"])
        self.assertIsNone(self.decision()["triggers_json"])
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)

    def test_a12_response_without_watermark_still_requires_history_through_its_fills(self):
        self.snapshot()
        self.candles()
        close = order_fill(105, 40)
        self.steps.extend([
            (Call("PUT", ROOT + "/trades/40/close", {"units": "ALL"}), reply({"orderFillTransaction": close})),
            (Call("GET", ROOT + "/transactions/sinceid?id=100"), reply(history(105, close))),
        ])
        self.cursor = 105
        self.snapshot([self.trades[1]])
        self.mutation(41, bodies=[order_fill(106, 41)], trades=[])
        self.run_stage(c1="short")
        self.assertEqual(self.db.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0], "106")

    def test_a12_later_cancel_or_reject_resolves_known_request_and_keeps_guard(self):
        for purpose, outcome in (("signal_close", "cancelled"), ("stop_to_entry", "rejected")):
            with self.subTest(purpose=purpose):
                self.fresh()
                identifier = self.prior_attempt(purpose, "pending")
                self.db.execute("UPDATE broker_attempts SET request_id = 'saved-request', broker_order_id = '99' WHERE attempt_id = ?",
                                (identifier,))
                if purpose == "signal_close":
                    activity = event(101, "ORDER_CANCEL", orderID="99", reason="MARKET_HALTED")
                else:
                    activity = event(101, "STOP_LOSS_ORDER_REJECT", tradeID="41", rejectReason="MARKET_HALTED")
                activity["requestID"] = "saved-request"
                self.snapshot(self.trades, activity)
                self.candles()
                self.run_stage()
                self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts WHERE attempt_id = ?",
                                                 (identifier,)).fetchone()[0], outcome)
                self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)
                self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_other_legs_fill_is_not_confirmation_of_requested_close(self):
        self.snapshot()
        self.candles()
        self.mutation(40, bodies=[order_fill(101, 41)], trades=[self.trades[0]])
        self.run_stage(c1="short")
        self.assertEqual(self.db.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "unknown")
        self.assertEqual(self.leg(1)["broker_state"], "open")
        self.assertEqual(self.leg(2)["broker_state"], "closed")

    def test_a12_partial_reduction_does_not_confirm_all_units_closed(self):
        self.snapshot()
        self.candles()
        remaining = deepcopy(self.trades[0])
        remaining["currentUnits"] = "600"
        reduction = order_fill(101, 40, units="400", effect="reduce", reason="MARKET_ORDER_TRADE_CLOSE")
        self.mutation(40, bodies=[reduction], trades=[remaining, self.trades[1]])
        self.mutation(41, bodies=[order_fill(102, 41)], trades=[remaining])
        self.run_stage(c1="short")
        first = self.db.execute("SELECT outcome FROM broker_attempts ORDER BY rowid LIMIT 1").fetchone()[0]
        self.assertEqual(first, "unknown")
        self.assertEqual(self.leg(1)["current_units"], "600")
        self.assertIsNone(self.leg(1)["exit_price"])

    def test_a12_close_when_tradeable_stays_occupied_without_reissuing(self):
        self.trades[0]["state"] = "CLOSE_WHEN_TRADEABLE"
        self.snapshot()
        self.candles()
        self.mutation(41, bodies=[order_fill(101, 41)], trades=[self.trades[0]])
        self.assertEqual(self.run_stage(c1="short"), "completed_with_errors")
        self.assertEqual(self.leg(1)["broker_state"], "open")
        self.assertEqual([call.path for call in self.transport.calls if call.method == "PUT"], [ROOT + "/trades/41/close"])
        self.next_run()
        self.snapshot([self.trades[0]])
        self.candles()
        self.run_stage(c1="short")
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 1)
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a07_malformed_indicator_output_keeps_the_other_exit_eligible(self):
        self.snapshot()
        self.candles()
        for number in (1, 2):
            self.mutation(39 + number, bodies=[order_fill(100 + number, 39 + number)], trades=self.trades[number:])
        with (patch.object(selected, "observe_c1", side_effect=KeyError("missing output")),
              patch.object(selected, "observe_exit", return_value=self.observation("short", "exit"))):
            self.assertEqual(self.run_stage(real=True), "completed_with_errors")
        self.assertEqual(self.leg()["broker_state"], "closed")
        self.assertEqual(json.loads(self.decision()["triggers_json"])["reasons"], ["exit"])
