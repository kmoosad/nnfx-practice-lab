"""Collect existing qualification evidence without arming, broker reads or notebook writes.

Independent of the optional final-host observer. Open trades, rejected attempts,
issues and unfinished sessions are retained and reported, never repaired.
"""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/var/lib/nnfx-practice')


@contextmanager
def copied_notebook(output, experiment):
    """Read a private DB/WAL copy while the caller holds controller exclusion.

    Even a mode=ro SQLite connection can update a writable source SHM file.
    Never open the real notebook with SQLite from this administrator collector.
    Let SQLite build its own WAL index beside the temporary copy instead.
    """
    from nnfx_practice.notebook import open_readonly
    with tempfile.TemporaryDirectory(prefix='.notebook-', dir=output) as temporary:
        root = Path(temporary)
        source = experiment.notebook_path(DATA)
        target = experiment.notebook_path(root)
        target.parent.mkdir(parents=True)
        for suffix in ('', '-wal'):
            copied = Path(str(target) + suffix)
            shutil.copyfile(Path(str(source) + suffix), copied)
            copied.chmod(0o600)
        with open_readonly(root, experiment) as db:
            yield db


def collect(output, controller='practice-a'):
    from nnfx_practice import qualification as q
    from nnfx_practice.config import read_registry
    from nnfx_practice.evidence import redact
    from nnfx_practice.qualification_review import TABLES, facts, report_values
    original = q.sealed_bytes(q.PLAN_DIRECTORY/(controller+'.json'))
    plan = q._document(original)
    experiment = read_registry(DATA)[controller]
    path = experiment.notebook_path(DATA)
    files = (path, Path(str(path)+'-wal'), Path(str(path)+'-shm'))
    descriptor = os.open(path.with_suffix('.lock'), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = {str(p):sha256(p.read_bytes()).hexdigest() for p in files}
        output.mkdir(parents=True,exist_ok=False)
        output.chmod(0o700)
        def save(name, raw):
            target=output/name
            with target.open('xb') as f:
                f.write(raw)
            target.chmod(0o600)
            return dict(path=str(target),sha256=sha256(raw).hexdigest())
        with copied_notebook(output,experiment) as db:
            db.execute('BEGIN')
            notebook=dict(db.execute('SELECT * FROM notebook').fetchone())
            # This standalone collector also runs with the installed schema-2
            # package while the controller update is still awaiting deployment.
            names=[name for name in TABLES if name != 'broker_transaction_observations']
            if db.execute("SELECT 1 FROM sqlite_schema WHERE name='broker_transaction_observations'").fetchone():
                names.append('broker_transaction_observations')
            tables={t:[dict(r) for r in db.execute('SELECT * FROM '+t)] for t in names}
            result=dict(classification='read-only qualification evidence collection',at=datetime.now(UTC).isoformat(),
                broker_requests=0, broker_mutations=0, control_changes=0, notebook_writes=False,
                notebook=redact(notebook,(notebook['account_id'],)),tables=tables,
                facts=facts(db,plan),qualification_account_report=report_values(db),
                ordinary_activated=notebook['activated_at'] is not None, practice_execution_qualified=False,
                final_review='pending; collection never grants activation',
                protected_plan=save('plan.json',original),runs={},session_artifacts={})
            directory=DATA/'var/qualification'/controller
            for source in sorted(directory.iterdir()):
                if source.suffix not in ('.claim','.jsonl'):
                    continue
                info=source.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                    raise ValueError('Unexpected capture file type')
                result['session_artifacts'][source.name]=save(source.name,source.read_bytes())
            # Keep raw capture artifacts apart from the ordinary notebook export.
            for run in tables['runs']:
                if not any(i['run_id']==run['run_id'] and i['mode']=='qualification' for i in tables['run_invocations']):
                    continue
                refs={}
                for label,source in (('claim',directory/(run['session_date']+'.claim')),
                                     ('captures',directory/(run['run_id']+'.jsonl'))):
                    refs[label]=result['session_artifacts'].get(source.name,dict(status='missing'))
                result['runs'][run['run_id']]=refs
            db.rollback()
        after={str(p):sha256(p.read_bytes()).hexdigest() for p in files}
        result['notebook_files_unchanged']=before==after
        result['notebook_changed_files']=[name for name in before if before[name]!=after[name]]
        result['notebook_data_files_unchanged']=all(before[str(p)]==after[str(p)] for p in files[:2])
        result['notebook_file_hashes']={'before':before,'after':after}
        save('progress.json',(json.dumps(result,indent=2)+'\n').encode())
        # Exported records already have connection identifiers/credentials redacted.
        # Let the checkout owner review this private copy without another admin
        # handoff; the real notebook, claims and protected plan keep their owners.
        owner=ROOT.stat()
        for item in output.iterdir():
            os.chown(item,owner.st_uid,owner.st_gid)
        os.chown(output,owner.st_uid,owner.st_gid)
        if not result['notebook_data_files_unchanged']:
            raise ValueError('Notebook database or WAL changed during collection; inspect ' + str(output/'progress.json'))
        return dict(output=str(output/'progress.json'),missing=result['facts']['missing'],ordinary_activated=result['ordinary_activated'])
    finally:
        os.close(descriptor)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if os.geteuid()!=0:
        parser.error('Administrator access is required to read protected evidence; no broker or control action was attempted')
    output=args.output or ROOT/'var/verification/m10-automatic-collections'/('collection-'+uuid4().hex[:12])
    print(json.dumps(collect(output)),flush=True)


if __name__=='__main__':
    main()
