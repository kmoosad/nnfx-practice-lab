# This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © loxx
# Indicator: STD-Adaptive T3 Channel w/ Ehlers Swiss Army Knife Mod. [Loxx]
# Library implementation: loxx/loxxexpandedsourcetypes, observed publication 4,
# used for the source import requesting publication 3 under owner-approved resolution.

import math
from .interface import Candle, IndicatorOutput
from .pine_compat import (
    LocalSeries, SeriesCall, exact_int, nz, ne, safe_div,
    pine_max, pine_min, history, sma, stdev, atr, crossover, crossunder,
)


def _child(state, key):
    if key not in state:
        state[key] = {}
    return state[key]


def _local(state, key):
    if key not in state:
        state[key] = LocalSeries()
    return state[key]


def _call(state, key, operation, bar, value, length):
    if key not in state:
        state[key] = SeriesCall(operation, length=length)
    return state[key].update(bar, value)


def rclose(candle):
    return float(candle.close)


def ropen(candle):
    return float(candle.open)


def rhigh(candle):
    return float(candle.high)


def rlow(candle):
    return float(candle.low)


def rmedian(candle):
    return (rhigh(candle) + rlow(candle)) / 2.0


def rtypical(candle):
    return (rhigh(candle) + rlow(candle) + rclose(candle)) / 3.0


def rweighted(candle):
    return (rhigh(candle) + rlow(candle) + rclose(candle) + rclose(candle)) / 4.0


def raverage(candle):
    return (ropen(candle) + rhigh(candle) + rlow(candle) + rclose(candle)) / 4.0


def ravemedbody(candle):
    return (ropen(candle) + rclose(candle)) / 2.0


def _trendreg(o, h, l, c):
    compute = 0.0
    if c > o:
        compute = (h + c) / 2.0
    else:
        compute = (l + c) / 2.0
    return compute


def _trendext(o, h, l, c):
    compute = 0.0
    if c > o:
        compute = h
    elif c < o:
        compute = l
    else:
        compute = c
    return compute


def rtrendb(candle):
    return _trendreg(ropen(candle), rhigh(candle), rlow(candle), rclose(candle))


def rtrendbext(candle):
    return _trendext(ropen(candle), rhigh(candle), rlow(candle), rclose(candle))


def _ama(src, length, fl, sl, candle, bar, state):
    flout = safe_div(2.0, fl + 1)
    slout = safe_div(2.0, sl + 1)
    hh = _call(state, 'hh', 'highest', bar, rhigh(candle), exact_int(length + 1))
    ll = _call(state, 'll', 'lowest', bar, rlow(candle), exact_int(length + 1))
    mltp = safe_div(abs(2 * src - ll - hh), hh - ll) if ne(hh - ll, 0) else 0.0
    ssc = mltp * (flout - slout) + slout
    ama_history = _local(state, 'ama')
    previous = nz(ama_history.get(bar))
    ama = previous + math.pow(ssc, 2) * (src - previous)
    ama_history.set(bar, ama)
    return ama


def _t3(src, length, bar, state):
    xe1_1 = _call(state, 'xe1_1', 'ema', bar, src, length)
    xe2_1 = _call(state, 'xe2_1', 'ema', bar, xe1_1, length)
    xe3_1 = _call(state, 'xe3_1', 'ema', bar, xe2_1, length)
    xe4_1 = _call(state, 'xe4_1', 'ema', bar, xe3_1, length)
    xe5_1 = _call(state, 'xe5_1', 'ema', bar, xe4_1, length)
    xe6_1 = _call(state, 'xe6_1', 'ema', bar, xe5_1, length)
    b_1 = 0.7
    c1_1 = -b_1 * b_1 * b_1
    c2_1 = 3 * b_1 * b_1 + 3 * b_1 * b_1 * b_1
    c3_1 = -6 * b_1 * b_1 - 3 * b_1 - 3 * b_1 * b_1 * b_1
    c4_1 = 1 + 3 * b_1 + b_1 * b_1 * b_1 + 3 * b_1 * b_1
    nT3Average = c1_1 * xe6_1 + c2_1 * xe5_1 + c3_1 * xe4_1 + c4_1 * xe3_1
    return nT3Average


