CREATE TABLE notebook (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    controller_id TEXT NOT NULL,
    notebook_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    home_currency TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    lookback_candles INTEGER NOT NULL CHECK (lookback_candles >= 15),
    qualification_snapshot_id TEXT,
    qualification_transaction_id TEXT,
    qualification_evidence_json TEXT,
    activation_snapshot_id TEXT,
    activation_transaction_id TEXT,
    activation_evidence_json TEXT,
    activated_at TEXT,
    imported_through_transaction_id TEXT,
    FOREIGN KEY (qualification_snapshot_id, qualification_transaction_id)
        REFERENCES account_snapshots (snapshot_id, last_transaction_id),
    FOREIGN KEY (activation_snapshot_id, activation_transaction_id)
        REFERENCES account_snapshots (snapshot_id, last_transaction_id),
    CHECK ((qualification_snapshot_id IS NULL) = (qualification_transaction_id IS NULL)),
    CHECK ((qualification_snapshot_id IS NULL) = (qualification_evidence_json IS NULL)),
    CHECK ((activated_at IS NULL) = (activation_snapshot_id IS NULL)),
    CHECK ((activated_at IS NULL) = (activation_transaction_id IS NULL)),
    CHECK ((activated_at IS NULL) = (activation_evidence_json IS NULL)),
    CHECK (activated_at IS NULL OR (
        qualification_snapshot_id IS NOT NULL AND activation_snapshot_id != qualification_snapshot_id
    ))
) STRICT;

CREATE TRIGGER notebook_binding_immutable BEFORE UPDATE OF
    singleton, controller_id, notebook_id, account_id, home_currency,
    strategy_version, manifest_json, manifest_hash, lookback_candles ON notebook
BEGIN
    SELECT RAISE(ABORT, 'Notebook binding is immutable');
END;

CREATE TRIGGER notebook_binding_no_delete BEFORE DELETE ON notebook
BEGIN
    SELECT RAISE(ABORT, 'Notebook binding cannot be deleted');
END;

CREATE TRIGGER notebook_binding_no_replace BEFORE INSERT ON notebook
WHEN EXISTS (SELECT 1 FROM notebook)
BEGIN
    SELECT RAISE(ABORT, 'Notebook binding cannot be replaced');
END;

CREATE TABLE account_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    purpose TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    responded_at TEXT,
    last_transaction_id TEXT,
    balance TEXT,
    unrealised_pl TEXT,
    margin_used TEXT,
    margin_available TEXT,
    home_currency TEXT,
    broker_state_json TEXT,
    reconciliation_status TEXT NOT NULL CHECK (reconciliation_status IN ('pending', 'reconciled', 'failed')),
    reconciliation_error TEXT,
    UNIQUE (snapshot_id, last_transaction_id)
) STRICT;

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    strategy_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds REAL,
    session_date TEXT NOT NULL,
    lookback_candles INTEGER NOT NULL CHECK (lookback_candles >= 15),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'completed_with_errors', 'failed')),
    last_progress_at TEXT NOT NULL,
    sizing_balance TEXT,
    sizing_balance_at TEXT,
    sizing_transaction_id TEXT,
    final_snapshot_id TEXT REFERENCES account_snapshots,
    refresh_error TEXT,
    CHECK ((sizing_balance IS NULL) = (sizing_balance_at IS NULL)),
    CHECK ((sizing_balance IS NULL) = (sizing_transaction_id IS NULL))
) STRICT;

CREATE TRIGGER run_sizing_balance_immutable BEFORE UPDATE ON runs
WHEN OLD.sizing_balance IS NOT NULL AND (
    NEW.sizing_balance IS NOT OLD.sizing_balance OR NEW.sizing_balance_at IS NOT OLD.sizing_balance_at
    OR NEW.sizing_transaction_id IS NOT OLD.sizing_transaction_id
)
BEGIN
    SELECT RAISE(ABORT, 'Run sizing balance is immutable');
