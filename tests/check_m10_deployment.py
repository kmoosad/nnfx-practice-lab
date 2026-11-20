"""Administrator broker-free check of the installed, unarmed real controller.

Temporarily deny its network and private/notebook paths, prove missing-plan
rejection twice, then remove only this probe's drop-in. Never provisions a plan.
"""

import json
import os
from pathlib import Path
import pwd
import subprocess
import time
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
DROPIN = '[Service]\nIPAddressDeny=any\nInaccessiblePaths=-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks\n'


def command(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if check and result.returncode:
        raise RuntimeError('Host command failed: ' + args[0])
    return result


def properties(unit):
    text = command('systemctl', 'show', unit,
                   '--property=LoadState,ActiveState,UnitFileState,Job,MainPID,InvocationID,ExecMainStatus,NRestarts,IPAddressDeny,InaccessiblePaths').stdout
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def require_inactive(service, timer):
    state, clock = properties(service), properties(timer)
    if (state.get('LoadState') != 'loaded' or state.get('ActiveState') != 'inactive'
            or state.get('Job') not in ('', '0') or clock.get('LoadState') != 'loaded'
            or clock.get('ActiveState') != 'inactive' or clock.get('UnitFileState') != 'disabled'
            or clock.get('Job') not in ('', '0')):
        raise RuntimeError('Defer probe: controller/timer must be inactive, timer disabled, no pending jobs')


def check_sources():
    import sysconfig
    from nnfx_practice.qualification import code_hashes
    expected = code_hashes()
    package = Path(sysconfig.get_path('purelib'))
    for name, digest in expected.items():
        for base in (CODE, package):
            if sha256((base / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Installed application differs; deploy and rerun affected checks')
    for name in ('nnfx-practice@.service', 'nnfx-practice@.timer', 'nnfx-practice-dashboard.service'):
        if (ROOT / 'deploy' / name).read_bytes() != Path('/etc/systemd/system', name).read_bytes():
            raise RuntimeError('Installed unit differs from checkout')
    return expected


def main():
    if os.geteuid() != 0:
        raise SystemExit('Administrator access is required; no host changes were made')
    # Import explicitly from the reviewed checkout, not a shell working directory.
    import sys
    if sys.prefix != str(CODE / '.venv'):
        raise SystemExit('Run this probe using /opt/nnfx-practice/.venv/bin/python')
    sys.path.insert(0, str(ROOT))
    from nnfx_practice.config import read_registry
    registry = read_registry(ROOT)
    if (DATA / 'config.toml').read_bytes() != (ROOT / 'config.toml').read_bytes():
        raise SystemExit('Deployed registry differs; stop for binding review')
    identities = check_sources()
    report = dict(at=datetime.now(UTC).isoformat(), classification='host broker-free unarmed M10 service verification',
                  source_hashes=identities, results={}, cleanup_errors=[], broker_requests=0,
                  probe_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  actual_notebooks_initialized=False, ordinary_trading_enabled=False,
                  execution_qualified=False, host_qualification_complete=False)
    output = ROOT / 'var/verification/m10-integration' / ('deployment-' + uuid4().hex[:12] + '.json')
    output.parent.mkdir(exist_ok=True)
    # Preflight every controller before any temporary service mutation.
    for controller, experiment in registry.items():
        plan = Path('/etc/nnfx-practice/qualification') / (controller + '.json')
        if plan.exists() or plan.is_symlink():
            raise SystemExit('Probe requires absent qualification plans; never overwrite or bypass a plan')
        require_inactive(f'nnfx-practice@{controller}.service', f'nnfx-practice@{controller}.timer')
        notebook = DATA / 'var/notebooks' / (experiment.notebook_id + '.sqlite3')
        if notebook.exists() or notebook.is_symlink():
            raise SystemExit('This uninitialized-deployment probe does not operate on an actual notebook')
    try:
        for controller, experiment in registry.items():
            service, timer = f'nnfx-practice@{controller}.service', f'nnfx-practice@{controller}.timer'
            directory = Path('/run/systemd/system') / (service + '.d')
            dropin = directory / '90-m10-broker-free-verification.conf'
            if directory.exists() or directory.is_symlink():
                raise RuntimeError('Existing runtime drop-ins require review before probe')
            directory.mkdir(mode=0o755)
            try:
                with dropin.open('x') as target:
                    target.write(DROPIN)
                dropin.chmod(0o644)
                command('systemctl', 'daemon-reload')
                seen = []
                for _ in range(2):
                    require_inactive(service, timer)
                    state = properties(service)
                    if ('0.0.0.0/0' not in state.get('IPAddressDeny', '')
                            or '.env' not in state.get('InaccessiblePaths', '')
                            or '/var/notebooks' not in state.get('InaccessiblePaths', '')):
                        raise RuntimeError('Broker-free probe barriers are not loaded')
                    command('systemctl', 'start', '--no-block', service)
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        state = properties(service)
                        if state.get('ActiveState') == 'failed':
                            break
                        time.sleep(0.1)
                    if (state.get('ActiveState') != 'failed' or state.get('ExecMainStatus') != '2'
                            or state.get('NRestarts') != '0' or not state.get('InvocationID')):
                        raise RuntimeError('Expected missing-plan rejection before broker/private/notebook access')
                    journal = command('journalctl', '_SYSTEMD_INVOCATION_ID=' + state['InvocationID'],
                                      '--no-pager', '-o', 'cat').stdout
                    expected = 'M10 qualification blocked: required protected plan/evidence file is unavailable'
                    if expected not in journal:
                        raise RuntimeError('Expected protected-plan rejection was not observed')
                    seen.append(dict(invocation_id=state['InvocationID'], exit_status=2, automatic_restarts=0,
                                     expected_rejection_observed=True))
                    command('systemctl', 'reset-failed', service)
                if seen[0]['invocation_id'] == seen[1]['invocation_id']:
                    raise RuntimeError('Two independent service invocations were not observed')
                report['results'][controller] = dict(unarmed_same_service_checks_passed=True, attempts=seen)
            finally:
                try:
                    command('systemctl', 'stop', service)
                    if dropin.exists():
                        if dropin.read_text() != DROPIN:
                            raise RuntimeError('Probe drop-in changed; do not remove it automatically')
                        dropin.unlink()
                    if directory.exists():
                        directory.rmdir()
                    command('systemctl', 'daemon-reload')
                    command('systemctl', 'reset-failed', service, check=False)
                except Exception as error:
                    report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
                    raise
            require_inactive(service, timer)
            if (DATA / 'var/notebooks' / (experiment.notebook_id + '.sqlite3')).exists():
                raise RuntimeError('Unexpected actual notebook file; stop for investigation')
        report['deployment_gate_checks_passed'] = True
    except Exception as error:
        report['deployment_gate_checks_passed'] = False
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        with output.open('x') as target:
            json.dump(report, target, indent=2)
            target.write('\n')
        os.chown(output, (ROOT / 'config.toml').stat().st_uid, (ROOT / 'config.toml').stat().st_gid)
        output.chmod(0o600)
    print(json.dumps(dict(report=str(output), deployment_gate_checks_passed=report['deployment_gate_checks_passed'],
                          execution_qualified=False, ordinary_trading_enabled=False)))
    if not report['deployment_gate_checks_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
