"""Read-only survey of the intended host; records unavailable prerequisites."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import socket
import subprocess


root = Path(__file__).resolve().parents[1]
commands = [
    ['systemctl', 'is-system-running'],
    ['systemctl', '--version'],
    ['timedatectl', 'show'],
    ['systemctl', 'show', 'chrony.service', '-p', 'ActiveState,ActiveEnterTimestamp'],
    ['loginctl', 'show-user', 'codexdev', '-p', 'Linger,State'],
    ['systemctl', 'show', 'user@1001.service', '-p', 'ActiveState,ActiveEnterTimestamp'],
    ['systemd-analyze', 'cat-config', 'systemd/logind.conf'],
    ['systemctl', 'show', 'sleep.target', 'suspend.target', 'hibernate.target', 'hybrid-sleep.target',
     '-p', 'Id,LoadState,ActiveState,UnitFileState'],
    ['uptime', '-s'],
    ['journalctl', '-b', '-u', 'systemd-suspend.service', '-u', 'systemd-hibernate.service', '--no-pager', '-n', '20'],
    ['systemctl', 'list-unit-files', 'nnfx-practice*', '--no-pager'],
    ['systemctl', '--user', 'list-unit-files', 'nnfx-m09-probe*', '--no-pager'],
    ['sudo', '-n', 'true'],
]
survey = dict(at=datetime.now(UTC).isoformat(), hostname=socket.gethostname(), uid=os.getuid(),
              os_release=Path('/etc/os-release').read_text(), commands=[], paths={})
for command in commands:
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    survey['commands'].append(dict(command=command, returncode=result.returncode,
                                   stdout=result.stdout, stderr=result.stderr))
for name in (root / '.env', root / 'config.toml', root / 'var/notebooks', Path('/opt/nnfx-practice'), Path('/var/lib/nnfx-practice')):
    if name.exists():
        info = name.stat()
        survey['paths'][str(name)] = dict(exists=True, mode=oct(info.st_mode & 0o7777), uid=info.st_uid, gid=info.st_gid)
    else:
        survey['paths'][str(name)] = dict(exists=False)
(root / 'var/verification/m09/host-prerequisites.json').write_text(json.dumps(survey, indent=2) + '\n')
print('Host prerequisite survey retained; no credentials read or broker requests made.')
