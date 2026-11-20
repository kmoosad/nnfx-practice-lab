"""Harmless systemd fixture. Public registry, lock and JSON trace only; no broker."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

from nnfx_practice.config import read_registry
from nnfx_practice.control import controller_exclusion


def main():
    root, controller = Path(sys.argv[1]), sys.argv[2]
    experiment = read_registry(root)[controller]
    binding = SimpleNamespace(experiment=experiment)
    directory = root / 'var'

    def record(phase):
        with (directory / f'{controller}.jsonl').open('a') as target:
            target.write(json.dumps(dict(controller=controller, notebook=experiment.notebook_id,
                                         phase=phase, pid=os.getpid(), at=datetime.now(UTC).isoformat())) + '\n')

    with controller_exclusion(root, binding):
        record('start')
        limit = time.monotonic() + 25
        while (directory / f'{controller}.hold').exists():
            if time.monotonic() > limit:
                raise RuntimeError('Fixture release deadline exceeded')
            time.sleep(0.05)
        record('failed' if (directory / f'{controller}.fail').exists() else 'end')
        return 7 if (directory / f'{controller}.fail').exists() else 0


if __name__ == '__main__':
    sys.exit(main())
