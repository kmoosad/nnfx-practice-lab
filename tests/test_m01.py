"""Controlled M01 checks for A12, A15 and A16."""

from dataclasses import replace
import json
import logging
import sqlite3

from nnfx_practice.config import ConfigurationError, read_registry
from nnfx_practice.evidence import redact
from nnfx_practice.notebook import (
    SCHEMA_VERSION, PairUnavailable, finish_pair, open_notebook, open_readonly,
    pair_is_available, pair_progress, prepare_attempt, reserve_set, transaction, utc_text,
)

from .support import (
    ACCOUNT, MANIFEST, TOKEN, Call, Interrupted, NotebookCase, ScriptedTransport, interrupt_commit,
)


class BindingTests(NotebookCase):
    def test_a16_reject_duplicate_registry_bindings(self):
        for changes in ({"controller_b": "controller-a"}, {"notebook_b": "notebook-a"}):
            with self.subTest(changes=changes):
                self.write_registry(**changes)
                with self.assertRaisesRegex(ConfigurationError, "Duplicate controller or notebook"):
                    read_registry(self.root)
        self.write_registry()
        self.write_private(account_b=ACCOUNT)
        with self.assertRaisesRegex(ConfigurationError, "Duplicate account"):
            self.binding()
        self.assertFalse((self.root / "var").exists())

    def test_a16_reject_unsafe_notebook_paths(self):
        self.write_registry(notebook_a="../private-account")
        with self.assertRaisesRegex(ConfigurationError, "identifier"):
            read_registry(self.root)
        self.write_registry()
        (self.root / "var").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ConfigurationError, "symbolic links"):
            read_registry(self.root)

    def test_a16_reject_private_file_with_open_permissions(self):
        (self.root / ".env").chmod(0o644)
        self.assertEqual(set(read_registry(self.root)), {"controller-a", "controller-b"})
        with self.assertRaisesRegex(ConfigurationError, "owner-only"):
            self.binding()

    def test_a16_reject_lookback_mismatch_and_missing_manifest(self):
        self.write_private(count=51)
        with self.assertRaisesRegex(ConfigurationError, "qualified count"):
            self.binding()
        self.manifest_path.unlink()
        with self.assertRaisesRegex(ConfigurationError, "manifest"):
            self.binding()

    def test_a16_an_unqualified_strategy_does_not_change_another_binding(self):
        bound = self.binding()
        self.notebook(bound)
        self.write_registry(strategy_b="unqualified-v2")
        with self.assertRaisesRegex(ConfigurationError, "manifest"):
            self.binding("controller-b")
        with open_notebook(self.root, self.binding()) as reopened:
            self.assertEqual(reopened.execute("SELECT manifest_hash FROM notebook").fetchone()[0], bound.manifest.hash)

    def test_a16_notebooks_are_independent_and_reopen_without_erasing_history(self):
        a, b = self.binding(), self.binding("controller-b")
        db_a, db_b = self.notebook(a), self.notebook(b)
        self.start_run(db_a, "run-a")
        self.start_run(db_b, "run-b")
        self.assertEqual(db_a.execute("SELECT run_id FROM runs").fetchone()[0], "run-a")
        self.assertEqual(db_b.execute("SELECT run_id FROM runs").fetchone()[0], "run-b")
        self.assertEqual(db_b.execute("SELECT home_currency FROM notebook").fetchone()[0], "EUR")
        self.assertNotEqual(a.experiment.notebook_path(self.root), b.experiment.notebook_path(self.root))
        with open_notebook(self.root, a, create=True) as reopened:
            self.assertEqual(reopened.execute("SELECT run_id FROM runs").fetchone()[0], "run-a")
        self.assertFalse(db_a.execute("PRAGMA foreign_key_check").fetchall())

    def test_a16_immutable_binding_rejects_identity_rule_and_count_changes(self):
        bound = self.binding()
        db = self.notebook(bound)
        self.start_run(db)
        self.write_private(account_a="fixture-account-other")
        wrong_account = self.binding()
        self.write_private(currency="GBP")
        wrong_currency = self.binding()
        self.write_private()
        self.write_manifest({**MANIFEST, "signal_rules": {"c1": "changed", "exit": "changed"}})
        wrong_rules = self.binding()
        self.write_manifest({**MANIFEST, "qualified_total_candle_count": 51})
        self.write_private(count=51)
        wrong_count = self.binding()
        for candidate in (wrong_account, wrong_currency, wrong_rules, wrong_count):
            with self.assertRaisesRegex(ConfigurationError, "original notebook binding"):
                with open_notebook(self.root, candidate, create=True):
                    self.fail("Mismatched binding opened")

        self.write_manifest(MANIFEST)
        self.write_private(token="rotated-fixture-token")
        rotated = self.binding()
        renamed = replace(rotated, experiment=replace(rotated.experiment, notebook_name="New name"))
        with open_notebook(self.root, renamed) as reopened:
            self.assertEqual(reopened.execute("SELECT run_id FROM runs").fetchone()[0], "run-a")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "immutable"):
            db.execute("UPDATE notebook SET home_currency = 'GBP'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "cannot be replaced"):
            db.execute("INSERT OR REPLACE INTO notebook SELECT * FROM notebook")

    def test_a16_preserve_existing_data_when_schema_version_is_unknown(self):
        bound = self.binding()
        path = bound.experiment.notebook_path(self.root)
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path, isolation_level=None) as legacy:
            self.addCleanup(legacy.close)
            legacy.executescript("CREATE TABLE existing (value TEXT); INSERT INTO existing VALUES ('keep');")
            with self.assertRaisesRegex(ConfigurationError, "populated unversioned"):
                with open_notebook(self.root, bound, create=True):
                    self.fail("Unversioned data was initialized")
            legacy.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
            with self.assertRaisesRegex(ConfigurationError, "Unsupported notebook schema"):
                with open_notebook(self.root, bound, create=True):
                    self.fail("Unknown schema was opened")
            self.assertEqual(legacy.execute("SELECT value FROM existing").fetchone()[0], "keep")

    def test_a16_qualification_baseline_has_its_own_transaction_and_leaves_activation_pending(self):
        binding = self.binding()
        db = self.notebook(binding)
        timestamp = "2026-11-16T21:50:00.123456789Z"
        with transaction(db):
            db.execute("""
                INSERT INTO account_snapshots (snapshot_id, purpose, requested_at, responded_at,
                    last_transaction_id, balance, home_currency, reconciliation_status)
                VALUES ('q0', 'qualification', ?, ?, '0010', '1000.0100', 'USD', 'reconciled')
            """, (timestamp, timestamp))
            db.execute("""
                UPDATE notebook SET qualification_snapshot_id = 'q0', qualification_transaction_id = '0010',
                    qualification_evidence_json = '["offline-q0"]', imported_through_transaction_id = '0010'
            """)
        with open_notebook(self.root, binding, create=True) as reopened:
            bound = reopened.execute("SELECT * FROM notebook").fetchone()
            self.assertEqual(bound["qualification_snapshot_id"], "q0")
            self.assertEqual(bound["imported_through_transaction_id"], "0010")
            self.assertEqual(bound["manifest_hash"], binding.manifest.hash)
            for field in ("activated_at", "activation_snapshot_id", "activation_evidence_json", "activation_transaction_id"):
                self.assertIsNone(bound[field])
            snapshot = reopened.execute("SELECT * FROM account_snapshots").fetchone()
            self.assertEqual(snapshot["responded_at"], timestamp)
            self.assertEqual(snapshot["balance"], "1000.0100")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("UPDATE notebook SET qualification_transaction_id = 'different-boundary'")


