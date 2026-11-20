"""Decimal candidate sizing. Broker acceptance and account qualification are separate."""

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, localcontext

from .broker import BrokerError, instrument, money
from .preflight import _instrument_check, _one_row, _tradeable_price


def positive(value, name):
    number = money(value)
    if number <= 0:
        raise BrokerError(f"{name} must be positive")
    return number


def tick(precision):
    # Bound external exponents before constructing Decimal values.
    if type(precision) is not int or not 0 <= precision <= 18:
        raise BrokerError("Unsupported executable precision")
    return Decimal(1).scaleb(-precision)


def levels(fill, atr, distance, direction, precision, *, with_target=True):
    with localcontext(prec=80):
        price = positive(fill, "Entry price")
        step = tick(precision)
        if price != price.quantize(step):
            raise BrokerError("Entry price cannot be represented exactly for stop-to-entry")
        sign = Decimal(1 if direction == "long" else -1)
        stop = price - sign * positive(distance, "Stop distance")
        raw_target = price + sign * positive(atr, "ATR") if with_target else None
        target = raw_target.quantize(step, rounding=ROUND_HALF_UP) if with_target else None
        if stop <= 0 or (with_target and (target <= 0 or sign * (target - price) <= 0)):
            raise BrokerError("Protection is zero or on the wrong side of entry")
        return {"stop": format(stop, "f"), "raw_target": format(raw_target, "f") if with_target else None,
                "target": format(target, "f") if with_target else None}


def margin_requirement(units, metadata, pricing, account, home, pair, legs):
    with localcontext(prec=80):
        base = pair.split("-")[0]
        # Unlike risk conversion, the approved margin contract permits identity for home base.
        factor = (Decimal(1) if base == home else positive(
            _one_row(pricing, "homeConversions", "currency", base).get("positionValue"), "positionValue"))
        instrument_rate = positive(metadata.get("marginRate"), "Instrument margin rate")
        account_rate = (positive(account["marginRate"], "Account margin rate")
                        if "marginRate" in account else None)
        # The Account contract describes an optional lower margin-rate override.
        # M10 must compare this candidate estimate with actual account margin.
        rate = min(instrument_rate, account_rate) if account_rate is not None else instrument_rate
        if instrument_rate > 1 or (account_rate is not None and account_rate > 1):
            raise BrokerError("Margin rate is outside the valid range")
        required = positive(units, "Units") * factor * rate * legs
        available = money(account.get("marginAvailable"))
        return {"legs": legs, "base_currency": base, "positionValue": str(factor),
                "instrument_rate": str(instrument_rate), "account_rate": str(account_rate) if account_rate is not None else None,
                "rate": str(rate), "rate_source": "account_override" if account_rate is not None and account_rate < instrument_rate else "instrument",
                "required": str(required), "available": str(available), "sufficient": available >= required}


def size_candidate(*, balance, atr, direction, pair, home, instruments, pricing, account,
                   pricing_at, existing_units="0"):
    """Return exact inputs/results; skip on missing conversion, precision or protection inputs."""
    if direction not in ("long", "short"):
        raise BrokerError("A fresh long or short event is required")
    for result in (_instrument_check(instruments, pair), _tradeable_price(pricing, pair)):
        if result["validation"] != "valid":
            raise BrokerError(result["reason"])
    metadata = _one_row(instruments, "instruments", "name", instrument(pair))
    price = _one_row(pricing, "prices", "instrument", instrument(pair))
    if any(obj.get("guaranteedStopLossOrderMode") == "REQUIRED" for obj in (metadata, account)):
        raise BrokerError("Candidate ordinary stops do not support required guaranteed stops")
    with localcontext(prec=80):
        price_tick, unit_step = tick(metadata["displayPrecision"]), tick(metadata["tradeUnitsPrecision"])
        b, a = positive(balance, "Sizing balance"), positive(atr, "ATR")
        quote = pair.split("-")[1]
        q = positive(_one_row(pricing, "homeConversions", "currency", quote).get("accountLoss"), "accountLoss")
        raw_distance = Decimal("1.5") * a
        distance = raw_distance.quantize(price_tick, rounding=ROUND_HALF_UP)
        if distance <= 0:
            raise BrokerError("Executable stop distance rounds to zero")
        budget = b * Decimal("0.01")
        maximum = positive(metadata["maximumOrderUnits"], "Order limit")
        position_limit, occupied = money(metadata["maximumPositionSize"]), money(existing_units)
        if occupied < 0:
            raise BrokerError("Existing absolute instrument units must not be negative")
        if position_limit:
            maximum = min(maximum, (position_limit - occupied) / 2)
        units = min(budget / (distance * q), maximum).quantize(unit_step, rounding=ROUND_DOWN)
        if units < positive(metadata["minimumTradeSize"], "Minimum units"):
            raise BrokerError("Allowed units are below the instrument minimum")
        loss = units * distance * q
        if loss > budget:
            raise BrokerError("Rounded units exceed the per-leg risk budget")
        estimated_fill = price["asks" if direction == "long" else "bids"][0]["price"]
        # This check is provisional; actual fills must pass the same level checks.
        intended = levels(estimated_fill, atr, str(distance), direction, metadata["displayPrecision"])
        margin = margin_requirement(str(units), metadata, pricing, account, home, pair, 2)
        return {"balance": balance, "atr": atr, "raw_stop_distance": str(raw_distance),
                "stop_distance": str(distance), "budget_per_leg": str(budget),
                "quote_currency": quote, "accountLoss": str(q), "pricing_at": pricing_at,
                "price_time": price["time"], "display_precision": metadata["displayPrecision"],
                "unit_precision": metadata["tradeUnitsPrecision"], "minimum_units": metadata["minimumTradeSize"],
                "maximum_order_units": metadata["maximumOrderUnits"], "maximum_position_units": metadata["maximumPositionSize"],
                "existing_units": existing_units, "units": str(units),
                "signed_units": str(units if direction == "long" else -units),
                "risk_per_leg": str(loss), "estimated_levels": intended, "margin": margin}
