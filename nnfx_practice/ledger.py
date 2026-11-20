"""Broker postings and boundary-consistent read queries for the notebook."""

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .broker import BrokerError, broker_id, money


ZERO = Decimal(0)
# Compare decimal IDs as text, including IDs with legacy zero padding.
_TRANSACTION_KEY = "length(ltrim(transaction_id, '0')), ltrim(transaction_id, '0')"
_FILL_FIELDS = (
    ("pl", "trading_pl", 1),
    ("financing", "financing", 1),
    ("commission", "commission", -1),
    ("guaranteedExecutionFee", "other_charge", -1),
    ("dividendAdjustment", "cash_adjustment", 1),
)


def transaction_key(value):
    digits = broker_id(value).lstrip("0")
    return len(digits), digits


def _snapshot_key(row):
    whole, _, fraction = row["responded_at"].removesuffix("Z").partition(".")
    return transaction_key(row["last_transaction_id"]), whole, fraction.ljust(9, "0"), row["rowid"]


def fill_details(body):
    """Yield the actual per-trade effects of an ORDER_FILL."""
    if body["type"] != "ORDER_FILL":
        return
    effects = [("open", body.get("tradeOpened")), ("reduce", body.get("tradeReduced"))]
    closed = body.get("tradesClosed", [])
    if not isinstance(closed, list) or not all(isinstance(item, dict) for item in closed):
        raise BrokerError("Invalid broker closing fills")
    effects.extend(("close", item) for item in closed)
    used = set()
    for effect, detail in effects:
        if detail is None:
            continue
        if not isinstance(detail, dict):
            raise BrokerError("Invalid broker fill detail")
        trade_id = broker_id(detail.get("tradeID"))
        if trade_id in used:
            raise BrokerError("Broker fill describes the same trade more than once")
        used.add(trade_id)
        units = money(detail.get("units"))
        price = money(detail["price"]) if detail.get("price") is not None else None
        if not units or (price is not None and price <= 0):
            raise BrokerError("Invalid broker fill units or price")
        yield effect, trade_id, units, price, detail
    if not used:
        raise BrokerError("Broker order fill has no per-trade effects")


def _posting_fields(body, fields, *, trade_id=None, prefix="", posted=True):
    for field, category, sign in fields:
        if body.get(field) is not None:
            source = prefix + field
            amount = money(body[field])
            yield source, str(amount if sign == 1 else amount.copy_negate()), category, trade_id, source, int(posted)


def postings(body, fills):
    """Count account totals once and retain explicit trade allocations for detail."""
    kind = body["type"]
    if kind == "ORDER_FILL":
        for field in ("pl", "financing"):
            money(body.get(field))
        yield from _posting_fields(body, _FILL_FIELDS)
        allocated_fields = (("realizedPL", "trading_pl", 1), *_FILL_FIELDS[1:])
        for effect, trade_id, _, _, detail in fills:
            prefix = f"{effect}.{trade_id}."
            yield from _posting_fields(detail, allocated_fields, trade_id=trade_id, prefix=prefix, posted=False)
    elif kind == "DAILY_FINANCING":
        fields = (("financing", "financing", 1),)
        money(body.get("financing"))
        yield from _posting_fields(body, fields)
        positions = body.get("positionFinancings", [])
        if not isinstance(positions, list):
            raise BrokerError("Invalid broker financing allocations")
        for position in positions:
            if not isinstance(position, dict) or not isinstance(position.get("openTradeFinancings", []), list):
                raise BrokerError("Invalid broker financing allocations")
            for detail in position.get("openTradeFinancings", []):
                if not isinstance(detail, dict):
                    raise BrokerError("Invalid broker financing allocations")
                trade_id = broker_id(detail.get("tradeID"))
                yield from _posting_fields(detail, fields, trade_id=trade_id, prefix=f"trade.{trade_id}.", posted=False)
    elif kind == "TRANSFER_FUNDS":
        money(body.get("amount"))
        yield from _posting_fields(body, (("amount", "cash_adjustment", 1),))


def _postings_between(db, start, end):
    return db.execute(f"""
        SELECT * FROM ledger_entries WHERE posted = 1
        AND ({_TRANSACTION_KEY}) > (?, ?) AND ({_TRANSACTION_KEY}) <= (?, ?)
        ORDER BY {_TRANSACTION_KEY}, component_key
    """, (*transaction_key(start), *transaction_key(end)))


@contextmanager
def _read_transaction(db):
    if db.in_transaction:
        yield
        return
    db.execute("BEGIN")
    try:
        yield
    finally:
        db.rollback()


@dataclass(frozen=True)
class AccountReport:
    period: str
    opening_snapshot_id: str
    snapshot_id: str
    boundary: str
    refreshed_at: str
    home_currency: str
    opening_balance: Decimal
    balance: Decimal
    unrealised_pl: Decimal | None
    realised_profit: Decimal
    realised_loss: Decimal
    financing: Decimal
    commission: Decimal
    other_charges: Decimal
    cash_adjustments: Decimal
    net_posted: Decimal


