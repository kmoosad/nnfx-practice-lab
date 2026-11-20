"""Observational Flask views. Only the public registry and read-only notebooks enter here."""

import argparse
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, localcontext
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from flask import Flask, abort, render_template

from .config import ConfigurationError, read_registry
from .ledger import account_report, trade_journal, transaction_key
from .notebook import open_readonly, pair_progress


NEW_YORK = ZoneInfo('America/New_York')


def _instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def ny_time(value):
    if value is None:
        return 'Unavailable'
    # datetime truncates nanoseconds; retain the broker's complete fraction in display.
    match = re.search(r'\.([0-9]+)', value)
    fraction = '.' + match[1] if match else ''
    local = _instant(value).astimezone(NEW_YORK)
    return local.strftime('%Y-%m-%d %H:%M:%S') + fraction + local.strftime(' %Z %z')


def ny_short(value):
    if value is None:
        return 'Unavailable'
    return _instant(value).astimezone(NEW_YORK).strftime('%d %b %Y · %H:%M:%S %Z %z')


def duration(value):
    if value is None:
        return 'Unavailable'
    return '<0.1 s' if 0 < value < 0.1 else f'{value:.1f} s'


def session_date(value):
    return date.fromisoformat(value).strftime('%d %b %Y')


def number(value, *, signed=False, grouped=False):
    if value is None:
        return 'Unavailable'
    value = Decimal(value)
    return format(value, ('+' if signed else '') + (',' if grouped else '') + 'f')


def tone(value):
    if value is None:
        return ''
    return 'win' if Decimal(value) > 0 else 'loss' if Decimal(value) < 0 else ''


