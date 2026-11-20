"""Broker-free system-deployment survey; inspection never qualifies execution.

Reads public configuration and host facts only. Does not read .env contents,
open notebooks, dispatch services, alter timers or contact OANDA. Run again
after administrator deployment; retain a new report rather than overwrite one.
"""

import argparse
from datetime import UTC, datetime
import grp
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import socket
import stat
import subprocess

from nnfx_practice.config import read_registry


ROOT = Path(__file__).resolve().parents[1]
PROPERTIES = 'Id,LoadState,ActiveState,UnitFileState,Job,User,Group,Type,Restart,NRestarts,Persistent,AccuracyUSec,TimersCalendar,NoNewPrivileges'


def observe_command(command, runner):
    try:
        result = runner(command, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        # Do not serialize arbitrary exception text or process environments.
        return dict(command=command, available=False, error=type(error).__name__)
    return dict(command=command, available=True, returncode=result.returncode,
                stdout=result.stdout, stderr=result.stderr)


def observe_path(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return dict(state='absent')
    except OSError as error:
        return dict(state='unavailable', error=type(error).__name__)
    return dict(state='present', mode=oct(stat.S_IMODE(info.st_mode)), uid=info.st_uid,
                gid=info.st_gid, symlink=stat.S_ISLNK(info.st_mode))


def collect(root=ROOT, *, runner=subprocess.run):
    root = root.resolve()
    registry = read_registry(root)  # Never load the private connection.
    report = dict(at=datetime.now(UTC).isoformat(), classification='host inspection; broker-free',
                  hostname=socket.gethostname(), uid=os.getuid(), commands=[], paths={}, identities={},
                  controllers={}, source_hashes={}, source_errors={}, qualification_established=False,
                  limitations=['Inspection does not establish owner review or execution authority.',
                               'System dispatch, maintenance, startup, wakefulness and deployed dashboard tests require observations.',
                               'Account GETs and offline fixtures do not establish practice execution.'])
    commands = [
        ['sudo', '-n', 'true'],
        ['systemctl', 'is-system-running'],
        ['timedatectl', 'show', '--property=NTPSynchronized', '--property=Timezone'],
        ['systemctl', 'show', 'chrony.service', '--property=ActiveState,ActiveEnterTimestamp'],
        ['systemctl', 'show', 'sleep.target', 'suspend.target', 'hibernate.target',
         '--property=Id,LoadState,ActiveState,UnitFileState'],
        ['systemd-analyze', 'cat-config', 'systemd/logind.conf'],
        ['uptime', '-s'],
        ['journalctl', '-b', '-u', 'systemd-suspend.service', '-u', 'systemd-hibernate.service',
         '--no-pager', '-n', '20'],
        ['systemd-analyze', 'calendar', '--base-time=2026-03-06 00:00:00 UTC', '--iterations=2',
         'Mon..Fri *-*-* 16:50:00 America/New_York'],
        ['systemd-analyze', 'calendar', '--base-time=2026-10-30 00:00:00 UTC', '--iterations=2',
         'Mon..Fri *-*-* 16:50:00 America/New_York'],
        ['systemctl', 'show', 'nnfx-practice-dashboard.service', '--property=' + PROPERTIES],
    ]
    for name in ('nnfx-run', 'nnfx-view'):
        try:
            account = pwd.getpwnam(name)
            report['identities'][name] = dict(state='present', uid=account.pw_uid,
                                             gid=account.pw_gid, shell=account.pw_shell)
        except KeyError:
            report['identities'][name] = dict(state='absent')
    try:
        report['identities']['nnfx-read'] = dict(state='present', gid=grp.getgrnam('nnfx-read').gr_gid)
    except KeyError:
        report['identities']['nnfx-read'] = dict(state='absent')
    for controller, experiment in registry.items():
        report['controllers'][controller] = dict(notebook_id=experiment.notebook_id,
                                                strategy_version=experiment.strategy_version)
        for kind in ('service', 'timer'):
            commands.append(['systemctl', 'show', f'nnfx-practice@{controller}.{kind}', '--property=' + PROPERTIES])
        for base in (root, Path('/var/lib/nnfx-practice')):
            # Stat only. Even an existing notebook's Q0/A0, cursor and WAL stay untouched.
            path = base / 'var/notebooks' / f'{experiment.notebook_id}.sqlite3'
            for suffix in ('', '-wal', '-shm'):
                target = Path(str(path) + suffix)
                report['paths'][str(target)] = observe_path(target)
            lock = path.with_suffix('.lock')
            report['paths'][str(lock)] = observe_path(lock)
    for path in (root / '.env', root / 'config.toml', Path('/opt/nnfx-practice'),
                 Path('/var/lib/nnfx-practice'), Path('/var/lib/nnfx-practice/.env'),
                 Path('/var/lib/nnfx-practice/var/notebooks'),
                 Path('/etc/sudoers.d/nnfx-practice'),
                 *(Path('/etc/systemd/system') / name for name in
                   ('nnfx-practice@.service', 'nnfx-practice@.timer', 'nnfx-practice-dashboard.service'))):
        report['paths'][str(path)] = observe_path(path)
    for command in commands:
        report['commands'].append(observe_command(command, runner))
    # Explicit source allowlist excludes credentials, notebooks and all prior evidence.
    sources = [root / 'config.toml', root / 'pyproject.toml',
               *sorted((root / 'nnfx_practice').rglob('*.py')),
               *sorted((root / 'nnfx_practice').glob('*.sql')),
               *sorted((root / 'nnfx_practice/templates').glob('*')),
               *sorted((root / 'strategies').rglob('*.py')),
               *sorted((root / 'strategies').rglob('*.json')),
               *sorted((root / 'deploy').glob('*.py')),
               *sorted((root / 'deploy').glob('*.service')),
               *sorted((root / 'deploy').glob('*.timer'))]
    for path in sources:
        name = str(path.relative_to(root))
        try:
            report['source_hashes'][name] = sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            report['source_errors'][name] = type(error).__name__
    report['collector_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    return report


def save_report(path, report):
    """Create private new evidence; never truncate a prior report or a symlink."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as target:
        json.dump(report, target, indent=2)
        target.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='new JSON file under var/verification/m10')
    args = parser.parse_args()
    directory = ROOT / 'var/verification/m10'
    if args.output.resolve().parent != directory.resolve() or args.output.suffix != '.json':
        parser.error('Use a new .json report directly under var/verification/m10')
    directory.mkdir(parents=True, exist_ok=True)
    if args.output.exists() or args.output.is_symlink():
        parser.error('Report already exists; retain it and choose a new filename')
    report = collect()
    try:
        save_report(args.output, report)
    except FileExistsError:
        parser.error('Report already exists; retain it and choose a new filename')
    print('Host inspection retained. Execution and activation qualification are not established.')


if __name__ == '__main__':
    main()
