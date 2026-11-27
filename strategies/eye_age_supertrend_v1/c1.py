# This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © EyeAlgo
# Eye Trend Zones (original code)
# Completed-candle NNFX conversion. Presentation-only functionality is omitted.

from math import isnan, nan
from .interface import Candle, IndicatorOutput
from .c1_pine_compat import atr as pine_atr, highest, lowest, rma, history, nz, safe_div, pine_max, pine_min


PER_SIDE = 12
MIN_H = 0.25
MAX_H = 1.5
NEAR = 0.25


def _rsi(values, length):
    changes = tuple(value - history(values, i) for i, value in enumerate(values))
    gains = rma(tuple(pine_max(change, 0.0) for change in changes), length)
    losses = rma(tuple(pine_max(-change, 0.0) for change in changes), length)
    # Normalized Wilder relative strength; an all-flat denominator yields NaN.
    return tuple(safe_div(100.0 * gain, gain + loss) for gain, loss in zip(gains, losses))


def _supertrend(close, mid, atr_values, factor):
    lower, upper, trend, directions = [], [], [], []
    for i in range(len(close)):
        raw_upper = mid[i] + factor * atr_values[i]
        raw_lower = mid[i] - factor * atr_values[i]
        previous_lower = nz(history(lower, i))
        previous_upper = nz(history(upper, i))
        previous_close = history(close, i)
        current_lower = raw_lower if raw_lower > previous_lower or previous_close < previous_lower else previous_lower
        current_upper = raw_upper if raw_upper < previous_upper or previous_close > previous_upper else previous_upper
        previous_trend = history(trend, i)
        if isnan(history(atr_values, i)):
            direction = 1
        elif previous_trend == previous_upper:
            direction = -1 if close[i] > current_upper else 1
        else:
            direction = 1 if close[i] < current_lower else -1
        lower.append(current_lower)
        upper.append(current_upper)
        directions.append(direction)
        trend.append(current_lower if direction == -1 else current_upper)
    return tuple(trend), tuple(directions)


def _pivots(values, left, right, is_high):
    result = []
    for i in range(len(values)):
        if i < left + right:
            result.append(nan)
            continue
        center = i - right
        candidate = values[center]
        valid = not isnan(candidate)
        # Equal older extrema are admitted; an equal newer extreme supersedes it.
        for j in range(center - left, center):
            comparison = candidate >= values[j] if is_high else candidate <= values[j]
            if not comparison:
                valid = False
                break
        if valid:
            for j in range(center + 1, i + 1):
                comparison = candidate > values[j] if is_high else candidate < values[j]
                if not comparison:
                    valid = False
                    break
        result.append(candidate if valid else nan)
    return tuple(result)


def f_addZone(top, bot, res, flipped, zones, atr, close, bar_index):
    # Retain active geometry, merge order, flip eligibility and capacity pruning.
    # Box bookkeeping and strength-only members have no confluence dependency.
    merged = False
    for z in zones:
        if not merged and z['res'] == res and top >= z['bot'] and bot <= z['top']:
            hMax = nz(atr) * MAX_H
            z['top'] = pine_max(z['top'], top)
            z['bot'] = pine_min(z['bot'], bot)
            if z['top'] - z['bot'] > hMax:
                if res:
                    z['bot'] = z['top'] - hMax
                else:
                    z['top'] = z['bot'] + hMax
            if flipped and not z['flipped']:
                z['flipped'] = True
                z['born'] = bar_index
            merged = True
    if not merged:
        zones.append({'top': top, 'bot': bot, 'res': res, 'flipped': flipped, 'born': bar_index})
        count = sum(1 for z in zones if z['res'] == res)
        while count > PER_SIDE:
            far = -1
            farD = -1.0
            for j, z in enumerate(zones):
                if z['res'] == res:
                    distance = abs((z['top'] + z['bot']) / 2.0 - close)
                    if distance > farD:
                        farD = distance
                        far = j
            if far >= 0:
                zones.pop(far)
            count -= 1


