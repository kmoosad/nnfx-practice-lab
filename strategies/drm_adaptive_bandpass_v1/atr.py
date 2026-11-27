"""The lab's true range and simple ATR, with its research-length guard lifted."""

from collections.abc import Sequence
import math
from typing import Literal

from .comparisons import compare_signal_numbers
from .interface import Candle


ATR_LENGTH = 14


class AssessmentError(ValueError):
    """A bounded Step 11 domain failure with a stable diagnostic code."""

    outcome: Literal["failed", "blocked"]

    def __init__(self, code: str, summary: str, *, outcome: Literal["failed", "blocked"]):
        self.code = code
        self.summary = summary
        self.outcome = outcome
        super().__init__(code)


class AssessmentFailed(AssessmentError):
    def __init__(self, code: str, summary: str):
        super().__init__(code, summary, outcome="failed")


def true_range_and_atr(candles: Sequence[Candle]) -> tuple[tuple[float, ...], tuple[float | None, ...]]:
    values = tuple(candles)
    ranges: list[float] = []
    averages: list[float | None] = []
    for index, candle in enumerate(values):
        candidates = (float(candle.high - candle.low),) if index == 0 else (
            float(candle.high - candle.low),
            float(abs(candle.high - values[index - 1].close)),
            float(abs(candle.low - values[index - 1].close)),
        )
        if any(not math.isfinite(value) for value in candidates):
            raise AssessmentFailed("true_range_invalid", "True range is not finite")
        winner = candidates[0]
        for candidate in candidates[1:]:
            if compare_signal_numbers(candidate, winner) > 0:
                winner = candidate
        ranges.append(winner)
        if index < ATR_LENGTH - 1:
            averages.append(None)
        else:
            try:
                average = math.fsum(ranges[index - ATR_LENGTH + 1:index + 1]) / ATR_LENGTH
            except OverflowError as error:
                raise AssessmentFailed("atr_invalid", "ATR calculation overflowed") from error
            if not math.isfinite(average):
                raise AssessmentFailed("atr_invalid", "ATR is not finite")
            averages.append(average)
    return tuple(ranges), tuple(averages)
