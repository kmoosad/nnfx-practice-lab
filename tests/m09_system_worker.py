"""Staged system-fixture worker: synthetic bindings only, never a live transport."""

from contextlib import nullcontext
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time

from strategies import t3_bandpass_v1 as strategy
from nnfx_practice.broker import HTTPReply, PracticeBroker
from nnfx_practice.config import Binding, PrivateConnection, StrategyManifest, read_registry
from nnfx_practice.control import MaintenanceDeferred, controller_exclusion, maintenance
from nnfx_practice.evidence import canonical_json
from nnfx_practice.host import SystemdService
from nnfx_practice.notebook import open_notebook, transaction


def fixture_binding(root, controller='a'):
    manifest = canonical_json(json.loads(Path(strategy.__file__).with_name('manifest.json').read_text()))
    return Binding(read_registry(root)[controller],
                   PrivateConnection(f'synthetic-account-{controller}', 'synthetic-not-a-token', 'USD', 386),
                   StrategyManifest(manifest, sha256(manifest.encode()).hexdigest(), 386))


def record(root, stream, phase, **fields):
    with (root / 'var' / f'{stream}.jsonl').open('a') as target:
        target.write(json.dumps(dict(at=datetime.now(UTC).isoformat(), phase=phase,
                                     pid=os.getpid(), uid=os.getuid(), gid=os.getgid(), **fields)) + '\n')


def release(root, label):
    deadline = time.monotonic() + 30
    while not (root / 'var' / f'release-{label}').exists():
        if time.monotonic() > deadline:
            raise RuntimeError('Synthetic fixture release deadline exceeded')
        time.sleep(0.05)


def initialize(root):
    for controller in ('a', 'b'):
        binding = fixture_binding(root, controller)
        with controller_exclusion(root, binding), open_notebook(root, binding, create=True) as db:
            with transaction(db):
                db.execute("INSERT INTO issues(issue_id, code, first_observed_at, last_observed_at, status) "
                           "VALUES('fixture', 'host-before-commit', ?, ?, 'open')",
                           (datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))


def controller(root, identifier):
    bound = fixture_binding(root, identifier)
    exclusion = nullcontext() if (root / 'var' / f'{identifier}.no-lock').exists() else controller_exclusion(root, bound)
    with exclusion:
        record(root, identifier, 'start', controller=identifier, notebook=bound.experiment.notebook_id)
        if (root / 'var' / f'{identifier}.hold').exists():
            release(root, identifier)
        failed = (root / 'var' / f'{identifier}.fail').exists()
        record(root, identifier, 'failed' if failed else 'end', controller=identifier)
        return 7 if failed else 0


class SyntheticRead:
    def __init__(self, binding):
        self.binding = binding
        self.calls = 0

    def request(self, method, path, payload=None):
        expected = '/v3/accounts/' + self.binding.connection.account_id
        if method != 'GET' or path != expected or payload is not None or self.calls:
            raise AssertionError('Unexpected synthetic request')
        self.calls += 1
        return HTTPReply(200, {'lastTransactionID': '100', 'account': {
            'id': self.binding.connection.account_id, 'currency': 'USD', 'balance': '1000',
            'lastTransactionID': '100', 'trades': [], 'orders': []}})


class IntendedFailure(Exception):
    pass


def maintain(root, prefix, tag, fail, dual=False):
    bound = fixture_binding(root)
    adapter = SystemdService('a', prefix=prefix, extra_timers=(prefix + '-qualification@a.timer',) if dual else ())
    outcome = 'completed'
    try:
        with maintenance(root, bound, adapter):
            transport = SyntheticRead(bound)
            with PracticeBroker(bound, transport=transport) as broker:
                assert broker.account().boundary == '100' and transport.calls == 1
            record(root, 'maintenance', 'read', tag=tag, source='fixture', network_requests=0)
            release(root, tag + '-read')
            with open_notebook(root, bound) as db:
                with transaction(db):
                    db.execute("UPDATE issues SET code=? WHERE issue_id='fixture'", ('maintenance-' + tag,))
                record(root, 'maintenance', 'write', tag=tag)
                release(root, tag + '-write')
            record(root, 'maintenance', 'notebook_closed', tag=tag)
            release(root, tag + '-finish')
            if fail:
                raise IntendedFailure()
    except IntendedFailure:
        outcome = 'intentional_failure'
    except MaintenanceDeferred:
        outcome = 'deferred'
    record(root, 'maintenance', 'result', tag=tag, outcome=outcome)


def dashboard_writer(root):
    with open_notebook(root, fixture_binding(root)) as db:
        with transaction(db):
            db.execute("UPDATE issues SET code='host-before-commit' WHERE issue_id='fixture'")
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE issues SET code='host-after-commit' WHERE issue_id='fixture'")
        record(root, 'writer', 'uncommitted')
        release(root, 'writer-commit')
        db.commit()
        record(root, 'writer', 'committed')
        release(root, 'writer-close')
    record(root, 'writer', 'closed')


def main():
    root = Path(sys.argv[1])
    if not root.name.startswith('nnfx-m09-system-') or root.parent != Path('/var/lib/nnfx-practice/var/verification'):
        raise ValueError('Expected isolated system-fixture directory')
    mode = sys.argv[2]
    if mode == 'initialize':
        initialize(root)
    elif mode == 'controller':
        return controller(root, sys.argv[3])
    elif mode == 'maintenance':
        maintain(root, sys.argv[3], sys.argv[4], sys.argv[5] == 'fail', sys.argv[6:] == ['dual'])
    elif mode == 'writer':
        dashboard_writer(root)
    else:
        raise ValueError('Unknown system-fixture worker mode')
    return 0


if __name__ == '__main__':
    sys.exit(main())
