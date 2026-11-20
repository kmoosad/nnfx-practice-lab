"""Offline inputs and interruption points shared by the milestone checks."""

from collections import deque
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nnfx_practice.config import load_binding
from nnfx_practice.notebook import open_notebook, start_run, transaction, utc_text


TOKEN = "fixture-token-a-private"
ACCOUNT = "fixture-account-a"
MANIFEST = {
    "strategy_version": "fixture-v1",
    "research_result_id": "offline-fixture-only",
    "source_commit": "a" * 40,
    "implementation_hashes": {"fixture.py": "b" * 64},
    "conversion_hashes": {},
    "dependency_hashes": {},
    "parameters": {"period": 12},
    "output_bindings": {"c1": "left", "exit": "right"},
    "signal_rules": {"c1": "fixture-c1", "exit": "fixture-exit"},
    "lab_numeric_semantics": {"purpose": "offline-fixture-only"},
    "qualified_total_candle_count": 50,
    "qualification_evidence": ["synthetic-fixture-reference"],
}


@dataclass
class ManualClock:
    current: datetime = datetime(2026, 11, 16, 21, 50, tzinfo=UTC)
    elapsed: float = 0

    def now(self):
        return self.current

    def monotonic(self):
        return self.elapsed

    def advance(self, seconds):
        self.current += timedelta(seconds=seconds)
        self.elapsed += seconds


class Interrupted(BaseException):
    """Simulates a process stopping before its next durable operation."""


@contextmanager
def interrupt_commit(db, *, after=False):
    if after:
        yield
        raise Interrupted("after commit")

    def deny_commit(action, arg, *_):
        if action == sqlite3.SQLITE_TRANSACTION and arg == "COMMIT":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    db.set_authorizer(deny_commit)
    try:
        yield
    finally:
        db.set_authorizer(None)


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    payload: object = None


class ScriptedTransport:
    def __init__(self, *script):
        self._script = deque(script)
        self.calls = []

    def request(self, method, path, payload=None):
        actual = Call(method, path, deepcopy(payload))
        self.calls.append(actual)
        if not self._script or actual != self._script[0][0]:
            raise AssertionError("Unexpected scripted transport request")
        _, response = self._script.popleft()
        return response() if callable(response) else deepcopy(response)

    def assert_consumed(self):
        if self._script:
            raise AssertionError("Scripted transport requests remain")


class NotebookCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.clock = ManualClock()
        self.manifest_path = self.root / "strategies" / "fixture-v1" / "manifest.json"
        self.manifest_path.parent.mkdir(parents=True)
        self.write_manifest(MANIFEST)
        self.write_registry()
        self.write_private()

    def write_registry(self, *, controller_b="controller-b", notebook_b="notebook-b",
                       notebook_a="notebook-a", strategy_b="fixture-v1"):
        text = f'''[[experiments]]
controller_id = "controller-a"
notebook_id = "{notebook_a}"
notebook_name = "Fixture A"
strategy_version = "fixture-v1"
connection_key = "PRACTICE_A"

[[experiments]]
controller_id = "{controller_b}"
notebook_id = "{notebook_b}"
notebook_name = "Fixture B"
strategy_version = "{strategy_b}"
connection_key = "PRACTICE_B"
'''
        (self.root / "config.toml").write_text(text, encoding="utf-8")

    def write_private(self, *, account_a=ACCOUNT, account_b="fixture-account-b", token=TOKEN,
                      currency="USD", count=50):
        text = f'''PRACTICE_A_ACCOUNT_ID={account_a}
PRACTICE_A_TOKEN={token}
PRACTICE_A_HOME_CURRENCY={currency}
PRACTICE_A_LOOKBACK_CANDLES={count}
PRACTICE_B_ACCOUNT_ID={account_b}
PRACTICE_B_TOKEN=fixture-token-b-private
PRACTICE_B_HOME_CURRENCY=EUR
PRACTICE_B_LOOKBACK_CANDLES=50
'''
        path = self.root / ".env"
        path.touch(mode=0o600)
        path.write_text(text, encoding="utf-8")

    def write_manifest(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def binding(self, controller="controller-a"):
        return load_binding(self.root, controller)

    def notebook(self, binding):
        return self.enterContext(open_notebook(self.root, binding, create=True))

    def start_run(self, db, run_id="run-a"):
        start_run(db, run_id=run_id, started_at=self.clock.now(), config_hash="c" * 64, code_hash="d" * 40)

    def add_decision(self, db, pair="EUR-USD", order=1, *, run_id="run-a", stage="manage_new"):
        with transaction(db):
            db.execute("""
                INSERT INTO pair_decisions (run_id, stage, pair, pair_order, started_at)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, stage, pair, order, utc_text(self.clock.now())))
