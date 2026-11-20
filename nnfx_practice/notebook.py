"""SQLite foundation for a single, permanently bound practice account."""

from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import os
import grp
from pathlib import Path
import re
import sqlite3
import stat
from zoneinfo import ZoneInfo

from .config import Binding, ConfigurationError, Experiment
from .evidence import encode_evidence, redact


SCHEMA_VERSION = 3
_HASH = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")


class PairUnavailable(ValueError):
    """A set, unconfirmed leg or unresolved issue already blocks the pair."""


@contextmanager
def transaction(db):
    """Commit a short write as one unit. Callers do broker work outside it."""
    db.execute("BEGIN IMMEDIATE")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _schema_version(db):
    return db.execute("PRAGMA user_version").fetchone()[0]


def _create_schema(db):
    _schema_script(db, "schema.sql")
    _schema_script(db, "schema_m07.sql")
    _schema_script(db, "schema_transactions.sql")
    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _schema_script(db, filename):
    # executescript would implicitly commit an existing transaction.
    statement = ""
    for line in Path(__file__).with_name(filename).read_text(encoding="utf-8").splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            db.execute(statement)
            statement = ""
    if statement.strip():
        raise RuntimeError("Incomplete notebook schema")


def _binding_values(binding):
    return (
        binding.experiment.controller_id, binding.experiment.notebook_id,
        binding.connection.account_id, binding.connection.home_currency,
        binding.experiment.strategy_version, binding.manifest.body,
        binding.manifest.hash, binding.connection.lookback_candles,
    )


def _check_binding(db, binding):
    row = db.execute("""
        SELECT controller_id, notebook_id, account_id, home_currency, strategy_version,
               manifest_json, manifest_hash, lookback_candles
        FROM notebook WHERE singleton = 1
    """).fetchone()
    if row is None or tuple(row) != _binding_values(binding):
        raise ConfigurationError("Configured binding differs from the original notebook binding")


