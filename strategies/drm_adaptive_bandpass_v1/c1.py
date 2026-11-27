# This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# © NordicAlphaLab

from math import isnan, nan
from .interface import Candle, IndicatorOutput
from .pine_compat import (
    array_percentile_linear_interpolation,
    ema,
    history,
    ne,
    nz,
    percentile_linear_interpolation,
)


def calculate(candles, *, momLen=60, Lookback=60, uThreshold=90.0,
              lThreshold=40.0, UseEMAConfluence=True, EMALength=30):
    closes = tuple(float(candle.close) for candle in candles)
    momentum_baseline = percentile_linear_interpolation(
        closes, momLen, (uThreshold + lThreshold) / 2.0
    )
    Momentum = tuple(
        close - baseline for close, baseline in zip(closes, momentum_baseline)
    )

    PriceWindow = []
    scores = []
    for momentum in Momentum:
        if not isnan(momentum):
            PriceWindow.append(momentum)
            if len(PriceWindow) > Lookback:
                PriceWindow.pop(0)

        AboveCount = 0
        score = nan
        if len(PriceWindow) == Lookback and not isnan(momentum):
            SortedPrices = PriceWindow.copy()
            SortedPrices.sort()
            for p in range(1, 100):
                PercentilePrice = array_percentile_linear_interpolation(
                    SortedPrices, p
                )
                if not isnan(PercentilePrice) and PercentilePrice < momentum:
                    AboveCount += 1
            score = AboveCount / 99.0 * 100.0
        scores.append(score)

    Score = tuple(scores)
    # This call is unconditional in the source, including when confluence is off.
    ScoreEMA = ema(Score, EMALength)

    state_outputs = {
        'EMA_Bullish': [],
        'EMA_Bearish': [],
        'Bullish': [],
        'Bearish': [],
        'NAL': [],
        'BullishFlip': [],
        'BearishFlip': [],
        'col': [],
        'bullish_transition': [],
        'bearish_transition': [],
    }
    nal_history = state_outputs['NAL']
    for i, (score, score_ema) in enumerate(zip(Score, ScoreEMA)):
        EMA_Bullish = (
            not UseEMAConfluence
            or (not isnan(score_ema) and score > score_ema)
        )
        EMA_Bearish = (
            not UseEMAConfluence
            or (not isnan(score_ema) and score < score_ema)
        )
        Bullish = not isnan(score) and score >= uThreshold and EMA_Bullish
        Bearish = not isnan(score) and score < lThreshold and EMA_Bearish

        previous_raw = history(nal_history, i)
        previous = nz(previous_raw, 0)
        NAL = 1 if Bullish else (-1 if Bearish else previous)

        # Completed-candle confirmation is true; no chart-last-bar inference.
        BullishFlip = NAL == 1 and ne(previous, 1)
        BearishFlip = NAL == -1 and ne(previous, -1)

        # Exact symbolic source-color representations, without renderer styling.
        col = (
            'color.rgb(0, 255, 200)' if NAL == 1
            else 'color.rgb(32, 94, 144)' if NAL == -1
            else 'color.gray'
        )
        bullish_transition = NAL == 1 and previous_raw == -1
        bearish_transition = NAL == -1 and previous_raw == 1

        state_outputs['EMA_Bullish'].append(EMA_Bullish)
        state_outputs['EMA_Bearish'].append(EMA_Bearish)
        state_outputs['Bullish'].append(Bullish)
        state_outputs['Bearish'].append(Bearish)
        state_outputs['NAL'].append(NAL)
        state_outputs['BullishFlip'].append(BullishFlip)
        state_outputs['BearishFlip'].append(BearishFlip)
        state_outputs['col'].append(col)
        state_outputs['bullish_transition'].append(bullish_transition)
        state_outputs['bearish_transition'].append(bearish_transition)

    series = {
        'Score': Score,
        'uThreshold': tuple(uThreshold for _ in candles),
        'lThreshold': tuple(lThreshold for _ in candles),
        'ScoreEMA': ScoreEMA,
        'ScoreEMA_plot': tuple(
            value if UseEMAConfluence else nan for value in ScoreEMA
        ),
    }
    series.update({key: tuple(values) for key, values in state_outputs.items()})
    return IndicatorOutput(
        timestamps=tuple(candle.timestamp for candle in candles),
        series=series,
    )
