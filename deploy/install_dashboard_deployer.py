"""One-time administrator installation of the narrowly scoped dashboard deployer."""

import argparse
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys

POLICY = Path('/etc/sudoers.d/nnfx-dashboard-deploy')
POLICY_TEXT = 'codexdev ALL=(root) NOPASSWD: /usr/local/sbin/nnfx-dashboard-deploy ""\n'


def needs_directory_hardening(d, path):
    info = path.lstat()
    return (path in (d.CODE / 'nnfx_practice', d.CODE / 'strategies')
            and stat.S_ISDIR(info.st_mode) and info.st_uid == d.ADMIN_UID and info.st_gid == 0
            and stat.S_IMODE(info.st_mode) == 0o775)


def inspect_trading_files(d):
    """Read-only preflight; propose only the two observed root:root 0775 repairs."""
    trading, repairs = {}, []
    for folder in ('nnfx_practice', 'strategies'):
        root = d.CODE / folder
        d.protected_parents(root)
        if needs_directory_hardening(d, root):
            repairs.append(root)
        else:
            d.protected(root, directory=True)
        for path in sorted(root.rglob('*')):
            if '__pycache__' in path.parts:
                continue
            d.protected(path, directory=path.is_dir())
            if path.is_file() and path.suffix in ('.py', '.sql', '.json', '.html', '.css'):
                trading[str(path.relative_to(d.CODE))] = d.digest(path.read_bytes())
    if not trading:
        raise ValueError('Qualified trading installation is missing')
    return trading, repairs


def install(d, helper_body, unit_body):
    if os.geteuid() != 0:
        raise ValueError('Administrator access is required for this one-time setup')
    pwd.getpwnam('codexdev')
    d.quiet_window()
    before = d.control_state()
    d.idle(before)
    for path in (d.HELPER, d.CONFIG, POLICY, d.CURRENT):
        d.protected_parents(path)
        if path.exists() or path.is_symlink():
            raise ValueError('Deployment setup already exists; preserve it and inspect before reinstalling')
    d.protected(d.UNIT_FILE)
    d.protected(d.DROPIN)
    if d.UNIT_FILE.read_bytes() != unit_body:
        raise ValueError('Installed dashboard unit differs from the reviewed service definition')
    prior = d.properties(d.UNIT, ('ActiveState', 'WorkingDirectory', 'DropInPaths', *d.SECURITY))
    previous = Path(prior['WorkingDirectory'])
    if (prior['ActiveState'] != 'active' or prior['DropInPaths'] != str(d.DROPIN)
            or previous.parent != d.RELEASES or not d.NAME.fullmatch(previous.name)
            or prior['User'] != 'nnfx-view' or prior['Group'] != 'nnfx-read'):
        raise ValueError('Existing dashboard does not match the restricted service layout')
    old_override = d.DROPIN.read_bytes()
    if old_override != ('[Service]\nWorkingDirectory=' + str(previous) + '\n').encode():
        raise ValueError('Unexpected dashboard override; preserve it for review')
    base = d.file_map(previous)
    if not d.ALLOWED <= base.keys():
        raise ValueError('Existing dashboard is missing a required file')
    trading, repairs = inspect_trading_files(d)
    override = ('[Service]\nWorkingDirectory=' + str(d.CURRENT) + '\n').encode()
    config = dict(unit_sha256=d.digest(unit_body), override_sha256=d.digest(override),
                  security=d.security(prior), base_files=d.hashes(base), trading_files=trading)
    d.health()
    # Validate the exact no-argument sudo rule before enabling anything.
    temporary_policy = POLICY.with_name('.nnfx-dashboard-deploy-check')
    with temporary_policy.open('x') as handle:
        handle.write(POLICY_TEXT)
    temporary_policy.chmod(0o440)
    try:
        subprocess.run(['/usr/sbin/visudo', '-c', '-f', str(temporary_policy)],
                       env=d.ENV, check=True, capture_output=True, timeout=10)
    finally:
        temporary_policy.unlink()
    created = []
    switched = False
    try:
        # Tighten only these existing directory modes; never rewrite trading files.
        # Retain the reduced permissions even if a later installation step fails.
        for path in repairs:
            if not needs_directory_hardening(d, path):
                raise ValueError('Application directory metadata changed during setup')
            path.chmod(0o755)
            d.protected(path, directory=True)
            print('Removed group-write permission:', path)
        d.protected_parents(d.STATE)
        d.STATE.mkdir(mode=0o755, exist_ok=True)
        d.protected(d.STATE, directory=True)
        d.atomic_file(d.HELPER, helper_body, 0o755)
        created.append(d.HELPER)
        d.atomic_file(d.CONFIG, (d.json.dumps(config, indent=2) + '\n').encode(), 0o644)
        created.append(d.CONFIG)
        d.CURRENT.symlink_to(previous.name)
        created.append(d.CURRENT)
        d.quiet_window()
        d.idle(d.control_state())
        switched = True
        d.atomic_file(d.DROPIN, override, 0o644)
        d.command('daemon-reload')
        d.command('restart', d.UNIT)
        d.health()
        d.verify_host(config)
        if d.control_state() != before:
            raise ValueError('Trading controls changed during installation')
        # Grant permission only once the restricted service setup has passed.
        d.atomic_file(POLICY, POLICY_TEXT.encode(), 0o440)
        created.append(POLICY)
        subprocess.run(['/usr/sbin/visudo', '-c'], env=d.ENV, check=True, capture_output=True, timeout=10)
    except Exception:
        if POLICY in created:
            POLICY.unlink()
            created.remove(POLICY)
        if switched:
            d.atomic_file(d.DROPIN, old_override, 0o644)
            d.command('daemon-reload')
            d.command('restart', d.UNIT)
            d.health()
        for path in reversed(created):
            path.unlink()
        raise
    print('Dashboard deployment access installed for codexdev. Trading controls are unchanged.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper-sha256', required=True)
    parser.add_argument('--apply', type=Path, help='Optional prepared dashboard request to apply after setup')
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required for this one-time setup')
    os.umask(0o022)
    source = Path(__file__).resolve().with_name('dashboard_deploy.py')
    body = source.read_bytes()
    if sha256(body).hexdigest() != args.helper_sha256:
        parser.error('Deployment helper differs from the reviewed version')
    # Execute exactly the verified bytes, avoiding a second read of writable source.
    spec = importlib.util.spec_from_loader('reviewed_dashboard_deployer', loader=None)
    d = importlib.util.module_from_spec(spec)
    exec(compile(body, str(source), 'exec'), d.__dict__)
    request = args.apply.read_bytes() if args.apply else None
    if request is not None:
        d.request(request)
    install(d, body, source.with_name('nnfx-practice-dashboard.service').read_bytes())
    if request is not None:
        subprocess.run([str(d.HELPER)], input=request, env=d.ENV, cwd='/', check=True, timeout=120)


if __name__ == '__main__':
    main()
