"""Reviewed administrator deployment of Python 03, initially without trading.

Preserves both existing histories, Python 01 scheduling and Python 02 setup.
Creates only Python 03's empty notebook; Q0 and its timer remain disabled.
"""

import argparse
from copy import deepcopy
from datetime import UTC, datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import sys
import zipfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
BASE = Path('/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03')


def registry_change(old, new):
    expected = dict(controller_id='practice-c', notebook_id='notebook-c', notebook_name='Python 03',
                    strategy_version='eye_age_supertrend_v1', connection_key='PRACTICE_C')
    if (set(old) != {'experiments'} or set(new) != {'experiments'} or len(old['experiments']) != 2
            or [row['controller_id'] for row in old['experiments']] != ['practice-a', 'practice-b']
            or new['experiments'] != [*old['experiments'], expected]):
        raise ValueError('Registry must preserve Python 01 and Python 02 and add exactly the reviewed Python 03 binding')


def private_fields(raw):
    values = {}
    for line in raw.decode().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not sep or not re.fullmatch('[A-Z][A-Z0-9_]*', key) or key in values:
            raise ValueError('Invalid private field format')
        if value.startswith(('"', "'")):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError('Invalid quoted private field')
            value = value[1:-1]
        values[key] = value
    return values


def private_change(old, new):
    required = {'PRACTICE_C_' + name for name in ('ACCOUNT_ID', 'TOKEN', 'HOME_CURRENCY', 'LOOKBACK_CANDLES')}
    if (set(new) != set(old) | required or any(new.get(k) != v for k, v in old.items())
            or new.get('PRACTICE_C_HOME_CURRENCY') != 'AUD'
            or new.get('PRACTICE_C_LOOKBACK_CANDLES') != '5000'
            or not new.get('PRACTICE_C_TOKEN')
            or not new.get('PRACTICE_C_ACCOUNT_ID')
            or new['PRACTICE_C_ACCOUNT_ID'] in {v for k, v in old.items() if k.endswith('_ACCOUNT_ID')}):
        raise ValueError('Private configuration must preserve Python 01 and Python 02 and bind a distinct reviewed account')


def updated_plan(old, code_hash, config_hash, controls_ref):
    if (old.get('version') != 2 or old.get('enabled') is not True
            or old.get('controller_id') != 'practice-a' or old.get('notebook_id') != 'notebook-a'):
        raise ValueError('Expected the existing enabled Python 01 automatic qualification plan')
    result = deepcopy(old)
    result.update(code_sha256=code_hash, config_sha256=config_hash)
    result['evidence']['m09_controller_controls'] = controls_ref
    return result


def validate_pending_bootstrap(inspection, raw, helper_hash, code_hash, config_hash, kernel):
    context = json.loads(raw)
    if (inspection.get('receipt_exists') is not False
            or sha256(raw).hexdigest() != inspection.get('context_sha256')
            or helper_hash != inspection.get('helper_sha256')
            or context.get('bootstrap_sha256') != helper_hash
            or context.get('code_sha256') != code_hash or context.get('config_sha256') != config_hash
            or context.get('kernel') != kernel):
        raise ValueError('Python 02 pending setup identity differs from the inspected deployment')


def updated_bootstrap(old, code_hash, config_hash, controls_ref):
    result = deepcopy(old)
    result.update(code_sha256=code_hash, config_sha256=config_hash)
    result['evidence']['m09_controller_controls'] = controls_ref
    return result


