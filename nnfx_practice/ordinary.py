"""Native ordinary activation and dispatch, available only with a sealed final review."""

from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd

from . import qualification as q
from .broker import PracticeBroker
from .config import ConfigurationError, load_binding
from .lifecycle import ACTIVATION_REQUIREMENTS, activate_ordinary, validate_strategy
from .qualification_review import artifact, load_review, verify_notebook


_VERIFIED = object()


class OrdinaryPermit(q.QualificationPermit):
    def check(self, binding):
        if (self._verification is not _VERIFIED or binding != self.binding or self.pid != os.getpid()
                or sha256(q.sealed_bytes(self.path)).hexdigest() != self.digest):
            raise ConfigurationError('Ordinary permit changed or was revoked')

    @property
    def references(self):
        review_ref = self.plan['activation_review']
        reference = review_ref['path'] + '#sha256=' + review_ref['sha256']
        return {name: reference for name in ACTIVATION_REQUIREMENTS}

    def verify_qualification(self, db):
        self.check(self.binding)
        return verify_notebook(db, self.plan, load_review(self.plan))

    def verify_activation(self, db):
        self.check(self.binding)
        row = db.execute('SELECT * FROM notebook').fetchone()
        snapshot = db.execute('SELECT * FROM account_snapshots WHERE snapshot_id = ?', (row['activation_snapshot_id'],)).fetchone()
        evidence = json.loads(row['activation_evidence_json'] or '{}')
        if (not row['activated_at'] or not snapshot or snapshot['purpose'] != 'activation'
                or snapshot['reconciliation_status'] != 'reconciled'
                or snapshot['last_transaction_id'] != row['activation_transaction_id']
                or evidence.get('source') != 'practice_get' or evidence.get('references') != self.references):
            raise ConfigurationError('Ordinary dispatch requires this reviewed, committed activation')


def load_permit(root, controller, operation, *, now=None):
    if Path(root) != q.DATA_ROOT or not q._RUN.fullmatch(controller) or operation not in ('activate', 'run', 'inspect'):
        raise ConfigurationError('Ordinary execution is disabled outside the reviewed deployed operation')
    path = q.PLAN_DIRECTORY / (controller + '.json')
    raw = q.sealed_bytes(path)
    plan = q._document(raw)
    if (type(plan.get('version')) is not int or plan['version'] != 2 or plan.get('mode') != 'ordinary'
            or plan.get('enabled') is not True or plan.get('controller_id') != controller
            or plan.get('host') != q.PRACTICE_HOST or plan.get('kernel') != q.host_identity()[1]
            or plan.get('code_sha256') != q.code_identity()
            or plan.get('config_sha256') != sha256((Path(root) / 'config.toml').read_bytes()).hexdigest()
            or not q._RUN.fullmatch(plan.get('run_id', '')) or len(plan['run_id']) > 54):
        raise ConfigurationError('Ordinary plan is missing, disabled or differs from reviewed deployment')
    slot = q.dispatch_slot(plan, 'run' if operation == 'run' else 'inspect', now or datetime.now(UTC))
    # Reuse the actual prerequisite observations, with their original authority
    # limited to qualification. The final review carries separate ordinary authority.
    prerequisites = q._document(artifact(plan.get('qualification_plan')))
    for key in ('controller_id', 'notebook_id', 'account_binding_sha256', 'manifest_sha256', 'code_sha256', 'config_sha256', 'kernel'):
        if prerequisites.get(key) != plan.get(key):
            raise ConfigurationError('Ordinary plan differs from the qualified binding')
    q.validate_evidence(prerequisites, q._evidence(prerequisites))
    load_review(plan)
    q.schedule_controls(controller, ordinary=True, running=operation == 'run')
    # host_controls normally requires ordinary scheduling off. At dispatch the
    # equivalent clock/service contract is checked without that inactive guard.
    if operation != 'run':
        q.host_controls(controller, 'inspect')
    else:
        q.host_service(controller, 'run')
    if operation == 'inspect':
        return {'ordinary_review_valid': True, 'activation_checked': False, 'timer_enabled_by_check': False}
    if os.getuid() != pwd.getpwnam('nnfx-run').pw_uid:
        raise ConfigurationError('Ordinary operations require the dedicated writer')
    binding = load_binding(root, controller)
    validate_strategy(binding)
    if (q.account_identity(binding) != plan['account_binding_sha256']
            or binding.manifest.hash != plan['manifest_sha256']
            or binding.experiment.notebook_id != plan['notebook_id']):
        raise ConfigurationError('Private ordinary binding differs')
    permit = OrdinaryPermit(binding, plan, path, sha256(raw).hexdigest(), operation, slot=slot)
    permit._verification = _VERIFIED
    return permit


def execute(root, controller, operation):
    permit = load_permit(root, controller, operation)
    from .host import controller_service
    from .master import run_master
    with PracticeBroker(permit.binding, ordinary=permit) as broker:
        if operation == 'activate':
            return activate_ordinary(root, controller, broker, service=controller_service(controller), evidence=permit.references)
        # Same date-claim namespace as qualification prevents a transition-day
        # duplicate and preserves all legacy claims. Ordinary candles stay in memory.
        permit.claim(root)
        return run_master(root, controller, broker, mode='ordinary', run_id=permit.run_id,
                          code_hash=permit.plan['code_sha256'], config_hash=permit.plan['config_sha256'])
