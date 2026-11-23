"""Incident-only schema-3 deployment and evidenced GBP-CAD operator disposition.

Run the frozen, verified copy as administrator. No trading run or broker mutation
is permitted. A failure after exclusion leaves both timers stopped and the
controller masked; inspect the retained receipt rather than rerunning blindly.
"""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CODE = Path('/opt/nnfx-practice')
DATA = Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
CONTROLLER = 'practice-a'
SERVICE = 'nnfx-practice@practice-a.service'
TIMERS = ('nnfx-practice@practice-a.timer', 'nnfx-practice-qualification@practice-a.timer')
SET = '87c2f95fc7cc45ab99875a831dfeb941'
ISSUE = 'incomplete_entry:' + SET + ':457cc1e38b664e15a29317333be59cec'
ACCOUNT = 'e7672a6e291ad80d603c429326e1d881faf10ad4c8dcf9083f81a67ee9343b87'
Q0 = 'c245f517b15448cabb2edbb5336a53aa'
OLD_CODE = 'e8eba7f18830772efe89bc24c4b55f7be7b7134b9c29d9979e7ab3409b5c3713'
WHEEL_NAME = 'nnfx_practice-0.1.0-py3-none-any.whl'
IMMUTABLE = ('runs', 'run_invocations', 'stages', 'pair_decisions', 'broker_attempts')
EXPLANATION = (
    'Owner requested reconciliation and resolution on 23 November 2026 after '
    'closing failed GBP-CAD trade 2251. OANDA fill 2257 closed all 42665 units; '
    '2258 cancelled stop 2252. Leg 2 was never sent. Preserve the incomplete '
    'entry and failed run. Import funding 2259 separately from trading results.'
)


def save(path, document):
    raw = (json.dumps(document, indent=2, default=str, allow_nan=False) + '\n').encode()
    temporary = path.with_name(path.name + '.next')
    with temporary.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run(*args, timeout=30, cwd='/', env=None, evidence=None, child_umask=-1):
    reply = subprocess.run([str(value) for value in args], cwd=cwd,
                           env=env or {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
                                       'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'},
                           capture_output=True, text=True, timeout=timeout, umask=child_umask)
    if evidence is not None:
        # Used only for package installation and broker-free fixture commands.
        save(evidence, dict(returncode=reply.returncode, stdout=reply.stdout, stderr=reply.stderr))
    if reply.returncode:
        raise RuntimeError('Administrative step failed; inspect the retained receipt')
    return reply.stdout


def state(unit):
    raw = run('systemctl', 'show', unit,
              '--property=LoadState,ActiveState,SubState,UnitFileState,Job,NextElapseUSecRealtime')
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def idle(states):
    service = states[SERVICE]
    if service['LoadState'] != 'loaded' or service['ActiveState'] not in ('inactive', 'failed'):
        raise ValueError('Controller must be idle and initially unmasked')
    if any(row['Job'] not in ('', '0') for row in states.values()):
        raise ValueError('Controller or timer has a pending job')
    if (states[TIMERS[0]]['ActiveState'] != 'inactive'
            or states[TIMERS[0]]['UnitFileState'] != 'disabled'
            or states[TIMERS[1]]['ActiveState'] not in ('active', 'inactive')):
        raise ValueError('Existing ordinary/qualification schedule differs')


def claims():
    directory = DATA / 'var/qualification' / CONTROLLER
    result = {}
    for path in sorted(directory.iterdir()):
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Unexpected retained qualification artifact')
        result[path.name] = dict(sha256=sha256(path.read_bytes()).hexdigest(),
                                 uid=info.st_uid, gid=info.st_gid, mode=stat.S_IMODE(info.st_mode))
    return result


