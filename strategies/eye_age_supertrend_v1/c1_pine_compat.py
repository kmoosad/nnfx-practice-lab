"""Closed-bar Pine calculation dependency, interface v1, rule revision 3.

This file is registered and hash-bound as one ``approved_dependency`` input.  It
is staged as ``nnfx.pine_compat`` for an admitted candidate; it is not imported
from the application checkout at candidate runtime.
"""

from collections import deque
from math import fsum, isqrt, isnan, nan, sqrt


__approved_module__ = "nnfx.pine_compat"
__dependency_interface__ = """pine_compat v1 public interface, rule revision 3
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
highest(values, length), lowest(values, length) -> tuple[float, ...]
rolling_sum(values, length) -> tuple[float, ...]
nz(value, replacement=0.0) -> scalar
safe_div(numerator, denominator) -> float
history(values, index, offset=1) -> value or NaN
crossover(left, right), crossunder(left, right) -> tuple[bool, ...]
ne(left, right) -> bool
pine_max(*values), pine_min(*values) -> numeric scalar or NaN
gated(values, condition) -> tuple of numeric values or NaN

values is an ordered finite-or-NaN numeric series. length is a positive simple
integer. Each candle supplies numeric high, low and close attributes. Series
results are aligned one-for-one with their input and use float NaN for numeric
missing values.
ne accepts numeric, Boolean, string and color-representation scalar operands;
it treats None and float NaN as missing without coercing strings to numbers.
pine_max/min accept one or more numeric scalar operands, with None also missing.
gated takes equal-length numeric values and Boolean/numeric conditions; it also
accepts None as missing and returns an empty tuple for two empty inputs.
"""
__approved_semantics__ = """NNFX closed-completed-bar rules, revision 3, applicable across source Pine versions.
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
true_range. highest and lowest inspect the last length bars (including the current
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
Calls have fresh batch-local state. Dynamic lengths, sample standard
deviation, other overloads, intrabar behavior and universal TradingView numeric
equivalence are outside this contract.
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