def open_pending_notebook_lock(path, writer):
    """Create the not-yet-run controller's lock with its native writer ownership."""
    created = False
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        created = True
    except FileExistsError:
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if created:
            os.fchown(descriptor, writer.pw_uid, writer.pw_gid)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != writer.pw_uid
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise ValueError('Pending controller lock must be a private, writer-owned regular file')
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required; nothing changed')
    base = args.base.resolve()
    if not Path('/mnt/nnfx-usb').is_mount() or not base.is_relative_to('/mnt/nnfx-usb'):
        parser.error('The mounted USB preparation is required; no fallback')
    sys.path.insert(0, str(ROOT))
    import tomllib
    from nnfx_practice import qualification as q
    from nnfx_practice.config import AccountBinding, AccountConnection, Experiment
    from deploy.upgrade_m10 import command, properties, quiet_window, file_fingerprints
    from tests.arm_m10_qualification import write_new, replace_plan
    from tests.check_m10_preparation import root_directory
    from deploy.python03_bootstrap import next_slot

    evidence, prepared = base / 'evidence', base / 'prepared'
    inspection = json.loads((evidence / 'host-inspection.json').read_bytes())
    package = json.loads((evidence / 'package-check.json').read_bytes())
    source_hashes = q.code_hashes()
    suite = (evidence / 'final-tests.log').read_text()
    if not re.search(r'Ran 42 tests in [\d.]+s\s+OK(?:\s|$)', suite):
        raise ValueError('The final 42 focused checks must pass before deployment')
    guards = (evidence / 'deployment-tests.log').read_text()
    if not re.search(r'Ran 15 tests in [\d.]+s\s+OK(?:\s|$)', guards):
        raise ValueError('The 15 history/deployment/bootstrap guard checks must pass before deployment')
    strategy_report = json.loads((ROOT / 'strategies/eye_age_supertrend_v1/qualification.json').read_bytes())
    if (strategy_report.get('status') != 'passed' or strategy_report.get('exhaustive') is not True
            or strategy_report.get('history_initialization') != dict(mode='anchored',
                start='2013-01-01T22:00:00+00:00', calendar='new_york_weekdays')
            or strategy_report.get('qualified_total_candle_count') != 5000):
        raise ValueError('Python 03 fixed-origin weekday history has not passed qualification')
    for name, digest in json.loads((evidence / 'release-files.json').read_bytes()).items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen release changed after verification')
    wheel = Path(package['wheel'])
    if package.get('status') != 'passed' or sha256(wheel.read_bytes()).hexdigest() != package['sha256']:
        raise ValueError('Verified package is missing or changed')
    with zipfile.ZipFile(wheel) as archive:
        if any(sha256(archive.read(name)).hexdigest() != digest for name, digest in source_hashes.items()):
            raise ValueError('Package and reviewed source differ')
    if any(sha256((CODE / name).read_bytes()).hexdigest() != digest for name, digest in inspection['source_hashes'].items()):
        raise ValueError('Installed source changed since inspection')
    quiet_window(datetime.now(UTC), q.NY)
    if q.host_identity()[1] != inspection['plans']['practice-a']['identity']['kernel']:
        raise ValueError('Host kernel changed; review current controls before deployment')
    plan_path = q.PLAN_DIRECTORY / 'practice-a.json'
    original = q.sealed_bytes(plan_path)
    old = q._document(original)
    if sha256(original).hexdigest() != inspection['plans']['practice-a']['sha256']:
        raise ValueError('Protected Python 01 plan changed since inspection')
    registry_raw = (DATA / 'config.toml').read_bytes()
    if sha256(registry_raw).hexdigest() != inspection['registry_sha256']:
        raise ValueError('Installed registry changed since inspection')
    new_registry = (prepared / 'config.toml').read_bytes()
    registry_change(tomllib.loads(registry_raw.decode()), tomllib.loads(new_registry.decode()))
    if (q.PLAN_DIRECTORY / 'practice-c.json').exists() or any((DATA / 'var/notebooks').glob('notebook-c.*')):
        raise ValueError('Python 03 already has production state; do not repeat this deployment')
    bootstrap_unit = 'nnfx-python03-prepare'
    if any(Path('/etc/systemd/system', bootstrap_unit + suffix).exists() for suffix in ('.service', '.timer')):
        raise ValueError('An initial Python 03 setup unit already exists; inspect instead of replacing it')
    # This addition is scoped to the inspected, not-yet-attempted Python 02 setup.
    bootstrap_b = inspection['python02_bootstrap']
    context_b_path = Path(bootstrap_b['context_path'])
    context_b_raw = q.sealed_bytes(context_b_path)
    context_b = q._document(context_b_raw)
    validate_pending_bootstrap(bootstrap_b, context_b_raw,
        sha256((CODE / 'python02_bootstrap.py').read_bytes()).hexdigest(),
        old['code_sha256'], old['config_sha256'], old['kernel'])
    old_b_units = {suffix: Path('/etc/systemd/system', 'nnfx-python02-prepare' + suffix).read_bytes()
                   for suffix in ('.service', '.timer')}
    import shlex
    commands_b = [line.split('=', 1)[1] for line in old_b_units['.service'].decode().splitlines()
                  if line.startswith('ExecStart=')]
    expected_b = [str(CODE / '.venv/bin/python'), '-I', '-B', str(CODE / 'python02_bootstrap.py'),
                  '--context', str(context_b_path)]
    if len(commands_b) != 1 or shlex.split(commands_b[0]) != expected_b:
        raise ValueError('Python 02 setup service no longer uses the inspected context')
    if ((q.PLAN_DIRECTORY / 'practice-b.json').exists()
            or (context_b_path.parent / 'bootstrap-receipt.json').exists()):
        raise ValueError('Python 02 setup has progressed; inspect and revise this addition')
    for suffix, active, enabled in (('.service', 'inactive', 'static'), ('.timer', 'active', 'enabled')):
        state = properties('nnfx-python02-prepare' + suffix)
        if state.get('ActiveState') != active or state.get('UnitFileState') != enabled or state.get('Job') not in ('', '0'):
            raise ValueError('Python 02 setup state changed; defer without interrupting it')
    writer = pwd.getpwnam('nnfx-run')
    private_path = DATA / '.env'
    info = private_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != writer.pw_uid or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Existing private connection permissions differ')
    old_private, new_private = private_path.read_bytes(), (prepared / '.env').read_bytes()
    private_change(private_fields(old_private), private_fields(new_private))
    fields = private_fields(new_private)
    experiment = Experiment(**tomllib.loads(new_registry.decode())['experiments'][2])
    bound = AccountBinding(experiment, AccountConnection(fields['PRACTICE_C_ACCOUNT_ID'], fields['PRACTICE_C_TOKEN'], 'AUD'))
    account = json.loads((evidence / 'account-preflight.json').read_bytes())
    if (account.get('status') != 'passed' or account.get('source') != 'practice_get'
            or account.get('account_binding_sha256') != q.account_identity(bound)):
        raise ValueError('Python 03 account preflight does not match the private binding')
    # Verify old evidence with the installed application before changing it.
    command(CODE / '.venv/bin/python', '-I', '-B', '-c',
            "from nnfx_practice import qualification as q; p=q._document(q.sealed_bytes(q.PLAN_DIRECTORY/'practice-a.json')); assert p['code_sha256']==q.code_identity(); q.validate_evidence(p,q._evidence(p))")
    for controller in ('practice-a', 'practice-b', 'practice-c'):
        state = properties(f'nnfx-practice@{controller}.service')
        if state.get('LoadState') != 'loaded' or state.get('ActiveState') not in ('inactive', 'failed') or state.get('Job') not in ('', '0'):
            raise ValueError('Controller must be idle; never stop a running controller')
        timer = properties(f'nnfx-practice@{controller}.timer')
        if timer.get('ActiveState') != 'inactive' or timer.get('UnitFileState') != 'disabled':
            raise ValueError('Ordinary trading must remain disabled')
    a_timer, b_timer = q.qualification_timer('practice-a'), q.qualification_timer('practice-c')
    for unit, active, enabled in ((a_timer, 'active', 'enabled'), (q.qualification_timer('practice-b'), 'inactive', 'disabled'), (b_timer, 'inactive', 'disabled')):
        state = properties(unit)
        if state.get('ActiveState') != active or state.get('UnitFileState') != enabled or state.get('Job') not in ('', '0'):
            raise ValueError('Qualification schedule differs from the inspected state')

    ident = 'python03-' + uuid4().hex[:12]
    archive = q.PLAN_DIRECTORY / 'evidence' / ident
    root_directory(archive, writer.pw_gid)
    def seal(name, raw, *, private=False):
        path = archive / name
        write_new(path, raw, uid=0, gid=0 if private else writer.pw_gid, mode=0o600 if private else 0o640)
        return dict(path=str(path), sha256=sha256(raw).hexdigest(), status='passed')
    seal('previous-plan.json', original)
    seal('previous-python02-context.json', context_b_raw)
    for suffix, raw in old_b_units.items():
        seal('preserved-python02-prepare' + suffix, raw)
    seal('previous-registry.toml', registry_raw)
    seal('previous-private.env', old_private, private=True)
    seal('candidate-private.env', new_private, private=True)
    seal('offline-tests.log', (evidence / 'final-tests.log').read_bytes())
    for name in ('nnfx_practice', 'strategies'):
        shutil.copytree(CODE / name, archive / ('previous-' + name), ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    receipt = dict(status='prepared', archive=str(archive), broker_requests=0,
                   python03_q0_initialized=False, python03_timer_enabled=False,
                   source_hashes=source_hashes, python03_account_binding_sha256=q.account_identity(bound))
    fd = fd_b = None
    excluded = False
    try:
        fd = os.open(DATA / 'var/notebooks/notebook-a.lock', os.O_RDWR | os.O_NOFOLLOW)
        fd_b = open_pending_notebook_lock(DATA / 'var/notebooks/notebook-b.lock', writer)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd_b, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = file_fingerprints()
        excluded = True
        command('systemctl', 'disable', '--now', a_timer)
        command('systemctl', 'stop', 'nnfx-python02-prepare.timer')
        pending_b = properties('nnfx-python02-prepare.service')
        if pending_b.get('ActiveState') != 'inactive' or pending_b.get('Job') not in ('', '0'):
            raise ValueError('Python 02 setup became active; preserve and investigate')
        if (context_b_path.parent / 'bootstrap-receipt.json').exists():
            raise ValueError('Python 02 setup was attempted; preserve and investigate')
        for controller in ('practice-a', 'practice-b', 'practice-c'):
            command('systemctl', 'mask', '--runtime', f'nnfx-practice@{controller}.service')
            state = properties(f'nnfx-practice@{controller}.service')
            if state.get('ActiveState') not in ('inactive', 'failed') or state.get('Job') not in ('', '0'):
                raise ValueError('Controller became active; preserve state and defer')
        disabled = json.dumps({**old, 'enabled': False}, indent=2).encode() + b'\n'
        replace_plan(plan_path, sha256(original).hexdigest(), disabled)
        for name in ('nnfx_practice', 'strategies'):
            shutil.copytree(ROOT / name, CODE / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for path in (CODE / name).rglob('*'):
                os.chown(path, 0, 0)
                path.chmod(0o755 if path.is_dir() else 0o644)
        shutil.copyfile(ROOT / 'pyproject.toml', CODE / 'pyproject.toml')
        command(CODE / '.venv/bin/python', '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall', wheel, timeout=120)
        command('install', '-o', 'root', '-g', 'nnfx-read', '-m', '0640', prepared / 'config.toml', DATA / 'config.toml')
        command('install', '-o', 'nnfx-run', '-g', 'nnfx-read', '-m', '0600', archive / 'candidate-private.env', private_path)
        new_strategy = DATA / 'strategies/eye_age_supertrend_v1'
        shutil.copytree(ROOT / 'strategies/eye_age_supertrend_v1', new_strategy)
        for path in (new_strategy, *new_strategy.rglob('*')):
            os.chown(path, 0, writer.pw_gid)
            path.chmod(0o750 if path.is_dir() else 0o640)
        policy = Path('/etc/sudoers.d/nnfx-practice')
        old_policy = policy.read_bytes()
        seal('previous-sudoers', old_policy, private=True)
        commands = [f'/usr/bin/systemctl --no-ask-password {op} {unit}' for op in ('start', 'stop')
                    for unit in ('nnfx-practice@practice-c.timer', b_timer)]
        commands += [f'/usr/bin/systemctl --no-ask-password {op} --runtime nnfx-practice@practice-c.service'
                     for op in ('mask', 'unmask')]
        ref = seal('candidate-sudoers', old_policy + ('\nnnfx-run ALL=(root) NOPASSWD: ' + ', '.join(commands) + '\n').encode(), private=True)
        command('visudo', '-c', '-f', ref['path'])
        command('install', '-o', 'root', '-g', 'root', '-m', '0440', ref['path'], policy)
        command('runuser', '-u', 'nnfx-run', '--', 'env', 'NNFX_NOTEBOOK_READ_GROUP=nnfx-read',
                CODE / '.venv/bin/python', '-I', '-B', '-c',
                "from pathlib import Path; from nnfx_practice.config import load_binding; from nnfx_practice.notebook import open_notebook; r=Path('/var/lib/nnfx-practice'); b=load_binding(r,'practice-c');\nwith open_notebook(r,b,create=True) as d: assert d.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0] is None")
        for controller in ('practice-a', 'practice-b', 'practice-c'):
            command('systemctl', 'unmask', '--runtime', f'nnfx-practice@{controller}.service')
        system_report = evidence / (ident + '-system.json')
        command(CODE / '.venv/bin/python', '-I', '-B', ROOT / 'tests/check_m09_system.py',
                '--preserve-existing-notebooks', '--output', system_report, timeout=600)
        controls = json.loads(system_report.read_bytes())
        if (controls.get('cleanup_errors') != [] or not controls.get('results', {}).get('fixture_checks_passed')
                or not controls['results'].get('actual_notebook_files_preserved')):
            raise ValueError('Updated system controls did not pass; inspect retained evidence')
        controls_ref = seal('controller-controls.json', system_report.read_bytes())
        plan = updated_plan(old, q.code_identity(), sha256(new_registry).hexdigest(), controls_ref)
        q.validate_evidence(plan, q._evidence(plan))
        q.automatic_authority(plan)
        after = file_fingerprints()
        if any(after.get(path) != fingerprint for path, fingerprint in before.items()):
            raise ValueError('Existing notebook or retained claims changed; preserve and investigate')
        quiet_window(datetime.now(UTC), q.NY)
        replace_plan(plan_path, sha256(disabled).hexdigest(), json.dumps(plan, indent=2).encode() + b'\n')
        command(CODE / '.venv/bin/python', '-I', '-B', '-m', 'nnfx_practice.host', 'qualification-check', 'practice-a')
        context_b_new = updated_bootstrap(context_b, q.code_identity(), sha256(new_registry).hexdigest(), controls_ref)
        replace_plan(context_b_path, sha256(context_b_raw).hexdigest(), json.dumps(context_b_new, indent=2).encode() + b'\n')
        if any(Path('/etc/systemd/system', 'nnfx-python02-prepare' + suffix).read_bytes() != raw
               for suffix, raw in old_b_units.items()):
            raise ValueError('Python 02 setup units changed; preserve and investigate')
        fcntl.flock(fd_b, fcntl.LOCK_UN)
        fcntl.flock(fd, fcntl.LOCK_UN)
        command('systemctl', 'enable', '--now', a_timer)
        restored = properties(a_timer)
        if any(restored.get(k) != v for k, v in (('ActiveState', 'active'), ('SubState', 'waiting'), ('UnitFileState', 'enabled'))):
            raise ValueError('Python 01 schedule restoration is uncertain; inspect without replay')
        command('systemctl', 'start', 'nnfx-python02-prepare.timer')
        restored_b = properties('nnfx-python02-prepare.timer')
        if restored_b.get('ActiveState') != 'active' or restored_b.get('SubState') != 'waiting':
            raise ValueError('Python 02 setup restoration is uncertain; inspect without replay')
        excluded = False
        # Python 01 and Python 02 are restored. The one-time Python 03 prerequisite job is
        # independent and never dispatches a trading run in its capture window.
        statement = ('Owner request on 27 November 2026: add the selected independent Python 03 practice test '
                     'under the existing trading and weekday scheduling rules, after its account-specific prerequisites pass.')
        manifest = json.loads((ROOT / 'strategies/eye_age_supertrend_v1/manifest.json').read_bytes())
        manifest_hash = sha256(q.canonical_json(manifest).encode()).hexdigest()
        authority = dict(account_label='Python 03', account_binding_sha256=q.account_identity(bound),
                         controller_id='practice-c', notebook_id='notebook-c', practice_host=q.PRACTICE_HOST,
                         manifest_sha256=manifest_hash, strategy_version='eye_age_supertrend_v1',
                         owner_statement=statement, ordinary_scheduled_trading_authorized=False,
                         ordinary_activation_authorized=False, strategy_changes_authorized=False,
                         trade_2_unit_reduction_authorized=False)
        refs = dict(strategy_qualification=seal('python03-strategy.json', (ROOT / 'strategies/eye_age_supertrend_v1/qualification.json').read_bytes()),
                    account_preflight=seal('python03-account.json', (evidence / 'account-preflight.json').read_bytes()),
                    execution_authority=seal('python03-authority.json', json.dumps(authority, indent=2).encode() + b'\n'),
                    m09_controller_controls=controls_ref)
        helper = ROOT / 'deploy/python03_bootstrap.py'
        context = dict(code_sha256=q.code_identity(), config_sha256=sha256(new_registry).hexdigest(),
                       kernel=q.host_identity()[1], account_binding_sha256=q.account_identity(bound),
                       manifest_sha256=manifest_hash, bootstrap_sha256=sha256(helper.read_bytes()).hexdigest(),
                       evidence=refs, owner_statement=statement)
        context_ref = seal('python03-context.json', json.dumps(context, indent=2).encode() + b'\n')
        command('install', '-o', 'root', '-g', 'root', '-m', '0644', helper, CODE / 'python03_bootstrap.py')
        capture_at = next_slot(datetime.now(UTC))
        service = ('[Unit]\nDescription=Python 03 initial candle check and guarded setup\n'
                   'Wants=network-online.target\nAfter=network-online.target time-sync.target\n\n'
                   '[Service]\nType=oneshot\nUser=root\nRestart=no\nTimeoutStartSec=15min\nUMask=0027\n'
                   'Environment=PYTHONDONTWRITEBYTECODE=1\nWorkingDirectory=/opt/nnfx-practice\n'
                   f'ExecStart={CODE}/.venv/bin/python -I -B {CODE}/python03_bootstrap.py --context {context_ref["path"]}\n')
        calendar = capture_at.astimezone(q.NY).strftime('%Y-%m-%d %H:%M:%S America/New_York')
        timer = (f'[Unit]\nDescription=Python 03 one-time prerequisite window\n\n[Timer]\nOnCalendar={calendar}\n'
                 f'Unit={bootstrap_unit}.service\nAccuracySec=1s\nRandomizedDelaySec=0\nPersistent=false\n\n[Install]\nWantedBy=timers.target\n')
        for suffix, raw in (('.service', service), ('.timer', timer)):
            staged = seal('python03-prepare' + suffix, raw.encode())
            command('install', '-o', 'root', '-g', 'root', '-m', '0644', staged['path'],
                    Path('/etc/systemd/system', bootstrap_unit + suffix))
        command('systemctl', 'daemon-reload')
        command('systemctl', 'enable', '--now', bootstrap_unit + '.timer')
        setup_state = properties(bootstrap_unit + '.timer')
        if setup_state.get('ActiveState') != 'active' or setup_state.get('SubState') != 'waiting':
            raise ValueError('Python 03 setup scheduling is uncertain; inspect retained units')
        # The observational server reads the registry once at process startup.
        command('systemctl', 'restart', 'nnfx-practice-dashboard.service')
        receipt.update(status='installed; Python 03 awaiting candle preflight and Q0',
                       python01_files_preserved=True, python02_files_preserved=True,
                       python02_setup_timer=restored_b, python02_context_sha256=sha256(context_b_path.read_bytes()).hexdigest(), python01_plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
                       python01_timer=restored, python03_timer=properties(b_timer),
                       controls_ref=controls_ref, system_report=str(system_report), bootstrap_context=context_ref,
                       bootstrap_timer=setup_state, capture_at=capture_at.isoformat())
    except BaseException as error:
        receipt.update(status='blocked; inspect receipt before recovery', error=type(error).__name__ + ': ' + str(error))
        if excluded:
            command('systemctl', 'disable', '--now', a_timer)
            command('systemctl', 'stop', 'nnfx-python02-prepare.timer')
        raise
    finally:
        if fd is not None:
            os.close(fd)
        if fd_b is not None:
            os.close(fd_b)
        path = evidence / (ident + '-deployment.json')
        with path.open('x') as target:
            json.dump(receipt, target, indent=2)
            target.write('\n')
        path.chmod(0o644)
        print('Deployment receipt:', path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
