"""M06: one fresh candidate decision and a conditional, scripted two-leg sequence.

The M07 master owns the 4.1 balance and 28-pair loop. This component never
initializes/activates a notebook or enables live mutations, repairs or retries.
"""

from dataclasses import asdict
from datetime import datetime
from decimal import localcontext
from itertools import groupby
import json
from pathlib import Path
from uuid import uuid4

from strategies import t3_bandpass_v1 as strategy

from .broker import BrokerError, broker_id, instrument, money
from .candles import capture_pair_candles
from .config import ConfigurationError, PERMITTED_PAIRS
from .evidence import canonical_json, encode_evidence, redact
from .ledger import fill_details
from .manage_open import _legs, _observe, _response_transactions
from .notebook import _check_binding, finish_pair, pair_is_available, prepare_attempt, reserve_set, transaction
from .preflight import _one_row, _tradeable_price
from .reconciliation import _issue, _release_closed_sets, apply_confirmed_transactions, import_through
from .signal_actions import entry_signal
from .sizing import levels, margin_requirement, size_candidate


STAGE = "manage_new"


class EntryFailure(ValueError):
    """Pair-local failure; actual effects and operator block must be retained."""


class _Candidate:
    def __init__(self, db, broker, run_id, pair):
        self.db, self.broker, self.run_id, self.pair = db, broker, run_id, pair
        self.set_id = None
        self.evidence = {"reads": []}
        self.plan = None

    def save(self):
        self.db.execute("UPDATE pair_decisions SET sizing_json = ? WHERE run_id = ? AND stage = ? AND pair = ?",
                        (encode_evidence(self.evidence, self.broker.private_values), self.run_id, STAGE, self.pair))

    def read(self, purpose, call, *, history=False, account=False):
        try:
            result = call()
        except BrokerError as failure:
            self.evidence["reads"].append({"purpose": purpose, "failure": str(failure), "evidence": failure.evidence})
            with transaction(self.db):
                self.save()
            if account or failure.status in (401, 403):
                raise
            raise EntryFailure(str(failure)) from None
        self.evidence["reads"].append({"purpose": purpose, **result.evidence()})
        with transaction(self.db):
            self.save()
        if account:
            money(result.body["account"].get("marginAvailable"))
        if history:
            import_through(self.db, self.broker, result.boundary)
            self.account_guard()
        return result

    def account_guard(self):
        if self.db.execute("SELECT 1 FROM issues WHERE status = 'open' AND pair IS NULL").fetchone():
            raise BrokerError("Unresolved account-wide issue prevents entry")

    def incomplete(self, reason, attempt_id=None):
        self.db.execute("UPDATE trade_sets SET establishment_status = 'incomplete' WHERE set_id = ?",
                        (self.set_id,))
        # An unsent expected leg is known not opened. Sent uncertainty stays null.
        self.db.execute("""
            UPDATE trade_legs SET broker_state = 'not_opened' WHERE set_id = ? AND broker_trade_id IS NULL
            AND NOT EXISTS (SELECT 1 FROM broker_attempts a WHERE a.set_id = trade_legs.set_id
                            AND a.leg_no = trade_legs.leg_no AND a.purpose = 'entry')
        """, (self.set_id,))
        _issue(self.db, "incomplete_entry", self.set_id, self.broker.now(), {"reason": reason},
               pair=self.pair, set_id=self.set_id, attempt_id=attempt_id)

    def response(self, attempt_id, response, *, target=None):
        """Commit returned facts and any immediate failure together before advancing."""
        db, broker = self.db, self.broker
        attempt = db.execute("SELECT * FROM broker_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()

        def save_response(outcome="unknown", error=None):
            db.execute("""
                UPDATE broker_attempts SET responded_at = ?, http_status = ?, request_id = ?, response_json = ?,
                    outcome = ?, error = ? WHERE attempt_id = ?
            """, (response.responded_at, response.status, response.request_id,
                  encode_evidence(response.evidence(), broker.private_values), outcome, error, attempt_id))

        try:
            bodies, boundary = _response_transactions(response)
            with transaction(db), localcontext(prec=80):
                save_response()
                apply_confirmed_transactions(db, broker, bodies)
                current = db.execute("SELECT * FROM broker_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
                outcome = current["outcome"]
                if target is not None:
                    related = [b for b in bodies if b.get("tradeID") == attempt["broker_trade_id"]]
                    confirmed = [b for b in related if b["type"] == "TAKE_PROFIT_ORDER"
                                 and b.get("timeInForce") == "GTC" and money(b.get("price")) == money(target)]
                    rejected = [b for b in related if b["type"] == "TAKE_PROFIT_ORDER_REJECT"]
                    outcome = "confirmed" if confirmed else "rejected" if rejected else "unknown"
                    if confirmed or rejected:
                        last = (confirmed or rejected)[-1]
                        db.execute("UPDATE broker_attempts SET broker_transaction_id = ?, broker_order_id = ? WHERE attempt_id = ?",
                                   (last["id"], last["id"] if confirmed else None, attempt_id))
                error = None
                if target is None and outcome == "confirmed":
                    error = self.fill_error(attempt["leg_no"])
                if outcome != "confirmed":
                    error = f"{attempt['purpose']}: {outcome}"
                save_response(outcome, error)
                if error:
                    # A definite whole-set no-fill may release after the full history check.
                    if target is None and outcome in ("rejected", "cancelled"):
                        db.execute("UPDATE trade_legs SET broker_state = 'not_opened' WHERE set_id = ? AND leg_no = ? AND broker_trade_id IS NULL",
                                   (self.set_id, attempt["leg_no"]))
                    if not (attempt["leg_no"] == 1 and target is None and outcome in ("rejected", "cancelled")):
                        self.incomplete(error, attempt_id)
        except BrokerError as failure:
            with transaction(db):
                save_response(error=str(failure))
                self.incomplete(str(failure), attempt_id)
            raise
        if response.status in (401, 403):
            raise BrokerError("Broker authentication or account access failed")
        if boundary is not None:
            import_through(db, broker, boundary)
        self.account_guard()
        if error:
            raise EntryFailure(error)
        if db.execute("SELECT 1 FROM issues WHERE status = 'open' AND pair = ?", (self.pair,)).fetchone():
            raise EntryFailure("Broker activity left an unresolved pair issue")

    def fill_error(self, number):
        leg = _legs(self.db, self.set_id)[number - 1]
        attempt = self.db.execute("SELECT * FROM broker_attempts WHERE set_id = ? AND leg_no = ? AND purpose = 'entry'",
                                  (self.set_id, number)).fetchone()
        fills = self.db.execute("SELECT * FROM fills WHERE transaction_id = ?", (attempt["broker_transaction_id"],)).fetchall()
        if len(fills) != 1 or fills[0]["effect"] != "open" or fills[0]["broker_trade_id"] != leg["broker_trade_id"]:
            return "Entry did not open exactly one distinct trade without reductions"
        if money(fills[0]["units"]) != money(self.plan["signed_units"]):
            return "Entry fill has wrong units"
        try:
            levels(fills[0]["price"], self.plan["atr"], self.plan["stop_distance"], self.direction,
                   self.plan["display_precision"], with_target=number == 1)
        except BrokerError as failure:
            return str(failure)
        return None

    def send_entry(self, number):
        attempt_id = uuid4().hex
        client_id = "entry-" + attempt_id
        payload = {"order": {
            "type": "MARKET", "instrument": instrument(self.pair), "units": self.plan["signed_units"],
            "timeInForce": "FOK", "positionFill": "OPEN_ONLY", "clientExtensions": {"id": client_id},
            "tradeClientExtensions": {"id": client_id},
            "stopLossOnFill": {"distance": self.plan["stop_distance"], "timeInForce": "GTC"},
        }}
        self.prepare(attempt_id, number, "entry", "POST", "/orders", payload, client_id=client_id)
        result = self.broker.enter_trade(self.pair, units=self.plan["signed_units"],
                                         distance=self.plan["stop_distance"], client_id=client_id)
        self.response(attempt_id, result)

    def prepare(self, attempt_id, number, purpose, method, path, payload, **kwargs):
        if self.db.execute("SELECT 1 FROM broker_attempts WHERE set_id = ? AND leg_no = ? AND purpose = ?",
                           (self.set_id, number, purpose)).fetchone():
            raise EntryFailure("An earlier attempt prevents automatic retry")
        prepare_attempt(self.db, self.broker.binding, attempt_id=attempt_id, run_id=self.run_id, stage=STAGE,
                        pair=self.pair, set_id=self.set_id, leg_no=number, purpose=purpose, method=method,
                        path=path, payload=payload, prepared_at=datetime.fromisoformat(self.broker.now()), **kwargs)

    def live_one(self, *, target):
        leg = _legs(self.db, self.set_id)[0]
        result = self.read("trade_1_protection" if target else "trade_1_stop",
                           lambda: self.broker.trade(leg["broker_trade_id"]), history=True)
        try:
            return self.validate_live_one(result.body["trade"], target=target)
        except BrokerError as failure:
            raise EntryFailure(str(failure)) from None

    def validate_live_one(self, trade, *, target):
        leg = _legs(self.db, self.set_id)[0]
        expected = levels(leg["entry_price"], self.plan["atr"], self.plan["stop_distance"], self.direction,
                          self.plan["display_precision"])
        if (trade.get("state") != "OPEN" or leg["broker_state"] != "open"
                or trade.get("instrument") != instrument(self.pair)
                or money(trade.get("initialUnits")) != money(self.plan["signed_units"])
                or money(trade.get("currentUnits")) != money(self.plan["signed_units"])
                or money(trade.get("price")) != money(leg["entry_price"])):
            raise EntryFailure("Trade 1 did not survive intact before establishment")
        for key, kind, price, order_id in (
            ("stopLossOrder", "STOP_LOSS", expected["stop"], leg["current_stop_order_id"]),
            ("takeProfitOrder", "TAKE_PROFIT", expected["target"], leg["target_order_id"]),
        ):
            if key == "takeProfitOrder" and not target:
                if trade.get(key) is not None:
                    raise EntryFailure("Unexpected target before its requested establishment")
                continue
            order = trade.get(key)
            if (not isinstance(order, dict) or order.get("state") != "PENDING" or order.get("type") != kind
                    or order.get("timeInForce") != "GTC" or order.get("id") != order_id
                    or order.get("tradeID") != leg["broker_trade_id"] or money(order.get("price")) != money(price)):
                raise EntryFailure("Trade 1 is missing its required fill-relative protection")
        return expected

    def establish(self):
        """Prove coexistence at a complete broker batch, even with a later price exit."""
        legs = _legs(self.db, self.set_id)
        if any(self.fill_error(number) for number in (1, 2)):
            raise EntryFailure("Both entry fills must match their requests")
        identities = [leg["broker_trade_id"] for leg in legs]
        if None in identities or len(set(identities)) != 2:
            raise EntryFailure("Two distinct broker trade IDs are required")
        expected = {leg["broker_trade_id"]: levels(leg["entry_price"], self.plan["atr"], self.plan["stop_distance"],
                    self.direction, self.plan["display_precision"], with_target=leg["leg_no"] == 1) for leg in legs}
        state = {identifier: {"open": False, "STOP_LOSS": None, "TAKE_PROFIT": None} for identifier in identities}
        rows = self.db.execute("SELECT body_json FROM broker_transactions ORDER BY length(transaction_id), transaction_id")
        records = [json.loads(row[0]) for row in rows]
        for _, batch in groupby(records, key=lambda body: body.get("batchID", body["id"])):
            batch = list(batch)
            for body in batch:
                for effect, identifier, units, _, _ in fill_details(body):
                    if identifier in state:
                        if effect != "open" or units != money(self.plan["signed_units"]):
                            raise EntryFailure("A leg exited or was reduced before set establishment")
                        state[identifier]["open"] = True
                kind, identifier = body["type"], body.get("tradeID")
                if kind in ("STOP_LOSS_ORDER", "TAKE_PROFIT_ORDER") and identifier in state:
                    field = kind.removesuffix("_ORDER")
                    if field == "TAKE_PROFIT" and identifier == identities[1]:
                        raise EntryFailure("Trade 2 must have no take-profit target")
                    desired = expected[identifier]["stop" if field == "STOP_LOSS" else "target"]
                    if body.get("timeInForce") != "GTC" or money(body.get("price")) != money(desired):
                        raise EntryFailure("Broker protection differs from frozen fill-relative levels")
                    state[identifier][field] = body["id"]
                if kind == "ORDER_CANCEL":
                    for item in state.values():
                        for field in ("STOP_LOSS", "TAKE_PROFIT"):
                            if item[field] == body.get("orderID"):
                                item[field] = None
            one, two = (state[identifier] for identifier in identities)
            if one["open"] and two["open"] and one["STOP_LOSS"] and two["STOP_LOSS"] and one["TAKE_PROFIT"] and not two["TAKE_PROFIT"]:
                proof = {"transaction_id": batch[-1]["id"], "batch_id": batch[-1].get("batchID"),
                         "trade_ids": identities, "protection": state, "at": batch[-1]["time"]}
                with transaction(self.db):
                    self.evidence["establishment"] = proof
                    self.save()
                    self.db.execute("UPDATE trade_sets SET establishment_status = 'complete', established_at = ? WHERE set_id = ?",
                                    (proof["at"], self.set_id))
                    _release_closed_sets(self.db, self.broker.now())
                return
        raise EntryFailure("Both distinct fills and required protection were not established together")

    def sequence(self):
        self.send_entry(1)
        expected = self.live_one(target=False)
        one = _legs(self.db, self.set_id)[0]
        with transaction(self.db):
            self.db.execute("UPDATE trade_legs SET intended_target = ? WHERE set_id = ? AND leg_no = 1",
                            (expected["target"], self.set_id))
            self.evidence["trade_1_levels"] = expected
            self.save()
        attempt_id = uuid4().hex
        self.prepare(attempt_id, 1, "entry_target", "PUT", f"/trades/{one['broker_trade_id']}/orders",
                     {"takeProfit": {"price": expected["target"], "timeInForce": "GTC"}}, broker_trade_id=one["broker_trade_id"])
        self.response(attempt_id, self.broker.set_target(one["broker_trade_id"], expected["target"]), target=expected["target"])
        self.live_one(target=True)
        prices = self.read("trade_2_pricing", lambda: self.broker.pricing(self.pair))
        summary = self.read("trade_2_margin", self.broker.summary, history=True, account=True)
        check = _tradeable_price(prices.body, self.pair)
        if check["validation"] != "valid":
            raise EntryFailure(check["reason"])
        try:
            margin = margin_requirement(self.plan["units"], self.metadata, prices.body, summary.body["account"],
                                        self.broker.binding.connection.home_currency, self.pair, 1)
        except BrokerError as failure:
            raise EntryFailure(str(failure)) from None
        with transaction(self.db):
            self.evidence["trade_2_margin"] = margin
            self.save()
        if not margin["sufficient"]:
            raise EntryFailure("Insufficient margin before Trade 2; no resized fallback")
        # Margin/history reads can themselves reveal a price exit or cancellation.
        one = _legs(self.db, self.set_id)[0]
        if (one["broker_state"] != "open" or money(one["current_units"]) != money(self.plan["signed_units"])
                or one["current_stop"] is None or one["confirmed_target"] is None
                or money(one["current_stop"]) != money(expected["stop"])
                or money(one["confirmed_target"]) != money(expected["target"])):
            raise EntryFailure("Trade 1 changed before Trade 2")
        self.send_entry(2)
        self.establish()
        for leg in _legs(self.db, self.set_id):
            if leg["broker_state"] == "closed":
                continue
            expected = levels(leg["entry_price"], self.plan["atr"], self.plan["stop_distance"], self.direction,
                              self.plan["display_precision"], with_target=leg["leg_no"] == 1)
            if (leg["current_stop"] is None or money(leg["current_stop"]) != money(expected["stop"])
                    or money(leg["current_units"]) != money(self.plan["signed_units"])
                    or (leg["leg_no"] == 1 and (leg["confirmed_target"] is None
                        or money(leg["confirmed_target"]) != money(expected["target"])))
                    or (leg["leg_no"] == 2 and leg["confirmed_target"] is not None)):
                raise EntryFailure("Surviving trade changed after establishment; operator review required")

    def fail_set(self, reason):
        if self.set_id is None:
            return
        with transaction(self.db):
            if self.db.execute("SELECT establishment_status FROM trade_sets WHERE set_id = ?", (self.set_id,)).fetchone()[0] == "complete":
                _issue(self.db, "post_establishment_change", self.set_id, self.broker.now(), {"reason": reason},
                       pair=self.pair, set_id=self.set_id)
                return
            attempts = self.db.execute("SELECT * FROM broker_attempts WHERE set_id = ?", (self.set_id,)).fetchall()
            legs = _legs(self.db, self.set_id)
            issues = self.db.execute("SELECT 1 FROM issues WHERE pair = ? AND status = 'open'", (self.pair,)).fetchone()
            clean = (len(attempts) == 1 and attempts[0]["purpose"] == "entry" and attempts[0]["leg_no"] == 1
                     and attempts[0]["outcome"] in ("rejected", "cancelled") and not issues
                     and all(leg["broker_trade_id"] is None for leg in legs))
            if clean:
                self.db.execute("UPDATE trade_legs SET broker_state = 'not_opened' WHERE set_id = ?", (self.set_id,))
                self.db.execute("UPDATE trade_sets SET establishment_status = 'not_opened', terminal_at = ? WHERE set_id = ?",
                                (self.broker.now(), self.set_id))
            else:
                self.incomplete(reason)

    def finish(self, outcome, reason):
        with transaction(self.db):
            issue = self.db.execute("SELECT issue_id FROM issues WHERE pair = ? AND status = 'open' LIMIT 1", (self.pair,)).fetchone()
            self.db.execute("UPDATE pair_decisions SET issue_id = ? WHERE run_id = ? AND stage = ? AND pair = ?",
                            (issue[0] if issue else None, self.run_id, STAGE, self.pair))
        finish_pair(self.db, self.broker.binding, run_id=self.run_id, stage=STAGE, pair=self.pair,
                    ended_at=datetime.fromisoformat(self.broker.now()), outcome=outcome, reason=reason)
        return outcome

    def run(self):
        if not pair_is_available(self.db, self.pair):
            with transaction(self.db):
                self.db.execute("""UPDATE pair_decisions SET requested_action = 'skip', set_id = (
                    SELECT s.set_id FROM trade_sets s WHERE s.pair = ? AND (s.terminal_at IS NULL OR EXISTS (
                        SELECT 1 FROM trade_legs l WHERE l.set_id = s.set_id AND (l.broker_state IS NULL OR l.broker_state = 'open')
                    )) LIMIT 1) WHERE run_id = ? AND stage = ? AND pair = ?""",
                    (self.pair, self.run_id, STAGE, self.pair))
            return self.finish("skipped", "Pair is occupied or blocked")
        capture = capture_pair_candles(self.db, self.broker, run_id=self.run_id, stage=STAGE, pair=self.pair)
        if capture.metadata["http_status"] in (401, 403):
            raise BrokerError("Broker authentication or account access failed")
        if capture.candles is None:
            return self.finish("skipped", capture.metadata["reason"])
        c1 = _observe(capture.candles, "c1")
        try:
            atr = strategy.sizing_atr(capture.candles)
        except (ArithmeticError, LookupError, TypeError, ValueError):
            atr = strategy.AtrObservation(None, "atr_calculation_failed")
        signal = entry_signal(c1.direction, atr.value)
        with transaction(self.db):
            self.db.execute("UPDATE stages SET current_step = '4.3' WHERE run_id = ? AND stage = ?",
                            (self.run_id, STAGE))
            self.db.execute("""
                UPDATE pair_decisions SET c1_json = ?, atr = ?, atr_valid = ?, requested_action = ?
                WHERE run_id = ? AND stage = ? AND pair = ?
            """, (encode_evidence(asdict(c1), self.broker.private_values), str(atr.value) if atr.value is not None else None,
                  int(entry_signal("long", atr.value) is not None), "enter" if signal else "skip", self.run_id, STAGE, self.pair))
        if c1.error or atr.error:
            return self.finish("failed", c1.error or atr.error)
        if signal is None:
            return self.finish("skipped", "No fresh C1 event with valid entry ATR")
        self.direction, atr_text = signal
        with transaction(self.db):
            self.db.execute("UPDATE stages SET current_step = '4.4' WHERE run_id = ? AND stage = ?",
                            (self.run_id, STAGE))
            self.db.execute("UPDATE runs SET last_progress_at = ? WHERE run_id = ?",
                            (self.broker.now(), self.run_id))
        instruments = self.read("instrument_limits", lambda: self.broker.instruments((self.pair,)))
        pricing = self.read("sizing_pricing", lambda: self.broker.pricing(self.pair))
        summary = self.read("pre_set_margin", self.broker.summary, history=True, account=True)
        balance = self.db.execute("SELECT sizing_balance FROM runs WHERE run_id = ?", (self.run_id,)).fetchone()[0]
        try:
            self.metadata = _one_row(instruments.body, "instruments", "name", instrument(self.pair))
            self.plan = size_candidate(balance=balance, atr=atr_text, direction=self.direction, pair=self.pair,
                                       home=self.broker.binding.connection.home_currency, instruments=instruments.body,
                                       pricing=pricing.body, account=summary.body["account"], pricing_at=pricing.responded_at)
        except BrokerError as failure:
            return self.finish("skipped", str(failure))
        with transaction(self.db):
            self.evidence["sizing"] = self.plan
            self.save()
        if not self.plan["margin"]["sufficient"]:
            return self.finish("skipped", "Insufficient margin for the intended two-leg set")
        if not pair_is_available(self.db, self.pair):
            return self.finish("skipped", "Pair became occupied or blocked during pre-entry history import")
        set_id = uuid4().hex
        reserve_set(self.db, set_id=set_id, run_id=self.run_id, pair=self.pair, direction=self.direction,
                    entry_atr=atr_text, stop_distance=self.plan["stop_distance"], planned_units=self.plan["units"])
        self.set_id = set_id
        self.sequence()
        return self.finish("completed", "Both distinct fills and required protection established together")


def enter_candidate(db, broker, *, run_id, pair):
    """Process one pair once with the immutable 4.1 balance; return its committed outcome."""
    _check_binding(db, broker.binding)
    broker.require_controller_execution()
    if db.in_transaction or pair not in PERMITTED_PAIRS:
        raise ValueError("Candidate requires an idle notebook and permitted pair")
    packaged = json.loads(Path(strategy.__file__).with_name("manifest.json").read_text())
    if (broker.binding.experiment.strategy_version != "t3_bandpass_v1"
            or broker.binding.manifest.body != canonical_json(packaged)
            or broker.binding.connection.lookback_candles != strategy.LOOKBACK_CANDLES):
        raise ConfigurationError("Entry requires qualified t3_bandpass_v1 and exactly 386 candles")
    run = db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if (run is None or run["status"] != "running" or run["sizing_balance"] is None
            or run["strategy_hash"] != broker.binding.manifest.hash or run["lookback_candles"] != strategy.LOOKBACK_CANDLES):
        raise ValueError("Candidate requires a matching running run and its committed 4.1 balance")
    candidate = _Candidate(db, broker, run_id, pair)
    candidate.account_guard()
    with transaction(db):
        db.execute("INSERT INTO pair_decisions (run_id, stage, pair, pair_order, started_at) VALUES (?, ?, ?, ?, ?)",
                   (run_id, STAGE, pair, PERMITTED_PAIRS.index(pair) + 1, broker.now()))
    try:
        return candidate.run()
    except EntryFailure as failure:
        candidate.fail_set(str(failure))
        return candidate.finish("failed" if candidate.set_id else "skipped", str(failure))
    except BrokerError as failure:
        # Account/history failures stop all entry work. Write failures propagate
        # untouched, leaving the last durable reservation/attempt for reconciliation.
        with transaction(db):
            if candidate.set_id:
                candidate.incomplete(str(failure))
            db.execute("UPDATE runs SET status = 'failed', ended_at = ?, last_progress_at = ? WHERE run_id = ?",
                       (broker.now(), broker.now(), run_id))
            db.execute("UPDATE stages SET status = 'failed', ended_at = ?, failure_summary = ? WHERE run_id = ? AND stage = ?",
                       (broker.now(), redact(str(failure), broker.private_values), run_id, STAGE))
        candidate.finish("failed", str(failure))
        raise