def age(value, now, *, compact=False):
    if value is None:
        return 'Unavailable'
    seconds = max(0, int((now - _instant(value)).total_seconds()))
    if compact:
        parts = [(seconds // 86400, 'd'), (seconds % 86400 // 3600, 'h'),
                 (seconds % 3600 // 60, 'm'), (seconds % 60, 's')]
        return ' '.join([f'{amount}{unit}' for amount, unit in parts if amount][:2]) or '0s'
    return f'{seconds // 86400}d {seconds % 86400 // 3600}h {seconds % 3600 // 60}m {seconds % 60}s'


def latest_launch(now):
    """Most recent weekday 16:50 New York, including DST and weekend boundaries."""
    local = now.astimezone(NEW_YORK)
    day = local.date()
    if local.time() < time(16, 50):
        day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return datetime.combine(day, time(16, 50), NEW_YORK)


def _period(transaction_id, binding):
    if transaction_id is None:
        return 'Unclassified'
    key = transaction_key(transaction_id)
    a0, q0 = binding['activation_transaction_id'], binding['qualification_transaction_id']
    if a0 is not None and key > transaction_key(a0):
        return 'Ordinary'
    if q0 is not None and key > transaction_key(q0):
        return 'Qualification'
    return 'Before Q0' if q0 else 'Unclassified'


def _pip_location(db, run_id, pair):
    row = db.execute('SELECT sizing_json FROM pair_decisions WHERE run_id = ? AND stage = ? AND pair = ?',
                     (run_id, 'manage_new', pair)).fetchone()
    if row is None or row[0] is None:
        return None
    try:
        evidence = json.loads(row[0])
    except ValueError:
        return None
    if not isinstance(evidence, dict):
        return None
    for read in evidence.get('reads', []):
        if read.get('purpose') != 'instrument_limits':
            continue
        for instrument in read.get('body', {}).get('instruments', []):
            location = instrument.get('pipLocation')
            if instrument.get('name') == pair.replace('-', '_') and type(location) is int and -20 <= location <= 20:
                return location
    return None


def _journal(db, binding, boundary):
    rows = db.execute('''SELECT trade_legs.set_id, leg_no, broker_trade_id, planned_units,
                         initial_units, current_units, broker_state, broker_state_at,
                         broker_state_transaction_id, entry_price, entry_at, original_stop,
                         current_stop, intended_target, confirmed_target, stop_to_entry_status,
                         exit_price, exit_at, exit_reason, trade_sets.pair, trade_sets.direction,
                         trade_sets.run_id, trade_sets.establishment_status, run_invocations.mode
                         FROM trade_legs JOIN trade_sets USING (set_id)
                         LEFT JOIN run_invocations USING (run_id) ORDER BY trade_sets.rowid, leg_no''').fetchall()
    journal = []
    for row in rows:
        leg = dict(row)
        leg.update(pips=None, trading_pl=None, fills=[], ledger=[], after_snapshot=False)
        leg['pip_location'] = _pip_location(db, row['run_id'], row['pair'])
        if row['broker_trade_id'] is not None:
            leg.update(trade_journal(db, row['broker_trade_id'], leg['pip_location'], boundary=boundary))
        leg['after_snapshot'] = leg['after_snapshot'] or any(
            item['after_snapshot'] for item in (*leg['fills'], *leg['ledger']))
        opening = next((f['transaction_id'] for f in leg['fills'] if f['effect'] == 'open'), None)
        # Legacy component records may lack an invocation; infer only from actual fills.
        leg['period'] = row['mode'].title() if row['mode'] else _period(opening, binding)
        for category, label in (('financing', 'financing'), ('commission', 'commission'), ('other_charge', 'other_charges')):
            amounts = [Decimal(e['amount']) for e in leg['ledger'] if e['category'] == category]
            leg[label] = sum(amounts, Decimal(0)) if amounts else None
        # Final outcomes are deliberately absent on open/partly reduced legs.
        if row['broker_state'] != 'closed':
            leg.update(exit_at=None, exit_price=None, exit_reason=None, pips=None, trading_pl=None)
        journal.append(leg)
    return journal


def _read_run(db, run_id):
    """Load the selected run's details only; callers own the read transaction."""
    row = db.execute('''SELECT runs.run_id, status, started_at, ended_at, duration_seconds,
        session_date, last_progress_at, refresh_error, run_invocations.mode
        FROM runs LEFT JOIN run_invocations USING (run_id) WHERE runs.run_id = ?''',
        (run_id,)).fetchone()
    if row is None:
        return None
    run = dict(row)
    run['stages'] = []
    for child in db.execute('''SELECT stage, status, started_at, ended_at, duration_seconds,
        current_step, current_pair, reconciliation_progress_json, expected_pair_count, failure_summary
        FROM stages WHERE run_id = ? ORDER BY CASE stage WHEN 'manage_open' THEN 1 ELSE 2 END''',
        (run_id,)):
        stage = dict(child)
        stage.update(dict(pair_progress(db, run_id, child['stage'])))
        stage['skip_reasons'] = [dict(r) for r in db.execute('''
            SELECT reason, count(*) AS count FROM pair_decisions
            WHERE run_id = ? AND stage = ? AND outcome = 'skipped'
            GROUP BY reason ORDER BY count(*) DESC, reason''', (run_id, child['stage']))]
        stage['reconciled'] = False
        if child['stage'] == 'manage_open' and child['reconciliation_progress_json']:
            try:
                reconciliation = json.loads(child['reconciliation_progress_json'])
            except ValueError:
                reconciliation = None
            if isinstance(reconciliation, dict) and isinstance(reconciliation.get('snapshot_id'), str):
                stage['reconciled'] = db.execute('''SELECT 1 FROM account_snapshots
                    WHERE snapshot_id = ? AND reconciliation_status = 'reconciled' ''',
                    (reconciliation.get('snapshot_id'),)).fetchone() is not None
        run['stages'].append(stage)
    run['decisions'] = [dict(d) for d in db.execute('''SELECT stage, pair, outcome, reason, ended_at
        FROM pair_decisions WHERE run_id = ? AND (outcome = 'failed' OR outcome IS NULL)
        ORDER BY stage, pair_order''', (run_id,))]
    run['needs_attention'] = (run['status'] != 'completed' or not run['ended_at']
        or bool(run['refresh_error']) or bool(run['decisions'])
        or any(s['status'] != 'completed' or not s['ended_at'] or s['failure_summary']
               for s in run['stages']))
    entry_stage = next((s for s in run['stages'] if s['stage'] == 'manage_new'), None)
    run['no_new_entries'] = bool(entry_stage and entry_stage['status'] == 'completed'
        and entry_stage['ended_at'] and entry_stage['expected_pair_count']
        and entry_stage['finished'] == entry_stage['skipped'] == entry_stage['expected_pair_count']
        and db.execute('SELECT 1 FROM trade_sets WHERE run_id = ? LIMIT 1', (run_id,)).fetchone() is None)
    return run


def read_run(root, experiment, run_id):
    """Read one run from its registered notebook without loading account/history content."""
    view = dict(experiment=experiment, error=None, run=None)
    try:
        with open_readonly(root, experiment) as db:
            db.execute('BEGIN')
            view['run'] = _read_run(db, run_id)
            db.rollback()
    except (OSError, sqlite3.Error, ConfigurationError, ValueError, KeyError, TypeError):
        view['error'] = 'Notebook unavailable: missing, unreadable or incompatible records.'
    return view


def read_view(root, experiment, now, *, detail=False):
    """Materialize one consistent committed view, then release the WAL reader."""
    view = dict(experiment=experiment, error=None)
    try:
        with open_readonly(root, experiment) as db, localcontext(prec=80):
            db.execute('BEGIN')
            binding = db.execute('''SELECT controller_id, notebook_id, strategy_version, manifest_json,
                manifest_hash, lookback_candles, home_currency, qualification_snapshot_id,
                qualification_transaction_id, activation_snapshot_id, activation_transaction_id, activated_at
                FROM notebook''').fetchone()
            view['binding'] = dict(binding)
            view['manifest'] = json.loads(binding['manifest_json'])
            view['reports'] = {p: account_report(db, p) for p in ('ordinary', 'qualification')}
            report = view['reports']['ordinary'] or view['reports']['qualification']
            view['report'] = report
            boundary = report.boundary if report else None
            # History contains summary metadata only. Stages, pair reasons and
            # reconciliation records are fetched only for the run being viewed.
            view['runs'] = [dict(r) for r in db.execute('''SELECT runs.run_id, status, started_at,
                ended_at, duration_seconds, session_date, run_invocations.mode,
                coalesce(refresh_error, '') != '' AS refresh_failed,
                (status != 'completed' OR ended_at IS NULL OR coalesce(refresh_error, '') != ''
                 OR EXISTS (SELECT 1 FROM stages s WHERE s.run_id = runs.run_id
                    AND (s.status != 'completed' OR s.ended_at IS NULL OR coalesce(s.failure_summary, '') != ''))
                 OR EXISTS (SELECT 1 FROM pair_decisions d WHERE d.run_id = runs.run_id
                    AND (d.outcome = 'failed' OR d.outcome IS NULL))) AS needs_attention
                FROM runs LEFT JOIN run_invocations USING (run_id)
                ORDER BY started_at DESC, runs.rowid DESC''')]
            view['latest_run'] = None
            if view['runs']:
                view['latest_run'] = _read_run(db, view['runs'][0]['run_id'])
                view['runs'][0] = view['latest_run']
            view['issues'] = [dict(r) for r in db.execute('''SELECT issue_id, pair, code, status, set_id, leg_no,
                attempt_id, first_observed_at, last_observed_at, operator_disposition, resolved_at
                FROM issues ORDER BY status, last_observed_at DESC''')]
            refreshes = [dict(r) for r in db.execute('''SELECT snapshot_id, purpose, requested_at, responded_at,
                reconciliation_status, reconciliation_error FROM account_snapshots WHERE purpose != 'sizing_balance'
                ORDER BY requested_at DESC, rowid DESC''')]
            view['refresh_problem'] = next((r for r in refreshes if r['reconciliation_status'] != 'reconciled'
                and (report is None or _instant(r['requested_at']) >= _instant(report.refreshed_at))), None)
            view['refresh_age'] = age(report.refreshed_at if report else None, now)
            view['refresh_age_short'] = age(report.refreshed_at if report else None, now, compact=True)
            view['expected_launch'] = latest_launch(now).astimezone(UTC).isoformat()
            view['schedule_stale'] = report is None or _instant(report.refreshed_at) < latest_launch(now)
            view['stale'] = (view['schedule_stale'] or view['refresh_problem'] is not None
                             or bool(view['latest_run'] and view['latest_run']['refresh_error']))
            if detail:
                view['journal'] = _journal(db, binding, boundary)
                groups = {}
                for leg in view['journal']:
                    group = groups.setdefault(leg['set_id'], dict(set_id=leg['set_id'], pair=leg['pair'],
                        direction=leg['direction'], establishment_status=leg['establishment_status'], legs=[]))
                    group['legs'].append(leg)
                view['journal_groups'] = list(reversed(groups.values()))
                for group in view['journal_groups']:
                    group['finished'] = all(leg['broker_state'] in ('closed', 'not_opened') for leg in group['legs'])
                    group['entry_at'] = next((leg['entry_at'] for leg in group['legs'] if leg['entry_at']), None)
                activity = [dict(r) for r in db.execute('''SELECT ledger_entries.transaction_id, component_key,
                    amount, category, broker_trade_id, source_field, posted, broker_transactions.broker_at
                    FROM ledger_entries JOIN broker_transactions USING (transaction_id)''')]
                activity.sort(key=lambda r: (transaction_key(r['transaction_id']), r['component_key']))
                for row in activity:
                    row['after_snapshot'] = boundary is not None and transaction_key(row['transaction_id']) > transaction_key(boundary)
                    row['period'] = _period(row['transaction_id'], binding)
                view['activity'] = activity
                view['attempts'] = [dict(r) for r in db.execute('''SELECT attempt_id, run_id, stage, pair, set_id, leg_no,
                    purpose, method, path, prepared_at, responded_at, http_status, request_id, broker_order_id,
                    broker_trade_id, broker_transaction_id, outcome, error FROM broker_attempts ORDER BY prepared_at''')]
            db.rollback()
    except (OSError, sqlite3.Error, ConfigurationError, ValueError, KeyError, TypeError):
        # File paths and exception text do not belong in an operator-facing response.
        view = dict(experiment=experiment, error='Notebook unavailable: missing, unreadable or incompatible records.')
    return view


def create_app(root=None, *, now=None):
    root = Path(root or Path.cwd()).resolve()
    clock = now or (lambda: datetime.now(UTC))
    registry = read_registry(root)
    notebooks = {e.notebook_id: e for e in registry.values()}
    app = Flask(__name__, static_folder=None)
    app.jinja_env.filters.update(ny=ny_time, ny_short=ny_short, duration=duration,
                                session_date=session_date, number=number, tone=tone)

    @app.after_request
    def committed_response(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    def views(detail=False):
        instant = clock()
        return [read_view(root, e, instant, detail=detail) for e in registry.values()]

    @app.get('/controllers')
    def controllers():
        return render_template('controllers.html', title='Controller', views=views())

    @app.get('/controllers/<controller_id>/runs/<run_id>')
    def controller_run(controller_id, run_id):
        experiment = registry.get(controller_id)
        if experiment is None:
            abort(404)
        view = read_run(root, experiment, run_id)
        if view['error'] is None and view['run'] is None:
            abort(404)
        return render_template('controller_run.html', title='Run details', view=view), 503 if view['error'] else 200

    @app.get('/notebooks')
    def notebook_list():
        return render_template('notebooks.html', title='Notebooks', views=views())

    @app.get('/notebooks/<notebook_id>')
    def notebook_detail(notebook_id):
        experiment = notebooks.get(notebook_id)
        if experiment is None:
            abort(404)
        return render_template('notebook.html', title=experiment.notebook_name,
                               view=read_view(root, experiment, clock(), detail=True))

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8878)
    args = parser.parse_args()
    # Direct entry point never invokes Flask CLI dotenv discovery or a reloader.
    create_app(args.root).run(host=args.host, port=args.port, debug=False, use_reloader=False, load_dotenv=False)


if __name__ == '__main__':
    main()
