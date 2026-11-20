"""Reconcile a bound notebook against complete OANDA practice read intervals."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import localcontext
import json
import re
from uuid import uuid4

from .broker import BrokerError, broker_id, money
from .evidence import encode_evidence, redact
from .ledger import ZERO, _TRANSACTION_KEY, _postings_between, _snapshot_key, fill_details, postings, transaction_key
from .notebook import _check_binding, transaction
from .transaction_records import merge_transaction


_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z")
_PAIR = re.compile(r"[A-Z]{3}_[A-Z]{3}")
_PROTECTION = {"STOP_LOSS": ("current_stop", "current_stop_order_id"),
               "TAKE_PROFIT": ("confirmed_target", "target_order_id")}
_LEGS = """
    SELECT trade_legs.*, trade_sets.pair, trade_sets.direction FROM trade_legs
    JOIN trade_sets USING (set_id)
"""


class _Records(dict):
    """A fetched batch's merged facts and the actual bodies behind them."""

    def __init__(self):
        super().__init__()
        self.sources = {}

    def add(self, body):
        identifier = broker_id(body.get("id"))
        if identifier in self:
            try:
                self[identifier] = merge_transaction(self[identifier], body)
            except BrokerError as failure:
                raise BrokerError("Conflicting transactions share a broker ID", evidence=failure.evidence) from None
        else:
            self[identifier] = body
        self.sources.setdefault(identifier, []).append(body)


def _time(value):
    if isinstance(value, str) and _TIME.fullmatch(value):
        try:
            datetime.fromisoformat(value)
        except ValueError:
            pass
        else:
            return value
    raise BrokerError("Invalid broker transaction time")


def _pair(value):
    if not isinstance(value, str) or not _PAIR.fullmatch(value):
        raise BrokerError("Broker activity cannot be isolated to an instrument")
    return value.replace("_", "-")


def _number(value):
    return int(broker_id(value))


def _cursor(db):
    cursor = db.execute("SELECT imported_through_transaction_id FROM notebook").fetchone()[0]
    if cursor is None:
        raise BrokerError("Notebook has no initialized history cursor")
    return broker_id(cursor)


def _leg(db, trade_id):
    return db.execute(_LEGS + " WHERE broker_trade_id = ?", (trade_id,)).fetchone()


def _update_leg(db, leg, **values):
    db.execute(f"UPDATE trade_legs SET {', '.join(name + ' = ?' for name in values)} "
               "WHERE set_id = ? AND leg_no = ?", (*values.values(), leg["set_id"], leg["leg_no"]))


