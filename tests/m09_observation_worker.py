"""Credential-free system-boot/calendar observer. Never opens a notebook/broker."""

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

from nnfx_practice.config import read_registry
from nnfx_practice.control import controller_exclusion


def login_state(runner=subprocess.run):
    try:
        result = runner(['loginctl', 'list-sessions', '--json=short'], capture_output=True,
                        text=True, check=True, timeout=5)
        rows = json.loads(result.stdout)
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get('class'), str) for row in rows):
            raise ValueError('Unknown session metadata')
        classes = {}
        for row in rows:
            if (not row['class'].startswith('user') and row['class'] not in
                    ('manager', 'manager-early', 'background', 'background-light', 'greeter', 'none')):
                raise ValueError('Unknown session class')
            classes[row['class']] = classes.get(row['class'], 0) + 1
        return dict(known=True, user_sessions=sum(count for name, count in classes.items() if name.startswith('user')),
                    classes=classes)
    except (OSError, subprocess.SubprocessError, ValueError):
        return dict(known=False, user_sessions=None)


def main():
    root, role = Path(sys.argv[1]), sys.argv[2]
    if (not root.name.startswith('nnfx-m09-observe-')
            or root.parent != Path('/var/lib/nnfx-practice/var/verification')
            or role not in ('boot', 'monitor', 'scheduled')):
        raise ValueError('Expected isolated observation fixture and role')
    settings = json.loads((root / 'observation.json').read_text())
    start = datetime.fromisoformat(settings['window_start'])
    end = datetime.fromisoformat(settings['window_end'])
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    experiment = read_registry(root)[role]

    def record(phase, **fields):
        before = time.monotonic()
        boottime = time.clock_gettime(time.CLOCK_BOOTTIME)
        after = time.monotonic()
        row = dict(at=datetime.now(UTC).isoformat(), phase=phase, role=role, boot_id=boot,
                   pid=os.getpid(), uid=os.getuid(), kernel=os.uname().release,
                   invocation_id=os.environ.get('INVOCATION_ID'), uptime_seconds=boottime,
                   suspend_offset=boottime - (before + after) / 2,
                   clock_uncertainty=(after - before) / 2, **fields)
        with (root / 'var' / f'{role}.jsonl').open('a') as target:
            target.write(json.dumps(row) + '\n')
            target.flush()
            os.fsync(target.fileno())

    with controller_exclusion(root, SimpleNamespace(experiment=experiment)):
        record('start')
        if role == 'boot':
            record('boot_marker', logins=login_state())
        elif role == 'scheduled':
            record('dispatch')
        else:
            while True:
                now = datetime.now(UTC)
                record('heartbeat', logins=login_state() if start-timedelta(seconds=20) <= now <= end+timedelta(seconds=20)
                       else dict(known=False, user_sessions=None))
                remaining = (end - datetime.now(UTC)).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(min(15, remaining))
        record('finish')


if __name__ == '__main__':
    main()