END;

CREATE TABLE stages (
    run_id TEXT NOT NULL REFERENCES runs,
    stage TEXT NOT NULL CHECK (stage IN ('manage_open', 'manage_new')),
    status TEXT NOT NULL CHECK (status IN (
        'not_started', 'running', 'completed', 'completed_with_errors', 'failed', 'blocked'
    )),
    started_at TEXT,
    ended_at TEXT,
    duration_seconds REAL,
    current_step TEXT,
    current_pair TEXT,
    reconciliation_progress_json TEXT,
    expected_pair_count INTEGER CHECK (expected_pair_count >= 0),
    failure_summary TEXT,
    PRIMARY KEY (run_id, stage)
) STRICT;

CREATE TABLE pair_decisions (
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    pair TEXT NOT NULL,
    pair_order INTEGER NOT NULL CHECK (pair_order BETWEEN 1 AND 28),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    capture_json TEXT,
    c1_json TEXT,
    exit_json TEXT,
    atr TEXT,
    atr_valid INTEGER CHECK (atr_valid IN (0, 1)),
    triggers_json TEXT,
    sizing_json TEXT,
    requested_action TEXT,
    outcome TEXT CHECK (outcome IN ('completed', 'skipped', 'failed')),
    reason TEXT,
    set_id TEXT REFERENCES trade_sets,
    issue_id TEXT REFERENCES issues,
    PRIMARY KEY (run_id, stage, pair),
    FOREIGN KEY (run_id, stage) REFERENCES stages,
    CHECK ((ended_at IS NULL) = (outcome IS NULL))
) STRICT;

CREATE TABLE trade_sets (
    set_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'manage_new' CHECK (stage = 'manage_new'),
    pair TEXT NOT NULL,
    strategy_hash TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('long', 'short')),
    entry_atr TEXT NOT NULL,
    stop_distance TEXT NOT NULL,
    expected_leg_count INTEGER NOT NULL DEFAULT 2 CHECK (expected_leg_count = 2),
    establishment_status TEXT NOT NULL CHECK (establishment_status IN (
        'pending', 'complete', 'incomplete', 'not_opened'
    )),
    established_at TEXT,
    terminal_at TEXT,
    UNIQUE (run_id, stage, pair),
    FOREIGN KEY (run_id, stage, pair) REFERENCES pair_decisions
) STRICT;

CREATE TRIGGER trade_set_entry_immutable BEFORE UPDATE OF entry_atr, stop_distance ON trade_sets
WHEN NEW.entry_atr IS NOT OLD.entry_atr OR NEW.stop_distance IS NOT OLD.stop_distance
BEGIN
    SELECT RAISE(ABORT, 'Trade set entry ATR and stop distance are immutable');
END;

CREATE TABLE trade_legs (
    set_id TEXT NOT NULL REFERENCES trade_sets,
    leg_no INTEGER NOT NULL CHECK (leg_no IN (1, 2)),
    broker_trade_id TEXT UNIQUE,
    planned_units TEXT NOT NULL,
    initial_units TEXT,
    current_units TEXT,
    broker_state TEXT CHECK (broker_state IN ('open', 'closed', 'not_opened')),
    broker_state_at TEXT,
    broker_state_transaction_id TEXT,
    entry_price TEXT,
    entry_at TEXT,
    original_stop TEXT,
    original_stop_order_id TEXT,
    current_stop TEXT,
    current_stop_order_id TEXT,
    intended_target TEXT,
    confirmed_target TEXT,
    target_order_id TEXT,
    stop_to_entry_status TEXT NOT NULL DEFAULT 'not_due' CHECK (stop_to_entry_status IN (
        'not_due', 'due', 'confirmed', 'failed', 'unknown'
    )),
    exit_price TEXT,
    exit_at TEXT,
    exit_transaction_id TEXT,
    exit_reason TEXT,
    PRIMARY KEY (set_id, leg_no)
) STRICT;