class DurabilityTests(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.db = self.notebook(self.bound)
        self.start_run(self.db)
        self.add_decision(self.db)

    def reserve(self, *, set_id="set-a", run_id="run-a", pair="EUR-USD"):
        reserve_set(self.db, set_id=set_id, run_id=run_id, pair=pair, direction="long",
                    entry_atr="0.0012300000001", stop_distance="0.001850", planned_units="8000.00")

    def prepare(self, *, payload=None, attempt_id="attempt-1", client_id="client-1", path="/orders"):
        prepare_attempt(self.db, self.bound, attempt_id=attempt_id, run_id="run-a", stage="manage_new",
                        pair="EUR-USD", set_id="set-a", leg_no=1, purpose="entry", method="POST",
                        path=path, client_id=client_id, prepared_at=self.clock.now(), payload=payload)

    def test_a12_failed_commit_rolls_back_reservation_and_legs(self):
        self.assertEqual(self.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.db.execute("PRAGMA synchronous").fetchone()[0], 2)
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with self.assertRaises(sqlite3.DatabaseError), interrupt_commit(self.db):
            self.reserve()
        with open_readonly(self.root, self.bound.experiment) as reader:
            self.assertTrue(pair_is_available(reader, "EUR-USD"))
            self.assertIsNone(reader.execute("SELECT set_id FROM pair_decisions").fetchone()[0])
            self.assertEqual(reader.execute("SELECT count(*) FROM trade_legs").fetchone()[0], 0)
        self.assertFalse(self.db.in_transaction)
        self.reserve()

    def test_a12_reservation_survives_commit_and_blocks_competing_decision(self):
        self.reserve()
        self.start_run(self.db, "run-b")
        self.add_decision(self.db, run_id="run-b")
        with self.assertRaises(PairUnavailable):
            self.reserve(set_id="set-b", run_id="run-b")
        with self.assertRaisesRegex(sqlite3.IntegrityError, r"trade_sets\.pair"):
            self.db.execute("""
                INSERT INTO trade_sets (set_id, run_id, pair, strategy_hash, direction,
                    entry_atr, stop_distance, establishment_status)
                VALUES ('set-b', 'run-b', 'EUR-USD', 'fixture', 'short', '0.001', '0.0015', 'pending')
            """)
        with open_readonly(self.root, self.bound.experiment) as reader:
            self.assertFalse(pair_is_available(reader, "EUR-USD"))
            self.assertTrue(pair_is_available(reader, "GBP-USD"))
            legs = reader.execute("SELECT leg_no, planned_units, broker_trade_id FROM trade_legs ORDER BY leg_no")
            self.assertEqual([tuple(leg) for leg in legs], [(1, "8000.00", None), (2, "8000.00", None)])

    def test_a12_open_issue_or_leg_blocks_pair_even_after_terminal_set(self):
        self.reserve()
        now = utc_text(self.clock.now())
        with transaction(self.db):
            self.db.execute("UPDATE trade_sets SET terminal_at = ?", (now,))
            self.db.execute("UPDATE trade_legs SET broker_state = 'open' WHERE leg_no = 1")
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))
        with transaction(self.db):
            self.db.execute("UPDATE trade_legs SET broker_state = 'closed'")
            self.db.execute("""
                INSERT INTO issues (issue_id, pair, code, first_observed_at, last_observed_at, set_id, status)
                VALUES ('issue-a', 'EUR-USD', 'uncertainty', ?, ?, 'set-a', 'open')
            """, (now, now))
        self.assertFalse(pair_is_available(self.db, "EUR-USD"))

    def test_a12_interruption_after_attempt_commit_before_send(self):
        self.reserve()
        transport = ScriptedTransport()
        with self.assertRaises(sqlite3.DatabaseError), interrupt_commit(self.db):
            self.prepare()
        self.assertEqual(self.db.execute("SELECT count(*) FROM broker_attempts").fetchone()[0], 0)
        with self.assertRaises(Interrupted), interrupt_commit(self.db, after=True):
            self.prepare()
        transport.assert_consumed()
        self.assertEqual(transport.calls, [])
        with open_notebook(self.root, self.bound) as reopened:
            self.assertEqual(reopened.execute("SELECT outcome FROM broker_attempts").fetchone()[0], "prepared")
            self.assertEqual(tuple(reopened.execute("SELECT status, ended_at FROM runs").fetchone()), ("running", None))
            self.assertFalse(pair_is_available(reopened, "EUR-USD"))

    def test_a12_scripted_send_sees_prepared_attempt_and_can_interrupt(self):
        self.reserve()
        payload = {"order": {"units": "8000.00"}}
        call = Call("POST", "/orders", payload)
        later_call = Call("GET", "/summary")

        def interrupt():
            self.assertFalse(self.db.in_transaction)
            with open_readonly(self.root, self.bound.experiment) as reader:
                row = reader.execute("SELECT outcome, payload_json, responded_at FROM broker_attempts").fetchone()
                self.assertEqual(row["outcome"], "prepared")
                self.assertEqual(json.loads(row["payload_json"]), payload)
                self.assertIsNone(row["responded_at"])
            raise Interrupted("before response commit")

        transport = ScriptedTransport((call, interrupt), (later_call, {"lastTransactionID": "0010"}))
        self.prepare(payload=payload)
        with self.assertRaises(Interrupted):
            transport.request(call.method, call.path, call.payload)
        self.assertEqual(transport.request(later_call.method, later_call.path), {"lastTransactionID": "0010"})
        self.assertEqual(transport.calls, [call, later_call])
        transport.assert_consumed()
        with self.assertRaisesRegex(sqlite3.IntegrityError, r"broker_attempts\.client_id"):
            self.prepare(attempt_id="duplicate-client")

    def test_a12_secrets_are_removed_from_prepared_evidence_and_reported_errors(self):
        self.reserve()
        self.prepare(payload={
            "order": {"units": "8000", "requestHeaders": {"Authorization": f"Bearer {TOKEN}"}},
            "access_token": "unrecognized-secret",
            "accountID": ACCOUNT,
            "notes": [f"session {TOKEN}", "Bearer other-secret", f"path /v3/accounts/{ACCOUNT}"],
        })
        row = self.db.execute("SELECT * FROM broker_attempts").fetchone()
        self.assertEqual(json.loads(row["payload_json"])["order"], {"units": "8000"})
        for secret in (TOKEN, ACCOUNT, "unrecognized-secret", "other-secret", "Authorization"):
            self.assertNotIn(secret, repr(tuple(row)))
        logger = logging.getLogger("offline.m01")
        with self.assertLogs(logger) as captured:
            logger.warning("%r %s", self.bound, redact(f"Connection failed: Bearer {TOKEN}", (TOKEN,)))
            self.write_private(token="invalid private-token-value")
            with self.assertRaises(ConfigurationError) as error:
                self.binding()
            logger.warning("%s", error.exception)
        for secret in (TOKEN, ACCOUNT, "invalid private-token-value"):
            self.assertNotIn(secret, "\n".join(captured.output))
        with self.assertRaisesRegex(ValueError, "account-relative"):
            self.prepare(path=f"/v3/accounts/{ACCOUNT}/orders")

    def test_a15_progress_counts_final_outcomes_and_readonly_sees_wal(self):
        self.add_decision(self.db, "GBP-USD", 2)
        self.add_decision(self.db, "AUD-USD", 3)
        self.add_decision(self.db, "NZD-USD", 4)
        (self.root / ".env").unlink()
        public = read_registry(self.root)["controller-a"]
        with open_readonly(self.root, public) as reader:
            for pair, outcome in (("EUR-USD", "completed"), ("GBP-USD", "skipped"), ("AUD-USD", "failed")):
                self.clock.advance(1.25)
                finish_pair(self.db, self.bound, run_id="run-a", stage="manage_new", pair=pair,
                            ended_at=self.clock.now(), outcome=outcome)
            self.assertEqual(tuple(pair_progress(reader, "run-a", "manage_new")), (3, 1, 1))
            self.assertEqual(tuple(pair_progress(reader, "run-a", "manage_open")), (0, 0, 0))
            self.assertEqual(reader.execute("SELECT count(*) FROM account_snapshots").fetchone()[0], 0)
            run = reader.execute("SELECT * FROM runs").fetchone()
            self.assertEqual(run["last_progress_at"], utc_text(self.clock.now()))
            self.assertEqual(run["session_date"], "2026-11-16")
            self.assertEqual(run["lookback_candles"], 50)
            stages = reader.execute("SELECT stage, status, expected_pair_count FROM stages ORDER BY stage")
            self.assertEqual([tuple(row) for row in stages], [
                ("manage_new", "not_started", 28), ("manage_open", "not_started", None),
            ])
            self.assertEqual(self.clock.monotonic(), 3.75)
            with transaction(self.db):
                self.db.execute("UPDATE runs SET status = 'completed' WHERE run_id = 'run-a'")
                self.assertEqual(reader.execute("SELECT status FROM runs").fetchone()[0], "running")
            self.assertEqual(reader.execute("SELECT status FROM runs").fetchone()[0], "completed")
            reader.execute("PRAGMA query_only = OFF")
            with self.assertRaisesRegex(sqlite3.OperationalError, "readonly"):
                reader.execute("UPDATE runs SET status = 'failed'")
