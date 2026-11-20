# This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © blackcat1402
# V2 - Polished: signal state machine + cooldown, ATR-based TP/SL tracking, full alert pack, dashboard
# Converted from Pine version 6: [blackcat] L2 Ehlers Bandpass Filter V2.
# Completed-candle calculation module; rendering and dashboard delivery are omitted.

import math
from .interface import Candle, IndicatorOutput
from .pine_compat import (
    LocalSeries, SeriesCall, atr, crossover, crossunder, history,
    ne, nz, pivotlow, pivothigh, safe_div,
)


def calculateBandpassFilter(closePrice, period, bandwidth, peakDecay):
    """The source-defined recurrence, including its persistent Signal fallback."""
    HP_history = LocalSeries()
    BP_history = LocalSeries()
    Peak_history = LocalSeries()
    Signal_history = LocalSeries()
    Trigger_history = LocalSeries()
    alpha2 = HP = gamma1 = alpha1 = beta1 = BP = Peak = Signal = Trigger = 0.0
    signals, triggers = [], []
    for bar, price in enumerate(closePrice):
        pi = 2 * math.asin(1)
        angle = safe_div(.25 * bandwidth * 2 * pi, period)
        alpha2 = safe_div(math.cos(angle) + math.sin(angle) - 1, math.cos(angle))
        HP = (1 + alpha2 / 2) * (price - nz(history(closePrice, bar))) + (1 - alpha2) * nz(HP_history.get(bar, 1))
        HP_history.set(bar, HP)

        beta1 = math.cos(safe_div(2 * pi, period))
        gamma1 = safe_div(1, math.cos(safe_div(2 * pi * bandwidth, period)))
        alpha1 = gamma1 - math.sqrt(gamma1 * gamma1 - 1)
        BP = .5 * (1 - alpha1) * (HP - nz(HP_history.get(bar, 2))) + beta1 * (1 + alpha1) * nz(BP_history.get(bar, 1)) - alpha1 * nz(BP_history.get(bar, 2))
        BP_history.set(bar, BP)
        BP = 0.0 if bar == 1 or bar == 2 else BP
        BP_history.set(bar, BP)

        Peak = peakDecay * nz(Peak_history.get(bar, 1))
        Peak_history.set(bar, Peak)
        Peak = abs(BP) if abs(BP) > Peak else Peak
        Peak_history.set(bar, Peak)
        Signal = safe_div(BP, Peak) if ne(Peak, 0) else Signal
        Signal_history.set(bar, Signal)

        angle = safe_div(1.5 * bandwidth * 2 * pi, period)
        alpha2 = safe_div(math.cos(angle) + math.sin(angle) - 1, math.cos(angle))
        Trigger = (1 + alpha2 / 2) * (Signal - nz(Signal_history.get(bar, 1))) + (1 - alpha2) * nz(Trigger_history.get(bar, 1))
        Trigger_history.set(bar, Trigger)
        signals.append(Signal)
        triggers.append(Trigger)
    return tuple(signals), tuple(triggers)


def _inRange(cond, bar, bars_call, rangeLower, rangeUpper):
    """One conditional source-function evaluation; its written call owns bars_call."""
    bars = bars_call.update(bar, cond == True)
    return rangeLower <= bars and bars <= rangeUpper


def _valuewhen_previous(condition, value, occurrences):
    """Source ta.valuewhen(..., 1); missing event values still count as events."""
    if condition:
        occurrences.append(value)
    position = len(occurrences) - 2
    return occurrences[position] if position >= 0 else math.nan


