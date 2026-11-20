"""Paired directional event interpretation from the lab."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Literal

from .interface import IndicatorOutput


Direction = Literal[-1, 0, 1]


@dataclass(frozen=True)
class SignalObservation:
    """Long, Short, no-event or unavailable state at one exact output row."""

    timestamp: datetime
    direction: Direction | None


def _series(output: IndicatorOutput, name: str) -> tuple[object, ...]:
    if not isinstance(output, IndicatorOutput):
        raise TypeError("indicator_output_required")
    if not isinstance(name, str) or name not in output.series:
        raise ValueError("unknown_signal_output")
    return output.series[name]


def _numeric(value: object) -> int | float | None:
    if type(value) not in (int, float):
        raise ValueError("invalid_numeric_signal_operand")
    try:
        converted = float(value)
    except (OverflowError, ValueError):
        raise ValueError("invalid_numeric_signal_operand") from None
    if math.isnan(converted):
        return None
    if not math.isfinite(converted):
        raise ValueError("invalid_numeric_signal_operand")
    return value


def _observations(
    output: IndicatorOutput, directions: Sequence[Direction | None]
) -> tuple[SignalObservation, ...]:
    return tuple(
        SignalObservation(timestamp, direction)
        for timestamp, direction in zip(output.timestamps, directions, strict=True)
    )


def _event(value: object, kind: str) -> bool | None:
    """Read one event using the calculation interface's declared encoding."""
    if kind == "boolean":
        if value is None or type(value) is bool:
            return value
        raise ValueError("invalid_boolean_signal_operand")
    if kind == "integer":
        if value is None:
            return None
        if type(value) is not int:
            raise ValueError("invalid_integer_signal_operand")
    elif kind != "numeric":
        raise ValueError("invalid_event_output_kind")
    number = _numeric(value)
    if number is None:
        return None
    if number not in (0, 1):
        raise ValueError("invalid_directional_event")
    return number == 1


def paired_directional_events(
    output: IndicatorOutput, long_output: str, short_output: str,
    *, long_kind: str = "numeric", short_kind: str = "numeric",
) -> tuple[SignalObservation, ...]:
    """Interpret declared Boolean or numeric/integer Long and Short events."""

    long_values = _series(output, long_output)
    short_values = _series(output, short_output)
    directions: list[Direction | None] = []
    for long_value, short_value in zip(long_values, short_values, strict=True):
        long_event = _event(long_value, long_kind)
        short_event = _event(short_value, short_kind)
        if long_event is None or short_event is None:
            directions.append(None)
            continue
        if long_event == 1 and short_event == 1:
            raise ValueError("simultaneous_directional_events")
        directions.append(1 if long_event == 1 else -1 if short_event == 1 else 0)
    return _observations(output, directions)
