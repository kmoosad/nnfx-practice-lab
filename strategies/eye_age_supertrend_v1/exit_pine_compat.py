"""Closed-bar Pine calculation dependency, interface v1, rule revision 6.

This file is registered and hash-bound as one ``approved_dependency`` input.  It
is staged as ``nnfx.pine_compat`` for an admitted candidate; it is not imported
from the application checkout at candidate runtime.
"""

from bisect import bisect_right
from collections import deque
from math import fsum, isfinite, isqrt, isnan, nan, sqrt


__approved_module__ = "nnfx.pine_compat"
__dependency_interface__ = """pine_compat v1 public interface, rule revision 6
exact_int(value) -> int
pine_round(value) -> int or NaN
sma(values, length) -> tuple[float, ...]
wma(values, length) -> tuple[float, ...]
hma(values, length) -> tuple[float, ...]
vwma(values, volumes, length) -> tuple[float, ...]
dmi(candles, di_length, adx_smoothing) -> (plus_di, minus_di, adx)
stdev(values, length) -> tuple[float, ...]
ema(values, length) -> tuple[float, ...]
rma(values, length) -> tuple[float, ...]
true_range(candles) -> tuple[float, ...]
atr(candles, length) -> tuple[float, ...]
supertrend(candles, factor, atr_length) -> (trend, direction)
percentrank(values, length) -> tuple[float, ...]
highest(values, length), lowest(values, length) -> tuple[float, ...]
rolling_sum(values, length) -> tuple[float, ...]
nz(value, replacement=0.0) -> scalar
safe_div(numerator, denominator) -> float
history(values, index, offset=1) -> value or NaN
crossover(left, right), crossunder(left, right) -> tuple[bool, ...]
ne(left, right) -> bool
pine_max(*values), pine_min(*values) -> numeric scalar or NaN
gated(values, condition) -> tuple of numeric values or NaN

LocalSeries(): set(bar, value) -> value; get(bar, offset=1) -> value or NaN
SeriesCall(operation, length=None, percentage=None):
    update(bar, value, other=NaN, length=None) -> scalar
    history -> LocalSeries of returned values
array_percentile_linear_interpolation(values, percentage) -> float
percentile_linear_interpolation(values, length, percentage) -> tuple[float, ...]
sar(candles, start, increment, maximum) -> tuple[float, ...]
pivothigh(values, left, right), pivotlow(values, left, right) -> tuple[float, ...]
highestbars(values, length), lowestbars(values, length) -> tuple[int or NaN, ...]
sma_dynamic(values, lengths), stdev_dynamic(values, lengths) -> tuple[float, ...]
highest_dynamic(values, lengths), lowest_dynamic(values, lengths) -> tuple[float, ...]
barssince(conditions) -> tuple[int or NaN, ...]
running_max(values), running_min(values) -> tuple[float, ...]

values is an ordered finite-or-NaN numeric series. length is a positive simple
integer. Each candle supplies numeric high, low and close attributes. Series
results are aligned one-for-one with their input and use float NaN for numeric
missing values.
supertrend accepts a numeric scalar factor or an aligned finite-or-NaN factor
series; atr_length is a positive simple integer. It returns two aligned numeric
tuples. A factor series must match the candle count. Zero and negative factors
are permitted; source parameter constraints remain authoritative.
ne accepts numeric, Boolean, string and color-representation scalar operands;
it treats None and float NaN as missing without coercing strings to numbers.
pine_max/min accept one or more numeric scalar operands, with None also missing.
gated takes equal-length numeric values and Boolean/numeric conditions; it also
accepts None as missing and returns an empty tuple for two empty inputs.
"""
__approved_semantics__ = """NNFX closed-completed-bar rules, revision 6, applicable across source Pine versions.
Revision-6 additions: exact_int accepts int unchanged or finite integral float,
converting only its representation to int. It rejects Boolean, fractional,
infinite or missing values with ValueError, without tolerance or rounding. Use it
at a discrete period/index boundary after the source expression; receiving helpers
still enforce their sign constraints. All previous helper argument rules remain.
pine_round implements only explicit source one-argument rounding: nearest integer,
ties toward positive infinity. Integers remain unchanged; None/float NaN yield NaN.
Boolean, nonnumeric and infinite values reject with ValueError. It preserves the
sides of representable half ties and never repairs an unrounded source expression.
The source version is context; these explicitly supplied NNFX rules govern the
standard helper calls. Custom recurrences retain their source initialization.
wma uses the latest length non-NaN observations, weighted 1 through length from
oldest to newest and divided by length*(length+1)/2. It remains NaN until length
observations exist, then carries its window over missing inputs.
hma uses half=max(1,length//2) and root=max(1,isqrt(length)); both round down.
It computes wma(2*wma(values,half)-wma(values,length),root). At a missing original
source observation the intermediate value is NaN, so every layer skips that
observation. Length one is the identity for defined values, carrying over missing.
vwma takes an explicit aligned volume series, without substituting missing data.
It is safe_div(sma(values*volumes,length),sma(volumes,length)) at each bar.
The two SMAs independently skip NaN under their existing contract. An unavailable
volume (None) rejects with missing_required_input; zero volume is available and a
zero denominator yields NaN. Empty aligned inputs return (). This maps Pine volume
to Candle.volume only under the common interface's declared-input convention.
dmi returns three aligned tuples (+DI,-DI,ADX). On each bar after the first,
up=high-previous_high and down=previous_low-low. +DM is up only when up>0 and
up>down, otherwise zero; -DM is down only when down>0 and down>up, otherwise zero.
Ties give zero to both. Both DM values are NaN if either change is missing.
TR uses max(high-low,abs(high-previous_close),abs(low-previous_close)); the first
bar and bars with missing current high/low or previous close have NaN TR.
Smooth TR and each DM independently with rma(di_length). Each DI is 100 times
smoothed DM / smoothed TR; a defined zero TR gives zero DI, while missing operands
give NaN. DX is abs(plus_di-minus_di)/(plus_di+minus_di), zero for a defined zero sum, NaN for missing
DI. ADX is 100*rma(DX,adx_smoothing). Thus length n DI first becomes available
after n defined changes, and ADX after its required defined DX observations.
All-missing startup stays NaN; flat complete prices eventually give zero DI/ADX.
These are explicit NNFX rules, not a universal TradingView equivalence claim.
sma and stdev use the latest length non-NaN observations and remain NaN until
that many observations exist. stdev implements the omitted biased=true overload
with population divisor length. ema uses alpha 2/(length+1), seeds from the first
non-NaN observation and retains state across NaN. rma uses alpha 1/length, seeds
with the SMA of the first length non-NaN observations and retains state across
NaN. true_range returns NaN when current high or low is NaN; otherwise it uses
high-low when the immediately previous close is NaN and the maximum of high-low,
abs(high-previous close) and abs(low-previous close) otherwise. atr is rma of
true_range.
supertrend uses hl2 and the existing atr(candles,atr_length). At each original
bar, raw upper/lower bands are hl2 plus/minus factor*ATR. Replace each missing
previous final band with zero. Retain the raw lower band when it exceeds the
previous lower band OR the previous close is below the previous lower band;
otherwise carry that previous band. Retain the raw upper band when it is below
the previous upper band OR the previous close exceeds the previous upper band;
otherwise carry that previous band. Missing numeric comparisons are false.
Set direction to +1 when the previous ATR is missing. Otherwise, if the previous
trend equals the zero-filled previous upper band, direction is -1 only when
current close strictly exceeds current upper band, and +1 otherwise. If that
equality is false, direction is +1 only when current close is strictly below
current lower band, and -1 otherwise. Trend is the lower band for -1 (uptrend),
upper band for +1 (downtrend). Before bar zero, ATR, close, bands and trend are
NaN. Apply this recurrence from the first bar, without extra warm-up masking;
in particular the first trend can be zero. Missing OHLC/factor values follow
the same recurrence, including ATR's existing skip/carry rules. Never substitute
this built-in helper for an explicitly source-defined Supertrend recurrence.
percentrank compares the current value with the immediately preceding length
original bars, EXCLUDING the current bar: 100*count(previous <= current)/length.
Ties count in full. The first eligible result is at zero-based index length.
Insufficient history, a missing current value or ANY NaN in that previous window
gives NaN. Missing observations occupy their original bar and are not skipped.
Length one is 100 for previous<=current and zero otherwise, once both are defined.
These window endpoints and startup are explicit NNFX choices; the public Pine
reference documents inclusive ties and NaN propagation but does not disambiguate
all window/startup details. No TradingView numerical equivalence is asserted.
Empty supertrend inputs return ((), ()); empty percentrank returns (). Both helpers
are unconditional original-bar calculations and are not supported by gated.
highest and lowest inspect the last length bars (including the current
bar), ignore NaN and use available startup bars; all-missing windows yield NaN.
rolling_sum requires length non-NaN observations and skips missing observations,
like sma. nz replaces None or numeric NaN, never zero or False. safe_div returns
NaN for a missing operand or zero denominator. history returns NaN before bar zero
and never uses negative Python indexing. Crosses require both operands defined
now and on the previous bar; equality on the previous bar is included, equality
on the current bar is excluded. Missing inputs produce False.
ne returns False when either operand is None or float NaN; otherwise compare the
original operands with !=. This applies to retained outputs as well as conditions,
deliberately standardizing older nullable inequality behavior. Zero, False and
strings (including the literal string 'nan') are defined values.
pine_max/min return NaN if any operand is missing, regardless of position;
otherwise return the numeric maximum/minimum without filtering out zero.
gated treats a missing condition as False, numeric zero as False and defined
nonzero numeric conditions as True. Boolean conditions keep their value. Strings
are not conditions. On a false condition, emit NaN; on a true condition, preserve
the input, normalizing a missing input to NaN. Keep original bar alignment.
Use gated only with sma, ema, rma, stdev and rolling_sum. For conditional ATR,
compute true_range on the full chart, then gate its values into rma. These helpers
skip missing inputs and retain their existing state/window; initialization still
requires their documented number of non-missing observations. They cannot tell
skipped executions from executed missing inputs. Keep the original condition for
source assignments; a skipped block performs no assignment. Report unsupported
behavior if a calculation needs that distinction inside the helper. Complete
OHLC input does not rule out missing derived values. Do not gate highest, lowest
or cross detection: their windows/history still use original chart positions.
Revision-5 additions (existing functions above are unchanged):
LocalSeries stores numeric/Boolean values (None normalizes to NaN). bar and offset
are nonnegative integers; writes must be chronological. Repeated set on one bar
replaces that bar's value, without changing previous bars. get(bar, offset) returns
the last committed value at or before bar-offset, or NaN before the first write.
Thus skipped bars do not insert observations; offsets into a gap read the same
last committed value. An executed NaN DOES replace the previous value. offset=0
can read the current assignment. Use separate ordinary variables for persistent
source updates, and LocalSeries for their history; history[1] never means the
previous loop iteration. These objects belong to one calculate invocation only.

SeriesCall supports only sma, wma, stdev, rolling_sum, ema, rma, highest, lowest,
highestbars, lowestbars, crossover, crossunder, barssince, running_max, running_min
and percentile_linear_interpolation. Other names reject. One instance represents
one written built-in call. Invoke update for each source evaluation, in order;
skipping a call means no update. Current-bar repetitions replace that bar's input
and result, evaluating against prior BAR commits, not earlier iterations. Custom
source persistent updates must still execute on every iteration outside this
helper. history exposes the local return series, including executed NaN results.
Call windows contain the current evaluation and prior executed bars' final inputs,
one observation per executed bar. Skipped bars contribute nothing; executed NaN
occupies a position for highest/lowest/offset/percentile windows. Mean/sum/WMA/
stdev/RMA seed windows instead skip missing observations as their batch APIs do.
EMA/RMA use the previous committed result with the existing seed/alpha rules.
Crosses compare current operands with the last committed pair; any missing operand
gives False. A missing condition is false. bars-since is zero when true, otherwise
the original chart-bar distance from the last committed true condition, or NaN
before any true condition. Running extrema skip missing and return NaN until the
first defined value, then combine current input with the prior committed result.
Offsets are nonpositive original chart-bar displacements from the current bar;
ties choose the most recent defined observation. Numeric empty windows give NaN.

Fixed window/EMA/RMA lengths are positive integers. SMA/WMA/stdev/sum/extrema/
offset/percentile calls may instead supply a positive integer length at update;
EMA/RMA require a fixed constructor length. Do not mix fixed and update lengths.
A missing dynamic length records the input but emits NaN; a later valid window
can use that observation. Zero, negative, Boolean, fractional or infinite lengths
reject. No default repair/rounding occurs. The four *_dynamic batch functions take
equal-sized values and lengths, on original chart bars. Their window, startup and
missing rules match the corresponding fixed-length batch functions at each bar.
They are not variable-alpha EMA/RMA. All public batch additions return () for
empty inputs after validating fixed arguments; mismatched series lengths reject.

Linear percentiles sort a copy, use rank=(n-1)*percentage/100 and interpolate
between floor/ceiling ranks. percentage is finite numeric in [0,100], not Boolean.
Array percentiles discard missing values; empty/all-missing gives NaN. Rolling
percentiles include the current observation, require length observations, and
return NaN for ANY missing window member. They do not mutate source arrays.

highestbars/lowestbars use the corresponding batch extreme window including
current, available startup bars and ignored missing values; the most recent tie
wins, offset zero denotes current, prior offsets are negative. pivothigh/pivotlow
take fixed nonnegative integer left/right strengths. At bar i, candidate i-right
is reported only after a complete left+right+1 window exists with no missing
member. It must be >= (<=) all left values and strictly > (<) all right values,
so the most recent equal extreme wins. Output appears on the confirmation bar,
never backdated; both strengths zero returns the defined current value.

sar uses finite numeric start/increment/maximum (not Boolean); source parameter
constraints remain authoritative. Bar zero is NaN. At bar one, close>prior close
starts below price with extreme=current high and result=prior low; otherwise
start above with extreme=current low and result=prior high. Set acceleration=start.
Each bar advance result by acceleration*(extreme-result). A below-price result
strictly above current low reverses above to max(current high,old extreme), with
extreme=current low and acceleration=start; the reverse test uses current high
and min(current low,old extreme). On noninitial, nonreversal bars, a strictly new
extreme advances acceleration to min(acceleration+increment,maximum). Finally
clamp below-price result to prior one/two lows, or above-price result to prior
one/two highs (only one at bar one). Missing operands propagate through arithmetic
and scalar extrema; missing comparisons are false. Do not invent recovery seeds.

Pivot ties/missing windows, percentile ranks, call observation windows and counter
timing are explicit NNFX conventions, not a universal TradingView-equivalence
claim. No dynamic EMA/RMA, arbitrary operation callbacks, intrabar execution or
automatic source-function/state translation is added.
"""


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


