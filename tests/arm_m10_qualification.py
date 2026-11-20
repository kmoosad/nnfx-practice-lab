"""Arm one initial M10 session after verified Q0; never enable ordinary timers.

No broker request is sent by this command. The dated timer dispatches the existing
controller, which may place authorized practice orders at the reviewed instant.
"""

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
from uuid import uuid4
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/var/lib/nnfx-practice')
CODE = Path('/opt/nnfx-practice')
SERVICE = 'nnfx-practice@practice-a.service'
ORDINARY_TIMER = 'nnfx-practice@practice-a.timer'
UNITS = Path('/etc/systemd/system')
NY = ZoneInfo('America/New_York')


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'TZ': 'UTC', 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('Host operation failed: ' + args[0])
    return result.stdout


def properties(unit):
    output = command('systemctl', 'show', unit, '--property=LoadState,ActiveState,SubState,Job,UnitFileState,'
                     'DropInPaths,Unit,Triggers,TimersCalendar,NextElapseUSecRealtime,AccuracyUSec,Persistent,RandomizedDelayUSec')
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def future_slot(plan, *, now=None):
    slot = datetime.fromisoformat(plan['dispatch_at'])
    local = slot.astimezone(NY)
    now = datetime.now(UTC) if now is None else now
    if (slot.utcoffset() != timedelta(0) or local.weekday() >= 5
            or (local.hour, local.minute, local.second, local.microsecond) != (16, 50, 0, 0)
            or slot <= now):
        raise ValueError('Qualification needs its reviewed future weekday 16:50 instant; no catch-up')
    return slot


