"""Exact numeric comparison policy for Confirmation signal operands."""

from decimal import Decimal, ROUND_HALF_UP, localcontext
import math


SIGNAL_SCALE = Decimal("0.000000001")


def normalize_signal_number(value: int | float) -> Decimal:
    """Normalize one finite binary64-safe operand by the approved signal rule."""

    if type(value) not in (int, float):
        raise TypeError("numeric_signal_operand")
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        raise ValueError("non_finite_signal_operand") from None
    if not math.isfinite(converted):
        raise ValueError("non_finite_signal_operand")

    decimal = Decimal(str(value)) if type(value) is float else Decimal(value)
    with localcontext() as context:
        context.prec = 400
        return decimal.quantize(SIGNAL_SCALE, rounding=ROUND_HALF_UP)


def compare_signal_numbers(left: int | float, right: int | float) -> int:
    """Return -1, 0 or 1 after normalizing both numeric signal operands."""

    normalized_left = normalize_signal_number(left)
    normalized_right = normalize_signal_number(right)
    return (normalized_left > normalized_right) - (
        normalized_left < normalized_right
    )