def gated(values, condition):
    """Mask skipped inputs for the approved missing-skipping helpers only."""

    if len(values) != len(condition):
        raise ValueError("unaligned gated operands")
    return tuple(
        value if _condition_true(active) and not _missing(value) else nan
        for value, active in zip(values, condition)
    )


def exact_int(value):
    """Lossless discrete representation, never a source rounding operation."""
    if type(value) is int:
        return value
    if type(value) is float and isfinite(value) and value.is_integer():
        return int(value)
    raise ValueError("discrete argument must be an exact integer")


def pine_round(value):
    """Explicit one-argument source round, nearest with ties upward."""
    if type(value) is int:
        return value
    if value is None or (type(value) is float and isnan(value)):
        return nan
    if type(value) is not float or not isfinite(value):
        raise ValueError("round requires a finite numeric value or missing observation")
    # Work on the represented binary64 value: adding 0.5 in float can erase
    # the distinction immediately below a half tie, or round a large integer up.
    numerator, denominator = value.as_integer_ratio()
    return (2 * numerator + denominator) // (2 * denominator)


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


def wma(values, length):
    """Linearly weighted non-missing observation window, newest weight largest."""
    length = _length(length)
    denominator = length * (length + 1) / 2
    return tuple(
        fsum(weight * value for weight, value in enumerate(window, 1)) / denominator
        if window else nan
        for window in _windows(values, length)
    )


