"""Qualify Python 03's fixed research origin inside its 5,000-candle capture.

The pre-origin padding in archived checks is an explicitly synthetic fixture:
changing it must not affect either indicator. Extended checks use retained
OANDA market data. Neither check is broker execution or scheduled preflight.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from nnfx_practice.candles import Candle
from strategies import eye_age_supertrend_v1 as strategy
from .check_python03_reference import NAMES, reference, values


def check(args):
    lab, inputs, pair, stride = args
    _, plan, pairs, original, saved = reference(lab)
    archived = next(p.candles for p in pairs if p.pair_code == pair)
    assert archived[0].timestamp == strategy.HISTORY_START
    packaged = {'c1': strategy.c1, 'exit': strategy.exit}
    observers = {'c1': strategy.observe_c1, 'exit': strategy.observe_exit}
    for role in NAMES:
        output = packaged[role].calculate(archived)
        expected = original[role].calculate(archived)
        assert {k: values(v) for k, v in output.series.items()} == {
            k: values(v) for k, v in expected.series.items()} == {
            k: tuple(v) for k, v in saved[pair][role + '_outputs'].items()}
    atr = strategy.atr.true_range_and_atr(archived)[1]
    assert atr == tuple(row['atr'] for row in saved[pair]['candles'])
    padding = tuple(Candle(strategy.HISTORY_START - timedelta(days=strategy.LOOKBACK_CANDLES - i),
        2.0, 3.0, 1.0, 2.5, None) for i in range(strategy.LOOKBACK_CANDLES))

    def padded(history):
        return padding[-(strategy.LOOKBACK_CANDLES - len(history)):] + tuple(history)

    def compare(window, expected, end):
        for role in NAMES:
            observed = observers[role](window)
            assert observed.current == tuple(expected[role][name][end] for name in NAMES[role])
            assert observed.previous == tuple(expected[role][name][end - 1] for name in NAMES[role])
            assert observed.error is None

    expected = {role: saved[pair][role + '_outputs'] for role in NAMES}
    archive_ends = sorted(set(range(plan['evaluation']['start_index'], len(archived), stride)) | {len(archived) - 1})
    for end in archive_ends:
        window = padded(archived[:end + 1])
        compare(window, expected, end)
        assert strategy.sizing_atr(window).value == atr[end]
    partial_checks = 0
    for end in range(600, len(archived), 127):
        candle = archived[end]
        for close in (candle.low, candle.high, (candle.open + candle.close) / 2):
            history = (*archived[:end], replace(candle, close=close))
            expected_partial = {role: original[role].calculate(history).series for role in NAMES}
            compare(padded(history), expected_partial, end)
            partial_checks += 1

    path = inputs / (pair.replace('/', '_') + '-extended.json')
    raw = path.read_bytes()
    document = json.loads(raw)
    rows = document['earlier']['body']['candles'] + document['recent']['body']['candles']
    extended = tuple(Candle(datetime.fromisoformat(row['time']),
        *(float(row['mid'][key]) for key in ('o', 'h', 'l', 'c')), row['volume']) for row in rows)
    assert all(a.timestamp < b.timestamp for a, b in zip(extended, extended[1:]))
    def normalized(sequence):
        return tuple(c for c in sequence if c.timestamp >= strategy.HISTORY_START
                     and c.timestamp.astimezone(ZoneInfo('America/New_York')).weekday() not in (4, 5))
    history = normalized(extended)
    overlap = tuple(c for c in history if c.timestamp <= archived[-1].timestamp)
    assert [(c.timestamp, c.open, c.high, c.low, c.close) for c in overlap] == [
        (c.timestamp, c.open, c.high, c.low, c.close) for c in archived]
    indices = {c.timestamp: i for i, c in enumerate(history)}
    expected = {role: original[role].calculate(history).series for role in NAMES}
    ends = sorted(set(range(strategy.LOOKBACK_CANDLES - 1, len(extended), stride)) | {len(extended) - 1})
    for end in ends:
        window = extended[end - strategy.LOOKBACK_CANDLES + 1:end + 1]
        index = indices[extended[end].timestamp]
        compare(window, expected, index)
        assert strategy.sizing_atr(window).value == strategy.atr.true_range_and_atr(history[:index + 1])[1][-1]
    for close in (history[-1].low, history[-1].high, (history[-1].open + history[-1].close) / 2):
        changed = (*extended[:-1], replace(extended[-1], close=close))
        expected_partial = {role: original[role].calculate(normalized(changed)).series for role in NAMES}
        compare(changed[-strategy.LOOKBACK_CANDLES:], expected_partial, len(history) - 1)
        partial_checks += 1
    return dict(pair=pair, archived_outputs='exact', archived_atr='exact', archived_windows=len(archive_ends),
        extended_windows=len(ends), extended_input_sha256=sha256(raw).hexdigest(),
        partial_snapshots=partial_checks, normalized_research_dates_and_ohlc='exact', status='passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stride', type=int, default=1)
    args = parser.parse_args()
    if args.stride < 1:
        parser.error('Stride must be positive')
    jobs = [(args.lab, args.inputs, pair, args.stride) for pair in ('EUR/USD', 'EUR/GBP', 'AUD/NZD', 'CHF/JPY')]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check, jobs))
    report = dict(source='offline_lab_reference_with_anchored_history', status='passed', exhaustive=args.stride == 1,
        result_id='18771091-9f76-4daf-bee9-a23f28634bae', qualified_total_candle_count=strategy.LOOKBACK_CANDLES,
        history_initialization=dict(mode='anchored', start=strategy.HISTORY_START.isoformat(), calendar='new_york_weekdays'),
        pairs=rows)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
