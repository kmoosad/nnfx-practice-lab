"""Arm one dated M10 continuation after a reviewed, completed no-entry session.

Preserves Q0, all notebook history and old claims. Sends one GET-only account
clearance under maintenance; only the dated existing controller can send orders.
This narrow path rejects any prior entry/attempt/issue and never activates A0.
"""

import argparse
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import pwd
import sqlite3
import stat
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CODE, DATA = Path('/opt/nnfx-practice'), Path('/var/lib/nnfx-practice')
CONTROLLER = 'practice-a'
SERVICE = 'nnfx-practice@practice-a.service'


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arm = helper('m10_initial_armer', ROOT / 'tests/arm_m10_qualification.py')
prep = helper('m10_account_preparation', ROOT / 'tests/check_m10_preparation.py')


def validate_review(review, old):
    n = review.get('notebook', {})
    tables = n.get('tables', {})
    rows = tables.get('notebook', [])
    runs = tables.get('runs', [])
    if (review.get('classification') != 'protected read-only evidence collection'
            or review.get('status') != 'collected' or review.get('collection_errors') != []
            or review.get('notebook_files_unchanged') is not True or n.get('query_only') is not True
            or n.get('account_binding_sha256') != old['account_binding_sha256'] or len(rows) != 1
            or not runs or runs[-1].get('run_id') != old['run_id']
            or any(row.get('status') != 'completed' or not row.get('ended_at')
                   or row.get('code_hash') != old['code_sha256'] or row.get('config_hash') != old['config_sha256']
                   or row.get('strategy_hash') != old['manifest_sha256'] for row in runs)
            or any(row.get('mode') != 'qualification' or row.get('evidence_json', {}).get('source') != 'practice_execution'
                   for row in tables.get('run_invocations', []))
            or len(tables.get('run_invocations', [])) != len(runs)):
        raise ValueError('Expected the reviewed actual completed qualification history for this old plan')
    row = rows[0]
    report = n.get('qualification_account_report')
    if (row.get('manifest_hash') != old['manifest_sha256']
            or not row.get('qualification_snapshot_id')
            or row.get('qualification_transaction_id') != row.get('imported_through_transaction_id')
            or any(row.get(key) is not None for key in ('activated_at', 'activation_snapshot_id', 'activation_transaction_id'))
            or n.get('ordinary_account_report_available') is not False):
        raise ValueError('Q0/cursor/binding changed or ordinary activation exists; preserve it')
    if (not isinstance(report, dict) or report.get('period') != 'qualification'
            or report.get('opening_snapshot_id') != row['qualification_snapshot_id']
            or report.get('boundary') != row['imported_through_transaction_id']
            or not report.get('snapshot_id') or report['snapshot_id'] != runs[-1].get('final_snapshot_id')
            or report.get('balance') != runs[-1].get('sizing_balance')):
        raise ValueError('Final reconciled qualification report differs from the reviewed no-entry run')
    for name in ('trade_sets', 'trade_legs', 'broker_attempts', 'issues', 'broker_transactions', 'fills', 'ledger_entries'):
        if name not in tables or tables[name]:
            raise ValueError('Prior execution/attempt/issue activity requires review; this path continues no-entry sessions only')
    if (len(tables.get('stages', [])) != 2 * len(runs)
            or any(row.get('status') != 'completed' for row in tables['stages'])
            or len(tables.get('pair_decisions', [])) != 28 * len(runs)
            or any(row.get('stage') != 'manage_new' or row.get('outcome') != 'skipped'
                   or row.get('c1_json', {}).get('direction') != 'no_event' or row.get('atr_valid') != 1
                   or row.get('capture_json', {}).get('validation') != 'valid'
                   for row in tables['pair_decisions'])):
        raise ValueError('Every reviewed session must have its complete, valid no-entry decisions')
    captures = review.get('broker_captures', {})
    if (captures.get('malformed_lines') != [] or not captures.get('rows')
            or any(row.get('method') != 'GET' or row.get('http_status') != 200
                   or row.get('source') != 'practice_execution' for row in captures['rows'])):
        raise ValueError('Uncertain or mutation captures cannot use this no-entry continuation')