CREATE TRIGGER leg_original_stop_immutable BEFORE UPDATE ON trade_legs
WHEN (OLD.original_stop IS NOT NULL AND NEW.original_stop IS NOT OLD.original_stop)
    OR (OLD.original_stop_order_id IS NOT NULL AND NEW.original_stop_order_id IS NOT OLD.original_stop_order_id)
BEGIN
    SELECT RAISE(ABORT, 'Original stop is immutable');
END;

CREATE TABLE broker_attempts (
    attempt_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    pair TEXT,
    set_id TEXT REFERENCES trade_sets,
    leg_no INTEGER,
    purpose TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    payload_json TEXT,
    client_id TEXT UNIQUE,
    prepared_at TEXT NOT NULL,
    responded_at TEXT,
    http_status INTEGER,
    request_id TEXT,
    broker_order_id TEXT,
    broker_trade_id TEXT,
    broker_transaction_id TEXT,
    response_json TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('prepared', 'confirmed', 'rejected', 'cancelled', 'pending', 'unknown')),
    error TEXT,
    FOREIGN KEY (run_id, stage) REFERENCES stages,
    FOREIGN KEY (run_id, stage, pair) REFERENCES pair_decisions,
    FOREIGN KEY (set_id, leg_no) REFERENCES trade_legs,
    CHECK (leg_no IS NULL OR set_id IS NOT NULL)
) STRICT;

CREATE TABLE broker_transactions (
    transaction_id TEXT PRIMARY KEY,
    broker_at TEXT NOT NULL,
    type TEXT NOT NULL,
    batch_id TEXT,
    request_id TEXT,
    imported_at TEXT NOT NULL,
    body_json TEXT NOT NULL
) STRICT;

CREATE TABLE fills (
    transaction_id TEXT NOT NULL REFERENCES broker_transactions,
    broker_trade_id TEXT NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('open', 'reduce', 'close')),
    order_id TEXT,
    units TEXT NOT NULL,
    price TEXT,
    filled_at TEXT NOT NULL,
    reason TEXT,
    set_id TEXT,
    leg_no INTEGER,
    PRIMARY KEY (transaction_id, broker_trade_id, effect),
    FOREIGN KEY (set_id, leg_no) REFERENCES trade_legs,
    CHECK ((set_id IS NULL) = (leg_no IS NULL))
) STRICT;

CREATE TABLE ledger_entries (
    transaction_id TEXT NOT NULL REFERENCES broker_transactions,
    component_key TEXT NOT NULL,
    amount TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('trading_pl', 'financing', 'commission', 'other_charge', 'cash_adjustment')),
    broker_trade_id TEXT,
    source_field TEXT NOT NULL,
    posted INTEGER NOT NULL CHECK (posted IN (0, 1)),
    PRIMARY KEY (transaction_id, component_key)
) STRICT;

CREATE TABLE issues (
    issue_id TEXT PRIMARY KEY,
    pair TEXT,
    code TEXT NOT NULL,
    first_observed_at TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    set_id TEXT REFERENCES trade_sets,
    leg_no INTEGER,
    attempt_id TEXT REFERENCES broker_attempts,
    broker_evidence_json TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    operator_disposition TEXT,
    operator_id TEXT,
    resolved_at TEXT,
    disposition_evidence_json TEXT,
    FOREIGN KEY (set_id, leg_no) REFERENCES trade_legs,
    CHECK (leg_no IS NULL OR set_id IS NOT NULL)
) STRICT;

CREATE UNIQUE INDEX reserved_pair ON trade_sets (pair) WHERE terminal_at IS NULL;
CREATE INDEX trade_sets_pair ON trade_sets (pair);
CREATE INDEX open_issues_pair ON issues (pair) WHERE status = 'open';
CREATE INDEX runs_started ON runs (started_at, run_id);
CREATE INDEX decisions_started ON pair_decisions (started_at, run_id);
