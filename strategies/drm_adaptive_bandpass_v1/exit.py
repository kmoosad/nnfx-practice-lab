# This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © blackcat1402
# V2 polished: Pine v6 migration, real adaptive dominant cycle (homodyne discriminator),
# position state machine, ATR take-profit / stop-loss, dashboard, full alert set.
# Converted for the NNFX completed-candle interface; presentation omissions are declared separately.

import math
from .interface import Candle, IndicatorOutput
from .pine_compat import (
    atr, highest, lowest, history, nz, safe_div, pine_max, pine_min,
    crossover, crossunder, pivotlow, pivothigh, barssince,
)


def calculate_ehlers_bandpass(close_price, avg_length, bw, adaptive_mode,
                              fixed_cycle, min_c, max_c, hp_len, lp_len,
                              lead_gain, p_decay, l_decay, trig_f):
    # One unconditional written source call, with fresh history for each batch.
    hp_h, filt_h, sh_h, i1_h = [], [], [], []
    inst_h, cycle_h, bp_h, peak_h = [], [], [], []
    signal_h, lead_peak_h, lead_signal_h = [], [], []
    trigger_h, trigger2_h, dominant_h = [], [], []
    pi = math.pi
    for i, p0 in enumerate(close_price):
        c_hp = math.cos(0.707 * 2 * pi / hp_len)
        s_hp = math.sin(0.707 * 2 * pi / hp_len)
        alpha1 = safe_div(c_hp + s_hp - 1, c_hp)
        p1 = nz(history(close_price, i, 1), p0)
        p2 = nz(history(close_price, i, 2), p0)
        hp = (math.pow(1 - alpha1 / 2, 2) * (p0 - 2 * p1 + p2)
              + 2 * (1 - alpha1) * nz(history(hp_h, i, 1))
              - math.pow(1 - alpha1, 2) * nz(history(hp_h, i, 2)))

        ss_a1 = math.exp(-1.414 * math.pi / lp_len)
        ss_b1 = 2 * ss_a1 * math.cos(1.414 * math.pi / lp_len)
        ss_c3 = -ss_a1 * ss_a1
        ss_c1 = 1 - ss_b1 - ss_c3
        filt = (ss_c1 * (hp + nz(history(hp_h, i, 1))) / 2
                + ss_b1 * nz(history(filt_h, i, 1))
                + ss_c3 * nz(history(filt_h, i, 2)))

        sh = (hp + 2 * nz(history(hp_h, i, 1))
              + 3 * nz(history(hp_h, i, 2)) + 3 * nz(history(hp_h, i, 3))
              + 2 * nz(history(hp_h, i, 4)) + nz(history(hp_h, i, 5))) / 12
        adj = 0.5 + 0.08 * nz(history(inst_h, i, 1))
        q1 = (0.0962 * sh + 0.5769 * nz(history(sh_h, i, 2))
              - 0.5769 * nz(history(sh_h, i, 4))
              - 0.0962 * nz(history(sh_h, i, 6))) * adj
        i1 = nz(history(sh_h, i, 3))
        q2 = (0.0962 * i1 + 0.5769 * nz(history(i1_h, i, 2))
              - 0.5769 * nz(history(i1_h, i, 4))
              - 0.0962 * nz(history(i1_h, i, 6))) * adj
        i2 = nz(history(i1_h, i, 3))
        re = i2 * i1 + q2 * q1
        im = i2 * q1 - q2 * i1
        phi = math.atan(0.0 if re == 0 else safe_div(im, re))
        per_raw = (safe_div(2 * pi, abs(phi)) if abs(phi) > 0.001
                   else nz(history(inst_h, i, 1), fixed_cycle))
        prev_per = nz(history(inst_h, i, 1), per_raw)
        per_raw = pine_min(per_raw, 1.5 * prev_per)
        per_raw = pine_max(per_raw, 0.67 * prev_per)
        lo_c = pine_min(min_c, max_c)
        hi_c = pine_max(min_c, max_c)
        per_cl = pine_max(lo_c, pine_min(hi_c, per_raw))
        inst_period = 0.33 * per_cl + 0.67 * prev_per
        cyc_prev = nz(history(cycle_h, i, 1), per_cl)
        cycle_smooth = cyc_prev + safe_div(per_cl - cyc_prev, pine_max(avg_length, 1.0))
        dominant_cycle = pine_max(lo_c, pine_min(hi_c, cycle_smooth)) if adaptive_mode else fixed_cycle

        beta1 = math.cos(safe_div(2 * pi, 0.9 * dominant_cycle))
        gamma1 = safe_div(1, math.cos(safe_div(2 * pi * bw, 0.9 * dominant_cycle)))
        alpha2 = gamma1 - math.sqrt(pine_max(gamma1 * gamma1 - 1, 0))
        bp = (0.5 * (1 - alpha2) * (filt - nz(history(filt_h, i, 2)))
              + beta1 * (1 + alpha2) * nz(history(bp_h, i, 1))
              - alpha2 * nz(history(bp_h, i, 2)))
        bp = 0.0 if i <= 2 else bp

        peak = p_decay * nz(history(peak_h, i, 1))
        peak = abs(bp) if abs(bp) > peak else peak
        signal = safe_div(bp, peak) if peak > 0 else nz(history(signal_h, i, 1))
        lead = lead_gain * (signal + nz(history(signal_h, i, 1))
                            - nz(history(signal_h, i, 2)) - nz(history(signal_h, i, 3))) / 4
        lead_peak = l_decay * nz(history(lead_peak_h, i, 1))
        lead_peak = abs(lead) if abs(lead) > lead_peak else lead_peak
        lead_signal = (safe_div(0.7 * lead, lead_peak) if lead_peak > 0
                       else nz(history(lead_signal_h, i, 1)))
        trigger = trig_f * nz(history(lead_signal_h, i, 1))
        trigger2 = trig_f * nz(history(signal_h, i, 1))

        hp_h.append(hp)
        filt_h.append(filt)
        sh_h.append(sh)
        i1_h.append(i1)
        inst_h.append(inst_period)
        cycle_h.append(cycle_smooth)
        bp_h.append(bp)
        peak_h.append(peak)
        signal_h.append(signal)
        lead_peak_h.append(lead_peak)
        lead_signal_h.append(lead_signal)
        trigger_h.append(trigger)
        trigger2_h.append(trigger2)
        dominant_h.append(dominant_cycle)
    return (tuple(lead_signal_h), tuple(trigger_h), tuple(signal_h),
            tuple(trigger2_h), tuple(dominant_h))


