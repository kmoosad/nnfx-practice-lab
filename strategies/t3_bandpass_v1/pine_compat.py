"""Selected calculations from the lab's registered pine_compat v1 dependency."""

from bisect import bisect_right
from collections import deque
from math import fsum, isfinite, isnan, nan, sqrt


def _missing(value):
    return value is None or (isinstance(value, float) and isnan(value))


def ne(left, right):
    """NNFX inequality: a missing operand produces False in every context."""

    return False if _missing(left) or _missing(right) else left != right


def pine_max(*values):
    """Scalar maximum that propagates any missing operand."""

    return nan if any(_missing(value) for value in values) else max(values)


def pine_min(*values):
    """Scalar minimum that propagates any missing operand."""

    return nan if any(_missing(value) for value in values) else min(values)


def _condition_true(value):
    if _missing(value):
        return False
    if not isinstance(value, (bool, int, float)):
        raise TypeError("gated condition must be Boolean, numeric or missing")
    return value != 0


def exact_int(value):
    """Lossless discrete representation, never a source rounding operation."""
    if type(value) is int:
        return value
    if type(value) is float and isfinite(value) and value.is_integer():
        return int(value)
    raise ValueError("discrete argument must be an exact integer")


def _length(value):
    if type(value) is not int or value <= 0:
        raise ValueError("length must be a positive integer")
    return value


def _windows(values, length):
    length = _length(length)
    window = deque(maxlen=length)
    for value in values:
        value = float(value)
        if not isnan(value):
            window.append(value)
        yield tuple(window) if len(window) == length else ()


def sma(values, length):
    """Return Pine-compatible simple moving averages for the approved scope."""

    return tuple(
        fsum(window) / length if window else nan
        for window in _windows(values, length)
    )


def stdev(values, length):
    """Return population standard deviation for the approved omitted-bias call."""

    length = _length(length)
    result = []
    for window in _windows(values, length):
        if not window:
            result.append(nan)
            continue
        mean = fsum(window) / length
        result.append(sqrt(fsum((value - mean) ** 2 for value in window) / length))
    return tuple(result)


def rma(values, length):
    """Return the approved SMA-seeded Wilder moving average."""

    length = _length(length)
    alpha = 1.0 / length
    state = nan
    seed = []
    result = []
    for value in values:
        value = float(value)
        if not isnan(value):
            if isnan(state):
                seed.append(value)
                if len(seed) == length:
                    state = fsum(seed) / length
            else:
                state = alpha * value + (1.0 - alpha) * state
        result.append(state)
    return tuple(result)


def true_range(candles):
    """Return the approved ``ta.tr(true)`` closed-bar series."""

    result = []
    previous_close = nan
    for candle in candles:
        high = float(candle.high)
        low = float(candle.low)
        close = float(candle.close)
        if isnan(high) or isnan(low):
            value = nan
        elif isnan(previous_close):
            value = high - low
        else:
            value = max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        result.append(value)
        previous_close = close
    return tuple(result)


def atr(candles, length):
    """Return the approved ATR as RMA of ``true_range(candles)``."""

    return rma(true_range(candles), length)


def nz(value, replacement=0.0):
    return replacement if value is None or (isinstance(value, float) and isnan(value)) else value


