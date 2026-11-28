# Acceptance checklist

Required scenarios derive from the [accepted brief](../PROJECT_BRIEF.md#acceptance-criteria).
These scenarios guide ongoing verification and future changes. The owner removed
M10 under the [operating decision](../PROJECT_BRIEF.md#delivery-sequence); this is
no longer an outstanding milestone checklist. Use [verification references](VERIFICATION.md) for dated
results and [README commands](../README.md#development-and-verification) to reproduce
focused checks. A linked test is coverage, not proof of live execution.

## Controlled verification

Use real components, temporary notebooks, scripted broker responses and a
controllable clock. Assert ordered requests, committed state and prohibited
requests' absence. Injected observations test orchestration; exact calculation
qualification compares original lab code on identical inputs. Preserve each
scenario/variation's identities, expected/actual outcome and evidence class.

### A01 timing and sessions

Weekday 16:50 New York resolves through March/November DST and skips weekends.
Each stage uses its own partial candle due to close at 17:00 on the run date.
Test captures before/at/after rollover, completed-only and next-session responses;
invalid inputs are unavailable. Record UTC capture/session and master duration.
Calendar calculations do not establish actual dispatch.
Tests: [candles](../tests/test_m03.py), [host/calendar](../tests/test_m09.py).

### A02 fresh events

Test crossings/transitions, continuing states, equality, missing operands and
invalid simultaneous directions. Only a fresh valid C1 event creates entry.
Hold Stage 2 candles/strategy fixed while changing Stage 1 decisions/former direction:
C1/ATR and entry direction must remain identical. Retain operands, rules and trace.
Tests: [selected events](../tests/test_m03_selected.py), [master](../tests/test_m07.py).

### A03 history and ATR

Require exactly the qualified count in both captures and validate completed
history/partial candle, including a short response that still exceeds nominal
warm-up. Wrong configured count fails binding. Compare outputs/current and prior
events/ATR exactly to the selected lab with ties, gaps and initialization cases.
Anchored history must preserve its immutable origin, ignore pre-origin padding,
accumulate the weekday suffix and fail if origin is absent; retain actual counts.
Invalid ATR blocks entry, not a valid exit; later ATR cannot move frozen levels.
Tests: [capture](../tests/test_m03.py), [selected strategy](../tests/test_m03_selected.py),
[Python 02](../tests/test_python02.py), [Python 03](../tests/test_python03.py).
Exact-reference tools and tested datasets: [comparisons](VERIFICATION.md#strategy-comparisons).

### A04 balance boundaries

First run/no trades, confirmed/unconfirmed closures all request one sizing balance
after finished Stage 1. Successful refresh allows other eligible pairs despite an
unresolved pair close; use fixed B with fresh per-set margin. Later balances and
final reporting never overwrite B. Fatal management failure or a failed sizing read prevents
Stage 2 requests. Tests: [master](../tests/test_m07.py).

### A05 sizing and margin

Test long/short, home/quote match and cross currency, differing accountLoss,
accountGain and positionValue, fractional units, tick/min/max/position limits and
margin before set/leg 2. Both directions use returned quote accountLoss; missing,
zero, negative, nonfinite, malformed or ambiguous conversion skips without orders,
including home-matching quote. No fallback. Units are base units rounded down;
executable-distance risk stays within 0.01B per leg. Retain currency/factor/time
and raw/rounded values; margin uses base positionValue and applicable rate source.
Tests: [sizing and entry](../tests/test_m06.py), [preflight](../tests/test_m04.py).

### A06 ordered entry loop

Mix occupied/issue/flat-no-event and eligible long/short pairs across all 28 in
brief order. Blocked pairs make zero pair-specific requests; eligible ones get
fresh captures. Commit current outcome before next pair. An unobserved broker
closure after Stage 1 leaves the locally open pair skipped. Complete entries
need two identified legs with confirmed protection.
Tests: [entry](../tests/test_m06.py), [master](../tests/test_m07.py).

### A07 signal exits

For surviving longs/shorts test opposite C1 only, Exit only, both, one unavailable,
same direction and persistent state. Correct opposite events close all eligible
survivors once; retain both triggers, errors and actual outcomes. Finish each pair
before the next capture. Tests: [management](../tests/test_m05.py).

### A08 entry after C1 close

After a C1 close, test independent Stage 2 long/short/no event, including former
direction. Flat/clear follows only fresh C1. Survivor/unconfirmed close skips
before candles. Record actual close separately from entry decision.
Tests: [master](../tests/test_m07.py).

### A09 entry after other closure

After Exit, TP, SL and mixed broker closures, test either fresh direction or no
event. Former direction/closure cause supplies no entry; no event means no order.
Tests: [master](../tests/test_m07.py).

### A10 TP and stop-to-entry

Test newly discovered/already recorded Trade 1 TP with Trade 2 live, already at
entry, closed before or during change. Only an eligible due stop changes, to its
own exact fill. Repeat next run after rejected/prepared/pending/unknown attempts:
no reissue. Later stop/closure confirmation updates facts but keeps the operator
issue/block until disposition. Closed Trade 2 is never modified.
Tests: [management](../tests/test_m05.py), [disposition/master](../tests/test_m07.py).

### A11 missing legs

Both absent legs with SL/SL, TP/SL, operator or mixed causes require each trade's
closing references/fills. Record individual causes/times/prices; missing evidence
or 404 preserves unresolved state and cannot permit entry.
Tests: [reconciliation](../tests/test_m02.py), [management](../tests/test_m05.py).

### A12 failures and durability

Cover first/second order rejection, target/stop failure, 2xx cancellation/pending,
timeout after accepted order, interruption before send/after fill/after target/
before Trade 2, and SQLite failure after broker action. No mutation replay, repair
or replacement leg. Durable intent and actual fills survive; complete means both
legs/protection established together. Price exit before that point is incomplete;
afterwards it is normal management. Wholly rejected/no-fill releases only when
neither leg opened and no issue remains; Trade 1 fill plus rejected Trade 2 stays
blocked even after closure. A failed stop never suppresses an independent exit.

Duplicate/enriched imports must not duplicate units/money; full interval and
cursor commit together, with conflict/balance/late-charge failures rolling back.
Test source-variant retention, strict unknown fields, numeric equivalence and
qualified conversion disclosures without another debit. Maintenance with an active
service/unpaused timer defers before reads. Disposition needs fresh broker proof;
reconciliation alone cannot clear issues. Interrupt/repeat Q0 commits and
migrations; preserve historical A0 and reject ordinary invocations. Other pairs continue only with
reliable account state/writes, otherwise visibly fail or remain unfinished.
Tests: [M02](../tests/test_m02.py), [M05](../tests/test_m05.py),
[M06](../tests/test_m06.py), [M07](../tests/test_m07.py),
[transaction variants](../tests/test_transaction_import.py), [host](../tests/test_m09.py).

### A13 unavailable markets and missed launches

Untradeable prices/unavailable candles skip with reasons, never queue orders.
A timer inactive across launch does not catch up; next run uses its own session.
Tests: [master](../tests/test_m07.py), [host](../tests/test_m09.py).

### A14 ledger and reporting

Long/short and JPY pips use recorded instrument pip size. Split reductions use
weighted final exit/final close time; open legs have no final outcome. Test gains,
losses, financing, commission, cash transfers, duplicate delivery and allocation
versus posting. Every summary component reconciles to the same snapshot S.
A +100 close after S remains journal-only through failed refresh; the next covering
snapshot includes it once. For historical +100, A0, then +20, practice profit is +120 once;
legacy read-only intervals still return +100 and +20 without changing records. Unknown amounts stay unavailable; signs/colours/currency agree.
Tests: [ledger/import](../tests/test_m02.py), [dashboard](../tests/test_m08.py).

### A15 observation and freshness

Show running/completed/failed/unfinished stages and refreshes, missing snapshots,
missed launches and DST offsets. Counts include only final outcomes; show newer
journal activity separately from snapshot totals. Check journal table/combined
filters, dates, full records/fills, empty/error cases, and on-demand history against
the [presentation contract](ARCHITECTURE.md#notebook-dashboard).
GET views work without credentials; mutation requests cannot write/start trading.
Registry allowlisting, escaping, read-only permissions, consistent transactions and
committed WAL visibility apply during and after writers.
Tests: [dashboard](../tests/test_m08.py), [native fixtures](../tests/test_m09_system.py).

### A16 independent bindings

Two accounts/controllers/notebooks isolate requests, records, locks and reports.
Reject duplicates, unsafe paths, account/currency mismatch and mutation of strategy,
rules/count/history before orders. Original strategy manages its original trades;
a change needs a new combination. Keep Q0/A0/bindings immutable across repeats.
Exclude controller launches throughout maintenance reads/writes; restore each
prior timer state after notebook release, including failure/initially paused cases.
Tests: [bindings](../tests/test_m01.py), [master](../tests/test_m07.py),
[Python 02](../tests/test_python02.py), [Python 03](../tests/test_python03.py).

## Account and execution evidence

Use distinct labels: **offline**, **host** (broker-free actual services),
**practice read-only** (intended-account GETs), **practice execution** (actual orders,
fills and transactions). Simulated failures/research fills are never live evidence.

Read-only preflight verifies intended identity/currency/balance, owner/profile
supplied division/platform, clear or explained existing activity, all 28 instruments,
precision/size/margin inputs, prices/conversions and scheduled partial-candle
availability. `hedgingEnabled` alone does not prove same-direction two-leg support.
MT4/client-extension and division-specific protected-size/FIFO restrictions need
account review; a Trade 2 unit reduction remains unapproved as a fallback.

For A05 retain includeHomeConversions responses and positive finite quote
accountLoss for every required currency. Live matching-quote is required only if
a permitted pair quotes in home currency. Independently require home accountLoss
exactly 1 when home appears as base or quote (EUR from EUR/USD for EUR home, while
USD still sizes that pair). If either case has no permitted pair, record its
specific not-applicable reason; this alone does not block practice setup. Controlled
matching-quote remains mandatory. Missing required factors/non-1 applicable home
factor block preflight. Compare actual broker margin during execution.

When assessing an account's execution path, retain actual long/short/cross-currency
IDs/units/fills, fill-relative protection, TP/scheduled stop-to-entry, targeted
closes, restrictions, daily financing and closure-charge reconciliation. Both-stage
16:50 captures, ordered 28-pair progress/duration and traded dashboard agreement
supplement controlled variations; do not claim every synthetic reversal occurred
live. [The operating checklist](IMPLEMENTATION_PLAN.md#operating-checklist) owns follow-up.

Host proof must include actual dispatch, no restart/replay/overlap, system-user
permissions and maintenance success/failure with both prior timer states. Calendar
or user-manager checks do not substitute for installed system-manager evidence.
Startup/unattended-window evidence follows
[operations](OPERATIONS.md#host-checks-and-unattended-evidence).

Record a scenario as verified only with its controlled checks and applicable
observed evidence; otherwise retain its evidence limits. Profitability is an
experiment outcome, not software acceptance. [Status](STATUS.md) records current
operation, follow-up and the scope of retained observations.
