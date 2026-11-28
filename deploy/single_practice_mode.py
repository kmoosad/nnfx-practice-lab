"""Reviewed, broker-free upgrade of the three installed practice controllers.

Keeps their existing trigger identities, plans, Q0, notebooks and date claims.
Requires the frozen USB release and administrator execution. Failures preserve
the receipt/backups and leave schedules excluded; never retry automatically.
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
import subprocess
import sys
import tarfile
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
CONTROLLERS = ('practice-a', 'practice-b', 'practice-c')
LEGACY_TIMER = Path('/etc/systemd/system/nnfx-practice@.timer')
SERVICE_KEYS = ('LoadState', 'ActiveState', 'SubState', 'MainPID', 'Job', 'InvocationID',
                'ExecMainStartTimestamp', 'ExecMainExitTimestamp', 'ExecMainStatus', 'DropInPaths')
TIMER_KEYS = ('LoadState', 'ActiveState', 'SubState', 'UnitFileState', 'Job', 'DropInPaths',
              'Unit', 'Persistent', 'AccuracyUSec', 'RandomizedDelayUSec', 'TimersCalendar',
              'NextElapseUSecRealtime')


def command(*args, timeout=30):
    completed = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout,
                               env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C'})
    if completed.returncode:
        error = RuntimeError('Upgrade command failed: ' + str(args[0]) + '; inspect the retained receipt')
        error.command_details = dict(argv=[str(a) for a in args], returncode=completed.returncode,
                                     stdout=completed.stdout[-8000:], stderr=completed.stderr[-8000:])
        raise error
    return completed.stdout


def properties(unit, keys):
    raw = command('systemctl', '--no-ask-password', 'show', unit, '--property=' + ','.join(keys))
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def updated_plan(old, controller, code_hash, controls_ref):
    """Change only the two code-dependent references; preserve every other field."""
    if (old.get('controller_id') != controller or old.get('version') != 2
            or old.get('enabled') is not True or old.get('mode') not in ('qualification', 'practice')):
        raise ValueError('Expected the existing enabled practice plan for ' + controller)
    result = deepcopy(old)
    result['code_sha256'] = code_hash
    result['evidence']['m09_controller_controls'] = controls_ref
    return result


def require_idle(services, timers, legacy):
    for state in services.values():
        if (state.get('LoadState') != 'loaded' or state.get('ActiveState') != 'inactive'
                or state.get('MainPID') != '0' or state.get('Job') not in ('', '0')
                or state.get('DropInPaths') != ''):
            raise ValueError('Controller is not idle; defer without stopping it')
    for state in timers.values():
        if any(state.get(k) != v for k, v in (
                ('LoadState', 'loaded'), ('ActiveState', 'active'), ('SubState', 'waiting'),
                ('UnitFileState', 'enabled'), ('DropInPaths', '')) ) or state.get('Job') not in ('', '0'):
            raise ValueError('Expected all three existing enabled practice schedules')
    for state in legacy.values():
        if (state.get('LoadState') != 'loaded' or state.get('ActiveState') != 'inactive'
                or state.get('UnitFileState') != 'disabled' or state.get('Job') not in ('', '0')
                or state.get('DropInPaths') != ''):
            raise ValueError('Legacy trigger is not disabled and idle')


def require_restored(before_services, after_services, before_timers, after_timers):
    if before_timers != after_timers:
        raise ValueError('Original trigger settings or next scheduled times were not preserved')
    for controller, before in before_services.items():
        after = after_services[controller]
        # Reload/unmask can discard an inactive unit's cached invocation metadata.
        # It must never create a new invocation, process or pending job.
        historical = {'InvocationID', 'ExecMainStartTimestamp', 'ExecMainExitTimestamp'}
        if any(after[k] not in ('', before[k]) if k in historical else after[k] != before[k]
               for k in SERVICE_KEYS):
            raise ValueError('Controller state changed or an unexpected invocation occurred')


def tighten_code_directories(code, *, owner_uid=0, owner_gid=0):
    """Remove group-write from the two known package roots, after checking both.

    Production requires root:root ownership. Alternate expected IDs are solely
    for offline fixtures; the administrator entry point uses the defaults.
    No recursive chmod, symlink following or service operation is permitted.
    """
    opened = []
    before = {}
    try:
        for name in ('nnfx_practice', 'strategies'):
            path = code / name
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            opened.append((path, fd))
            info = os.fstat(fd)
            mode = stat.S_IMODE(info.st_mode)
            if (info.st_uid != owner_uid or info.st_gid != owner_gid
                    or mode not in (0o755, 0o775)):
                raise ValueError('Unexpected package directory ownership/mode: ' + str(path))
            before[str(path)] = dict(uid=info.st_uid, gid=info.st_gid, mode=mode)
        for path, fd in opened:
            if before[str(path)]['mode'] == 0o775:
                os.fchmod(fd, 0o755)
        return before
    finally:
        for _, fd in opened:
            os.close(fd)


def verify_dashboard_before(dashboard, config, installed_code, expected):
    """Verify the observed dashboard and the current protected-plan code baseline.

    A full shared-code upgrade can supersede old dashboard-only trading pins.
    The caller has already matched installed_code to all protected trading plans.
    Keep the deployed helper/configuration and its security contract unchanged.
    """
    if sha256(dashboard.CONFIG.read_bytes()).hexdigest() != expected['config_sha256']:
        raise ValueError('Dashboard configuration changed since preparation')
    previous = dashboard.active_release()
    if (previous != expected['release'] or
            dashboard.hashes(dashboard.file_map(dashboard.RELEASES / previous)) != expected['files']):
        raise ValueError('Active dashboard release changed since preparation')
    reviewed = deepcopy(config)
    reviewed['trading_files'] = installed_code
    dashboard.verify_host(reviewed)
    return previous


def verify_release(base):
    """Check the frozen source, completed tests and standard wheel before writes."""
    manifest = json.loads((base / 'release.json').read_bytes())
    for relative, expected in manifest['release_files'].items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_relative_to(ROOT) or '..' in path.parts:
            raise ValueError('Unsafe release path')
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen release changed after verification')
    log = base / manifest['offline_suite']['path']
    if sha256(log.read_bytes()).hexdigest() != manifest['offline_suite']['sha256']:
        raise ValueError('Offline suite changed')
    body = log.read_text()
    if not re.search(r'Ran \d+ tests? in [\d.]+s\s+OK\s*$', body):
        # Keep the original failure log when a test fixture needs correction.
        # Every failure must have an individually named, passing rerun; interrupted
        # workers or missing results cannot be converted into a passing suite.
        failures = set(re.findall(r'(?m)^(?:FAIL|ERROR): \w+ \(([^)]+)\)$', body))
        exits = re.findall(r'Worker \d+ \(exit (-?\d+)\)', body)
        if not failures or 'KeyboardInterrupt' in body or any(code not in ('0', '1') for code in exits):
            raise ValueError('A complete passing offline suite is required')
        for ref in manifest['offline_suite'].get('reruns', []):
            raw = (base / ref['path']).read_bytes()
            if sha256(raw).hexdigest() != ref['sha256'] or not re.search(r'Ran \d+ tests? in [\d.]+s\s+OK\s*$', raw.decode()):
                raise ValueError('A complete passing rerun is required')
            failures.difference_update(re.findall(r'(?m)^\w+ \(([^)]+)\) \.\.\. ok$', raw.decode()))
        if failures:
            raise ValueError('A complete passing offline suite is required')
    wheel = base / manifest['wheel']['path']
    if sha256(wheel.read_bytes()).hexdigest() != manifest['wheel']['sha256']:
        raise ValueError('Prepared wheel changed')
    with zipfile.ZipFile(wheel) as package:
        actual = {name: sha256(package.read(name)).hexdigest() for name in package.namelist()
                  if name.startswith(('nnfx_practice/', 'strategies/'))}
    if actual != manifest['code_files']:
        raise ValueError('Wheel does not exactly match the reviewed application')
    return manifest, wheel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator execution is required; no service changed')
    base = args.prepared.resolve()
    if not Path('/mnt/nnfx-usb').is_mount() or not base.is_relative_to('/mnt/nnfx-usb'):
        parser.error('Mounted USB preparation is required; no fallback')
    if (base / 'evidence/deployment.json').exists():
        parser.error('A deployment receipt already exists; inspect it instead of replaying')
    os.umask(0o077)
    os.environ['TMPDIR'] = str(base / 'tmp')
    os.environ['PIP_CACHE_DIR'] = str(base / 'cache/pip')
    sys.path.insert(0, str(ROOT))
    from nnfx_practice import qualification as q
    from nnfx_practice.config import read_registry
    from deploy import dashboard_deploy as dashboard
    from deploy.upgrade_m10 import file_fingerprints, quiet_window
    from tests.arm_m10_qualification import replace_plan, write_new

    manifest, wheel = verify_release(base)
    registry = read_registry(DATA)
    if q.code_hashes() != manifest['code_files'] or set(registry) != set(CONTROLLERS):
        raise ValueError('Release or installed registry differs from the reviewed three-account scope')
    quiet_window(datetime.now(UTC), q.NY)
    services = {c: properties(f'nnfx-practice@{c}.service', SERVICE_KEYS) for c in CONTROLLERS}
    timers = {c: properties(q.qualification_timer(c), TIMER_KEYS) for c in CONTROLLERS}
    legacy = {c: properties(f'nnfx-practice@{c}.timer', TIMER_KEYS) for c in CONTROLLERS}
    require_idle(services, timers, legacy)
    originals = {c: q.sealed_bytes(q.PLAN_DIRECTORY / (c + '.json')) for c in CONTROLLERS}
    plans = {c: q._document(raw) for c, raw in originals.items()}
    old_source = manifest['installed_before']
    for name, expected in old_source.items():
        if sha256((CODE / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Installed code changed since preparation')
    if set(old_source) - set(manifest['code_files']) != {'nnfx_practice/ordinary.py'}:
        raise ValueError('Unexpected application removal scope')
    for c, plan in plans.items():
        updated_plan(plan, c, q.code_identity(), {})
        if (plan['code_sha256'] != sha256(q.canonical_json(old_source).encode()).hexdigest()
                or plan['config_sha256'] != sha256((DATA / 'config.toml').read_bytes()).hexdigest()
                or plan['kernel'] != q.host_identity()[1]):
            raise ValueError('Existing plan no longer matches the installed code/configuration/kernel')
        lock = registry[c].notebook_path(DATA).with_suffix('.lock').lstat()
        if not stat.S_ISREG(lock.st_mode) or lock.st_nlink != 1:
            raise ValueError('Expected an existing regular notebook lock')
    if LEGACY_TIMER.read_bytes() != (ROOT / 'deploy/nnfx-practice@.timer').read_bytes():
        raise ValueError('Unexpected legacy timer definition')

    writer = pwd.getpwnam('nnfx-run')
    ident = 'single-mode-' + uuid4().hex[:12]
    archive = Path('/etc/nnfx-practice/upgrades') / ident
    archive.parent.mkdir(mode=0o750, exist_ok=True)
    archive.mkdir(mode=0o750)
    for directory in (archive.parent, archive):
        os.chown(directory, 0, writer.pw_gid)
        directory.chmod(0o750)
    def seal(name, raw):
        path = archive / name
        write_new(path, raw, uid=0, gid=writer.pw_gid, mode=0o640)
        return {'path': str(path), 'sha256': sha256(raw).hexdigest()}
    for c, raw in originals.items():
        seal(c + '-plan-before.json', raw)
    seal('legacy-timer-before', LEGACY_TIMER.read_bytes())
    old_dashboard_config = dashboard.CONFIG.read_bytes()
    if sha256(old_dashboard_config).hexdigest() != manifest['dashboard_before']['config_sha256']:
        raise ValueError('Dashboard configuration changed since preparation')
    preflight = dict(archive=str(archive), status='started', trading_service_changes=False,
                     notebook_writes=0, started_at=datetime.now(UTC).isoformat())
    try:
        dashboard.protected_parents(CODE)
        dashboard.protected(CODE, directory=True)
        # Earlier installs left these root:root directories at 0775. Tighten
        # only those known modes before the unchanged strict dashboard check.
        modes = tighten_code_directories(CODE)
        preflight['package_directory_modes_before'] = modes
        seal('package-directory-modes-before.json', json.dumps(modes, indent=2).encode())
        previous_dashboard = verify_dashboard_before(dashboard, json.loads(old_dashboard_config),
                                                      old_source, manifest['dashboard_before'])
        preflight['status'] = 'passed'
    except Exception as error:
        preflight.update(status='failed', error=str(error))
        raise
    finally:
        preflight['finished_at'] = datetime.now(UTC).isoformat()
        receipt = base / 'evidence' / ('preflight-' + ident + '.json')
        receipt.write_text(json.dumps(preflight, indent=2) + '\n')
        os.chown(receipt, base.stat().st_uid, base.stat().st_gid)
        receipt.chmod(0o600)
    seal('dashboard-config-before.json', old_dashboard_config)
    before_security = dashboard.security(dashboard.properties(dashboard.UNIT, dashboard.SECURITY))
    private_hash = sha256((DATA / '.env').read_bytes()).hexdigest()
    registry_hash = sha256((DATA / 'config.toml').read_bytes()).hexdigest()
    purelib = Path(command(CODE / '.venv/bin/python', '-I', '-B', '-c',
                           'import sysconfig; print(sysconfig.get_path("purelib"))').strip())
    with tarfile.open(archive / 'code-before.tar', 'w') as backup:
        for source, prefix in ((CODE, 'source'), (purelib, 'installed')):
            for name in ('nnfx_practice', 'strategies'):
                backup.add(source / name, arcname=prefix + '/' + name)
        for path in purelib.glob('nnfx_practice-*.dist-info'):
            backup.add(path, arcname='installed/' + path.name)
    descriptor = None
    locks = []
    result = {'status': 'started', 'archive': str(archive), 'actions': [],
              'started_at': datetime.now(UTC).isoformat(), 'services_before': services,
              'timers_before': timers, 'previous_dashboard': previous_dashboard,
              'broker_requests': 0, 'notebook_writes': 0,
              'package_directory_modes_before': modes}
    try:
        # Disable existing triggers temporarily; every state is restored only on
        # success. Masking never stops a running controller.
        for c in CONTROLLERS:
            command('systemctl', 'disable', '--now', q.qualification_timer(c))
            command('systemctl', 'mask', '--runtime', f'nnfx-practice@{c}.service')
        for c in CONTROLLERS:
            state = properties(f'nnfx-practice@{c}.service', SERVICE_KEYS)
            if state['ActiveState'] != 'inactive' or state['MainPID'] != '0' or state['Job'] not in ('', '0'):
                raise ValueError('Controller became active; preserve state and defer')
            # Open existing locks only; creating a new one could miss a live owner.
            path = registry[c].notebook_path(DATA).with_suffix('.lock')
            descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locks.append(descriptor)
            descriptor = None
        before = file_fingerprints()
        seal('notebooks-and-claims-before.json', json.dumps(before, indent=2).encode())
        disabled = {}
        for c in CONTROLLERS:
            disabled[c] = (json.dumps({**plans[c], 'enabled': False}, indent=2) + '\n').encode()
            replace_plan(q.PLAN_DIRECTORY / (c + '.json'), sha256(originals[c]).hexdigest(), disabled[c])
        result['actions'].append('all schedules excluded and plans disabled; notebook locks held')
        # The only removed application file is the retired ordinary adapter.
        for name in manifest['code_files']:
            target = CODE / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            shutil.copyfile(ROOT / name, target)
            os.chown(target, 0, 0)
            target.chmod(0o644)
        (CODE / 'nnfx_practice/ordinary.py').unlink()
        for name in ('nnfx_practice', 'strategies'):
            for path in (CODE / name, *(CODE / name).rglob('*')):
                if path.is_dir():
                    os.chown(path, 0, 0)
                    path.chmod(0o755)
        command(CODE / '.venv/bin/python', '-m', 'pip', 'install', '--no-index', '--no-deps',
                '--force-reinstall', wheel, timeout=120)
        for root in (CODE, purelib):
            for package in ('nnfx_practice', 'strategies'):
                for path in (root / package, *(root / package).rglob('*')):
                    if path.is_symlink():
                        raise ValueError('Unexpected installed package symlink')
                    os.chown(path, 0, 0)
                    path.chmod(0o755 if path.is_dir() else 0o644)
            for name, expected in manifest['code_files'].items():
                if sha256((root / name).read_bytes()).hexdigest() != expected:
                    raise ValueError('Installed package/source differs from the release')
            if (root / 'nnfx_practice/ordinary.py').exists():
                raise ValueError('Retired ordinary adapter remains installed')
        LEGACY_TIMER.unlink()
        command('systemctl', 'daemon-reload')
        # Disabled plans and held locks exclude native execution during fixtures.
        for c in CONTROLLERS:
            command('systemctl', 'unmask', '--runtime', f'nnfx-practice@{c}.service')
        report = base / 'evidence/native-host-controls.json'
        command(CODE / '.venv/bin/python', '-I', '-B', ROOT / 'tests/check_m09_system.py',
                '--preserve-existing-notebooks', '--output', report, timeout=600)
        controls = json.loads(report.read_bytes())
        if (controls.get('cleanup_errors') != [] or not controls.get('results', {}).get('fixture_checks_passed')
                or not controls['results'].get('actual_notebook_files_preserved')):
            raise ValueError('Native controls failed; inspect the retained report')
        controls_ref = {**seal('native-host-controls.json', report.read_bytes()), 'status': 'passed'}
        refreshed = {c: updated_plan(plans[c], c, q.code_identity(), controls_ref) for c in CONTROLLERS}
        for plan in refreshed.values():
            q.validate_evidence(plan, q._evidence(plan))
            q.automatic_authority(plan)
        if file_fingerprints() != before:
            raise ValueError('Notebook/sidecar/claim preservation check failed')
        for c, plan in refreshed.items():
            replace_plan(q.PLAN_DIRECTORY / (c + '.json'), sha256(disabled[c]).hexdigest(),
                         (json.dumps(plan, indent=2) + '\n').encode())
            command(CODE / '.venv/bin/python', '-I', '-B', '-m', 'nnfx_practice.host', 'practice-check', c)
        result['actions'].append('verified package and native controls; refreshed only code/control references')
        # A full administrator release is needed because the ledger also changed.
        # Existing helper permissions and service sandbox settings remain intact.
        with dashboard.locked():
            if (dashboard.active_release() != previous_dashboard
                    or dashboard.CONFIG.read_bytes() != old_dashboard_config):
                raise ValueError('Dashboard changed during the upgrade; preserve it for review')
            release = 'dashboard-' + ident
            destination = dashboard.RELEASES / release
            destination.mkdir(mode=0o755)
            destination.chmod(0o755)
            for name in manifest['code_files']:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                shutil.copyfile(ROOT / name, target)
                target.chmod(0o644)
            # mkdir(parents=True) applies the process umask to intermediate dirs.
            for path in destination.rglob('*'):
                if path.is_dir():
                    path.chmod(0o755)
            config = json.loads(old_dashboard_config)
            config.update(base_files=manifest['code_files'], trading_files=manifest['code_files'])
            dashboard.atomic_file(dashboard.CONFIG, (json.dumps(config, indent=2) + '\n').encode(), 0o644)
            dashboard.select_release(release)
            try:
                dashboard.command('restart', dashboard.UNIT)
                dashboard.health()
                dashboard.verify_host(config)
                http = dashboard.build_opener(dashboard.ProxyHandler({}), dashboard.NoRedirect())
                pages = {}
                for route in ('/controllers', '/notebooks', '/notebooks/notebook-a',
                              '/notebooks/notebook-b', '/notebooks/notebook-c'):
                    with http.open('http://127.0.0.1:8879' + route, timeout=10) as response:
                        body = response.read(dashboard.MAX_INPUT + 1)
                        if (response.status != 200 or len(body) > dashboard.MAX_INPUT
                                or b'Notebook unavailable' in body
                                or b'Ordinary trading has not been activated' in body
                                or (route.startswith('/notebooks/') and b'Practice trading account summary' not in body)):
                            raise ValueError('Single-mode dashboard verification failed')
                        pages[route] = dict(status=response.status, sha256=sha256(body).hexdigest())
                result['dashboard_pages'] = pages
            except Exception:
                dashboard.select_release(previous_dashboard)
                dashboard.atomic_file(dashboard.CONFIG, old_dashboard_config, 0o644)
                dashboard.command('restart', dashboard.UNIT)
                raise
            if dashboard.security(dashboard.properties(dashboard.UNIT, dashboard.SECURITY)) != before_security:
                raise ValueError('Dashboard restrictions changed')
            result['dashboard_release'] = release
        if (file_fingerprints() != before or sha256((DATA / '.env').read_bytes()).hexdigest() != private_hash
                or sha256((DATA / 'config.toml').read_bytes()).hexdigest() != registry_hash):
            raise ValueError('Existing records or private bindings changed')
        quiet_window(datetime.now(UTC), q.NY)
        for fd in locks:
            os.close(fd)
        locks.clear()
        for c in CONTROLLERS:
            command('systemctl', 'enable', '--now', q.qualification_timer(c))
        after_services = {c: properties(f'nnfx-practice@{c}.service', SERVICE_KEYS) for c in CONTROLLERS}
        after_timers = {c: properties(q.qualification_timer(c), TIMER_KEYS) for c in CONTROLLERS}
        require_restored(services, after_services, timers, after_timers)
        result.update(status='completed', services_after=after_services, timers_after=after_timers,
                      notebooks_and_claims_unchanged=True, credentials_and_registry_unchanged=True,
                      strategy_and_schedule_unchanged=True, dashboard_security_unchanged=True)
    except Exception as error:
        result.update(status='failed', error=str(error), recovery='Inspect protected backups and receipt; do not replay or start a controller')
        if hasattr(error, 'command_details'):
            result['failed_command'] = error.command_details
        # Never restore an uncertain scheduler or attempt a trading run as a test.
        for c in CONTROLLERS:
            for args in (('disable', '--now', q.qualification_timer(c)),
                         ('mask', '--runtime', f'nnfx-practice@{c}.service')):
                try:
                    command('systemctl', *args)
                except Exception:
                    result.setdefault('exclusion_errors', []).append(c)
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for fd in locks:
            os.close(fd)
        result['finished_at'] = datetime.now(UTC).isoformat()
        receipt = base / 'evidence/deployment.json'
        receipt.write_text(json.dumps(result, indent=2) + '\n')
        os.chown(receipt, base.stat().st_uid, base.stat().st_gid)
        receipt.chmod(0o600)
    print('Single practice mode installed; schedules and all notebook/claim files preserved. Receipt: ' + str(receipt))


if __name__ == '__main__':
    main()