def audit_current(review):
    """Require unchanged current history; never open a writer or recreate a sidecar."""
    from nnfx_practice.config import read_registry
    experiment = read_registry(DATA)[CONTROLLER]
    path = experiment.notebook_path(DATA)
    writer = pwd.getpwnam('nnfx-run')
    folder = path.parent.lstat()
    if (not stat.S_ISDIR(folder.st_mode) or folder.st_uid != writer.pw_uid or folder.st_gid != writer.pw_gid
            or folder.st_mode & 0o077 != 0o050 or not folder.st_mode & stat.S_ISGID):
        raise ValueError('Actual notebook directory permissions differ')
    for item in (path, Path(str(path) + '-wal'), Path(str(path) + '-shm')):
        info = item.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != writer.pw_uid
                or info.st_gid != writer.pw_gid or stat.S_IMODE(info.st_mode) != 0o640):
            raise ValueError('Existing shared notebook/WAL/SHM permissions are required; nothing is created')
    collector_path = ROOT / 'var/verification/m10-review-20261120/collect_review.py'
    if sha256(collector_path.read_bytes()).hexdigest() != review['source_sha256']:
        raise ValueError('Reviewed read-only collector source changed')
    collector = helper('m10_readonly_collector', collector_path)
    current, _ = collector.notebook_export(path)
    if current != review['notebook']:
        raise ValueError('Current notebook differs from the reviewed history; preserve and investigate')
    return current


def renewed_plan(old, *, slot, run_id, host, controls):
    candidate = deepcopy(old)
    candidate.update(enabled=False, run_id=run_id, dispatch_at=slot,
                     boot_id=host[0], kernel=host[1], phase='initial_account_path_continuation')
    candidate['evidence']['m09_controller_controls'] = dict(status='passed', path='pending protected copy',
                                                          sha256=sha256(controls).hexdigest())
    arm.future_slot(candidate)
    return candidate


def check_triggers(old):
    from nnfx_practice import qualification as q
    service = arm.properties(SERVICE)
    if service.get('ActiveState') != 'inactive' or service.get('Job') not in ('', '0'):
        raise ValueError('Controller active/pending; never stop it to continue qualification')
    triggered = q._command('systemctl', 'show', SERVICE, '--property=TriggeredBy')
    old_timer = 'nnfx-m10-qualify-' + old['run_id'] + '.timer'
    for unit in triggered.get('TriggeredBy', '').split():
        state = arm.properties(unit)
        idle = state.get('ActiveState') == 'inactive'
        elapsed_old = (unit == old_timer and state.get('SubState') == 'elapsed'
                       and state.get('NextElapseUSecRealtime') == '')
        if state.get('Job') not in ('', '0') or not (idle or elapsed_old):
            raise ValueError('Another controller trigger can still dispatch; preserve and review')


