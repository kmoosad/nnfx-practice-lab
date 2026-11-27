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
from .test_m03 import daily_body
from .test_m03 import _CALL
from .test_m02 import reply
from .support import MANIFEST, ScriptedTransport
from nnfx_practice.candles import anchored_history, capture_daily_candles
from strategies import t3_bandpass_v1 as first, drm_adaptive_bandpass_v1 as second, eye_age_supertrend_v1 as third
from .m07_support import EVIDENCE, Service, World
from .support import NotebookCase
from .test_m10_integration import PermitCase
from nnfx_practice import qualification as q


class Python03Checks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.write_registry(strategy_b="drm_adaptive_bandpass_v1")
        path = self.root / "config.toml"
        path.write_text(path.read_text().replace('"fixture-v1"', '"t3_bandpass_v1"')
                        .replace('"Fixture A"', '"Python 01"').replace('"Fixture B"', '"Python 02"')
                        + '\n[[experiments]]\ncontroller_id="controller-c"\nnotebook_id="notebook-c"\nnotebook_name="Python 03"\nstrategy_version="eye_age_supertrend_v1"\nconnection_key="PRACTICE_C"\n')
        for version, module in (("t3_bandpass_v1", first), ("drm_adaptive_bandpass_v1", second), ("eye_age_supertrend_v1", third)):
            folder = self.root / "strategies" / version
            folder.mkdir()
            (folder / "manifest.json").write_bytes(Path(module.__file__).with_name("manifest.json").read_bytes())
        self.write_private(count=first.LOOKBACK_CANDLES)
        private = self.root / ".env"
        private.write_text(private.read_text().replace("PRACTICE_B_LOOKBACK_CANDLES=50",
                           f"PRACTICE_B_LOOKBACK_CANDLES={second.LOOKBACK_CANDLES}")
                           + f"\nPRACTICE_C_ACCOUNT_ID=fixture-account-c\nPRACTICE_C_TOKEN=fixture-token-c\nPRACTICE_C_HOME_CURRENCY=USD\nPRACTICE_C_LOOKBACK_CANDLES={third.LOOKBACK_CANDLES}\n")

    def test_exact_independent_selection_rejects_cross_binding_and_unknown_versions(self):
        a, b = self.binding(), self.binding("controller-c")
        self.assertIs(select_strategy(a), first)
        self.assertIs(select_strategy(b), third)
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
        folder = Path(third.__file__).parent
        manifest = json.loads((folder / "manifest.json").read_bytes())
        self.assertEqual(manifest["implementation_hashes"], {
            p.name: sha256(p.read_bytes()).hexdigest() for p in folder.glob("*.py")})
        self.assertEqual(manifest["qualification_report_sha256"], sha256((folder / "qualification.json").read_bytes()).hexdigest())
        report = json.loads((folder / "qualification.json").read_bytes())
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["exhaustive"])
        for role, module, names in (("c1", third.c1, third.C1_OUTPUTS), ("exit", third.exit, third.EXIT_OUTPUTS)):
            params = signature(module.calculate).parameters
            self.assertEqual(manifest["parameters"][role], {k: v.default for k, v in params.items() if k != "candles"})
            self.assertEqual(names, tuple(manifest["output_bindings"][role][d]["python_name"] for d in ("long", "short")))
        self.assertEqual(third.C1_OUTPUTS, ("confluence_buy", "confluence_sell"))
        self.assertEqual(third.EXIT_OUTPUTS, ("buySignal", "sellSignal"))

    def prepare(self):
        self.prior_bytes = {}
        for controller in ('controller-a', 'controller-b'):
            bound = self.binding(controller)
            with open_notebook(self.root, bound, create=True):
                pass
            path = bound.experiment.notebook_path(self.root)
            self.prior_bytes[path] = path.read_bytes()
        self.bound = self.binding("controller-c")
        self.world = World(self)
        self.world.candle_count = dict.fromkeys(PERMITTED_PAIRS, third.LOOKBACK_CANDLES)
        self.run_id = "python03-1"
        self.broker = PracticeBroker(self.bound, transport=self.world, now=self.clock.now)
        initialize_qualification(self.root, "controller-c", self.broker, service=Service(), evidence=EVIDENCE)
        self.db = self.enterContext(open_notebook(self.root, self.bound))

    def master(self):
        # The shared broker fixture's transaction factory defaults to account A.
        # Its generated transactions must identify this independent account C.
        with patch("tests.test_m02.ACCOUNT", self.bound.connection.account_id):
            return run_master(self.root, "controller-c", self.broker, mode="qualification", evidence=EVIDENCE,
                              run_id=self.run_id, config_hash="c" * 64, code_hash="d" * 64, elapsed=self.clock.monotonic)

    def test_fresh_events_exit_direction_and_exact_history_window(self):
        start = third.HISTORY_START - timedelta(days=1000)
        candles = tuple(Candle(start + timedelta(days=i), 1.0, 1.0, 1.0, 1.0, None)
                        for i in range(third.LOOKBACK_CANDLES))
        stamps = tuple(c.timestamp for c in third.history_candles(candles))
        no = (False,) * len(stamps)
        c1 = third.IndicatorOutput(stamps, {"confluence_buy": no, "confluence_sell": no, "tDir": (1,) * len(stamps), "turnUp": (*no[:-1], True)})
        exits = third.IndicatorOutput(stamps, {"buySignal": (*no[:-1], True), "sellSignal": no})
        with patch.object(third.c1, "calculate", return_value=c1), patch.object(third.exit, "calculate", return_value=exits):
            self.assertEqual(third.observe_c1(candles).direction, "no_event")
            event = third.observe_exit(candles)
            self.assertEqual(exit_reasons("short", c1="no_event", exit_signal=event.direction), ("exit",))
            self.assertEqual(exit_reasons("long", c1="no_event", exit_signal=event.direction), ())
        for long_event, short_event, expected in ((True, False, 'long'), (False, True, 'short'), (True, True, 'unavailable')):
            output = third.IndicatorOutput(stamps, {'confluence_buy': (*no[:-1], long_event),
                                                    'confluence_sell': (*no[:-1], short_event)})
            with patch.object(third.c1, 'calculate', return_value=output):
                self.assertEqual(third.observe_c1(candles).direction, expected)
        for calculate in (third.observe_c1, third.observe_exit, third.sizing_atr):
            with self.assertRaisesRegex(ValueError, "exact qualified candle count"):
                calculate(candles[1:])

    def test_real_calculation_and_dashboard_keep_three_notebooks_separate(self):
        self.prepare()
        self.master()
        row = self.db.execute("SELECT status,lookback_candles FROM runs").fetchone()
        self.assertEqual(tuple(row), ("completed", third.LOOKBACK_CANDLES))
        self.assertEqual(self.db.execute("SELECT count(*) FROM pair_decisions").fetchone()[0], 28)
        self.assertTrue(all(call.method == "GET" for call in self.world.calls))
        self.assertTrue(all(self.bound.connection.account_id in call.path for call in self.world.calls))
        self.assertTrue(all(path.read_bytes() == raw for path, raw in self.prior_bytes.items()))

        client = create_app(self.root).test_client()
        for url in ("/controllers", "/notebooks"):
            page = client.get(url)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b"Python 01", page.data)
            self.assertIn(b"Python 02", page.data)
            self.assertIn(b"Python 03", page.data)
        page = client.get("/notebooks/notebook-c")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Eye Trend Zones", page.data)

    def test_missing_origin_blocks_calculation_and_orders_even_with_exact_capture_count(self):
        self.prepare()
        def missing_origin(call):
            if '/candles?' not in call.path:
                return None
            body = daily_body(self.clock.now().date(), count=third.LOOKBACK_CANDLES + 1)
            body['instrument'] = call.path.split('/instruments/')[1].split('/')[0]
            body['candles'] = [row for row in body['candles']
                               if datetime.fromisoformat(row['time']) != third.HISTORY_START]
            self.assertEqual(len(body['candles']), third.LOOKBACK_CANDLES)
            return reply(body)
        self.world.on_call = missing_origin
        with patch.object(third, 'observe_c1', side_effect=AssertionError('History was not validated')):
            self.master()
        self.assertTrue(all(call.method == 'GET' for call in self.world.calls))
        captures = [json.loads(row[0]) for row in self.db.execute('SELECT capture_json FROM pair_decisions')]
        self.assertEqual(len(captures), 28)
        self.assertTrue(all(row['reason'] == 'Required indicator history start candle is unavailable' for row in captures))
        self.assertTrue(all(path.read_bytes() == raw for path, raw in self.prior_bytes.items()))

    def test_new_strategy_enters_two_legs_then_closes_on_its_opposite_exit(self):
        self.prepare()
        def c1(candles):
            self.assertEqual(len(candles), third.LOOKBACK_CANDLES)
            direction = "long" if self.world.capture == ("EUR-USD", "new") else "no_event"
            return third.EventObservation(direction, third.C1_RULE_ID, third.C1_OUTPUTS)
        with (patch.object(third, "observe_c1", side_effect=c1),
              patch.object(third, "sizing_atr", return_value=third.AtrObservation(0.001)),
              patch.object(first, "observe_c1", side_effect=AssertionError("Wrong strategy"))):
            self.master()
        self.assertEqual(len(self.world.trades), 2)
        self.run_id = "python03-2"
        self.clock.advance(86400)
        with (patch.object(third, "observe_c1", return_value=third.EventObservation("no_event", third.C1_RULE_ID, third.C1_OUTPUTS)),
              patch.object(third, "observe_exit", return_value=third.EventObservation("short", third.EXIT_RULE_ID, third.EXIT_OUTPUTS)),
              patch.object(first, "observe_exit", side_effect=AssertionError("Wrong exit"))):
            self.master()
        self.assertEqual(len(self.world.trades), 0)
        self.assertEqual(sum(c.method == "POST" for c in self.world.calls), 2)
        self.assertEqual(sum(c.path.endswith("/close") for c in self.world.calls), 2)
        decision = self.db.execute("SELECT exit_json FROM pair_decisions WHERE stage='manage_open'").fetchone()
        self.assertEqual(json.loads(decision[0])["rule_id"], third.EXIT_RULE_ID)
        self.assertTrue(all(path.read_bytes() == raw for path, raw in self.prior_bytes.items()))


class AnchoredCaptureChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.body = daily_body(self.clock.now().date(), count=51)
        self.body['candles'] = self.body['candles'][2:]
        self.origin = datetime.fromisoformat(self.body['candles'][3]['time'])
        self.weekend = dict(time='2026-11-13T22:00:00.000000000Z', complete=True, volume=1,
                            mid=dict(o='9.0', h='10.0', l='8.0', c='9.5'))
        self.body['candles'].insert(-1, self.weekend)
        self.body['candles'].sort(key=lambda r: r['time'])
        self.assertEqual(len(self.body['candles']), 50)
        self.write_manifest({**MANIFEST, 'history_initialization': dict(mode='anchored',
            start=self.origin.isoformat(), calendar='new_york_weekdays')})

    def capture(self):
        broker = PracticeBroker(self.binding(), transport=ScriptedTransport((_CALL, reply(self.body))), now=self.clock.now)
        return capture_daily_candles(broker, 'EUR-USD', session_date=self.clock.now().date())

    def test_historical_weekend_is_reported_and_excluded_only_for_anchored_history(self):
        result = self.capture()
        self.assertEqual(result.metadata['validation'], 'valid')
        self.assertEqual(result.metadata['excluded_non_session_candles'], 1)
        selected = anchored_history(result.candles, self.origin)
        self.assertEqual(selected[0].timestamp, self.origin)
        self.assertEqual(selected[-1], result.candles[-1])
        self.assertNotIn(datetime.fromisoformat(self.weekend['time']), [c.timestamp for c in selected])
        self.assertEqual(result.metadata['indicator_candle_count'], len(selected))
        self.write_manifest(MANIFEST)
        self.assertEqual(self.capture().metadata['validation'], 'unavailable')

    def test_excluded_rows_still_require_valid_prices_and_current_candle_stays_strict(self):
        self.weekend['mid']['h'] = '0.0'
        self.assertEqual(self.capture().metadata['validation'], 'unavailable')
        self.weekend['mid']['h'] = '10.0'
        self.body['candles'][-1]['time'] = '2026-11-14T22:00:00.000000000Z'
        self.assertEqual(self.capture().metadata['validation'], 'unavailable')


class Python03PermitChecks(PermitCase):
    def setUp(self):
        super().setUp()
        manifest = json.loads(Path(third.__file__).with_name("manifest.json").read_bytes())
        digest = sha256(q.canonical_json(manifest).encode()).hexdigest()
        self.plan["manifest_sha256"] = digest
        self.documents["candle_preflight"].update(manifest_sha256=digest, lookback_candles=third.LOOKBACK_CANDLES)
        self.documents["private_connection"]["binding"]["manifest_sha256"] = digest
        self.documents["execution_authority"].update(account_label="Python 03", manifest_sha256=digest,
                                                     strategy_version="eye_age_supertrend_v1")
        self.plan["evidence"]["strategy_qualification"]["sha256"] = manifest["qualification_report_sha256"]

    def test_new_strategy_evidence_uses_its_own_window_and_authority(self):
        q.validate_evidence(self.plan, self.documents)

    def test_python01_evidence_cannot_qualify_python03(self):
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
