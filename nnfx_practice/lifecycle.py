"""Explicit qualification and ordinary activation; no timer or order operations."""

import json
from pathlib import Path
from uuid import uuid4

from strategies import t3_bandpass_v1 as strategy

from .broker import money
from .config import ConfigurationError, load_binding
from .control import maintenance
from .evidence import canonical_json, encode_evidence
from .notebook import _check_binding, open_notebook, transaction
from .reconciliation import _save_snapshot, _snapshot, reconcile_snapshot


INITIAL_REQUIREMENTS = ('strategy_qualification', 'account_preflight', 'candle_preflight', 'initial_account_resolution')
EXECUTION_REQUIREMENTS = (*INITIAL_REQUIREMENTS, 'm09_controller_controls', 'execution_authority')
ACTIVATION_REQUIREMENTS = (*EXECUTION_REQUIREMENTS, 'm10_final', *(f'A{i:02}' for i in range(1, 17)))


def validate_strategy(binding):
    packaged = json.loads(Path(strategy.__file__).with_name('manifest.json').read_text())
    if (binding.experiment.strategy_version != 't3_bandpass_v1'
            or binding.manifest.body != canonical_json(packaged)
            or binding.connection.lookback_candles != strategy.LOOKBACK_CANDLES):
        raise ConfigurationError('Lifecycle requires qualified t3_bandpass_v1 and exactly 386 candles')


def evidence_record(broker, evidence, requirements):
    """References record externally reviewed prerequisites, never infer a pass.

    References alone cannot enable execution. Live qualification additionally
    requires a verified permit; native activation also validates completed evidence.
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
    if mode == 'ordinary':
        if row['activated_at'] is None:
            raise ConfigurationError('Ordinary startup requires committed activation')
        refs = None
    elif mode == 'qualification':
        if row['qualification_snapshot_id'] is None or row['activated_at'] is not None:
            raise ConfigurationError('Qualification requires an initialized, unactivated notebook')
        refs = evidence_record(broker, evidence, EXECUTION_REQUIREMENTS)
    else:
        raise ConfigurationError('Expected explicit ordinary or qualification invocation')
    if mode == 'qualification':
        broker.require_qualification_execution()
    else:
        broker.require_ordinary_execution()
        if broker._ordinary is not None:
            broker._ordinary.verify_activation(db)
    return refs


def activate_ordinary(root, controller_id, broker, *, service, evidence):
    broker.require_ordinary_execution('activate')
    binding = bound_broker(root, controller_id, broker)
    refs = evidence_record(broker, evidence, ACTIVATION_REQUIREMENTS)
    with maintenance(root, binding, service):
        with open_notebook(root, binding) as db:
            row = db.execute('SELECT * FROM notebook').fetchone()
            if row['qualification_snapshot_id'] is None:
                raise ConfigurationError('Qualification must be initialized first')
            if row['activated_at'] is not None:
                saved = db.execute('SELECT * FROM account_snapshots WHERE snapshot_id = ?',
                                   (row['activation_snapshot_id'],)).fetchone()
                if (saved is None or saved['purpose'] != 'activation' or saved['reconciliation_status'] != 'reconciled'
                        or saved['last_transaction_id'] != row['activation_transaction_id']
                        or not row['activation_evidence_json']):
                    raise ConfigurationError('Existing activation record is inconsistent')
                if broker._ordinary is not None:
                    broker._ordinary.verify_activation(db)
                return row['activation_snapshot_id']

            if broker._ordinary is not None:
                broker._ordinary.verify_qualification(db)

            def commit_activation(identifier, snapshot):
                require_clear(db, snapshot)
                db.execute('''UPDATE notebook SET activation_snapshot_id = ?, activation_transaction_id = ?,
                              activation_evidence_json = ?, activated_at = ? WHERE activated_at IS NULL''',
                           (identifier, snapshot.boundary, refs, broker.now()))

            return reconcile_snapshot(db, broker, purpose='activation', on_reconciled=commit_activation)