@contextmanager
def _connect(path, mode):
    db = sqlite3.connect(f"{path.as_uri()}?mode={mode}", uri=True, isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA recursive_triggers = ON")
        yield db
    finally:
        db.close()


@contextmanager
def open_notebook(root: Path, binding: Binding, *, create: bool = False):
    """Open a bound writer or explicitly create and bind an empty notebook."""
    if binding.connection.lookback_candles != binding.manifest.lookback_candles:
        raise ConfigurationError("Configured lookback differs from the qualified count")
    shared = bool(os.environ.get('NNFX_NOTEBOOK_READ_GROUP'))
    if shared and (not hasattr(sqlite3.Connection, 'setconfig')
                   or not hasattr(sqlite3, 'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE')):
        raise ConfigurationError('Shared WAL notebooks require Python 3.12+ with NO_CKPT_ON_CLOSE support')
    path = binding.experiment.notebook_path(root)
    if create:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)

    _share_notebook(path)

    with _connect(path, "rw") as db:
        if shared:
            # Keep readable WAL/SHM files after the last writer closes. A reader
            # with no directory-write permission cannot recreate these files.
            # Normal WAL autocheckpointing remains enabled.
            db.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        db.execute("PRAGMA synchronous = FULL")
        if create and _schema_version(db) == 0:
            with transaction(db):
                # Recheck after taking the writer lock in case another opener initialized it.
                if _schema_version(db) == 0:
                    if db.execute("SELECT 1 FROM sqlite_schema LIMIT 1").fetchone():
                        raise ConfigurationError("Cannot initialize a populated unversioned notebook")
                    _create_schema(db)
                    db.execute("""
                        INSERT INTO notebook (
                            singleton, controller_id, notebook_id, account_id, home_currency,
                            strategy_version, manifest_json, manifest_hash, lookback_candles
                        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, _binding_values(binding))
        if _schema_version(db) in (1, 2):
            _check_binding(db, binding)
            with transaction(db):
                if _schema_version(db) == 1:
                    _schema_script(db, "schema_m07.sql")
                    db.execute("PRAGMA user_version = 2")
                if _schema_version(db) == 2:
                    _schema_script(db, "schema_transactions.sql")
                    db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        if _schema_version(db) != SCHEMA_VERSION:
            raise ConfigurationError("Unsupported notebook schema version")
        _check_binding(db, binding)
        if db.execute("PRAGMA journal_mode = WAL").fetchone()[0] != "wal":
            raise RuntimeError("Could not enable notebook WAL")
        yield db


def _share_notebook(path):
    """Opt-in deployment group reads; private local notebooks retain mode 0600.

    The installer creates a setgid directory owned by the writer/readers group.
    SQLite gives newly created WAL/SHM files the database's permissions; cover
    existing sidecars too, before a deployed reader can access this notebook.
    """
    group = os.environ.get('NNFX_NOTEBOOK_READ_GROUP')
    if not group:
        return
    try:
        gid = grp.getgrnam(group).gr_gid
        directory = path.parent.stat()
        if directory.st_gid != gid or directory.st_mode & 0o077 != 0o050:
            raise ConfigurationError('Notebook reader directory must grant group read/traverse only')
        for name in (path, Path(str(path) + '-wal'), Path(str(path) + '-shm')):
            try:
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                continue
            try:
                info = os.fstat(descriptor)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != os.getuid() or info.st_gid != gid):
                    raise ConfigurationError('Notebook reader file ownership is invalid')
                os.fchmod(descriptor, 0o640)
            finally:
                os.close(descriptor)
    except (KeyError, OSError):
        raise ConfigurationError('Cannot prepare notebook reader permissions') from None


@contextmanager
def open_readonly(root: Path, experiment: Experiment):
    """Read committed notebook records without needing private configuration."""
    with _connect(experiment.notebook_path(root), "ro") as db:
        db.execute("PRAGMA query_only = ON")
        if _schema_version(db) not in (2, SCHEMA_VERSION):
            raise ConfigurationError("Unsupported notebook schema version")
        row = db.execute("""
            SELECT controller_id, notebook_id, strategy_version FROM notebook WHERE singleton = 1
        """).fetchone()
        if row is None or tuple(row) != (experiment.controller_id, experiment.notebook_id, experiment.strategy_version):
            raise ConfigurationError("Registry entry differs from the original notebook binding")
        yield db


def utc_text(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("A timezone-aware timestamp is required")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def start_run(db, *, run_id, started_at, config_hash, code_hash, mode=None, evidence=None):
    if not _HASH.fullmatch(config_hash) or not _HASH.fullmatch(code_hash):
        raise ValueError("Expected configuration and code hashes")
    start = utc_text(started_at)
    session_date = started_at.astimezone(ZoneInfo("America/New_York")).date().isoformat()
    with transaction(db):
        db.execute("""
            INSERT INTO runs (
                run_id, strategy_hash, config_hash, code_hash, started_at, session_date,
                lookback_candles, status, last_progress_at
            ) SELECT ?, manifest_hash, ?, ?, ?, ?, lookback_candles, 'running', ?
              FROM notebook WHERE singleton = 1
        """, (run_id, config_hash, code_hash, start, session_date, start))
        db.executemany("""
            INSERT INTO stages (run_id, stage, status, expected_pair_count)
            VALUES (?, ?, 'not_started', ?)
        """, [(run_id, "manage_open", None), (run_id, "manage_new", 28)])
        if mode is not None:
            db.execute("INSERT INTO run_invocations (run_id, mode, evidence_json) VALUES (?, ?, ?)",
                       (run_id, mode, evidence))


def pair_progress(db, run_id, stage):
    return db.execute("""
        SELECT count(outcome) AS finished,
               count(CASE WHEN outcome = 'skipped' THEN 1 END) AS skipped,
               count(CASE WHEN outcome = 'failed' THEN 1 END) AS failed
        FROM pair_decisions WHERE run_id = ? AND stage = ?
    """, (run_id, stage)).fetchone()


def finish_pair(db, binding, *, run_id, stage, pair, ended_at, outcome, reason=None):
    end = utc_text(ended_at)
    private_values = (binding.connection.token, binding.connection.account_id)
    with transaction(db):
        _check_binding(db, binding)
        updated = db.execute("""
            UPDATE pair_decisions SET ended_at = ?, outcome = ?, reason = ?
            WHERE run_id = ? AND stage = ? AND pair = ? AND outcome IS NULL
        """, (end, outcome, redact(reason, private_values), run_id, stage, pair))
        if updated.rowcount != 1:
            raise ValueError("Expected one unfinished pair decision")
        db.execute("UPDATE runs SET last_progress_at = ? WHERE run_id = ?", (end, run_id))


def pair_is_available(db, pair):
    return bool(db.execute("""
        SELECT NOT EXISTS (
            SELECT 1 FROM trade_sets WHERE pair = ? AND terminal_at IS NULL
        ) AND NOT EXISTS (
            SELECT 1 FROM trade_legs JOIN trade_sets USING (set_id)
            WHERE trade_sets.pair = ? AND (broker_state IS NULL OR broker_state = 'open')
        ) AND NOT EXISTS (
            SELECT 1 FROM issues WHERE pair = ? AND status = 'open'
        )
    """, (pair, pair, pair)).fetchone()[0])


def _decimal_text(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError("An exact decimal is required")
    try:
        number = Decimal(value)
        valid = number.is_finite() and number > 0
    except InvalidOperation:
        valid = False
    if not valid:
        raise ValueError("A positive finite decimal is required")
    return str(value)


def reserve_set(db, *, set_id, run_id, pair, direction, entry_atr, stop_distance, planned_units):
    """Reserve a pair and both legs against an existing unfinished entry decision."""
    entry_atr = _decimal_text(entry_atr)
    stop_distance = _decimal_text(stop_distance)
    planned_units = _decimal_text(planned_units)
    with transaction(db):
        if not pair_is_available(db, pair):
            raise PairUnavailable("Pair is occupied or blocked")
        decision = db.execute("""
            SELECT runs.strategy_hash FROM pair_decisions JOIN runs USING (run_id)
            WHERE run_id = ? AND stage = 'manage_new' AND pair = ?
              AND outcome IS NULL AND set_id IS NULL AND runs.status = 'running'
        """, (run_id, pair)).fetchone()
        if decision is None:
            raise ValueError("Expected one unreserved, unfinished entry decision")
        db.execute("""
            INSERT INTO trade_sets (set_id, run_id, pair, strategy_hash, direction,
                                    entry_atr, stop_distance, establishment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (set_id, run_id, pair, decision[0], direction, entry_atr, stop_distance))
        db.executemany("""
            INSERT INTO trade_legs (set_id, leg_no, planned_units) VALUES (?, ?, ?)
        """, [(set_id, leg, planned_units) for leg in (1, 2)])
        db.execute("""
            UPDATE pair_decisions SET set_id = ? WHERE run_id = ? AND stage = 'manage_new' AND pair = ?
        """, (set_id, run_id, pair))


def prepare_attempt(
    db, binding, *, attempt_id, run_id, stage, purpose, method, path, prepared_at,
    pair=None, set_id=None, leg_no=None, client_id=None, payload=None,
    broker_trade_id=None,
):
    """Persist one intent before handing off to a transport."""
    private_values = (binding.connection.token, binding.connection.account_id)
    if not re.fullmatch(r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]*", path) or path.startswith("/v3/"):
        raise ValueError("Use a clean, account-relative request path")
    for value in (attempt_id, run_id, stage, pair, set_id, purpose, method, path, client_id, broker_trade_id):
        if redact(value, private_values) != value:
            raise ValueError("Attempt metadata contains private connection information")
    encoded = None if payload is None else encode_evidence(payload, private_values)
    with transaction(db):
        _check_binding(db, binding)
        if set_id is not None:
            match = db.execute("SELECT pair FROM trade_sets WHERE set_id = ?", (set_id,)).fetchone()
            # Reconciliation actions precede the surviving-pair decisions.
            # Those attempts identify their pair through the registered set.
            reconciliation_stop = (pair is None and stage == "manage_open" and purpose == "stop_to_entry"
                                   and leg_no == 2 and broker_trade_id is not None)
            if match is None or (match[0] != pair and not reconciliation_stop):
                raise ValueError("Attempt set does not match its pair")
        if broker_trade_id is not None:
            leg = db.execute("SELECT broker_trade_id FROM trade_legs WHERE set_id = ? AND leg_no = ?",
                             (set_id, leg_no)).fetchone()
            if leg is None or leg[0] != broker_trade_id:
                raise ValueError("Attempt trade does not match its registered leg")
        db.execute("""
            INSERT INTO broker_attempts (attempt_id, run_id, stage, pair, set_id, leg_no,
                purpose, method, path, payload_json, client_id, prepared_at, broker_trade_id, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'prepared')
        """, (attempt_id, run_id, stage, pair, set_id, leg_no, purpose, method, path,
              encoded, client_id, utc_text(prepared_at), broker_trade_id))
