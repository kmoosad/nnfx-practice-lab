"""Reviewed administrator deployment of Python 02, initially without trading.

Preserves Python 01 history and restores its existing qualification schedule.
Creates only Python 02's empty notebook; Q0 and its timer remain disabled.
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
BASE = Path('/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02')


def registry_change(old, new):
    expected = dict(controller_id='practice-b', notebook_id='notebook-b', notebook_name='Python 02',
                    strategy_version='drm_adaptive_bandpass_v1', connection_key='PRACTICE_B')
    if (set(old) != {'experiments'} or set(new) != {'experiments'} or len(old['experiments']) != 1
            or old['experiments'][0]['controller_id'] != 'practice-a'
            or new['experiments'] != [old['experiments'][0], expected]):
        raise ValueError('Registry must preserve Python 01 and add exactly the reviewed Python 02 binding')


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
    required = {'PRACTICE_B_' + name for name in ('ACCOUNT_ID', 'TOKEN', 'HOME_CURRENCY', 'LOOKBACK_CANDLES')}
    if (set(new) != set(old) | required or any(new.get(k) != v for k, v in old.items())
            or new.get('PRACTICE_B_HOME_CURRENCY') != 'AUD'
            or new.get('PRACTICE_B_LOOKBACK_CANDLES') != '512'
            or not new.get('PRACTICE_B_TOKEN')
            or not new.get('PRACTICE_B_ACCOUNT_ID')
            or new['PRACTICE_B_ACCOUNT_ID'] == old.get('PRACTICE_A_ACCOUNT_ID')):
        raise ValueError('Private configuration must preserve Python 01 and bind a distinct reviewed account')


def updated_plan(old, code_hash, config_hash, controls_ref):
    if (old.get('version') != 2 or old.get('enabled') is not True
            or old.get('controller_id') != 'practice-a' or old.get('notebook_id') != 'notebook-a'):
        raise ValueError('Expected the existing enabled Python 01 automatic qualification plan')
    result = deepcopy(old)
    result.update(code_sha256=code_hash, config_sha256=config_hash)
    result['evidence']['m09_controller_controls'] = controls_ref
    return result


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
    from deploy.python02_bootstrap import next_slot

    evidence, prepared = base / 'evidence', base / 'prepared'
    inspection = json.loads((evidence / 'host-inspection.json').read_bytes())
    package = json.loads((evidence / 'package-check.json').read_bytes())
    source_hashes = q.code_hashes()
    suite = (evidence / 'final-tests.log').read_text()
    if not re.search(r'Ran 16 tests in [\d.]+s\s+OK\s*$', suite):
        raise ValueError('The final 16 focused checks must pass before deployment')
    guards = (evidence / 'deployment-tests.log').read_text()
    if not re.search(r'Ran 9 tests in [\d.]+s\s+OK(?:\s|$)', guards):
        raise ValueError('The nine deployment/bootstrap guard checks must pass before deployment')
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
    if (q.PLAN_DIRECTORY / 'practice-b.json').exists() or any((DATA / 'var/notebooks').glob('notebook-b.*')):
        raise ValueError('Python 02 already has production state; do not repeat this deployment')
    bootstrap_unit = 'nnfx-python02-prepare'
    if any(Path('/etc/systemd/system', bootstrap_unit + suffix).exists() for suffix in ('.service', '.timer')):
        raise ValueError('An initial Python 02 setup unit already exists; inspect instead of replacing it')
    writer = pwd.getpwnam('nnfx-run')
    private_path = DATA / '.env'
    info = private_path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != writer.pw_uid or stat.S_IMODE(info.st_mode) != 0o600:
        raise ValueError('Existing private connection permissions differ')
    old_private, new_private = private_path.read_bytes(), (prepared / '.env').read_bytes()
    private_change(private_fields(old_private), private_fields(new_private))
    fields = private_fields(new_private)
    experiment = Experiment(**tomllib.loads(new_registry.decode())['experiments'][1])
    bound = AccountBinding(experiment, AccountConnection(fields['PRACTICE_B_ACCOUNT_ID'], fields['PRACTICE_B_TOKEN'], 'AUD'))
    account = json.loads((evidence / 'account-preflight.json').read_bytes())
    if (account.get('status') != 'passed' or account.get('source') != 'practice_get'
            or account.get('account_binding_sha256') != q.account_identity(bound)):
        raise ValueError('Python 02 account preflight does not match the private binding')
    # Verify old evidence with the installed application before changing it.
    command(CODE / '.venv/bin/python', '-I', '-B', '-c',
            "from nnfx_practice import qualification as q; p=q._document(q.sealed_bytes(q.PLAN_DIRECTORY/'practice-a.json')); assert p['code_sha256']==q.code_identity(); q.validate_evidence(p,q._evidence(p))")
    for controller in ('practice-a', 'practice-b'):
        state = properties(f'nnfx-practice@{controller}.service')
        if state.get('LoadState') != 'loaded' or state.get('ActiveState') not in ('inactive', 'failed') or state.get('Job') not in ('', '0'):
            raise ValueError('Controller must be idle; never stop a running controller')
        timer = properties(f'nnfx-practice@{controller}.timer')
        if timer.get('ActiveState') != 'inactive' or timer.get('UnitFileState') != 'disabled':
            raise ValueError('Ordinary trading must remain disabled')
    a_timer, b_timer = q.qualification_timer('practice-a'), q.qualification_timer('practice-b')
    for unit, active, enabled in ((a_timer, 'active', 'enabled'), (b_timer, 'inactive', 'disabled')):
        state = properties(unit)
        if state.get('ActiveState') != active or state.get('UnitFileState') != enabled or state.get('Job') not in ('', '0'):
            raise ValueError('Qualification schedule differs from the inspected state')

    ident = 'python02-' + uuid4().hex[:12]
    archive = q.PLAN_DIRECTORY / 'evidence' / ident
    root_directory(archive, writer.pw_gid)
    def seal(name, raw, *, private=False):
        path = archive / name
        write_new(path, raw, uid=0, gid=0 if private else writer.pw_gid, mode=0o600 if private else 0o640)
        return dict(path=str(path), sha256=sha256(raw).hexdigest(), status='passed')
    seal('previous-plan.json', original)
    seal('previous-registry.toml', registry_raw)
    seal('previous-private.env', old_private, private=True)
    seal('candidate-private.env', new_private, private=True)
    seal('offline-tests.log', (evidence / 'final-tests.log').read_bytes())
    for name in ('nnfx_practice', 'strategies'):
        shutil.copytree(CODE / name, archive / ('previous-' + name), ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    receipt = dict(status='prepared', archive=str(archive), broker_requests=0,
                   python02_q0_initialized=False, python02_timer_enabled=False,
                   source_hashes=source_hashes, python02_account_binding_sha256=q.account_identity(bound))
    fd = os.open(DATA / 'var/notebooks/notebook-a.lock', os.O_RDWR | os.O_NOFOLLOW)
    excluded = False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = file_fingerprints()
        command('systemctl', 'disable', '--now', a_timer)
        excluded = True
        for controller in ('practice-a', 'practice-b'):
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
        new_strategy = DATA / 'strategies/drm_adaptive_bandpass_v1'
        shutil.copytree(ROOT / 'strategies/drm_adaptive_bandpass_v1', new_strategy)
        for path in (new_strategy, *new_strategy.rglob('*')):
            os.chown(path, 0, writer.pw_gid)
            path.chmod(0o750 if path.is_dir() else 0o640)
        policy = Path('/etc/sudoers.d/nnfx-practice')
        old_policy = policy.read_bytes()
        seal('previous-sudoers', old_policy, private=True)
        commands = [f'/usr/bin/systemctl --no-ask-password {op} {unit}' for op in ('start', 'stop')
                    for unit in ('nnfx-practice@practice-b.timer', b_timer)]
        commands += [f'/usr/bin/systemctl --no-ask-password {op} --runtime nnfx-practice@practice-b.service'
                     for op in ('mask', 'unmask')]
        ref = seal('candidate-sudoers', old_policy + ('\nnnfx-run ALL=(root) NOPASSWD: ' + ', '.join(commands) + '\n').encode(), private=True)
        command('visudo', '-c', '-f', ref['path'])
        command('install', '-o', 'root', '-g', 'root', '-m', '0440', ref['path'], policy)
        command('runuser', '-u', 'nnfx-run', '--', 'env', 'NNFX_NOTEBOOK_READ_GROUP=nnfx-read',
                CODE / '.venv/bin/python', '-I', '-B', '-c',
                "from pathlib import Path; from nnfx_practice.config import load_binding; from nnfx_practice.notebook import open_notebook; r=Path('/var/lib/nnfx-practice'); b=load_binding(r,'practice-b');\nwith open_notebook(r,b,create=True) as d: assert d.execute('SELECT qualification_snapshot_id FROM notebook').fetchone()[0] is None")
        for controller in ('practice-a', 'practice-b'):
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
        fcntl.flock(fd, fcntl.LOCK_UN)
        command('systemctl', 'enable', '--now', a_timer)
        restored = properties(a_timer)
        if any(restored.get(k) != v for k, v in (('ActiveState', 'active'), ('SubState', 'waiting'), ('UnitFileState', 'enabled'))):
            raise ValueError('Python 01 schedule restoration is uncertain; inspect without replay')
        excluded = False
        # Python 01 is restored. The one-time Python 02 prerequisite job is
        # independent and never dispatches a trading run in its capture window.
        statement = ('Owner request on 27 November 2026: add the selected independent Python 02 practice test '
                     'under the existing trading and weekday scheduling rules, after its account-specific prerequisites pass.')
        manifest = json.loads((ROOT / 'strategies/drm_adaptive_bandpass_v1/manifest.json').read_bytes())
        manifest_hash = sha256(q.canonical_json(manifest).encode()).hexdigest()
        authority = dict(account_label='Python 02', account_binding_sha256=q.account_identity(bound),
                         controller_id='practice-b', notebook_id='notebook-b', practice_host=q.PRACTICE_HOST,
                         manifest_sha256=manifest_hash, strategy_version='drm_adaptive_bandpass_v1',
                         owner_statement=statement, ordinary_scheduled_trading_authorized=False,
                         ordinary_activation_authorized=False, strategy_changes_authorized=False,
                         trade_2_unit_reduction_authorized=False)
        refs = dict(strategy_qualification=seal('python02-strategy.json', (ROOT / 'strategies/drm_adaptive_bandpass_v1/qualification.json').read_bytes()),
                    account_preflight=seal('python02-account.json', (evidence / 'account-preflight.json').read_bytes()),
                    execution_authority=seal('python02-authority.json', json.dumps(authority, indent=2).encode() + b'\n'),
                    m09_controller_controls=controls_ref)
        helper = ROOT / 'deploy/python02_bootstrap.py'
        context = dict(code_sha256=q.code_identity(), config_sha256=sha256(new_registry).hexdigest(),
                       kernel=q.host_identity()[1], account_binding_sha256=q.account_identity(bound),
                       manifest_sha256=manifest_hash, bootstrap_sha256=sha256(helper.read_bytes()).hexdigest(),
                       evidence=refs, owner_statement=statement)
        context_ref = seal('python02-context.json', json.dumps(context, indent=2).encode() + b'\n')
        command('install', '-o', 'root', '-g', 'root', '-m', '0644', helper, CODE / 'python02_bootstrap.py')
        capture_at = next_slot(datetime.now(UTC))
        service = ('[Unit]\nDescription=Python 02 initial candle check and guarded setup\n'
                   'Wants=network-online.target\nAfter=network-online.target time-sync.target\n\n'
                   '[Service]\nType=oneshot\nUser=root\nRestart=no\nTimeoutStartSec=15min\nUMask=0027\n'
                   'Environment=PYTHONDONTWRITEBYTECODE=1\nWorkingDirectory=/opt/nnfx-practice\n'
                   f'ExecStart={CODE}/.venv/bin/python -I -B {CODE}/python02_bootstrap.py --context {context_ref["path"]}\n')
        calendar = capture_at.astimezone(q.NY).strftime('%Y-%m-%d %H:%M:%S America/New_York')
        timer = (f'[Unit]\nDescription=Python 02 one-time prerequisite window\n\n[Timer]\nOnCalendar={calendar}\n'
                 f'Unit={bootstrap_unit}.service\nAccuracySec=1s\nRandomizedDelaySec=0\nPersistent=false\n\n[Install]\nWantedBy=timers.target\n')
        for suffix, raw in (('.service', service), ('.timer', timer)):
            staged = seal('python02-prepare' + suffix, raw.encode())
            command('install', '-o', 'root', '-g', 'root', '-m', '0644', staged['path'],
                    Path('/etc/systemd/system', bootstrap_unit + suffix))
        command('systemctl', 'daemon-reload')
        command('systemctl', 'enable', '--now', bootstrap_unit + '.timer')
        setup_state = properties(bootstrap_unit + '.timer')
        if setup_state.get('ActiveState') != 'active' or setup_state.get('SubState') != 'waiting':
            raise ValueError('Python 02 setup scheduling is uncertain; inspect retained units')
        # The observational server reads the registry once at process startup.
        command('systemctl', 'restart', 'nnfx-practice-dashboard.service')
        receipt.update(status='installed; Python 02 awaiting candle preflight and Q0',
                       python01_files_preserved=True, python01_plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),
                       python01_timer=restored, python02_timer=properties(b_timer),
                       controls_ref=controls_ref, system_report=str(system_report), bootstrap_context=context_ref,
                       bootstrap_timer=setup_state, capture_at=capture_at.isoformat())
    except BaseException as error:
        receipt.update(status='blocked; inspect receipt before recovery', error=type(error).__name__ + ': ' + str(error))
        if excluded:
            command('systemctl', 'disable', '--now', a_timer)
        raise
    finally:
        os.close(fd)
        path = evidence / (ident + '-deployment.json')
        with path.open('x') as target:
            json.dump(receipt, target, indent=2)
            target.write('\n')
        path.chmod(0o644)
        print('Deployment receipt:', path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
