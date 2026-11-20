"""Administrator preparation of a DISABLED M10 plan; one account-scoped GET.

Never initializes a notebook, enables a plan, creates a timer or sends mutations.
Changed account activity remains pending for owner review.
"""

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
CONTROLLER = 'practice-a'


def write_new(path, document, *, uid=None, gid=None, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'w') as target:
        if uid is not None:
            os.fchown(target.fileno(), uid, gid)
        os.fchmod(target.fileno(), mode)
        json.dump(document, target, indent=2)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())


def root_directory(path, group):
    if path.is_symlink():
        raise ValueError('Protected directory must not be a symlink')
    if not path.exists():
        path.mkdir(mode=0o750)
        os.chown(path, 0, group)
        path.chmod(0o750)
    info = path.stat()
    if info.st_uid != 0 or info.st_mode & 0o022 or not path.is_dir():
        raise ValueError('Protected directory ownership/permissions require review')
    if not ((info.st_mode & 0o005) == 0o005 or
            (info.st_gid == group and info.st_mode & 0o050 == 0o050)):
        raise ValueError('Protected directory is not traversable by the service group')


def verify_host_receipt(receipt, system_digest, deployment_digest, hashes):
    from nnfx_practice.qualification import host_identity
    boot, kernel = host_identity()
    if (receipt.get('system_report', {}).get('sha256') != system_digest
            or receipt.get('deployment_report', {}).get('sha256') != deployment_digest
            or receipt.get('application_hashes') != hashes
            or receipt.get('host_context', {}).get('boot_id') != boot
            or receipt.get('host_context', {}).get('kernel') != kernel):
        raise ValueError('Reviewed deployment/host context changed; repeat affected checks before preparation')


def read_clearance(settings):
    """Writer-only read under the existing maintenance exclusion; no notebook."""
    from nnfx_practice.broker import BrokerError, PracticeBroker, money
    from nnfx_practice.config import load_binding
    from nnfx_practice.control import MaintenanceDeferred, maintenance
    from nnfx_practice.host import SystemdService
    from nnfx_practice.qualification import account_identity, validate_strategy
    from nnfx_practice.reconciliation import _snapshot

    if os.getuid() != pwd.getpwnam('nnfx-run').pw_uid:
        raise ValueError('Fresh account check requires the dedicated writer')
    binding = load_binding(DATA, CONTROLLER)
    validate_strategy(binding)
    if (account_identity(binding) != settings['account_binding_sha256']
            or binding.manifest.hash != settings['manifest_sha256']):
        raise ValueError('Private binding differs; no broker request was made')
    result = None
    try:
        with maintenance(DATA, binding, SystemdService(CONTROLLER)):
            with PracticeBroker(binding) as broker:
                read = None
                try:
                    read = broker.account()  # Default transport: one GET, no retry.
                    snapshot = _snapshot(read)
                except BrokerError as error:
                    result = dict(at=broker.now(), source=broker.evidence_source, status='pending',
                                  classification='fresh practice account GET failed; no execution',
                                  account_binding_sha256=account_identity(binding),
                                  explanation='Read or validation failed; no account clearance was established.',
                                  evidence=error.evidence or (read.evidence() if read else {}),
                                  broker_requests=1, mutations_sent=0, actual_notebook_opened=False)
                else:
                    unchanged = (snapshot.boundary == settings['transaction_boundary']
                                 and money(snapshot.account['balance']) == money(settings['balance']))
                    clear = not snapshot.trades and not snapshot.orders
                    passed = clear and unchanged
                    result = dict(at=broker.now(), source=broker.evidence_source, status='passed' if passed else 'pending',
                        classification='fresh practice account GET under maintenance; no execution',
                        controller_id=CONTROLLER, notebook_id=binding.experiment.notebook_id,
                        account_binding_sha256=account_identity(binding), manifest_sha256=binding.manifest.hash,
                        open_trade_count=len(snapshot.trades), pending_order_count=len(snapshot.orders),
                        transaction_boundary=snapshot.boundary, unchanged_since_preflight=unchanged,
                        explanation=('Fresh snapshot has no trades/orders and the same transaction/balance boundary as reviewed M04.'
                                     if passed else 'Existing trades/orders or changed account activity requires owner review.'),
                        evidence=read.evidence(), broker_requests=1, mutations_sent=0,
                        actual_notebook_opened=False)
    except MaintenanceDeferred as error:
        if result is None:
            raise
        result.update(status='pending', maintenance_error=str(error))
    return result