def timer_definition(plan):
    run = plan['run_id']
    if not isinstance(run, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', run):
        raise ValueError('Invalid qualification run ID')
    slot = datetime.fromisoformat(plan['dispatch_at']).astimezone(NY)
    calendar = slot.strftime('%Y-%m-%d %H:%M:%S America/New_York')
    name = 'nnfx-m10-qualify-' + run + '.timer'
    body = ('[Unit]\nDescription=NNFX initial M10 qualification ' + run + '\n\n'
            '[Timer]\nOnCalendar=' + calendar + '\nAccuracySec=1s\nRandomizedDelaySec=0\n'
            'Persistent=false\nUnit=' + SERVICE + '\n')
    return name, body


def validate_initialization(report, plan, prepared):
    for name in ('actual_notebook_initialized', 'matches_reviewed_clearance',
                 'disabled_plan_restored', 'ordinary_controls_verified_inactive'):
        if report.get(name) is not True:
            raise ValueError('Q0 prerequisite is pending: ' + name)
    if (report.get('status') != 'passed' or report.get('source') != 'practice_get'
            or any(report.get(key) is not False for key in (
                'ordinary_activation_performed', 'ordinary_trading_enabled', 'qualification_enabled', 'timer_created'))
            or report.get('mutations_sent') != 0 or not report.get('q0_snapshot_id')
            or report.get('transaction_boundary') != report.get('imported_through_transaction_id')
            or report.get('account_binding_sha256') != plan['account_binding_sha256']
            or report.get('manifest_sha256') != plan['manifest_sha256']
            or report.get('disabled_plan_sha256') != prepared['plan_sha256']):
        raise ValueError('Expected actual, unactivated Q0 evidence for this exact disabled plan')


def audit_notebook(plan, initialization, resolution):
    from nnfx_practice.broker import money
    from nnfx_practice.config import read_registry
    from nnfx_practice.evidence import canonical_json
    from nnfx_practice.notebook import open_readonly
    experiment = read_registry(DATA)[plan['controller_id']]
    path = experiment.notebook_path(DATA)
    writer = pwd.getpwnam('nnfx-run')
    directory = path.parent.stat()
    if (directory.st_uid != writer.pw_uid or directory.st_gid != writer.pw_gid
            or directory.st_mode & 0o077 != 0o050 or not directory.st_mode & stat.S_ISGID):
        raise ValueError('Actual notebook directory permissions differ from the verified writer/readers contract')
    for item in (path, Path(str(path) + '-wal'), Path(str(path) + '-shm')):
        info = item.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != writer.pw_uid
                or info.st_gid != writer.pw_gid or stat.S_IMODE(info.st_mode) != 0o640):
            raise ValueError('Actual shared notebook/WAL/SHM ownership or permissions require review')
    with open_readonly(DATA, experiment) as db:
        row = db.execute('SELECT * FROM notebook').fetchone()
        identity = [row['controller_id'], row['notebook_id'], row['account_id'], row['home_currency']]
        digest = sha256(canonical_json(identity).encode()).hexdigest()
        snapshot = db.execute('SELECT * FROM account_snapshots WHERE snapshot_id=?',
                              (row['qualification_snapshot_id'],)).fetchone()
        if (digest != plan['account_binding_sha256'] or row['manifest_hash'] != plan['manifest_sha256']
                or sha256(row['manifest_json'].encode()).hexdigest() != plan['manifest_sha256']
                or row['lookback_candles'] != 386 or row['strategy_version'] != 't3_bandpass_v1'
                or row['qualification_snapshot_id'] != initialization['q0_snapshot_id']
                or row['activated_at'] is not None or row['activation_snapshot_id'] is not None
                or row['activation_transaction_id'] is not None or snapshot is None
                or snapshot['purpose'] != 'qualification' or snapshot['reconciliation_status'] != 'reconciled'
                or row['qualification_transaction_id'] != row['imported_through_transaction_id']
                or row['qualification_transaction_id'] != initialization['transaction_boundary']
                or snapshot['last_transaction_id'] != resolution['transaction_boundary']
                or money(snapshot['balance']) != money(resolution['evidence']['body']['account']['balance'])):
            raise ValueError('Current Q0/cursor/binding differs or ordinary activation exists; preserve history')
        for table in ('runs', 'trade_sets', 'trade_legs', 'broker_attempts', 'issues', 'broker_transactions'):
            if db.execute('SELECT count(*) FROM ' + table).fetchone()[0]:
                raise ValueError('Existing qualification activity requires review; this is the initial-session armer')
    return dict(q0_snapshot_id=initialization['q0_snapshot_id'], transaction_boundary=initialization['transaction_boundary'],
                cursor_matches_q0=True, ordinary_activation_present=False, query_only=True)


def claim_path(plan):
    directory = DATA / 'var/qualification' / 'practice-a'
    for part in (DATA / 'var', directory.parent, directory):
        if part.is_symlink():
            raise ValueError('Qualification evidence path contains a symlink')
    session = datetime.fromisoformat(plan['dispatch_at']).astimezone(NY).date().isoformat()
    path = directory / (session + '.claim')
    if path.exists() or path.is_symlink():
        raise ValueError('This qualification session was already attempted; no replay')
    return path


def validate_waiting_timer(state, plan, *, now=None):
    slot = future_slot(plan, now=now)
    calendar = slot.astimezone(NY).strftime('%Y-%m-%d %H:%M:%S America/New_York')
    if (state.get('LoadState') != 'loaded' or state.get('ActiveState') != 'active'
            or state.get('SubState') != 'waiting' or state.get('Unit') != SERVICE
            or state.get('Triggers') != SERVICE or state.get('Persistent') != 'no'
            or state.get('AccuracyUSec') != '1s' or state.get('RandomizedDelayUSec') != '0'
            or state.get('UnitFileState') != 'static' or state.get('DropInPaths') != ''
            or state.get('Job') not in ('', '0') or 'OnCalendar=' + calendar not in state.get('TimersCalendar', '')):
        raise ValueError('Qualification timer is not the reviewed single dated dispatch')
    text = state.get('NextElapseUSecRealtime', '')
    if not text.endswith(' UTC'):
        raise ValueError('Timer next expiry is unavailable')
    try:
        actual = datetime.fromisoformat(text.split(' ', 1)[1].removesuffix(' UTC')).replace(tzinfo=UTC)
    except (ValueError, IndexError):
        raise ValueError('Timer next expiry is invalid') from None
    if actual != slot:
        raise ValueError('Timer next expiry differs from the reviewed instant')