def safe_div(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return nan
    return float(numerator) / float(denominator)


def history(values, index, offset=1):
    if type(offset) is not int or offset < 0 or type(index) is not int or index < 0:
        raise ValueError("invalid history index")
    return nan if index < offset else values[index - offset]


def _cross(left, right, above):
    if len(left) != len(right):
        raise ValueError("unaligned cross operands")
    result = []
    for i in range(len(left)):
        if i == 0 or any(v is None or isnan(float(v)) for v in (left[i], right[i], left[i-1], right[i-1])):
            result.append(False)
        elif above:
            result.append(left[i] > right[i] and left[i-1] <= right[i-1])
        else:
            result.append(left[i] < right[i] and left[i-1] >= right[i-1])
    return tuple(result)


def crossover(left, right):
    return _cross(left, right, True)


def crossunder(left, right):
    return _cross(left, right, False)


class LocalSeries:
    """Sparse completed-bar history for one written local series."""

    def __init__(self):
        self._bars = []
        self._values = []

    def set(self, bar, value):
        _bar_index(bar)
        if value is None:
            value = nan
        if not isinstance(value, (bool, int, float)):
            raise TypeError("local history requires numeric or Boolean values")
        if self._bars and bar < self._bars[-1]:
            raise ValueError("history writes must be chronological")
        if self._bars and bar == self._bars[-1]:
            self._values[-1] = value
        else:
            self._bars.append(bar)
            self._values.append(value)
        return value

    def get(self, bar, offset=1):
        _bar_index(bar)
        _bar_index(offset)
        position = bisect_right(self._bars, bar - offset) - 1
        return nan if position < 0 else self._values[position]

    def _window(self, length, skip_missing=False):
        result = []
        for bar, value in zip(reversed(self._bars), reversed(self._values)):
            if skip_missing and _missing(value):
                continue
            result.append((bar, value))
            if len(result) == length:
                break
        return result[::-1]


def _bar_index(value):
    if type(value) is not int or value < 0:
        raise ValueError("index/strength must be a nonnegative integer")
    return value


def _finite_parameter(value):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError("parameter must be finite numeric, not Boolean")
    return value


def _percentage(value):
    _finite_parameter(value)
    if not 0 <= value <= 100:
        raise ValueError("percentage must be between zero and 100")
    return value


def array_percentile_linear_interpolation(values, percentage):
    """Interpolate sorted defined observations without modifying the input."""
    _percentage(percentage)
    ordered = sorted(float(value) for value in values if not _missing(value))
    if not ordered:
        return nan
    rank = (len(ordered) - 1) * percentage / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


class SeriesCall:
    """Closed-bar state for the explicitly supported written built-in calls."""

    _WINDOWS = frozenset({
        "sma", "wma", "stdev", "rolling_sum", "highest", "lowest",
        "highestbars", "lowestbars", "percentile_linear_interpolation",
    })
    _RECURSIVE = frozenset({"ema", "rma"})
    _OTHER = frozenset({
        "crossover", "crossunder", "barssince", "running_max", "running_min",
    })

    def __init__(self, operation, length=None, percentage=None):
        if operation not in self._WINDOWS | self._RECURSIVE | self._OTHER:
            raise ValueError("unsupported SeriesCall operation")
        if length is not None:
            _length(length)
            if operation in self._OTHER:
                raise ValueError("operation does not take a length")
        if operation in self._RECURSIVE and length is None:
            raise ValueError("EMA/RMA require a fixed positive integer length")
        if operation == "percentile_linear_interpolation":
            _percentage(percentage)
        elif percentage is not None:
            raise ValueError("percentage is only supported for percentiles")
        self.operation, self.length, self.percentage = operation, length, percentage
        self._source, self._other = LocalSeries(), LocalSeries()
        self._last_true, self.history = LocalSeries(), LocalSeries()

    def update(self, bar, value, other=nan, length=None):
        operation = self.operation
        if self.length is not None and length is not None:
            raise ValueError("do not mix fixed and dynamic lengths")
        if operation in self._OTHER and length is not None:
            raise ValueError("operation does not take a length")
        period = self.length if self.length is not None else length
        if operation in self._WINDOWS | self._RECURSIVE and not _missing(period):
            _length(period)
        self._source.set(bar, value)
        value = self._source.get(bar, 0)
        previous = self.history.get(bar, 1)

        if operation in self._WINDOWS | self._RECURSIVE and _missing(period):
            result = nan
        elif operation in ("crossover", "crossunder"):
            self._other.set(bar, other)
            old_left, old_right = self._source.get(bar, 1), self._other.get(bar, 1)
            if any(_missing(v) for v in (value, other, old_left, old_right)):
                result = False
            elif operation == "crossover":
                result = value > other and old_left <= old_right
            else:
                result = value < other and old_left >= old_right
        elif operation == "barssince":
            last_true = bar if _condition_true(value) else self._last_true.get(bar, 1)
            self._last_true.set(bar, last_true)
            result = nan if _missing(last_true) else bar - last_true
        elif operation in ("running_max", "running_min"):
            choose = max if operation == "running_max" else min
            if _missing(value):
                result = previous
            elif _missing(previous):
                result = value
            else:
                result = choose(previous, value)
        elif operation in self._RECURSIVE:
            if _missing(value):
                result = previous
            elif _missing(previous):
                if operation == "ema":
                    result = value
                else:
                    seed = self._source._window(period, skip_missing=True)
                    result = fsum(v for _, v in seed) / period if len(seed) == period else nan
            else:
                alpha = 2.0 / (period + 1) if operation == "ema" else 1.0 / period
                result = alpha * value + (1 - alpha) * previous
        else:
            skips = operation in {"sma", "wma", "stdev", "rolling_sum"}
            window = self._source._window(period, skip_missing=skips)
            values = [v for _, v in window]
            if operation in ("highest", "lowest", "highestbars", "lowestbars"):
                defined = [(b, v) for b, v in window if not _missing(v)]
                choose = max if operation in ("highest", "highestbars") else min
                if not defined:
                    result = nan
                else:
                    extreme = choose(v for _, v in defined)
                    result = extreme
                    if operation.endswith("bars"):
                        result = next(b - bar for b, v in reversed(defined) if v == extreme)
            elif len(values) < period:
                result = nan
            elif operation == "percentile_linear_interpolation":
                result = nan if any(_missing(v) for v in values) else (
                    array_percentile_linear_interpolation(values, self.percentage)
                )
            elif operation == "wma":
                result = fsum(w * v for w, v in enumerate(values, 1)) / (period * (period + 1) / 2)
            else:
                total = fsum(values)
                if operation == "rolling_sum":
                    result = total
                elif operation == "sma":
                    result = total / period
                else:
                    mean = total / period
                    result = sqrt(fsum((v - mean) ** 2 for v in values) / period)
        return self.history.set(bar, result)


def _pivot(values, left, right, high):
    _bar_index(left)
    _bar_index(right)
    values = tuple(values)
    result = []
    for i in range(len(values)):
        window = values[max(0, i - left - right):i + 1]
        if len(window) < left + right + 1 or any(_missing(v) for v in window):
            result.append(nan)
            continue
        candidate = window[left]
        if high:
            is_pivot = (all(candidate >= v for v in window[:left]) and
                        all(candidate > v for v in window[left+1:]))
        else:
            is_pivot = (all(candidate <= v for v in window[:left]) and
                        all(candidate < v for v in window[left+1:]))
        result.append(candidate if is_pivot else nan)
    return tuple(result)


def pivothigh(values, left, right):
    return _pivot(values, left, right, True)


def pivotlow(values, left, right):
    return _pivot(values, left, right, False)
