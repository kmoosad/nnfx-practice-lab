"""STD-Adaptive T3 confirmation and L2 Ehlers Bandpass exit."""

from dataclasses import dataclass
from typing import Callable, Sequence

from nnfx_practice.candles import Candle
from nnfx_practice.signal_actions import Signal

from . import c1, exit
from .atr import AssessmentFailed, true_range_and_atr
from .interface import IndicatorOutput
from .signals import paired_directional_events


LOOKBACK_CANDLES = 386
C1_RULE_ID = "a53e86e2-845e-4ee8-ba59-fb6d763bcfa2"
EXIT_RULE_ID = "c277fa0e-233f-4089-9294-29d263b2936a"
C1_OUTPUTS = ("goLong", "goShort")
EXIT_OUTPUTS = ("longEntry", "shortEntry")

_DIRECTIONS: dict[int | None, Signal] = {
    1: "long", -1: "short", 0: "no_event", None: "unavailable",
}


@dataclass(frozen=True)
class EventObservation:
    direction: Signal
    rule_id: str
    output_names: tuple[str, str]
    current: tuple[bool | None, ...] = ()
    previous: tuple[bool | None, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class AtrObservation:
    value: float | None
    error: str | None = None


def _require_window(candles: Sequence[Candle]) -> None:
    if len(candles) != LOOKBACK_CANDLES:
        raise ValueError("The strategy requires the exact qualified candle count")


def _observe(
    candles: Sequence[Candle],
    calculate: Callable[[Sequence[Candle]], IndicatorOutput],
    rule_id: str,
    names: tuple[str, str],
) -> EventObservation:
    _require_window(candles)
    try:
        output = calculate(candles)
    except (ArithmeticError, ValueError):
        return EventObservation("unavailable", rule_id, names, error="indicator_calculation_failed")

    current = tuple(output.series[name][-1] for name in names)
    previous = tuple(output.series[name][-2] for name in names)
    try:
        observations = paired_directional_events(
            output, *names, long_kind="boolean", short_kind="boolean",
        )
    except ValueError as failure:
        return EventObservation("unavailable", rule_id, names, current, previous, str(failure))
    return EventObservation(_DIRECTIONS[observations[-1].direction], rule_id, names, current, previous)


def observe_c1(candles: Sequence[Candle]) -> EventObservation:
    return _observe(candles, c1.calculate, C1_RULE_ID, C1_OUTPUTS)


def observe_exit(candles: Sequence[Candle]) -> EventObservation:
    # Evaluate the saved completed-input Lab conversion at the practice snapshot.
    # The candle remains partial in the capture record.
    return _observe(candles, exit.calculate, EXIT_RULE_ID, EXIT_OUTPUTS)


def sizing_atr(candles: Sequence[Candle]) -> AtrObservation:
    _require_window(candles)
    try:
        _, averages = true_range_and_atr(candles)
    except AssessmentFailed as failure:
        return AtrObservation(None, failure.code)
    return AtrObservation(averages[-1])
