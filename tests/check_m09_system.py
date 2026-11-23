"""Administrator-only, broker-free fixtures under the deployed system manager.

Ordinary units remain inactive/disabled. Uses separate fixture units, synthetic
notebooks and a temporary exact-unit sudoers grant, removed in finally cleanup.
Does not read/provision credentials or initialize/activate actual notebooks.
Startup without login, wakefulness and intended 16:50 dispatch remain separate.
"""

import argparse
from datetime import UTC, datetime, timedelta
import grp
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

from nnfx_practice.config import read_registry


ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
UNIT_NAMES = ('nnfx-practice@.service', 'nnfx-practice@.timer', 'nnfx-practice-dashboard.service')
DASHBOARD_PORT = 8879


def notebook_fingerprints(paths, *, allow_existing, uid, gid):
    """Hash existing actual files without opening SQLite or creating sidecars."""
    result = {}
    for path in paths:
        files = {}
        for suffix in ('', '-wal', '-shm', '-journal'):
            item = Path(str(path) + suffix)
            try:
                descriptor = os.open(item, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                files[str(item)] = None
                continue
            with os.fdopen(descriptor, 'rb') as source:
                info = os.fstat(source.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != uid or info.st_gid != gid
                        or stat.S_IMODE(info.st_mode) != 0o640):
                    raise ValueError('Actual notebook file ownership/type/permissions require review')
                files[str(item)] = dict(sha256=sha256(source.read()).hexdigest(),
                    uid=info.st_uid, gid=info.st_gid, mode=stat.S_IMODE(info.st_mode), inode=info.st_ino)
        if not allow_existing and any(value is not None for value in files.values()):
            raise ValueError('Actual notebook exists; use --preserve-existing-notebooks after reviewing its history')
        if files[str(path)] is None and any(value is not None for value in files.values()):
            raise ValueError('Orphan actual notebook sidecars require review; nothing is repaired')
        result[str(path)] = files
    return result


def fixture_definition(service, timer, dashboard, *, prefix, fixture, worker, dashboard_worker, port):
    if not re.fullmatch(r'nnfx-m09-system-[a-f0-9]{12}', prefix):
        raise ValueError('Expected an isolated fixture unit prefix')
    expected = f'ExecStart={PYTHON} -m nnfx_practice.host --root {DATA} dispatch %i'
    if service.count(expected) != 1:
        raise ValueError('Deployed controller command differs from the reviewed template')
    service = service.replace(expected, f'ExecStart={PYTHON} {worker} {fixture} controller %i')
    service += f'\n[Service]\nInaccessiblePaths=-{DATA}/.env {DATA}/var/notebooks\nIPAddressDeny=any\n'
    timer = timer.replace('Unit=nnfx-practice@%i.service', f'Unit={prefix}@%i.service')
    expected = f'ExecStart={PYTHON} -m nnfx_practice.serve --root {DATA} --host 0.0.0.0 --port {DASHBOARD_PORT}'
    if dashboard.count(expected) != 1:
        raise ValueError('Deployed dashboard command differs from the reviewed template')
    # Translate the template before inserting the worker command: fixture itself
    # contains DATA, so translating afterward would duplicate its directory.
    dashboard = dashboard.replace(str(DATA), str(fixture))
    expected = expected.replace(str(DATA), str(fixture))
    dashboard = dashboard.replace(expected, f'ExecStart={PYTHON} {dashboard_worker} {fixture} {port}')
    dashboard = dashboard.replace(f'tcp:{DASHBOARD_PORT}', f'tcp:{port}')
    dashboard += f'\n[Service]\nInaccessiblePaths=-{DATA}/.env {DATA}/var/notebooks\n'
    return service, timer, dashboard


def fixture_policy(prefix):
    if not re.fullmatch(r'nnfx-m09-system-[a-f0-9]{12}', prefix):
        raise ValueError('Expected an isolated fixture unit prefix')
    commands = [f'/usr/bin/systemctl --no-ask-password {operation} {prefix}@a.timer'
                for operation in ('start', 'stop')]
    commands += [f'/usr/bin/systemctl --no-ask-password {operation} --runtime {prefix}@a.service'
                 for operation in ('mask', 'unmask')]
    commands += [f'/usr/bin/systemctl --no-ask-password {operation} {prefix}-qualification@a.timer'
                 for operation in ('start', 'stop')]
    return 'nnfx-run ALL=(root) NOPASSWD: ' + ', '.join(commands) + '\n'


def stage_workers(source, staged):
    staged.mkdir(parents=True, mode=0o755)
    # Dedicated service identities must traverse this public-code directory,
    # including when the administrator uses umask 077 for private evidence.
    staged.chmod(0o755)
    for name in ('m09_system_worker.py', 'm09_dashboard_worker.py'):
        shutil.copyfile(source / name, staged / name)
        (staged / name).chmod(0o644)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new credential-free JSON report; default under checkout var/verification/m09-system')
    parser.add_argument('--preserve-existing-notebooks', action='store_true',
                        help='verify existing actual notebook/sidecar bytes and ownership remain unchanged; never open SQLite')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required; no fixture or unit was changed')
    prefix = 'nnfx-m09-system-' + uuid4().hex[:12]
    output = args.output or ROOT / f'var/verification/m09-system/{prefix}.json'
    if output.exists() or output.is_symlink():
        parser.error('Use a new report filename; existing evidence is preserved')
    fixture = DATA / 'var/verification' / prefix
    staged = CODE / 'verification' / prefix
    runtime = Path('/run/systemd/system')
    policy = Path('/etc/sudoers.d') / prefix
    results, commands, created, children = {}, [], [], []
    all_units = [f'{prefix}@{c}.{kind}' for c in ('a', 'b') for kind in ('service', 'timer')]
    all_units.append(prefix + '-dashboard.service')
    auxiliary = prefix + '-qualification@a.timer'
    all_units.append(auxiliary)
    report = dict(at=datetime.now(UTC).isoformat(), classification='system-manager broker-free fixtures',
                  prefix=prefix, ordinary_units_started=False, actual_notebooks_initialized=False,
                  broker_requests=0, execution_qualified=False, host_qualification_complete=False,
                  remaining=['startup without login', 'wakefulness and intended 16:50 system dispatch',
                             'actual credential provisioning/permissions', 'production dashboard and final practice integration'],
                  results=results, commands=commands)
    report['host_context'] = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), kernel=os.uname().release)
    actual_files = None

    def run(command, *, check=True):
        try:
            result = subprocess.run([str(a) for a in command], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            result = subprocess.CompletedProcess(command, 125, '', type(error).__name__)
        commands.append(dict(at=datetime.now(UTC).isoformat(), command=[str(a) for a in command],
                             returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        if check and result.returncode:
            raise RuntimeError('Broker-free host command failed; inspect retained report')
        return result

    def ctl(*values, check=True):
        return run(['systemctl', '--no-ask-password', *values], check=check)

    def properties(unit):
        result = ctl('show', unit, '--property=LoadState,ActiveState,UnitFileState,Job,NRestarts,User,Group,Type,Restart,NoNewPrivileges')
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def ordinary_inactive():
        for identifier in registry:
            for kind in ('service', 'timer'):
                values = properties(f'nnfx-practice@{identifier}.{kind}')
                assert values['LoadState'] == 'loaded'
                assert values['ActiveState'] in ('inactive', 'failed') and values['Job'] in ('', '0')
                assert 'enabled' not in values.get('UnitFileState', '')

    def wait(predicate, label, seconds=20):
        limit = time.monotonic() + seconds
        while not predicate():
            if time.monotonic() >= limit:
                raise AssertionError(label)
            time.sleep(0.05)

    def records(stream):
        path = fixture / 'var' / f'{stream}.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def starts(identifier='a'):
        return sum(row['phase'] == 'start' for row in records(identifier))

    def quiet(identifier='a'):
        return properties(f'{prefix}@{identifier}.service')['ActiveState'] in ('inactive', 'failed')

    def release(label):
        (fixture / 'var' / f'release-{label}').touch()

    def write(path, body, mode=0o644):
        with path.open('x') as target:
            target.write(body)
        path.chmod(mode)
        created.append(path)

    def actor(mode, *arguments, background=False):
        command = ['runuser', '-u', 'nnfx-run', '--', 'env', 'PYTHONDONTWRITEBYTECODE=1',
                   'NNFX_NOTEBOOK_READ_GROUP=nnfx-read', str(PYTHON), str(worker), str(fixture), mode, *arguments]
        out = (fixture / 'var' / f'child-{len(children)}.log').open('w')
        try:
            process = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT,
                                       cwd=CODE, start_new_session=True)
        finally:
            out.close()
        children.append(process)
        commands.append(dict(at=datetime.now(UTC).isoformat(), command=command, pid=process.pid))
        if not background and process.wait(timeout=30):
            raise RuntimeError('Synthetic writer action failed; inspect fixture child log')
        return process

    def arm(seconds=4):
        ctl('stop', f'{prefix}@a.timer')
        when = datetime.now(UTC) + timedelta(seconds=seconds)
        path = runtime / f'{prefix}@a.timer.d/fixture.conf'
        path.write_text('[Timer]\nOnCalendar=\nOnCalendar=' + when.strftime('%Y-%m-%d %H:%M:%S UTC') + '\n')
        path.chmod(0o644)
        ctl('daemon-reload')
        return when

    registry = {}
    try:
        print('Checking deployment and keeping ordinary timers inactive.', flush=True)
        registry = read_registry(DATA)
        ordinary_inactive()
        clock = run(['timedatectl', 'show', '--property=NTPSynchronized']).stdout
        assert clock.strip() == 'NTPSynchronized=yes', 'Clock synchronization is not established'
        results['clock'] = clock
        writer = pwd.getpwnam('nnfx-run')
        viewer = pwd.getpwnam('nnfx-view')
        group = grp.getgrnam('nnfx-read').gr_gid
        assert writer.pw_uid != viewer.pw_uid and writer.pw_gid == viewer.pw_gid == group
        assert writer.pw_shell == viewer.pw_shell == '/usr/sbin/nologin'
        for path, uid, gid, mode in ((CODE, 0, 0, 0o755), (DATA, writer.pw_uid, group, 0o750),
                                    (DATA / 'var', writer.pw_uid, group, 0o750),
                                    (DATA / 'var/notebooks', writer.pw_uid, group, 0o2750)):
            info = path.stat()
            assert (info.st_uid, info.st_gid, info.st_mode & 0o7777) == (uid, gid, mode)
        actual_paths = [experiment.notebook_path(DATA) for experiment in registry.values()]
        actual_files = notebook_fingerprints(actual_paths, allow_existing=args.preserve_existing_notebooks,
                                             uid=writer.pw_uid, gid=group)
        report['actual_notebook_files_before'] = actual_files
        report['existing_notebooks_preserved_mode'] = args.preserve_existing_notebooks
        private = DATA / '.env'
        if private.exists():
            info = private.stat()
            assert (info.st_uid, info.st_gid, info.st_mode & 0o777) == (writer.pw_uid, group, 0o600)
            results['actual_credentials'] = 'owner-only metadata checked; contents not read'
        else:
            results['actual_credentials'] = 'unprovisioned; execution prerequisite remains open'
        report['registry_sha256'] = sha256((DATA / 'config.toml').read_bytes()).hexdigest()
        purelib = Path(run([PYTHON, '-I', '-B', '-c', 'import sysconfig; print(sysconfig.get_path("purelib"))']).stdout.strip())
        report['deployed_source_hashes'] = {}
        for package in ('nnfx_practice', 'strategies'):
            for source in sorted((ROOT / package).rglob('*')):
                if source.suffix not in ('.py', '.sql', '.json', '.html', '.css') or not source.is_file():
                    continue
                name = source.relative_to(ROOT)
                copied, installed = CODE / name, purelib / name
                expected = sha256(source.read_bytes()).hexdigest()
                assert sha256(copied.read_bytes()).hexdigest() == expected, 'Deployed source differs from reviewed checkout'
                assert sha256(installed.read_bytes()).hexdigest() == expected, 'Installed package differs from reviewed checkout'
                assert copied.stat().st_uid == installed.stat().st_uid == 0
                assert not (copied.stat().st_mode | installed.stat().st_mode) & 0o022
                report['deployed_source_hashes'][str(name)] = expected
        templates = [(Path('/etc/systemd/system') / name).read_text() for name in UNIT_NAMES]
        for name, body in zip(UNIT_NAMES, templates):
            assert body == (ROOT / 'deploy' / name).read_text(), 'Installed unit differs; review before testing'
        report['source_hashes'] = {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                                   for path in [Path(__file__), ROOT / 'tests/m09_system_worker.py',
                                                ROOT / 'tests/m09_dashboard_worker.py',
                                                *(ROOT / 'deploy' / name for name in UNIT_NAMES)]}
        for directory, mode in ((DATA / 'var/verification', 0o750), (fixture, 0o750),
                                (fixture / 'var', 0o750), (fixture / 'var/notebooks', 0o2750)):
            if directory == DATA / 'var/verification' and directory.exists():
                continue
            directory.mkdir(mode=mode)
            os.chown(directory, writer.pw_uid, group)
            directory.chmod(mode)
        stage_workers(ROOT / 'tests', staged)
        worker = staged / 'm09_system_worker.py'
        dashboard_worker = staged / 'm09_dashboard_worker.py'
        (fixture / 'config.toml').write_text(''.join(
            f'[[experiments]]\ncontroller_id="{c}"\nnotebook_id="notebook-{c}"\n'
            f'notebook_name="Synthetic host {c}"\nstrategy_version="t3_bandpass_v1"\nconnection_key="FIXTURE_{c.upper()}"\n'
            for c in ('a', 'b')))
        os.chown(fixture / 'config.toml', 0, group)
        (fixture / 'config.toml').chmod(0o640)
        (fixture / '.env').write_text('SYNTHETIC=not-a-real-credential\n')
        os.chown(fixture / '.env', writer.pw_uid, group)
        (fixture / '.env').chmod(0o600)
        actor('initialize')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        service, timer, dashboard = fixture_definition(*templates, prefix=prefix, fixture=fixture,
                                                     worker=worker, dashboard_worker=dashboard_worker, port=port)
        for filename, body in ((prefix + '@.service', service), (prefix + '@.timer', timer),
                               (prefix + '-dashboard.service', dashboard),
                               (prefix + '-qualification@a.timer', timer.replace('%i', 'a'))):
            write(runtime / filename, body)
        dropin = runtime / f'{prefix}@a.timer.d'
        dropin.mkdir()
        write(dropin / 'fixture.conf', '[Timer]\n')
        write(policy, fixture_policy(prefix), 0o440)
        run(['visudo', '-c', '-f', policy])
        ctl('daemon-reload')
        results['loaded_fixture_settings'] = ctl('show', *all_units, '--property=Id,User,Group,Type,Restart,AccuracyUSec,Persistent,TimersCalendar').stdout
        for unit, expected_user, expected_type in (
            (f'{prefix}@a.service', 'nnfx-run', 'oneshot'),
            (f'{prefix}@b.service', 'nnfx-run', 'oneshot'),
            (prefix + '-dashboard.service', 'nnfx-view', 'exec'),
        ):
            values = properties(unit)
            assert values['User'] == expected_user and values['Group'] == 'nnfx-read'
            assert values['Type'] == expected_type and values['Restart'] == 'no'
            assert values['NoNewPrivileges'] == 'yes'

        print('Checking system dispatch, restart, missed launch and overlap.', flush=True)
        arm()
        ctl('start', f'{prefix}@a.timer')
        wait(lambda: starts() == 1 and quiet(), 'system fixture dispatch')
        assert all(row['uid'] == writer.pw_uid for row in records('a'))
        results['system_timer_dispatch'] = records('a')
        (fixture / 'var/a.fail').touch()
        before = starts()
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait(lambda: starts() == before + 1 and quiet(), 'failing oneshot')
        time.sleep(1.2)
        assert starts() == before + 1 and properties(f'{prefix}@a.service')['NRestarts'] == '0'
        (fixture / 'var/a.fail').unlink()
        ctl('reset-failed', f'{prefix}@a.service')
        results['no_automatic_restart'] = True
        when = arm(2)
        before = starts()
        wait(lambda: datetime.now(UTC) > when + timedelta(seconds=1.5), 'missed fixture instant')
        ctl('start', f'{prefix}@a.timer')
        time.sleep(1.2)
        assert starts() == before
        arm()
        ctl('start', f'{prefix}@a.timer')
        wait(lambda: starts() == before + 1 and quiet(), 'next fixture instant')
        results['inactive_missed_no_catch_up'] = True
        arm()
        (fixture / 'var/a.hold').touch()
        before = starts()
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait(lambda: starts() == before + 1, 'held service')
        ctl('start', '--no-block', f'{prefix}@a.service')
        ctl('start', f'{prefix}@a.timer')
        ctl('start', '--no-block', f'{prefix}@b.service')
        wait(lambda: starts('b') == 1 and quiet('b'), 'independent controller')
        time.sleep(4.5)
        assert starts() == before + 1
        actor('maintenance', prefix, 'busy-lock', 'ok')
        assert any(r.get('tag') == 'busy-lock' and r.get('outcome') == 'deferred' for r in records('maintenance'))
        release('a')
        wait(quiet, 'held service release')
        (fixture / 'var/a.hold').unlink()
        (fixture / 'var/release-a').unlink()
        (fixture / 'var/a.no-lock').touch()
        (fixture / 'var/a.hold').touch()
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait(lambda: not quiet(), 'active service without application lock')
        actor('maintenance', prefix, 'active-service', 'ok')
        assert any(r.get('tag') == 'active-service' and r.get('outcome') == 'deferred' for r in records('maintenance'))
        release('a')
        wait(quiet, 'active service completion')
        (fixture / 'var/a.hold').unlink()
        (fixture / 'var/a.no-lock').unlink()
        results['no_overlap_independent_controller_active_deferral'] = True

        print('Checking writer maintenance with active/paused timers, success and failure.', flush=True)
        for active, failed in ((True, False), (True, True), (False, False), (False, True)):
            tag = f'active-{active}-failure-{failed}'
            when = arm(4)
            if active:
                ctl('start', f'{prefix}@a.timer')
            before = starts()
            child = actor('maintenance', prefix, tag, 'fail' if failed else 'ok', background=True)
            for phase in ('read', 'write'):
                wait(lambda: any(r.get('tag') == tag and r['phase'] == phase for r in records('maintenance')),
                     'maintenance ' + phase)
                assert properties(f'{prefix}@a.service')['LoadState'] == 'masked'
                assert properties(f'{prefix}@a.timer')['ActiveState'] == 'inactive'
                assert ctl('start', '--no-block', f'{prefix}@a.service', check=False).returncode != 0
                release(tag + '-' + phase)
            wait(lambda: any(r.get('tag') == tag and r['phase'] == 'notebook_closed' for r in records('maintenance')),
                 'notebook close before restoration')
            wait(lambda: datetime.now(UTC) > when + timedelta(seconds=1.5), 'excluded timer instant')
            assert starts() == before
            release(tag + '-finish')
            assert child.wait(timeout=15) == 0
            time.sleep(0.5)
            assert starts() == before
            assert properties(f'{prefix}@a.service')['LoadState'] == 'loaded'
            assert (properties(f'{prefix}@a.timer')['ActiveState'] == 'active') == active
            expected = 'intentional_failure' if failed else 'completed'
            assert any(r.get('tag') == tag and r.get('outcome') == expected for r in records('maintenance'))
            results[tag] = True

        print('Checking both schedules share maintenance exclusion and restore independently.', flush=True)
        results['dual_timer_maintenance'] = []
        for ordinary, qualification, failed in ((False, True, False), (False, True, True),
                                               (True, False, False), (False, False, True)):
            tag = f'dual-{ordinary}-{qualification}-{failed}'
            ctl('start' if ordinary else 'stop', f'{prefix}@a.timer')
            ctl('start' if qualification else 'stop', auxiliary)
            before = starts()
            child = actor('maintenance', prefix, tag, 'fail' if failed else 'ok', 'dual', background=True)
            for phase in ('read', 'write'):
                wait(lambda: any(r.get('tag') == tag and r['phase'] == phase for r in records('maintenance')), tag)
                assert properties(f'{prefix}@a.service')['LoadState'] == 'masked'
                assert all(properties(unit)['ActiveState'] == 'inactive' for unit in (f'{prefix}@a.timer', auxiliary))
                assert ctl('start', '--no-block', f'{prefix}@a.service', check=False).returncode != 0
                release(tag + '-' + phase)
            wait(lambda: any(r.get('tag') == tag and r['phase'] == 'notebook_closed' for r in records('maintenance')), tag)
            release(tag + '-finish')
            assert child.wait(timeout=15) == 0 and starts() == before
            assert (properties(f'{prefix}@a.timer')['ActiveState'] == 'active') == ordinary
            assert (properties(auxiliary)['ActiveState'] == 'active') == qualification
            outcome = next(r for r in records('maintenance') if r.get('tag') == tag and r['phase'] == 'result')
            assert outcome['outcome'] == ('intentional_failure' if failed else 'completed')
            results['dual_timer_maintenance'].append(dict(ordinary=ordinary, qualification=qualification,
                                                         failed=failed, outcome=outcome))
        ctl('stop', auxiliary)

        print('Checking separate dashboard identity, sandbox and committed WAL visibility.', flush=True)
        child = actor('writer', background=True)
        wait(lambda: any(r['phase'] == 'uncommitted' for r in records('writer')), 'uncommitted writer')
        ctl('start', prefix + '-dashboard.service')
        url = f'http://127.0.0.1:{port}/notebooks/notebook-a'
        def get():
            try:
                with urlopen(url, timeout=1) as response:
                    return response.read().decode()
            except OSError:
                return ''
        def dashboard_ready():
            if 'host-before-commit' in get():
                return True
            if properties(prefix + '-dashboard.service')['ActiveState'] in ('failed', 'inactive'):
                raise RuntimeError('Dashboard fixture exited before serving; inspect retained fixture journal')
            return False
        wait(dashboard_ready, 'dashboard reads committed fixture')
        pid = ctl('show', prefix + '-dashboard.service', '--property=MainPID', '--value').stdout.strip()
        assert pid.isdigit() and int(pid) > 0
        uid_line = next(line for line in (Path('/proc') / pid / 'status').read_text().splitlines() if line.startswith('Uid:'))
        assert all(int(uid) == viewer.pw_uid for uid in uid_line.split()[1:])
        results['dashboard_pid_identity'] = dict(pid=int(pid), uid=viewer.pw_uid)
        assert 'host-after-commit' not in get()
        release('writer-commit')
        wait(lambda: 'host-after-commit' in get(), 'committed WAL visibility')
        release('writer-close')
        assert child.wait(timeout=15) == 0
        assert 'host-after-commit' in get()
        for suffix in ('', '-wal', '-shm'):
            info = Path(str(fixture / 'var/notebooks/notebook-a.sqlite3') + suffix).stat()
            assert (info.st_uid, info.st_gid, info.st_mode & 0o777) == (writer.pw_uid, group, 0o640)
        try:
            urlopen(Request(url, method='POST'), timeout=2)
            raise AssertionError('Dashboard accepted POST')
        except HTTPError as error:
            assert error.code == 405
        results['dashboard_system_sandbox_and_wal'] = True
        results['fixture_checks_passed'] = True
        ordinary_inactive()
    except BaseException as error:
        report['error'] = f'{type(error).__name__}: {error}'
        results['fixture_checks_passed'] = False
    finally:
        cleanup_errors = []
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=5)
        ctl('stop', *all_units, check=False)
        ctl('unmask', '--runtime', f'{prefix}@a.service', check=False)
        run(['journalctl', '-u', prefix + '-dashboard.service', '--no-pager', '-n', '60'], check=False)
        ctl('reset-failed', *all_units, check=False)
        for path in reversed(created):
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError as error:
                cleanup_errors.append(dict(path=str(path), error=type(error).__name__))
        dropin = runtime / f'{prefix}@a.timer.d'
        try:
            if dropin.exists():
                dropin.rmdir()
        except OSError as error:
            cleanup_errors.append(dict(path=str(dropin), error=type(error).__name__))
        ctl('daemon-reload', check=False)
        results['cleanup'] = ctl('list-unit-files', prefix + '*', '--no-pager', check=False).stdout
        leftovers = [str(path) for path in runtime.glob(prefix + '*')]
        if policy.exists() or leftovers:
            cleanup_errors.append(dict(policy_remaining=policy.exists(), unit_paths_remaining=leftovers))
        if results.get('fixture_checks_passed'):
            try:
                ordinary_inactive()
            except (AssertionError, RuntimeError):
                cleanup_errors.append(dict(error='Ordinary units no longer verified inactive'))
        if actual_files is not None:
            try:
                observed = notebook_fingerprints(actual_paths, allow_existing=args.preserve_existing_notebooks,
                                                uid=writer.pw_uid, gid=group)
                results['actual_notebook_files_preserved'] = observed == actual_files
                if observed != actual_files:
                    cleanup_errors.append(dict(error='Actual notebook/sidecar bytes or metadata changed; preserve and investigate'))
            except (OSError, ValueError):
                cleanup_errors.append(dict(error='Could not verify actual notebook/sidecar preservation'))
        if report['host_context'] != dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), kernel=os.uname().release):
            cleanup_errors.append(dict(error='Boot/kernel changed during fixture checks'))
        report['cleanup_errors'] = cleanup_errors
        if cleanup_errors:
            results['fixture_checks_passed'] = False
        report['fixture_data'] = str(fixture)
        report['staged_workers'] = str(staged)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as target:
            json.dump(report, target, indent=2)
            target.write('\n')
        output.chmod(0o644)  # Report contains only public host facts/synthetic records.
        print(json.dumps(dict(report=str(output), fixture_checks_passed=results.get('fixture_checks_passed', False),
                              host_qualification_complete=False, error=report.get('error'))), flush=True)
    return 0 if results.get('fixture_checks_passed') else 1


if __name__ == '__main__':
    sys.exit(main())
