# Detailed design

Approved 16 November 2026; later comparison/history decisions incorporated.
[Brief](../PROJECT_BRIEF.md) owns trading rules; [architecture](ARCHITECTURE.md) owns
workflow/presentation; [status](STATUS.md) records operation and account evidence limits.

## Configuration and records

Public `config.toml` binds controller/notebook IDs, name, strategy version and
connection key. Owner-only `.env` supplies prefixed ACCOUNT_ID, TOKEN,
HOME_CURRENCY and LOOKBACK_CANDLES. Pin requests to api-fxpractice.oanda.com and
the bound account, even with shared tokens. Exclude credentials/headers from evidence.

Freeze research/source, conversion/dependency hashes, parameters, output/rule IDs,
numeric semantics, qualified count/history and evidence references in the manifest.
Startup checks unique bindings, safe paths, notebook identity, manifest/count and
broker account/currency before trading. Log mismatches only in a safely bound
notebook or redacted service log. Token/name changes preserve binding; strategy/
rule/parameter/count/origin changes require a new binding. No defaults.
[Candle/ATR contract](ARCHITECTURE.md#candle-and-signal-inputs) owns calculations.

One `var/notebooks/<notebook-id>.sqlite3` per account uses foreign keys, WAL, short
transactions and synchronous=FULL. IDs/decimal prices/units/money are text; UTC
preserves broker precision. JSON holds bounded evidence; relationships use columns.
No network inside a write transaction.

| Record | Durable meaning |
| --- | --- |
| `notebook` singleton | Schema; immutable controller/notebook/account/currency/manifest; Q0, historical A0/evidence/time; imported-through cursor. |
| `runs`, `stages`, `run_invocations` | Run/config/code/strategy, count, UTC/session/duration, fixed sizing balance/time/boundary, snapshot/error, stage progress, mode/prerequisites. |
| `pair_decisions` | Run/stage/pair/order, capture and current/prior operands/rule IDs, ATR validity, triggers, sizing, action/outcome/reason and related set/issues. |
| `trade_sets`, `trade_legs` | Two expected legs, direction, frozen ATR/distance, run/balance, establishment/terminal time; unique broker IDs, planned/initial/current units, confirmed fills/state/boundary, original/current protection/order IDs, stop-to-entry, final exit. Unknown = null. |
| `broker_attempts` | Local/client identity, run/stage/set/leg/pair, purpose, redacted method/path/payload, prepared/response times, HTTP status, RequestID, broker IDs/body and classified outcome/error. |
| `broker_transactions`, `broker_transaction_observations` | Unique broker ID, cumulative accepted facts; distinct redacted sources keyed by ID/body, first observation time. |
| `fills`, `ledger_entries` | Unique transaction/trade/effect: units/price/time/cause. Unique transaction/component: signed home amount, category/allocation/source, posted/informational. |
| `account_snapshots`, `issues` | Snapshot purpose/time/boundary/amounts/state/reconciliation; issue scope/code/identities/evidence, first/last observation and operator disposition/time. |

Progress counts final pair decisions: Stage 1 survivors after 3.1; Stage 2,
28 pairs. A 3.1 stop attempt links its set, not a decision; issues name the pair.
Track reconciliation separately. Sizing JSON retains metadata/conversions, both
labelled margin reads, Trade 1 verification and establishment transaction/batch/trade/order proof.

Schema 2: invocation labels, immutable Q0/A0 and atomic master/children/invocation
commit; no invented legacy component modes. Schema 3: seed source observations
atomically after binding validation; preserve all records/baselines/cursor.
Deploy compatible schema 2/3 readers before writer upgrades; readers never migrate.
Include observations in review digests/exports.

## Run and commit contracts

Create master/children before account work with UTC start, New York session,
identities and count; use a monotonic clock for duration. Never resume run IDs.
[Workflow](ARCHITECTURE.md#numbered-workflow) owns sequencing.
Keep pending sizing evidence outside reporting; later balances never replace it.
Fatal Stage 1/balance failure blocks entry; isolated pair failure can continue
only with reliable account reads/writes.

1. Commit observations/triggers, reserved set/both planned legs and each mutation's
   own attempt; end the write transaction before its single send.
2. Before another change, commit response/confirmed facts/fills/protection/issues
   together. Fill history gaps first; response IDs never advance the cursor.
3. Atomically commit complete history, source observations, projections and cursor;
   conflict/balance failure rolls everything back.
4. Commit pair outcome/progress/time before advancing. Final reporting imports
   through its snapshot; failed refresh retains the last good snapshot.

## State rules

HTTP success is not proof; these rules own retries and eligibility.

| Record | Allowed transition and evidence |
| --- | --- |
| Run/stage | Child `not_started` → `running` → `completed`, `completed_with_errors` or `failed`; prior fatal failure may leave it `blocked`. Interrupted running rows stay unfinished. Account-wide uncertainty/write failure ends mutations. |
| Attempt | Commit `prepared`; only its creator may send, once. Interrupted attempts stay unresolved, even if possibly unsent. Evidence sets confirmed/rejected/cancelled/pending; ambiguous response/timeout is unknown. Never automatically resend failed/uncertain mutations, repair orders or replace legs. |
| Establishment | Pending → complete requires proof both distinct legs/protection coexisted. Failed/uncertain steps stop entry; unresolved effects/protection need an issue. Reconcile interrupted pending sets as incomplete/uncertain with an issue. Wholly rejected/no-fill is not_opened; release only with proof neither leg opened and no issue. Filled Trade 1/rejected Trade 2 stays incomplete after closure; exits preserve historical completion. |
| Leg | Only broker evidence sets open/closed/not_opened. Missing open-list entries retain last confirmed state and create uncertainty; absence/404 never proves closure. |
| Stop-to-entry | Confirm Trade 1 TP; closed Trade 2/already-equal stop needs no request. Prior failed or prepared/pending/unknown change bars reissue. Broker evidence must confirm new stop ID/price or intervening closure; rejection/uncertainty creates a failed/unknown issue that later confirmation cannot clear. |
| Signal close | Guard surviving legs independently. Rejected/unresolved close creates an issue, barring automatic repeat; other eligible legs may close. Protection issues alone never suppress valid exits. |
| Issue/eligibility | Records determine eligibility; no mutable flag. Entry requires no open/unresolved leg, reserved set or open pair issue. Reconciliation never clears issues. Evidenced disposition resolves only its issue, preserving failure history and occupancy/uncertainty guards. |

Unique broker/client/derived IDs prevent duplicates. A partial unique set index
reserves each pair until all legs are closed/not opened and entry uncertainty
resolved; terminal sets retain issues. First confirmed protection is immutable;
attempts retain requests, evidence updates current levels. Separate signal reasons
from actual broker closure causes.

## Reconciliation procedure

At boundary S capture full account trades/orders/amounts. Under `/v3/accounts/{boundAccountID}` use `GET /`,
`/instruments`, `/summary`, `/pricing?instruments={instrument}&includeHomeConversions=true`,
instrument candles, `/transactions/sinceid?id={cursor}` or bounded pages/ranges,
targeted transaction/trade/order GETs. Retain pricing time, tradeable status,
bid/ask and base/quote conversions. Translate `EUR-USD` to `EUR_USD`. Metadata
precedes pairs; label summary reads sizing_balance, margin_before_set or margin_before_leg_2.

Import unfiltered history after the cursor through S in broker order/batches;
retain later evidence for a consistent boundary. Integer gaps cannot prove missing
transactions; never advance to the highest observed ID. Retrieve complete history
and all referenced/known facts. Unobserved omissions without balance effects or
references cannot be inferred.
Match account/trade/order/transaction/client/request identities and deduplicate.
Retrieve missing legs' closing references/fills; check both stops if both legs
are absent. Preserve each cause; unresolved legs block their pair.

Unexpected trades/orders create instrument issues; never automatically adopt/cancel
them. Unattributable activity, missing history or unexplained balance makes account
state unreliable. Publish only history/money-reconciled snapshots; isolated pair
issues may remain. Older observations/history cannot roll back confirmed leg/order
state. Refresh snapshots preceding the cursor or fail visibly. Missing history
through a prior response ends dependent work; retain evidence.

### Repeated transaction policy

Owner agreed field-aware comparison on 21 November, later extended by single-close
evidence. [transaction_records.py](../nnfx_practice/transaction_records.py) owns
field locations; arbitrary differences remain conflicts.

- Strict identity/instrument/time/reason/trade membership/protection; missing core
  fields or changed prices/quantities conflict. Compare known decimal strings by
  exact value, including nested price/conversion/fee fields. No coercion
  of IDs, arbitrary strings, null, booleans, JSON numbers or invalid decimals.
- Match `tradesClosed` by unique trade ID; reject duplicates/membership changes.
  Other arrays retain order. Apply the same comparison within a fetched batch.
- Known supplements may appear/disappear without erasing facts: fill/per-trade
  commission, guaranteed execution fee, dividend adjustment; per-trade P/L/financing;
  half-spread cost/initial margin; client tags/comments and transfer comments.
  Shared values must agree. Spread/margin descriptions are not extra debits.
- Accept zero-valued `baseFinancingHomeConversionCost`,
  `guaranteedExecutionFeeHomeConversionCost`, `homeConversionCost` and
  `plHomeConversionCost` on fills and opened/reduced/closed details. Nonzero requires
  a fill closing exactly one trade, opening/reducing none, with
  accountBalance, matching transaction/trade nonzero P/L and identical
  plHomeConversionCost/homeConversionCost at both levels. Cost must be nonpositive
  and no larger than absolute P/L; financing/guaranteed-fee conversion components
  are zero at both levels. Disclosures are included in P/L, never extra debits.
  Complete history must explain transaction/snapshot balances.
  Other nonzero shapes, invalid values and unknown changes block import.
- New posted amounts use unique existing mappings; a nonzero addition requires
  broker accountBalance and a transaction beyond the prior imported cursor.
  Never rewrite completed account totals. Later allocations are informational;
  nonzero fill allocations require their account total; complete allocations must
  sum to it. Match existing postings; never silently overwrite or ignore them.

Keep distinct redacted bodies/cumulative facts. Conflicts identify ID/paths and
roll back import. Comparison permits no retry, replacement leg or issue resolution.

## Sizing and two-leg entry

Let B = fixed 4.1 balance, a = frozen signal ATR, q = returned quote-currency
`accountLoss`: finite/positive even for home-matching quotes. Never substitute 1,
accountGain or positionValue. [A05](ACCEPTANCE.md#a05-sizing-and-margin) owns live
identity-factor/applicability checks. Round ticks nearest, half-away-from-zero;
retain raw/rounded values; reject zero/wrong-side/unsupported distances.

```text
budget = B × 0.01
step = 10 ** -tradeUnitsPrecision
d = round_to_price_tick(1.5 × a)
units = floor((budget / (d × q)) / step) × step
planned risk per leg = units × d × q <= budget
```

Bound order size and combined remaining instrument position limit; round down,
reject below-minimum/nonpositive/nonfinite inputs, then apply direction.
Equal units require account evidence; no silent size fallback.
Retain B/a/d/q, currency, pricing time, limits/precision and risk. Margin uses base
`positionValue` (1 when base is home), applicable instrument/account override rate
and its source. Require current margin for both legs; recheck before Trade 2 with B
unchanged. Failure after Trade 1 leaves an incomplete set; never shrink/queue a leg.

Reserve both legs; apply commit/attempt guards to each step:

1. Trade 1 `MARKET`, signed units, `FOK`, `OPEN_ONLY`, supported order/trade client
   extensions and GTC `stopLossOnFill.distance=d`; confirm distinct ID/units/fill/stop.
2. Set GTC takeProfit.price at actual fill ± a, valid tick/correct side, via
   `PUT /trades/{id}/orders`, omitting stopLoss. Verify before proceeding. The
   stop-only interval is explicit; target rejection leaves an incomplete set.
3. Verify Trade 1 survives protected, recheck margin, send Trade 2 by the same
   market/stop mechanism with no target. Confirm distinct ID/units/fill/stop.
4. Prove both legs/protection coexisted using transaction order and trade/orders.
   Earlier price exit is incomplete; exit after establishment is normal.

Reducing another trade, wrong units or missing ID/protection fails the path;
retain actual effects. Stops use each actual fill and d, unaffected by later ATR.
Scheduled TP management needs no candle/new ATR; request Trade 2's exact entry
stop only when eligible. Unrepresentable entry creates an issue, never a substitute level. Signal close uses
`PUT /trades/{id}/close`, `units="ALL"`, Trade 1 then Trade 2, confirming each.
A queued close occupies the pair; retain intervening closure causes.
Planned risk never guarantees realised loss or zero after an entry stop.

## Failure and disposition

Unavailable input/market/conversion or pre-set margin produces a reasoned skip;
calculation errors remain failures. Isolated pair failures may continue; binding,
authentication, history/balance or write failure ends reliable account work.
A post-action write failure leaves committed intent and a redacted service error;
the dashboard may remain unfinished.
Local disposition under [maintenance exclusion](OPERATIONS.md#maintenance-and-evidence-collection)
uses fresh read-only reconciliation; store issue/operator/time/explanation and
matching terminal/restored-protection evidence. Send no orders. It may record
unsent planned legs or uncertain targets on confirmed closed trades;
prepared entry, pending orders, unsupported/unattributed uncertainty stay open.
A restored stop does not release an open leg. The dashboard only observes.

## Monetary records

Closed legs retain reductions, absolute-unit-weighted exit price, final time and
mixed causes; pips use `10 ** pipLocation` per the brief. Open/part-reduced legs
have no final exit/pips/result; posted reductions/charges still enter totals.
Missing values stay unknown.

Opening balance + trading P/L + financing + other signed charges + cash adjustments
must equal realised balance. Normalize charges; preserve raw fields and unallocated
account amounts. Count postings once; allocations/cumulative trade totals only
explain/cross-check them. Spread is in fills; unknown money or unexplained differences are errors.

Use [practice totals from Q0](IMPLEMENTATION_PLAN.md#practice-lifecycle); preserve legacy intervals read-only.
Summaries end at reconciled snapshot S: balance, unrealised result, currency/time,
net posted result, positive/negative trading postings and distinct financing/charges/cash.
A +100 close after S appears in activity, excluded from summary profit until a
covering snapshot. Display cutoffs never rewind trade state or change eligibility.
