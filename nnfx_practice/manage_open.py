"""Stage 1: reconcile, adjust eligible stops, then manage surviving pairs.

M05 uses injected scripted transports. The network transport remains GET-only;
the master lifecycle and execution qualification belong to M07 and M10.
"""

from dataclasses import asdict
from datetime import datetime
from decimal import localcontext
import json
from time import monotonic
from uuid import uuid4

from .broker import BrokerError, broker_id, money
from .candles import capture_pair_candles
from .config import PERMITTED_PAIRS
from .evidence import encode_evidence, redact
from .notebook import _check_binding, finish_pair, pair_progress, prepare_attempt, transaction
from .reconciliation import (
    _LEGS, _issue, _release_closed_sets, _update_leg,
    apply_confirmed_transactions, import_through, reconcile_snapshot,
)
from .signal_actions import exit_reasons
from .strategy import select_strategy


STAGE = "manage_open"


def _legs(db, set_id):
    return db.execute(_LEGS + " WHERE trade_legs.set_id = ? ORDER BY leg_no", (set_id,)).fetchall()


def _observe(candles, role, strategy):
    try:
        return (strategy.observe_c1 if role == "c1" else strategy.observe_exit)(candles)
    except (ArithmeticError, LookupError, TypeError, ValueError):
        # Keep a malformed calculation/output local to its indicator. The other
        # indicator must still be evaluated for a required exit.
        return strategy.EventObservation(
            "unavailable", strategy.C1_RULE_ID if role == "c1" else strategy.EXIT_RULE_ID,
            strategy.C1_OUTPUTS if role == "c1" else strategy.EXIT_OUTPUTS,
            error="indicator_calculation_failed",
        )


def _live_ids(db, snapshot_id):
    evidence = db.execute("SELECT broker_state_json FROM account_snapshots WHERE snapshot_id = ?",
                          (snapshot_id,)).fetchone()[0]
    return set(json.loads(evidence)["body"]["trades"])


def _guarded(db, leg, purpose):
    # Even a previously confirmed action is not an invitation to repair a later
    # operator change. Each leg/action can originate at most once in this release.
    if db.execute("SELECT 1 FROM broker_attempts WHERE set_id = ? AND leg_no = ? AND purpose = ?",
                  (leg["set_id"], leg["leg_no"], purpose)).fetchone():
        return True
    if purpose == "stop_to_entry":
        if leg["stop_to_entry_status"] in ("failed", "unknown", "confirmed"):
            return True
        return bool(db.execute("""
            SELECT 1 FROM issues WHERE status = 'open' AND set_id = ?
            AND (leg_no IS NULL OR leg_no = ?) AND code IN
                ('stop_to_entry', 'missing_protection', 'interrupted_set', 'queued_close')
        """, (leg["set_id"], leg["leg_no"])).fetchone())
    return bool(db.execute("""
        SELECT 1 FROM issues WHERE status = 'open' AND set_id = ?
        AND (leg_no IS NULL OR leg_no = ?) AND code IN ('signal_close', 'queued_close')
    """, (leg["set_id"], leg["leg_no"])).fetchone())


def _response_transactions(response):
    bodies = [value for key, value in response.body.items() if key.endswith("Transaction")]
    if any(not isinstance(body, dict) for body in bodies):
        raise BrokerError("Malformed mutation transaction evidence")
    identifiers = [broker_id(body.get("id")) for body in bodies]
    boundary = (response.boundary if "lastTransactionID" in response.body else
                max(identifiers, key=int, default=None))
    if boundary and any(int(identifier) > int(boundary) for identifier in identifiers):
        raise BrokerError("Mutation transaction exceeds its response boundary")
    return bodies, boundary


