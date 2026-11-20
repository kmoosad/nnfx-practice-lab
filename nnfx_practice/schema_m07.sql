CREATE TABLE run_invocations (
    run_id TEXT PRIMARY KEY REFERENCES runs,
    mode TEXT NOT NULL CHECK (mode IN ('ordinary', 'qualification')),
    evidence_json TEXT,
    CHECK (mode != 'qualification' OR evidence_json IS NOT NULL)
) STRICT;

CREATE TRIGGER qualification_baseline_immutable BEFORE UPDATE ON notebook
WHEN OLD.qualification_snapshot_id IS NOT NULL AND (
    NEW.qualification_snapshot_id IS NOT OLD.qualification_snapshot_id
    OR NEW.qualification_transaction_id IS NOT OLD.qualification_transaction_id
    OR NEW.qualification_evidence_json IS NOT OLD.qualification_evidence_json
)
BEGIN
    SELECT RAISE(ABORT, 'Qualification baseline is immutable');
END;

CREATE TRIGGER activation_baseline_immutable BEFORE UPDATE ON notebook
WHEN OLD.activated_at IS NOT NULL AND (
    NEW.activation_snapshot_id IS NOT OLD.activation_snapshot_id
    OR NEW.activation_transaction_id IS NOT OLD.activation_transaction_id
    OR NEW.activation_evidence_json IS NOT OLD.activation_evidence_json
    OR NEW.activated_at IS NOT OLD.activated_at
)
BEGIN
    SELECT RAISE(ABORT, 'Activation baseline is immutable');
END;

CREATE TRIGGER baseline_snapshot_no_update BEFORE UPDATE ON account_snapshots
WHEN OLD.snapshot_id IN (SELECT qualification_snapshot_id FROM notebook UNION SELECT activation_snapshot_id FROM notebook)
BEGIN
    SELECT RAISE(ABORT, 'Bound baseline snapshot is immutable');
END;

CREATE TRIGGER baseline_snapshot_no_delete BEFORE DELETE ON account_snapshots
WHEN OLD.snapshot_id IN (SELECT qualification_snapshot_id FROM notebook UNION SELECT activation_snapshot_id FROM notebook)
BEGIN
    SELECT RAISE(ABORT, 'Bound baseline snapshot cannot be deleted');
END;
