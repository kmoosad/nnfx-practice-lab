"""Read-only inspection of historical qualification records and review packets.

No pass flags create broker evidence. Retained packets pin source artifacts and
committed notebook facts; this module cannot authorize execution or create A0.
"""

from datetime import datetime, timedelta
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
import math
import re

from . import qualification as q
from .broker import money
from .config import ConfigurationError, PERMITTED_PAIRS
from .evidence import canonical_json
from .ledger import account_report
from .sizing import levels


TABLES = ('account_snapshots', 'runs', 'run_invocations', 'stages', 'pair_decisions', 'trade_sets', 'trade_legs',
          'broker_attempts', 'broker_transactions', 'broker_transaction_observations', 'fills', 'ledger_entries', 'issues')


def record_tables(db):
    # Schema-2 exports remain readable before the writer's atomic migration.
    if db.execute('PRAGMA user_version').fetchone()[0] == 2:
        return tuple(name for name in TABLES if name != 'broker_transaction_observations')
    return TABLES


def fail(reason):
    raise ConfigurationError('Ordinary activation blocked: ' + reason)


def artifact(ref):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str) or not q._SHA.fullmatch(ref.get('sha256', '')):
        fail('missing sealed evidence artifact')
    raw = q.sealed_bytes(ref['path'])
    if sha256(raw).hexdigest() != ref['sha256']:
        fail('review artifact changed')
    return raw


def record_hash(db):
    # Q0 and the reviewed history are pinned without serializing the account ID.
    row = db.execute('SELECT qualification_snapshot_id, qualification_transaction_id, manifest_hash FROM notebook').fetchone()
    records = {'baseline': list(row)}
    for table in record_tables(db):
        records[table] = sorted((dict(r) for r in db.execute('SELECT * FROM ' + table)), key=canonical_json)
    return sha256(canonical_json(records).encode()).hexdigest()


def report_values(db):
    return {key: str(value) if isinstance(value, Decimal) else value
            for key, value in asdict(account_report(db, 'qualification')).items()}


