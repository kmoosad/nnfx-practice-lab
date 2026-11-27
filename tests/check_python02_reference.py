"""Offline comparison with Python 02's immutable Indicator Lab result.

Run with an explicit --lab checkout and USB --output directory. The lab is
read-only; it is not a runtime dependency of the practice application.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import math
from pathlib import Path
import sqlite3
import sys

from strategies import drm_adaptive_bandpass_v1 as strategy


RESULT = "6e00cc56-d19a-43b1-a6e1-528eb075dc9e"
NAMES = {"c1": strategy.C1_OUTPUTS, "exit": strategy.EXIT_OUTPUTS}


def reference(lab):
    sys.path.insert(0, str(lab))
    from nnfx import assessment
    root = lab / "var/operating"
    with sqlite3.connect((root / "nnfx.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        def artifact(ref):
            ident = ref if isinstance(ref, str) else ref["id"]
            path, digest = db.execute("SELECT relative_path, sha256 FROM artifacts WHERE id=?", (ident,)).fetchone()
            raw = (root / "artifacts" / path).read_bytes()
            assert sha256(raw).hexdigest() == digest
            if isinstance(ref, dict):
                assert digest == ref["sha256"]
            return raw

        result = json.loads(artifact(RESULT))
        plan = json.loads(artifact(result["plan"]))
        _, _, pairs = assessment.load_assessment_dataset(db, root / "artifacts", plan["dataset"]["id"])
        spec = spec_from_file_location("nnfx.pine_compat", lab / "inputs/dependencies/pine_compat_v1.py")
        dependency = module_from_spec(spec)
        sys.modules[spec.name] = dependency
        spec.loader.exec_module(dependency)
        modules = {}
        for role in NAMES:
            raw = artifact(plan[role]["candidate"])
            module = type(sys)("reference_" + role)
            exec(compile(raw, "saved_" + role, "exec"), module.__dict__)
            modules[role] = module
        saved = {item["pair"]: json.loads(artifact(json.loads(artifact(item["evidence"]))["observations"]))
                 for item in result["pairs"]}
    return assessment, plan, pairs, modules, saved


def values(sequence):
    return tuple(None if isinstance(x, float) and math.isnan(x) else x for x in sequence)


def check_pair(args):
    lab, pair_code, count, stride = args
    assessment, plan, pairs, original, saved = reference(lab)
    candles = next(p.candles for p in pairs if p.pair_code == pair_code)
    saved = saved[pair_code]
    packaged = {"c1": strategy.c1, "exit": strategy.exit}
    for role in NAMES:
        raw = original[role].calculate(candles)
        output = packaged[role].calculate(candles)
        assert raw.timestamps == output.timestamps
        assert {key: values(seq) for key, seq in raw.series.items()} == {
            key: values(seq) for key, seq in output.series.items()}
        assert {key: values(seq) for key, seq in output.series.items()} == {
            key: tuple(seq) for key, seq in saved[role + "_outputs"].items()}
    ranges, atr = strategy.atr.true_range_and_atr(candles)
    assert (ranges, atr) == assessment.true_range_and_atr(candles)
    assert ranges == tuple(row["true_range"] for row in saved["candles"])
    assert atr == tuple(row["atr"] for row in saved["candles"])
    mismatches = {role: [] for role in NAMES}
    checked = 0
    for end in range(max(count - 1, plan["evaluation"]["start_index"]), len(candles), stride):
        window = candles[end - count + 1:end + 1]
        for role in NAMES:
            output = packaged[role].calculate(window)
            if any(values(output.series[name][-2:]) != tuple(saved[role + "_outputs"][name][end - 1:end + 1])
                   for name in NAMES[role]):
                mismatches[role].append(end)
        checked += 1
    partial_checks = 0
    partial_mismatches = {role: [] for role in NAMES}
    for end in range(max(count - 1, 600), len(candles), 127):
        candle = candles[end]
        for close in (candle.low, candle.high, (candle.open + candle.close) / 2):
            full = (*candles[:end], replace(candle, close=close))
            for role in NAMES:
                output = packaged[role].calculate(full[-count:])
                raw = original[role].calculate(full)
                if any(values(output.series[name][-2:]) != values(raw.series[name][-2:]) for name in NAMES[role]):
                    partial_mismatches[role].append(end)
            partial_checks += 1
    return dict(pair=pair_code, count=count, stride=stride, archived_outputs="exact",
                archived_atr="exact", windows=checked, mismatches=mismatches,
                partial_snapshots=partial_checks, partial_mismatches=partial_mismatches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--stride", type=int, default=1)
    args = parser.parse_args()
    jobs = [(args.lab, pair, args.count, args.stride) for pair in ("EUR/USD", "EUR/GBP", "AUD/NZD", "CHF/JPY")]
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(check_pair, jobs))
    passed = all(not any(r["mismatches"].values()) and not any(r["partial_mismatches"].values()) for r in rows)
    report = dict(source="offline_lab_reference", result_id="a83ffe21-90eb-4674-99e3-7c80d6871a6c",
                  status="passed" if passed else "failed", exhaustive=args.stride == 1, pairs=rows)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