def write_new(path, body, *, uid, gid, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as target:
        os.fchown(target.fileno(), uid, gid)
        os.fchmod(target.fileno(), mode)
        target.write(body)
        target.flush()
        os.fsync(target.fileno())


def replace_plan(path, expected, body):
    from nnfx_practice.qualification import sealed_bytes
    if sha256(sealed_bytes(path)).hexdigest() != expected:
        raise ValueError('Protected plan changed; no replacement was made')
    fd, temporary = tempfile.mkstemp(prefix='.arm-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            os.fchown(target.fileno(), 0, path.stat().st_gid)
            os.fchmod(target.fileno(), 0o640)
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def arm(initialization_path):
    from nnfx_practice import qualification as q
    initialization_raw = initialization_path.read_bytes()
    initialization = q._document(initialization_raw)
    prepared_path = Path(initialization['prepared'])
    prepared = q._document(prepared_path.read_bytes())
    path = q.PLAN_DIRECTORY / 'practice-a.json'
    original = q.sealed_bytes(path)
    original_hash = sha256(original).hexdigest()
    plan = q._document(original)
    if plan.get('enabled') is not False or original_hash != prepared['plan_sha256']:
        raise ValueError('Expected the reviewed disabled plan; existing arming state is preserved')
    validate_initialization(initialization, plan, prepared)
    if initialization['source_sha256'] != sha256((ROOT / 'tests/initialize_m10_qualification.py').read_bytes()).hexdigest():
        raise ValueError('Q0 wrapper source differs from its actual initialization evidence')
    q.load_permit(DATA, 'practice-a', 'inspect')
    future_slot(plan)
    for name, digest in q.code_hashes().items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != digest or sha256((CODE / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Checkout/copied/installed code differs; review affected qualification')
    resolution = q._document(q.sealed_bytes(plan['evidence']['initial_account_resolution']['path']))
    audit = audit_notebook(plan, initialization, resolution)
    attempt = claim_path(plan)
    service = properties(SERVICE)
    if service.get('ActiveState') != 'inactive' or service.get('Job') not in ('', '0'):
        raise ValueError('Controller is active/pending; do not stop it to arm')
    triggered = q._command('systemctl', 'show', SERVICE, '--property=TriggeredBy')
    for unit in triggered.get('TriggeredBy', '').split():
        state = properties(unit)
        if state.get('ActiveState') != 'inactive' or state.get('Job') not in ('', '0'):
            raise ValueError('Another controller trigger is active/pending')
    name, timer_body = timer_definition(plan)
    timer_file = UNITS / name
    if timer_file.exists() or timer_file.is_symlink():
        raise ValueError('Existing qualification timer preserved; no automatic rearming')
    identifier = 'm10-arm-' + uuid4().hex[:12]
    output = ROOT / 'var/verification/m10-arming'
    output.mkdir(exist_ok=True)
    owner = (ROOT / 'config.toml').stat()
    active_plan = dict(plan, enabled=True)
    active = (json.dumps(active_plan, indent=2) + '\n').encode()
    active_hash = sha256(active).hexdigest()
    result = dict(at=datetime.now(UTC).isoformat(), status='pending', phase='initial_account_path',
                  classification='one-session M10 scheduler arming; execution results pending',
                  initialization_report=str(initialization_path), initialization_sha256=sha256(initialization_raw).hexdigest(),
                  q0=audit, timer=name, service=SERVICE, run_id=plan['run_id'], dispatch_at=plan['dispatch_at'],
                  dispatch_melbourne=datetime.fromisoformat(plan['dispatch_at']).astimezone(ZoneInfo('Australia/Melbourne')).isoformat(),
                  account_label='Python 01', account_binding_sha256=plan['account_binding_sha256'],
                  disabled_plan_sha256=original_hash, active_plan_sha256=active_hash,
                  timer_definition_sha256=sha256(timer_body.encode()).hexdigest(), source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  broker_requests_sent_by_armer=0, ordinary_trading_enabled=False, ordinary_activation_performed=False,
                  practice_execution_qualified=False, host_qualification_complete=False)
    write_new(output / (identifier + '-intent.json'), (json.dumps(result, indent=2) + '\n').encode(),
              uid=owner.st_uid, gid=owner.st_gid, mode=0o600)
    created = enabled = start_attempted = False
    try:
        write_new(timer_file, timer_body.encode(), uid=0, gid=0, mode=0o644)
        created = True
        command('systemd-analyze', 'verify', str(timer_file))
        command('systemctl', 'daemon-reload')
        q.host_controls('practice-a', 'inspect')
        future_slot(plan)
        claim_path(plan)
        enabled = True  # Replacement can apply even if its final fsync fails.
        replace_plan(path, original_hash, active)
        q.load_permit(DATA, 'practice-a', 'inspect')
        future_slot(plan)
        start_attempted = True  # A timeout may still have started it: never retry/roll back blindly.
        command('systemctl', 'start', name)
        state = properties(name)
        validate_waiting_timer(state, plan)
        q.host_controls('practice-a', 'inspect')
        result.update(status='armed', qualification_plan_enabled=True, qualification_timer_state=state,
                      ordinary_controls_verified_inactive=True, execution_result='pending scheduled dispatch')
    except (ValueError, OSError, subprocess.TimeoutExpired, sqlite3.Error) as error:
        result.update(error=str(error), timer_start_attempted=start_attempted)
        if not start_attempted:
            try:
                service_state = properties(SERVICE)
                if (service_state.get('ActiveState') != 'inactive' or service_state.get('Job') not in ('', '0')
                        or (attempt.exists() or attempt.is_symlink())
                        or (created and properties(name).get('ActiveState') != 'inactive')):
                    raise ValueError('Dispatch state uncertain; preserve plan/timer for review')
                if enabled:
                    observed = sha256(q.sealed_bytes(path)).hexdigest()
                    if observed == active_hash:
                        replace_plan(path, active_hash, original)
                    elif observed != original_hash:
                        raise ValueError('Concurrent plan change preserved for review')
                if created:
                    if timer_file.read_text() != timer_body:
                        raise ValueError('Timer changed; preserve it for review')
                    timer_file.unlink()
                    command('systemctl', 'daemon-reload')
                elif timer_file.exists() or timer_file.is_symlink():
                    raise ValueError('Unconfirmed timer creation preserved for review')
                result['pre_dispatch_cleanup_completed'] = True
            except (ValueError, OSError, subprocess.TimeoutExpired) as cleanup:
                result['cleanup_pending'] = str(cleanup)
        else:
            result['recovery'] = 'Inspect actual service/timer/claim/notebook; no automatic retry or service stop.'
    report = output / (identifier + '.json')
    write_new(report, (json.dumps(result, indent=2) + '\n').encode(), uid=owner.st_uid, gid=owner.st_gid, mode=0o600)
    print(json.dumps(dict(report=str(report), **result)), flush=True)
    return 0 if result['status'] == 'armed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialization', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required; no plan, timer or broker request was changed')
    if sys.prefix != str(CODE / '.venv'):
        parser.error('Use /opt/nnfx-practice/.venv/bin/python')
    try:
        code = arm(args.initialization)
    except (ValueError, OSError, subprocess.TimeoutExpired, sqlite3.Error) as error:
        parser.exit(2, str(error) + '\nArming is incomplete; preserve evidence and inspect state.\n')
    raise SystemExit(code)


if __name__ == '__main__':
    main()