def facts(db, plan):
    """Concrete record IDs, including missing requirements; useful before review."""
    count = db.execute('SELECT lookback_candles FROM notebook').fetchone()[0]
    runs = {r['run_id']: dict(r) for r in db.execute('''SELECT r.* FROM runs r JOIN run_invocations i USING(run_id)
        WHERE i.mode = 'qualification' ''') if json.loads(db.execute(
        'SELECT evidence_json FROM run_invocations WHERE run_id = ?', (r['run_id'],)).fetchone()[0]).get('source') == 'practice_execution'
        and r['code_hash'] == plan['code_sha256'] and r['config_hash'] == plan['config_sha256']
        and r['strategy_hash'] == plan['manifest_sha256']}
    sets = []
    for item in db.execute("SELECT * FROM trade_sets WHERE establishment_status = 'complete'"):
        if item['run_id'] not in runs:
            continue
        legs = [dict(r) for r in db.execute('SELECT * FROM trade_legs WHERE set_id = ? ORDER BY leg_no', (item['set_id'],))]
        decision = db.execute("SELECT sizing_json FROM pair_decisions WHERE set_id = ? AND stage = 'manage_new'", (item['set_id'],)).fetchone()
        evidence = json.loads(decision[0] or '{}') if decision else {}
        sizing = evidence.get('sizing', {})
        protection = evidence.get('establishment', {}).get('protection', {})
        if len(legs) != 2 or not sizing or len({r['broker_trade_id'] for r in legs}) != 2:
            continue
        valid = True
        for leg in legs:
            fill = db.execute("SELECT * FROM fills WHERE set_id = ? AND leg_no = ? AND effect = 'open'", (item['set_id'], leg['leg_no'])).fetchone()
            if not fill or not leg['broker_trade_id'] or leg['initial_units'] is None:
                valid = False
                break
            expected = levels(leg['entry_price'], item['entry_atr'], item['stop_distance'], item['direction'],
                              sizing['display_precision'], with_target=leg['leg_no'] == 1)
            historical = protection.get(leg['broker_trade_id'], {})
            target = db.execute('SELECT body_json FROM broker_transactions WHERE transaction_id = ?',
                                (historical.get('TAKE_PROFIT'),)).fetchone()
            target = json.loads(target[0]) if target else {}
            if (abs(money(fill['units'])) != money(leg['planned_units'])
                    or money(fill['units']) != money(leg['initial_units'])
                    or money(fill['units']) != money(sizing['signed_units'])
                    or money(fill['price']) != money(leg['entry_price'])
                    or money(leg['original_stop']) != money(expected['stop'])
                    or not leg['original_stop_order_id']
                    or historical.get('STOP_LOSS') != leg['original_stop_order_id']
                    or historical.get('open') is not True
                    or (leg['leg_no'] == 1 and (target.get('type') != 'TAKE_PROFIT_ORDER' or
                        target.get('tradeID') != leg['broker_trade_id'] or money(target.get('price')) != money(expected['target'])))
                    or (leg['leg_no'] == 2 and historical.get('TAKE_PROFIT') is not None)):
                valid = False
        reads = {r.get('purpose'): r for r in evidence.get('reads', [])}
        margins = (sizing.get('margin', {}), evidence.get('trade_2_margin', {}))
        margin_proof = (all(m.get('required') is not None and m.get('available') is not None
                            and money(m['required']) <= money(m['available']) for m in margins)
                        and all(reads.get(p, {}).get('http_status') == 200 for p in ('pre_set_margin', 'trade_2_margin')))
        if (valid and margin_proof and money(sizing['balance']) == money(runs[item['run_id']]['sizing_balance'])
                and money(sizing['risk_per_leg']) <= money(sizing['balance']) * money('0.01')):
            sets.append(dict(set_id=item['set_id'], run_id=item['run_id'], pair=item['pair'], direction=item['direction'],
                             trade_ids=[r['broker_trade_id'] for r in legs], margin_estimates=list(margins),
                             broker_margin=[reads[p]['body']['account'] for p in ('pre_set_margin', 'trade_2_margin')]))
    stops, closes = [], []
    for attempt in db.execute("SELECT * FROM broker_attempts WHERE outcome = 'confirmed'"):
        if attempt['run_id'] not in runs or not attempt['response_json'] or attempt['http_status'] not in (200, 201):
            continue
        leg = db.execute('SELECT * FROM trade_legs WHERE set_id = ? AND leg_no = ?', (attempt['set_id'], attempt['leg_no'])).fetchone()
        if not leg:
            continue
        payload = json.loads(attempt['payload_json'])
        if attempt['purpose'] == 'signal_close' and payload == {'units': 'ALL'} and leg['exit_transaction_id']:
            closes.append(attempt['attempt_id'])
        if attempt['purpose'] == 'stop_to_entry' and leg['leg_no'] == 2:
            one = db.execute('SELECT * FROM trade_legs WHERE set_id = ? AND leg_no = 1', (leg['set_id'],)).fetchone()
            if (one['exit_reason'] == 'TAKE_PROFIT_ORDER' and one['exit_transaction_id']
                    and leg['stop_to_entry_status'] == 'confirmed'
                    and money(payload.get('stopLoss', {}).get('price')) == money(leg['entry_price'])
                    and runs[attempt['run_id']]['session_date'] > one['entry_at'][:10]):
                stops.append(attempt['attempt_id'])
    final = []
    for run in runs.values():
        decisions = [dict(r) for r in db.execute('SELECT * FROM pair_decisions WHERE run_id = ?', (run['run_id'],))]
        entries = sorted((r for r in decisions if r['stage'] == 'manage_new'), key=lambda r: r['pair_order'])
        stages = [dict(r) for r in db.execute('SELECT * FROM stages WHERE run_id = ?', (run['run_id'],))]
        start = datetime.fromisoformat(run['started_at']).astimezone(q.NY)
        if (run['status'] == 'completed' and run['ended_at'] and run['duration_seconds'] is not None
                and math.isfinite(run['duration_seconds']) and run['duration_seconds'] >= 0
                and start.weekday() < 5 and (start.hour, start.minute) == (16, 50)
                and run['lookback_candles'] == count and run['final_snapshot_id'] and not run['refresh_error']
                and len(stages) == 2 and all(s['status'] == 'completed' for s in stages)
                and [r['pair'] for r in entries] == list(PERMITTED_PAIRS)
                and all(r['outcome'] in ('completed', 'skipped') for r in entries)
                and all(any(r['stage'] == stage and json.loads(r['capture_json'] or '{}').get('validation') == 'valid'
                            for r in decisions) for stage in ('manage_open', 'manage_new'))):
            final.append(run['run_id'])
    financing = [r[0] for r in db.execute("SELECT transaction_id FROM broker_transactions WHERE type = 'DAILY_FINANCING'")]
    result = dict(sets=sets, stop_to_entry_attempts=stops, targeted_close_attempts=closes,
                  final_runs=final, daily_financing_transactions=financing, record_sha256=record_hash(db))
    present = {'long_sets': any(s['direction'] == 'long' for s in sets),
               'short_sets': any(s['direction'] == 'short' for s in sets),
               'cross_currency_sets': any(s['pair'].split('-')[1] != db.execute('SELECT home_currency FROM notebook').fetchone()[0] for s in sets),
               'scheduled_stop_to_entry': bool(stops), 'targeted_closes': bool(closes),
               'final_both_stage_run': bool(final), 'daily_financing': bool(financing)}
    result['missing'] = [key for key, value in present.items() if not value]
    return result


