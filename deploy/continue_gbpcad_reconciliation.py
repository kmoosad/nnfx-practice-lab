"""Continue explicitly reviewed installation checkpoints before notebook writes.

The original frozen package, receipt, backup, reader release and failure history
are preserved. This is not a rerun of the initial migration.
"""

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import sys
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = 'gbpcad-reconcile-1c86fd008419'


def verify_checkpoint(receipt, states, installed_code, *, expected_phase='compatible_reader_deployed',
                      expected_code=None):
    from deploy import reconcile_gbpcad as action
    expected_code=action.OLD_CODE if expected_code is None else expected_code
    if (receipt.get('status') != 'inspection_required'
            or receipt.get('phase') != expected_phase
            or receipt.get('broker_mutations') != 0 or receipt.get('ordinary_activated') is not False
            or receipt.get('after') or receipt.get('result') or installed_code != expected_code):
        raise ValueError('This continuation requires the exact reviewed pre-notebook failure')
    before = receipt['before']
    if (before['schema'] != 2 or before['notebook']['imported_through_transaction_id'] != '2249'
            or before['notebook']['qualification_snapshot_id'] != action.Q0
            or before['notebook']['activated_at'] is not None
            or len(before['issues']) != 1 or before['issues'][0]['issue_id'] != action.ISSUE
            or before['issues'][0]['status'] != 'open'):
        raise ValueError('Original notebook checkpoint differs')
    service = states[action.SERVICE]
    if service['LoadState'] != 'masked' or service['ActiveState'] not in ('inactive', 'failed'):
        raise ValueError('Continuation requires the retained idle controller mask')
    if any(row['Job'] not in ('', '0') for row in states.values()):
        raise ValueError('A controller or timer job is pending')
    for unit in action.TIMERS:
        if (states[unit]['ActiveState'] != 'inactive'
                or states[unit]['UnitFileState'] != receipt['before_controls'][unit]['UnitFileState']):
            raise ValueError('Original excluded timer states differ')