def continue_session(args):
    from nnfx_practice import qualification as q
    review_raw = args.previous_review.read_bytes()
    review = q._document(review_raw)
    plan_path = q.PLAN_DIRECTORY / (CONTROLLER + '.json')
    original = q.sealed_bytes(plan_path)
    old = q._document(original)
    if (old.get('controller_id') != CONTROLLER or old.get('notebook_id') != 'notebook-a'
            or old.get('host') != q.PRACTICE_HOST or old.get('version') != 1
            or sha256(original).hexdigest() != review.get('protected_plan', {}).get('sha256')):
        raise ValueError('The old protected plan differs from the reviewed actual session')
    old_slot = datetime.fromisoformat(old['dispatch_at'])
    if old_slot + timedelta(minutes=1) >= datetime.now(UTC):
        raise ValueError('The reviewed previous dispatch must be past; never overlap or catch up')
    validate_review(review, old)
    if old['code_sha256'] != q.code_identity() or old['config_sha256'] != sha256((DATA / 'config.toml').read_bytes()).hexdigest():
        raise ValueError('Application/config changed; review affected qualification before continuation')
    controls_raw = args.system_report.read_bytes()
    controls = q._document(controls_raw)
    boot, kernel = q.host_identity()
    if (controls.get('host_context') != dict(boot_id=boot, kernel=kernel)
            or controls.get('cleanup_errors') != [] or controls.get('existing_notebooks_preserved_mode') is not True
            or controls.get('results', {}).get('fixture_checks_passed') is not True
            or controls['results'].get('actual_notebook_files_preserved') is not True):
        raise ValueError('Current-boot successful system fixtures with notebook preservation are required')
    for name, digest in controls.get('source_hashes', {}).items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('System fixture source/unit changed since its observed pass')
    for name, digest in q.code_hashes().items():
        if any(sha256((base / name).read_bytes()).hexdigest() != digest for base in (ROOT, CODE)):
            raise ValueError('Checkout/copied/installed application differs')
    q.host_controls(CONTROLLER, 'inspect')
    check_triggers(old)
    current = audit_current(review)
    old_claim = DATA / 'var/qualification' / CONTROLLER / (old_slot.astimezone(arm.NY).date().isoformat() + '.claim')
    if old_claim.is_symlink() or sha256(old_claim.read_bytes()).hexdigest() != review['session_claim']['sha256']:
        raise ValueError('Previous claim differs; never delete or replay it')
    identifier = 'm10-continuation-' + uuid4().hex[:12]
    candidate = renewed_plan(old, slot=args.dispatch_at, run_id='m10-' + uuid4().hex,
                             host=(boot, kernel), controls=controls_raw)
    target_claim = arm.claim_path(candidate)
    name, timer_body = arm.timer_definition(candidate)
    timer_path = arm.UNITS / name
    if timer_path.exists() or timer_path.is_symlink():
        raise ValueError('New timer already exists; no automatic rearming')
    documents = q._evidence(old)
    documents['m09_controller_controls'] = controls
    q.validate_evidence(candidate, documents)
    output = ROOT / 'var/verification/m10-continuation'
    output.mkdir(exist_ok=True)
    owner = (ROOT / 'config.toml').stat()
    writer = pwd.getpwnam('nnfx-run')
    result = dict(at=datetime.now(UTC).isoformat(), status='pending', phase='initial_account_path_continuation',
        classification='dated M10 qualification continuation after reviewed no-entry history; not ordinary activation',
        previous_review=str(args.previous_review), previous_review_sha256=sha256(review_raw).hexdigest(),
        old_plan_sha256=sha256(original).hexdigest(), old_run_id=old['run_id'], run_id=candidate['run_id'],
        dispatch_at=candidate['dispatch_at'], dispatch_melbourne=datetime.fromisoformat(candidate['dispatch_at']).astimezone(ZoneInfo('Australia/Melbourne')).isoformat(),
        system_report=str(args.system_report), system_report_sha256=sha256(controls_raw).hexdigest(),
        source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        q0_snapshot_id=current['tables']['notebook'][0]['qualification_snapshot_id'],
        cursor=current['tables']['notebook'][0]['imported_through_transaction_id'],
        ordinary_trading_enabled=False, ordinary_activation_performed=False, practice_execution_qualified=False,
        notebook_writes=False, broker_requests_sent_by_continuation=0, broker_mutations_sent_by_continuation=0)

    def record(suffix, document):
        prep.write_new(output / (identifier + suffix + '.json'), document,
                       uid=owner.st_uid, gid=owner.st_gid, mode=0o600)

    record('-intent', result)
    created = replacement_attempted = start_attempted = False
    our_hashes = set()
    try:
        staged = CODE / 'verification' / identifier
        staged.mkdir(mode=0o755)
        staged.chmod(0o755)
        worker = staged / 'check.py'
        worker.write_bytes((ROOT / 'tests/check_m10_preparation.py').read_bytes())
        worker.chmod(0o644)
        report = current['qualification_account_report']
        settings = dict(account_binding_sha256=old['account_binding_sha256'], manifest_sha256=old['manifest_sha256'],
                        transaction_boundary=report['boundary'], balance=report['balance'])
        settings_path = staged / 'read-settings.json'
        prep.write_new(settings_path, settings, uid=0, gid=writer.pw_gid, mode=0o640)
        result['broker_requests_sent_by_continuation'] = 'unknown; inspect account-check evidence'
        clearance = prep.run_worker(worker, settings_path)
        record('-account', clearance)
        result['broker_requests_sent_by_continuation'] = 1
        if (clearance.get('status') != 'passed' or clearance.get('mutations_sent') != 0
                or clearance.get('source') != 'practice_get'):
            raise ValueError('Fresh account clearance is pending; no plan/timer enabled')
        q.host_controls(CONTROLLER, 'inspect')
        audit_current(review)
        check_triggers(old)
        arm.future_slot(candidate)
        arm.claim_path(candidate)
        destination = q.PLAN_DIRECTORY / 'evidence' / identifier
        prep.root_directory(destination, writer.pw_gid)
        for label, body in [('previous-plan', original), ('previous-review', review_raw),
                            ('m09_controller_controls', controls_raw),
                            ('initial_account_resolution', (json.dumps(clearance, indent=2) + '\n').encode())]:
            path = destination / (label + '.json')
            arm.write_new(path, body, uid=0, gid=writer.pw_gid, mode=0o640)
            if label in ('m09_controller_controls', 'initial_account_resolution'):
                candidate['evidence'][label] = dict(status='passed', path=str(path), sha256=sha256(body).hexdigest())
        candidate['previous_session_review'] = dict(path=str(destination / 'previous-review.json'), sha256=sha256(review_raw).hexdigest())
        documents['initial_account_resolution'] = clearance
        q.validate_evidence(candidate, documents)
        disabled = (json.dumps(candidate, indent=2) + '\n').encode()
        disabled_hash = sha256(disabled).hexdigest()
        our_hashes.add(disabled_hash)
        replacement_attempted = True
        arm.replace_plan(plan_path, sha256(original).hexdigest(), disabled)
        q.load_permit(DATA, CONTROLLER, 'inspect')
        arm.write_new(timer_path, timer_body.encode(), uid=0, gid=0, mode=0o644)
        created = True
        arm.command('systemd-analyze', 'verify', str(timer_path))
        arm.command('systemctl', 'daemon-reload')
        active = (json.dumps(dict(candidate, enabled=True), indent=2) + '\n').encode()
        active_hash = sha256(active).hexdigest()
        our_hashes.add(active_hash)
        arm.replace_plan(plan_path, disabled_hash, active)
        q.load_permit(DATA, CONTROLLER, 'inspect')
        q.host_controls(CONTROLLER, 'inspect')
        arm.future_slot(candidate)
        arm.claim_path(candidate)
        start_attempted = True
        arm.command('systemctl', 'start', name)
        waiting = arm.properties(name)
        arm.validate_waiting_timer(waiting, candidate)
        q.host_controls(CONTROLLER, 'inspect')
        result.update(status='armed', timer=name, qualification_timer_state=waiting,
                      active_plan_sha256=active_hash, archived_previous_plan=str(destination / 'previous-plan.json'),
                      ordinary_controls_verified_inactive=True, execution_result='pending scheduled dispatch')
    except (ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        result.update(error=str(error), timer_start_attempted=start_attempted)
        result.setdefault('broker_requests_sent_by_continuation', 'unknown; inspect account-check evidence')
        if not start_attempted:
            try:
                state = arm.properties(SERVICE)
                if (state.get('ActiveState') != 'inactive' or state.get('Job') not in ('', '0')
                        or target_claim.exists() or target_claim.is_symlink()
                        or (created and arm.properties(name).get('ActiveState') != 'inactive')):
                    raise ValueError('Dispatch state uncertain; preserve plan/timer/evidence')
                observed = sha256(q.sealed_bytes(plan_path)).hexdigest()
                if replacement_attempted and observed in our_hashes:
                    arm.replace_plan(plan_path, observed, original)
                elif observed != sha256(original).hexdigest():
                    raise ValueError('Concurrent plan change preserved')
                if created and timer_path.read_text() == timer_body:
                    timer_path.unlink()
                    arm.command('systemctl', 'daemon-reload')
                elif timer_path.exists() or timer_path.is_symlink():
                    raise ValueError('Unconfirmed/changed timer creation preserved for review')
                result['expired_original_plan_restored'] = True
            except (ValueError, OSError, subprocess.TimeoutExpired) as cleanup:
                result['cleanup_pending'] = str(cleanup)
        else:
            result['recovery'] = 'Inspect actual service/claim/notebook; no automatic retry, rollback or service stop.'
    record('', result)
    print(json.dumps(dict(report=str(output / (identifier + '.json')), **result)), flush=True)
    return 0 if result['status'] == 'armed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous-review', type=Path, required=True)
    parser.add_argument('--system-report', type=Path, required=True)
    parser.add_argument('--dispatch-at', required=True)
    parser.add_argument('--arm', action='store_true', help='explicitly arm the dated qualification timer; may trade at that instant')
    args = parser.parse_args()
    if os.geteuid() != 0 or sys.prefix != str(CODE / '.venv') or not args.arm:
        parser.error('Use administrator installed Python and explicit --arm; no broker, plan or timer was changed')
    try:
        code = continue_session(args)
    except (ValueError, OSError, KeyError, sqlite3.Error) as error:
        parser.exit(2, str(error) + '\nContinuation incomplete; preserve records and inspect state.\n')
    raise SystemExit(code)


if __name__ == '__main__':
    main()