def load_review(plan):
    review = q._document(artifact(plan.get('activation_review')))
    for key in ('account_binding_sha256', 'manifest_sha256', 'config_sha256', 'code_sha256', 'kernel', 'controller_id', 'notebook_id'):
        if review.get(key) != plan.get(key):
            fail('review identity differs: ' + key)
    authority = review.get('owner_authorization', {})
    if (authority.get('ordinary_activation') is not True or authority.get('ordinary_scheduling') is not True
            or not authority.get('statement') or not authority.get('reviewer') or not authority.get('at')
            or authority.get('reviewed_record_sha256') != review.get('record_sha256')):
        fail('final owner review and ordinary authorization are missing')
    log = artifact(review.get('offline_suite')).decode()
    match = re.search(r'Ran (\d+) tests in [\d.]+s\s+OK\s*$', log)
    passed_tests = set(re.findall(r'(?m)^(test_\S+ \(tests\.[^)]+\)) \.\.\. ok$', log))
    if not match or int(match[1]) < 427 or len(passed_tests) < 400 or '... FAIL' in log or '... ERROR' in log:
        fail('completed offline suite evidence is missing')
    acceptance = review.get('acceptance', {})
    if set(acceptance) != {f'A{i:02}' for i in range(1, 17)}:
        fail('A01–A16 review is incomplete')
    for name, case in acceptance.items():
        # Human judgments must cite observed values from protected artifacts.
        # A nonempty reference or {status: passed} is deliberately insufficient.
        if (case.get('conclusion') != 'accepted' or not case.get('explanation') or not case.get('observations')
                or not case.get('offline_tests') or not set(case['offline_tests']) <= passed_tests):
            fail(name + ' lacks a completed evidence review')
        for observation in case['observations']:
            document = q._document(artifact(observation.get('artifact')))
            pointer = observation.get('pointer')
            if not isinstance(pointer, list) or not pointer:
                fail(name + ' needs a concrete evidence location')
            value = document
            try:
                for key in pointer:
                    value = value[key]
            except (KeyError, IndexError, TypeError):
                fail(name + ' evidence location is missing')
            if (isinstance(value, bool) or value in (None, '', 'passed', 'complete', 'accepted')
                    or value != observation.get('observed')):
                fail(name + ' cites a pass flag or mismatching observation')
    return review


