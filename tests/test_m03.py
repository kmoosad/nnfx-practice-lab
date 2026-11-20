"""Offline M03 candle and decision checks using the bound M01 fixture."""

from copy import deepcopy
from datetime import UTC, date, datetime, time, timedelta
import json
from zoneinfo import ZoneInfo

from nnfx_practice.broker import HTTPReply, PracticeBroker
from nnfx_practice.candles import capture_pair_candles
from nnfx_practice.config import ConfigurationError
from nnfx_practice.notebook import transaction
from nnfx_practice.signal_actions import entry_signal, exit_reasons
from tests.support import ACCOUNT, TOKEN, Call, NotebookCase, ScriptedTransport


_PATH = (f"/v3/accounts/{ACCOUNT}/instruments/EUR_USD/candles?price=M&granularity=D"
         "&count=50&smooth=false&dailyAlignment=17&alignmentTimezone=America%2FNew_York")
_CALL = Call("GET", _PATH)


def daily_body(session_date, *, count=50, close="1.20000"):
    rows = []
    day = session_date
    while len(rows) < count:
        if day.weekday() < 5:
            local = datetime.combine(day - timedelta(days=1), time(17), ZoneInfo("America/New_York"))
            rows.append({
                "time": local.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                "complete": bool(rows), "volume": 15,
                "mid": {"o": "1.10000", "h": "1.40000", "l": "1.00000",
                        "c": "1.12000" if rows else close},
            })
        day -= timedelta(days=1)
    return {"instrument": "EUR_USD", "granularity": "D", "candles": list(reversed(rows))}


