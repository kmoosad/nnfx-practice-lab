"""Opt-in real user-systemd checks using broker-free, separately named fixtures.

Never loads actual .env, touches actual notebooks, or starts an ordinary trading timer.
Run outside the sandbox with host-systemd access. Evidence survives cleanup.
"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import time
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from nnfx_practice.broker import PracticeBroker
from nnfx_practice.config import Binding, PrivateConnection, StrategyManifest, read_registry
from nnfx_practice.control import MaintenanceDeferred, controller_exclusion, maintenance
from nnfx_practice.host import SystemdService
from nnfx_practice.evidence import canonical_json
from nnfx_practice.notebook import open_notebook, transaction
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.support import MANIFEST, Call, ScriptedTransport
from tests.test_m02 import account, reply


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'var/verification/m09'


def main():
    prefix = f'nnfx-m09-probe-{os.getpid()}'
    fixture = EVIDENCE / prefix
    source_paths = [*sorted((ROOT / 'nnfx_practice').glob('*.py')),
                    *sorted((ROOT / 'nnfx_practice').glob('*.sql')),
                    *(ROOT / 'tests' / name for name in ('check_m09_host.py', 'm09_worker.py', 'm09_dashboard_worker.py')),
                    *sorted((ROOT / 'deploy').glob('*.service')), *sorted((ROOT / 'deploy').glob('*.timer')),
                    ROOT / 'pyproject.toml']
    source_hashes = {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest() for path in source_paths}
    units = fixture / 'units'
    units.mkdir(parents=True)
    (fixture / 'var').mkdir()
    (fixture / 'config.toml').write_text(''.join(
        f'[[experiments]]\ncontroller_id="{c}"\nnotebook_id="notebook-{c}"\n'
        f'notebook_name="Host probe {c}"\nstrategy_version="fixture-v1"\nconnection_key="FIXTURE_{c.upper()}"\n'
        for c in ('a', 'b')))
    registry = read_registry(fixture)
    manifest = canonical_json(MANIFEST)
    bound = Binding(registry['a'], PrivateConnection('fixture-account-a', 'synthetic-not-a-token', 'USD', 50),
                    StrategyManifest(manifest, sha256(manifest.encode()).hexdigest(), 50))
    results, commands = {}, []
    all_units = [f'{prefix}@{c}.{kind}' for c in ('a', 'b') for kind in ('service', 'timer')]

    def ctl(*args, check=True):
        result = subprocess.run(['systemctl', '--user', '--no-ask-password', *args],
                                capture_output=True, text=True, timeout=30)
        commands.append(dict(at=datetime.now(UTC).isoformat(), args=args, returncode=result.returncode,
                             stdout=result.stdout, stderr=result.stderr))
        if check and result.returncode:
            raise RuntimeError(f'systemctl fixture command failed: {args}')
        return result

    def wait_for(predicate, label, seconds=15):
        deadline = time.monotonic() + seconds
        while not predicate():
            if time.monotonic() > deadline:
                raise AssertionError(label)
            time.sleep(0.1)

    def records(c='a'):
        path = fixture / 'var' / f'{c}.jsonl'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def starts(c='a'):
        return sum(row['phase'] == 'start' for row in records(c))

    def quiet(c='a'):
        return ctl('show', f'{prefix}@{c}.service', '-p', 'ActiveState', '--value').stdout.strip() in ('inactive', 'failed')

    def arm(when):
        ctl('stop', f'{prefix}@a.timer')
        override = units / f'{prefix}@a.timer.d'
        override.mkdir(exist_ok=True)
        (override / 'probe.conf').write_text('[Timer]\nOnCalendar=\nOnCalendar=' + when + '\n')
        ctl('daemon-reload')

    def future(seconds):
        return (datetime.now(UTC) + timedelta(seconds=seconds)).strftime('%Y-%m-%d %H:%M:%S UTC')

    def state():
        return ctl('show', *all_units, '-p',
                   'Id,LoadState,ActiveState,Job,Type,Restart,NRestarts,Result,AccuracyUSec,Persistent,TimersCalendar').stdout

    try:
        # Use production Type/Restart/timeout and the exact production timer.
        # Separate-user filesystem/network restrictions require the system deployment.
        service = '[Unit]\nDescription=M09 broker-free host fixture %i\n[Service]\nType=oneshot\nRestart=no\nTimeoutStartSec=infinity\n'
        service += f'ExecStart={ROOT}/.venv/bin/python {ROOT}/tests/m09_worker.py {fixture} %i\n'
        (units / f'{prefix}@.service').write_text(service)
        (units / f'{prefix}@.timer').write_text((ROOT / 'deploy/nnfx-practice@.timer').read_text().replace('nnfx-practice', prefix))
        ctl('link', str(units / f'{prefix}@.service'), str(units / f'{prefix}@.timer'))
        # Instance drop-ins under the manager's runtime directory, never ordinary units.
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'systemd/user'
        runtime.mkdir(parents=True, exist_ok=True)
        dropin_link = runtime / f'{prefix}@a.timer.d'
        (units / f'{prefix}@a.timer.d').mkdir()
        dropin_link.symlink_to(units / f'{prefix}@a.timer.d', target_is_directory=True)
        ctl('daemon-reload')
        ctl('show', *all_units)  # Materialize each inactive instance before queries.
        adapter = SystemdService('a', user=True, prefix=prefix)
        results['production_calendar_loaded'] = state()
        arm(future(3))
        ctl('start', f'{prefix}@a.timer')
        wait_for(lambda: starts() == 1 and quiet(), 'actual timer dispatch')
        results['actual_timer_dispatch'] = records()

        # Failure is recorded once and is never automatically restarted.
        (fixture / 'var/a.fail').touch()
        before = starts()
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait_for(lambda: starts() == before + 1 and quiet(), 'fixture failure')
        time.sleep(1.2)
        assert starts() == before + 1
        assert ctl('show', f'{prefix}@a.service', '-p', 'NRestarts', '--value').stdout.strip() == '0'
        results['no_restart'] = state()
        (fixture / 'var/a.fail').unlink()
        ctl('reset-failed', f'{prefix}@a.service')

        # A paused timer spans a missed calendar instant. Restart never catches up.
        arm(future(2))
        before = starts()
        time.sleep(2.5)
        ctl('start', f'{prefix}@a.timer')
        time.sleep(1.2)
        assert starts() == before
        results['inactive_missed_no_catch_up'] = state()
        arm(future(3))
        ctl('start', f'{prefix}@a.timer')
        wait_for(lambda: starts() == before + 1 and quiet(), 'next regular fixture dispatch')
        results['next_dispatch_uses_new_instant'] = records()[-2:]

        # Timer expiry and a manual second start do not duplicate an active oneshot.
        arm(future(3))
        hold = fixture / 'var/a.hold'
        hold.touch()
        before = starts()
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait_for(lambda: starts() == before + 1, 'held fixture start')
        ctl('start', '--no-block', f'{prefix}@a.service')
        ctl('start', f'{prefix}@a.timer')
        ctl('start', '--no-block', f'{prefix}@b.service')
        wait_for(lambda: starts('b') == 1 and quiet('b'), 'independent controller')
        time.sleep(3.5)
        assert starts() == before + 1
        # Busy master lock defers maintenance before changing timer state.
        try:
            with maintenance(fixture, bound, adapter):
                raise AssertionError('active fixture admitted maintenance')
        except MaintenanceDeferred:
            pass
        results['no_overlap_independent_controller_active_deferral'] = state()
        hold.unlink()
        wait_for(quiet, 'held service release')

        # Service active without the application lock: adapter must still defer.
        sleeper = units / f'{prefix}@a.service.d'
        sleeper.mkdir()
        (sleeper / 'probe.conf').write_text('[Service]\nExecStart=\nExecStart=/usr/bin/sleep 4\n')
        sleeper_link = runtime / f'{prefix}@a.service.d'
        sleeper_link.symlink_to(sleeper, target_is_directory=True)
        ctl('daemon-reload')
        ctl('start', '--no-block', f'{prefix}@a.service')
        wait_for(adapter.service_active, 'active service without application lock')
        try:
            with maintenance(fixture, bound, adapter):
                raise AssertionError('active service admitted maintenance')
        except MaintenanceDeferred:
            pass
        assert adapter.timer_active()
        wait_for(quiet, 'active service completes without interruption')
        sleeper_link.unlink()
        ctl('daemon-reload')
        results['active_service_without_lock_defers'] = True

        # Include a scheduled expiry during broker-read/notebook-write phases.
        for initially_active, fail in ((True, False), (True, True), (False, False), (False, True)):
            arm(future(2))
            if initially_active:
                ctl('start', f'{prefix}@a.timer')
            before = starts()
            phases = []
            try:
                with maintenance(fixture, bound, adapter):
                    assert not adapter.timer_active()
                    assert adapter._properties(adapter.service)['LoadState'] == 'masked'
                    for phase in ('broker_read_fixture', 'notebook_write_fixture'):
                        if phase == 'broker_read_fixture':
                            transport = ScriptedTransport((Call('GET', '/v3/accounts/fixture-account-a'), reply(account(100))))
                            with PracticeBroker(bound, transport=transport) as broker:
                                assert broker.account().boundary == '100'
                            transport.assert_consumed()
                        else:
                            with open_notebook(fixture, bound, create=True) as db:
                                with transaction(db):
                                    db.execute("INSERT OR REPLACE INTO issues(issue_id, code, first_observed_at, last_observed_at, status) "
                                               "VALUES('fixture', 'maintenance-fixture', '2026-11-19T00:00:00Z', '2026-11-19T00:00:00Z', 'open')")
                        blocked = ctl('start', '--no-block', f'{prefix}@a.service', check=False)
                        assert blocked.returncode != 0
                        with controller_exclusion(fixture, SimpleNamespace(experiment=registry['b'])):
                            pass
                        phases.append(phase)
                    time.sleep(2.5)
                    assert starts() == before
                    if fail:
                        raise ValueError('intentional maintenance fixture failure')
            except ValueError:
                if not fail:
                    raise
            assert adapter.timer_active() == initially_active
            assert adapter._properties(adapter.service)['LoadState'] == 'loaded'
            time.sleep(0.5)
            assert starts() == before
            results[f'maintenance_active={initially_active}_failure={fail}'] = dict(phases=phases, states=state())
        results['synthetic_notebooks_only'] = list(str(p.relative_to(fixture)) for p in (fixture / 'var').rglob('*.sqlite3'))

        # Try the production dashboard restrictions in user scope. Separate UIDs,
        # ProtectHome and system startup still require the administrator install.
        dashboard_unit = f'{prefix}-dashboard.service'
        all_units.append(dashboard_unit)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        (fixture / '.env').write_text('SYNTHETIC=not-a-real-credential\n')
        (fixture / '.env').chmod(0o600)
        dashboard = (ROOT / 'deploy/nnfx-practice-dashboard.service').read_text()
        dashboard = dashboard.replace('User=nnfx-view\n', '').replace('Group=nnfx-read\n', '')
        dashboard = dashboard.replace('/opt/nnfx-practice', str(ROOT)).replace('/var/lib/nnfx-practice', str(fixture))
        dashboard = dashboard.replace('ProtectHome=yes', 'ProtectHome=no\nPrivateUsers=yes')
        dashboard = dashboard.replace(f'ExecStart={ROOT}/.venv/bin/python -m nnfx_practice.serve --root {fixture} --host 0.0.0.0 --port 8878',
                                      f'ExecStart={ROOT}/.venv/bin/python {ROOT}/tests/m09_dashboard_worker.py {fixture} {port}')
        dashboard = dashboard.replace('tcp:8878', f'tcp:{port}')
        (units / dashboard_unit).write_text(dashboard)
        ctl('link', str(units / dashboard_unit))
        with open_notebook(fixture, bound) as db:
            db.execute('PRAGMA wal_autocheckpoint=0')
            with transaction(db):
                db.execute("UPDATE issues SET code='host-before-commit' WHERE issue_id='fixture'")
            started = ctl('start', dashboard_unit, check=False)
            try:
                if started.returncode:
                    raise RuntimeError('User manager could not apply dashboard sandbox; system deployment still required')
                url = f'http://127.0.0.1:{port}/notebooks/notebook-a'
                def get():
                    try:
                        with urlopen(url, timeout=1) as response:
                            return response.read().decode()
                    except OSError:
                        return ''
                wait_for(lambda: bool(get()), 'dashboard sandbox startup', seconds=5)
                assert 'host-before-commit' in get()
                db.execute('BEGIN IMMEDIATE')
                db.execute("UPDATE issues SET code='host-after-commit' WHERE issue_id='fixture'")
                assert 'host-after-commit' not in get()
                db.commit()
                assert 'host-after-commit' in get()
                try:
                    urlopen(Request(url, method='POST'), timeout=2)
                    raise AssertionError('Mutation route accepted')
                except HTTPError as error:
                    assert error.code == 405
                results['dashboard_user_sandbox_wal'] = dict(passed=True, scope='same UID, production restrictions except ProtectHome; PrivateUsers added')
            except (RuntimeError, AssertionError) as error:
                results['dashboard_user_sandbox_wal'] = dict(passed=False, unmet=str(error))
        logs = subprocess.run(['journalctl', '--user', '-u', dashboard_unit, '--no-pager', '-n', '40'],
                              capture_output=True, text=True, timeout=10)
        (fixture / 'dashboard-journal.log').write_text(logs.stdout + logs.stderr)
        ctl('stop', dashboard_unit, check=False)
        results['controller_probes_passed'] = True
        results['passed'] = results['dashboard_user_sandbox_wal']['passed']
    except BaseException as error:
        results['passed'] = False
        results['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        ctl('stop', *all_units, check=False)
        ctl('unmask', '--runtime', f'{prefix}@a.service', check=False)
        ctl('reset-failed', *all_units, check=False)
        # Remove only this run's manager links. Preserve fixture source and traces.
        for name in (f'{prefix}@a.timer.d', f'{prefix}@a.service.d'):
            path = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'systemd/user' / name
            if path.is_symlink():
                path.unlink()
        for kind in ('service', 'timer'):
            ctl('disable', f'{prefix}@.{kind}', check=False)
        ctl('disable', f'{prefix}-dashboard.service', check=False)
        ctl('daemon-reload', check=False)
        results['cleanup'] = ctl('list-unit-files', prefix + '*', '--no-pager', check=False).stdout
        report = dict(scope='actual host user-systemd; broker-free fixtures only', prefix=prefix,
                      at=datetime.now(UTC).isoformat(), source_hashes=source_hashes, results=results, commands=commands)
        (fixture / 'host-results.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(dict(evidence=str(fixture / 'host-results.json'), passed=results.get('passed'))))


if __name__ == '__main__':
    main()