def main(*, checkpoint_id=CHECKPOINT, installed_checkpoint=False):
    os.umask(0o077)
    if sys.argv[1:] or os.geteuid() != 0:
        raise SystemExit('Administrator access is required; no action attempted')
    sys.path.insert(0, str(ROOT))
    from deploy import dashboard_deploy as d
    from deploy import reconcile_gbpcad as action
    from nnfx_practice import qualification as q
    verification = json.loads((ROOT / 'operation-verification.json').read_bytes())
    hashes = q.code_hashes()
    if verification['source_hashes'] != hashes:
        raise ValueError('Frozen application differs from verified source')
    for name, digest in verification['operation_hashes'].items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen continuation or fixture changed')
    suite = ROOT / verification['suite']['path']
    match = re.search(r'Ran (\d+) tests in [\d.]+s\s+OK\s*$', suite.read_text())
    if (sha256(suite.read_bytes()).hexdigest() != verification['suite']['sha256']
            or not match or int(match[1]) < 555):
        raise ValueError('Verified passing suite changed')
    wheel = action.verified_wheel(ROOT, verification, hashes)
    previous = q.PLAN_DIRECTORY / 'evidence' / checkpoint_id
    raw_receipt = q.sealed_bytes(previous / 'receipt.json')
    if sha256(raw_receipt).hexdigest() != verification['checkpoint_receipt_sha256']:
        raise ValueError('The retained failure receipt changed; inspect rather than retry')
    checkpoint = json.loads(raw_receipt)
    if checkpoint.get('archive') != str(previous):
        raise ValueError('Failure archive does not match the specific reviewed checkpoint')
    original_verification = q.sealed_bytes(previous / 'operation-verification.json')
    if sha256(original_verification).hexdigest() != verification['original_verification_sha256']:
        raise ValueError('Original verification changed')
    if json.loads(original_verification)['source_hashes'] != hashes:
        raise ValueError('Continuation must use the same application package')
    forbidden=('worker','reconcile.py') if installed_checkpoint else ('worker','reconcile.py','controller-controls.json')
    if any((previous / name).exists() for name in forbidden):
        raise ValueError('A later step already began; preserve evidence and inspect it')
    backup=previous
    if installed_checkpoint:
        backup=Path(checkpoint['original_archive'])
        if str(backup)!=verification['backup_archive'] or backup.parent!=q.PLAN_DIRECTORY/'evidence':
            raise ValueError('Original notebook backup archive differs')
        backup_receipt=q.sealed_bytes(backup/'receipt.json')
        if sha256(backup_receipt).hexdigest()!=verification['backup_receipt_sha256']:
            raise ValueError('Original backup/failure receipt changed')
        if json.loads(backup_receipt)['before']!=checkpoint['before']:
            raise ValueError('Notebook checkpoint differs from original backup')
        failed_controls=q.sealed_bytes(previous/'controller-controls.json')
        if sha256(failed_controls).hexdigest()!=verification['failed_controls_sha256']:
            raise ValueError('Retained host-control failure report changed')
        failure=json.loads(failed_controls)
        if (failure.get('cleanup_errors')!=[] or failure.get('results',{}).get('actual_notebook_files_preserved') is not True
                or failure['results'].get('fixture_checks_passed') is not False
                or failure.get('deployed_source_hashes')!=hashes):
            raise ValueError('Host failure has unresolved cleanup, data changes or different installed code')
    original = q.sealed_bytes(backup / 'previous-plan.json')
    plan_path = q.PLAN_DIRECTORY / (action.CONTROLLER + '.json')
    if q.sealed_bytes(plan_path) != original:
        raise ValueError('Protected qualification plan changed')
    old = json.loads(original)
    if (old['code_sha256'] != action.OLD_CODE or old['account_binding_sha256'] != action.ACCOUNT
            or old['version'] != 2 or old['mode'] != 'qualification' or old['kernel'] != q.host_identity()[1]):
        raise ValueError('Original qualification binding differs')
    installed = json.loads(action.run(action.PYTHON, '-I', '-B', '-c',
        'import json; from nnfx_practice import qualification as q; '
        'print(json.dumps(dict(code=q.code_identity(),hashes=q.code_hashes())))'))
    states = {unit:action.state(unit) for unit in (action.SERVICE, *action.TIMERS)}
    verify_checkpoint(checkpoint, states, installed['code'],
                      expected_phase='checking_host_controls' if installed_checkpoint else 'compatible_reader_deployed',
                      expected_code=q.code_identity() if installed_checkpoint else action.OLD_CODE)
    d.quiet_window()
    identifier = 'gbpcad-continue-' + uuid4().hex[:12]
    archive = q.PLAN_DIRECTORY / 'evidence' / identifier
    archive.mkdir(mode=0o750)
    archive.chmod(0o750)
    os.chown(archive, 0, pwd.getpwnam('nnfx-run').pw_gid)
    output = ROOT / 'var/verification' / identifier
    output.mkdir(parents=True, mode=0o700)
    receipt = dict(status='continuation_preflight', at=datetime.now(UTC).isoformat(), archive=str(archive),
                   original_archive=str(previous), original_failure_receipt_sha256=sha256(raw_receipt).hexdigest(),
                   backup_archive=str(backup),
                   before=checkpoint['before'], before_controls=checkpoint['before_controls'],
                   checkpoint_controls=states, broker_mutations=0, ordinary_activated=False,
                   release=checkpoint['release'])
    try:
        with d.locked(), action.exclusion():
            config = json.loads(d.CONFIG.read_bytes())
            if config['trading_files'] != installed['hashes'] or d.active_release() != checkpoint['release']:
                raise ValueError('Interrupted package or reader checkpoint changed')
            candidate = deepcopy(config)
            candidate['trading_files'] = hashes
            # Validate all installed source and existing restrictions without
            # rewriting the reader or its already-completed configuration.
            d.verify_host(candidate)
            if d.hashes(d.file_map(d.RELEASES / checkpoint['release'])) != config['base_files']:
                raise ValueError('Compatible reader release changed')
            if action.copied_state(archive) != checkpoint['before']:
                raise ValueError('Actual notebook differs from the retained pre-write checkpoint')
            for suffix in ('', '-wal'):
                name = 'notebook-a.sqlite3' + suffix
                current = action.DATA / 'var/notebooks' / name
                if sha256(current.read_bytes()).digest() != sha256((backup / 'notebook-before' / name).read_bytes()).digest():
                    raise ValueError('Actual notebook database or WAL changed since the backup')
            original_claims = action.claims()
            action.save(archive / 'original-failure-receipt.json', checkpoint)
            (archive / 'operation-verification.json').write_bytes((ROOT / 'operation-verification.json').read_bytes())
            if installed_checkpoint:
                receipt['status']='repairing_public_package_permissions'
                action.save(archive/'receipt.json',receipt)
                purelib=Path(action.run(action.PYTHON,'-I','-B','-c',
                    'import sysconfig; print(sysconfig.get_path("purelib"))').strip())
                changes=action.repair_package_permissions(purelib,hashes)
                action.save(archive/'package-permissions.json',dict(changes=changes,private_files_touched=False))
                for identity in ('nnfx-run','nnfx-view'):
                    raw=action.run('/usr/sbin/runuser','-u',identity,'--',action.PYTHON,'-I','-B','-c',
                        'import json; from nnfx_practice import qualification as q; '
                        'from nnfx_practice.notebook import SCHEMA_VERSION; '
                        'print(json.dumps(dict(code=q.code_identity(),schema=SCHEMA_VERSION)))')
                    proof=json.loads(raw)
                    if proof!={'code':q.code_identity(),'schema':3}:
                        raise ValueError('Service identity cannot import the exact installed package')
                    action.save(archive/('service-import-'+identity+'.json'),proof)
            else:
                # Exercise pip's real filename/metadata validation before installing.
                action.run(action.PYTHON, '-I', '-B', '-m', 'pip', 'install', '--dry-run', '--no-index',
                           '--no-deps', '--no-cache-dir', '--disable-pip-version-check', '--force-reinstall', wheel,
                           evidence=archive / 'package-dry-run.json')
            d.health()
            plan, worker_dir, script = action.prepare_disposition(
                archive, receipt, wheel=wheel, hashes=hashes, config=config, old=old,
                before=checkpoint['before'], original_claims=original_claims,install_package=not installed_checkpoint)
        action.finish_disposition(archive, receipt, plan=plan, worker_dir=worker_dir, script=script,
                                  before=checkpoint['before'], original_claims=original_claims,
                                  original=original, plan_path=plan_path, config=config,
                                  before_controls=checkpoint['before_controls'])
    except BaseException as error:
        receipt.update(phase=receipt['status'], status='inspection_required', error_type=type(error).__name__)
        for unit in action.TIMERS:
            try:
                action.run('systemctl', 'stop', unit)
            except Exception:
                pass
        try:
            action.run('systemctl', 'mask', '--runtime', action.SERVICE)
        except Exception:
            pass
        receipt['recovery'] = 'Preserve both archives. Inspect the explicit phase and retained step output; do not rerun.'
    finally:
        action.save(archive / 'receipt.json', receipt)
        action.save(output / 'result.json', receipt)
        owner = ROOT.stat()
        action.export_diagnostics(archive,output,owner)
        os.chown(output / 'result.json', owner.st_uid, owner.st_gid)
        os.chown(output, owner.st_uid, owner.st_gid)
        print(json.dumps(dict(status=receipt['status'], output=str(output / 'result.json'))), flush=True)
    return 0 if receipt['status'] == 'reconciled_and_resolved' else 2


if __name__ == '__main__':
    raise SystemExit(main())
