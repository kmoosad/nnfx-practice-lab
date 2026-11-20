"""Field-aware comparison of repeated broker transaction evidence.

Unknown differences remain conflicts. Optional fields are an explicit policy,
not a rule that missing means zero or that unrecognized data can be ignored.
"""

from .broker import BrokerError, broker_id, money


_COSTS = frozenset({
    "baseFinancingHomeConversionCost", "guaranteedExecutionFeeHomeConversionCost",
    "homeConversionCost", "plHomeConversionCost",
})
_FEES = frozenset({"commission", "guaranteedExecutionFee", "dividendAdjustment"})
_FILL_NUMBERS = _COSTS | _FEES | {
    "units", "requestedUnits", "price", "fullVWAP", "pl", "financing", "accountBalance",
    "baseFinancing", "quoteFinancing", "quotePL", "quoteGuaranteedExecutionFee",
    "halfSpreadCost", "gainQuoteHomeConversionFactor", "lossQuoteHomeConversionFactor",
}
_TRADE_NUMBERS = _COSTS | _FEES | {
    "units", "price", "realizedPL", "financing", "baseFinancing", "quoteFinancing",
    "quoteGuaranteedExecutionFee", "financingRate", "halfSpreadCost", "initialMarginRequired",
}
_FILL_OPTIONAL = _COSTS | _FEES | {"halfSpreadCost"}
_TRADE_OPTIONAL = _COSTS | _FEES | {"realizedPL", "financing", "halfSpreadCost", "initialMarginRequired"}
_ORDERS = frozenset({
    "MARKET_ORDER", "LIMIT_ORDER", "STOP_ORDER", "MARKET_IF_TOUCHED_ORDER",
    "STOP_LOSS_ORDER", "TAKE_PROFIT_ORDER", "TRAILING_STOP_LOSS_ORDER", "GUARANTEED_STOP_LOSS_ORDER",
})
_MISSING = object()


def _fields(kind, path):
    """Return known decimal fields and fields allowed to supplement this object."""
    if not path:
        if kind == "ORDER_FILL":
            return _FILL_NUMBERS, _FILL_OPTIONAL
        if kind.removesuffix("_REJECT") in _ORDERS:
            return {"units", "price", "distance", "priceBound", "trailingStopLossDistance"}, set()
        if kind == "TRANSFER_FUNDS":
            return {"amount", "accountBalance"}, {"comment"}
        if kind == "DAILY_FINANCING":
            return {"financing", "accountBalance"}, set()
    if kind == "ORDER_FILL" and path in (("tradeOpened",), ("tradeReduced",), ("tradesClosed", "*")):
        return _TRADE_NUMBERS, _TRADE_OPTIONAL
    if kind == "ORDER_FILL":
        if path == ("fullPrice",):
            return {"closeoutBid", "closeoutAsk"}, set()
        if len(path) == 3 and path[0] == "fullPrice" and path[1] in ("bids", "asks"):
            return {"price", "liquidity"}, set()
        if len(path) == 2 and path[0] == "homeConversionFactors" and path[1] in (
            "gainBaseHome", "lossBaseHome", "gainQuoteHome", "lossQuoteHome",
        ):
            return {"factor"}, set()
    if path and path[-1] in ("clientExtensions", "tradeClientExtensions"):
        return set(), {"tag", "comment"}
    if kind.removesuffix("_REJECT") in _ORDERS and path in (
        ("stopLossOnFill",), ("takeProfitOnFill",), ("trailingStopLossOnFill",), ("guaranteedStopLossOnFill",),
    ):
        return {"price", "distance"}, set()
    return set(), set()


def merge_transaction(previous, current):
    """Return cumulative accepted facts, retaining prior spellings and list order.

    Callers archive each actual response separately and validate new postings
    against the import cursor/balance before committing the cumulative record.
    """
    kind = current["type"]
    identifier = broker_id(current["id"])
    conflicts = set()

    def conflict(path):
        conflicts.add(".".join(path) or "transaction")

    def merge(left, right, path=()):
        parent, name = path[:-1], path[-1] if path else ""
        numbers, optional = _fields(kind, parent)
        if left is _MISSING or right is _MISSING:
            value = right if left is _MISSING else left
            if name not in optional:
                conflict(path)
            # Validate a supplied optional value even on its first observation.
            return merge(value, value, path)
        if name in numbers:
            try:
                a, b = money(left), money(right)
                if a != b or (name in _COSTS and a != 0):
                    conflict(path)
            except BrokerError:
                conflict(path)
            return left
        if name in optional and name in {"tag", "comment"}:
            if not isinstance(left, str) or not isinstance(right, str):
                conflict(path)
        if type(left) is not type(right):
            conflict(path)
            return left
        if isinstance(left, dict):
            return {key: merge(left.get(key, _MISSING), right.get(key, _MISSING), (*path, key))
                    for key in sorted(left.keys() | right.keys())}
        if isinstance(left, list):
            if kind == "ORDER_FILL" and path == ("tradesClosed",):
                def indexed(items):
                    result = {}
                    for item in items:
                        if not isinstance(item, dict):
                            raise BrokerError("Invalid broker closing fills")
                        trade_id = broker_id(item.get("tradeID"))
                        if trade_id in result:
                            raise BrokerError("Duplicate broker closing trade ID")
                        result[trade_id] = item
                    return result
                a, b = indexed(left), indexed(right)
                if a.keys() != b.keys():
                    conflict(path)
                    return left
                return [merge(item, b[trade_id], (*path, "*")) for trade_id, item in a.items()]
            if len(left) != len(right):
                conflict(path)
                return left
            return [merge(a, b, (*path, str(index))) for index, (a, b) in enumerate(zip(left, right))]
        if left != right:
            conflict(path)
        return left

    result = merge(current if previous is None else previous, current)
    if conflicts:
        raise BrokerError(f"Imported broker transaction changed or has unsupported values (transaction {identifier})",
                          evidence={"transaction_id": identifier, "changed_fields": sorted(conflicts)})
    return result
