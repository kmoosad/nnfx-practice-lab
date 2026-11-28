"""Administrator setup. Never copies credentials, creates notebooks or starts timers."""

import argparse
import grp
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import sqlite3
import subprocess
import sys


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--registry', type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required')
    if sys.version_info < (3, 12) or not hasattr(sqlite3, 'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE'):
        parser.error('Deployment requires Python 3.12+ with SQLite NO_CKPT_ON_CLOSE support')
    if importlib.util.find_spec('ensurepip') is None:
        package = f'python{sys.version_info.major}.{sys.version_info.minor}-venv'
        parser.error(f'Missing Python venv/pip support. Install {package} '
                     f'(sudo apt-get install {package}), then rerun this installer. '
                     'No deployment changes were made by this invocation.')
    source = args.source.resolve()
    sys.path.insert(0, str(source))
    from nnfx_practice.config import read_registry
    if args.registry.name != 'config.toml':
        parser.error('Registry filename must be config.toml')
    registry = read_registry(args.registry.resolve().parent)  # Public fields only.
    code, data = Path('/opt/nnfx-practice'), Path('/var/lib/nnfx-practice')
    target = data / 'config.toml'
    if target.exists() and target.read_bytes() != args.registry.read_bytes():
        parser.error('Existing registry differs; preserve it and review the binding change separately')
    for identifier in registry:
        plan = Path('/etc/nnfx-practice/qualification') / (identifier + '.json')
        if plan.exists() or plan.is_symlink():
            parser.error('Existing qualification plan requires review before changing deployed code; do not overwrite it')
        for kind in ('service', 'timer'):
            result = subprocess.run(['systemctl', 'show', f'nnfx-practice@{identifier}.{kind}',
                                     '--property=ActiveState,LoadState,Job,UnitFileState'],
                                    capture_output=True, text=True, check=True)
            state = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
            if (state.get('ActiveState') not in ('inactive', 'failed') or state.get('Job') not in ('', '0')
                    or state.get('LoadState') == 'masked' or 'enabled' in state.get('UnitFileState', '')):
                parser.error('Defer installation while a controller/timer is active, enabled, masked or has a pending job')
    try:
        grp.getgrnam('nnfx-read')
    except KeyError:
        run('groupadd', '--system', 'nnfx-read')
    for user in ('nnfx-run', 'nnfx-view'):
        try:
            account = pwd.getpwnam(user)
            if account.pw_gid != grp.getgrnam('nnfx-read').gr_gid or account.pw_shell != '/usr/sbin/nologin':
                parser.error(f'Existing {user} does not match the dedicated service account contract')
        except KeyError:
            run('useradd', '--system', '--no-create-home', '--gid', 'nnfx-read',
                '--shell', '/usr/sbin/nologin', user)
    run('install', '-d', '-o', 'root', '-g', 'root', '-m', '0755', str(code))
    for directory in ('nnfx_practice', 'strategies'):
        shutil.copytree(source / directory, code / directory, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(source / 'pyproject.toml', code / 'pyproject.toml')
    # Service users must never be able to modify executable application code.
    for item in code.rglob('*'):
        if '.venv' not in item.parts:
            os.chown(item, 0, 0)
            item.chmod(0o755 if item.is_dir() else 0o644)
    run(sys.executable, '-m', 'venv', str(code / '.venv'))
    run(str(code / '.venv/bin/python'), '-m', 'pip', 'install', str(code))
    for directory, mode in ((data, '0750'), (data / 'var', '0750'), (data / 'var/notebooks', '2750')):
        run('install', '-d', '-o', 'nnfx-run', '-g', 'nnfx-read', '-m', mode, str(directory))
    run('install', '-o', 'root', '-g', 'nnfx-read', '-m', '0640', str(args.registry), str(target))
    shutil.copytree(source / 'strategies', data / 'strategies', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for filename in ('nnfx-practice@.service', 'nnfx-practice-dashboard.service',
                     'nnfx-practice-qualification@.timer'):
        run('install', '-o', 'root', '-g', 'root', '-m', '0644', str(source / 'deploy' / filename),
            '/etc/systemd/system/' + filename)
    # Exact unit names and operations only; no shell, arbitrary arguments or daemon-reload grant.
    commands = []
    for identifier in registry:
        stem = f'nnfx-practice@{identifier}'
        for operation in ('start', 'stop'):
            commands.append(f'/usr/bin/systemctl --no-ask-password {operation} nnfx-practice-qualification@{identifier}.timer')
        for operation in ('mask', 'unmask'):
            commands.append(f'/usr/bin/systemctl --no-ask-password {operation} --runtime {stem}.service')
    policy = code / 'sudoers.tmp'
    policy.write_text('nnfx-run ALL=(root) NOPASSWD: ' + ', '.join(commands) + '\n')
    policy.chmod(0o600)
    run('visudo', '-c', '-f', str(policy))
    run('install', '-o', 'root', '-g', 'root', '-m', '0440', str(policy), '/etc/sudoers.d/nnfx-practice')
    policy.unlink()
    run('systemctl', 'daemon-reload')
    print('Installed. Dashboard and practice schedules remain stopped until account-specific setup is authorized.')


if __name__ == '__main__':
    main()
