"""Repair only the installed-package permission checkpoint and finish disposition."""

import os
from pathlib import Path
import sys


if __name__=='__main__':
    if os.geteuid()!=0 or sys.argv[1:]:
        raise SystemExit('Administrator access is required; no action attempted')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from deploy.continue_gbpcad_reconciliation import main
    raise SystemExit(main(checkpoint_id='gbpcad-continue-6a8d0b04c443',installed_checkpoint=True))