def run_worker(script, settings):
    args = ['runuser', '-u', 'nnfx-run', '--', str(PYTHON), '-I', '-B', str(script),
            '--worker-settings', str(settings)]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise ValueError('Account check timed out; inspect maintenance state before recovery') from None
    if process.returncode:
        raise ValueError('Account check failed; inspect maintenance state and retained evidence')
    result = json.loads(stdout)
    if result.get('source') != 'practice_get' or result.get('broker_requests') != 1:
        raise ValueError('Expected one actual account-scoped GET')
    return result


def prepare(args):
    from nnfx_practice import qualification as q

    group = pwd.getpwnam('nnfx-run').pw_gid
    slot = datetime.fromisoformat(args.dispatch_at)
    local = slot.astimezone(ZoneInfo('America/New_York'))
    if (slot.utcoffset() != timedelta(0) or local.weekday() >= 5
            or (local.hour, local.minute, local.second, local.microsecond) != (16, 50, 0, 0)
            or slot <= datetime.now(UTC)):
        raise ValueError('Choose a future weekday 16:50 New York instant expressed in UTC')
    plan_path = q.PLAN_DIRECTORY / (CONTROLLER + '.json')
    if plan_path.exists() or plan_path.is_symlink():
        raise ValueError('Existing plan is preserved; review it before another preparation')
    system = json.loads(args.system_report.read_text())
    deployed = json.loads(args.deployment_report.read_text())
    hashes = q.code_hashes()
    if (not deployed.get('deployment_gate_checks_passed') or deployed.get('cleanup_errors') != []
            or system.get('cleanup_errors') != [] or system.get('deployed_source_hashes') != hashes
            or deployed.get('source_hashes') != hashes):
        raise ValueError('Current successful deployment/controller evidence is required')
    receipt = json.loads((ROOT / 'var/verification/m10-deployed/verification.json').read_text())
    verify_host_receipt(receipt, sha256(args.system_report.read_bytes()).hexdigest(),
                        sha256(args.deployment_report.read_bytes()).hexdigest(), hashes)
    for name, expected in hashes.items():
        for base in (ROOT, CODE):
            if sha256((base / name).read_bytes()).hexdigest() != expected:
                raise ValueError('Checkout/copied/installed application differs from tested deployment')
    q.host_controls(CONTROLLER, 'inspect')
    notebook = DATA / 'var/notebooks/notebook-a.sqlite3'
    if notebook.exists() or notebook.is_symlink():
        raise ValueError('Preserve existing notebook/history; this preparation is for the initial uninitialized path')
    private_info = (DATA / '.env').stat()
    writer = pwd.getpwnam('nnfx-run')
    if (private_info.st_uid, private_info.st_gid, private_info.st_mode & 0o777) != (writer.pw_uid, group, 0o600):
        raise ValueError('Deployed private permissions differ')
    sources = {
        'strategy_qualification': ROOT / 'strategies/t3_bandpass_v1/qualification.json',
        'account_preflight': ROOT / 'var/preflight/account-2026-11-18-python-01-division.json',
        'candle_preflight': ROOT / 'var/preflight/candles-2026-11-18-python-01.json',
        'm09_controller_controls': args.system_report,
        'execution_authority': ROOT / 'var/verification/m10-authority/authorization.json',
        'private_connection': ROOT / 'var/verification/m09-private/private-5185eb0637bf.json',
    }
    raw = {name: path.read_bytes() for name, path in sources.items()}
    docs = {name: q._document(body) for name, body in raw.items()}
    account = docs['account_preflight']
    if account.get('status') != 'passed' or account.get('source') != 'practice_get':
        raise ValueError('Reviewed M04 account evidence is required before the fresh GET')
    old = account['account']['evidence']['body']
    settings = dict(account_binding_sha256=account['account_binding_sha256'],
                    manifest_sha256=docs['candle_preflight']['manifest_sha256'],
                    transaction_boundary=old['lastTransactionID'], balance=old['account']['balance'])
    identifier = 'm10-preparation-' + uuid4().hex[:12]
    staged = CODE / 'verification' / identifier
    staged.mkdir(mode=0o755)
    staged.chmod(0o755)
    script = staged / 'check.py'
    script.write_bytes(Path(__file__).read_bytes())
    script.chmod(0o644)
    settings_path = staged / 'read-settings.json'
    write_new(settings_path, settings, uid=0, gid=group, mode=0o640)
    print('Checking one account-scoped GET under maintenance; no notebook, orders or timer activation.', flush=True)
    output = ROOT / 'var/verification/m10-preparation'
    output.mkdir(exist_ok=True)
    owner = (ROOT / 'config.toml').stat()
    report = output / (identifier + '.json')
    try:
        clearance = run_worker(script, settings_path)
    except ValueError:
        write_new(report, dict(status='pending', classification='account check interrupted or unavailable',
                               broker_requests='unknown', mutations_sent=0, plan_created=False,
                               note='Inspect maintenance state; do not infer account clearance or retry automatically.'),
                  uid=owner.st_uid, gid=owner.st_gid)
        raise
    write_new(report, clearance, uid=owner.st_uid, gid=owner.st_gid)
    q.host_controls(CONTROLLER, 'inspect')
    if notebook.exists() or notebook.is_symlink():
        raise ValueError('Unexpected actual notebook; stop and review')
    if clearance.get('status') != 'passed':
        print(json.dumps(dict(report=str(report), status='pending account review', plan_created=False,
                              qualification_enabled=False, ordinary_trading_enabled=False)))
        return 1
    docs['initial_account_resolution'] = clearance
    raw['initial_account_resolution'] = (json.dumps(clearance, indent=2) + '\n').encode()
    boot, kernel = q.host_identity()
    plan = dict(version=1, enabled=False, host=q.PRACTICE_HOST, controller_id=CONTROLLER, notebook_id='notebook-a',
                run_id='m10-' + uuid4().hex, dispatch_at=slot.isoformat(),
                account_binding_sha256=settings['account_binding_sha256'], manifest_sha256=settings['manifest_sha256'],
                code_sha256=q.code_identity(), config_sha256=sha256((DATA / 'config.toml').read_bytes()).hexdigest(),
                boot_id=boot, kernel=kernel, evidence={})
    # Check semantic prerequisites before writing any protected plan/evidence.
    for name, body in raw.items():
        plan['evidence'][name] = dict(status='passed', path='pending protected copy', sha256=sha256(body).hexdigest())
    q.validate_evidence(plan, docs)
    for directory in (q.PLAN_DIRECTORY.parent, q.PLAN_DIRECTORY, q.PLAN_DIRECTORY / 'evidence'):
        root_directory(directory, group)
    destination = q.PLAN_DIRECTORY / 'evidence' / identifier
    root_directory(destination, group)
    for name, body in raw.items():
        path = destination / (name + '.json')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640)
        with os.fdopen(fd, 'wb') as target:
            os.fchown(target.fileno(), 0, group)
            os.fchmod(target.fileno(), 0o640)
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        plan['evidence'][name]['path'] = str(path)
    write_new(plan_path, plan, uid=0, gid=group, mode=0o640)
    inspection = q.load_permit(DATA, CONTROLLER, 'inspect')
    result = dict(report=str(report), plan=str(plan_path), plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
                  inspection=inspection, qualification_enabled=False, ordinary_trading_enabled=False,
                  actual_notebook_initialized=False, timer_created=False, mutations_sent=0,
                  staged_worker=str(script), staged_worker_sha256=sha256(script.read_bytes()).hexdigest(),
                  source_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    final = output / (identifier + '-prepared.json')
    write_new(final, result, uid=owner.st_uid, gid=owner.st_gid)
    print(json.dumps(dict(metadata=str(final), **result)), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker-settings', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--system-report', type=Path)
    parser.add_argument('--deployment-report', type=Path)
    parser.add_argument('--dispatch-at')
    args = parser.parse_args()
    if args.worker_settings is not None:
        from nnfx_practice.qualification import sealed_bytes
        def stop(*_):
            raise SystemExit(2)
        signal.signal(signal.SIGTERM, stop)
        print(json.dumps(read_clearance(json.loads(sealed_bytes(args.worker_settings)))))
        return
    if os.geteuid() != 0:
        parser.error('Administrator access is required; no changes or broker requests were made')
    if sys.prefix != str(CODE / '.venv'):
        parser.error('Use /opt/nnfx-practice/.venv/bin/python')
    if not all((args.system_report, args.deployment_report, args.dispatch_at)):
        parser.error('Supply both successful system reports and an explicit future dispatch instant')
    try:
        result = prepare(args)
    except (ValueError, OSError) as error:
        parser.exit(2, f'{type(error).__name__}: {error}\nPreparation incomplete; retain reports and inspect maintenance/disabled-plan state. No broker mutation was sent.\n')
    raise SystemExit(result)


if __name__ == '__main__':
    main()