def account_report(db, period):
    """Read qualification (Q0 to at most A0) or ordinary results (after A0)."""
    if period not in ("qualification", "ordinary"):
        raise ValueError("Expected qualification or ordinary reporting")
    with _read_transaction(db), localcontext(prec=80):
        binding = db.execute("SELECT * FROM notebook").fetchone()
        baseline_id = binding["qualification_snapshot_id" if period == "qualification" else "activation_snapshot_id"]
        if baseline_id is None:
            return None
        baseline = db.execute("SELECT rowid, * FROM account_snapshots WHERE snapshot_id = ?", (baseline_id,)).fetchone()
        if baseline["reconciliation_status"] != "reconciled":
            return None
        cap = binding["activation_transaction_id"] if period == "qualification" else None
        if cap is not None:
            # The committed activation snapshot is the final qualification observation.
            snapshot = db.execute("SELECT * FROM account_snapshots WHERE snapshot_id = ?",
                                  (binding["activation_snapshot_id"],)).fetchone()
            if snapshot["reconciliation_status"] != "reconciled":
                return None
        else:
            rows = db.execute("""
                SELECT rowid, * FROM account_snapshots WHERE reconciliation_status = 'reconciled'
                AND home_currency = ?
            """, (binding["home_currency"],))
            opening_key = _snapshot_key(baseline)
            snapshot = max(
                (row for row in rows if _snapshot_key(row) >= opening_key),
                key=_snapshot_key,
                default=baseline,
            )
        totals = dict.fromkeys(("profit", "loss", "financing", "commission", "other_charge", "cash_adjustment"), ZERO)
        for row in _postings_between(db, baseline["last_transaction_id"], snapshot["last_transaction_id"]):
            amount = money(row["amount"])
            category = row["category"]
            if category == "trading_pl":
                category = "profit" if amount >= 0 else "loss"
            totals[category] += amount
        return AccountReport(
            period, baseline_id, snapshot["snapshot_id"], snapshot["last_transaction_id"],
            snapshot["responded_at"], binding["home_currency"], money(baseline["balance"]),
            money(snapshot["balance"]), money(snapshot["unrealised_pl"]) if snapshot["unrealised_pl"] is not None else None,
            totals["profit"], totals["loss"], totals["financing"], totals["commission"], totals["other_charge"],
            totals["cash_adjustment"], sum(totals.values(), ZERO),
        )


def trade_journal(db, trade_id, pip_location, *, boundary=None):
    """Read current facts and dated detail; absent pip metadata leaves pips unknown."""
    trade_id = broker_id(trade_id)
    if pip_location is not None and (type(pip_location) is not int or not -20 <= pip_location <= 20):
        raise ValueError("Invalid instrument pip location")
    cutoff = transaction_key(boundary) if boundary is not None else None
    with _read_transaction(db), localcontext(prec=80):
        row = db.execute("""
            SELECT trade_legs.*, trade_sets.pair, trade_sets.direction FROM trade_legs
            JOIN trade_sets USING (set_id) WHERE broker_trade_id = ?
        """, (trade_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        fills = db.execute(f"""
            SELECT * FROM fills WHERE broker_trade_id = ? ORDER BY {_TRANSACTION_KEY}
        """, (trade_id,))
        result["fills"] = [
            {**fill, "after_snapshot": cutoff is not None and transaction_key(fill["transaction_id"]) > cutoff}
            for fill in fills
        ]
        entries = db.execute(f"""
            SELECT ledger_entries.*, broker_transactions.broker_at FROM ledger_entries
            JOIN broker_transactions USING (transaction_id)
            WHERE broker_trade_id = ? ORDER BY {_TRANSACTION_KEY}, component_key
        """, (trade_id,))
        result["ledger"] = [
            {**entry, "after_snapshot": cutoff is not None and transaction_key(entry["transaction_id"]) > cutoff}
            for entry in entries
        ]
        result["after_snapshot"] = cutoff is not None and row["broker_state_transaction_id"] is not None and (
            transaction_key(row["broker_state_transaction_id"]) > cutoff
        )
        result["pips"] = None
        result["trading_pl"] = None
        if row["broker_state"] == "closed" and row["exit_transaction_id"] is not None:
            if pip_location is not None and row["exit_price"] is not None and row["entry_price"] is not None:
                difference = money(row["exit_price"]) - money(row["entry_price"])
                result["pips"] = difference.scaleb(-pip_location) * (1 if row["direction"] == "long" else -1)
            reductions = {fill["transaction_id"] for fill in result["fills"] if fill["effect"] != "open"}
            allocations = {entry["transaction_id"]: money(entry["amount"]) for entry in result["ledger"]
                           if entry["category"] == "trading_pl"}
            volume = sum((abs(money(fill["units"])) for fill in result["fills"] if fill["effect"] != "open"), ZERO)
            if (row["initial_units"] is not None and volume == abs(money(row["initial_units"]))
                    and reductions and reductions <= allocations.keys()):
                result["trading_pl"] = sum((allocations[key] for key in reductions), ZERO)
        return result
