"""Observational Flask views. Only the public registry and read-only notebooks enter here."""

import argparse
from datetime import UTC, datetime, time, timedelta
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


def number(value, *, signed=False):
    if value is None:
        return 'Unavailable'
    value = Decimal(value)
    return format(value, '+f' if signed else 'f')


def tone(value):
    if value is None:
        return ''
    return 'win' if Decimal(value) > 0 else 'loss' if Decimal(value) < 0 else ''


def age(value, now):
    if value is None:
        return 'Unavailable'
    seconds = max(0, int((now - _instant(value)).total_seconds()))
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
            runs = db.execute('''SELECT runs.run_id, status, started_at, ended_at, duration_seconds, session_date,
                                 last_progress_at, refresh_error, run_invocations.mode
                                 FROM runs LEFT JOIN run_invocations USING (run_id)
                                 ORDER BY started_at DESC, runs.rowid DESC''').fetchall()
            view['runs'] = []
            for row in runs:
                run = dict(row)
                run['stages'] = []
                for child in db.execute('''SELECT stage, status, started_at, ended_at, duration_seconds,
                    current_step, current_pair, reconciliation_progress_json, expected_pair_count, failure_summary
                    FROM stages WHERE run_id = ? ORDER BY CASE stage WHEN 'manage_open' THEN 1 ELSE 2 END''',
                    (row['run_id'],)):
                    stage = dict(child)
                    stage.update(dict(pair_progress(db, row['run_id'], child['stage'])))
                    run['stages'].append(stage)
                run['decisions'] = [dict(d) for d in db.execute('''SELECT stage, pair, outcome, reason, ended_at
                    FROM pair_decisions WHERE run_id = ? AND (outcome = 'failed' OR outcome IS NULL)
                    ORDER BY stage, pair_order''', (row['run_id'],))]
                view['runs'].append(run)
            view['latest_run'] = view['runs'][0] if view['runs'] else None
            view['issues'] = [dict(r) for r in db.execute('''SELECT issue_id, pair, code, status, set_id, leg_no,
                attempt_id, first_observed_at, last_observed_at, operator_disposition, resolved_at
                FROM issues ORDER BY status, last_observed_at DESC''')]
            refreshes = [dict(r) for r in db.execute('''SELECT snapshot_id, purpose, requested_at, responded_at,
                reconciliation_status, reconciliation_error FROM account_snapshots WHERE purpose != 'sizing_balance'
                ORDER BY requested_at DESC, rowid DESC''')]
            view['refresh_problem'] = next((r for r in refreshes if r['reconciliation_status'] != 'reconciled'
                and (report is None or _instant(r['requested_at']) >= _instant(report.refreshed_at))), None)
            view['refresh_age'] = age(report.refreshed_at if report else None, now)
            view['expected_launch'] = latest_launch(now).astimezone(UTC).isoformat()
            view['schedule_stale'] = report is None or _instant(report.refreshed_at) < latest_launch(now)
            view['stale'] = (view['schedule_stale'] or view['refresh_problem'] is not None
                             or bool(view['latest_run'] and view['latest_run']['refresh_error']))
            if detail:
                view['journal'] = _journal(db, binding, boundary)
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
    app.jinja_env.filters.update(ny=ny_time, number=number, tone=tone)

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
