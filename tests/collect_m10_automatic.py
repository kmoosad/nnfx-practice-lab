"""Collect existing qualification evidence without arming, broker reads or notebook writes.

Independent of the optional final-host observer. Open trades, rejected attempts,
issues and unfinished sessions are retained and reported, never repaired.
"""

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/var/lib/nnfx-practice')


def collect(output, controller='practice-a'):
    from nnfx_practice import qualification as q
    from nnfx_practice.config import read_registry
    from nnfx_practice.evidence import redact
    from nnfx_practice.notebook import open_readonly
    from nnfx_practice.qualification_review import TABLES, facts, report_values
    original = q.sealed_bytes(q.PLAN_DIRECTORY/(controller+'.json'))
    plan = q._document(original)
    experiment = read_registry(DATA)[controller]
    path = experiment.notebook_path(DATA)
    files = (path, Path(str(path)+'-wal'), Path(str(path)+'-shm'))
    before = {str(p):sha256(p.read_bytes()).hexdigest() for p in files}
    descriptor = os.open(path.with_suffix('.lock'), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(descriptor,fcntl.LOCK_EX | fcntl.LOCK_NB)
        output.mkdir(parents=True,exist_ok=False)
        output.chmod(0o700)
        def save(name, raw):
            target=output/name
            with target.open('xb') as f:
                f.write(raw)
            target.chmod(0o600)
            return dict(path=str(target),sha256=sha256(raw).hexdigest())
        with open_readonly(DATA,experiment) as db:
            db.execute('BEGIN')
            notebook=dict(db.execute('SELECT * FROM notebook').fetchone())
            tables={t:[dict(r) for r in db.execute('SELECT * FROM '+t)] for t in TABLES}
            result=dict(classification='read-only qualification evidence collection',at=datetime.now(UTC).isoformat(),
                broker_requests=0, broker_mutations=0, control_changes=0, notebook_writes=False,
                notebook=redact(notebook,(notebook['account_id'],)),tables=tables,
                facts=facts(db,plan),qualification_account_report=report_values(db),
                ordinary_activated=notebook['activated_at'] is not None, practice_execution_qualified=False,
                final_review='pending; collection never grants activation',
                protected_plan=save('plan.json',original),runs={})
            # Keep raw capture artifacts apart from the ordinary notebook export.
            for run in tables['runs']:
                if not any(i['run_id']==run['run_id'] and i['mode']=='qualification' for i in tables['run_invocations']):
                    continue
                refs={}
                directory=DATA/'var/qualification'/controller
                for label,source in (('claim',directory/(run['session_date']+'.claim')),
                                     ('captures',directory/(run['run_id']+'.jsonl'))):
                    try:
                        info=source.lstat()
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:
                            raise ValueError('Unexpected capture file type')
                        refs[label]=save(run['run_id']+'.'+('claim' if label=='claim' else 'jsonl'),source.read_bytes())
                    except FileNotFoundError:
                        refs[label]=dict(status='missing')
                result['runs'][run['run_id']]=refs
            db.rollback()
        after={str(p):sha256(p.read_bytes()).hexdigest() for p in files}
        result['notebook_files_unchanged']=before==after
        if before!=after:
            raise ValueError('Notebook files changed during collection; preserve output and inspect')
        save('progress.json',(json.dumps(result,indent=2)+'\n').encode())
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