def hma(values, length):
    """Hull construction with explicit integer lengths and missing-input gating."""
    length = _length(length)
    values = tuple(values)
    short = wma(values, max(1, length // 2))
    long = wma(values, length)
    raw = tuple(nan if _missing(value) else 2 * a - b
                for value, a, b in zip(values, short, long))
    return wma(raw, max(1, isqrt(length)))


def vwma(values, volumes, length):
    """Ratio of independent SMAs; never manufacture absent volume."""
    length = _length(length)
    if len(values) != len(volumes):
        raise ValueError("unaligned volume operands")
    if any(value is None for value in volumes):
        raise ValueError("missing_required_input")
    products = tuple(float(value) * float(volume) for value, volume in zip(values, volumes))
    return tuple(safe_div(a, b) for a, b in zip(sma(products, length), sma(volumes, length)))


def dmi(candles, di_length, adx_smoothing):
    """Directional movement and ADX with explicit Wilder startup and zero rules."""
    di_length = _length(di_length)
    adx_smoothing = _length(adx_smoothing)
    positive, negative, ranges = [], [], []
    previous_high = previous_low = previous_close = nan
    for candle in candles:
        high, low, close = float(candle.high), float(candle.low), float(candle.close)
        up, down = high - previous_high, previous_low - low
        if isnan(up) or isnan(down):
            positive.append(nan)
            negative.append(nan)
        else:
            positive.append(up if up > 0 and up > down else 0.0)
            negative.append(down if down > 0 and down > up else 0.0)
        ranges.append(nan if any(isnan(v) for v in (high, low, previous_close)) else
                      max(high - low, abs(high - previous_close), abs(low - previous_close)))
        previous_high, previous_low, previous_close = high, low, close
    smoothed_range = rma(ranges, di_length)

    def ratio(numerator, denominator):
        if isnan(numerator) or isnan(denominator):
            return nan
        return 0.0 if denominator == 0 else numerator / denominator

    plus = tuple(100 * ratio(a, b) for a, b in zip(rma(positive, di_length), smoothed_range))
    minus = tuple(100 * ratio(a, b) for a, b in zip(rma(negative, di_length), smoothed_range))
    dx = tuple(ratio(abs(a - b), a + b) for a, b in zip(plus, minus))
    return plus, minus, tuple(100 * value for value in rma(dx, adx_smoothing))


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


def ema(values, length):
    """Return the approved first-defined-seed exponential moving average."""

    length = _length(length)
    alpha = 2.0 / (length + 1.0)
    state = nan
    result = []
    for value in values:
        value = float(value)
        if not isnan(value):
            state = value if isnan(state) else alpha * value + (1.0 - alpha) * state
        result.append(state)
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


def supertrend(candles, factor, atr_length):
    """Return the specified original-bar Supertrend and direction (+1/-1)."""

    candles = tuple(candles)
    volatility = atr(candles, atr_length)
    if type(factor) in (int, float):
        factors = (float(factor),) * len(candles)
    else:
        factors = tuple(float(value) for value in factor)
        if len(factors) != len(candles):
            raise ValueError("unaligned supertrend factors")
    previous_close = previous_atr = previous_lower = previous_upper = previous_trend = nan
    trends, directions = [], []
    for candle, scale, current_atr in zip(candles, factors, volatility):
        midpoint = (float(candle.high) + float(candle.low)) / 2.0
        close = float(candle.close)
        lower = midpoint - scale * current_atr
        upper = midpoint + scale * current_atr
        prev_lower, prev_upper = nz(previous_lower), nz(previous_upper)
        lower = lower if lower > prev_lower or previous_close < prev_lower else prev_lower
        upper = upper if upper < prev_upper or previous_close > prev_upper else prev_upper
        if isnan(previous_atr):
            direction = 1.0
        elif previous_trend == prev_upper:
            direction = -1.0 if close > upper else 1.0
        else:
            direction = 1.0 if close < lower else -1.0
        trend = lower if direction == -1.0 else upper
        trends.append(trend)
        directions.append(direction)
        previous_close, previous_atr = close, current_atr
        previous_lower, previous_upper, previous_trend = lower, upper, trend
    return tuple(trends), tuple(directions)


def percentrank(values, length):
    """Rank current against the preceding length bars, with inclusive ties."""

    length = _length(length)
    window = deque(maxlen=length)
    result = []
    for value in values:
        value = float(value)
        if len(window) < length or isnan(value) or any(isnan(prior) for prior in window):
            result.append(nan)
        else:
            result.append(100.0 * sum(prior <= value for prior in window) / length)
        window.append(value)
    return tuple(result)


def _extreme(values, length, choose):
    window = deque(maxlen=_length(length))
    result = []
    for value in values:
        window.append(float(value))
        defined = [v for v in window if not isnan(v)]
        result.append(choose(defined) if defined else nan)
    return tuple(result)


def highest(values, length):
    return _extreme(values, length, max)


def lowest(values, length):
    return _extreme(values, length, min)


def rolling_sum(values, length):
    return tuple(fsum(window) if window else nan for window in _windows(values, length))


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


def _call_batch(values, operation, length=None, percentage=None):
    call = SeriesCall(operation, length, percentage)
    return tuple(call.update(i, value) for i, value in enumerate(values))


def percentile_linear_interpolation(values, length, percentage):
    _length(length)
    return _call_batch(values, "percentile_linear_interpolation", length, percentage)


def highestbars(values, length):
    _length(length)
    return _call_batch(values, "highestbars", length)


def lowestbars(values, length):
    _length(length)
    return _call_batch(values, "lowestbars", length)


def _dynamic(values, lengths, operation):
    values, lengths = tuple(values), tuple(lengths)
    if len(values) != len(lengths):
        raise ValueError("unaligned dynamic lengths")
    call = SeriesCall(operation)
    return tuple(
        call.update(i, value, length=length)
        for i, (value, length) in enumerate(zip(values, lengths))
    )


def sma_dynamic(values, lengths):
    return _dynamic(values, lengths, "sma")


def stdev_dynamic(values, lengths):
    return _dynamic(values, lengths, "stdev")


def highest_dynamic(values, lengths):
    return _dynamic(values, lengths, "highest")


def lowest_dynamic(values, lengths):
    return _dynamic(values, lengths, "lowest")


def barssince(conditions):
    return _call_batch(conditions, "barssince")


def running_max(values):
    return _call_batch(values, "running_max")


def running_min(values):
    return _call_batch(values, "running_min")


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


def sar(candles, start, increment, maximum):
    """Published SAR recurrence with explicit NNFX missing/scalar semantics."""
    for value in (start, increment, maximum):
        _finite_parameter(value)
    candles = tuple(candles)
    result, extreme, acceleration = nan, nan, nan
    below = False
    output = []
    for i, candle in enumerate(candles):
        if i == 0:
            output.append(nan)
            continue
        high, low, close = float(candle.high), float(candle.low), float(candle.close)
        first = i == 1
        if first:
            below = close > float(candles[i-1].close)
            extreme = high if below else low
            result = float(candles[i-1].low if below else candles[i-1].high)
            acceleration = start
        result += acceleration * (extreme - result)
        if below and result > low:
            first, below = True, False
            result, extreme, acceleration = pine_max(high, extreme), low, start
        elif not below and result < high:
            first, below = True, True
            result, extreme, acceleration = pine_min(low, extreme), high, start
        if not first:
            if below and high > extreme:
                extreme, acceleration = high, min(acceleration + increment, maximum)
            elif not below and low < extreme:
                extreme, acceleration = low, min(acceleration + increment, maximum)
        prior = candles[max(0, i-2):i]
        if below:
            result = pine_min(result, *(float(c.low) for c in prior))
        else:
            result = pine_max(result, *(float(c.high) for c in prior))
        output.append(result)
    return tuple(output)
