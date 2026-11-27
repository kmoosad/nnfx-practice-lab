# This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © Uncle_the_shooter
# Python conversion of Age Adaptive Supertrend, Pine version 6.

import math
from .interface import Candle, IndicatorOutput
from .exit_pine_compat import (
    atr as ta_atr,
    supertrend,
    history,
    nz,
    ne,
    safe_div,
    pine_max,
    pine_min,
)


MAX_HIST = 300
MIN_SAMPLES = 15
SMOOTH_H = 2.0
USE_CENSOR = True
SPLIT_DIR = True


def sig(x):
    # Preserve 1 / (1 + exp(-x)), including its zero-valued overflow tail.
    try:
        exponential = math.exp(-x)
    except OverflowError:
        exponential = math.inf
    return safe_div(1.0, 1.0 + exponential)


def survAccum(durs, ids, t, nowId, hl, h):
    num = 0.0
    den = 0.0
    for i, dv in enumerate(durs):
        w = math.pow(0.5, safe_div(float(nowId - ids[i]), hl))
        if h > 0:
            a = safe_div(
                sig(safe_div(dv - t - 0.5, h)),
                sig(safe_div(dv - 0.5, h)),
            )
        else:
            a = 1.0 if dv > t else 0.0
        num += w * a
        den += w
    return num, den


def pushCapped(durs, ids, v, id, cap):
    durs.append(v)
    ids.append(id)
    if len(durs) > cap:
        durs.pop(0)
        ids.pop(0)


def calculate(
    candles,
    *,
    atrLen=10,
    baseMult=3.0,
    kExp=1.0,
    floorMult=1.2,
    halfLife=40.0,
    useEr=True,
    erHi=0.40,
    showRef=False,
):
    # Rendering, the independent TP/SL drawing subsystem, and the summary
    # table are omitted. dir retains the regime selecting the source colors.
    refMult = baseMult
    erLo = erHi - 0.25
    closes = tuple(float(c.close) for c in candles)

    # These two built-ins execute unconditionally in the source. Their only
    # inputs are immutable market rows and parameters, so batch evaluation
    # preserves their state and alignment independently of the custom loop.
    refST, refDir = supertrend(candles, refMult, atrLen)
    atr_values = ta_atr(candles, atrLen)

    durUp = []
    idsUp = []
    durDn = []
    idsDn = []
    refAge = 0
    seqId = 0

    dir = 1
    age = 0
    upBand = math.nan
    dnBand = math.nan
    tStart = math.nan
    tPath = 0.0

    result = {
        'plotLine': [],
        'hl2': [],
        'reference_plot': [],
        'dir': [],
        'flipped': [],
        'buySignal': [],
        'sellSignal': [],
        'buySignal_numeric': [],
        'sellSignal_numeric': [],
    }

    for i, candle in enumerate(candles):
        close = closes[i]
        previous_close = history(closes, i)
        previous_refDir = history(refDir, i)

        refFlip = (
            not math.isnan(previous_refDir)
            and ne(refDir[i], previous_refDir)
        )
        if refFlip:
            seqId += 1
            if previous_refDir < 0:
                pushCapped(durUp, idsUp, refAge, seqId, MAX_HIST)
            else:
                pushCapped(durDn, idsDn, refAge, seqId, MAX_HIST)
            refAge = 1
        else:
            refAge += 1

        if math.isnan(tStart):
            tStart = close
        tPath += abs(close - nz(previous_close, close))
        er = (
            safe_div(pine_max(0.0, dir * (close - tStart)), tPath)
            if tPath > 0 else 1.0
        )

        # Keep both written survival-function evaluations, in source order.
        numU, denU = survAccum(
            durUp, idsUp, age, seqId + 1, halfLife, SMOOTH_H
        )
        numD, denD = survAccum(
            durDn, idsDn, age, seqId + 1, halfLife, SMOOTH_H
        )
        num = (numU if dir == 1 else numD) if SPLIT_DIR else numU + numD
        den = (denU if dir == 1 else denD) if SPLIT_DIR else denU + denD
        nObs = (
            (len(durUp) if dir == 1 else len(durDn))
            if SPLIT_DIR else len(durUp) + len(durDn)
        )

        refIsUp = refDir[i] < 0
        censorFits = not SPLIT_DIR or ((dir == 1) == refIsUp)
        if USE_CENSOR and censorFits and refAge > age:
            num += 1.0
            den += 1.0

        S = safe_div(num, den) if nObs >= MIN_SAMPLES and den > 0 else 1.0
        if useEr:
            g = pine_max(
                0.0,
                pine_min(
                    1.0,
                    safe_div(erHi - er, pine_max(erHi - erLo, 1e-6)),
                ),
            )
        else:
            g = 1.0
        Seff = 1.0 - (1.0 - S) * g
        mult = pine_max(floorMult, baseMult * math.pow(Seff, kExp))

        multUp = mult if dir == 1 else baseMult
        multDn = mult if dir == -1 else baseMult
        atr = atr_values[i]
        hl2 = safe_div(float(candle.high) + float(candle.low), 2.0)
        newUp = hl2 - multUp * atr
        newDn = hl2 + multDn * atr

        prevUp = upBand
        prevDn = dnBand
        upBand = (
            newUp if math.isnan(prevUp) or previous_close < prevUp
            else pine_max(newUp, prevUp)
        )
        dnBand = (
            newDn if math.isnan(prevDn) or previous_close > prevDn
            else pine_min(newDn, prevDn)
        )

        prevDir = dir
        if dir == 1 and close < upBand:
            dir = -1
        elif dir == -1 and close > dnBand:
            dir = 1

        flipped = ne(dir, prevDir)
        if flipped:
            age = 1
            tStart = close
            tPath = 0.0
        else:
            age += 1

        buySignal = flipped and dir == 1
        sellSignal = flipped and dir == -1
        st = upBand if dir == 1 else dnBand
        plotLine = math.nan if flipped else st

        result['plotLine'].append(plotLine)
        result['hl2'].append(hl2)
        result['reference_plot'].append(refST[i] if showRef else math.nan)
        result['dir'].append(dir)
        result['flipped'].append(flipped)
        result['buySignal'].append(buySignal)
        result['sellSignal'].append(sellSignal)
        result['buySignal_numeric'].append(1.0 if buySignal else math.nan)
        result['sellSignal_numeric'].append(1.0 if sellSignal else math.nan)

    return IndicatorOutput(
        timestamps=tuple(c.timestamp for c in candles),
        series={name: tuple(values) for name, values in result.items()},
    )
