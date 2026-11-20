"""Broker-free dashboard sandbox probe, using synthetic records/credentials only."""

import errno
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace

from waitress import serve

from nnfx_practice.config import read_registry
from nnfx_practice.control import controller_exclusion
from nnfx_practice.dashboard import create_app


def check_control_commands(runner=subprocess.run):
    checks = {}
    # InaccessiblePaths can leave a stat-able placeholder. Check execution
    # denial; --version has no control effect if an isolation check fails.
    for name in ('systemctl', 'sudo'):
        try:
            runner(['/usr/bin/' + name, '--version'], capture_output=True, text=True, timeout=5)
        except (PermissionError, FileNotFoundError):
            checks[name + '_inaccessible'] = True
        else:
            raise AssertionError('Dashboard could execute ' + name)
    return checks


def main():
    root, port = Path(sys.argv[1]), int(sys.argv[2])
    checks = {}
    try:
        (root / '.env').read_text()
        raise AssertionError('Synthetic credential file was readable')
    except PermissionError:
        checks['credentials_inaccessible'] = True
    try:
        (root / 'forbidden-write').touch()
        raise AssertionError('Dashboard filesystem was writable')
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM)
        checks['filesystem_readonly'] = True
    try:
        with socket.socket() as client:
            client.connect(('127.0.0.1', port))
        raise AssertionError('Dashboard could connect out')
    except PermissionError:
        checks['outgoing_connections_denied'] = True
    try:
        binding = SimpleNamespace(experiment=read_registry(root)['a'])
        with controller_exclusion(root, binding):
            raise AssertionError('Dashboard obtained trading/maintenance lock')
    except OSError:
        checks['controller_maintenance_lock_denied'] = True
    checks.update(check_control_commands())
    print(json.dumps(checks), flush=True)
    serve(create_app(root), host='127.0.0.1', port=port)


if __name__ == '__main__':
    main()
