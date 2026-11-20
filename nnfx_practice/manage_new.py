"""Stage 2: each candidate commits before the next brief-ordered pair."""

from time import monotonic

from .broker import BrokerError
from .config import PERMITTED_PAIRS
from .entry import enter_candidate
from .evidence import redact
from .notebook import pair_progress, transaction


def manage_new(db, broker, *, run_id, elapsed=monotonic):
    start = elapsed()
    with transaction(db):
        changed = db.execute('''UPDATE stages SET status = 'running', started_at = ?, current_step = '4.2'
            WHERE run_id = ? AND stage = 'manage_new' AND status = 'not_started'
            AND EXISTS (SELECT 1 FROM runs WHERE runs.run_id = stages.run_id
                        AND status = 'running' AND sizing_balance IS NOT NULL)
            AND EXISTS (SELECT 1 FROM stages s WHERE s.run_id = stages.run_id AND s.stage = 'manage_open'
                        AND s.status IN ('completed', 'completed_with_errors'))''', (broker.now(), run_id))
        if changed.rowcount != 1:
            raise ValueError('Entry loop requires finished management and a new stage with its sizing balance')
    try:
        for pair in PERMITTED_PAIRS:
            with transaction(db):
                db.execute("UPDATE stages SET current_step = '4.2', current_pair = ? WHERE run_id = ? AND stage = 'manage_new'",
                           (pair, run_id))
                db.execute('UPDATE runs SET last_progress_at = ? WHERE run_id = ?', (broker.now(), run_id))
            enter_candidate(db, broker, run_id=run_id, pair=pair)
    except BrokerError as failure:
        with transaction(db):
            db.execute('''UPDATE stages SET status = 'failed', ended_at = ?, duration_seconds = ?, failure_summary = ?
                          WHERE run_id = ? AND stage = 'manage_new' ''',
                       (broker.now(), elapsed() - start, redact(str(failure), broker.private_values), run_id))
        raise
    failures = pair_progress(db, run_id, 'manage_new')['failed']
    status = 'completed_with_errors' if failures else 'completed'
    with transaction(db):
        db.execute('''UPDATE stages SET status = ?, ended_at = ?, duration_seconds = ?, current_step = '4.5',
                      current_pair = NULL, failure_summary = ? WHERE run_id = ? AND stage = 'manage_new' ''',
                   (status, broker.now(), elapsed() - start, f'{failures} failed pairs' if failures else None, run_id))
        db.execute('UPDATE runs SET last_progress_at = ? WHERE run_id = ?', (broker.now(), run_id))
    return status
