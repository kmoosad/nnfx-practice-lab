"""One scheduled read-only candle pass, guarded Q0, then future qualification.

Installed root-owned by add_python03.py. Never invokes a trading run. A failed
attempt is retained and requires review; it is not automatically retried.
"""

import argparse
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import subprocess
from uuid import uuid4
from zoneinfo import ZoneInfo


CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
NY = ZoneInfo('America/New_York')


def next_slot(now):
    local = now.astimezone(NY)
    slot = local.replace(hour=16, minute=50, second=0, microsecond=0)
    if slot <= local:
        slot += timedelta(days=1)
    while slot.weekday() >= 5:
        slot += timedelta(days=1)
    return slot.astimezone(UTC)


def run(*args, timeout=120):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    if result.returncode:
        raise RuntimeError('Python 03 setup step failed; retained evidence needs review')
    return result.stdout


def native(program, *args, timeout=120):
    return run('runuser', '-u', 'nnfx-run', '--', CODE / '.venv/bin/python', '-I', '-B', '-c', program, *args, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Expected the installed administrator-owned setup service')
    from nnfx_practice import qualification as q
    context = q._document(q.sealed_bytes(args.context))
    if (context['code_sha256'] != q.code_identity() or context['kernel'] != q.host_identity()[1]
            or context['config_sha256'] != sha256((DATA / 'config.toml').read_bytes()).hexdigest()
            or context['bootstrap_sha256'] != sha256(Path(__file__).read_bytes()).hexdigest()):
        raise ValueError('Reviewed code/configuration/kernel changed before initial capture')
    local = datetime.now(UTC).astimezone(NY)
    if local.weekday() >= 5 or (local.hour, local.minute) != (16, 50):
        raise ValueError('This setup requires its own weekday 16:50 New York candle')
    folder = args.context.parent
    receipt_path = folder / 'bootstrap-receipt.json'
    # An exclusive marker prevents automatic repeats after any uncertain result.
    with receipt_path.open('x') as target:
        target.write('{"status":"started"}\n')
    receipt_path.chmod(0o640)
    writer = pwd.getpwnam('nnfx-run')
    os.chown(receipt_path, 0, writer.pw_gid)
    record = dict(status='started', started_at=datetime.now(UTC).isoformat(), trading_run_invoked=False)
    def seal(name, value):
        raw = json.dumps(value, indent=2, allow_nan=False).encode() + b'\n'
        path = folder / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o640)
        with os.fdopen(fd, 'wb') as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
            os.fchown(target.fileno(), 0, writer.pw_gid)
        return dict(path=str(path), sha256=sha256(raw).hexdigest(), status=value.get('status', 'passed'))
    plan_path = q.PLAN_DIRECTORY / 'practice-c.json'
    try:
        if plan_path.exists():
            raise ValueError('Python 03 already has a protected plan; inspect instead of replacing it')
        capture = json.loads(native(
            "import json; from pathlib import Path; from nnfx_practice.config import load_binding; from nnfx_practice.broker import PracticeBroker; from nnfx_practice.preflight import check_candles; b=load_binding(Path('/var/lib/nnfx-practice'),'practice-c');\nwith PracticeBroker(b) as broker: print(json.dumps(check_candles(broker)))", timeout=600))
        record['candle_report'] = seal('candle-preflight.json', capture)
        if (capture.get('status') != 'passed' or capture.get('valid_windows') != 28
                or capture.get('account_binding_sha256') != context['account_binding_sha256']
                or capture.get('manifest_sha256') != context['manifest_sha256']):
            raise ValueError('The intended-account 28-pair candle capture did not pass')
        account = capture['account']['evidence']['body']['account']
        if account.get('trades') or account.get('orders') or account.get('openTradeCount') != 0 or account.get('pendingOrderCount') != 0:
            raise ValueError('Initial Python 03 account activity needs owner resolution')
        details = json.loads(native(
            "import json,os,stat; from pathlib import Path; from nnfx_practice.config import load_binding; from nnfx_practice.qualification import account_identity; b=load_binding(Path('/var/lib/nnfx-practice'),'practice-c'); s=Path('/var/lib/nnfx-practice/.env').stat(); print(json.dumps(dict(account_binding_sha256=account_identity(b),manifest_sha256=b.manifest.hash,uid=os.getuid(),private_uid=s.st_uid,private_gid=s.st_gid,private_mode=stat.S_IMODE(s.st_mode))))"))
        reader = subprocess.run(['runuser', '-u', 'nnfx-view', '--', 'test', '-r', str(DATA / '.env')], capture_output=True)
        if reader.returncode != 1 or details['account_binding_sha256'] != context['account_binding_sha256']:
            raise ValueError('Private binding or dashboard credential isolation differs')
        private = seal('private-connection.json', dict(private_checks_passed=True, binding=details,
                      viewer=dict(uid=pwd.getpwnam('nnfx-view').pw_uid, credential_readable=False)))
        resolution = seal('initial-account-resolution.json', dict(status='passed',
            account_binding_sha256=context['account_binding_sha256'],
            explanation='The intended-account scheduled candle preflight observed no open trades or pending orders; initialization requires a fresh clear snapshot again.'))
        first = next_slot(datetime.now(UTC))
        refs = {**context['evidence'], 'candle_preflight': record['candle_report'],
                'private_connection': private, 'initial_account_resolution': resolution}
        plan = dict(version=1, enabled=True, mode='qualification', controller_id='practice-c', notebook_id='notebook-c',
                    host=q.PRACTICE_HOST, account_binding_sha256=context['account_binding_sha256'],
                    manifest_sha256=context['manifest_sha256'], code_sha256=context['code_sha256'],
                    config_sha256=context['config_sha256'], kernel=context['kernel'], boot_id=q.host_identity()[0],
                    run_id='python03-auto-' + uuid4().hex[:12], dispatch_at=first.isoformat(), evidence=refs)
        q.validate_evidence(plan, q._evidence(plan))
        # Root owns the permit; the native writer still performs all normal
        # identity, maintenance, fresh-account and Q0 checks.
        initial = seal('initial-plan.json', plan)
        run('install', '-o', 'root', '-g', 'nnfx-read', '-m', '0640', initial['path'], plan_path)
        run('runuser', '-u', 'nnfx-run', '--', 'env', 'NNFX_NOTEBOOK_READ_GROUP=nnfx-read',
            CODE / '.venv/bin/python', '-I', '-B', '-m', 'nnfx_practice.host', 'qualification-initialize', 'practice-c')
        record['q0_initialized'] = True
        authority = seal('automatic-authority.json', dict(controller_id='practice-c', notebook_id='notebook-c',
            account_binding_sha256=context['account_binding_sha256'], schedule=q.SCHEDULE,
            statement=context['owner_statement'], ordinary_activation_authorized=False,
            ordinary_scheduled_trading_authorized=False))
        plan.update(version=2, schedule=q.SCHEDULE, automatic_schedule_authority=authority)
        q.validate_evidence(plan, q._evidence(plan))
        q.automatic_authority(plan)
        automatic = seal('automatic-plan.json', plan)
        run('install', '-o', 'root', '-g', 'nnfx-read', '-m', '0640', automatic['path'], plan_path)
        run(CODE / '.venv/bin/python', '-I', '-B', '-m', 'nnfx_practice.host', 'qualification-check', 'practice-c')
        run('systemctl', 'enable', '--now', q.qualification_timer('practice-c'))
        state = run('systemctl', 'show', q.qualification_timer('practice-c'), '--property=ActiveState,SubState,UnitFileState')
        if not all(value in state.splitlines() for value in ('ActiveState=active', 'SubState=waiting', 'UnitFileState=enabled')):
            raise ValueError('Python 03 schedule state is uncertain; inspect without replay')
        record.update(status='initialized; automatic qualification scheduled', first_dispatch=first.isoformat())
    except BaseException as error:
        record.update(status='blocked; inspect before recovery', error=type(error).__name__ + ': ' + str(error))
        # Preserve any Q0 and plan for review. Disable future attempts, never
        # roll back a notebook, rerun initialization or invoke a trading run.
        run('systemctl', 'disable', '--now', q.qualification_timer('practice-c'))
        raise
    finally:
        receipt_path.write_text(json.dumps(record, indent=2) + '\n')
    print('Python 03 setup:', record['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