@contextmanager
def exclusion():
    descriptor = os.open(DATA / 'var/notebooks/notebook-a.lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def inspect_db(db):
    """No private account identifier is exported, even from the backup copy."""
    from nnfx_practice.evidence import canonical_json
    row = dict(db.execute('SELECT * FROM notebook').fetchone())
    account = row.pop('account_id')
    digest = sha256(canonical_json([row['controller_id'], row['notebook_id'],
                                    account, row['home_currency']]).encode()).hexdigest()
    if digest != ACCOUNT or row['qualification_snapshot_id'] != Q0 or row['activated_at'] is not None:
        raise ValueError('Expected initialized, unactivated incident notebook binding')
    tables = {table: [dict(r) for r in db.execute('SELECT * FROM ' + table)] for table in IMMUTABLE}
    q0 = dict(db.execute('SELECT * FROM account_snapshots WHERE snapshot_id=?', (Q0,)).fetchone())
    return dict(schema=db.execute('PRAGMA user_version').fetchone()[0], notebook=row,
                immutable_hashes={table:sha256(canonical_json(rows).encode()).hexdigest()
                                  for table,rows in tables.items()},
                q0_sha256=sha256(canonical_json(q0).encode()).hexdigest(),
                issues=[dict(r) for r in db.execute('SELECT * FROM issues')])


def copied_state(directory):
    """Copy DB/WAL before opening SQLite; never change the source SHM as root."""
    from nnfx_practice.config import read_registry
    from nnfx_practice.notebook import open_readonly
    experiment = read_registry(DATA)[CONTROLLER]
    with tempfile.TemporaryDirectory(dir=directory) as temporary:
        root = Path(temporary)
        target = experiment.notebook_path(root)
        target.parent.mkdir(parents=True)
        for suffix in ('', '-wal'):
            shutil.copyfile(Path(str(experiment.notebook_path(DATA)) + suffix), Path(str(target) + suffix))
        with open_readonly(root, experiment) as db:
            return inspect_db(db)


def verify_preserved(before, after):
    old, new = dict(before['notebook']), dict(after['notebook'])
    old.pop('imported_through_transaction_id')
    new.pop('imported_through_transaction_id')
    if (old != new or before['immutable_hashes'] != after['immutable_hashes']
            or before['q0_sha256'] != after['q0_sha256'] or after['schema'] != 3):
        raise ValueError('Notebook identity, Q0 or original failure/attempt history changed')
    prior = {row['issue_id']:row for row in before['issues']}
    current = {row['issue_id']:row for row in after['issues']}
    if prior.keys() != current.keys() or current[ISSUE]['status'] != 'resolved':
        raise ValueError('The expected issue was not resolved, or additional issues appeared')
    for key in prior.keys() - {ISSUE}:
        if prior[key] != current[key]:
            raise ValueError('An unrelated issue changed')
    for key in ('pair', 'code', 'set_id', 'leg_no', 'attempt_id', 'first_observed_at', 'broker_evidence_json'):
        if prior[ISSUE][key] != current[ISSUE][key]:
            raise ValueError('Original incident evidence changed')


def verify_closed(db):
    from nnfx_practice.broker import money
    from nnfx_practice.ledger import account_report
    from nnfx_practice.notebook import pair_is_available
    legs = db.execute('SELECT * FROM trade_legs WHERE set_id=? ORDER BY leg_no', (SET,)).fetchall()
    if (len(legs) != 2 or legs[0]['broker_trade_id'] != '2251' or legs[0]['broker_state'] != 'closed'
            or legs[0]['exit_transaction_id'] != '2257' or money(legs[0]['exit_price']) != money('1.87819')
            or money(legs[0]['current_units']) != 0 or legs[1]['broker_trade_id'] is not None
            or legs[1]['broker_state'] != 'not_opened'):
        raise ValueError('Both original legs must have evidenced terminal states')
    trade_set = db.execute('SELECT * FROM trade_sets WHERE set_id=?', (SET,)).fetchone()
    if (trade_set['establishment_status'] != 'incomplete' or not trade_set['terminal_at']
            or not pair_is_available(db, 'GBP-CAD')):
        raise ValueError('Incomplete set history or released entry block is inconsistent')
    funding = db.execute('SELECT body_json FROM broker_transactions WHERE transaction_id=?', ('2259',)).fetchone()
    body = json.loads(funding[0]) if funding else {}
    if body.get('type') != 'TRANSFER_FUNDS' or money(body.get('amount')) != money('50.03'):
        raise ValueError('Owner-reported funding is not confirmed by broker history')
    posting = db.execute("SELECT * FROM ledger_entries WHERE transaction_id='2259' AND posted=1").fetchall()
    if len(posting) != 1 or posting[0]['category'] != 'cash_adjustment' or money(posting[0]['amount']) != money('50.03'):
        raise ValueError('Funding must be recorded separately from trade P/L')
    report = account_report(db, 'qualification')
    return dict(legs=[{key:leg[key] for key in ('leg_no','broker_trade_id','broker_state','exit_price',
                                               'exit_transaction_id','exit_reason')} for leg in legs],
                pair_available=True, report=asdict(report))


def worker(directory):
    """Use installed code and the service's private settings and normal disposition."""
    from nnfx_practice.broker import BrokerError, PracticeBroker
    from nnfx_practice.config import load_binding
    from nnfx_practice.control import maintenance
    from nnfx_practice.disposition import record_disposition
    from nnfx_practice.host import controller_service
    from nnfx_practice.notebook import open_notebook
    from nnfx_practice.qualification import account_identity
    if os.getuid() != pwd.getpwnam('nnfx-run').pw_uid:
        raise ValueError('Only the trading identity may load private settings')
    binding = load_binding(DATA, CONTROLLER)
    if account_identity(binding) != ACCOUNT:
        raise ValueError('Private account binding differs from this incident')

    class Reads(PracticeBroker):
        def _get(self, *args, **kwargs):
            try:
                read = super()._get(*args, **kwargs)
            except BrokerError as error:
                save(directory / ('failure-' + uuid4().hex + '.json'), dict(status=error.status, evidence=error.evidence))
                raise
            save(directory / ('read-' + uuid4().hex + '.json'), read.evidence())
            return read

    with Reads(binding) as broker:
        # Default native transport has no mutation guard, so all non-GETs fail.
        proof = record_disposition(DATA, CONTROLLER, broker, service=controller_service(CONTROLLER),
                                   issue_id=ISSUE, operator_id='owner-via-codex', explanation=EXPLANATION)
        with maintenance(DATA, binding, controller_service(CONTROLLER)):
            with open_notebook(DATA, binding) as db:
                result = verify_closed(db)
        save(directory / 'result.json', dict(outcome='reconciled_and_resolved', proof=proof,
                                             broker_mutations=0, ordinary_activated=False, **result))


def install_files(source, target, files):
    for name in files:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        temporary = path.with_name(path.name + '.next')
        with temporary.open('xb') as handle:
            handle.write((source / name).read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, path)


def replacement_plan(old, code_hash, controls_ref):
    from copy import deepcopy
    plan = deepcopy(old)
    plan['code_sha256'] = code_hash
    plan['evidence']['m09_controller_controls'] = controls_ref
    # In particular retain run_id, schedule, authority, Q0, manifest and enabled.
    return plan


def verified_wheel(root, verification, hashes):
    wheel = root / verification['wheel']['path']
    if wheel.name != WHEEL_NAME:
        raise ValueError('Preserve the valid distribution wheel filename before deployment')
    if sha256(wheel.read_bytes()).hexdigest() != verification['wheel']['sha256']:
        raise ValueError('Frozen wheel changed')
    with zipfile.ZipFile(wheel) as package:
        if any(sha256(package.read(name)).hexdigest() != digest for name,digest in hashes.items()):
            raise ValueError('Frozen wheel differs from verified application source')
    return wheel


def repair_package_permissions(purelib, hashes, *, expected_uid=0):
    """Repair only the verified wheel's public code; never touch private data/dependencies."""
    for name,digest in hashes.items():
        path=purelib/name
        if path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Installed package bytes differ before permission repair')
    paths=[]
    for name in ('nnfx_practice','strategies','nnfx_practice-0.1.0.dist-info'):
        directory=purelib/name
        for path in (directory,*sorted(directory.rglob('*'))):
            info=path.lstat()
            if (info.st_uid!=expected_uid or path.is_symlink()
                    or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
                    or (stat.S_ISREG(info.st_mode) and info.st_nlink!=1)
                    or stat.S_IMODE(info.st_mode) not in ((0o700,0o755) if path.is_dir() else (0o600,0o644))):
                raise ValueError('Unexpected wheel file ownership/type/mode; no permissions repaired')
            paths.append((path,info,0o755 if path.is_dir() else 0o644))
    changes=[]
    for path,info,mode in paths:
        if stat.S_IMODE(info.st_mode)!=mode:
            path.chmod(mode)
            changes.append(dict(path=str(path.relative_to(purelib)),before=stat.S_IMODE(info.st_mode),after=mode))
    return changes


def prepare_disposition(archive, receipt, *, wheel, hashes, config, old, before, original_claims,
                        install_package=True):
    """Caller holds dashboard and notebook exclusion; actual data is still untouched."""
    from deploy import dashboard_deploy as d
    from nnfx_practice import qualification as q
    receipt['status'] = 'installing_verified_package' if install_package else 'verifying_installed_package'
    save(archive / 'receipt.json', receipt)
    if install_package:
        run(PYTHON, '-m', 'pip', 'install', '--no-index', '--no-deps', '--force-reinstall', wheel,
            timeout=120, evidence=archive / 'package-install.json', child_umask=0o022)
    installed_new = json.loads(run(PYTHON, '-I', '-B', '-c',
        'import json; from nnfx_practice import qualification as q; print(json.dumps(q.code_hashes()))'))
    if installed_new != hashes:
        raise ValueError('Installed wheel differs from verified source')
    config['trading_files'] = hashes
    d.atomic_file(d.CONFIG, (json.dumps(config, indent=2) + '\n').encode(), 0o644)
    d.verify_host(config)
    # Stopped timers, the held notebook lock and the stale old plan/code identity
    # exclude actual dispatch while separately named broker-free fixtures run.
    receipt['status'] = 'checking_host_controls'
    save(archive / 'receipt.json', receipt)
    run('systemctl', 'unmask', '--runtime', SERVICE)
    report = archive / 'controller-controls.json'
    run(PYTHON, '-I', '-B', ROOT / 'tests/check_m09_system.py',
        '--preserve-existing-notebooks', '--output', report, timeout=300,
        evidence=archive / 'host-fixture-command.json')
    controls = json.loads(report.read_bytes())
    if (controls.get('cleanup_errors') != [] or not controls.get('results',{}).get('fixture_checks_passed')
            or not controls['results'].get('actual_notebook_files_preserved')):
        raise ValueError('Affected host controls did not pass')
    run('systemctl', 'mask', '--runtime', SERVICE)
    if state(SERVICE)['ActiveState'] not in ('inactive', 'failed'):
        raise ValueError('Actual controller must remain idle throughout fixtures')
    report.chmod(0o640)
    os.chown(report, 0, pwd.getpwnam('nnfx-run').pw_gid)
    reference = dict(path=str(report), sha256=sha256(report.read_bytes()).hexdigest(), status='passed')
    plan = replacement_plan(old, q.code_identity(), reference)
    q.validate_evidence(plan, q._evidence(plan))
    q.automatic_authority(plan)
    if copied_state(archive) != before or claims() != original_claims:
        raise ValueError('History changed before the explicit maintenance write')
    worker_dir = archive / 'worker'
    worker_dir.mkdir(mode=0o700)
    os.chown(worker_dir, pwd.getpwnam('nnfx-run').pw_uid, pwd.getpwnam('nnfx-run').pw_gid)
    script = archive / 'reconcile.py'
    script.write_bytes(Path(__file__).read_bytes())
    script.chmod(0o640)
    os.chown(script, 0, pwd.getpwnam('nnfx-run').pw_gid)
    receipt['status'] = 'ready_for_evidenced_disposition'
    save(archive / 'receipt.json', receipt)
    return plan, worker_dir, script


def export_diagnostics(archive, output, owner):
    # These commands/checks never load private settings or make broker requests.
    # Export only their known JSON reports, never arbitrary files or worker reads.
    errors=[]
    for name in ('package-install.json','package-dry-run.json','package-permissions.json',
                 'service-import-nnfx-run.json','service-import-nnfx-view.json',
                 'host-fixture-command.json','controller-controls.json'):
        source=archive/name
        if source.is_file() and not source.is_symlink():
            try:
                document=json.loads(source.read_bytes())
            except (OSError,ValueError) as error:
                errors.append(dict(file=name,error_type=type(error).__name__))
                continue
            target=output/name
            save(target,document)
            os.chown(target,owner.st_uid,owner.st_gid)
    if errors:
        target=output/'diagnostic-export-errors.json'
        save(target,errors)
        os.chown(target,owner.st_uid,owner.st_gid)


def finish_disposition(archive, receipt, *, plan, worker_dir, script, before, original_claims,
                       original, plan_path, config, before_controls):
    """Call outside parent exclusion: normal disposition acquires the same lock."""
    from deploy import dashboard_deploy as d
    from nnfx_practice import qualification as q
    from tests.arm_m10_qualification import replace_plan
    run('/usr/sbin/runuser', '-u', 'nnfx-run', '--', PYTHON, '-I', '-B', script, '--worker', worker_dir,
        env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL':'C',
             'NNFX_NOTEBOOK_READ_GROUP':'nnfx-read', 'PYTHONDONTWRITEBYTECODE':'1'}, timeout=120)
    with d.locked(), exclusion():
        result = json.loads((worker_dir / 'result.json').read_bytes())
        after = copied_state(archive)
        verify_preserved(before, after)
        if claims() != original_claims:
            raise ValueError('Existing qualification claims or capture artifacts changed')
        raw = (json.dumps(plan, indent=2) + '\n').encode()
        replace_plan(plan_path, sha256(original).hexdigest(), raw)
        d.health()
        d.verify_host(config)
        receipt.update(status='reconciled_and_resolved', after=after, result=result,
                       plan_sha256=sha256(raw).hexdigest(), claims_preserved=True)
        d.quiet_window()
        run('systemctl', 'unmask', '--runtime', SERVICE)
        for unit in TIMERS:
            run('systemctl', 'start' if before_controls[unit]['ActiveState'] == 'active' else 'stop', unit)
        receipt['after_controls'] = {unit:state(unit) for unit in (SERVICE, *TIMERS)}
        idle(receipt['after_controls'])
        for unit in TIMERS:
            if any(receipt['after_controls'][unit][key] != before_controls[unit][key]
                   for key in ('ActiveState', 'UnitFileState')):
                raise ValueError('Prior schedule was not restored')
        q.host_controls(CONTROLLER, 'inspect')
        if before_controls[TIMERS[1]]['ActiveState'] == 'active':
            q.schedule_controls(CONTROLLER)