class CandleChecks(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.db = self.notebook(self.bound)

    def broker(self, *responses):
        transport = ScriptedTransport(*((_CALL, response) for response in responses))
        self.addCleanup(transport.assert_consumed)
        return PracticeBroker(self.bound, transport=transport, now=self.clock.now), transport

    def add_pair(self, run_id="run-a", stage="manage_new"):
        self.add_decision(self.db, run_id=run_id, stage=stage)

    def capture(self, broker, run_id="run-a", stage="manage_new"):
        result = capture_pair_candles(self.db, broker, run_id=run_id, stage=stage, pair="EUR-USD")
        record = self.db.execute("""
            SELECT capture_json FROM pair_decisions WHERE run_id = ? AND stage = ? AND pair = 'EUR-USD'
        """, (run_id, stage)).fetchone()[0]
        self.assertNotIn('"candles"', record)
        self.assertNotIn(ACCOUNT, record)
        self.assertNotIn(TOKEN, record)
        self.assertEqual(json.loads(record), result.metadata)
        return result

    def test_a01_weekday_sessions_across_march_and_november_dst(self):
        cases = (
            ("2026-03-06T21:50:00Z", "2026-03-05T22:00:00.000000000Z"),
            ("2026-03-09T20:50:00Z", "2026-03-08T21:00:00.000000000Z"),
            ("2026-10-30T20:50:00Z", "2026-10-29T21:00:00.000000000Z"),
            ("2026-11-02T21:50:00Z", "2026-11-01T22:00:00.000000000Z"),
        )
        for run_at, signal_start in cases:
            with self.subTest(run_at=run_at):
                self.clock.current = datetime.fromisoformat(run_at)
                session_date = date.fromisoformat(run_at[:10])
                run_id = session_date.isoformat()
                self.start_run(self.db, run_id)
                self.add_pair(run_id)
                broker, transport = self.broker(HTTPReply(200, daily_body(session_date), "fixture-request"))
                result = self.capture(broker, run_id)
                self.assertEqual(len(result.candles), 50)
                self.assertEqual(result.candles[-1].timestamp, datetime.fromisoformat(signal_start))
                self.assertEqual(result.metadata, {
                    "session_date": run_id, "requested_at": run_at.replace("Z", ".000000Z"),
                    "responded_at": run_at.replace("Z", ".000000Z"), "http_status": 200,
                    "request_id": "fixture-request", "received_count": 50,
                    "signal_candle_start": signal_start, "validation": "valid", "reason": None,
                })
                self.assertEqual(transport.calls, [_CALL])

    def test_a01_each_stage_fetches_and_records_its_own_window(self):
        self.start_run(self.db)
        self.add_pair(stage="manage_open")
        self.add_pair(stage="manage_new")

        def reply(close):
            self.assertFalse(self.db.in_transaction)
            self.clock.advance(2)
            return HTTPReply(200, daily_body(date(2026, 11, 16), close=close))

        broker, transport = self.broker(lambda: reply("1.20000"), lambda: reply("1.25000"))
        opened = self.capture(broker, stage="manage_open")
        self.clock.advance(30)
        new = self.capture(broker, stage="manage_new")
        self.assertEqual(opened.candles[-1].close, 1.2)
        self.assertEqual(new.candles[-1].close, 1.25)
        self.assertEqual(opened.metadata["responded_at"], "2026-11-16T21:50:02.000000Z")
        self.assertEqual(new.metadata["requested_at"], "2026-11-16T21:50:32.000000Z")
        with self.assertRaisesRegex(ValueError, "without a candle capture"):
            self.capture(broker)
        self.assertEqual(transport.calls, [_CALL, _CALL])

    def test_a01_weekend_run_has_no_intended_window(self):
        for day in (21, 22):
            with self.subTest(day=day):
                self.clock.current = datetime(2026, 11, day, 21, 50, tzinfo=UTC)
                run_id = f"weekend-{day}"
                self.start_run(self.db, run_id)
                self.add_pair(run_id)
                broker, transport = self.broker()
                result = self.capture(broker, run_id)
                self.assertIsNone(result.candles)
                self.assertIsNone(result.metadata["requested_at"])
                self.assertEqual(result.metadata["reason"], "Run date has no weekday FX session")
                self.assertEqual(transport.calls, [])

    def test_a01_rollover_is_checked_when_response_arrives(self):
        self.start_run(self.db)
        self.add_pair(stage="manage_open")
        self.add_pair(stage="manage_new")
        self.clock.current = datetime(2026, 11, 16, 21, 59, 58, tzinfo=UTC)
        body = daily_body(date(2026, 11, 16))

        def response():
            self.clock.advance(1)
            return HTTPReply(200, body)

        broker, _ = self.broker(response, response)
        first = self.capture(broker, stage="manage_open")
        self.assertEqual(first.metadata["validation"], "valid")
        second = self.capture(broker, stage="manage_new")
        self.assertIsNone(second.candles)
        self.assertEqual(second.metadata["responded_at"], "2026-11-16T22:00:00.000000Z")
        self.assertEqual(second.metadata["reason"], "Capture time falls outside the intended session")
        self.assertEqual(first.candles[-1].close, 1.2)

    def test_a01_rejects_completed_only_or_another_sessions_partial(self):
        completed = daily_body(date(2026, 11, 16))
        completed["candles"][-1]["complete"] = True
        cases = (
            (completed, "Expected completed history and a final partial candle"),
            (daily_body(date(2026, 11, 13)), "Final candle belongs to a different session"),
            (daily_body(date(2026, 11, 17)), "Final candle belongs to a different session"),
        )
        for index, (body, reason) in enumerate(cases):
            with self.subTest(index=index):
                run_id = f"run-{index}"
                self.start_run(self.db, run_id)
                self.add_pair(run_id)
                broker, _ = self.broker(HTTPReply(200, body))
                result = self.capture(broker, run_id)
                self.assertIsNone(result.candles)
                self.assertEqual(result.metadata["validation"], "unavailable")
                self.assertEqual(result.metadata["reason"], reason)

    def test_a03_rejects_all_counts_other_than_the_bound_count_in_both_stages(self):
        for count in (0, 14, 49, 51):
            with self.subTest(count=count):
                run_id = f"count-{count}"
                self.start_run(self.db, run_id)
                self.add_pair(run_id, "manage_open")
                self.add_pair(run_id, "manage_new")
                reply = HTTPReply(200, daily_body(date(2026, 11, 16), count=count))
                broker, _ = self.broker(reply, reply)
                for stage in ("manage_open", "manage_new"):
                    result = self.capture(broker, run_id, stage)
                    self.assertIsNone(result.candles)
                    self.assertEqual(result.metadata["received_count"], count)
                    self.assertEqual(result.metadata["reason"], "Received candle count differs from the qualified count")

    def test_a03_rejects_malformed_ohlc_flags_identity_and_history(self):
        changes = (
            ("wrong instrument", lambda body, rows: body.update(instrument="USD_JPY")),
            ("wrong granularity", lambda body, rows: body.update(granularity="H1")),
            ("invalid array", lambda body, rows: body.update(candles={})),
            ("invalid candle", lambda body, rows: rows.__setitem__(0, None)),
            ("duplicate", lambda body, rows: rows[1].update(time=rows[0]["time"])),
            ("unordered", lambda body, rows: rows.__setitem__(slice(0, 2), rows[1::-1])),
            ("invalid date", lambda body, rows: rows[0].update(time="2026-02-30T22:00:00Z")),
            ("nonzero nanoseconds", lambda body, rows: rows[-1].update(time="2026-11-15T22:00:00.000000001Z")),
            ("wrong daily boundary", lambda body, rows: rows[-2].update(time="2026-11-12T21:00:00Z")),
            ("weekend history", lambda body, rows: rows[-2].update(time="2026-11-13T22:00:00Z")),
            ("incomplete history", lambda body, rows: rows[0].update(complete=False)),
            ("non-Boolean complete", lambda body, rows: rows[-1].update(complete=0)),
            ("missing mid", lambda body, rows: rows[-1].pop("mid")),
            ("negative volume", lambda body, rows: rows[-1].update(volume=-1)),
            ("NaN", lambda body, rows: rows[-1]["mid"].update(h="NaN")),
            ("infinity", lambda body, rows: rows[-1]["mid"].update(h="Infinity")),
            ("Boolean price", lambda body, rows: rows[-1]["mid"].update(o=True)),
            ("missing close", lambda body, rows: rows[-1]["mid"].pop("c")),
            ("zero price", lambda body, rows: rows[-1]["mid"].update(l="0")),
            ("inconsistent OHLC", lambda body, rows: rows[-1]["mid"].update(c="1.40000000000000001")),
        )
        original = daily_body(date(2026, 11, 16))
        for index, (name, change) in enumerate(changes):
            with self.subTest(name=name):
                body = deepcopy(original)
                change(body, body["candles"])
                run_id = f"invalid-{index}"
                self.start_run(self.db, run_id)
                self.add_pair(run_id)
                broker, _ = self.broker(HTTPReply(200, body))
                result = self.capture(broker, run_id)
                self.assertIsNone(result.candles)
                self.assertEqual(result.metadata["validation"], "unavailable")
                self.assertTrue(result.metadata["reason"])

    def test_a03_market_history_can_skip_a_date(self):
        self.start_run(self.db)
        self.add_pair()
        body = daily_body(date(2026, 11, 16), count=51)
        del body["candles"][-10]
        broker, _ = self.broker(HTTPReply(200, body))
        self.assertEqual(self.capture(broker).metadata["validation"], "valid")

    def test_a03_records_broker_failures_without_response_body(self):
        self.start_run(self.db)
        self.add_pair(stage="manage_open")
        self.add_pair(stage="manage_new")

        def timeout():
            raise TimeoutError(TOKEN)

        broker, _ = self.broker(HTTPReply(503, {"message": TOKEN}, ACCOUNT), timeout)
        for stage, status in (("manage_open", 503), ("manage_new", None)):
            result = self.capture(broker, stage=stage)
            self.assertIsNone(result.candles)
            self.assertEqual(result.metadata["http_status"], status)
            self.assertIsNone(result.metadata["received_count"])
            self.assertIsNotNone(result.metadata["requested_at"])
            self.assertIsNotNone(result.metadata["responded_at"])

    def test_a03_run_binding_mismatch_fails_before_the_candle_request(self):
        self.start_run(self.db)
        self.add_pair()
        with transaction(self.db):
            self.db.execute("UPDATE runs SET lookback_candles = 49, strategy_hash = ?", ("c" * 64,))
        broker, transport = self.broker()
        with self.assertRaisesRegex(ConfigurationError, "differs from the binding"):
            self.capture(broker)
        self.assertEqual(transport.calls, [])

    def test_a02_and_a03_only_fresh_events_and_valid_atr_are_eligible_for_entry(self):
        atr = 0.0012345678901234567
        for c1 in ("long", "short"):
            self.assertEqual(entry_signal(c1, atr), (c1, str(atr)))
            self.assertEqual(float(entry_signal(c1, atr)[1]), atr)
        self.assertIsNone(entry_signal("no_event", atr))
        self.assertIsNone(entry_signal("unavailable", atr))
        for invalid in (None, float("nan"), float("inf"), 0.0, -0.1, True):
            with self.subTest(atr=invalid):
                self.assertIsNone(entry_signal("short", invalid))
                self.assertEqual(exit_reasons("long", c1="unavailable", exit_signal="short"), ("exit",))
                self.assertEqual(exit_reasons("long", c1="short", exit_signal="unavailable"), ("c1",))
                self.assertEqual(exit_reasons("short", c1="long", exit_signal="long"), ("c1", "exit"))
                self.assertEqual(exit_reasons("short", c1="no_event", exit_signal="short"), ())