def _record_response(db, broker, attempt_id, response):
    """Response, confirmed effects and failure issue share one durable commit."""
    evidence = encode_evidence(response.evidence(), broker.private_values)

    def save(outcome, error=None, order_id=None, identifier=None):
        db.execute("""
            UPDATE broker_attempts SET responded_at = ?, http_status = ?, request_id = ?,
                response_json = ?, outcome = ?, error = ?, broker_order_id = ?, broker_transaction_id = ?
            WHERE attempt_id = ?
        """, (response.responded_at, response.status, response.request_id, evidence, outcome,
              error, order_id, identifier, attempt_id))

    def issue(leg, purpose, outcome):
        if purpose == "stop_to_entry":
            _update_leg(db, leg, stop_to_entry_status=("failed" if outcome in ("rejected", "cancelled") else "unknown"))
        _issue(db, purpose, attempt_id, response.responded_at,
               {"attempt_id": attempt_id, "outcome": outcome}, leg=leg, attempt_id=attempt_id)

    attempt = db.execute("SELECT * FROM broker_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
    purpose = attempt["purpose"]
    leg = _legs(db, attempt["set_id"])[attempt["leg_no"] - 1]
    try:
        bodies, boundary = _response_transactions(response)
        with transaction(db), localcontext(prec=80):
            # Retain the request identity before projecting the broker facts.
            save("unknown")
            apply_confirmed_transactions(db, broker, bodies)
            leg = _legs(db, attempt["set_id"])[attempt["leg_no"] - 1]
            current = db.execute("SELECT * FROM broker_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
            outcome = current["outcome"]
            identifier = current["broker_transaction_id"]
            order_id = current["broker_order_id"]
            # Match request transactions to this trade; HTTP success alone is
            # never confirmation. Cancelling the old stop is not the new stop.
            related = [body for body in bodies if (
                body.get("tradeID") == leg["broker_trade_id"] or
                isinstance(body.get("tradeClose"), dict) and
                body["tradeClose"].get("tradeID") == leg["broker_trade_id"]
            )]
            creations = [body for body in related if body["type"] in ("MARKET_ORDER", "STOP_LOSS_ORDER")]
            if creations:
                order_id = broker_id(creations[-1]["id"])
            if outcome not in ("confirmed", "cancelled"):
                rejects = [body for body in related if body["type"] in
                           ("MARKET_ORDER_REJECT", "STOP_LOSS_ORDER_REJECT")]
                cancels = [body for body in bodies if body.get("type") == "ORDER_CANCEL"
                           and order_id is not None and body.get("orderID") == order_id]
                if rejects:
                    outcome, identifier = "rejected", broker_id(rejects[-1]["id"])
                elif cancels:
                    outcome, identifier = "cancelled", broker_id(cancels[-1]["id"])
                elif creations and purpose == "signal_close":
                    outcome, identifier = "pending", order_id
            if purpose == "stop_to_entry" and outcome == "confirmed":
                order_id = leg["current_stop_order_id"]
            error = None if outcome == "confirmed" else f"{purpose}: {outcome}"
            save(outcome, error, order_id, identifier)
            if outcome != "confirmed" and leg["broker_state"] != "closed":
                issue(leg, purpose, outcome)
            _release_closed_sets(db, response.responded_at)
    except BrokerError as failure:
        # Validation failures roll back projections but retain the returned
        # evidence and unresolved intent before ending the run.
        with transaction(db):
            save("unknown", str(failure))
            issue(leg, purpose, "unknown")
        raise
    return boundary


def _change(db, broker, run_id, leg, purpose):
    stop = leg["entry_price"] if purpose == "stop_to_entry" else None
    if purpose == "stop_to_entry" and (stop is None or money(stop) <= 0):
        raise BrokerError("Registered trade has no usable entry price")
    attempt_id = uuid4().hex
    path = f"/trades/{leg['broker_trade_id']}/" + ("orders" if stop is not None else "close")
    payload = {"stopLoss": {"price": stop, "timeInForce": "GTC"}} if stop is not None else {"units": "ALL"}
    prepare_attempt(
        db, broker.binding, attempt_id=attempt_id, run_id=run_id, stage=STAGE,
        # Stop adjustments belong to reconciliation, before signal-pair selection.
        pair=leg["pair"] if purpose == "signal_close" else None,
        set_id=leg["set_id"], leg_no=leg["leg_no"], broker_trade_id=leg["broker_trade_id"],
        purpose=purpose, method="PUT", path=path, payload=payload,
        prepared_at=datetime.fromisoformat(broker.now()),
    )
    response = broker.change_trade(leg["broker_trade_id"], stop_price=stop)
    boundary = _record_response(db, broker, attempt_id, response)
    if response.status in (401, 403):
        raise BrokerError("Broker authentication or account access failed")
    if boundary is not None:
        # Response IDs are not a history cursor. Fill the whole gap before
        # another dependent request, retaining the response if the read fails.
        import_through(db, broker, boundary)
    snapshot_id = reconcile_snapshot(db, broker, purpose="management_verification")
    return _live_ids(db, snapshot_id)


def _reconciliation(db, broker, run_id):
    # Load both legs for every registered set with an open leg before reading
    # the broker. The reconciliation layer also handles unfinished entries.
    sets = db.execute("""
        SELECT * FROM trade_sets WHERE EXISTS (
            SELECT 1 FROM trade_legs WHERE trade_legs.set_id = trade_sets.set_id AND broker_state = 'open'
        )
    """).fetchall()
    registered = {row["set_id"]: _legs(db, row["set_id"]) for row in sets}
    if any(len(legs) != 2 for legs in registered.values()):
        raise BrokerError("Registered set does not contain both expected legs")
    snapshot_id = reconcile_snapshot(db, broker, purpose="manage_open")
    live = _live_ids(db, snapshot_id)
    if db.execute("SELECT 1 FROM issues WHERE status = 'open' AND pair IS NULL").fetchone():
        raise BrokerError("Unresolved account-wide issue prevents trade management")
    if any(row["pair"] not in PERMITTED_PAIRS for row in sets):
        raise BrokerError("Registered trade uses an unpermitted pair")
    sets = sorted(sets, key=lambda row: PERMITTED_PAIRS.index(row["pair"]))
    adjustments = []
    for row in sets:
        one, two = _legs(db, row["set_id"])
        if one["broker_state"] != "closed" or one["exit_reason"] != "TAKE_PROFIT_ORDER":
            continue
        action = "closed" if two["broker_state"] == "closed" else "unresolved"
        if two["broker_trade_id"] in live and two["broker_state"] == "open":
            if two["current_stop_order_id"] and two["current_stop"] is not None and (
                money(two["current_stop"]) == money(two["entry_price"])
            ):
                with transaction(db):
                    _update_leg(db, two, stop_to_entry_status="confirmed")
                action = "already_at_entry"
            elif _guarded(db, two, "stop_to_entry"):
                action = "operator_required"
            else:
                with transaction(db):
                    _update_leg(db, two, stop_to_entry_status="due")
                live = _change(db, broker, run_id, two, "stop_to_entry")
                action = "attempted"
        adjustments.append({"set_id": row["set_id"], "pair": row["pair"], "action": action})
    with transaction(db):
        db.execute("""
            UPDATE stages SET reconciliation_progress_json = ? WHERE run_id = ? AND stage = ?
        """, (encode_evidence({"snapshot_id": snapshot_id, "registered_sets": list(registered),
                              "stop_adjustments": adjustments}, broker.private_values), run_id, STAGE))
    return live


def _pair(db, broker, run_id, row, live, strategy):
    pair, set_id = row["pair"], row["set_id"]
    with transaction(db):
        db.execute("""
            INSERT INTO pair_decisions (run_id, stage, pair, pair_order, started_at, set_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, STAGE, pair, PERMITTED_PAIRS.index(pair) + 1, broker.now(), set_id))
        db.execute("UPDATE stages SET current_step = '3.2', current_pair = ? WHERE run_id = ? AND stage = ?",
                   (pair, run_id, STAGE))
        db.execute("UPDATE runs SET last_progress_at = ? WHERE run_id = ?", (broker.now(), run_id))
    if all(leg["broker_state"] in ("closed", "not_opened") for leg in _legs(db, set_id)):
        finish_pair(db, broker.binding, run_id=run_id, stage=STAGE, pair=pair,
                    ended_at=datetime.fromisoformat(broker.now()), outcome="completed",
                    reason="Broker confirmed closure while managing an earlier pair")
        return live
    capture = capture_pair_candles(db, broker, run_id=run_id, stage=STAGE, pair=pair)
    if capture.metadata["http_status"] in (401, 403):
        raise BrokerError("Broker authentication or account access failed")
    outcome, reason = "completed", "No opposite event; surviving trades retained"
    if capture.candles is None:
        outcome, reason = "skipped", capture.metadata["reason"]
    else:
        # These two observations are independent; no ATR is needed for exits.
        c1 = _observe(capture.candles, "c1", strategy)
        exit_signal = _observe(capture.candles, "exit", strategy)
        triggers = exit_reasons(row["direction"], c1=c1.direction, exit_signal=exit_signal.direction)
        survivors = [{"leg_no": leg["leg_no"], "trade_id": leg["broker_trade_id"],
                      "state": leg["broker_state"], "units": leg["current_units"],
                      "confirmed_live": leg["broker_trade_id"] in live} for leg in _legs(db, set_id)]
        with transaction(db):
            db.execute("""
                UPDATE pair_decisions SET c1_json = ?, exit_json = ?, triggers_json = ?, requested_action = ?
                WHERE run_id = ? AND stage = ? AND pair = ?
            """, (encode_evidence(asdict(c1), broker.private_values),
                  encode_evidence(asdict(exit_signal), broker.private_values),
                  encode_evidence({"reasons": triggers, "legs": survivors}, broker.private_values),
                  "close" if triggers else "hold", run_id, STAGE, pair))
            db.execute("UPDATE stages SET current_step = '3.4' WHERE run_id = ? AND stage = ?", (run_id, STAGE))
        if triggers:
            for number in (1, 2):
                leg = _legs(db, set_id)[number - 1]
                if leg["broker_state"] == "closed":
                    continue
                if leg["broker_trade_id"] not in live or _guarded(db, leg, "signal_close"):
                    continue
                live = _change(db, broker, run_id, leg, "signal_close")
            remaining = [leg for leg in _legs(db, set_id) if leg["broker_state"] not in ("closed", "not_opened")]
            outcome = "failed" if remaining else "completed"
            reason = "Required close remains unconfirmed or guarded" if remaining else "All surviving legs confirmed closed"
        if c1.error or exit_signal.error:
            outcome, reason = "failed", reason + "; indicator calculation failed"
        elif not triggers and "unavailable" in (c1.direction, exit_signal.direction):
            outcome, reason = "skipped", "Indicator input unavailable; no eligible opposite event"
    issue = db.execute("SELECT issue_id FROM issues WHERE pair = ? AND status = 'open' LIMIT 1", (pair,)).fetchone()
    if issue:
        outcome, reason = "failed", reason + "; unresolved broker issue"
        with transaction(db):
            db.execute("UPDATE pair_decisions SET issue_id = ? WHERE run_id = ? AND stage = ? AND pair = ?",
                       (issue[0], run_id, STAGE, pair))
    finish_pair(db, broker.binding, run_id=run_id, stage=STAGE, pair=pair,
                ended_at=datetime.fromisoformat(broker.now()), outcome=outcome, reason=reason)
    return live


def manage_open(db, broker, *, run_id, elapsed=monotonic):
    """Run Stage 1 once; return its status. Fatal reads raise, write failures stop."""
    _check_binding(db, broker.binding)
    if db.in_transaction:
        raise ValueError("Stage 1 requires an idle notebook connection")
    strategy = select_strategy(broker.binding)
    broker.require_controller_execution()
    start = elapsed()
    with transaction(db):
        changed = db.execute("""
            UPDATE stages SET status = 'running', started_at = ?, current_step = '3.1'
            WHERE run_id = ? AND stage = ? AND status = 'not_started'
            AND EXISTS (SELECT 1 FROM runs WHERE runs.run_id = stages.run_id AND status = 'running'
                        AND strategy_hash = ? AND lookback_candles = ?)
        """, (broker.now(), run_id, STAGE, broker.binding.manifest.hash, strategy.LOOKBACK_CANDLES))
        if changed.rowcount != 1:
            raise ValueError("Stage 1 requires a new, matching run and cannot resume an unfinished stage")
    try:
        live = _reconciliation(db, broker, run_id)
        pairs = db.execute("""
            SELECT * FROM trade_sets WHERE EXISTS (
                SELECT 1 FROM trade_legs WHERE trade_legs.set_id = trade_sets.set_id AND broker_state = 'open'
            )
        """).fetchall()
        pairs = [row for row in pairs if any(leg["broker_trade_id"] in live and leg["broker_state"] == "open"
                                            for leg in _legs(db, row["set_id"]))]
        pairs = sorted(pairs, key=lambda row: PERMITTED_PAIRS.index(row["pair"]))
        with transaction(db):
            db.execute("UPDATE stages SET expected_pair_count = ? WHERE run_id = ? AND stage = ?",
                       (len(pairs), run_id, STAGE))
        for row in pairs:
            live = _pair(db, broker, run_id, row, live, strategy)
    except BrokerError as failure:
        with transaction(db):
            db.execute("""
                UPDATE stages SET status = 'failed', ended_at = ?, duration_seconds = ?, failure_summary = ?
                WHERE run_id = ? AND stage = ?
            """, (broker.now(), elapsed() - start, redact(str(failure), broker.private_values), run_id, STAGE))
            db.execute("UPDATE stages SET status = 'blocked' WHERE run_id = ? AND stage = 'manage_new'", (run_id,))
            db.execute("UPDATE runs SET status = 'failed', ended_at = ?, last_progress_at = ? WHERE run_id = ?",
                       (broker.now(), broker.now(), run_id))
        raise
    failures = pair_progress(db, run_id, STAGE)["failed"]
    issues = db.execute("SELECT count(*) FROM issues WHERE status = 'open'").fetchone()[0]
    status = "completed_with_errors" if failures or issues else "completed"
    with transaction(db):
        db.execute("""
            UPDATE stages SET status = ?, ended_at = ?, duration_seconds = ?, current_step = '3.6',
                current_pair = NULL, failure_summary = ? WHERE run_id = ? AND stage = ?
        """, (status, broker.now(), elapsed() - start,
              f"{failures} failed pair decisions; {issues} open issues" if failures or issues else None, run_id, STAGE))
        db.execute("UPDATE runs SET last_progress_at = ? WHERE run_id = ?", (broker.now(), run_id))
    return status