def calculate(candles, *, atrLen=25, factor=2.5, showZones=True, swingLen=8, impulse=1.0, showFlip=True, rsiLenL=14, rsiUpLv=80, rsiDnLv=20, showStar=True, rsiLook=10, detailAlerts=True):
    timestamps = tuple(candle.timestamp for candle in candles)
    opens = tuple(float(candle.open) for candle in candles)
    high = tuple(float(candle.high) for candle in candles)
    low = tuple(float(candle.low) for candle in candles)
    close = tuple(float(candle.close) for candle in candles)
    mid = tuple((h + l) / 2.0 for h, l in zip(high, low))
    atr_values = pine_atr(candles, atrLen)
    ll3 = lowest(low, 3)
    hh3 = highest(high, 3)
    rsiL = _rsi(close, rsiLenL)
    rsiHi = tuple(value > rsiUpLv for value in rsiL)
    rsiLo = tuple(value < rsiDnLv for value in rsiL)
    tl, tDir = _supertrend(close, mid, atr_values, factor)
    up = tuple(direction < 0 for direction in tDir)
    turnUp = tuple(direction < 0 and nz(history(tDir, i)) > 0 for i, direction in enumerate(tDir))
    turnDn = tuple(direction > 0 and nz(history(tDir, i)) < 0 for i, direction in enumerate(tDir))
    tlShow = tuple(tl[i] if direction == nz(history(tDir, i)) else nan for i, direction in enumerate(tDir))
    ph = _pivots(high, swingLen, swingLen, True)
    pl = _pivots(low, swingLen, swingLen, False)
    winLow = lowest(low, swingLen + 1)
    winHigh = highest(high, swingLen + 1)

    names = ('atSup', 'atRes', 'rsiConfL', 'rsiConfS', 'starsL', 'starsS', 'confluence_buy', 'confluence_sell', 'rsi_above_upper', 'rsi_below_lower', 'detailed_alert')
    dynamic = {name: [] for name in names}
    zones = []
    last_hi = None
    last_lo = None
    for i in range(len(candles)):
        current_atr = atr_values[i]
        if rsiHi[i]:
            last_hi = i
        if rsiLo[i]:
            last_lo = i

        # barstate.isconfirmed is true for this completed-candle interface.
        if showZones and not isnan(current_atr):
            if not isnan(ph[i]):
                impD = safe_div(ph[i] - winLow[i], current_atr)
                if impD >= impulse:
                    bodyTop = pine_max(history(opens, i, swingLen), history(close, i, swingLen))
                    bottom = pine_max(ph[i] - current_atr * MAX_H, pine_min(bodyTop, ph[i] - current_atr * MIN_H))
                    f_addZone(ph[i], bottom, True, False, zones, current_atr, close[i], i)
            if not isnan(pl[i]):
                impU = safe_div(winHigh[i] - pl[i], current_atr)
                if impU >= impulse:
                    bodyBot = pine_min(history(opens, i, swingLen), history(close, i, swingLen))
                    top = pine_min(pl[i] + current_atr * MAX_H, pine_max(bodyBot, pl[i] + current_atr * MIN_H))
                    f_addZone(top, pl[i], False, False, zones, current_atr, close[i], i)

            pending_flips = []
            for j in range(len(zones) - 1, -1, -1):
                z = zones[j]
                broken = close[i] > z['top'] if z['res'] else close[i] < z['bot']
                if broken:
                    zones.pop(j)
                    if showFlip and not z['flipped']:
                        pending_flips.append((z['top'], z['bot'], not z['res']))
            for top, bottom, resistance in pending_flips:
                f_addZone(top, bottom, resistance, True, zones, current_atr, close[i], i)

        atSup = False
        atRes = False
        tol = nz(current_atr) * NEAR
        for z in zones:
            if z['born'] == i and z['flipped']:
                continue
            if not z['res'] and ll3[i] <= z['top'] + tol and close[i] >= z['bot'] - tol:
                atSup = True
            if z['res'] and hh3[i] >= z['bot'] - tol and close[i] <= z['top'] + tol:
                atRes = True
        rsiConfL = last_lo is not None and i - last_lo <= rsiLook
        rsiConfS = last_hi is not None and i - last_hi <= rsiLook
        starsL = (int(atSup) + int(rsiConfL)) if showStar else 0
        starsS = (int(atRes) + int(rsiConfS)) if showStar else 0
        previous_hi = False if i == 0 else history(rsiHi, i)
        previous_lo = False if i == 0 else history(rsiLo, i)
        values = (atSup, atRes, rsiConfL, rsiConfS, starsL, starsS,
                  turnUp[i] and starsL > 0, turnDn[i] and starsS > 0,
                  rsiHi[i] and not previous_hi, rsiLo[i] and not previous_lo,
                  detailAlerts and (turnUp[i] or turnDn[i]))
        for name, value in zip(names, values):
            dynamic[name].append(value)

    series = {'tlShow': tlShow, 'hl2': mid, 'tl': tl, 'tDir': tDir,
              'up': up, 'turnUp': turnUp, 'turnDn': turnDn,
              'rsiL': rsiL, 'rsiHi': rsiHi, 'rsiLo': rsiLo}
    series.update({name: tuple(values) for name, values in dynamic.items()})
    return IndicatorOutput(timestamps=timestamps, series=series)
