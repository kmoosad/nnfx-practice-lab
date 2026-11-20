"""Initialize Q0 using verified preparation; restore the disabled plan afterward.

Administrator wrapper only. No timer creation, controller dispatch or mutations.
Existing notebooks/attempts are preserved for review, never reset or retried.
"""

import argparse
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import tempfile
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
CONTROLLER = 'practice-a'


def write_new(path, value, *, uid, gid, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'w') as target:
        os.fchown(target.fileno(), uid, gid)
        os.fchmod(target.fileno(), mode)
        json.dump(value, target, indent=2)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())


def replace_plan(path, expected, body):
    from nnfx_practice.qualification import sealed_bytes
    if sha256(sealed_bytes(path)).hexdigest() != expected:
        raise ValueError('Protected plan changed; preserve it for review')
    group = path.stat().st_gid
    fd, temporary = tempfile.mkstemp(prefix='.q0-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            os.fchown(target.fileno(), 0, group)
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


@contextmanager
def initialization_plan(path, expected):
    from nnfx_practice.qualification import sealed_bytes
    original = sealed_bytes(path)
    plan = json.loads(original)
    if sha256(original).hexdigest() != expected or plan.get('enabled') is not False:
        raise ValueError('Expected the reviewed disabled plan')
    plan['enabled'] = True
    active = (json.dumps(plan, indent=2) + '\n').encode()
    active_hash = sha256(active).hexdigest()
    replace_plan(path, expected, active)
    try:
        yield active_hash
    finally:
        observed = sha256(sealed_bytes(path)).hexdigest()
        if observed == active_hash:
            replace_plan(path, active_hash, original)
        elif observed != expected:
            raise ValueError('Concurrent plan change preserved; inspect before recovery')


def initialize_worker(settings):
    from nnfx_practice.broker import PracticeBroker, money
    from nnfx_practice.host import SystemdService
    from nnfx_practice.lifecycle import initialize_qualification
    from nnfx_practice.notebook import _check_binding, open_readonly
    from nnfx_practice.qualification import load_permit

    class InitializationBroker(PracticeBroker):
        request_count = 0

        def _get(self, *args, **kwargs):
            self.request_count += 1
            return super()._get(*args, **kwargs)

        def _mutate(self, *_args, **_kwargs):
            raise ValueError('Q0 initialization is GET-only')

    permit = load_permit(DATA, CONTROLLER, 'initialize')
    if (permit.digest != settings['initialization_plan_sha256']
            or permit.plan['account_binding_sha256'] != settings['account_binding_sha256']):
        raise ValueError('Initialization permit differs from the reviewed plan/binding')
    with InitializationBroker(permit.binding, qualification=permit) as broker:
        q0 = initialize_qualification(DATA, CONTROLLER, broker, service=SystemdService(CONTROLLER),
                                      evidence=permit.references)
        requests = broker.request_count
        source = broker.evidence_source
    with open_readonly(DATA, permit.binding.experiment) as db:
        _check_binding(db, permit.binding)
        row = db.execute('''SELECT qualification_snapshot_id, qualification_transaction_id,
                            imported_through_transaction_id, activation_snapshot_id, activated_at
                            FROM notebook''').fetchone()
        snapshot = db.execute('''SELECT purpose, last_transaction_id, balance, reconciliation_status
                                 FROM account_snapshots WHERE snapshot_id=?''', (q0,)).fetchone()
        clean = all(db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0
                    for table in ('runs', 'trade_sets', 'broker_attempts', 'issues'))
        matches = (row['qualification_snapshot_id'] == q0
                   and row['qualification_transaction_id'] == row['imported_through_transaction_id']
                   == snapshot['last_transaction_id'] == settings['transaction_boundary']
                   and money(snapshot['balance']) == money(settings['balance'])
                   and snapshot['purpose'] == 'qualification' and snapshot['reconciliation_status'] == 'reconciled'
                   and row['activation_snapshot_id'] is None and row['activated_at'] is None and clean)
        return dict(source=source, status='passed' if matches else 'pending',
                    classification='Q0 initialization and read-only verification; no execution',
                    q0_snapshot_id=q0, transaction_boundary=row['qualification_transaction_id'],
                    imported_through_transaction_id=row['imported_through_transaction_id'],
                    account_binding_sha256=permit.plan['account_binding_sha256'],
                    manifest_sha256=permit.binding.manifest.hash, matches_reviewed_clearance=matches,
                    broker_requests=requests, mutations_sent=0, actual_notebook_initialized=True,
                    ordinary_activation_performed=False, ordinary_trading_enabled=False)


def require_empty_notebook():
    path = DATA / 'var/notebooks/notebook-a.sqlite3'
    for candidate in (path, *(Path(str(path) + suffix) for suffix in ('-wal', '-shm', '-journal'))):
        if candidate.exists() or candidate.is_symlink():
            raise ValueError('Existing notebook/sidecars preserved; inspect Q0/history before further action')


def verify_q0_result(result, plan, boundary):
    if (result.get('source') != 'practice_get' or result.get('mutations_sent') != 0
            or result.get('ordinary_activation_performed') is not False
            or result.get('ordinary_trading_enabled') is not False):
        raise ValueError('Expected actual GET-only initialization evidence with ordinary activation unset')
    if result.get('status') == 'passed' and (
            result.get('actual_notebook_initialized') is not True
            or result.get('matches_reviewed_clearance') is not True
            or not isinstance(result.get('q0_snapshot_id'), str) or not result['q0_snapshot_id']
            or result.get('transaction_boundary') != boundary
            or result.get('imported_through_transaction_id') != boundary
            or result.get('account_binding_sha256') != plan['account_binding_sha256']
            or result.get('manifest_sha256') != plan['manifest_sha256']
            or type(result.get('broker_requests')) is not int or result['broker_requests'] < 1):
        raise ValueError('Q0 evidence does not match the reviewed clearance and immutable binding')


def initialize(prepared_path):
    from nnfx_practice import qualification as q
    meta = json.loads(prepared_path.read_text())
    path = q.PLAN_DIRECTORY / (CONTROLLER + '.json')
    original = q.sealed_bytes(path)
    if meta.get('plan') != str(path) or sha256(original).hexdigest() != meta.get('plan_sha256'):
        raise ValueError('Prepared metadata and protected plan differ')
    q.load_permit(DATA, CONTROLLER, 'inspect')
    plan = q._document(original)
    if plan.get('enabled') is not False or datetime.fromisoformat(plan['dispatch_at']) <= datetime.now(UTC):
        raise ValueError('Expected a disabled plan for a future qualification session')
    require_empty_notebook()
    resolution_ref = plan['evidence']['initial_account_resolution']
    raw = q.sealed_bytes(resolution_ref['path'])
    if sha256(raw).hexdigest() != resolution_ref['sha256']:
        raise ValueError('Protected account clearance changed')
    resolution = q._document(raw)
    if (resolution.get('status') != 'passed' or resolution.get('source') != 'practice_get'
            or resolution.get('open_trade_count') != 0 or resolution.get('pending_order_count') != 0
            or resolution.get('unchanged_since_preflight') is not True):
        raise ValueError('Fresh account clearance is not a verified pass')
    triggered = q._command('systemctl', 'show', 'nnfx-practice@practice-a.service', '--property=TriggeredBy')
    for unit in triggered.get('TriggeredBy', '').split():
        state = q._command('systemctl', 'show', unit, '--property=ActiveState,Job')
        if state.get('ActiveState') != 'inactive' or state.get('Job') not in ('', '0'):
            raise ValueError('A controller trigger is active or pending; no initialization was attempted')
    identifier = 'm10-q0-' + uuid4().hex[:12]
    stage = CODE / 'verification' / identifier
    stage.mkdir(mode=0o755)
    stage.chmod(0o755)
    worker = stage / 'initialize.py'
    worker.write_bytes(Path(__file__).read_bytes())
    worker.chmod(0o644)
    output = ROOT / 'var/verification/m10-initialization'
    output.mkdir(exist_ok=True)
    owner = (ROOT / 'config.toml').stat()
    write_new(output / (identifier + '-intent.json'),
              dict(prepared=str(prepared_path), disabled_plan_sha256=meta['plan_sha256'],
                   phase='initialization only; no timer or dispatch', broker_mutations_allowed=False),
              uid=owner.st_uid, gid=owner.st_gid)
    result = dict(status='pending', actual_notebook_initialized='unknown', broker_requests='unknown',
                  mutations_sent=0, timer_created=False, ordinary_trading_enabled=False)
    try:
        with initialization_plan(path, meta['plan_sha256']) as active_hash:
            body = resolution['evidence']['body']
            settings = dict(initialization_plan_sha256=active_hash,
                            account_binding_sha256=plan['account_binding_sha256'],
                            transaction_boundary=resolution['transaction_boundary'], balance=body['account']['balance'])
            settings_path = stage / 'settings.json'
            write_new(settings_path, settings, uid=0, gid=pwd.getpwnam('nnfx-run').pw_gid, mode=0o640)
            process = subprocess.Popen(['runuser', '-u', 'nnfx-run', '--', 'env',
                                        'NNFX_NOTEBOOK_READ_GROUP=nnfx-read', str(PYTHON), '-I', '-B',
                                        str(worker), '--worker-settings', str(settings_path)],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                stdout, _ = process.communicate(timeout=60)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise ValueError('Initialization interrupted; preserve notebook and inspect maintenance state') from None
            if process.returncode:
                raise ValueError('Initialization failed; preserve notebook and inspect maintenance state')
            result.update(json.loads(stdout))
            verify_q0_result(result, plan, resolution['transaction_boundary'])
    except (ValueError, OSError) as error:
        result.update(status='pending', error=str(error))
    try:
        result['disabled_plan_restored'] = sha256(q.sealed_bytes(path)).hexdigest() == meta['plan_sha256']
        q.host_controls(CONTROLLER, 'inspect')
        result['ordinary_controls_verified_inactive'] = True
    except (ValueError, OSError) as error:
        result.update(status='pending', control_error=str(error))
    result.update(at=datetime.now(UTC).isoformat(), prepared=str(prepared_path),
                  disabled_plan_sha256=meta['plan_sha256'], source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  qualification_enabled=False if result.get('disabled_plan_restored') else 'pending verification')
    report = output / (identifier + '.json')
    write_new(report, result, uid=owner.st_uid, gid=owner.st_gid)
    print(json.dumps(dict(report=str(report), **result)), flush=True)
    return 0 if result['status'] == 'passed' and result.get('disabled_plan_restored') else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--worker-settings', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_settings is not None:
        from nnfx_practice.qualification import sealed_bytes
        print(json.dumps(initialize_worker(json.loads(sealed_bytes(args.worker_settings)))))
        return
    if os.geteuid() != 0:
        parser.error('Administrator access is required; no Q0 or broker request was made')
    if sys.prefix != str(CODE / '.venv') or args.prepared is None:
        parser.error('Use the installed Python and supply --prepared metadata')
    try:
        result = initialize(args.prepared)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\nNo dispatch or timer was started; preserve existing evidence.\n')
    raise SystemExit(result)


if __name__ == '__main__':
    main()