def verify_host(review, plan, final_run):
    boot = q._document(artifact(review.get('startup')))
    if not any(r.get('phase') == 'boot_marker' and r.get('kernel') == plan['kernel']
               and r.get('invocation_id') and r.get('logins', {}).get('known') is True
               and r['logins'].get('user_sessions') == 0 for r in boot.get('rows', [])):
        fail('startup without login evidence is incomplete')
    window = q._document(artifact(review.get('scheduled_window')))
    start = datetime.fromisoformat(final_run['started_at']).replace(second=0, microsecond=0)
    rows = window.get('rows', [])
    times = [datetime.fromisoformat(r['at']) for r in rows]
    offsets = [r.get('suspend_offset') for r in rows]
    errors = [r.get('clock_uncertainty') for r in rows]
    if (len(rows) < 2 or times != sorted(times) or times[0] > start - timedelta(minutes=10)
            or times[-1] < start + timedelta(minutes=15)
            or any(not 0 < (b-a).total_seconds() <= 45 for a, b in zip(times, times[1:]))
            or any(r.get('kernel') != plan['kernel'] or not r.get('invocation_id') for r in rows)
            or len({r.get('boot_id') for r in rows}) != 1 or not rows[0].get('boot_id')
            or not all(type(v) in (int, float) and math.isfinite(v) for v in offsets + errors)
            or min(errors) < 0 or max(errors) > .01 or max(offsets)-min(offsets) > .25):
        fail('matching current-kernel scheduled window is unproven')
    no_sessions = all(r.get('logins', {}).get('known') is True and r['logins'].get('user_sessions') == 0 for r in rows)
    if not no_sessions and (window.get('operator_intervention') != 'none' or not window.get('owner_statement')):
        fail('unattended window context remains unconfirmed')


def verify_notebook(db, plan, review):
    if record_hash(db) != review.get('record_sha256'):
        fail('qualification records changed since final review')
    if db.execute("""SELECT 1 FROM issues WHERE status != 'resolved' OR operator_id IS NULL
                     OR operator_disposition IS NULL OR resolved_at IS NULL OR disposition_evidence_json IS NULL""").fetchone():
        fail('qualification issues require evidenced operator disposition')
    observed = facts(db, plan)
    if observed['missing']:
        fail('actual qualification remains pending: ' + ', '.join(observed['missing']))
    final_id = review.get('final_run_id')
    if final_id not in observed['final_runs']:
        fail('review does not select a completed final integration run')
    run = dict(db.execute('SELECT * FROM runs WHERE run_id = ?', (final_id,)).fetchone())
    verify_host(review, plan, run)
    report = report_values(db)
    dashboard = q._document(artifact(review.get('dashboard_comparison')))
    if (report['snapshot_id'] != run['final_snapshot_id'] or dashboard.get('account_report') != report
            or dashboard.get('run_id') != final_id or dashboard.get('method') != 'GET'
            or dashboard.get('http_status') != 200 or not dashboard.get('owner_lan_confirmation')):
        fail('traded dashboard comparison differs from the reconciled notebook')
    html = artifact(dashboard.get('html')).decode()
    if any(s not in html for s in (final_id, report['balance'], *[t for s in observed['sets'] for t in s['trade_ids']])):
        fail('retained dashboard does not contain reviewed run, balance and trades')
    captures = review.get('runs', {})
    needed = {final_id} | {s['run_id'] for s in observed['sets']}
    needed |= {r[0] for r in db.execute("SELECT DISTINCT run_id FROM broker_attempts WHERE purpose IN ('stop_to_entry', 'signal_close') AND outcome = 'confirmed'")}
    for run_id in needed:
        refs = captures.get(run_id, {})
        claim = q._document(artifact(refs.get('claim')))
        if claim.get('run_id') != run_id or not q._SHA.fullmatch(claim.get('plan_sha256', '')):
            fail('durable session claim is missing')
        raw = artifact(refs.get('captures'))
        rows = [q._document(line) for line in raw.splitlines()]
        if not rows or any(row.get('source') != 'practice_execution' for row in rows):
            fail('simulated or missing broker captures')
        for attempt in db.execute('SELECT response_json FROM broker_attempts WHERE run_id = ?', (run_id,)):
            response = json.loads(attempt[0] or '{}')
            if response and not any({k: v for k, v in row.items() if k != 'source'} == response for row in rows):
                fail('attempt response lacks matching retained broker evidence')
    return observed
