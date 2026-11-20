"""Explicit master invocations. Scheduler timing belongs to M09, execution to M10."""

from datetime import datetime
import logging
import sqlite3
from time import monotonic
from uuid import uuid4

from .broker import BrokerError, money
from .control import controller_exclusion
from .evidence import redact
from .lifecycle import bound_broker, require_invocation
from .manage_new import manage_new
from .manage_open import manage_open
from .notebook import open_notebook, start_run, transaction
from .reconciliation import _balance_through, _save_snapshot, import_through, reconcile_snapshot


log = logging.getLogger(__name__)


def sizing_refresh(db, broker, run_id):
    """Exactly one 4.1 request; keep its read apart from reconciled reports."""
    row = db.execute('SELECT * FROM runs WHERE run_id = ?', (run_id,)).fetchone()
    if row['sizing_balance'] is not None:
        raise ValueError('Sizing refresh cannot be repeated')
    with transaction(db):
        db.execute("UPDATE stages SET current_step = '4.1' WHERE run_id = ? AND stage = 'manage_new'", (run_id,))
        db.execute('UPDATE runs SET last_progress_at = ? WHERE run_id = ?', (broker.now(), run_id))
    read = None
    at = broker.now()
    try:
        read = broker.summary()
        balance = money(read.body['account']['balance'])
        import_through(db, broker, read.boundary)
        if balance != _balance_through(db, read.boundary):
            raise BrokerError('Unexplained sizing balance at the returned transaction boundary')
        if db.execute("SELECT 1 FROM issues WHERE status = 'open' AND pair IS NULL").fetchone():
            raise BrokerError('Unresolved account-wide issue prevents entry')
        with transaction(db):
            # A summary is sizing evidence, not a reconciled account snapshot.
            identifier = uuid4().hex
            _save_snapshot(db, broker, identifier, 'sizing_balance', read, at)
            db.execute("UPDATE account_snapshots SET reconciliation_status = 'pending' WHERE snapshot_id = ?", (identifier,))
            db.execute('''UPDATE runs SET sizing_balance = ?, sizing_balance_at = ?, sizing_transaction_id = ?,
                          last_progress_at = ? WHERE run_id = ?''',
                       (str(balance), read.responded_at, read.boundary, broker.now(), run_id))
    except BrokerError as failure:
        with transaction(db):
            _save_snapshot(db, broker, uuid4().hex, 'sizing_balance', read, at, failure=failure)
        raise


def run_master(root, controller_id, broker, *, mode='ordinary', evidence=None,
               config_hash, code_hash, run_id=None, elapsed=monotonic):
    """Create one new run; never resume it, replay an entry, or enable a timer."""
    binding = bound_broker(root, controller_id, broker)
    with controller_exclusion(root, binding):
        try:
            with open_notebook(root, binding) as db:
                refs = require_invocation(db, broker, mode, evidence)
                identifier = run_id or uuid4().hex
                start = elapsed()
                start_run(db, run_id=identifier, started_at=datetime.fromisoformat(broker.now()),
                          config_hash=config_hash, code_hash=code_hash, mode=mode, evidence=refs)
                try:
                    manage_open(db, broker, run_id=identifier, elapsed=elapsed)
                    sizing_refresh(db, broker, identifier)
                    manage_new(db, broker, run_id=identifier, elapsed=elapsed)
                except BrokerError as failure:
                    error = redact(str(failure), broker.private_values)
                    with transaction(db):
                        db.execute('''UPDATE stages SET status = 'blocked', failure_summary = ?
                                      WHERE run_id = ? AND status = 'not_started' ''', (error, identifier))
                        db.execute('''UPDATE runs SET status = 'failed', ended_at = ?, duration_seconds = ?,
                                      last_progress_at = ?, refresh_error = ? WHERE run_id = ?''',
                                   (broker.now(), elapsed() - start, broker.now(), error, identifier))
                    raise
                final_id = error = None
                try:
                    final_id = reconcile_snapshot(db, broker, purpose='reporting')
                except BrokerError as failure:
                    error = redact(str(failure), broker.private_values)
                failed = error or db.execute('''SELECT 1 FROM stages WHERE run_id = ?
                                               AND status != 'completed' ''', (identifier,)).fetchone()
                issues = db.execute("SELECT 1 FROM issues WHERE status = 'open'").fetchone()
                status = 'completed_with_errors' if failed or issues else 'completed'
                with transaction(db):
                    db.execute('''UPDATE runs SET status = ?, ended_at = ?, duration_seconds = ?, last_progress_at = ?,
                                  final_snapshot_id = ?, refresh_error = ? WHERE run_id = ?''',
                               (status, broker.now(), elapsed() - start, broker.now(), final_id, error, identifier))
                return identifier
        except sqlite3.Error:
            # Do not attempt another notebook write or broker request. The prior
            # committed progress/intent is the durable interruption evidence.
            log.error('Notebook write failed; controller stopped without further broker requests')
            raise