def calculate(candles, *, avgLength=3, bandwidth=0.3,
              cycleMode='Adaptive (Hilbert)', fixedCycle=48,
              minCycle=10.0, maxCycle=48.0, hpPeriod=48.0, lpPeriod=10.0,
              leadGain=1.3, peakDecay=0.991, leadDecay=0.93, trigFactor=0.9,
              cooldownBars=2, confirmClose=True, useZeroFilter=False, useZeroExit=True,
              useTPSL=True, atrLen=14, slMult=2.0, tpMult=3.0,
              useTrail=False, trailLen=10, trailMult=3.0, showStateBG=True,
              lbR=5, lbL=5, rangeUpper=60, rangeLower=5,
              plotBull=True, plotHiddenBull=False, plotBear=True, plotHiddenBear=False):
    closes = tuple(float(c.close) for c in candles)
    highs = tuple(float(c.high) for c in candles)
    lows = tuple(float(c.low) for c in candles)
    lead_signal, trigger, signal, trigger2, domCycle = calculate_ehlers_bandpass(
        closes, avgLength, bandwidth, cycleMode == 'Adaptive (Hilbert)',
        fixedCycle, minCycle, maxCycle, hpPeriod, lpPeriod,
        leadGain, peakDecay, leadDecay, trigFactor)
    atrVal = atr(candles, atrLen)
    hh = highest(highs, trailLen)
    ll = lowest(lows, trailLen)
    hhTrail = tuple(a - trailMult * b for a, b in zip(hh, atrVal))
    llTrail = tuple(a + trailMult * b for a, b in zip(ll, atrVal))
    zero = (0.0,) * len(candles)
    rawLong = crossover(lead_signal, trigger)
    rawShort = crossunder(lead_signal, trigger)
    xUnderZero = crossunder(lead_signal, zero)
    xOverZero = crossover(lead_signal, zero)
    series = {
        'lead_signal': lead_signal, 'trigger': trigger, 'signal': signal,
        'trigger2': trigger2, 'domCycle': domCycle, 'atrVal': atrVal,
        'zero_line': zero,
        'lead_fill_color': tuple('color.new(color.yellow, 60)' if a > b else
                                 'color.new(color.fuchsia, 60)' for a, b in zip(lead_signal, trigger)),
        'signal_fill_color': tuple('color.new(color.green, 70)' if a > b else
                                   'color.new(color.red, 70)' for a, b in zip(signal, trigger2)),
        'rawLong': rawLong, 'rawShort': rawShort,
        'xUnderZero': xUnderZero, 'xOverZero': xOverZero,
    }
    state_outputs = (
        'entryPrice', 'slLevel', 'tpLevel', 'trailLevel', 'posState',
        'cooldownOK', 'longOK', 'shortOK', 'stopLongHit', 'stopShortHit',
        'tpLongHit', 'tpShortHit', 'zeroExitLong', 'zeroExitShort',
        'doLongExit', 'doShortExit', 'entryBlocked', 'doLongEntry', 'doShortEntry',
        'flipLong', 'flipShort', 'longExitTag', 'shortExitTag', 'confirmed', 'bgCol',
        'position_flip', 'confirmed_and_doLongEntry', 'confirmed_and_doShortEntry',
        'confirmed_and_doLongExit', 'confirmed_and_doShortExit',
    )
    for name in state_outputs:
        series[name] = []
    posState = 0
    entryPrice = slLevel = tpLevel = trailLevel = math.nan
    lastSignalBar = None
    for i in range(len(candles)):
        barsSinceSignal = 999999 if lastSignalBar is None else i - lastSignalBar
        cooldownOK = barsSinceSignal > cooldownBars
        longOK = not useZeroFilter or lead_signal[i] > 0
        shortOK = not useZeroFilter or lead_signal[i] < 0
        effStopLong = (pine_max(nz(slLevel, -1e10), nz(trailLevel, -1e10))
                       if useTrail else nz(slLevel, -1e10))
        effStopShort = (pine_min(nz(slLevel, 1e10), nz(trailLevel, 1e10))
                        if useTrail else nz(slLevel, 1e10))
        stopLongHit = posState == 1 and useTPSL and lows[i] <= effStopLong
        stopShortHit = posState == -1 and useTPSL and highs[i] >= effStopShort
        tpLongHit = posState == 1 and useTPSL and highs[i] >= nz(tpLevel, 1e10)
        tpShortHit = posState == -1 and useTPSL and lows[i] <= nz(tpLevel, -1e10)
        zeroExitLong = posState == 1 and useZeroExit and xUnderZero[i]
        zeroExitShort = posState == -1 and useZeroExit and xOverZero[i]
        doLongExit = posState == 1 and (stopLongHit or tpLongHit or zeroExitLong)
        doShortExit = posState == -1 and (stopShortHit or tpShortHit or zeroExitShort)
        entryBlocked = doLongExit or doShortExit or stopLongHit or stopShortHit
        doLongEntry = (not entryBlocked and cooldownOK and posState <= 0
                       and rawLong[i] and longOK)
        doShortEntry = (not entryBlocked and cooldownOK and posState >= 0
                        and rawShort[i] and shortOK)
        flipLong = doLongEntry and posState == -1
        flipShort = doShortEntry and posState == 1
        longExitTag = 'SL' if stopLongHit else 'TP' if tpLongHit else 'X0'
        shortExitTag = 'SL' if stopShortHit else 'TP' if tpShortHit else 'X0'

        if doLongEntry:
            posState = 1
            entryPrice = closes[i]
            slLevel = closes[i] - slMult * atrVal[i] if useTPSL else math.nan
            tpLevel = closes[i] + tpMult * atrVal[i] if useTPSL else math.nan
            trailLevel = slLevel if useTrail else math.nan
            lastSignalBar = i
        elif doShortEntry:
            posState = -1
            entryPrice = closes[i]
            slLevel = closes[i] + slMult * atrVal[i] if useTPSL else math.nan
            tpLevel = closes[i] - tpMult * atrVal[i] if useTPSL else math.nan
            trailLevel = slLevel if useTrail else math.nan
            lastSignalBar = i
        elif doLongExit or doShortExit:
            posState = 0
            entryPrice = slLevel = tpLevel = trailLevel = math.nan
            lastSignalBar = i
        if useTrail and posState == 1:
            trailLevel = pine_max(nz(trailLevel, slLevel), hhTrail[i])
        elif useTrail and posState == -1:
            trailLevel = pine_min(nz(trailLevel, slLevel), llTrail[i])

        # Completed-candle confirmation is true; it is not a chart-last-bar test.
        confirmed = not confirmClose or True
        bgCol = None
        if showStateBG:
            bgCol = ('color.new(color.green, 92)' if posState == 1 else
                     'color.new(color.red, 92)' if posState == -1 else None)
        values = {
            'entryPrice': entryPrice, 'slLevel': slLevel, 'tpLevel': tpLevel,
            'trailLevel': trailLevel, 'posState': posState, 'cooldownOK': cooldownOK,
            'longOK': longOK, 'shortOK': shortOK,
            'stopLongHit': stopLongHit, 'stopShortHit': stopShortHit,
            'tpLongHit': tpLongHit, 'tpShortHit': tpShortHit,
            'zeroExitLong': zeroExitLong, 'zeroExitShort': zeroExitShort,
            'doLongExit': doLongExit, 'doShortExit': doShortExit,
            'entryBlocked': entryBlocked, 'doLongEntry': doLongEntry,
            'doShortEntry': doShortEntry, 'flipLong': flipLong, 'flipShort': flipShort,
            'longExitTag': longExitTag, 'shortExitTag': shortExitTag,
            'confirmed': confirmed, 'bgCol': bgCol,
            'position_flip': flipLong or flipShort,
            'confirmed_and_doLongEntry': confirmed and doLongEntry,
            'confirmed_and_doShortEntry': confirmed and doShortEntry,
            'confirmed_and_doLongExit': confirmed and doLongExit,
            'confirmed_and_doShortExit': confirmed and doShortExit,
        }
        for name, value in values.items():
            series[name].append(value)

    osc = lead_signal
    pl = pivotlow(osc, lbL, lbR)
    ph = pivothigh(osc, lbL, lbR)
    plFound = tuple(not math.isnan(v) for v in pl)
    phFound = tuple(not math.isnan(v) for v in ph)
    barsSincePL = tuple(nz(v, 999999) for v in barssince(plFound))
    barsSincePH = tuple(nz(v, 999999) for v in barssince(phFound))
    series['plFound'] = plFound
    series['phFound'] = phFound
    div_outputs = (
        'plInRange', 'phInRange', 'oscHL', 'priceLL', 'bullCond',
        'oscLL', 'priceHL', 'hiddenBullCond', 'oscLH', 'priceHH', 'bearCond',
        'oscHH', 'priceLH', 'hiddenBearCond', 'pivot_low_plot', 'pivot_high_plot',
        'bull_color', 'hidden_bull_color', 'bear_color', 'hidden_bear_color',
        'confirmed_and_bullCond', 'confirmed_and_bearCond',
    )
    for name in div_outputs:
        series[name] = []
    low_events, high_events = [], []
    for i in range(len(candles)):
        current_osc = history(osc, i, lbR)
        current_low = history(lows, i, lbR)
        current_high = history(highs, i, lbR)
        # valuewhen occurrence 1 includes the current occurrence, then selects
        # the second most recent. Identical unconditional written queries share
        # only their event data, with no change to execution or observation timing.
        if plFound[i]:
            low_events.append((current_osc, current_low))
        if phFound[i]:
            high_events.append((current_osc, current_high))
        previous_low = low_events[len(low_events) - 2] if len(low_events) >= 2 else (math.nan, math.nan)
        previous_high = high_events[len(high_events) - 2] if len(high_events) >= 2 else (math.nan, math.nan)
        plInRange = rangeLower <= barsSincePL[i] and barsSincePL[i] <= rangeUpper
        phInRange = rangeLower <= barsSincePH[i] and barsSincePH[i] <= rangeUpper
        oscHL = current_osc > nz(previous_low[0], current_osc) and plInRange
        priceLL = current_low < nz(previous_low[1], current_low)
        bullCond = plotBull and priceLL and oscHL and plFound[i]
        oscLL = current_osc < nz(previous_low[0], current_osc) and plInRange
        priceHL = current_low > nz(previous_low[1], current_low)
        hiddenBullCond = plotHiddenBull and priceHL and oscLL and plFound[i]
        oscLH = current_osc < nz(previous_high[0], current_osc) and phInRange
        priceHH = current_high > nz(previous_high[1], current_high)
        bearCond = plotBear and priceHH and oscLH and phFound[i]
        oscHH = current_osc > nz(previous_high[0], current_osc) and phInRange
        priceLH = current_high < nz(previous_high[1], current_high)
        hiddenBearCond = plotHiddenBear and priceLH and oscHH and phFound[i]
        confirmed = series['confirmed'][i]
        values = {
            'plInRange': plInRange, 'phInRange': phInRange,
            'oscHL': oscHL, 'priceLL': priceLL, 'bullCond': bullCond,
            'oscLL': oscLL, 'priceHL': priceHL, 'hiddenBullCond': hiddenBullCond,
            'oscLH': oscLH, 'priceHH': priceHH, 'bearCond': bearCond,
            'oscHH': oscHH, 'priceLH': priceLH, 'hiddenBearCond': hiddenBearCond,
            'pivot_low_plot': current_osc if plFound[i] else math.nan,
            'pivot_high_plot': current_osc if phFound[i] else math.nan,
            'bull_color': 'color.new(color.green, 0)' if bullCond else 'color.new(color.white, 100)',
            'hidden_bull_color': 'color.new(color.green, 0)' if hiddenBullCond else 'color.new(color.white, 100)',
            'bear_color': 'color.new(color.red, 0)' if bearCond else 'color.new(color.white, 100)',
            'hidden_bear_color': 'color.new(color.red, 0)' if hiddenBearCond else 'color.new(color.white, 100)',
            'confirmed_and_bullCond': confirmed and bullCond,
            'confirmed_and_bearCond': confirmed and bearCond,
        }
        for name, value in values.items():
            series[name].append(value)
    return IndicatorOutput(
        timestamps=tuple(c.timestamp for c in candles),
        series={name: tuple(values) for name, values in series.items()},
    )
