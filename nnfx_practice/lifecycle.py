"""One practice lifecycle with an immutable opening record; no order operations."""

from uuid import uuid4

from .broker import money
from .config import ConfigurationError, load_binding
from .control import maintenance
from .evidence import encode_evidence
from .notebook import _check_binding, open_notebook, transaction
from .reconciliation import _save_snapshot, _snapshot, reconcile_snapshot
from .strategy import select_strategy


INITIAL_REQUIREMENTS = ('strategy_qualification', 'account_preflight', 'candle_preflight', 'initial_account_resolution')
EXECUTION_REQUIREMENTS = (*INITIAL_REQUIREMENTS, 'm09_controller_controls', 'execution_authority')


def validate_strategy(binding):
    select_strategy(binding)


def evidence_record(broker, evidence, requirements):
    """References record externally reviewed prerequisites, never infer a pass.

    References alone cannot enable execution. Native practice trading additionally
    requires a verified, account-bound permit.
    """
    if not isinstance(evidence, dict) or any(
        not isinstance(evidence.get(key), str) or not evidence[key].strip() for key in requirements
    ):
        raise ConfigurationError('Missing required qualification evidence references')
    return encode_evidence({'source': broker.evidence_source, 'references': evidence}, broker.private_values)


def bound_broker(root, controller_id, broker):
    binding = load_binding(root, controller_id)
    if binding != broker.binding:
        raise ConfigurationError('Broker does not match the current registry binding')
    validate_strategy(binding)
    return binding


def require_clear(db, snapshot):
    if snapshot.trades or snapshot.orders:
        raise ConfigurationError('Account must have no remaining trades or pending orders')
    for sql in (
        "SELECT 1 FROM issues WHERE status = 'open'",
        "SELECT 1 FROM trade_sets WHERE terminal_at IS NULL",
        "SELECT 1 FROM trade_legs WHERE broker_state IS NULL OR broker_state = 'open'",
        "SELECT 1 FROM broker_attempts WHERE outcome IN ('prepared', 'pending', 'unknown')",
    ):
        if db.execute(sql).fetchone():
            raise ConfigurationError('Unresolved notebook activity requires evidenced operator disposition')


def initialize_qualification(root, controller_id, broker, *, service, evidence):
    # Check the permit before private configuration, maintenance or Q0 effects.
    broker.require_qualification_execution()
    binding = bound_broker(root, controller_id, broker)
    refs = evidence_record(broker, evidence, INITIAL_REQUIREMENTS)
    with maintenance(root, binding, service):
        with open_notebook(root, binding, create=True) as db:
            row = db.execute('SELECT * FROM notebook').fetchone()
            if row['qualification_snapshot_id'] is not None:
                # Never reset the cursor, previous attempts or Q0, including after a crash.
                reconcile_snapshot(db, broker, purpose='qualification_reopen')
                return row['qualification_snapshot_id']
            if row['imported_through_transaction_id'] is not None or any(
                db.execute(f'SELECT 1 FROM {table}').fetchone() for table in
                ('runs', 'broker_transactions', 'account_snapshots', 'trade_sets', 'issues')
            ):
                raise ConfigurationError('Cannot initialize over existing unbaselined history')
            read = broker.account()
            snapshot = _snapshot(read)
            require_clear(db, snapshot)
            money(snapshot.account['balance'])
            identifier = uuid4().hex
            with transaction(db):
                _save_snapshot(db, broker, identifier, 'qualification', read, broker.now())
                db.execute('''UPDATE notebook SET qualification_snapshot_id = ?, qualification_transaction_id = ?,
                              qualification_evidence_json = ?, imported_through_transaction_id = ?''',
                           (identifier, snapshot.boundary, refs, snapshot.boundary))
            return identifier


def require_invocation(db, broker, mode, evidence):
    _check_binding(db, broker.binding)
    validate_strategy(broker.binding)
    row = db.execute('SELECT * FROM notebook').fetchone()
    # "qualification" is a compatibility spelling in existing plans/callers.
    # A historical A0 is immutable evidence, not another executable mode.
    if mode not in ('practice', 'qualification'):
        raise ConfigurationError('Only practice trading is supported')
    if row['qualification_snapshot_id'] is None:
        raise ConfigurationError('Practice trading requires an initialized notebook')
    refs = evidence_record(broker, evidence, EXECUTION_REQUIREMENTS)
    broker.require_qualification_execution()
    return refs