def _kama(src, length, kama_fastend, kama_slowend, bar, state):
    src_history = _local(state, 'src')
    xvnoise = abs(src - src_history.get(bar))
    src_history.set(bar, src)
    nfastend = kama_fastend
    nslowend = kama_slowend
    nsignal = abs(src - src_history.get(bar, exact_int(length)))
    nnoise = _call(state, 'nnoise', 'rolling_sum', bar, xvnoise, exact_int(length))
    nefratio = safe_div(nsignal, nnoise) if ne(nnoise, 0) else 0.0
    nsmooth = math.pow(nefratio * (nfastend - nslowend) + nslowend, 2)
    ama_history = _local(state, 'nAMA')
    previous = nz(ama_history.get(bar))
    nAMA = previous + nsmooth * (src - previous)
    ama_history.set(bar, nAMA)
    return nAMA


def _habingest(candle):
    out = (ropen(candle) + rclose(candle)) / 2.0 + (
        safe_div(rclose(candle) - ropen(candle), rhigh(candle) - rlow(candle))
        * abs((rclose(candle) - ropen(candle)) / 2.0)
    )
    out = rclose(candle) if math.isnan(out) else out
    return out


def habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    amaout = _ama(_habingest(candle), 2, amafl, amasl, candle, bar, _child(state, 'amaout'))
    t3out = _t3(_habingest(candle), 3, bar, _child(state, 't3out'))
    kamaout = _kama(_habingest(candle), 2, kfl, ksl, bar, _child(state, 'kamaout'))
    result = amaout if smthtype == 'AMA' else t3out if smthtype == 'T3' else kamaout
    _local(state, 'return').set(bar, result)
    return result


def habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    open_history = _local(state, 'habopen')
    previous = open_history.get(bar)
    current = 0.0
    # The two written habclose calls in the ternary own distinct state.
    # Their [1] reads are committed local history, not the current return.
    if math.isnan(previous):
        close_state = _child(state, 'initial_habclose')
        habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, close_state)
        current = (nz(current) + nz(_local(close_state, 'return').get(bar))) / 2.0
    else:
        close_state = _child(state, 'later_habclose')
        habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, close_state)
        current = (nz(previous) + nz(_local(close_state, 'return').get(bar))) / 2.0
    open_history.set(bar, current)
    return current


def habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    return pine_max(
        rhigh(candle),
        habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open')),
        habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close')),
    )


def hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    return pine_min(
        rlow(candle),
        habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open')),
        habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close')),
    )


