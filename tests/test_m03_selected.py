"""Offline checks for the selected strategy's packaged calculation boundary."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from inspect import signature
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from nnfx_practice.candles import Candle
from nnfx_practice.signal_actions import entry_signal, exit_reasons
from strategies import t3_bandpass_v1 as selected
from strategies.t3_bandpass_v1.interface import IndicatorOutput


class SelectedStrategyTests(unittest.TestCase):
    def setUp(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        self.candles = tuple(
            Candle(start + timedelta(days=bar), 1.0, 1.0, 1.0, 1.0, None)
            for bar in range(selected.LOOKBACK_CANDLES)
        )

    def test_manifest_binds_the_qualified_count_defaults_outputs_and_code(self):
        folder = Path(selected.__file__).parent
        manifest = json.loads((folder / "manifest.json").read_bytes())
        self.assertEqual(manifest["qualified_total_candle_count"], selected.LOOKBACK_CANDLES)
        self.assertEqual(manifest["qualification_report_sha256"],
                         sha256((folder / "qualification.json").read_bytes()).hexdigest())
        self.assertEqual(manifest["implementation_hashes"], {
            file.name: sha256(file.read_bytes()).hexdigest() for file in folder.glob("*.py")
        })
        for role, implementation, event_names, rule_id in (
            ("c1", selected.c1, selected.C1_OUTPUTS, selected.C1_RULE_ID),
            ("exit", selected.exit, selected.EXIT_OUTPUTS, selected.EXIT_RULE_ID),
        ):
            params = signature(implementation.calculate).parameters
            self.assertEqual({key: params[key].default for key in params if key != "candles"},
                             manifest["parameters"][role])
            self.assertEqual(manifest["signal_rules"][role]["id"], rule_id)
            self.assertEqual(event_names, tuple(manifest["output_bindings"][role][direction]["python_name"]
                                                for direction in ("long", "short")))

    def test_short_windows_fail_each_calculation_boundary(self):
        for compute in (selected.observe_c1, selected.observe_exit, selected.sizing_atr):
            with self.subTest(compute=compute.__name__):
                with self.assertRaisesRegex(ValueError, "exact qualified candle count"):
                    compute(self.candles[1:])

    def test_unavailable_or_conflicting_events_and_zero_atr_keep_exit_independent(self):
        timestamps = tuple(candle.timestamp for candle in self.candles)
        no = (False,) * (len(timestamps) - 1)
        conflict = IndicatorOutput(timestamps, {"goLong": (*no, True), "goShort": (*no, True)})
        opposite = IndicatorOutput(timestamps, {"longEntry": (*no, False), "shortEntry": (*no, True)})
        with (patch.object(selected.c1, "calculate", return_value=conflict),
              patch.object(selected.exit, "calculate", return_value=opposite)):
            c1 = selected.observe_c1(self.candles)
            exit_signal = selected.observe_exit(self.candles)
        atr = selected.sizing_atr(self.candles)
        self.assertEqual((c1.direction, c1.error), ("unavailable", "simultaneous_directional_events"))
        self.assertEqual(c1.current, (True, True))
        self.assertEqual((exit_signal.direction, exit_signal.error), ("short", None))
        self.assertEqual((atr.value, atr.error), (0.0, None))
        self.assertIsNone(entry_signal(c1.direction, atr.value))
        self.assertEqual(exit_reasons("long", c1=c1.direction, exit_signal=exit_signal.direction), ("exit",))
