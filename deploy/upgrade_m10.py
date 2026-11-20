"""Administrator migration from the retained dated M10 plan to automatic qualification.

Preserves notebook/claims, archives the protected plan/code, runs new broker-free
host fixtures, and arms only the weekday qualification timer. No broker request.
On failure after exclusion, leaves schedules stopped for explicit investigation.
"""

import argparse
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import sys
import zipfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
CONTROLLER = 'practice-a'
SERVICE = 'nnfx-practice@practice-a.service'
ORDINARY = 'nnfx-practice@practice-a.timer'
QUALIFICATION = 'nnfx-practice-qualification@practice-a.timer'


def command(*args, timeout=30):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout,
                            env={**os.environ, 'TZ': 'UTC', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'})
    if result.returncode:
        raise RuntimeError('Deployment step failed: ' + str(args[0]) + '; inspect retained receipt')
    return result.stdout


def properties(unit):
    output = command('systemctl', 'show', unit, '--property=LoadState,ActiveState,SubState,UnitFileState,Job,DropInPaths,TriggeredBy')
    return dict(line.split('=', 1) for line in output.splitlines() if '=' in line)


def quiet_window(now, ny):
    local = now.astimezone(ny)
    if local.weekday() < 5 and (16, 35) <= (local.hour, local.minute) <= (17, 10):
        raise ValueError('Defer deployment outside the trading window; never interrupt an eligible run')


def qualify_current(old, *, now, expected, digest, registry_hash, kernel):
    if (digest != expected or old.get('version') != 1 or old.get('mode', 'qualification') != 'qualification'
            or old.get('controller_id') != CONTROLLER or old.get('notebook_id') != 'notebook-a'
            or old.get('config_sha256') != registry_hash or old.get('kernel') != kernel):
        raise ValueError('Existing protected plan/binding differs; preserve it and inspect, never blindly rearm')


def candidate(old, *, code_hash, boot, kernel, controls_ref, authority_ref):
    plan = deepcopy(old)
    plan.update(version=2, mode='qualification', enabled=False, schedule='Mon..Fri *-*-* 16:50:00 America/New_York',
                run_id='m10-auto-' + uuid4().hex[:12], code_sha256=code_hash, boot_id=boot, kernel=kernel)
    plan['evidence']['m09_controller_controls'] = controls_ref
    plan['automatic_schedule_authority'] = authority_ref
    return plan


def validate_verification(verification, root, source_hashes):
    import re
    required = {'deploy/upgrade_m10.py', 'deploy/nnfx-practice-qualification@.timer',
                'tests/check_m09_system.py', 'tests/m09_system_worker.py', 'tests/m09_dashboard_worker.py',
                'tests/arm_m10_qualification.py', 'tests/check_m10_preparation.py'}
    if (verification.get('classification') != 'offline automatic M10 implementation'
            or verification.get('source_hashes') != source_hashes
            or not required <= set(verification.get('deployment_hashes', {}))):
        raise ValueError('Offline verification does not match current application/deployment source')
    suite = root / verification['suite_log']
    match = re.search(r'Ran (\d+) tests in [\d.]+s\s+OK\s*$', suite.read_text())
    if (sha256(suite.read_bytes()).hexdigest() != verification.get('suite_sha256')
            or not match or int(match[1]) < 427):
        raise ValueError('Passing offline suite artifact is missing or changed')
    for name, digest in verification['deployment_hashes'].items():
        if sha256((root/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Deployment/fixture source changed after verification')
    wheel = root / verification['wheel']['path']
    if sha256(wheel.read_bytes()).hexdigest() != verification['wheel']['sha256']:
        raise ValueError('Prepared offline package changed')
    with zipfile.ZipFile(wheel) as package:
        for name,digest in source_hashes.items():
            if sha256(package.read(name)).hexdigest() != digest:
                raise ValueError('Prepared package differs from verified application')


def notebook_state():
    from nnfx_practice.config import read_registry
    from nnfx_practice.evidence import canonical_json
    from nnfx_practice.notebook import open_readonly
    experiment = read_registry(DATA)[CONTROLLER]
    writer = pwd.getpwnam('nnfx-run')
    path = experiment.notebook_path(DATA)
    for item in (path, Path(str(path)+'-wal'), Path(str(path)+'-shm')):
        info = item.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != writer.pw_uid or info.st_gid != writer.pw_gid
                or stat.S_IMODE(info.st_mode) != 0o640):
            raise ValueError('Existing notebook/WAL/SHM permissions are required; nothing is created')
    with open_readonly(DATA, experiment) as db:
        row = db.execute('SELECT * FROM notebook').fetchone()
        if not row['qualification_snapshot_id'] or row['activated_at'] is not None:
            raise ValueError('Existing unactivated Q0 is required; no notebook is created or reset')
        snapshot = db.execute('SELECT * FROM account_snapshots WHERE snapshot_id=?', (row['qualification_snapshot_id'],)).fetchone()
        if (not snapshot or snapshot['purpose'] != 'qualification' or snapshot['reconciliation_status'] != 'reconciled'
                or snapshot['last_transaction_id'] != row['qualification_transaction_id']):
            raise ValueError('Q0 evidence is inconsistent')
        return dict(q0=row['qualification_snapshot_id'], q0_boundary=row['qualification_transaction_id'],
                    cursor=row['imported_through_transaction_id'], activated_at=row['activated_at'],
                    manifest_sha256=row['manifest_hash'], account_binding_sha256=sha256(canonical_json([
                        row['controller_id'], row['notebook_id'], row['account_id'], row['home_currency']]).encode()).hexdigest(),
                    counts={t: db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in
                        ('runs','broker_attempts','trade_sets','trade_legs','issues','fills','broker_transactions','ledger_entries')})


def file_fingerprints():
    # No writer connection, checkpoint, replacement DB, sidecar or credential read.
    output = {}
    for folder in (DATA/'var/notebooks', DATA/'var/qualification'):
        for path in sorted(folder.rglob('*')):
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ValueError('Unexpected symlink in protected history')
            if path.is_file():
                output[str(path)] = dict(sha256=sha256(path.read_bytes()).hexdigest(), uid=info.st_uid,
                    gid=info.st_gid, mode=stat.S_IMODE(info.st_mode), inode=info.st_ino)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--verification', type=Path, required=True, help='offline source manifest prepared in the checkout')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required; no plan, timer or broker action was attempted')
    sys.path.insert(0, str(ROOT))
    from nnfx_practice import qualification as q
    from nnfx_practice.config import read_registry
    from tests.arm_m10_qualification import replace_plan, write_new
    from tests.check_m10_preparation import root_directory
    quiet_window(datetime.now(UTC), q.NY)
    if set(read_registry(DATA)) != {CONTROLLER}:
        raise ValueError('This migration is scoped to Python 01; review other controllers before updating shared code')
    verification = json.loads(args.verification.read_bytes())
    validate_verification(verification,ROOT,q.code_hashes())
    plan_path = q.PLAN_DIRECTORY / (CONTROLLER + '.json')
    original = q.sealed_bytes(plan_path)
    old = q._document(original)
    qualify_current(old, now=datetime.now(UTC), expected=args.expected_plan_sha256,
                    digest=sha256(original).hexdigest(), registry_hash=sha256((DATA/'config.toml').read_bytes()).hexdigest(),
                    kernel=q.host_identity()[1])
    # Validate installed prerequisites with installed code; no elapsed-date rearming.
    program = "from nnfx_practice import qualification as q; p=q._document(q.sealed_bytes(q.PLAN_DIRECTORY/'practice-a.json')); assert p['code_sha256']==q.code_identity(); q.validate_evidence(p,q._evidence(p))"
    command(CODE/'.venv/bin/python', '-I', '-B', '-c', program)
    ordinary = properties(ORDINARY)
    service = properties(SERVICE)
    recurring = properties(QUALIFICATION)
    if recurring.get('LoadState') != 'not-found' and (recurring.get('ActiveState') != 'inactive'
            or recurring.get('UnitFileState') != 'disabled' or recurring.get('Job') not in ('','0')):
        raise ValueError('An automatic qualification schedule already exists; inspect instead of rearming')
    if (ordinary.get('ActiveState') != 'inactive' or ordinary.get('UnitFileState') != 'disabled'
            or ordinary.get('Job') not in ('','0') or service.get('ActiveState') not in ('inactive','failed')
            or service.get('Job') not in ('','0') or service.get('LoadState') != 'loaded'):
        raise ValueError('Controller/ordinary controls are not inactive; never stop a running controller')
    legacy = 'nnfx-m10-qualify-' + old['run_id'] + '.timer'
    triggers = service.get('TriggeredBy','').split()
    for unit in triggers:
        state = properties(unit)
        if state.get('Job') not in ('','0') or (unit != legacy and state.get('ActiveState') != 'inactive'):
            raise ValueError('Unexpected active trigger; preserve and inspect it')
    expected_legacy, body = __import__('tests.arm_m10_qualification', fromlist=['timer_definition']).timer_definition(old)
    if expected_legacy != legacy or Path('/etc/systemd/system', legacy).read_text() != body:
        raise ValueError('Dated timer differs from the protected plan')
    writer = pwd.getpwnam('nnfx-run')
    baseline = notebook_state()
    if any(baseline[key] != old[key] for key in ('manifest_sha256','account_binding_sha256')):
        raise ValueError('Notebook binding differs from protected plan')
    identifier = 'm10-automatic-' + uuid4().hex[:12]
    archive = q.PLAN_DIRECTORY/'evidence'/identifier
    root_directory(archive, writer.pw_gid)
    output = ROOT/'var/verification/m10-automatic-deployment'
    output.mkdir(parents=True, exist_ok=True)
    receipt = output/(identifier+'.json')
    record = dict(classification='automatic M10 qualification deployment', status='prepared',
                  at=datetime.now(UTC).isoformat(), old_plan_sha256=sha256(original).hexdigest(),
                  archive=str(archive), before=baseline, broker_requests=0, ordinary_activation_performed=False,
                  ordinary_timer_enabled=False, source_hashes=q.code_hashes())
    def seal(name, raw):
        path = archive/name
        write_new(path, raw, uid=0, gid=writer.pw_gid, mode=0o640)
        return dict(path=str(path), sha256=sha256(raw).hexdigest(), status='passed')
    seal('previous-plan.json', original)
    seal('dated-timer.txt', body.encode())
    seal('offline-verification.json', args.verification.read_bytes())
    wheel_path=ROOT/verification['wheel']['path']
    package_ref=seal(wheel_path.name,wheel_path.read_bytes())
    for name in ('nnfx_practice', 'strategies'):
        shutil.copytree(CODE/name, archive/('previous-'+name), ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    lock_path = DATA/'var/notebooks/notebook-a.lock'
    fd = os.open(lock_path, os.O_RDWR | os.O_NOFOLLOW)
    excluded = False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before_files = file_fingerprints()
        command('systemctl', 'stop', legacy)
        command('systemctl', 'mask', '--runtime', SERVICE)
        excluded = True
        current = properties(SERVICE)
        if current.get('ActiveState') not in ('inactive','failed') or current.get('Job') not in ('','0'):
            raise ValueError('Controller became active/pending; deployment deferred without interrupting it')
        disabled = dict(old, enabled=False)
        disabled_raw = (json.dumps(disabled, indent=2)+'\n').encode()
        replace_plan(plan_path, sha256(original).hexdigest(), disabled_raw)
        record['status'] = 'excluded; updating application'
        # No credentials, registry, strategy data, notebook or history is replaced.
        for name in ('nnfx_practice','strategies'):
            shutil.copytree(ROOT/name, CODE/name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copyfile(ROOT/'pyproject.toml', CODE/'pyproject.toml')
        for name in ('nnfx_practice','strategies'):
            for path in (CODE/name).rglob('*'):
                os.chown(path,0,0); path.chmod(0o755 if path.is_dir() else 0o644)
        command(CODE/'.venv/bin/python', '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall',
                package_ref['path'], timeout=120)
        command('install','-o','root','-g','root','-m','0644',ROOT/'deploy/nnfx-practice-qualification@.timer',
                '/etc/systemd/system/nnfx-practice-qualification@.timer')
        policy = Path('/etc/sudoers.d/nnfx-practice')
        previous_policy = q.sealed_bytes(policy)
        seal('previous-sudoers.txt', previous_policy)
        extra = ', '.join('/usr/bin/systemctl --no-ask-password '+op+' '+QUALIFICATION for op in ('start','stop'))
        updated_policy = previous_policy + ('nnfx-run ALL=(root) NOPASSWD: '+extra+'\n').encode()
        staged_policy = archive/'updated-sudoers'
        write_new(staged_policy,updated_policy,uid=0,gid=0,mode=0o440)
        command('visudo','-c','-f',staged_policy)
        command('install','-o','root','-g','root','-m','0440',staged_policy,policy)
        command('systemctl','daemon-reload')
        command('systemctl','unmask','--runtime',SERVICE)
        # Disabled plan and stopped triggers protect the fixture interval. The
        # actual notebook lock remains held; these fixtures use isolated notebooks.
        system_report = output/(identifier+'-system.json')
        command(CODE/'.venv/bin/python','-I','-B',ROOT/'tests/check_m09_system.py',
                '--preserve-existing-notebooks','--output',system_report,timeout=240)
        controls = q._document(system_report.read_bytes())
        if (controls.get('cleanup_errors') != [] or controls.get('results',{}).get('fixture_checks_passed') is not True
                or controls['results'].get('actual_notebook_files_preserved') is not True):
            raise ValueError('Updated essential system fixtures did not pass')
        controls_ref = seal('controller-controls.json',system_report.read_bytes())
        authority = dict(controller_id=CONTROLLER, notebook_id=old['notebook_id'], account_binding_sha256=old['account_binding_sha256'],
            statement='Owner request 20 November 2026: implement automatic scheduled Python 01 practice qualification, including subsequent management, without daily administrator arming.',
            schedule=q.SCHEDULE, ordinary_activation_authorized=False, ordinary_scheduled_trading_authorized=False)
        authority_ref = seal('automatic-schedule-authority.json',(json.dumps(authority,indent=2)+'\n').encode())
        plan = candidate(old, code_hash=q.code_identity(), boot=q.host_identity()[0], kernel=q.host_identity()[1],
                         controls_ref=controls_ref, authority_ref=authority_ref)
        q.validate_evidence(plan,q._evidence(plan))
        if baseline != notebook_state() or before_files != file_fingerprints():
            raise ValueError('Notebook or retained claims changed; preserve and investigate')
        quiet_window(datetime.now(UTC),q.NY)
        plan.update(enabled=True)
        raw = (json.dumps(plan,indent=2)+'\n').encode()
        replace_plan(plan_path,sha256(disabled_raw).hexdigest(),raw)
        # Checks prerequisites and both inactive schedules, without loading secrets.
        command(CODE/'.venv/bin/python','-I','-B','-m','nnfx_practice.host','qualification-check',CONTROLLER)
        record.update(status='verified; ready to arm', plan_sha256=sha256(raw).hexdigest(), after=notebook_state(),
                      system_report=str(system_report), files_preserved=True)
        # Release maintenance before enabling a regular future launch. No immediate
        # controller start, Persistent=false, same-day claims cover an elapsed one-shot.
        fcntl.flock(fd,fcntl.LOCK_UN)
        record['start_attempted'] = True
        command('systemctl','enable','--now',QUALIFICATION)
        timer = properties(QUALIFICATION)
        if timer.get('ActiveState') != 'active' or timer.get('SubState') != 'waiting' or timer.get('UnitFileState') != 'enabled':
            raise ValueError('Qualification schedule state is uncertain; inspect without retry')
        record.update(status='armed', qualification_timer=timer, ordinary_timer=properties(ORDINARY),
                      next_expiry=command('systemctl','show',QUALIFICATION,'--property=NextElapseUSecRealtime','--value').strip())
    except BaseException as error:
        record.update(status='blocked; inspect receipt before recovery', error=type(error).__name__+': '+str(error))
        if excluded:
            # Safe failure: never restore an obsolete plan/code or stop the service.
            for unit in (legacy, QUALIFICATION):
                try:
                    if unit == QUALIFICATION:
                        command('systemctl','disable','--now',unit)
                    else:
                        command('systemctl','stop',unit)
                except (RuntimeError,subprocess.TimeoutExpired):
                    pass
            record['recovery'] = 'Schedules left stopped. Preserve plan/archive/history; inspect before a new reviewed deployment.'
        raise
    finally:
        os.close(fd)
        with receipt.open('x') as target:
            json.dump(record,target,indent=2); target.write('\n')
        receipt.chmod(0o644)
        print(json.dumps({'receipt':str(receipt),'status':record['status']}),flush=True)


if __name__ == '__main__':
    main()
