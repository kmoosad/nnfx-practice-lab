"""Explicit offline probes of the original lab on generic synthetic inputs."""

from datetime import UTC, datetime, timedelta
import math
import unittest
from unittest.mock import patch

from nnfx import assessment
from nnfx.comparisons import compare_signal_numbers
from nnfx.interface import Candle, IndicatorOutput

from nnfx_practice.signal_actions import entry_signal, exit_reasons


_START = datetime(2020, 1, 1, tzinfo=UTC)
_LEVEL = {"form": "numeric_level_crossing", "output_id": "series", "level": 0,
          "long_orientation": "above"}
_DIRECTION = {-1: "short", 0: "no_event", 1: "long", None: "unavailable"}


def timestamps(count):
    return tuple(_START + timedelta(days=index) for index in range(count))


def level_output(values):
    return IndicatorOutput(timestamps(len(values)), {"series": values})


def directions(output, rule, kinds=None, *, candles=()):
    names = {name: name for name in output.series}
    if kinds is None:
        kinds = dict.fromkeys(names, "numeric")
    observations = assessment.interpret_signals(output, rule, names, kinds, candles=candles)
    return tuple(observation.direction for observation in observations)


class LabReferences(unittest.TestCase):
    def test_a02_level_crossing_uses_equality_and_resets_on_missing_operand(self):
        nan = float("nan")
        output = level_output((nan, -1, 4e-10, 5e-10, 1, nan, -1, -1, 0, -1))
        self.assertEqual(directions(output, _LEVEL), (None, 0, 0, 1, 0, None, 0, 0, 0, -1))
        self.assertEqual(compare_signal_numbers(4e-10, 0), 0)
        self.assertEqual(compare_signal_numbers(5e-10, 0), 1)
        self.assertEqual(compare_signal_numbers(-5e-10, 0), -1)

    def test_a02_two_series_and_close_cross_only_on_fresh_changes(self):
        nan = float("nan")
        close = (1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 0.5)
        times = timestamps(len(close))
        line = (1.5, 1.0, 1.0, 1.0, nan, 1.0, 1.0)
        series = IndicatorOutput(times, {"close": close, "line": line})
        two_series = {"form": "two_series_crossing", "first_output_id": "close",
                      "second_output_id": "line", "long_orientation": "first_above_second"}
        self.assertEqual(directions(series, two_series), (0, 0, 1, 0, None, 0, -1))
        candles = tuple(Candle(time, price, price, price, price) for time, price in zip(times, close))
        candle_close = {"form": "candle_close_crossing", "output_id": "line", "long_orientation": "below"}
        self.assertEqual(directions(series, candle_close, candles=candles), (0, 0, -1, 0, None, 0, 1))

    def test_a02_state_transition_rejects_carried_state_and_resets_on_missing(self):
        output = level_output(("down", "up", "up", None, "down", "down", "up", "down"))
        rule = {"form": "state_transition", "output_id": "series",
                "permitted_state_values": ["down", "up"], "long_previous": "down",
                "long_current": "up", "short_previous": "up", "short_current": "down"}
        self.assertEqual(directions(output, rule, {"series": "categorical"}), (0, 1, 0, None, 0, 0, 1, -1))

    def test_a02_paired_events_reject_simultaneous_signals(self):
        rule = {"form": "paired_directional_events", "long_output_id": "up", "short_output_id": "down"}
        kinds = {"up": "boolean", "down": "integer"}
        output = IndicatorOutput(timestamps(4), {"up": (False, True, None, False), "down": (0, 0, 1, 1)})
        self.assertEqual(directions(output, rule, kinds), (0, 1, None, -1))
        simultaneous = IndicatorOutput(timestamps(1), {"up": (True,), "down": (1,)})
        with self.assertRaises(assessment.AssessmentFailed) as error:
            directions(simultaneous, rule, kinds)
        self.assertEqual(str(error.exception.__cause__), "simultaneous_directional_events")

    def test_a03_initialization_requires_current_and_previous_rule_operands(self):
        nan = float("nan")
        ready = level_output((nan, nan, -1.0, 1.0))
        shorter = level_output((nan, nan, 1.0))
        missing_current = level_output((nan, nan, -1.0, nan))
        names, kinds = {"series": "series"}, {"series": "numeric"}
        with patch.object(assessment, "EVALUATION_START", 3):
            assessment.require_boundary_readiness(ready, _LEVEL, names, kinds)
            with self.assertRaises(assessment.AssessmentFailed):
                assessment.require_boundary_readiness(missing_current, _LEVEL, names, kinds)
        with patch.object(assessment, "EVALUATION_START", 2):
            with self.assertRaises(assessment.AssessmentFailed):
                assessment.require_boundary_readiness(shorter, _LEVEL, names, kinds)
        self.assertEqual(directions(ready, _LEVEL)[-1], 1)
        self.assertEqual(directions(shorter, _LEVEL)[-1], 0)

    def test_a03_true_range_keeps_the_first_full_precision_winner_on_a_tie(self):
        first, second = timestamps(2)
        target = Candle(second, 1.5, 2.0, 1.0, 1.5)
        for offset in (2e-10, 6e-10):
            price = 1.0 - offset
            previous = Candle(first, price, price, price, price)
            with self.subTest(offset=offset), patch.object(assessment, "EVALUATION_END", 2):
                ranges, atr = assessment.true_range_and_atr((previous, target))
                gap = target.high - previous.close
                self.assertGreater(gap, 1.0)
                self.assertEqual(ranges[-1], 1.0 if offset == 2e-10 else gap)
                self.assertEqual(atr, (None, None))

    def test_a03_a_gap_needs_the_previous_close_before_the_fourteen_ranges(self):
        count = assessment.EVALUATION_END
        prices = (1.0,) * (count - 14) + (4.0,) * 14
        candles = tuple(Candle(time, price, price, price, price)
                        for time, price in zip(timestamps(count), prices, strict=True))
        full_ranges, full_atr = assessment.true_range_and_atr(candles)
        self.assertEqual(full_ranges[-14:], (3.0,) + (0.0,) * 13)
        self.assertEqual(full_atr[-1], math.fsum(full_ranges[-14:]) / 14)
        for size, expected in ((13, None), (14, 0.0), (15, full_atr[-1])):
            # Change only the lab's fixed research-length guard for this probe.
            with self.subTest(size=size), patch.object(assessment, "EVALUATION_END", size):
                _, atr = assessment.true_range_and_atr(candles[-size:])
                self.assertEqual(atr[-1], expected)

    def test_a03_reference_exit_event_stays_actionable_with_zero_atr(self):
        output = level_output((1.0, -1.0))
        event = _DIRECTION[directions(output, _LEVEL)[-1]]
        candles = tuple(Candle(time, 1.0, 1.0, 1.0, 1.0) for time in timestamps(15))
        with patch.object(assessment, "EVALUATION_END", 15):
            _, atr = assessment.true_range_and_atr(candles)
        self.assertEqual(event, "short")
        self.assertEqual(atr[-1], 0.0)
        self.assertIsNone(entry_signal(event, atr[-1]))
        self.assertEqual(exit_reasons("long", c1="unavailable", exit_signal=event), ("exit",))