def habmedian(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    return (high + low) / 2.0


def habtypical(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    close = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close'))
    return (high + low + close) / 3.0


def habweighted(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    close1 = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close1'))
    close2 = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close2'))
    return (high + low + close1 + close2) / 4.0


def habaverage(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    open_value = habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open'))
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    close = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close'))
    return (open_value + high + low + close) / 4.0


def habavemedbody(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    open_value = habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open'))
    close = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close'))
    return (open_value + close) / 2.0


def habtrendb(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    open_value = habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open'))
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    close = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close'))
    return _trendreg(open_value, high, low, close)


def habtrendbext(smthtype, amafl, amasl, kfl, ksl, candle, bar, state):
    open_value = habopen(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'open'))
    high = habhigh(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'high'))
    low = hablow(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'low'))
    close = habclose(smthtype, amafl, amasl, kfl, ksl, candle, bar, _child(state, 'close'))
    return _trendext(open_value, high, low, close)


def _iT3(src, per, hot, clean, bar, state):
    a = hot
    _c1 = -a * a * a
    _c2 = 3 * a * a + 3 * a * a * a
    _c3 = -6 * a * a - 3 * a - 3 * a * a * a
    _c4 = 1 + 3 * a + a * a * a + 3 * a * a
    alpha = 0.0
    if clean == 'T3 New':
        alpha = safe_div(2.0, 2.0 + (per - 1.0) / 2.0)
    elif clean == 'T3 Swiss Army Knife Mod':
        alpha = safe_div(
            math.cos(safe_div(2 * math.pi, per))
            + math.sin(safe_div(2 * math.pi, per)) - 1,
            math.cos(safe_div(2 * math.pi, per)),
        )
    else:
        alpha = safe_div(2.0, 1.0 + per)
    stages = []
    current = src
    for key in ('_t30', '_t31', '_t32', '_t33', '_t34', '_t35'):
        stage_history = _local(state, key)
        previous = nz(stage_history.get(bar))
        current = previous + alpha * (current - previous)
        stage_history.set(bar, current)
        stages.append(current)
    out = _c1 * stages[5] + _c2 * stages[4] + _c3 * stages[3] + _c4 * stages[2]
    return out


def calculate(
    candles, *,
    smthtype='Kaufman',
    srcoption='Close',
    per=35,
    T3Hot=0.7,
    T3Clean='T3 Swiss Army Knife Mod',
    AdaptPeriod=24,
    atrper=72,
    mult=3.0,
    kfl=0.666,
    ksl=0.0645,
    amafl=2,
    amasl=30,
):
    # NNFX-015 heikin_ashi_sources: remove the synthetic-ticker requests and
    # their exclusive HA switch branches. The common boundary rejects every
    # HA source selection. Close is the unchanged, source-defined default;
    # regular and library HAB alternatives need no synthetic chart input.
    regular_sources = {
        'Close': rclose,
        'Open': ropen,
        'High': rhigh,
        'Low': rlow,
        'Median': rmedian,
        'Typical': rtypical,
        'Weighted': rweighted,
        'Average': raverage,
        'Average Median Body': ravemedbody,
        'Trend Biased': rtrendb,
        'Trend Biased (Extreme)': rtrendbext,
    }
    better_sources = {
        'HAB Close': habclose,
        'HAB Open': habopen,
        'HAB High': habhigh,
        'HAB Low': hablow,
        'HAB Median': habmedian,
        'HAB Typical': habtypical,
        'HAB Weighted': habweighted,
        'HAB Average': habaverage,
        'HAB Average Median Body': habavemedbody,
        'HAB Trend Biased': habtrendb,
        'HAB Trend Biased (Extreme)': habtrendbext,
    }
    source_state = {}
    src_values = []
    for bar, candle in enumerate(candles):
        if srcoption in regular_sources:
            src = regular_sources[srcoption](candle)
        else:
            src = better_sources[srcoption](
                smthtype, amafl, amasl, kfl, ksl, candle, bar, source_state
            )
        src_values.append(src)

    dev = stdev(src_values, AdaptPeriod)
    avg = sma(dev, AdaptPeriod)
    t3_state = {}
    out_values = []
    for bar, src in enumerate(src_values):
        period = 0.0
        if ne(dev[bar], 0):
            period = safe_div(per * avg[bar], dev[bar])
        else:
            period = per
        if period < 3:
            period = 3
        out_values.append(_iT3(src, period, T3Hot, T3Clean, bar, t3_state))

    out = tuple(out_values)
    sig = tuple(history(out, bar) for bar in range(len(candles)))
    slope_values = []
    for current, previous in zip(out, sig):
        slope = 0.0
        if current > previous:
            slope = 1.0
        if current < previous:
            slope = -1.0
        slope_values.append(slope)
    slope = tuple(slope_values)
    atr_values = atr(candles, atrper)
    smax = tuple(value + volatility * mult for value, volatility in zip(out, atr_values))
    smin = tuple(value - volatility * mult for value, volatility in zip(out, atr_values))
    colorout = tuple('#2DD204' if value == 1 else '#D2042D' for value in slope)
    goLong = crossover(out, sig)
    goShort = crossunder(out, sig)
    return IndicatorOutput(
        timestamps=tuple(candle.timestamp for candle in candles),
        series={
            'out': out,
            'smax': smax,
            'smin': smin,
            'slope': slope,
            'colorout': colorout,
            'goLong': goLong,
            'goShort': goShort,
        },
    )