def main():
    os.umask(0o077)
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        try:
            worker(Path(sys.argv[2]))
        except Exception as error:
            print(json.dumps(dict(outcome='inspection_required', error_type=type(error).__name__)))
            return 2
        return 0
    if sys.argv[1:] or os.geteuid() != 0:
        raise SystemExit('Run the frozen command without arguments as administrator; no action attempted')
    sys.path.insert(0, str(ROOT))
    from deploy import dashboard_deploy as d
    from nnfx_practice import qualification as q
    from nnfx_practice.config import read_registry
    verification = json.loads((ROOT / 'operation-verification.json').read_bytes())
    hashes = q.code_hashes()
    if verification['source_hashes'] != hashes:
        raise ValueError('Frozen application differs from the verified correction')
    for name, expected in verification['operation_hashes'].items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen operation/fixture differs from its offline verification')
    suite = ROOT / verification['suite']['path']
    match = re.search(r'Ran (\d+) tests in [\d.]+s\s+OK\s*$', suite.read_text())
    if (sha256(suite.read_bytes()).hexdigest() != verification['suite']['sha256']
            or not match or int(match[1]) < 555):
        raise ValueError('Passing full offline suite is missing or changed')
    wheel = verified_wheel(ROOT, verification, hashes)
    d.quiet_window()
    if set(read_registry(DATA)) != {CONTROLLER}:
        raise ValueError('This operation is scoped to the single incident notebook')
    plan_path = q.PLAN_DIRECTORY / (CONTROLLER + '.json')
    original = q.sealed_bytes(plan_path)
    old = q._document(original)
    if (old['version'] != 2 or old['mode'] != 'qualification' or old['code_sha256'] != OLD_CODE
            or old['account_binding_sha256'] != ACCOUNT or old['kernel'] != q.host_identity()[1]):
        raise ValueError('Protected qualification plan differs; do not rearm or replace it')
    installed = json.loads(run(PYTHON, '-I', '-B', '-c',
        'import json; from nnfx_practice import qualification as q; '
        'print(json.dumps(dict(code=q.code_identity(),hashes=q.code_hashes())))'))
    if installed['code'] != OLD_CODE:
        raise ValueError('Installed package differs or this deployment already ran')
    run(PYTHON, '-I', '-B', '-c',
        'from nnfx_practice import qualification as q; '
        "p=q._document(q.sealed_bytes(q.PLAN_DIRECTORY/'practice-a.json')); "
        'q.validate_evidence(p,q._evidence(p)); q.automatic_authority(p)')
    before_controls = {unit:state(unit) for unit in (SERVICE, *TIMERS)}
    idle(before_controls)
    identifier = 'gbpcad-reconcile-' + uuid4().hex[:12]
    archive = q.PLAN_DIRECTORY / 'evidence' / identifier
    archive.mkdir(mode=0o750)
    archive.chmod(0o750)
    os.chown(archive, 0, pwd.getpwnam('nnfx-run').pw_gid)
    output = ROOT / 'var/verification' / identifier
    output.mkdir(parents=True, mode=0o700)
    receipt = dict(status='prepared', at=datetime.now(UTC).isoformat(), archive=str(archive),
                   broker_mutations=0, ordinary_activated=False, before_controls=before_controls)
    changed = False
    try:
        with d.locked(), exclusion():
            config = json.loads(d.CONFIG.read_bytes())
            d.verify_host(config)
            if config['trading_files'] != installed['hashes']:
                raise ValueError('Installed source and package differ')
            original_claims = claims()
            before = copied_state(archive)
            if (before['schema'] != 2 or before['notebook']['imported_through_transaction_id'] != '2249'
                    or len(before['issues']) != 1 or before['issues'][0]['issue_id'] != ISSUE
                    or before['issues'][0]['status'] != 'open'):
                raise ValueError('Notebook no longer matches the investigated incident')
            receipt['before'] = before
            backup = archive / 'notebook-before'
            backup.mkdir(mode=0o700)
            for suffix in ('', '-wal', '-shm'):
                source = DATA / ('var/notebooks/notebook-a.sqlite3' + suffix)
                shutil.copyfile(source, backup / source.name)
            for folder in ('nnfx_practice', 'strategies'):
                shutil.copytree(CODE / folder, archive / ('previous-' + folder),
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            (archive / 'previous-plan.json').write_bytes(original)
            (archive / 'operation-verification.json').write_bytes((ROOT / 'operation-verification.json').read_bytes())
            (archive / 'previous-dashboard-config.json').write_bytes(d.CONFIG.read_bytes())
            receipt['previous_release'] = d.active_release()
            save(archive / 'receipt.json', receipt)
            # No live file changes precede complete preflight and backup.
            changed = True
            for unit in TIMERS:
                run('systemctl', 'stop', unit)
            run('systemctl', 'mask', '--runtime', SERVICE)
            if state(SERVICE)['ActiveState'] not in ('inactive', 'failed') or state(SERVICE)['Job'] not in ('','0'):
                raise ValueError('Controller became active; never interrupt it')
            files = d.file_map(d.RELEASES / receipt['previous_release'])
            if d.hashes(files) != config['base_files']:
                # Allowlisted visual edits can postdate the original base map.
                if files.keys() != config['base_files'].keys() or any(
                        d.digest(body) != config['base_files'][name] for name,body in files.items() if name not in d.ALLOWED):
                    raise ValueError('Dashboard base files changed outside the approved surface')
            files['nnfx_practice/notebook.py'] = (ROOT / 'nnfx_practice/notebook.py').read_bytes()
            name = 'dashboard-schema3-' + sha256(json.dumps(d.hashes(files), sort_keys=True).encode()).hexdigest()[:16]
            destination = d.RELEASES / name
            destination.mkdir(mode=0o755)
            destination.chmod(0o755)
            for relative, body in files.items():
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                target.write_bytes(body)
                target.chmod(0o644)
            for directory in destination.rglob('*'):
                if directory.is_dir():
                    directory.chmod(0o755)
            config['base_files'] = d.hashes(files)
            d.atomic_file(d.CONFIG, (json.dumps(config, indent=2) + '\n').encode(), 0o644)
            d.select_release(name)
            d.command('restart', d.UNIT)
            d.health()  # Prove compatible reader works while notebook is still schema 2.
            receipt.update(status='compatible_reader_deployed', release=name)
            save(archive / 'receipt.json', receipt)
            install_files(ROOT, CODE, hashes)
            plan, worker_dir, script = prepare_disposition(
                archive, receipt, wheel=wheel, hashes=hashes, config=config, old=old,
                before=before, original_claims=original_claims)
        # The parent-owned mask remains while normal disposition owns exclusion.
        finish_disposition(archive, receipt, plan=plan, worker_dir=worker_dir, script=script,
                           before=before, original_claims=original_claims, original=original,
                           plan_path=plan_path, config=config, before_controls=before_controls)
    except BaseException as error:
        receipt.update(phase=receipt['status'], status='inspection_required', error_type=type(error).__name__)
        if changed:
            # Preserve schema-3 data/code and all evidence, with no automatic rollback.
            for unit in TIMERS:
                try:
                    run('systemctl', 'stop', unit)
                except Exception:
                    pass
            try:
                run('systemctl', 'mask', '--runtime', SERVICE)
            except Exception:
                pass
            receipt['recovery'] = 'Inspect archive; both timers should be stopped and controller masked. Do not rerun.'
    finally:
        save(archive / 'receipt.json', receipt)
        save(output / 'result.json', receipt)
        owner = ROOT.stat()
        export_diagnostics(archive,output,owner)
        os.chown(output / 'result.json', owner.st_uid, owner.st_gid)
        os.chown(output, owner.st_uid, owner.st_gid)
        print(json.dumps(dict(status=receipt['status'], output=str(output / 'result.json'))), flush=True)
    return 0 if receipt['status'] == 'reconciled_and_resolved' else 2


if __name__ == '__main__':
    raise SystemExit(main())
