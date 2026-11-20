#!/usr/bin/python3 -I
"""Root-owned, no-argument dashboard deployer. Stdin is data, never root code."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from zoneinfo import ZoneInfo

RELEASES = Path('/opt/nnfx-dashboard')
CURRENT = RELEASES / 'current'
CONFIG = Path('/etc/nnfx-dashboard-deploy.json')
STATE = Path('/var/lib/nnfx-dashboard-deploy')
HELPER = Path('/usr/local/sbin/nnfx-dashboard-deploy')
UNIT = 'nnfx-practice-dashboard.service'
UNIT_FILE = Path('/etc/systemd/system') / UNIT
DROPIN = Path('/etc/systemd/system') / (UNIT + '.d/50-dashboard-layout.conf')
CODE = Path('/opt/nnfx-practice')
SYSTEMCTL = '/usr/bin/systemctl'
CONTROLS = ('nnfx-practice@practice-a.service', 'nnfx-practice@practice-a.timer',
            'nnfx-practice-qualification@practice-a.timer')
ALLOWED = frozenset({'nnfx_practice/dashboard.py', *('nnfx_practice/templates/' + name for name in (
    'base.html', 'controllers.html', 'controller_macros.html', 'controller_run.html', 'dashboard.css',
    'notebook.html', 'notebooks.html', 'notebook_macros.html', 'journal_macros.html'))})
ADMIN_UID = 0
MAX_INPUT = 2 * 1024 * 1024
NAME = re.compile(r'dashboard-[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SECURITY = ('User', 'Group', 'NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'PrivateTmp',
            'PrivateDevices', 'ReadOnlyPaths', 'InaccessiblePaths', 'IPAddressDeny', 'IPAddressAllow',
            'SocketBindDeny', 'SocketBindAllow', 'SystemCallFilter', 'SystemCallErrorNumber',
            'CapabilityBoundingSet', 'UMask', 'Environment', 'Restart')
UNORDERED = frozenset(('ReadOnlyPaths', 'InaccessiblePaths', 'IPAddressDeny', 'IPAddressAllow',
                       'SocketBindDeny', 'SocketBindAllow', 'CapabilityBoundingSet', 'Environment'))
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
       'SYSTEMD_PAGER': '', 'SYSTEMD_COLORS': '0'}


class Refused(ValueError):
    """An operator-safe refusal message with no submitted content."""


def digest(body):
    return sha256(body).hexdigest()


def protected(path, directory=False):
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != ADMIN_UID or info.st_mode & 0o022:
        raise Refused('Deployment path is not administrator-owned and protected')
    if not directory and info.st_nlink != 1:
        raise Refused('Deployment files must not be hard links')


def protected_parents(path):
    for parent in reversed(path.parents):
        protected(parent, directory=True)


def file_map(root):
    protected_parents(root)
    protected(root, directory=True)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise Refused('Release contains a symbolic link')
        protected(path, directory=path.is_dir())
        if path.is_file():
            result[str(path.relative_to(root))] = path.read_bytes()
    return result


def hashes(files):
    return {name: digest(body) for name, body in files.items()}


def command(*args):
    result = subprocess.run([SYSTEMCTL, '--no-pager', '--no-ask-password', *args],
                            env=ENV, cwd='/', capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Dashboard service operation failed')
    return result.stdout.strip()


def properties(unit, keys):
    return dict(line.split('=', 1) for line in command('show', unit, '--property=' + ','.join(keys)).splitlines()
                if '=' in line)


def security(settings):
    result = {}
    for key in SECURITY:
        value = settings[key]
        if key == 'SystemCallFilter':
            value = ['deny' if value.startswith('~') else 'allow', sorted(value.lstrip('~').split())]
        elif key in UNORDERED:
            value = sorted(value.split())
        result[key] = value
    return result


def control_state():
    keys = ('ActiveState', 'MainPID', 'Job', 'UnitFileState', 'NextElapseUSecRealtime')
    return {name: properties(name, keys) for name in CONTROLS}


def quiet_window():
    now = datetime.now(timezone.utc).astimezone(ZoneInfo('America/New_York'))
    if now.weekday() < 5 and (16, 35) <= (now.hour, now.minute) <= (17, 10):
        raise Refused('Wait until outside the scheduled trading window')


def idle(controls):
    runner = controls[CONTROLS[0]]
    if runner['ActiveState'] not in ('inactive', 'failed') or runner['MainPID'] != '0':
        raise Refused('Wait until the trading controller is idle')
    if any(row['Job'] not in ('', '0') for row in controls.values()):
        raise Refused('Wait until trading service jobs finish')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def health():
    # No proxy environment, redirects, response-selected URLs or unlimited reads.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    for route, marker in (('/controllers', b'controller-card'), ('/notebooks', b'notebook-card'),
                          ('/notebooks/notebook-a', b'journal-metrics')):
        for attempt in range(8):
            try:
                with opener.open('http://127.0.0.1:8879' + route, timeout=2) as response:
                    body = response.read(MAX_INPUT + 1)
                    if response.status != 200 or len(body) > MAX_INPUT or marker not in body or b'Notebook unavailable' in body:
                        raise Refused('Dashboard page verification failed')
                break
            except (URLError, TimeoutError):
                if attempt == 7:
                    raise Refused('Dashboard is unavailable after restart') from None
                time.sleep(0.25)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused('Duplicate request field')
        result[key] = value
    return result


def request(raw):
    if len(raw) > MAX_INPUT:
        raise Refused('Dashboard update exceeds the size limit')
    doc = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(doc, dict) or set(doc) != {'expected_release', 'files'}:
        raise Refused('Expected a release identity and dashboard files only')
    if not isinstance(doc['expected_release'], str) or not NAME.fullmatch(doc['expected_release']):
        raise Refused('Invalid expected release identity')
    files = doc['files']
    if not isinstance(files, dict) or not files or not files.keys() <= ALLOWED:
        raise Refused('Only the approved dashboard files can be deployed')
    if any(not isinstance(body, str) or '\x00' in body for body in files.values()):
        raise Refused('Dashboard file contents must be text')
    return doc['expected_release'], {name: body.encode('utf-8') for name, body in files.items()}


def atomic_file(path, body, mode):
    # Parent is protected, and every caller holds the deployment lock.
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('xb') as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(mode)
    os.replace(temporary, path)


def select_release(name):
    temporary = CURRENT.with_name('current.next')
    temporary.symlink_to(name)
    os.replace(temporary, CURRENT)


def active_release():
    info = CURRENT.lstat()
    name = os.readlink(CURRENT)
    if info.st_uid != ADMIN_UID or not stat.S_ISLNK(info.st_mode) or not NAME.fullmatch(name):
        raise Refused('Unexpected active dashboard release link')
    return name


def verify_host(config):
    protected(CONFIG)
    for path, expected in ((UNIT_FILE, config['unit_sha256']), (DROPIN, config['override_sha256'])):
        protected_parents(path)
        protected(path)
        if digest(path.read_bytes()) != expected:
            raise Refused('Dashboard service configuration changed; administrator review required')
    for name, expected in config['trading_files'].items():
        path = CODE / name
        protected_parents(path)
        protected(path)
        if digest(path.read_bytes()) != expected:
            raise Refused('Qualified trading code changed; administrator review required')
    state = properties(UNIT, ('ActiveState', 'WorkingDirectory', 'DropInPaths', *SECURITY))
    if (state['ActiveState'] != 'active' or state['WorkingDirectory'] != str(CURRENT)
            or state['DropInPaths'] != str(DROPIN) or security(state) != config['security']):
        raise Refused('Dashboard service restrictions changed; administrator review required')


@contextmanager
def locked():
    protected_parents(STATE)
    protected(STATE, directory=True)
    lock = STATE / 'lock'
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        protected(lock)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def deploy(raw):
    expected, overlay = request(raw)
    with locked():
        protected_parents(CONFIG)
        protected(CONFIG)
        config = json.loads(CONFIG.read_bytes())
        verify_host(config)
        quiet_window()
        before = control_state()
        idle(before)
        previous = active_release()
        if previous != expected:
            raise Refused('Dashboard changed since preparation; prepare the update again')
        files = file_map(RELEASES / previous)
        if files.keys() != config['base_files'].keys() or any(
                digest(body) != config['base_files'][name] for name, body in files.items() if name not in ALLOWED):
            raise Refused('Files outside the dashboard changed; administrator review required')
        files.update(overlay)
        identity = digest(json.dumps(hashes(files), sort_keys=True).encode())
        name = 'dashboard-deploy-' + identity[:24]
        if name == previous:
            return {'status': 'unchanged', 'release': previous}
        destination = RELEASES / name
        if destination.exists():
            if file_map(destination) != files:
                raise Refused('Existing release does not match the submitted update')
        else:
            destination.mkdir(mode=0o755)
            for relative, body in files.items():
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                with target.open('xb') as handle:
                    handle.write(body)
                target.chmod(0o644)
            # An interrupted staging operation is retained, never silently overwritten.
            if file_map(destination) != files:
                raise Refused('Release staging verification failed')
        quiet_window()
        idle(control_state())
        result = {'previous_release': previous, 'release': name, 'files_sha256': hashes(overlay),
                  'at': datetime.now(timezone.utc).isoformat()}
        switched = False
        try:
            select_release(name)
            switched = True
            command('restart', UNIT)
            health()
            verify_host(config)
            if control_state() != before:
                raise Refused('Trading service state changed during dashboard deployment')
            result['status'] = 'deployed'
        except Exception:
            result['status'] = 'failed'
            if switched:
                try:
                    select_release(previous)
                    command('restart', UNIT)
                    health()
                    verify_host(config)
                    result['rollback'] = 'previous dashboard restored'
                except Exception:
                    result['rollback'] = 'failed; administrator attention required'
            raise
        finally:
            receipt = STATE / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
            atomic_file(receipt, (json.dumps(result, indent=2) + '\n').encode(), 0o644)
            print(json.dumps({'receipt': str(receipt), **result}))
        return result


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise SystemExit('Use the installed dashboard deployer with no arguments')
    os.umask(0o022)
    try:
        deploy(sys.stdin.buffer.read(MAX_INPUT + 1))
    except Exception as error:
        # Never echo submitted file contents, service stderr or arbitrary exceptions.
        message = str(error) if isinstance(error, Refused) else type(error).__name__
        raise SystemExit('Dashboard update refused or failed: ' + message + '. Check any deployment receipt.') from None


if __name__ == '__main__':
    main()