def calculate(
    candles, *, Period=20, Bandwidth=0.3, PeakDecay=0.991,
    confirmOnClose=True, cooldownBars=3,
    useTPSL=True, atrLen=14, slMult=2.0, tpMult=3.0,
    showBG=True,
    lbR=5, lbL=5, rangeUpper=60, rangeLower=5,
    plotBull=True, plotHiddenBull=False, plotBear=True, plotHiddenBear=False,
):
    closes = tuple(c.close for c in candles)
    lows = tuple(c.low for c in candles)
    highs = tuple(c.high for c in candles)
    Signal, Trigger = calculateBandpassFilter(closes, Period, Bandwidth, PeakDecay)

    # The interface supplies completed candles: barstate.isconfirmed is true.
    barOK = tuple(not confirmOnClose or True for _ in candles)
    crossUp = tuple(cross and ok for cross, ok in zip(crossover(Trigger, Signal), barOK))
    crossDown = tuple(cross and ok for cross, ok in zip(crossunder(Trigger, Signal), barOK))
    atrVal = atr(candles, atrLen)

    series = {
        'Signal': Signal,
        'Trigger': Trigger,
        'signal_fill_color': tuple('color.yellow' if a < b else 'color.fuchsia' for a, b in zip(Signal, Trigger)),
        'barOK': barOK,
        'crossUp': crossUp,
        'crossDown': crossDown,
    }
    risk_names = (
        'posState', 'entryPrice', 'take_profit', 'stop_loss', 'cooldownOK',
        'tpHitLong', 'slHitLong', 'tpHitShort', 'slHitShort', 'tpHit', 'slHit',
        'rawLongEntry', 'rawShortEntry', 'longEntry', 'shortEntry',
        'entry_or_exit_alert', 'background_color',
    )
    for name in risk_names:
        series[name] = []

    posState = 0
    lastSignalBar = None
    entryPrice = slPrice = tpPrice = math.nan
    for bar, close in enumerate(closes):
        cooldownOK = lastSignalBar is None or bar - lastSignalBar > cooldownBars
        tpHitLong = posState == 1 and useTPSL and not math.isnan(tpPrice) and close >= tpPrice and barOK[bar]
        slHitLong = posState == 1 and useTPSL and not math.isnan(slPrice) and close <= slPrice and barOK[bar]
        tpHitShort = posState == -1 and useTPSL and not math.isnan(tpPrice) and close <= tpPrice and barOK[bar]
        slHitShort = posState == -1 and useTPSL and not math.isnan(slPrice) and close >= slPrice and barOK[bar]
        tpHit = tpHitLong or tpHitShort
        slHit = slHitLong or slHitShort
        rawLongEntry = crossUp[bar] and cooldownOK
        rawShortEntry = crossDown[bar] and cooldownOK
        longEntry = rawLongEntry and not tpHit and not slHit
        shortEntry = rawShortEntry and not tpHit and not slHit

        if longEntry:
            posState = 1
            lastSignalBar = bar
            entryPrice = close
            slPrice = close - slMult * atrVal[bar]
            tpPrice = close + tpMult * atrVal[bar]
        elif shortEntry:
            posState = -1
            lastSignalBar = bar
            entryPrice = close
            slPrice = close + slMult * atrVal[bar]
            tpPrice = close - tpMult * atrVal[bar]
        elif tpHit or slHit:
            posState = 0
            lastSignalBar = bar
            entryPrice = math.nan
            slPrice = math.nan
            tpPrice = math.nan

        background = ('color.new(color.green, 95)' if showBG and posState == 1 else
                      'color.new(color.red, 95)' if showBG and posState == -1 else None)
        values = (
            posState, entryPrice, tpPrice if useTPSL else math.nan,
            slPrice if useTPSL else math.nan, cooldownOK,
            tpHitLong, slHitLong, tpHitShort, slHitShort, tpHit, slHit,
            rawLongEntry, rawShortEntry, longEntry, shortEntry,
            longEntry or shortEntry or tpHit or slHit, background,
        )
        for name, value in zip(risk_names, values):
            series[name].append(value)

    plFound = tuple(not math.isnan(value) for value in pivotlow(Signal, lbL, lbR))
    phFound = tuple(not math.isnan(value) for value in pivothigh(Signal, lbL, lbR))
    series['plFound'] = plFound
    series['phFound'] = phFound
    divergence_names = (
        'oscHL', 'priceLL', 'bullCond', 'regular_bullish_plot', 'regular_bullish_color',
        'oscLL', 'priceHL', 'hiddenBullCond', 'hidden_bullish_plot', 'hidden_bullish_color',
        'oscLH', 'priceHH', 'bearCond', 'regular_bearish_plot', 'regular_bearish_color',
        'oscHH', 'priceLH', 'hiddenBearCond', 'hidden_bearish_plot', 'hidden_bearish_color',
    )
    for name in divergence_names:
        series[name] = []

    # Four written _inRange calls have independent conditional barssince state.
    range_hl = SeriesCall('barssince')
    range_ll = SeriesCall('barssince')
    range_lh = SeriesCall('barssince')
    range_hh = SeriesCall('barssince')
    # Separate state for all eight written valuewhen calls, in source order.
    vw_hl, vw_price_ll, vw_ll, vw_price_hl = [], [], [], []
    vw_lh, vw_price_hh, vw_hh, vw_price_lh = [], [], [], []

    for bar in range(len(candles)):
        osc_pivot = history(Signal, bar, lbR)
        low_pivot = history(lows, bar, lbR)
        high_pivot = history(highs, bar, lbR)

        previous = _valuewhen_previous(plFound[bar], osc_pivot, vw_hl)
        oscHL = osc_pivot > previous and _inRange(history(plFound, bar), bar, range_hl, rangeLower, rangeUpper)
        previous = _valuewhen_previous(plFound[bar], low_pivot, vw_price_ll)
        priceLL = low_pivot < previous
        bullCond = plotBull and priceLL and oscHL and plFound[bar]

        previous = _valuewhen_previous(plFound[bar], osc_pivot, vw_ll)
        oscLL = osc_pivot < previous and _inRange(history(plFound, bar), bar, range_ll, rangeLower, rangeUpper)
        previous = _valuewhen_previous(plFound[bar], low_pivot, vw_price_hl)
        priceHL = low_pivot > previous
        hiddenBullCond = plotHiddenBull and priceHL and oscLL and plFound[bar]

        previous = _valuewhen_previous(phFound[bar], osc_pivot, vw_lh)
        oscLH = osc_pivot < previous and _inRange(history(phFound, bar), bar, range_lh, rangeLower, rangeUpper)
        previous = _valuewhen_previous(phFound[bar], high_pivot, vw_price_hh)
        priceHH = high_pivot > previous
        bearCond = plotBear and priceHH and oscLH and phFound[bar]

        previous = _valuewhen_previous(phFound[bar], osc_pivot, vw_hh)
        oscHH = osc_pivot > previous and _inRange(history(phFound, bar), bar, range_hh, rangeLower, rangeUpper)
        previous = _valuewhen_previous(phFound[bar], high_pivot, vw_price_lh)
        priceLH = high_pivot < previous
        hiddenBearCond = plotHiddenBear and priceLH and oscHH and phFound[bar]

        values = (
            oscHL, priceLL, bullCond,
            osc_pivot if plFound[bar] else math.nan,
            'color.new(color.green, 0)' if bullCond else 'color.new(color.white, 100)',
            oscLL, priceHL, hiddenBullCond,
            osc_pivot if plFound[bar] else math.nan,
            'color.new(color.green, 0)' if hiddenBullCond else 'color.new(color.white, 100)',
            oscLH, priceHH, bearCond,
            osc_pivot if phFound[bar] else math.nan,
            'color.new(color.red, 0)' if bearCond else 'color.new(color.white, 100)',
            oscHH, priceLH, hiddenBearCond,
            osc_pivot if phFound[bar] else math.nan,
            'color.new(color.red, 0)' if hiddenBearCond else 'color.new(color.white, 100)',
        )
        for name, value in zip(divergence_names, values):
            series[name].append(value)

    return IndicatorOutput(
        timestamps=tuple(c.timestamp for c in candles),
        series={name: tuple(values) for name, values in series.items()},
    )
