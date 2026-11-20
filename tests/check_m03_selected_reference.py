"""Compare the selected practice strategy with the Indicator Lab's saved result."""

from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor
from functools import cache
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
import math
from multiprocessing import get_context
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

from nnfx import assessment

from strategies import t3_bandpass_v1 as strategy
from strategies.t3_bandpass_v1 import atr


_LAB = Path(__file__).resolve().parents[2] / "nnfx-indicator-lab"
_DB = _LAB / "var/operating/nnfx.sqlite3"
_ARTIFACTS = _DB.parent / "artifacts"
_MANIFEST = Path(strategy.__file__).with_name("manifest.json")
_MODULES = {"c1": strategy.c1, "exit": strategy.exit}
_NAMES = {"c1": strategy.C1_OUTPUTS, "exit": strategy.EXIT_OUTPUTS}
_EVENTS = {1: "long", -1: "short", 0: "none", None: "unavailable"}


def _load_module(name, path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@cache
def saved_reference():
    manifest = json.loads(_MANIFEST.read_text())
    provenance = manifest["research_provenance"]
    with sqlite3.connect(_DB.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
        db.row_factory = sqlite3.Row

        def artifact(reference):
            row = db.execute("SELECT relative_path, sha256 FROM artifacts WHERE id=?",
                             (reference["id"],)).fetchone()
            path = _ARTIFACTS / row["relative_path"]
            assert sha256(path.read_bytes()).hexdigest() == row["sha256"] == reference["sha256"]
            return path

        result = json.loads(artifact(provenance["result_artifact"]).read_bytes())
        assert result["result_id"] == manifest["research_result_id"]
        plan = json.loads(artifact(result["plan"]).read_bytes())
        dataset, _, pairs = assessment.load_assessment_dataset(db, _ARTIFACTS, plan["dataset"]["id"])
        assert dataset.sha256 == plan["dataset"]["manifest_sha256"]
        assert [(p.dataset_member_id, p.artifact.sha256) for p in pairs] == [
            (p["member"]["id"], p["member"]["sha256"]) for p in plan["pair_members"]
        ]
        dependency = _LAB / provenance["pine_dependency"]["path"]
        assert sha256(dependency.read_bytes()).hexdigest() == provenance["pine_dependency"]["sha256"]
        _load_module("nnfx.pine_compat", dependency)
        modules = {role: _load_module(f"frozen_{role}", artifact(plan[role]["candidate"])) for role in _MODULES}
        frozen = {}
        for member in result["pairs"]:
            pair = json.loads(artifact(member["evidence"]).read_bytes())
            frozen[member["pair"]] = json.loads(artifact(pair["observations"]).read_bytes())
    return manifest, plan, pairs, modules, frozen


def _saved_values(values):
    return tuple(None if isinstance(value, float) and math.isnan(value) else value for value in values)


def _event_tuple(output, role, last=None):
    return tuple(output.series[name][last] for name in _NAMES[role])


class SelectedReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.plan, cls.pairs, cls.original, cls.saved = saved_reference()

    def _signals(self, role, output, candles):
        rule = self.manifest["signal_rules"][role]["definition"]
        bindings = self.plan[role]["outputs"]
        return assessment.interpret_signals(
            output, rule,
            {item["output_id"]: item["python_name"] for item in bindings},
            {item["output_id"]: item["value_kind"] for item in bindings},
            candles=candles,
        )

    def _compare_outputs(self, role, candles):
        parameters = self.manifest["parameters"][role]
        original = self.original[role].calculate(candles, **parameters)
        packaged = _MODULES[role].calculate(candles)
        self.assertEqual(original.timestamps, packaged.timestamps)
        self.assertEqual(original.series.keys(), packaged.series.keys())
        for name in original.series:
            self.assertEqual(_saved_values(original.series[name]), _saved_values(packaged.series[name]),
                             f"{role}.{name}")
        return original

    def test_a02_a03_all_archived_outputs_match_the_saved_assessment(self):
        for pair in self.pairs:
            with self.subTest(pair=pair.pair_code):
                candles = pair.candles
                saved = self.saved[pair.pair_code]
                for role in _MODULES:
                    original = self._compare_outputs(role, candles)
                    self.assertEqual({name: _saved_values(series) for name, series in original.series.items()},
                                     {name: tuple(series) for name, series in saved[role + "_outputs"].items()})
                    observations = self._signals(role, original, candles)
                    self.assertEqual(tuple(_EVENTS[o.direction] for o in observations),
                                     tuple(row[role + "_event"] for row in saved["candles"]))
                true_ranges, averages = atr.true_range_and_atr(candles)
                self.assertEqual((true_ranges, averages), assessment.true_range_and_atr(candles))
                self.assertEqual(true_ranges, tuple(row["true_range"] for row in saved["candles"]))
                self.assertEqual(averages, tuple(row["atr"] for row in saved["candles"]))

    def test_a02_a03_synthetic_partial_snapshots_match_original_on_identical_windows(self):
        count = strategy.LOOKBACK_CANDLES
        for pair in self.pairs:
            for end in range(600, len(pair.candles), 127):
                candle = pair.candles[end]
                for close in (candle.low, candle.high, (candle.open + candle.close) / 2):
                    with self.subTest(pair=pair.pair_code, end=end, close=close):
                        full = (*pair.candles[:end], replace(candle, close=close))
                        window = full[-count:]
                        for role, observe in (("c1", strategy.observe_c1), ("exit", strategy.observe_exit)):
                            identical = self._compare_outputs(role, window)
                            full_output = self.original[role].calculate(full, **self.manifest["parameters"][role])
                            self.assertEqual(_event_tuple(identical, role, slice(-2, None)),
                                             _event_tuple(full_output, role, slice(-2, None)))
                            event = observe(window)
                            direction = _EVENTS[self._signals(role, identical, window)[-1].direction]
                            self.assertEqual(event.direction, "no_event" if direction == "none" else direction)
                            self.assertEqual(event.rule_id, self.manifest["signal_rules"][role]["id"])
                            self.assertEqual(event.current, _event_tuple(identical, role, -1))
                            self.assertEqual(event.previous, _event_tuple(identical, role, -2))
                            self.assertIsNone(event.error)
                        with patch.object(assessment, "EVALUATION_END", len(full)):
                            _, averages = assessment.true_range_and_atr(full)
                        self.assertEqual(strategy.sizing_atr(window).value, averages[-1])

    def test_a03_385_bars_produce_a_different_prior_exit_event(self):
        candles = self.pairs[0].candles[:1649]
        self.assertEqual(self.pairs[0].pair_code, "EUR/USD")
        self.assertEqual(candles[-1].timestamp.isoformat(), "2019-05-14T21:00:00+00:00")
        count = strategy.LOOKBACK_CANDLES
        window = candles[-count:]
        self.assertEqual(strategy.observe_exit(window).previous, (False, False))
        short = self._compare_outputs("exit", window[1:])
        self.assertEqual(_event_tuple(short, "exit", -2), (False, True))
        with self.assertRaisesRegex(ValueError, "exact qualified candle count"):
            strategy.observe_exit(window[1:])

    def test_a03_rolling_atr_matches_every_qualified_archived_endpoint(self):
        for pair in self.pairs:
            _, reference = assessment.true_range_and_atr(pair.candles)
            for end in range(strategy.LOOKBACK_CANDLES - 1, len(pair.candles)):
                # Only these fourteen ranges can contribute. The fifteenth
                # candle supplies the prior close for their oldest range.
                _, rolling = atr.true_range_and_atr(pair.candles[end - 14:end + 1])
                self.assertEqual(rolling[-1], reference[end], (pair.pair_code, end))


def _scan_pair(pair_code):
    manifest, plan, pairs, original, saved = saved_reference()
    data = next(pair.candles for pair in pairs if pair.pair_code == pair_code)
    max_count = strategy.LOOKBACK_CANDLES
    first_end = plan["evaluation"]["start_index"]
    reference = saved[pair_code]
    results = {n: {"tested": 0, "c1_mismatches": 0, "exit_mismatches": 0} for n in range(15, max_count + 1)}
    for start in range(len(data) - 14):
        history = data[start:start + max_count]
        outputs = {role: original[role].calculate(history, **manifest["parameters"][role])
                   for role in _MODULES}
        # Accepted entry events are causal. One run per start also supplies the
        # current and previous events for every shorter prefix of that window.
        for end in range(max(first_end, start + 14), start + len(history)):
            count = end - start + 1
            stats = results[count]
            stats["tested"] += 1
            for role, names in _NAMES.items():
                expected = tuple(tuple(reference[role + "_outputs"][name][end-1:end+1]) for name in names)
                if _event_tuple(outputs[role], role, slice(count - 2, count)) != expected:
                    stats[role + "_mismatches"] += 1
                    stats.setdefault(role + "_witness_end", end)
    return pair_code, results


def sweep():
    """Verify every feasible archived endpoint for each count up to the binding."""
    _, _, pairs, _, _ = saved_reference()
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context("fork")) as pool:
        results = dict(pool.map(_scan_pair, (pair.pair_code for pair in pairs)))
    passing = [
        count for count in range(15, strategy.LOOKBACK_CANDLES + 1)
        if all(stats[count]["c1_mismatches"] == stats[count]["exit_mismatches"] == 0
               for stats in results.values())
    ]
    if passing != [strategy.LOOKBACK_CANDLES]:
        raise AssertionError(f"Passing counts differ from the sole qualified count: {passing}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--sweep"]:
        sweep()
    else:
        unittest.main()