def _issue(db, code, identity, at, evidence, *, pair=None, leg=None, set_id=None, attempt_id=None):
    if leg is not None:
        pair, set_id = leg["pair"], leg["set_id"]
    prefix = f"{code}:{identity}:"
    existing = db.execute("""
        SELECT issue_id FROM issues WHERE substr(issue_id, 1, ?) = ? AND status = 'open'
    """, (len(prefix), prefix)).fetchone()
    encoded = encode_evidence(evidence, ())
    if existing is not None:
        db.execute("""
            UPDATE issues SET last_observed_at = ?, broker_evidence_json = ?
            WHERE issue_id = ? AND last_observed_at <= ?
        """, (at, encoded, existing[0], at))
    else:
        db.execute("""
            INSERT INTO issues (issue_id, pair, code, first_observed_at, last_observed_at,
                                set_id, leg_no, attempt_id, broker_evidence_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (prefix + uuid4().hex, pair, code, at, at, set_id, leg["leg_no"] if leg else None, attempt_id, encoded))


def _history(broker, cursor, boundary, *, deferred=None):
    records = _Records()
    for body in broker.history(cursor, boundary, deferred=deferred):
        records.add(body)
    if cursor != boundary and boundary not in records:
        raise BrokerError("Broker history is missing the requested boundary transaction")
    return records


def _correlated_entry(db, body, identifier):
    """Link only an entry with an exact recorded client, order or request identity."""
    extensions = body.get("clientExtensions")
    client_id = body.get("clientOrderID") or (extensions.get("id") if isinstance(extensions, dict) else None)
    order_id = body.get("orderID")
    if body["type"] == "MARKET_ORDER":
        order_id = identifier
    request_id = body.get("requestID") if body["type"] != "ORDER_CANCEL" else None
    attempt = db.execute("""
        SELECT * FROM broker_attempts WHERE method = 'POST' AND path = '/orders'
        AND set_id IS NOT NULL AND leg_no IS NOT NULL
        AND (client_id = ? OR broker_order_id = ? OR (
            request_id = ? AND (broker_order_id IS NULL OR broker_order_id = ?)
        ))
    """, (client_id, order_id, request_id, order_id)).fetchall()
    if len(attempt) > 1:
        raise BrokerError("Broker transaction has conflicting local entry identities")
    return attempt[0] if attempt else None


def _entry_evidence(db, attempt, body, identifier, at, fills):
    if attempt is None:
        return
    kind = body["type"]
    if kind == "ORDER_FILL":
        opened = next((trade_id for effect, trade_id, *_ in fills if effect == "open"), None)
        if opened is None:
            return
        if attempt["outcome"] in ("rejected", "cancelled"):
            raise BrokerError("Entry fill contradicts the recorded broker outcome")
        leg = db.execute(_LEGS + " WHERE trade_legs.set_id = ? AND leg_no = ?",
                         (attempt["set_id"], attempt["leg_no"])).fetchone()
        if leg["broker_trade_id"] not in (None, opened) or leg["pair"] != _pair(body.get("instrument")):
            raise BrokerError("Entry fill does not match its registered leg")
        owner = _leg(db, opened)
        if owner is not None and (owner["set_id"], owner["leg_no"]) != (leg["set_id"], leg["leg_no"]):
            raise BrokerError("Entry fill matches two registered legs")
        _update_leg(db, leg, broker_trade_id=opened)
        outcome, order_id = "confirmed", body.get("orderID")
    elif kind in ("MARKET_ORDER", "MARKET_ORDER_REJECT", "ORDER_CANCEL"):
        opened = None
        outcome = {"MARKET_ORDER": "pending", "MARKET_ORDER_REJECT": "rejected", "ORDER_CANCEL": "cancelled"}[kind]
        order_id = identifier if kind == "MARKET_ORDER" else body.get("orderID")
    else:
        return
    prior = attempt["broker_transaction_id"]
    if attempt["outcome"] in ("confirmed", "rejected", "cancelled") or (prior and _number(prior) >= _number(identifier)):
        return
    db.execute("""
        UPDATE broker_attempts SET outcome = ?, broker_transaction_id = ?,
            broker_order_id = coalesce(?, broker_order_id), broker_trade_id = coalesce(?, broker_trade_id),
            request_id = coalesce(request_id, ?), responded_at = coalesce(responded_at, ?)
        WHERE attempt_id = ?
    """, (outcome, identifier, order_id, opened, body.get("requestID"), at, attempt["attempt_id"]))


def _new_enough(leg, identifier):
    return leg["broker_state_transaction_id"] is None or _number(identifier) >= _number(leg["broker_state_transaction_id"])


def _set_protection(db, leg, kind, order_id, price, boundary, at):
    if leg["broker_state"] == "closed" or not _new_enough(leg, boundary):
        return
    price_field, id_field = _PROTECTION[kind]
    values = {price_field: price, id_field: order_id, "broker_state_at": at, "broker_state_transaction_id": boundary}
    if kind == "STOP_LOSS" and price is not None:
        values["original_stop"] = leg["original_stop"] or price
        values["original_stop_order_id"] = leg["original_stop_order_id"] or order_id
    _update_leg(db, leg, **values)


def _apply_fill(db, leg, effect, units, price, body, identifier, *, complete_history):
    at = body["time"]
    if not _new_enough(leg, identifier) or leg["broker_state_transaction_id"] == identifier:
        return
    if effect == "open":
        if (units > 0) != (leg["direction"] == "long") or leg["broker_state"] in ("closed", "not_opened"):
            raise BrokerError("Opening fill contradicts registered trade state")
        _update_leg(db, leg, initial_units=str(units), current_units=str(units), broker_state="open",
                    broker_state_at=at, broker_state_transaction_id=identifier, entry_at=at,
                    entry_price=str(price) if price is not None else None)
    elif effect == "close":
        _update_leg(db, leg, broker_state="closed", current_units="0", broker_state_at=at,
                    broker_state_transaction_id=identifier, exit_at=at, exit_transaction_id=identifier,
                    exit_reason=body["reason"], current_stop=None, current_stop_order_id=None,
                    confirmed_target=None, target_order_id=None)
    elif complete_history and leg["current_units"] is not None and leg["broker_state"] == "open":
        remaining = abs(money(leg["current_units"])) - abs(units)
        if remaining <= 0:
            raise BrokerError("Trade reduction contradicts registered open units")
        if leg["direction"] == "short":
            remaining = -remaining
        _update_leg(db, leg, current_units=str(remaining), broker_state_at=at, broker_state_transaction_id=identifier)


def _exit_summary(db, leg):
    if leg["broker_state"] != "closed" or leg["initial_units"] is None or leg["exit_transaction_id"] is None:
        return
    reductions = db.execute(f"""
        SELECT units, price FROM fills WHERE broker_trade_id = ? AND effect IN ('reduce', 'close')
        AND ({_TRANSACTION_KEY}) <= (?, ?) ORDER BY {_TRANSACTION_KEY}
    """, (leg["broker_trade_id"], *transaction_key(leg["exit_transaction_id"]))).fetchall()
    volume = sum((abs(money(row["units"])) for row in reductions), ZERO)
    if volume == abs(money(leg["initial_units"])) and all(row["price"] is not None for row in reductions):
        value = sum((abs(money(row["units"])) * money(row["price"]) for row in reductions), ZERO)
        _update_leg(db, leg, exit_price=str(value / volume))


def _store(db, broker, records, at, *, complete_history, imported_before=None, observations=None):
    """Insert and project source records in broker order inside the caller's write."""
    touched = set()
    imported_before = _cursor(db) if imported_before is None else imported_before
    observations = getattr(records, 'sources', {}) if observations is None else observations
    for identifier, raw in sorted(records.items(), key=lambda item: int(item[0])):
        broker.verify_transaction(raw)
        body = redact(raw, broker.private_values)
        stamp = _time(body.get("time"))
        try:
            sources = []
            for source in observations.get(identifier, [raw]):
                broker.verify_transaction(source)
                sources.append(encode_evidence(source, broker.private_values))
        except ValueError:
            raise BrokerError("Broker transaction evidence exceeds the notebook limit",
                              evidence={"transaction_id": identifier}) from None
        prior = db.execute("SELECT body_json FROM broker_transactions WHERE transaction_id = ?", (identifier,)).fetchone()
        body = merge_transaction(json.loads(prior[0]) if prior is not None else None, body)
        try:
            merged = encode_evidence(body, ())
        except ValueError:
            raise BrokerError("Combined broker transaction evidence exceeds the notebook limit",
                              evidence={"transaction_id": identifier}) from None
        if prior is None:
            db.execute("""
                INSERT INTO broker_transactions (transaction_id, broker_at, type, batch_id, request_id, imported_at, body_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (identifier, stamp, body["type"], body.get("batchID"), body.get("requestID"), at, merged))
        elif prior[0] != merged:
            db.execute("UPDATE broker_transactions SET body_json = ? WHERE transaction_id = ?", (merged, identifier))
        db.executemany("""INSERT INTO broker_transaction_observations (transaction_id, observed_at, body_json)
                          VALUES (?, ?, ?) ON CONFLICT (transaction_id, body_json) DO NOTHING""",
                       [(identifier, at, source) for source in sources])

        fills = list(fill_details(body))
        attempt = _correlated_entry(db, body, identifier) if body["type"] in (
            "MARKET_ORDER", "MARKET_ORDER_REJECT", "ORDER_FILL", "ORDER_CANCEL"
        ) else None
        _entry_evidence(db, attempt, body, identifier, stamp, fills)
        for effect, trade_id, units, price, _ in fills:
            leg = _leg(db, trade_id)
            if leg is not None and leg["pair"] != _pair(body.get("instrument")):
                raise BrokerError("Broker fill instrument differs from the registered leg")
            if not isinstance(body.get("reason"), str):
                raise BrokerError("Broker fill reason is missing")
            order_id = broker_id(body.get("orderID"))
            db.execute("""
                INSERT INTO fills (transaction_id, broker_trade_id, effect, order_id, units, price, filled_at,
                    reason, set_id, leg_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (transaction_id, broker_trade_id, effect) DO UPDATE SET
                    set_id = excluded.set_id, leg_no = excluded.leg_no WHERE fills.set_id IS NULL
            """, (identifier, trade_id, effect, order_id, str(units), str(price) if price is not None else None,
                  stamp, body["reason"], leg["set_id"] if leg else None, leg["leg_no"] if leg else None))
            if leg is not None:
                _apply_fill(db, leg, effect, units, price, body, identifier, complete_history=complete_history)
                touched.add(trade_id)
            elif prior is None:
                _issue(db, "unexpected_trade", trade_id, at, {"trade_id": trade_id, "transaction_id": identifier},
                       pair=_pair(body.get("instrument")))

        kind = body["type"]
        if kind.removesuffix("_ORDER") in _PROTECTION and kind.endswith("_ORDER"):
            trade_id = broker_id(body.get("tradeID"))
            leg = _leg(db, trade_id)
            if leg is not None:
                price = str(money(body["price"])) if body.get("price") is not None else None
                _set_protection(db, leg, kind.removesuffix("_ORDER"), identifier, price, identifier, stamp)
        if kind in ("MARKET_ORDER", "LIMIT_ORDER", "STOP_ORDER", "MARKET_IF_TOUCHED_ORDER") and (
            attempt is None and prior is None and body.get("reason") not in ("TRADE_CLOSE", "POSITION_CLOSEOUT")
        ):
            _issue(db, "unexpected_order", identifier, at, {"order_id": identifier, "type": kind},
                   pair=_pair(body.get("instrument")))
        if kind == "ORDER_CANCEL":
            order_id = broker_id(body.get("orderID"))
            for leg in db.execute(_LEGS + " WHERE current_stop_order_id = ? OR target_order_id = ?", (order_id, order_id)):
                protection = "STOP_LOSS" if leg["current_stop_order_id"] == order_id else "TAKE_PROFIT"
                _set_protection(db, leg, protection, None, None, identifier, stamp)

        for entry in postings(body, fills):
            existing = db.execute("""SELECT amount, category, broker_trade_id, source_field, posted FROM ledger_entries
                                     WHERE transaction_id = ? AND component_key = ?""", (identifier, entry[0])).fetchone()
            if existing is not None:
                if money(existing["amount"]) != money(entry[1]) or tuple(existing)[1:] != tuple(entry[2:]):
                    raise BrokerError("Broker transaction conflicts with an existing accounting entry",
                                      evidence={"transaction_id": identifier, "source_field": entry[0]})
            elif prior is not None and entry[-1] and money(entry[1]) != ZERO and _number(identifier) <= _number(imported_before):
                raise BrokerError("New monetary posting would change already imported history",
                                  evidence={"transaction_id": identifier, "source_field": entry[0]})
            elif prior is not None and entry[-1] and money(entry[1]) != ZERO and body.get("accountBalance") is None:
                raise BrokerError("Additional monetary posting lacks broker balance evidence",
                                  evidence={"transaction_id": identifier, "source_field": entry[0]})
            if body["type"] == "ORDER_FILL" and existing is None and not entry[-1] and money(entry[1]) != ZERO:
                field = entry[0].rsplit('.', 1)[-1]
                total_field = 'pl' if field == 'realizedPL' else field
                total = body.get(total_field)
                allocations = [detail[field] for *_, detail in fills if field in detail]
                if total is None or (len(allocations) == len(fills) and
                                     sum((money(value) for value in allocations), ZERO) != money(total)):
                    raise BrokerError("Additional trade allocation lacks a matching transaction total",
                                      evidence={"transaction_id": identifier, "source_field": entry[0]})
            db.execute("""
                INSERT INTO ledger_entries (transaction_id, component_key, amount, category, broker_trade_id,
                    source_field, posted) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (transaction_id, component_key) DO NOTHING
            """, (identifier, *entry))
        _management_transaction(db, body, identifier, stamp)
    for trade_id in touched:
        _exit_summary(db, _leg(db, trade_id))
    _management_attempts(db, at)


def _management_transaction(db, body, identifier, at):
    """Correlate later rejection/cancellation/queue evidence to a known request."""
    kind = body["type"]
    if kind not in ("MARKET_ORDER", "MARKET_ORDER_REJECT", "STOP_LOSS_ORDER_REJECT", "ORDER_CANCEL"):
        return
    for attempt in db.execute("""
        SELECT * FROM broker_attempts WHERE purpose IN ('signal_close', 'stop_to_entry')
        AND outcome IN ('prepared', 'pending', 'unknown')
        AND (request_id = ? OR broker_order_id = ?)
    """, (body.get("requestID"), body.get("orderID"))).fetchall():
        leg = db.execute(_LEGS + " WHERE trade_legs.set_id = ? AND leg_no = ?",
                         (attempt["set_id"], attempt["leg_no"])).fetchone()
        trade_close = body.get("tradeClose")
        target = body.get("tradeID") or (trade_close.get("tradeID") if isinstance(trade_close, dict) else None)
        if kind == "ORDER_CANCEL":
            if body.get("orderID") != attempt["broker_order_id"]:
                continue
            outcome = "cancelled"
        elif target != leg["broker_trade_id"]:
            continue
        elif kind == "MARKET_ORDER" and attempt["purpose"] == "signal_close":
            outcome = "pending"
        elif (kind == "MARKET_ORDER_REJECT" and attempt["purpose"] == "signal_close" or
              kind == "STOP_LOSS_ORDER_REJECT" and attempt["purpose"] == "stop_to_entry"):
            outcome = "rejected"
        else:
            continue
        db.execute("""
            UPDATE broker_attempts SET outcome = ?, broker_transaction_id = ?,
                broker_order_id = coalesce(?, broker_order_id), responded_at = coalesce(responded_at, ?)
            WHERE attempt_id = ?
        """, (outcome, identifier, identifier if kind == "MARKET_ORDER" else None, at, attempt["attempt_id"]))
        if outcome in ("cancelled", "rejected"):
            if attempt["purpose"] == "stop_to_entry":
                _update_leg(db, leg, stop_to_entry_status="failed")
            _issue(db, attempt["purpose"], attempt["attempt_id"], at,
                   {"transaction_id": identifier, "outcome": outcome}, leg=leg, attempt_id=attempt["attempt_id"])


def _management_attempts(db, at):
    """Resolve observed effects without replaying requests or clearing issues."""
    for attempt in db.execute("""
        SELECT * FROM broker_attempts WHERE purpose IN ('signal_close', 'stop_to_entry')
        AND outcome IN ('prepared', 'pending', 'unknown')
    """).fetchall():
        leg = db.execute(_LEGS + " WHERE trade_legs.set_id = ? AND leg_no = ?",
                         (attempt["set_id"], attempt["leg_no"])).fetchone()
        if leg is None:
            continue
        outcome = identifier = order_id = None
        if leg["broker_state"] == "closed" and leg["exit_transaction_id"]:
            outcome = "confirmed" if attempt["purpose"] == "signal_close" else "cancelled"
            identifier = leg["exit_transaction_id"]
            if attempt["purpose"] == "signal_close":
                fill = db.execute("SELECT order_id FROM fills WHERE transaction_id = ? AND broker_trade_id = ? AND effect = 'close'",
                                  (identifier, leg["broker_trade_id"])).fetchone()
                order_id = fill[0] if fill else None
        elif attempt["purpose"] == "stop_to_entry" and leg["current_stop_order_id"] and leg["current_stop"]:
            requested = json.loads(attempt["payload_json"])["stopLoss"]["price"]
            if money(leg["current_stop"]) == money(requested):
                outcome, identifier = "confirmed", leg["current_stop_order_id"]
                order_id = leg["current_stop_order_id"]
                _update_leg(db, leg, stop_to_entry_status="confirmed")
        if outcome:
            db.execute("""
                UPDATE broker_attempts SET outcome = ?, broker_transaction_id = ?, broker_order_id = coalesce(?, broker_order_id),
                    responded_at = coalesce(responded_at, ?) WHERE attempt_id = ?
            """, (outcome, identifier, order_id, at, attempt["attempt_id"]))


def _balance_through(db, boundary):
    currency = db.execute("SELECT home_currency FROM notebook").fetchone()[0]
    snapshots = db.execute("""
        SELECT rowid, * FROM account_snapshots WHERE reconciliation_status = 'reconciled' AND home_currency = ?
    """, (currency,))
    base = max(
        (row for row in snapshots if _number(row["last_transaction_id"]) <= _number(boundary)),
        key=_snapshot_key,
        default=None,
    )
    if base is None:
        raise BrokerError("No reconciled opening balance covers the history interval")
    balance = money(base["balance"])
    totals = {}
    for row in _postings_between(db, base["last_transaction_id"], boundary):
        identifier = broker_id(row["transaction_id"])
        totals[identifier] = totals.get(identifier, ZERO) + money(row["amount"])
    rows = db.execute(f"""
        SELECT transaction_id, body_json FROM broker_transactions
        WHERE ({_TRANSACTION_KEY}) > (?, ?) AND ({_TRANSACTION_KEY}) <= (?, ?)
        ORDER BY {_TRANSACTION_KEY}
    """, (*transaction_key(base["last_transaction_id"]), *transaction_key(boundary)))
    for row in rows:
        identifier = broker_id(row["transaction_id"])
        balance += totals.get(identifier, ZERO)
        body = json.loads(row["body_json"])
        amount = body.get("accountBalance")
        if amount is not None and balance != money(amount):
            raise BrokerError("Unexplained broker transaction balance",
                              evidence={"transaction_id": identifier, "expected_balance": str(balance),
                                        "broker_balance": amount, "transaction_type": body["type"]})
    return balance


def _advance(db, cursor, boundary, records):
    if _cursor(db) != cursor:
        raise BrokerError("Imported history changed during the read; take a fresh snapshot")
    known = db.execute(f"""
        SELECT transaction_id FROM broker_transactions WHERE ({_TRANSACTION_KEY}) > (?, ?)
        AND ({_TRANSACTION_KEY}) <= (?, ?)
    """, (*transaction_key(cursor), *transaction_key(boundary)))
    if any(broker_id(row[0]) not in records for row in known):
        raise BrokerError("Broker history omitted a previously confirmed transaction")
    start, end = int(cursor), int(boundary)
    if end > start:
        observations = db.execute("""
            SELECT broker_state_json FROM account_snapshots
            WHERE reconciliation_status = 'reconciled' AND broker_state_json LIKE '%"deferred_transaction_ids"%'
        """)
        for row in observations:
            deferred = json.loads(row[0]).get("deferred_transaction_ids", [])
            if any(start < int(identifier) <= end and identifier not in records for identifier in deferred):
                raise BrokerError("Broker history omitted a previously observed transaction")
    db.execute("UPDATE notebook SET imported_through_transaction_id = ?", (boundary,))


def import_through(db, broker, boundary):
    """Import a complete interval without changing the latest account snapshot."""
    _check_binding(db, broker.binding)
    if db.in_transaction:
        raise ValueError("Broker reads require an idle notebook connection")
    cursor, boundary = _cursor(db), broker_id(boundary)
    records = _history(broker, cursor, boundary)
    with transaction(db), localcontext(prec=80):
        _advance(db, cursor, boundary, records)
        _store(db, broker, records, broker.now(), complete_history=True, imported_before=cursor)
        _balance_through(db, boundary)
        _release_closed_sets(db, broker.now())


def record_confirmed_transactions(db, broker, bodies):
    """Retain broker-confirmed response activity without claiming history coverage."""
    with transaction(db), localcontext(prec=80):
        apply_confirmed_transactions(db, broker, bodies)
        _release_closed_sets(db, broker.now())


def apply_confirmed_transactions(db, broker, bodies):
    """Project response activity inside the caller's atomic outcome commit."""
    if not db.in_transaction:
        raise ValueError("Confirmed activity requires a notebook write transaction")
    _check_binding(db, broker.binding)
    records = _Records()
    for body in bodies:
        broker.verify_transaction(body)
        records.add(body)
    cursor = _number(_cursor(db))
    q0 = db.execute("SELECT qualification_transaction_id FROM notebook").fetchone()[0]
    if q0 is None:
        raise BrokerError("Notebook has no qualification baseline")
    start = _number(q0)
    for identifier in records:
        if start < int(identifier) <= cursor and db.execute(
            "SELECT 1 FROM broker_transactions WHERE transaction_id = ?", (identifier,)
        ).fetchone() is None:
            raise BrokerError("Previously imported history omitted a confirmed transaction",
                              evidence={"transaction_id": identifier})
    _store(db, broker, records, broker.now(), complete_history=False)


@dataclass(frozen=True)
class _Snapshot:
    read: object
    trades: dict = field(repr=False)
    orders: dict = field(repr=False)

    @property
    def account(self):
        return self.read.body["account"]

    @property
    def boundary(self):
        return self.read.boundary


def _objects(items):
    if not isinstance(items, list):
        raise BrokerError("Broker account snapshot omits its trade or order list")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise BrokerError("Invalid account snapshot trade or order")
        identifier = broker_id(item.get("id"))
        if identifier in result:
            raise BrokerError("Duplicate trade or order in broker account snapshot")
        result[identifier] = item
    return result


def _snapshot(read):
    account = read.body["account"]
    for field in ("balance", "unrealizedPL", "marginUsed", "marginAvailable"):
        money(account.get(field))
    return _Snapshot(read, _objects(account.get("trades")), _objects(account.get("orders")))


def _optional(read, identifier):
    try:
        return read(identifier)
    except BrokerError as failure:
        if failure.status == 404:
            return None
        raise


def _closing_records(db, broker, snapshot, cursor, records):
    reductions = {}
    for identifier, body in records.items():
        for effect, trade_id, units, price, _ in fill_details(body):
            if effect != "open":
                reductions.setdefault(trade_id, {})[identifier] = (effect, units, price)
    at = snapshot.read.responded_at
    absent = [leg for leg in db.execute(_LEGS) if leg["broker_trade_id"] is not None
              and leg["broker_trade_id"] not in snapshot.trades and _new_enough(leg, snapshot.boundary)]
    supplements = {}
    lookup = {}
    for leg in absent:
        trade_id = leg["broker_trade_id"]
        local_close = leg["broker_state"] == "closed" and leg["exit_transaction_id"] and leg["exit_price"] is not None
        fills = reductions.get(trade_id, {}).copy()
        for row in db.execute("""
            SELECT transaction_id, effect, units, price FROM fills
            WHERE broker_trade_id = ? AND effect IN ('reduce', 'close')
        """, (trade_id,)):
            if _number(row["transaction_id"]) <= _number(snapshot.boundary):
                fills.setdefault(row["transaction_id"], (row["effect"], money(row["units"]), row["price"]))
        complete_close = (
            leg["initial_units"] is not None
            and any(effect == "close" for effect, _, _ in fills.values())
            and all(price is not None for _, _, price in fills.values())
            and sum((abs(units) for _, units, _ in fills.values()), ZERO) == abs(money(leg["initial_units"]))
        )
        if local_close or complete_close:
            # An actual closing fill contains its order ID and broker cause.
            continue
        trade = _optional(broker.trade, trade_id)
        references = []
        if trade is not None:
            detail = trade.body["trade"]
            references = detail.get("closingTransactionIDs", [])
            if not isinstance(references, list):
                raise BrokerError("Invalid broker closing transaction references")
            if detail.get("instrument") is not None and _pair(detail["instrument"]) != leg["pair"]:
                raise BrokerError("Broker trade instrument differs from the registered leg")

        stops = {leg[name] for name in ("current_stop_order_id", "original_stop_order_id")} - {None}
        for stop_id in sorted(stops, key=_number):
            order = _optional(broker.order, stop_id)
            if order is None:
                continue
            detail = order.body["order"]
            if detail.get("tradeID") is not None and broker_id(detail["tradeID"]) != trade_id:
                raise BrokerError("Registered protective order refers to another trade")
            if detail.get("state") == "FILLED" and detail.get("fillingTransactionID") is not None:
                references = [*references, detail["fillingTransactionID"]]

        for reference in sorted({broker_id(value) for value in references}, key=_number):
            if _number(reference) > _number(snapshot.boundary):
                continue
            if reference not in records and reference not in lookup:
                known = db.execute("SELECT body_json FROM broker_transactions WHERE transaction_id = ?",
                                   (reference,)).fetchone()
                if known is not None:
                    lookup[reference] = json.loads(known[0])
                else:
                    found = _optional(broker.transaction, reference)
                    lookup[reference] = found.body["transaction"] if found is not None else None
                    if _number(reference) > _number(cursor):
                        raise BrokerError("Broker history omitted a referenced closing transaction",
                                          evidence={"transaction_id": reference, "observed_at": at})
                    if lookup[reference] is not None:
                        baseline = db.execute("SELECT qualification_transaction_id FROM notebook").fetchone()[0]
                        if baseline is None or _number(reference) > _number(baseline):
                            raise BrokerError("Imported history is missing a referenced closing transaction",
                                              evidence={"transaction_id": reference, "observed_at": at})
                        supplements[reference] = lookup[reference]
            body = records.get(reference, lookup.get(reference))
            if body is not None and not any(
                effect in ("reduce", "close") and affected == trade_id
                for effect, affected, *_ in fill_details(body)
            ):
                raise BrokerError("Closing reference does not contain a fill for its trade")
    return supplements


def _snapshot_orders(db, broker, snapshot, at):
    """Group confirmed dependent orders and preserve unexpected broker identities."""
    by_trade = {}
    for order_id, order in snapshot.orders.items():
        trade_id = broker_id(order["tradeID"]) if order.get("tradeID") is not None else None
        leg = _leg(db, trade_id) if trade_id is not None else None
        kind = order.get("type")
        if leg is not None and kind in _PROTECTION and order.get("state") == "PENDING":
            effects = by_trade.setdefault(trade_id, {})
            if kind in effects:
                _issue(db, "unexpected_order", order_id, at, {"order_id": order_id, "type": kind}, leg=leg)
            else:
                effects[kind] = order
            continue
        extensions = order.get("clientExtensions")
        client_id = extensions.get("id") if isinstance(extensions, dict) else None
        attempt = db.execute("""
            SELECT 1 FROM broker_attempts WHERE broker_order_id = ? OR client_id = ?
        """, (order_id, redact(client_id, broker.private_values))).fetchone()
        if attempt is not None:
            continue
        trade = snapshot.trades.get(trade_id)
        name = order.get("instrument") or (trade.get("instrument") if trade else None)
        pair = leg["pair"] if leg is not None else _pair(name)
        _issue(db, "unexpected_order", order_id, at, {"order_id": order_id, "type": kind}, pair=pair)
    return by_trade


def _compare_trades(db, broker, snapshot):
    boundary = snapshot.boundary
    at = snapshot.read.responded_at
    orders = _snapshot_orders(db, broker, snapshot, at)
    for trade_id, trade in snapshot.trades.items():
        pair = _pair(trade.get("instrument"))
        leg = _leg(db, trade_id)
        if leg is None:
            _issue(db, "unexpected_trade", trade_id, at, {"trade_id": trade_id, "boundary": boundary}, pair=pair)
            continue
        if not _new_enough(leg, boundary):
            continue
        if pair != leg["pair"] or trade.get("state") not in ("OPEN", "CLOSE_WHEN_TRADEABLE") or leg["broker_state"] in ("closed", "not_opened"):
            raise BrokerError("Snapshot contradicts registered trade identity or state")
        current = money(trade.get("currentUnits"))
        initial = money(trade.get("initialUnits"))
        price = money(trade.get("price"))
        opened = _time(trade.get("openTime"))
        if not 0 < abs(current) <= abs(initial) or price <= 0 or (
            (current > 0) != (leg["direction"] == "long") or (initial > 0) != (current > 0)
        ):
            raise BrokerError("Snapshot contains invalid registered trade units or price")
        if leg["current_units"] is not None and current != money(leg["current_units"]):
            _issue(db, "unexplained_units", trade_id, at, {
                "trade_id": trade_id, "boundary": boundary, "broker_units": str(current),
                "previous_units": leg["current_units"],
            }, leg=leg)
        _update_leg(db, leg, broker_state="open", current_units=str(current), initial_units=str(initial),
                    entry_price=str(price), entry_at=opened, broker_state_at=at, broker_state_transaction_id=boundary)
        if trade["state"] == "CLOSE_WHEN_TRADEABLE":
            _issue(db, "queued_close", trade_id, at,
                   {"trade_id": trade_id, "state": trade["state"], "boundary": boundary}, leg=leg)
            db.execute("""
                UPDATE broker_attempts SET outcome = 'pending'
                WHERE set_id = ? AND leg_no = ? AND purpose = 'signal_close'
                AND outcome IN ('prepared', 'pending', 'unknown')
            """, (leg["set_id"], leg["leg_no"]))

        for kind, inline in (("STOP_LOSS", "stopLossOrder"), ("TAKE_PROFIT", "takeProfitOrder")):
            order = trade.get(inline) or orders.get(trade_id, {}).get(kind)
            if order is None:
                _set_protection(db, leg, kind, None, None, boundary, at)
                if kind == "STOP_LOSS" or leg["leg_no"] == 1:
                    _issue(db, "missing_protection", f"{trade_id}:{kind}", at,
                           {"trade_id": trade_id, "protection": kind, "boundary": boundary}, leg=leg)
                continue
            if not isinstance(order, dict) or order.get("state") != "PENDING" or (
                order.get("tradeID") is not None and broker_id(order["tradeID"]) != trade_id
            ):
                raise BrokerError("Snapshot protection contradicts its registered trade")
            order_id = broker_id(order.get("id"))
            price = money(order.get("price"))
            if price <= 0:
                raise BrokerError("Invalid broker protection price")
            _set_protection(db, leg, kind, order_id, str(price), boundary, at)

    for leg in db.execute(_LEGS + " WHERE broker_trade_id IS NOT NULL").fetchall():
        trade_id = leg["broker_trade_id"]
        if trade_id in snapshot.trades or not _new_enough(leg, boundary):
            continue
        if leg["broker_state"] != "closed" or leg["exit_transaction_id"] is None or leg["exit_price"] is None:
            _issue(db, "missing_closing_evidence", trade_id, at,
                   {"trade_id": trade_id, "boundary": boundary}, leg=leg)


def _compare_reservations(db, at):
    for row in db.execute("""
        SELECT set_id, pair FROM trade_sets WHERE establishment_status = 'pending' AND terminal_at IS NULL
    """).fetchall():
        db.execute("UPDATE trade_sets SET establishment_status = 'incomplete' WHERE set_id = ?", (row["set_id"],))
        _issue(db, "interrupted_set", row["set_id"], at, {"set_id": row["set_id"]},
               pair=row["pair"], set_id=row["set_id"])
    for attempt in db.execute("""
        SELECT attempt_id, coalesce(broker_attempts.pair, trade_sets.pair) AS pair,
               broker_attempts.set_id FROM broker_attempts LEFT JOIN trade_sets USING (set_id)
        WHERE outcome IN ('prepared', 'pending', 'unknown')
    """):
        _issue(db, "unresolved_attempt", attempt["attempt_id"], at, {"attempt_id": attempt["attempt_id"]},
               pair=attempt["pair"], set_id=attempt["set_id"], attempt_id=attempt["attempt_id"])
    _release_closed_sets(db, at)


def _release_closed_sets(db, at):
    db.execute("""
        UPDATE trade_sets SET terminal_at = ?
        WHERE terminal_at IS NULL AND establishment_status IN ('complete', 'incomplete', 'not_opened')
        AND (SELECT count(*) FROM trade_legs
             WHERE trade_legs.set_id = trade_sets.set_id AND broker_state IN ('closed', 'not_opened')) = expected_leg_count
        AND NOT EXISTS (SELECT 1 FROM broker_attempts
                        WHERE broker_attempts.set_id = trade_sets.set_id AND outcome IN ('prepared', 'pending', 'unknown'))
    """, (at,))


def _save_snapshot(db, broker, snapshot_id, purpose, read, at, *, failure=None, deferred=()):
    body = read.body if read is not None else {}
    account = body.get("account", {})
    evidence = {}
    if read is not None:
        evidence = read.evidence({
            "lastTransactionID": body.get("lastTransactionID"),
            "account": {name: account[name] for name in (
                "currency", "balance", "unrealizedPL", "marginUsed", "marginAvailable",
            ) if name in account},
            "trades": [item.get("id") for item in account.get("trades", []) if isinstance(item, dict)]
            if isinstance(account.get("trades"), list) else [],
            "orders": [item.get("id") for item in account.get("orders", []) if isinstance(item, dict)]
            if isinstance(account.get("orders"), list) else [],
        })
    if failure is not None and failure.evidence is not None:
        evidence["failure"] = failure.evidence
    if deferred:
        evidence["deferred_transaction_ids"] = sorted(deferred, key=int)[:1000]
        evidence["deferred_transaction_count"] = len(deferred)
    try:
        encoded = encode_evidence(evidence, broker.private_values)
    except ValueError:
        if failure is None:
            raise BrokerError("Account snapshot evidence exceeds the notebook limit") from None
        encoded = encode_evidence({"failure": str(failure), "details": "Response evidence exceeded the notebook limit"},
                                  broker.private_values)

    def account_text(name):
        value = account.get(name)
        return redact(value, broker.private_values) if isinstance(value, str) else None

    boundary = body.get("lastTransactionID")
    received_at = read.responded_at if read else (failure.evidence or {}).get("responded_at")
    db.execute("""
        INSERT INTO account_snapshots (snapshot_id, purpose, requested_at, responded_at,
            last_transaction_id, balance, unrealised_pl, margin_used, margin_available,
            home_currency, broker_state_json, reconciliation_status, reconciliation_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (snapshot_id, purpose, read.requested_at if read else at, received_at,
          boundary if isinstance(boundary, str) else None, account_text("balance"), account_text("unrealizedPL"),
          account_text("marginUsed"), account_text("marginAvailable"), account_text("currency"), encoded,
          "reconciled" if failure is None else "failed", str(failure) if failure is not None else None))


def reconcile_snapshot(db, broker, *, purpose="reporting", snapshot_id=None, on_reconciled=None):
    """Capture, retrieve and apply a snapshot interval, or retain a failed read."""
    _check_binding(db, broker.binding)
    if db.in_transaction:
        raise ValueError("Broker reads require an idle notebook connection")
    snapshot_id = snapshot_id or uuid4().hex
    at = broker.now()
    read = None
    try:
        cursor = _cursor(db)
        read = broker.account()
        snapshot = _snapshot(read)
        deferred = set()
        records = _history(broker, cursor, snapshot.boundary, deferred=deferred)
        with localcontext(prec=80):
            supplements = _closing_records(db, broker, snapshot, cursor, records)
        with transaction(db), localcontext(prec=80):
            # A crash may have left a prepared intent before any response commit.
            # Later confirmation must not silently erase the operator's issue.
            for attempt in db.execute("""
                SELECT broker_attempts.*, trade_sets.pair AS affected_pair
                FROM broker_attempts JOIN trade_sets USING (set_id)
                WHERE purpose IN ('stop_to_entry', 'signal_close')
                AND outcome IN ('prepared', 'pending', 'unknown')
            """).fetchall():
                _issue(db, "unresolved_attempt", attempt["attempt_id"], read.responded_at,
                       {"attempt_id": attempt["attempt_id"]}, pair=attempt["affected_pair"],
                       set_id=attempt["set_id"], attempt_id=attempt["attempt_id"])
            _advance(db, cursor, snapshot.boundary, records)
            _store(db, broker, {**supplements, **records}, snapshot.read.responded_at,
                   complete_history=True, imported_before=cursor, observations=records.sources)
            expected, actual = _balance_through(db, snapshot.boundary), money(snapshot.account["balance"])
            if expected != actual:
                raise BrokerError("Unexplained broker snapshot balance", evidence={
                    "expected_balance": str(expected), "broker_balance": str(actual), "boundary": snapshot.boundary,
                })
            _compare_trades(db, broker, snapshot)
            _management_attempts(db, snapshot.read.responded_at)
            _compare_reservations(db, snapshot.read.responded_at)
            _save_snapshot(db, broker, snapshot_id, purpose, read, at, deferred=deferred)
            if on_reconciled is not None:
                # Local lifecycle/disposition changes share the snapshot commit.
                # The callback must do no network I/O.
                on_reconciled(snapshot_id, snapshot)
    except BrokerError as failure:
        with transaction(db):
            _save_snapshot(db, broker, snapshot_id, purpose, read, at, failure=failure)
        raise
    return snapshot_id
