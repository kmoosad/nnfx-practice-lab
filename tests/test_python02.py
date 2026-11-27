"""Independent strategy/account routing; all broker execution is offline."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from inspect import signature
import json
from pathlib import Path
from unittest.mock import patch

from nnfx_practice.broker import PracticeBroker
from nnfx_practice.candles import Candle
from nnfx_practice.config import ConfigurationError, PERMITTED_PAIRS
from nnfx_practice.dashboard import create_app
from nnfx_practice.lifecycle import initialize_qualification
from nnfx_practice.master import run_master
from nnfx_practice.notebook import open_notebook
from nnfx_practice.strategy import select_strategy, manifest_for_hash
from nnfx_practice.signal_actions import exit_reasons
from strategies import t3_bandpass_v1 as first, drm_adaptive_bandpass_v1 as second
from .m07_support import EVIDENCE, Service, World
from .support import NotebookCase
from .test_m10_integration import PermitCase
from nnfx_practice import qualification as q


class Python02Checks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.write_registry(strategy_b="drm_adaptive_bandpass_v1")
        path = self.root / "config.toml"
        path.write_text(path.read_text().replace('"fixture-v1"', '"t3_bandpass_v1"')
                        .replace('"Fixture A"', '"Python 01"').replace('"Fixture B"', '"Python 02"'))
        for version, module in (("t3_bandpass_v1", first), ("drm_adaptive_bandpass_v1", second)):
            folder = self.root / "strategies" / version
            folder.mkdir()
            (folder / "manifest.json").write_bytes(Path(module.__file__).with_name("manifest.json").read_bytes())
        self.write_private(count=first.LOOKBACK_CANDLES)
        private = self.root / ".env"
        private.write_text(private.read_text().replace("PRACTICE_B_LOOKBACK_CANDLES=50",
                                                      f"PRACTICE_B_LOOKBACK_CANDLES={second.LOOKBACK_CANDLES}"))

    def test_exact_independent_selection_rejects_cross_binding_and_unknown_versions(self):
        a, b = self.binding(), self.binding("controller-b")
        self.assertIs(select_strategy(a), first)
        self.assertIs(select_strategy(b), second)
        self.assertNotEqual(a.connection.account_id, b.connection.account_id)
        self.assertNotEqual(a.experiment.notebook_path(self.root), b.experiment.notebook_path(self.root))
        for bad in (replace(b, manifest=a.manifest),
                    replace(b, connection=replace(b.connection, lookback_candles=386)),
                    replace(b, experiment=replace(b.experiment, strategy_version="unknown"))):
            with self.assertRaises(ConfigurationError):
                select_strategy(bad)
        self.assertEqual(manifest_for_hash(b.manifest.hash)["strategy_version"], b.experiment.strategy_version)
        with self.assertRaises(ConfigurationError):
            manifest_for_hash("a" * 64)

    def test_manifest_pins_outputs_parameters_and_each_packaged_implementation(self):
        folder = Path(second.__file__).parent
        manifest = json.loads((folder / "manifest.json").read_bytes())
        self.assertEqual(manifest["implementation_hashes"], {
            p.name: sha256(p.read_bytes()).hexdigest() for p in folder.glob("*.py")})
        self.assertEqual(manifest["qualification_report_sha256"], sha256((folder / "qualification.json").read_bytes()).hexdigest())
        report = json.loads((folder / "qualification.json").read_bytes())
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["exhaustive"])
        for role, module, names in (("c1", second.c1, second.C1_OUTPUTS), ("exit", second.exit, second.EXIT_OUTPUTS)):
            params = signature(module.calculate).parameters
            self.assertEqual(manifest["parameters"][role], {k: v.default for k, v in params.items() if k != "candles"})
            self.assertEqual(names, tuple(manifest["output_bindings"][role][d]["python_name"] for d in ("long", "short")))
        self.assertEqual(second.C1_OUTPUTS, ("BullishFlip", "BearishFlip"))
        self.assertEqual(second.EXIT_OUTPUTS, ("doLongExit", "doShortExit"))

    def prepare(self):
        a = self.binding()
        with open_notebook(self.root, a, create=True):
            pass
        self.first_bytes = a.experiment.notebook_path(self.root).read_bytes()
        self.bound = self.binding("controller-b")
        self.world = World(self)
        self.world.candle_count = dict.fromkeys(PERMITTED_PAIRS, second.LOOKBACK_CANDLES)
        self.run_id = "python02-1"
        self.broker = PracticeBroker(self.bound, transport=self.world, now=self.clock.now)
        initialize_qualification(self.root, "controller-b", self.broker, service=Service(), evidence=EVIDENCE)
        self.db = self.enterContext(open_notebook(self.root, self.bound))

    def master(self):
        # The shared broker fixture's transaction factory defaults to account A.
        # Its generated transactions must identify this independent account B.
        with patch("tests.test_m02.ACCOUNT", self.bound.connection.account_id):
            return run_master(self.root, "controller-b", self.broker, mode="qualification", evidence=EVIDENCE,
                              run_id=self.run_id, config_hash="c" * 64, code_hash="d" * 64, elapsed=self.clock.monotonic)

    def test_fresh_events_exit_direction_and_exact_history_window(self):
        start = datetime(2026, 1, 1, tzinfo=UTC)
        candles = tuple(Candle(start + timedelta(days=i), 1.0, 1.0, 1.0, 1.0, None)
                        for i in range(second.LOOKBACK_CANDLES))
        stamps = tuple(c.timestamp for c in candles)
        no = (False,) * len(candles)
        c1 = second.IndicatorOutput(stamps, {"BullishFlip": no, "BearishFlip": no, "NAL": (1,) * len(candles)})
        exits = second.IndicatorOutput(stamps, {"doLongExit": (*no[:-1], True), "doShortExit": no})
        with patch.object(second.c1, "calculate", return_value=c1), patch.object(second.exit, "calculate", return_value=exits):
            self.assertEqual(second.observe_c1(candles).direction, "no_event")
            event = second.observe_exit(candles)
            self.assertEqual(exit_reasons("short", c1="no_event", exit_signal=event.direction), ("exit",))
            self.assertEqual(exit_reasons("long", c1="no_event", exit_signal=event.direction), ())
        for calculate in (second.observe_c1, second.observe_exit, second.sizing_atr):
            with self.assertRaisesRegex(ValueError, "exact qualified candle count"):
                calculate(candles[1:])

    def test_real_calculation_and_dashboard_keep_both_notebooks_separate(self):
        self.prepare()
        self.master()
        row = self.db.execute("SELECT status,lookback_candles FROM runs").fetchone()
        self.assertEqual(tuple(row), ("completed", second.LOOKBACK_CANDLES))
        self.assertEqual(self.db.execute("SELECT count(*) FROM pair_decisions").fetchone()[0], 28)
        self.assertTrue(all(call.method == "GET" for call in self.world.calls))
        self.assertTrue(all(self.bound.connection.account_id in call.path for call in self.world.calls))
        self.assertEqual(self.binding().experiment.notebook_path(self.root).read_bytes(), self.first_bytes)

        client = create_app(self.root).test_client()
        for url in ("/controllers", "/notebooks"):
            page = client.get(url)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Python 01", page.data)
            self.assertIn(b"Python 02", page.data)
        page = client.get("/notebooks/notebook-b")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Distributional Rank Momentum", page.data)

    def test_new_strategy_enters_two_legs_then_closes_on_its_opposite_exit(self):
        self.prepare()
        def c1(candles):
            self.assertEqual(len(candles), second.LOOKBACK_CANDLES)
            direction = "long" if self.world.capture == ("EUR-USD", "new") else "no_event"
            return second.EventObservation(direction, second.C1_RULE_ID, second.C1_OUTPUTS)
        with (patch.object(second, "observe_c1", side_effect=c1),
              patch.object(second, "sizing_atr", return_value=second.AtrObservation(0.001)),
              patch.object(first, "observe_c1", side_effect=AssertionError("Wrong strategy"))):
            self.master()
        self.assertEqual(len(self.world.trades), 2)
        self.run_id = "python02-2"
        self.clock.advance(86400)
        with (patch.object(second, "observe_c1", return_value=second.EventObservation("no_event", second.C1_RULE_ID, second.C1_OUTPUTS)),
              patch.object(second, "observe_exit", return_value=second.EventObservation("short", second.EXIT_RULE_ID, second.EXIT_OUTPUTS)),
              patch.object(first, "observe_exit", side_effect=AssertionError("Wrong exit"))):
            self.master()
        self.assertEqual(len(self.world.trades), 0)
        self.assertEqual(sum(c.method == "POST" for c in self.world.calls), 2)
        self.assertEqual(sum(c.path.endswith("/close") for c in self.world.calls), 2)
        decision = self.db.execute("SELECT exit_json FROM pair_decisions WHERE stage='manage_open'").fetchone()
        self.assertEqual(json.loads(decision[0])["rule_id"], second.EXIT_RULE_ID)
        self.assertEqual(self.binding().experiment.notebook_path(self.root).read_bytes(), self.first_bytes)


class Python02PermitChecks(PermitCase):
    def setUp(self):
        super().setUp()
        manifest = json.loads(Path(second.__file__).with_name("manifest.json").read_bytes())
        digest = sha256(q.canonical_json(manifest).encode()).hexdigest()
        self.plan["manifest_sha256"] = digest
        self.documents["candle_preflight"].update(manifest_sha256=digest, lookback_candles=second.LOOKBACK_CANDLES)
        self.documents["private_connection"]["binding"]["manifest_sha256"] = digest
        self.documents["execution_authority"].update(account_label="Python 02", manifest_sha256=digest,
                                                     strategy_version="drm_adaptive_bandpass_v1")
        self.plan["evidence"]["strategy_qualification"]["sha256"] = manifest["qualification_report_sha256"]

    def test_new_strategy_evidence_uses_its_own_window_and_authority(self):
        q.validate_evidence(self.plan, self.documents)

    def test_python01_evidence_cannot_qualify_python02(self):
        for document, field, wrong in (
            ("candle_preflight", "lookback_candles", 386),
            ("execution_authority", "strategy_version", "t3_bandpass_v1"),
            ("execution_authority", "account_binding_sha256", "f" * 64),
            ("execution_authority", "controller_id", "different-controller"),
            ("execution_authority", "notebook_id", "different-notebook"),
        ):
            with self.subTest(document=document, field=field):
                old = self.documents[document][field]
                self.documents[document][field] = wrong
                with self.assertRaises(ConfigurationError):
                    q.validate_evidence(self.plan, self.documents)
                self.documents[document][field] = old
