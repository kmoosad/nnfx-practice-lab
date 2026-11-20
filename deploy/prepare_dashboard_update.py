"""Prepare dashboard-only stdin data as codexdev; this command has no privileges."""

import argparse
import json
from pathlib import Path
import subprocess

# This allowlist is also enforced independently by the installed root-owned helper.
from deploy.dashboard_deploy import ALLOWED, CURRENT, MAX_INPUT, RELEASES, UNIT


def prepare(source, active):
    if active.parent != RELEASES:
        raise ValueError('Unexpected active dashboard location')
    changed = {}
    for name in sorted(ALLOWED):
        body = (source / name).read_text()
        if body.encode() != (active / name).read_bytes():
            changed[name] = body
    if not changed:
        raise ValueError('No dashboard changes to deploy')
    raw = (json.dumps({'expected_release': active.name, 'files': changed}, ensure_ascii=False) + '\n').encode()
    if len(raw) > MAX_INPUT:
        raise ValueError('Dashboard changes exceed the deployment size limit')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = subprocess.check_output(['/usr/bin/systemctl', '--no-pager', 'show', UNIT,
                                         '--property=WorkingDirectory', '--value'], text=True).strip()
    active = CURRENT.resolve() if Path(directory) == CURRENT else Path(directory)
    raw = prepare(Path(__file__).resolve().parents[1], active)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print('Prepared dashboard-only update:', args.output)


if __name__ == '__main__':
    main()
