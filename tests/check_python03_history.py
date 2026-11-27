"""Offline initialization check against retained OANDA historical market data.

This does not contact OANDA or qualify a scheduled partial-candle capture.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from nnfx_practice.candles import Candle
from strategies import eye_age_supertrend_v1 as strategy
from .check_python03_reference import NAMES, reference, values


def check_pair(args):
    lab, path, count, stride = args
    raw = path.read_bytes()
    document = json.loads(raw)
    rows = document['earlier']['body']['candles'] + document['recent']['body']['candles']
    candles = tuple(Candle(datetime.fromisoformat(row['time']),
        *(float(row['mid'][key]) for key in ('o', 'h', 'l', 'c')), row['volume']) for row in rows)
    assert len(candles) > count
    assert all(a.timestamp < b.timestamp for a, b in zip(candles, candles[1:]))
    assert all(0 < c.low <= min(c.open, c.close) <= max(c.open, c.close) <= c.high for c in candles)
    _, _, _, original, _ = reference(lab)
    packaged = {'c1': strategy.c1, 'exit': strategy.exit}
    full = {}
    for role in NAMES:
        full[role] = original[role].calculate(candles)
        same = packaged[role].calculate(candles)
        assert {k: values(v) for k, v in full[role].series.items()} == {k: values(v) for k, v in same.series.items()}
    mismatches = {role: [] for role in NAMES}
    examples = []
    endpoints = sorted(set(range(count - 1, len(candles), stride)) | {len(candles) - 1})
    atr = strategy.atr.true_range_and_atr(candles)[1]
    for end in endpoints:
        window = candles[end - count + 1:end + 1]
        assert strategy.atr.true_range_and_atr(window)[1][-1] == atr[end]
        for role in NAMES:
            output = packaged[role].calculate(window)
            observed = {name: values(output.series[name][-2:]) for name in NAMES[role]}
            expected = {name: values(full[role].series[name][end - 1:end + 1]) for name in NAMES[role]}
            if observed != expected:
                mismatches[role].append(end)
                if len(examples) < 8:
                    examples.append(dict(role=role, timestamp=candles[end].timestamp.isoformat(),
                        window=observed, full_history=expected))
    partial = {role: [] for role in NAMES}
    for close in (candles[-1].low, candles[-1].high, (candles[-1].open + candles[-1].close) / 2):
        changed = (*candles[:-1], replace(candles[-1], close=close))
        for role in NAMES:
            output = packaged[role].calculate(changed[-count:])
            expected = original[role].calculate(changed)
            if any(values(output.series[name][-2:]) != values(expected.series[name][-2:]) for name in NAMES[role]):
                partial[role].append(close)
    return dict(pair=path.stem.split('-')[0], input_sha256=sha256(raw).hexdigest(),
        available_candles=len(candles), first=candles[0].timestamp.isoformat(), last=candles[-1].timestamp.isoformat(),
        count=count, stride=stride, windows=len(endpoints), identical_inputs='exact', sizing_atr='exact',
        mismatches=mismatches, mismatch_examples=examples, partial_mismatches=partial)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--stride', type=int, default=32)
    args = parser.parse_args()
    if not 15 <= args.count <= 5000 or args.stride < 1:
        parser.error('Count must be 15–5000 and stride must be positive')
    jobs = [(args.lab, args.inputs / (pair + '-extended.json'), args.count, args.stride)
            for pair in ('EUR_USD', 'EUR_GBP', 'AUD_NZD', 'CHF_JPY')]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check_pair, jobs))
    passed = all(not any(r['mismatches'].values()) and not any(r['partial_mismatches'].values()) for r in rows)
    report = dict(source='offline_calculation_on_retained_oanda_history', status='passed' if passed else 'failed',
        exhaustive=args.stride == 1, pairs=rows)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(status=report['status'], pairs=[dict(pair=r['pair'], count=r['count'],
        windows=r['windows'], mismatches={role: len(v) for role, v in r['mismatches'].items()},
        partial_mismatches=r['partial_mismatches']) for r in rows])), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
