CREATE TABLE broker_transaction_observations (
    transaction_id TEXT NOT NULL REFERENCES broker_transactions,
    observed_at TEXT NOT NULL,
    body_json TEXT NOT NULL,
    PRIMARY KEY (transaction_id, body_json)
) STRICT;

INSERT INTO broker_transaction_observations (transaction_id, observed_at, body_json)
SELECT transaction_id, imported_at, body_json FROM broker_transactions;
