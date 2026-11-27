# Project status

Updated 27 November 2026 (UTC).

## Current position

**Python 03 is being prepared on `codex/python-03`.** Its intended AUD practice
account passed read-only preflight. The selected Eye Trend Zones / Age Adaptive
Supertrend calculations pass with the authorized fixed-origin weekday history.
The 72-file package and 42 final controller regression checks pass. It is ready
for administrator installation. See [Python 03](#python-03); production remains
unchanged.

**Python 02 is installed from `codex/python-02`.** Its independent controller and
notebook are visible on the production dashboard. The selected DRM/adaptive
BandPass strategy passed the archived comparison, and its AUD practice account
passed read-only preflight. Python 01's records and schedule were preserved.
The initial candle check is scheduled for **28 November 08:50 Melbourne**;
Python 02's Q0 and qualification scheduling remain pending that check and guarded
initialization. See [Python 02](#python-02) for the observed deployment evidence.

The journal's single table, filters, readable labels and two-line dates are
[deployed and verified](#production-journal-deployment) on production port 8879 /
private HTTPS 8443. The live table contains all 12 saved trade records, with
matching account totals, prices, charges, precise timestamps and fills. Trading
code, schedules and dashboard restrictions are unchanged; the deployment did not
start a trading run or contact OANDA.

The earlier [development preview](#development-preview-with-production-data)
remains separate on localhost 8880 without a loaded snapshot or HTTPS 8444.
Its pre-USB snapshot setup command is retired; future development data must follow
[USB worktree guidance](../AGENTS.md#development-worktrees). The production journal
already provides the new layout with real saved records.

The failed GBP-CAD entry is **closed at OANDA, reconciled in the notebook and
resolved by evidenced operator disposition**. The owner completed the protected
recovery at **23 November 21:01 Melbourne / 10:01 UTC**. The actual notebook is
now schema **3**, imported through **2259**, with leg 1 closed by fill `2257`,
leg 2 recorded as never opened and no open issue for the pair. The incomplete
entry, failed run, original attempt, Q0 and existing qualification claims remain
intact; A0 is unset. The [completed recovery and independent verification](#verified-notebook-reconciliation-and-restored-schedule)
retain the receipt, actual host checks, fresh broker response and rendered pages.

At the 23 November recovery verification, Python 01 had **zero open trades, positions or pending orders**, with exact
balance **AUD 50,000.0032**. The notebook separately records the **AUD 43.8956
trading loss**, **AUD 6.2319 financing** and owner's **AUD 50.03 virtual funding**.
The journal shows the actual exit at **1.87819 / -9.7 pips**, no open issues and
one resolved issue. Its retained failed-run label is historical, not an open
broker incident or an unfinished recovery.

The compatible dashboard reader, corrected source and installed package match
the verified 49 application/resource files. Both service identities passed native
package imports, the refreshed essential system/maintenance/dashboard-WAL fixtures
passed, and all fixture units/grants were removed. The **566-test offline suite**
and native permissions reproduction remain separate preparation evidence.
The original transaction-import correction was merged in `5664c32`; the additional
qualified P/L conversion mapping and incident maintenance fixes are now deployed.

**Qualification scheduling is restored**: enabled/active/waiting for the next
regular run at **24 November 08:50 Melbourne / 23 November 21:50 UTC**. The
controller is unmasked and idle with its original failed-run state retained.
Ordinary scheduling remains disabled/inactive; no ordinary activation or trading
run was started by maintenance. **This incident is resolved; M10 remains
incomplete.** Do not rerun the incident deployment or recovery commands.

Both dashboards are **available through Tailscale**. The owner reported working
access after the administrator setup. Verification at **21:39 Melbourne on
20 November** confirms indicator lab HTTPS 443 forwards to local 8878 and practice
HTTPS 8443 forwards to local 8879; both dashboard URLs return HTTP 200. The
[Tailscale access record](#tailscale-access-to-both-dashboards) retains the evidence,
and the [README](../README.md#access-both-dashboards-through-tailscale) owns the
client addresses and setup reference.

The owner authorized [scoped dashboard deployment access](#scoped-dashboard-deployment-access)
for `codexdev`. The corrected one-time setup and the
[Controller wording update](#controller-wording-update) are **installed and deployed**.
The [live verification](#verified-scoped-dashboard-deployment) confirms the exact
no-argument grant, denial of broader commands, successful unchanged-content use by
`codexdev`, all 47 release files, unchanged qualified trading code/restrictions and
schedules, and **12 passing live browser checks**. The **68 focused offline checks**
remain the implementation evidence. Do not rerun the administrator installer;
future reviewed dashboard updates use the restricted command.

The [Controller layout update](#controller-layout-update-on-dashboard-updates),
[Notebooks overview](#notebooks-overview-update) and
[trading journal](#trading-journal-layout-update) are merged into `main` from
`dashboard-updates` and are **deployed on port 8879**. The
[verified dashboard deployment](#verified-dashboard-layout-deployment) passed
live page/navigation checks at 320, 716 and 1280 pixels, with no browser errors
or horizontal overflow. Its 41 focused offline checks and 14 deployment checks
also pass. The separate dashboard release preserves qualified trading code,
notebook records, service restrictions and the automatic qualification schedule.

M10 automatic weekday practice qualification and guarded native ordinary
activation/dispatch are **deployed**. That migration preserved the preceding
dashboard; the independent dashboard release above is now active. The
owner ran the prepared migration from the serveradmin terminal on 20 November;
the [deployment verification](#verified-m10-automatic-qualification-deployment)
confirms its `armed` receipt, updated host-fixture pass and live schedule. The
**427-test baseline** and **460-test isolated M10 suite** retain that migration's
offline verification and 43-file identity. The current 49-file package and
566-test incident correction are verified in the completed recovery above.

The 20 November deployment inspection confirmed automatic qualification was
`enabled/active/waiting` for Monday–Friday at 16:50 New York, then due at
**21 November 08:50 Melbourne / 20 November 16:50 New York**. That run has now
failed as recorded above. The former dated timer was stopped with no next expiry. Ordinary
timer remains `disabled/inactive`, the controller is idle, and the dashboard remains
active on 8879 using the verified separate release. The M10 administrator receipt confirms
Q0 `c245f517b15448cabb2edbb5336a53aa`, cursor `2249` and A0 unset, with all notebook,
sidecar and claim files preserved. These protected notebook observations come from
the deployment receipt; the unprivileged verifier did not reopen the notebook.

The automatic plan keeps the same controller, strategy and 16:50 partial-candle
workflow. It can wait for natural fresh signals and manage actual qualification
trades on later regular runs without daily administrator arming. Durable date
claims preserve the old one-shot's replay protection. The migration archived the
old plan/code, preserved all history, checked current host controls and new dual-timer
maintenance behavior, and enabled only qualification scheduling. Final host/window
checks stay separate from initial execution prerequisites. Startup without login
on -43 and prior essential host/dashboard checks remain retained; a refreshed
current-kernel observer has not been found.

M09 deployment and controlled Python 01 practice execution are already authorized.
No repeat authorization or daily administrator arming is needed for those scopes.
The agent's denied deployment attempt was followed by successful owner execution;
do not repeat the migration.
Actual eligible long/short/cross-currency fills, protection, scheduled stop-to-entry,
targeted closes, margin/restrictions/charges, final integration and final ordinary
authorization remain pending. Ordinary activation and scheduling have **not** been
performed. **M10 is not complete.**

M09's implementation is approved for deployment and broker-free verification,
with remaining final host acceptance dependencies and new-version deployment checks. Access to Ubuntu
`thinkbook-server` is confirmed. Its
broker-free user-systemd dispatch and maintenance checks passed. Administrator
installation completed. System controller/maintenance and dashboard sandbox/WAL
fixture checks now have observed passes; remaining host acceptance and actual
account execution requirements stay open. The
[M09 record](#m09-host-operation-and-maintenance-exclusion) separates these results;
user-scope probes do not qualify the system deployment.

M08's prior offline suite passed 294 tests, including 30 dashboard checks. The
[M08 verification record](#m08-observational-dashboard) retains rendered GET
pages, committed fixture rows, package checks and visual review. No broker
request was made for M08, no actual notebook was initialized or activated,
and no trading timer was enabled. That M08 work enabled no live mutations.

M04 is complete and ready for owner review. The
[account and live candle passes](#m04-read-only-preflight) passed for Python 01
with the owner-confirmed OANDA Australia Pty Ltd division. All 28 permitted
pairs returned the qualified 386-candle window at weekday 16:50 New York.
The report was absent at the earlier M05–M07 handoffs and became available
after the scheduled capture.

M03 implementation and [offline strategy qualification](#m03-selected-strategy-qualification)
are complete and ready for owner review. Python 01 is bound to the selected
STD-Adaptive T3 Channel C1 and L2 Ehlers Bandpass Filter Exit with 386 daily
candles, including the partial candle.
M02 is ready for owner review. All 37 [M01](#m01-offline-foundation) and
[M02](#m02-offline-broker-reconciliation-and-ledger) checks passed again.

The owner approved the ten-milestone [implementation plan](IMPLEMENTATION_PLAN.md)
on 16 November 2026 after the three review fixes. Its verification distinguishes
offline checks, host operation, read-only account preflight and actual OANDA
practice execution. Each milestone is requested in a new chat.

All three plan findings are addressed: the no-fill exception now applies only
when neither expected leg opened and no issue remains; qualification initialization
and its transition to ordinary activation are assigned to M01/M02/M07 with
controlled checks; and the initial account-path check can proceed after the
required trading and service controls without waiting for the dashboard. Final
integration qualification and ordinary activation still require the completed
dashboard, host checks and acceptance evidence. These are approved planning
refinements, not evidence of implementation or a change to the trading rules.

The owner approved the [detailed design](DETAILED_DESIGN.md) on 16 November 2026. It
preserves the approved [numbered workflow and architecture](ARCHITECTURE.md)
and the brief's trading rules. It covers controller responsibilities,
configuration and activation, SQLite records and commit boundaries, broker
requests and reconciliation, failure handling, the read-only dashboard and
controlled test setups for every acceptance scenario A01–A16.

The four review fixes are incorporated: guard stop changes against earlier
failed/unresolved attempts, require the exact qualified candle window, exclude
scheduled launches throughout notebook maintenance, and align dashboard summary
totals with the displayed balance snapshot. The state table now owns retry and
entry-block decisions; finished/skip/failure counts derive from recorded pair
outcomes. The affected acceptance cases describe the corresponding checks.

Risk sizing now consistently uses the quote currency's returned OANDA
`accountLoss`, including when quote and home currency match. Missing or invalid
factors skip the entry without a fallback. The architecture and design agree;
margin continues to use `positionValue`. A05 retains the controlled matching-quote
test for every configuration. Its live equivalent is required only when a
permitted pair quotes in the account's home currency. The live check that the
home-currency factor is 1 can use a base or quote conversion entry. Cases excluded
by the permitted pair list are recorded as not applicable with a reason;
missing/invalid required conversion entries still prevent activation. The
account-specific conversion evidence is recorded in [M04](#m04-read-only-preflight).

The proposed two-leg order path remains conditional on verification of the
intended OANDA practice account. The selected strategy and lookback have
offline evidence. Actual two-leg execution and charge mapping remain pending.

| Stage | State |
| --- | --- |
| Project brief | Final, version 1 |
| Project guidance and supporting documents | Established |
| Architecture and OANDA integration | Approved workflow and agreed refinements documented. Partial read-only account evidence recorded in M04 |
| Detailed design | Approved by the owner on 16 November 2026. Account execution qualification remains open |
| Implementation plan | Approved by the owner on 16 November 2026 after all three review findings were addressed |
| M01 configuration, notebook and controlled-check foundation | Implemented and offline checks passed. Ready for review |
| M02 read-only broker access, reconciliation and ledger | Implemented and offline checks passed. Ready for review |
| M03 candle validation and selected strategy qualification | Complete offline. Selected conversions match the archived result and 386 candles are qualified. Ready for owner review |
| M04 intended practice-account read-only preflight | Complete. Offline checks, intended-account GETs and live qualified candle coverage passed. Ready for owner review |
| M05 Manage Open Trades | Implemented. All 102 offline checks passed, including 40 M05 checks. Ready for owner review |
| M06 sizing and candidate two-leg entry | Implemented. All 171 offline tests passed, including 69 M06 checks. Ready for owner review |
| M07 master workflow, entry loop and operator disposition | Implemented offline. All 264 baseline tests passed again before M08 |
| M08 observational dashboard | Implemented offline. All 294 tests passed, including 30 M08 checks. Ready for owner review |
| M09 host operation and maintenance exclusion | Startup, refreshed essential system/maintenance controls and dashboard isolation/WAL passed on -43; actual dashboard/notebook and LAN agreement passed. Prior -42 scheduled-window unattended context remains unconfirmed; keep kernel/window scopes separate. Ordinary timer disabled |
| M10 practice qualification and ordinary activation | GBP-CAD incident resolved: schema-3 notebook reconciled through 2259, actual close/funding imported and issue resolved. Reader/package and affected host checks verified; qualification schedule restored. Ordinary remains disabled and A0 unset; full execution qualification remains pending |

## Transaction import failure on 21 November

The owner requested investigation and a diagnosis branch after run
`m10-auto-bfeea7da7de9-20261120` failed at **21 November 08:50 Melbourne /
20 November 16:50 New York**. Service inspection confirms exit status 2. The
dashboard records 15 no-entry pairs followed by failed GBP-CAD (16 of 28 checked).
The management stage and sizing refresh succeeded before entry; the master
stopped on the history failure without obtaining a final reporting snapshot.

**Observed broker evidence.** The administrator's
[read-only export](../var/verification/m10-automatic-collections/collection-c100b2e47ec0/progress.json)
and retained responses confirm order `2250`, short fill/trade `2251` for
**42,665 units at 1.87722**, and on-fill stop `2252` at **1.88824**, all in batch
`2250`. The order response contains the create/fill bodies and references the
stop through boundary `2252`; history supplies its actual body. No target or
Trade 2 request was sent. The notebook retained the first fill but rolled back
the history import, so it shows no confirmed stop and cursor `2249`. Historical
stop creation is confirmed; these retained responses do not establish its
current broker status after the failed run.

**Cause and correction.** History adds four zero-valued conversion-cost fields
to fill `2251` and one to its `tradeOpened` object. Every other field matches the
saved response exactly. The strict body comparison raised
`Imported broker transaction changed` before stop `2252` could be imported.
The initial correction allowed the five observed zero-valued omissions. The
owner then agreed to broaden it beyond this one response shape. The
[reconciliation contract](DETAILED_DESIGN.md#reconciliation-procedure) owns the
replacement field-aware policy: exact numeric equivalence at known paths,
compatible supplemental metadata and supported fees, and closed-trade lists
matched by ID. Identity, core facts, unknown differences, invalid values and
unqualified nonzero conversion costs remain failures. Diagnostic evidence names
the transaction and field paths. No signal, sizing, entry sequence or automatic
repair rule changed.

**Broader correction.** Accepted source variants are retained separately from
the cumulative transaction facts used for projections. A later supported charge
is posted once only before that transaction's history interval is complete,
with broker balance evidence and reconciliation; it cannot silently alter an
already imported account balance. Later per-trade allocations remain informational
and must agree with the corresponding transaction totals when complete.
Sparse echoes never remove previously accepted facts or fees. Compatible duplicate
bodies within a response/history batch receive the same policy and retain their
individual sources. Schema 3 adds the evidence table and atomically seeds it from
existing transaction rows; interrupted migration rolls back. Updated readers
support schemas 2 and 3, and qualification review digests/collector exports include
the response variants.

**Collector correction.** The original administrator collector failed its
all-file hash comparison and left its partial export protected. A root-owned
SQLite read-only connection can change the source SHM read marks; that failed
collector did not retain per-file hash results, so the exact original difference
cannot be established. The corrected collector reads a temporary DB/WAL copy
under exclusion, preserves failure exports for inspection, and distinguishes
database/WAL changes from SHM changes. Its four focused checks pass, including
retained uncheckpointed WAL after the last writer exits. The owner ran the
corrected collector successfully; **all three real source files were unchanged**.
The frozen migration bundle was preserved.

**Verification.** The initial narrow patch's
[505-test log](../var/verification/transaction-import-20261121/full-suite.log)
and [replay](../var/verification/transaction-import-20261121/replay-result.json)
remain historical evidence. The broader version passes **520 offline tests** in
the [new full suite](../var/verification/transaction-import-broader-20261121/full-suite.log).
Its 15 additional cases cover decimal equivalence, opening/reducing/closing
fills, reordered closed trades, retained metadata, new supported fees, balance
failure rollback, rejection of late charges and absent balance evidence,
informational allocations and contradictory allocation totals, core conflicts,
and interrupted/repeated schema migration. Retained observations also pass the
existing credential-redaction check.
The existing two-leg entry test still completes with history-enriched fills and
stop bodies absent from mutation responses. Collector checks still pass.

The [new exact-evidence replay](../var/verification/transaction-import-broader-20261121/replay-result.json)
reproduces the old failure, replays schema migration, then imports through `2252`
and records stop **1.88824**. Four source observations retain all original bodies
and the enriched fill; cumulative facts gain the zero-cost fields. Fills, ledger,
attempts and issues remain unchanged. The incomplete set and open issue remain
blocked. This is an in-memory offline import using retained responses, with no
broker requests or actual notebook writes. The
[wheel verification](../var/verification/transaction-import-broader-20261121/package-verification.json)
matches all **49 application/resource files** and passes isolated import, schema
creation and numeric comparison checks. The backend build succeeded without
downloads after the environment's pip/build front ends were unavailable.

**Operational outcome.** The [completed incident recovery](#verified-notebook-reconciliation-and-restored-schedule)
installed and verified the compatible reader/package, preserved notebook/Q0/claims
and the original backups, passed affected host checks, reconciled actual broker
history and resolved the specific issue through normal operator disposition.
The protected code identity is refreshed and the original qualification schedule
restored. Preserve all failure and backup evidence; do not rerun the initial
installer, automatic migration or any incident recovery, replay the failed run or
complete Trade 2. Comprehensive M10 execution qualification and final ordinary
authority remain separate pending work. The field-aware import fix grants no
automatic repair or strategy change.

**Merge and owner-requested exit.** The owner approved merging the broader fix
and closing the failed entry's remaining trade. Commit `5664c32` is fast-forwarded
into local `main` and pushed to `origin/main`. The pre-existing Tailscale document
edits remain uncommitted and were not included. All 49 verified application/resource
files still match the 520-test verification. No runtime deployment occurred.

The incident-only [administrator close command](../tests/close_failed_gbpcad_2251.py)
is pinned to the investigated account fingerprint and trade `2251`. It checks the
fresh account and original trade identity, excludes controller launches using the
existing dual-timer maintenance boundary, and durably records an attempt before
sending the [OANDA trade-specific close](https://developer.oanda.com/rest-live-v20/trade-ep/).
It sends `ALL` only for this remaining short trade. It retains redacted replies,
verifies the closed trade against its closing fill, and restores prior timer state.
Already-closed trades require only reads; subsequent invocations never submit a
second request, including after a rejection, interruption or lost response.
The command does not open/migrate/write the notebook or clear its issue.

The [15 offline operator-close checks](../var/verification/operator-close-2251/preparation/tests.log)
pass, including the native practice transport with mocked network replies.
The command also imports with the installed interpreter/package. The attempted
administrator invocation was denied by the host's existing `codexdev` sudo policy;
**no broker request was sent and closure is not confirmed**. The owner has been
asked to run the prepared command from the `serveradmin` terminal:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/close_failed_gbpcad_2251.py
```

Its printed output identifies a private, owner-readable result/evidence export.
Protected attempt evidence stays under the deployed data directory. After the
earlier publication block, the owner requested committing and pushing the
completed changes on 21 November. The requested publication includes the incident
helper, its offline tests and this investigation record. Raw broker responses and
private connection settings remain outside version control.

**Administrator attempt and helper correction.** The owner ran the initial
command. Its [saved result](../var/verification/operator-close-2251/inspection-43da4997d82e/result.json)
reports `inspection_required` / `ConfigurationError`, with no request or response
artifacts. The installed settings loader requires its caller's real UID to own
the private `.env`; loading as root fails that check for the service-owned file.
The initial helper's offline tests did not exercise that administrator boundary.
No broker request or notebook change was performed by this failed configuration
load, and the trade's current broker state remains unconfirmed.

The corrected command retains the same invocation above. The administrator
launches a temporary root-owned helper copy as `nnfx-run`, matching the existing
deployment tools. That worker loads its own private configuration and performs
maintenance/broker operations; the administrator only exports the redacted
result. Credential ownership and permissions stay unchanged. Errors now identify
the failing phase without copying private exception text. The
[21 offline checks](../var/verification/operator-close-2251/worker-identity-fix/tests.log)
include the real owner-only settings check followed by a simulated close under
the matching identity, sealed-copy launch/cleanup, timeout handling, and the
previous rejection/uncertainty/no-duplicate cases. The installed-interpreter
entry point also rejects the wrong service identity before loading credentials.
All 49 application/resource files remain identical to the merged fix's verification.
These offline checks make no broker requests.

**Corrected administrator execution: API unavailable.** The owner ran the
corrected command at **21 November 10:26 Melbourne / 20 November 23:26 UTC**.
Its [result and retained account response](../var/verification/operator-close-2251/inspection-00bac9af84b6/result.json)
show `inspection_required` / `BrokerError` at `account_close`. The sole request
was `GET /summary`, which returned **HTTP 520**, no OANDA request ID and no JSON
body. No close attempt claim or mutation was created. The trade's current state,
protection and closure could not be verified; the notebook and issue are unchanged.

An independent, unauthenticated `GET /v3/accounts` from the same host at
23:27:10 UTC also returned 520, with Cloudflare's plain-text `error code: 520`
response and ray `a5db3943fcaea768-SYD`. The
[probe and verification](../var/verification/operator-close-2251/api-unavailable-20261121/verification.json)
retain these observations. Cloudflare's
[520 definition](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-520/)
identifies an empty or unexpected origin-server response. This establishes an
API availability failure from this host; its exact cause, geographic extent and
recovery time are not established. The public OANDA maintenance notice found
concerned 7 November and does not explain this event.

Read-only systemd inspection confirms the controller is loaded/unmasked, retains
its prior failed-run state and has no pending job. Ordinary scheduling remains
disabled/inactive. Automatic qualification is enabled/active/waiting, next due
**24 November 08:50 Melbourne / 23 November 21:50 UTC**. Maintenance restored the
normal schedule. The authorized close requires fresh broker reads once the API
responds normally. Coordinated fix deployment and evidence-backed notebook
disposition remain pending; preserve the actual fill/exit history.

**520 investigation and public-path recovery.** Further investigation at the
owner's request confirms that the deployed broker module and checkout module
are byte-identical. The retained failed-run capture contains **23 successful
HTTP responses** (22 HTTP 200, one HTTP 201), including two successful
`GET /summary` requests at 21:50 UTC. The run's import/comparison error was local
and distinct from the later HTTP 520 account-read failure.

At **21 November 01:19:21 UTC / 12:19 Melbourne**, two independent public probes
from the same host received JSON **HTTP 401**, each with an OANDA `RequestID`.
This is the [expected response to omitted authentication](https://developer.oanda.com/rest-live-v20/troubleshooting-errors/),
not a test of the real token. Python used TLS 1.3/HTTP 1.1 and curl used HTTP 2,
reaching the two normally resolved Cloudflare addresses. Certificate validation
passed and no proxy environment was configured. The plain-text 520 was no
longer reproduced; the market was still closed. The
[investigation evidence](../var/verification/oanda-520-investigation-20261121/investigation.json)
retains timing, response headers, Cloudflare rays, TLS results, source hashes
and the earlier successful-summary comparison.

These observations support a **transient OANDA/Cloudflare API-path failure**.
They do not identify the precise upstream cause or demonstrate continuous
unavailability between observations. The published 7 November maintenance
notice is unrelated; a separate European CFD crypto notice for 21 November
08:00–11:00 UTC has a different scope and time. Weekend maintenance remains
unconfirmed. OANDA's [Australian trading hours](https://www.oanda.com/au-en/trading/hours-of-operation/)
prevent executing the exit while the market is closed; the next scheduled FX
open is **23 November 09:05 Melbourne / 22 November 22:05 UTC**.

The local incident helper now supports `--inspect-only`. This mode supplies no
native mutation guard and reads account/trade evidence without a close attempt,
notebook change or issue disposition. HTTP read failures now expose their status
and endpoint without private exception text. All **24 focused offline checks**
pass, including propagation of the read-only option through the administrator
worker and rejection of any close attempt in that mode. The installed-interpreter
entry point rejects the wrong service identity before credential access. The
owner has been asked to run the read-only inspection because the protected
credentials still require the trading service identity:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/close_failed_gbpcad_2251.py --inspect-only
```

Public routing recovery did not establish authenticated account recovery or the
trade's current state. No additional close request, deployment or publication
was performed by this investigation.

**Authenticated inspection: maintenance explicitly confirmed.** The owner ran
`--inspect-only`. At **21 November 12:27:13 Melbourne / 01:27:13 UTC**, the sole
new request was `GET /summary`. OANDA returned **HTTP 503**, request ID `0`, and
`{"errorMessage":"System under maintenance, please try again later."}`. The
[authenticated verification](../var/verification/oanda-520-investigation-20261121/authenticated-maintenance.json)
and [saved inspection](../var/verification/operator-close-2251/inspection-4dce795296cb/result.json)
retain the response and hashes. The response log is cumulative: its two earlier
520 request/response records are preserved alongside the two new 503 records.
No close claim or mutation was created, and no trade GET was reached. The
notebook and issue remain unchanged.

This directly confirms **maintenance blocking authenticated account access**,
even though public requests already reached the authentication service. It makes
maintenance a likely explanation for the earlier 520, without proving that both
responses have the same upstream cause. At this inspection, fresh account/trade
verification remained blocked. The authorized exit still requires current broker
state and an open market; it has not been executed or queued.

**Publication verification.** The combined offline suite passes **544 tests** in
[the final publication log](../var/verification/publish-investigation-20261121/full-suite.log),
including all 24 operator-helper checks and the 520-test reconciliation baseline.
All 49 application/resource files retain their previously verified hashes; this
follow-up publishes the operator tool, tests and investigation record without a
runtime deployment, notebook migration or broker mutation.

**22 November maintenance recheck: authenticated access recovered.** At
**22 November 19:49:31 Melbourne / 08:49:31 UTC**, a native read-only practice
`GET /summary` returned **HTTP 200**, request ID `61573386244581878`. The local
private binding matched the investigated account fingerprint, and the broker
reader verified the returned account identity and currency. The preceding public
unauthenticated request returned the expected JSON HTTP 401 with an OANDA
request ID. The [retained check](../var/verification/oanda-maintenance-recheck-20261122/probe-084931.json)
records both results without credentials or account figures. An earlier restricted
connection could not resolve the hostname; that local failure is not evidence of
an OANDA outage. This establishes account-read recovery at the observed time,
not uninterrupted availability or order execution capability. No trade read,
broker mutation, notebook write, issue disposition or scheduling change occurred;
the failed entry's current protection and closure remain unverified.

**22 November requested close: market closed.** Following the owner's renewed
request to close the failed GBP-CAD entry, the
[fresh account, trade and pricing reads](../var/verification/operator-close-2251/preclose-20261122T085302Z/read-only.json)
all returned HTTP 200 at **22 November 19:53 Melbourne / 08:53 UTC**. The account
fingerprint and original trade identity were checked against the incident helper.
Trade `2251` remains `OPEN`, with `currentUnits=-42665`; its stop-loss order
`2252` is `PENDING` at `1.88824`. GBP-CAD pricing reports
`status=non-tradeable` and `tradeable=false`, with its last quote from
20 November 21:59 UTC. OANDA's current
[Australian trading hours](https://www.oanda.com/au-en/trading/hours-of-operation/)
confirm that existing positions cannot be closed outside market hours and FX
reopens Sunday 17:05 New York, next **23 November 09:05 Melbourne /
22 November 22:05 UTC**. No close was sent or queued, no attempt claim was created,
and no notebook, issue, service or schedule changed. The authorized close remains
pending fresh broker verification when the market is tradeable.

**23 November requested cleanup: market open, administrator access required.**
The owner renewed the request to close the failed entry. At **10:50 Melbourne /
22 November 23:50 UTC**, the
[fresh read-only verification](../var/verification/operator-close-2251/preclose-20261122T235029Z/read-only.json)
returned HTTP 200 for the bound Python 01 account summary, original trade,
GBP-CAD pricing and stop order. The account fingerprint and original fill
identity match the incident helper. Trade `2251` is still `OPEN` for
`-42665` units; stop `2252` remains `PENDING` at `1.88824`. Current pricing
reports `status=tradeable` and `tradeable=true`.

The exact prepared close command was attempted with non-interactive sudo and
denied by the server's existing `codexdev` sudo policy before the helper started.
The sudo grant permits only the restricted dashboard deployment command. This
was an operating-system access denial, not an automatic approval-review rejection.
No broker mutation, notebook write, issue disposition or service/timer change
occurred. Read-only systemd inspection confirms the controller remains failed
with no pending job, ordinary scheduling is disabled/inactive, and automatic
qualification is enabled/active/waiting for **24 November 08:50 Melbourne /
23 November 21:50 UTC**.

All **24 focused offline operator-close checks** pass again. The administrator
command above remains ready to close only this trade, retain its actual fill and
restore prior scheduling. Its fresh identity checks and durable claim prevent
duplicate close submissions. Closure still requires administrator execution and
broker confirmation; notebook reconciliation and issue disposition remain pending.

**23 November administrator close: broker cleanup confirmed.** The owner ran
the prepared command and requested verification. The
[retained administrator result and responses](../var/verification/operator-close-2251/inspection-427a561ed3e3/result.json)
show one durably claimed `PUT /trades/2251/close` at **11:04:13 Melbourne /
00:04:13 UTC**. OANDA returned HTTP 200 with close order `2256`, fill `2257`
and linked stop cancellation `2258`. The helper then reported
`inspection_required` because its post-close `GET /trades/2251` returned
HTTP 404 / `NO_SUCH_TRADE`; this was a verification lookup failure after the
confirmed fill, not a rejected close. The durable attempt claim remains and
prevents a second close submission. Do not remove or reset it.

The [independent read-only verification](../var/verification/operator-close-2251/postclose-20261123T000525Z/verification.json)
at **11:05 Melbourne / 00:05 UTC** checked the intended account fingerprint and
fresh broker transactions. Fill `2257` has reason `MARKET_ORDER_TRADE_CLOSE`
and closes exactly trade `2251` for all **42,665 units at 1.87819**. Against
the original short entry at `1.87722`, this is **-9.7 pips** and **AUD -43.8956**
trading P/L; the fill posts zero additional financing or commission. Previously
posted financing remains separate. Cancellation `2258` names stop order `2252`
with reason `LINKED_TRADE_CLOSED`.

The fresh full account response through `2258` confirms **zero open trades,
zero open positions, zero pending orders and zero unrealised P/L**, with balance
**AUD 49,949.9732**. The trade-detail endpoint still returns 404; closure is
established by the matching closing transaction and account state together.
Read-only systemd inspection confirms the helper restored the prior schedule:
the controller is loaded, failed and idle with no pending job; ordinary scheduling
is disabled/inactive, and automatic qualification is enabled/active/waiting,
next due **24 November 08:50 Melbourne / 23 November 21:50 UTC**.

No additional broker mutation, notebook write, schema migration, issue disposition
or trading-fix deployment was performed during verification. The open-position
cleanup is complete at OANDA. The notebook and dashboard still require the
coordinated reader/controller deployment, reconciliation and evidence-backed
operator disposition already recorded above; M10 remains incomplete.

## Notebook reconciliation for the closed GBP-CAD trade

On 23 November the owner requested reconciliation and resolution of the closed
GBP-CAD issue, then reported adding AUD 50.03 of virtual funds. Native read-only
[account and history responses](../var/verification/operator-close-2251/history-20261123T001051Z.json)
at **11:10 Melbourne / 00:10 UTC** confirm transaction `2259` is `TRANSFER_FUNDS`
for `50.0300000000`, with current balance **AUD 50,000.0032**. Transactions
`2253`–`2255` retain the actual financing, and `2256`–`2258` retain the operator
close and stop cancellation. No broker mutation or notebook write was made by
these reads. Funding is a cash adjustment, not a trading gain.

**Additional accounting qualification.** The first offline rehearsal correctly
blocked history fill `2257`: its P/L conversion disclosures are nonzero
(`-0.42844810179192`), unlike the earlier zero-only entry evidence. The existing
merged fix did not qualify this shape. The [reconciliation policy](DETAILED_DESIGN.md#reconciliation-procedure)
now qualifies matching single-close P/L conversion disclosures with zero other
conversion components, numeric equality, valid account balance and matching
per-trade realised P/L. Retain these amounts without a second ledger debit.
[OANDA Australia's settlement-rate explanation](https://help.oanda.com/au/en/faqs/home-currency-conversion.htm)
includes the conversion fee in the rate applied to P/L; the actual broker balance
movement independently confirms `49993.8688 - 43.8956 = 49949.9732` for this
account. Other nonzero conversion shapes remain blocked. Four focused regression
checks cover retention, numeric/sparse echoes, invalid or inconsistent shapes,
no double posting and unexplained-balance rollback. Strategy and order rules
are unchanged.

**Verified offline result.** The [exact-evidence rehearsal](../var/verification/operator-reconcile-2251/replay-result.json)
reconstructs the exported schema-2 notebook in a temporary fixture, migrates it,
and runs the normal `record_disposition` against the fresh retained account and
history. It imports through `2259`, closes leg 1 at `1.87819` through fill `2257`,
records leg 2 as never opened, releases the set reservation and resolves the
specific incomplete-entry issue. The original failure evidence, incomplete set,
failed run, committed entry attempt and Q0 remain intact. Repeating the normal
disposition adds neither broker reads nor postings. This is an offline rehearsal,
not a write to the real notebook or proof of deployed reconciliation.

| Qualification account component | Exact AUD amount |
| --- | ---: |
| Original Q0 balance, retained | 50000.1007 |
| Realised trading loss | -43.8956 |
| Financing | -6.2319 |
| Added virtual funding, separately recorded | +50.0300000000 |
| Reconciled balance through `2259` | 50000.0032 |

The [full offline suite](../var/verification/operator-reconcile-2251/full-suite.log)
passes **555 tests**. The final [seven operator checks](../var/verification/operator-reconcile-2251/operation-tests.log)
also pass, including administrative ordering and a host-fixture failure that
withholds the actual notebook write and leaves controller launches excluded.
The [frozen preparation](../var/verification/operator-reconcile-2251/preparation.json)
records all 49 source/package hashes, isolated schema-3 package import and the
verified wheel. The incident-only [maintenance helper](../deploy/reconcile_gbpcad.py)
backs up notebook/WAL/SHM and prior code/plan, deploys the compatible reader
before any schema migration, updates the importer/package and dashboard
deployment fingerprints, reruns affected broker-free host fixtures, and runs
the normal GET-only disposition as `nnfx-run`. It preserves Q0, all prior
claims/captures, failed-run history, automatic run prefix, authority and schedule;
ordinary activation remains unset. Success restores the prior timer states.
Failure after exclusion retains the archive and leaves timers stopped with the
controller masked for inspection; do not rerun blindly or roll back schema-3 data
to the older writer.

**Initial administrator handoff, retained as history.** The exact non-interactive command
was denied by the existing `codexdev` sudo policy before the helper started.
This was an operating-system access denial, not an automatic approval-review
rejection. The owner subsequently ran the following command. **Do not rerun it**;
its completed steps and retained failure require the continuation below:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/gbpcad-reconciliation-20261123/deploy/reconcile_gbpcad.py
```

### Administrator attempt and verified continuation

At **23 November 13:46:56 Melbourne / 02:46:56 UTC**, the owner's administrator
execution [retained this failure result](../var/prepared/gbpcad-reconciliation-20261123/var/verification/gbpcad-reconcile-1c86fd008419/result.json):
`inspection_required`, phase `compatible_reader_deployed`, error type
`RuntimeError`. It created the original protected backup/archive, deployed
`dashboard-schema3-5c8d7916787e3c60`, and copied all 49 verified source files.
The notebook disposition worker and later host-fixture stage were not reached.
The original receipt and frozen package remain unchanged.

**Cause and current checkpoint.** Preparation renamed the valid distribution
wheel to `package.whl`. Pip rejects that name before installation; a native
read-only dry run reproduces `Invalid wheel filename (wrong number of parts)`.
The prior tests mocked pip and missed its filename contract. Read-only inspection
confirms corrected source identity
`752b8c10867eddd687c3909678da935bc23b13a5f9cd8f6fb6c08c42e8daeb8e`, but the
installed package still has its original schema-2 identity `e8eba7f1...`. The
deployed reader's `notebook.py` matches the verified compatible source. The
dashboard is active; the notebook has not been migrated/reconciled. Both timers
are inactive, ordinary remains disabled, qualification remains enabled, and the
controller is idle/failed and runtime-masked with no pending job. The failure
left the documented exclusion in place and did not submit a broker mutation.

**Corrected preparation.** The incident helper now rejects an invalid distribution
filename before any live changes and retains package/fixture step output in its
protected archive. The separate
[continuation](../deploy/continue_gbpcad_reconciliation.py) accepts only the exact
retained failure receipt and pre-write notebook checkpoint. It verifies the old
package identity, unchanged original plan, backup DB/WAL bytes, notebook rows,
completed reader release and service restrictions before installing the same
wheel under its original valid filename. It uses a new evidence archive and
preserves the prior backup and failure receipt. It then resumes the already
verified host checks, normal GET-only disposition and original schedule
restoration; it does not repeat the reader deployment or original migration.

The [full updated suite](../var/verification/operator-reconcile-2251/continuation-full-suite.log)
passes **559 offline tests**. Its 11 operator checks include initial and
continuation ordering, preserved reader/old receipt, invalid-wheel refusal,
checkpoint mismatch refusal and exclusion after a host-fixture failure. The
[native pip dry run](../var/verification/operator-reconcile-2251/wheel-filename-verification.json)
accepts `nnfx_practice-0.1.0-py3-none-any.whl` with the unchanged wheel hash
`bb7ed3dd41cd821284c7207688e451c9190a90f8f72969b1bc0cafc8ef3805e0` and performs
no installation. The [new frozen preparation](../var/verification/operator-reconcile-2251/continuation-preparation.json)
binds the exact original receipt, source/package and continuation hashes. The
financial mapping and offline reconciliation result above are unchanged.

The agent's continuation invocation was also denied by `codexdev`'s existing
sudo policy before it started. This is a server access limitation, not an
automatic approval-review rejection. From the `serveradmin` terminal, run:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/gbpcad-reconciliation-continuation-20261123/deploy/continue_gbpcad_reconciliation.py
```

Allow a few minutes for broker-free system checks. Require its exported
`status: reconciled_and_resolved`, then verify the live notebook, dashboard and
restored schedules. The printed result is owner-readable beneath the new frozen
directory's `var/verification`; original backups and detailed read evidence stay
protected. That continuation was subsequently executed and stopped as recorded
below. **Do not rerun it.**

### Permissions repair before notebook reconciliation

The owner ran the continuation at **23 November 19:38 Melbourne / 08:38 UTC**.
Its [saved result](../var/prepared/gbpcad-reconciliation-continuation-20261123/var/verification/gbpcad-continue-6a8d0b04c443/result.json)
reports `inspection_required` at `checking_host_controls`. Package installation
completed and all **49 installed/source hashes** matched, but the first synthetic
writer (`initialize`) failed before fixture units were installed. The owner
exported the [command output](../var/verification/operator-reconcile-2251/host-fixture-command.json)
and [full fixture report](../var/verification/operator-reconcile-2251/controller-controls.json).
The report confirms `actual_notebook_files_preserved=true`, `cleanup_errors=[]`,
zero remaining fixture unit files and no broker requests. No notebook migration,
disposition worker or protected plan update occurred.

**Observed permission defect.** The incident administrator used `umask 077` for
private evidence. Pip and the fixture stager inherited it when creating public
code directories. Inspection confirms mode `700` on both installed application
package directories and the staged fixture-worker directory. An unprivileged
isolated import cannot read the installed package. This is a deployment-helper
defect, separate from the broker transaction comparison. The compatible dashboard
reader continues to run. Both timers remain inactive, qualification is still
enabled and ordinary disabled, and the controller is idle/failed and runtime-masked.

The [native temporary-install reproduction](../var/verification/operator-reconcile-2251/permissions-native-replay.json)
installs the same wheel into a disposable target with umask 077 and reproduces
the mode-700 directories. The scoped repair restores public directories to 755
and files to 644, preserving all 49 application hashes and touching no actual
installed package or notebook during this replay. Production repair checks all
49 application hashes and every targeted path's ownership, type, link count and
expected mode before changing permissions. It covers only this wheel's two application packages and
distribution metadata. Credentials, notebook files, dependencies and the Python
runtime are excluded. Future pip installation explicitly uses child umask 022;
private parent evidence retains 077. Fixture worker staging explicitly sets its
public directory mode and copied script modes.

The [final recovery entry point](../deploy/finish_gbpcad_reconciliation.py) is
pinned to this exact second failure receipt and its verified cleanup/preservation
report. It retains both prior archives and the original DB/WAL backup, checks
that the actual notebook still matches, repairs only the installed public-code
permissions, and verifies isolated imports as **both `nnfx-run` and `nnfx-view`**.
It performs no package reinstall or reader redeployment. It then repeats the
affected host fixtures with the corrected staging boundary and uses the same
GET-only, evidence-backed disposition and schedule restoration. Known package/
fixture diagnostics are now automatically exported with the result for owner review;
private worker reads remain protected. A partial diagnostic file does not prevent
the result export.

The [566-test full suite](../var/verification/operator-reconcile-2251/permissions-full-suite.log)
and [36 focused checks](../var/verification/operator-reconcile-2251/permissions-focused.log)
pass. New cases exercise real subprocess umask inheritance, staging under private
umask, bounded/idempotent permission repair, rejection before any chmod when an
unexpected link appears, automatic safe diagnostic export, and both successful
and deferred recovery without reinstalling the package or replacing the reader.
The [frozen recovery manifest](../var/verification/operator-reconcile-2251/permissions-preparation.json)
binds the unchanged application/wheel, exact second failure report and both
backup receipts to the verified operator/fixture sources. The source identity
remains `752b8c10...`; accounting behavior and the offline financial result above
are unchanged.

The owner executed the following new frozen recovery from the `serveradmin`
terminal. It is retained as history; **do not rerun it**:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/gbpcad-reconciliation-permissions-20261123/deploy/finish_gbpcad_reconciliation.py
```

The recovery returned `status: reconciled_and_resolved`. Its completed live
verification is recorded below; the preceding paused state is historical.

### Verified notebook reconciliation and restored schedule

The owner ran the final recovery at **23 November 21:00 Melbourne / 10:00 UTC**.
Its [successful administrator receipt](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/result.json)
records completed reconciliation at **21:01:29 Melbourne / 10:01:29 UTC**, with
`status: reconciled_and_resolved`, no broker mutation and no ordinary activation.
The recovery repaired **98 public package paths** without touching private files,
reinstalling the wheel or replacing the already-compatible reader. Both
[writer](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/service-import-nnfx-run.json)
and [viewer](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/service-import-nnfx-view.json)
imports confirmed schema 3 and the exact installed code identity `752b8c10...`.

**Actual host verification passed.** The
[fresh system-manager fixture report](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/controller-controls.json)
confirms the dedicated writer dispatch, no automatic restart, missed-run/no-catch-up
behavior, independent-controller overlap/active-run deferral, maintenance success
and failure with active/paused timers, both-schedule exclusion and restoration,
and separate dashboard identity, sandbox and committed WAL visibility. The clock
is synchronized. All 49 installed/source file hashes match. Notebook files were
unchanged throughout these broker-free fixtures. `fixture_checks_passed=true`,
`error=null`, `cleanup_errors=[]` and zero fixture unit files remain. These are
refreshed essential checks on the current boot/kernel, not completion of the
separate intended-window/startup or all M10 acceptance requirements.

**Actual notebook disposition committed.** Native practice account/history GETs
produced snapshot `7ced09da601d454296df0d4ea5df98b5` through **2259**. Schema 3
retains original transaction observations and reconciles the complete interval.
The registered leg for trade `2251` is closed at **1.87819** through fill `2257`,
with reason `MARKET_ORDER_TRADE_CLOSE`. Leg 2 has no broker ID and remains
`not_opened`; the disposition proof explicitly records `unsent_legs=[2]`.
The set remains historically incomplete, now terminal, and GBP-CAD is available
for a future independently eligible entry. The specific issue is `resolved`,
with operator `owner-via-codex`, the owner's explanation and matching closing
evidence. The original issue body, failed runs/stages/decisions, confirmed entry
attempt and Q0 snapshot are preserved; existing claims/captures are byte-identical.
No failed run was resumed, second leg opened or closing request repeated.

The committed qualification report matches the exact financial breakdown above:
**AUD 50,000.0032 balance**, **-43.8956 trading loss**, **-6.2319 financing**,
**+50.0300000000 cash adjustment**, zero commission/other charges/unrealised P/L
and **-0.0975000000 net change from the original AUD 50,000.1007 Q0**. Conversion
disclosures are retained without an extra debit. The funding is not a trading
gain. Q0 `c245f517b15448cabb2edbb5336a53aa` is unchanged and A0 remains unset.

**Independent completion check at 21:05 Melbourne / 10:05 UTC.** The
[fresh native OANDA account read, live page checks and systemd states](../var/verification/operator-reconcile-2251/completed-20261123T100526Z/verification.json)
confirm balance `50000.0032`, boundary `2259`, zero open trades/positions/pending
orders and zero unrealised P/L. Controller, Notebooks and journal GETs all return
HTTP 200 with no unavailable-notebook error. Notebooks and journal display the
reconciled balance; Controller and journal show **No open issues** and **Resolved
issues (1)**. The journal displays the actual exit, pips, loss, financing and cash
adjustment, with the incomplete-entry and failed-run history retained. This
verification made no broker mutation or notebook write.

The controller is loaded/unmasked and idle/failed with no pending job. The
qualification timer is **enabled/active/waiting**, next due **24 November 08:50
Melbourne / 23 November 21:50 UTC**; ordinary is **disabled/inactive**. The
dashboard remains active on its existing release and port 8879. Both prior failure
archives and the original backup remain protected and preserved. **The GBP-CAD
cleanup and notebook issue resolution are complete. M10 remains incomplete and
ordinary trading remains unauthorized/unactivated.**

## Journal trade table and filters

On 25 November 2026 (UTC), the owner requested one table with filters and all
trade records in the journal at `/notebooks/notebook-a`, on a new branch. The
change is on `journal-trades-table` and applies to every notebook's shared
journal template. The [brief](../PROJECT_BRIEF.md#notebook-and-observational-dashboard)
owns the accepted presentation requirement, and the
[design](DETAILED_DESIGN.md) describes the display and read-only filter contracts.

The table defaults to every recorded leg, including open, closed, confirmed not
opened and unconfirmed/planned records. Newest sets appear first with their legs
adjacent. Its 22 columns include entry/exit records, units, protection, signed
pips, trading result, separate charges, period, entry status and broker/set IDs.
Search and pair/status/direction/period/entry-date filters combine through GET
requests. Dates use inclusive New York days; invalid ranges/choices show an
error. Matching/total counts and a clear link make the current view explicit.
Filters leave account summary totals at their original reconciled boundary.
Each row links to its full record and fills below the table, keeping active
filters. The wider journal has one scroll region with pinned pair/leg identity
and column headings. No JavaScript or new runtime dependency was added.

The [74 focused offline checks](../var/verification/journal-all-records-20261125/checks.log)
pass: the 45 M08 checks, M09 retained-WAL reader and 28 dashboard deployment
boundary checks. New controlled cases cover combined filters, every status,
search, empty results, New York date boundaries in standard/daylight time,
validation, preserved totals, escaping and notebook-bound record selection.
The [browser checks](../var/verification/journal-all-records-20261125/browser-checks.json)
pass at 320, 390, 716, 1280 and 1600 pixels against temporary synthetic notebooks.
All 34 sample records appear in one table with 22 columns. Actual filter submit,
reset, no matches, unconfirmed records, record/fill navigation, preserved filters,
empty notebooks, keyboard scrolling and pinned identity/headings pass with no
page-level horizontal overflow or browser errors. The
[desktop table](../var/verification/journal-all-records-20261125/trades-1280.png)
and [filtered phone view](../var/verification/journal-all-records-20261125/filtered-390.png)
were visually reviewed.

These are local layout checks, separate from actual OANDA practice execution.
Merge and deployment remain pending; the installed dashboard, notebook records
and trading operation have not been changed by this work.

### Journal wording review

On 25 November 2026 (UTC), the owner requested a human-readability review of the
journal's headings and content. The same branch now uses consistent labels such
as Pair / trade, Entry price, Profit / loss and Trading phase. The guide explains
paired trade sets, phase boundaries, units, final results, stop changes and
missing values. Filter notes state the New York date rules and that account
totals are independent of the table filters. Strategy is now a section-level
heading, and Hide trade details avoids suggesting that the link closes a trade.

Open trades show Not closed yet in final-result fields; confirmed unopened legs
show Not applicable, unconfirmed states remain explicit and missing amounts show
Not recorded. Zero still displays as zero. Closed stops are labelled inactive.
Readable stop statuses and exit reasons replace raw codes in the table; full
record/fill details retain the original broker codes and identifiers. Search
accepts both the displayed exit reason and its broker code. Account activity now
distinguishes account postings from trade breakdowns, and broker request copy
keeps prepared/requested outcomes separate from broker confirmation. Account
reporting/configuration labels explain the identifiers and activation records.

The [74 focused checks](../var/verification/journal-wording-20261125/checks.log)
pass after the wording changes, retaining the accounting, filter, read-only and
deployment-boundary checks. The
[final browser checks](../var/verification/journal-wording-20261125/browser-checks.json)
pass at 320, 390, 716, 1280 and 1600 pixels with synthetic notebooks. They cover
headings, contextual open-trade values, the guide, readable and original reason
codes, expanded details, filters and navigation, with no page overflow or browser
errors. The [revised table](../var/verification/journal-wording-20261125/trades-1280.png)
and [phone trade details](../var/verification/journal-wording-20261125/record-390.png)
were visually reviewed. These supersede the earlier preview captions above.
This is local display verification; merge/deployment remain pending and no
broker operation or notebook-data change was performed.

### Development preview with production data

On 25 November 2026 (UTC), the owner requested a development version using current
production data. The frozen
[preview package](../var/previews/journal-development-20261125/source-manifest.json)
combines the active dashboard's qualified runtime with this branch's dashboard
files. The two schema/transaction resources absent from the deployed reader-only
bundle were copied from the installed qualified runtime for a complete 49-file
package. All 49 source identities are retained. Production code was not changed.

The [preview launcher](../var/previews/journal-development-20261125/run_preview.py)
runs as `codexdev` in the enabled, non-transient user service
`nnfx-practice-dev.service`, listening only on localhost 8880. The existing user
manager has lingering enabled. `NoNewPrivileges=yes`, `UMask=0077` and the
`connect` syscall denial are active. The service uses only its private snapshot;
it cannot read the protected production notebook under `codexdev`'s current
permissions. Its development banner will show when the copy was captured.

**Historical preparation; snapshot setup not executed.** The production notebook is readable by
`nnfx-view` / `nnfx-read`; `codexdev` has neither that access nor a general sudo
grant. The prepared
[one-time setup helper](../var/previews/journal-development-20261125/load_production_snapshot.py)
was prepared for a serveradmin invocation. Its internal-storage setup is now
retired under the [USB policy](../AGENTS.md#development-worktrees); the
[README](../README.md#development-journal-preview) records the disposition. The
retained helper exports only notebook-a
using SQLite backup after dropping to the existing reader identity, verifies that
the reader cannot write the source, and copies no `.env` or credentials. It
installs the private snapshot as `codexdev`, verifies readiness and adds only the
private HTTPS 8444 forward. It checks the existing 443/8443 routes and refuses
an occupied preview endpoint or an existing snapshot. No production/trading
service, timer or notebook permission is changed by the helper.

The [46 frozen-package checks](../var/verification/journal-development-20261125/frozen-checks.log)
pass. The [controlled export/preview check](../var/verification/journal-development-20261125/offline-checks.json)
also passes: committed WAL rows survive backup, source DB/WAL/SHM hashes stay
unchanged, credentials are absent from the export, filters and fills work, and
mutation requests are rejected. These are synthetic fixture results.
The [host preparation record](../var/verification/journal-development-20261125/host-preparation.json)
confirms the real development service is active/enabled and waiting for its
production snapshot. Production `/notebooks/notebook-a` returns HTTP 200; its
service PID remains `526722` and both existing Tailscale routes are unchanged.
No actual production snapshot has been copied, HTTPS 8444 is not configured yet,
and the preview deliberately returns HTTP 503 while awaiting setup. Actual-data
rendering and private HTTPS verification remain pending after owner execution.
The journal branch remains unmerged and production deployment is pending.

### Readable trade dates

On 26 November 2026 (UTC), the owner requested clearer entry date/time text before
loading the production snapshot. Entry and exit cells now show a readable date,
such as `25 Nov 2026`, above the time, such as `16:50:11 EST -0500`. The existing
New York formatter supplies the timezone and UTC offset. Fractional seconds are
omitted from the visible table text; the complete original timestamp remains in
the HTML time element, the exact New York tooltip and the expanded trade record.
The date columns are narrower and each date/time line stays together.

The [74 focused source checks](../var/verification/journal-dates-20261126/checks.log)
pass, including the existing New York date-boundary cases extended to inspect
the visible date/time in standard and daylight time. The
[browser checks](../var/verification/journal-dates-20261126/browser-checks.json)
pass at 320, 390, 716, 1280 and 1600 pixels with a Melbourne browser timezone.
They verify the two-line display, compact column width, exact timestamp
attributes/details and consistent entry/exit formatting, alongside the existing
filters and navigation checks. There are no browser errors or page overflow.
The [updated table](../var/verification/journal-dates-20261126/trades-1280.png)
was visually reviewed. These checks use synthetic notebooks.

The [49-file development package](../var/verification/journal-dates-20261126/development-package.json)
was refreshed with the two template/style files, and its
[46 focused checks](../var/verification/journal-dates-20261126/frozen-checks.log)
pass. Only `nnfx-practice-dev.service` was restarted. The production dashboard
remains active with PID `526722`; loading production data and adding HTTPS 8444
are still pending. The administrator setup helper is unchanged, so the previously
provided command remains valid.

### Journal merge to main

On 26 November 2026 (UTC), the owner approved committing, merging and pushing the
reviewed journal changes. Commit `581a57f` contains the single trade table,
read-only filters, readable labels and dates, controlled dashboard checks and
their owning documentation. It was fast-forward merged from
`journal-trades-table` into `main` after confirming that local and remote main
shared the same base.

The committed runtime files match the source hashes retained by the passing
[74 source checks and browser review](#readable-trade-dates); the updated frozen
development package also retains its 46 passing checks. All 27 added local
documentation links were checked against the staged content and `AGENTS.md`
remains within its 300-line limit. The pre-existing Tailscale documentation edits
were preserved separately from the journal commit. The
[repository verification](../var/verification/journal-merge-20261126/integration.json)
retains the commit and remote-reference results.

Repository integration does not deploy the dashboard. Production deployment and
the development preview's administrator snapshot/HTTPS setup remain separate.

### Production journal deployment

On 26 November 2026 (UTC), the owner authorized production deployment of the
merged journal. Preparation and all new verification data used the mounted USB
worktree at `/mnt/nnfx-usb/development/worktrees/nnfx-practice-lab/deploy-journal-20261126`.
The deployment used the existing no-argument, allowlisted helper for `codexdev`.
It restarted only the dashboard outside the trading window with the controller
idle. The ordinary timer remains disabled/inactive; qualification remains
enabled/active for 26 November 21:50 UTC.

The initial six-file release applied the merged table, filters, wording and dates.
Live review then exposed a display edge case: closing a trade clears active
protection fields, so a historical planned target was labelled unconfirmed.
Commit `52fe994` corrects that presentation. Closed protection is
inactive and historical plans stay visible; open/unconfirmed targets retain
their warnings. No broker state or recorded price was changed.

The final release is `dashboard-deploy-47c54274a23e09eee665c3f0`, receipt
`/var/lib/nnfx-dashboard-deploy/20261126T121104461876.json`. The
[host verification](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/final-host-verification.json) confirms all 47
release files, all 49 unchanged qualified trading files, unchanged trading
controls, service restrictions, helper and deployment configuration. The process
is active as `nnfx-view:nnfx-read`, PID `1097787`, on the existing port 8879.
Existing Tailscale routes are retained.

The [74 focused checks](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/checks.log) pass on the USB worktree. The
[three targeted protection checks](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/protection-checks.log) pass after
the correction, including a new regression case for cleared protection fields
and preserved warnings on open targets. The
[saved production-data comparison](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/live-data-checks.json) checks all
12 trade records, account totals, IDs, prices, units, charges, closed results,
precise entry/exit times and every recorded fill against the pre-deployment UI.
The [live browser checks](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/browser-checks.json) pass at 320, 390, 716
and 1280 pixels: one table with 22 columns, readable New York times, filters,
clear/no-match states, details/fills, keyboard scrolling and navigation. Expanded
records fit without page overflow or browser errors. Private HTTPS 8443 returns
200 with normal certificate validation; the verifier maps the hostname to the
existing tailnet IP to accommodate this host's local DNS behavior. The
[desktop table](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/journal-live-1280.png) and
[phone trade details](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126/trade-details-live-390.png) were visually reviewed.

Chromium's first launch exceeded Unix socket path limits in the deeply nested
USB temporary directory. Browser working files therefore used the task-specific
short USB path `/mnt/nnfx-usb/development/tmp/jp26`; captures and other artifacts
were retained on USB and archived during the cleanup below. Internal storage
was not used as a fallback.

On 26 November 2026, repository cleanup removed the merged
`deploy-journal-20261126` worktree and the merged local branches
`deploy-journal-20261126` and `journal-trades-table`. Only the main checkout and
local `main` branch remain. All 191 worktree data/artifact files were moved to
`/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var`,
with matching contents and metadata verified before removal. The evidence links
above now use that archive; the [cleanup record](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/cleanup-record.json)
retains the file hashes and removed branch commits.

These are production deployment and saved-data display checks. No broker request,
notebook write, strategy change or trading-control change was performed. M10
execution qualification and ordinary activation retain their existing scope and
remaining requirements. The earlier internal-storage development snapshot setup
was never executed and is retired; production can be viewed at the normal URL.

## Tailscale access to both dashboards

On 20 November 2026, the owner requested access to both the indicator lab and
practice dashboards through the current Tailscale setup. The active Serve
configuration has HTTPS 443 at `thinkbook-server.tail57730c.ts.net` forwarding
`/` to `http://127.0.0.1:8878`. HTTPS 8443 on the same hostname forwards `/` to
`http://127.0.0.1:8879`. The
[README](../README.md#access-both-dashboards-through-tailscale) owns the command
and client addresses.

**Initial attempt at 18:49 Melbourne.** Direct configuration returned
`Access denied: serve config denied`; the exact non-interactive sudo attempt was
also denied for `codexdev`. A subsequent `tailscale serve status --json` matched
the captured pre-change configuration, with only the existing 443 endpoint.
No 8443 endpoint was installed by that attempt. The existing indicator HTTPS endpoint returned
HTTP 200 with normal certificate validation and an explicit DNS-to-Tailscale-IP
mapping (`100.106.59.99`); this host's ordinary lookup of its MagicDNS hostname
failed. The practice LAN `/controllers` page also returned HTTP 200.

The [verification summary](../var/verification/tailscale-dashboards-20261120/verification.json)
and [original Serve configuration](../var/verification/tailscale-dashboards-20261120/serve-before.json)
retain that initial result.

**Completed and verified at 21:39 Melbourne.** After the phone-key and
administrator setup instructions, the owner reported that access was working.
Read-only `tailscale serve status --json` confirms both HTTPS forwards above,
with the original 443 route preserved. Indicator lab `/` and practice
`/controllers` both return HTTP 200 over HTTPS with normal certificate validation.
These local requests use an explicit hostname-to-Tailscale-IP mapping because of
the earlier local MagicDNS lookup failure; client access is owner-reported.
Additional remote browser/navigation checks were not performed for this setup.
The [completion summary](../var/verification/tailscale-dashboards-20261120/completion.json)
and [active Serve configuration](../var/verification/tailscale-dashboards-20261120/serve-active.json)
retain the observed result. No application deployment, trading run, broker request
or timer change was performed for this access work.

## Controller wording update

On 20 November 2026 (Melbourne), the owner requested replacing “skipped” and
reviewing the rest of the Controller page for unclear language. Entry summaries
now say “28 / 28 pairs checked” and “28 with no entry · 0 failed”, retaining the
recorded reason. Open-trade skips say “exit check(s) unavailable”; they do not imply
a successful hold decision. Empty management stages say “No open trades to manage”
without a zero-only outcome line. Account reconciliation, saved-record notices,
account freshness, missing run types, unfinished checks and operator-response
messages use clearer language. Issue headings use readable words while the exact
codes remain in details. Shared freshness/issue/header/footer wording also appears
on the Notebooks pages; trading rules, stored records and lifecycle are unchanged.

All **40 focused dashboard checks** pass in the checkout and against the exact
staged release using the installed Python environment. Existing mixed-outcome
coverage now also checks unavailable exit inputs, retained reasons and exclusion
of unfinished decisions. The [fixture browser review](../var/verification/controller-wording-20261120/browser-checks.json)
passed **21 checks** across seven healthy/error/history states at 320, 716 and 1280
pixels, with no browser errors or horizontal overflow when details are collapsed
or expanded. Keyboard access to full run records passes. The
[716-pixel preview](../var/verification/controller-wording-20261120/controller-716.png)
was visually reviewed. These are offline fixture checks, not broker execution.

The [prepared release](../var/prepared/dashboard-wording-20261120/verification.json)
changes only four templates relative to the verified live dashboard. All other
release files and the qualified trading installation match their prior hashes.
Its **16 offline deployment checks** pass, including upgrade/rollback, changed
previous-release/override rejection, security preservation, active-controller
refusal and trading-window deferral. The helper switches only the dashboard
working directory, restores the preceding override if verification fails, and
retains notebook/plan/control preservation checks. The original deployment
bundle is unchanged.

At preparation, read-only host inspection confirmed the dashboard active from
`/opt/nnfx-dashboard/dashboard-a7d756b-7a3d198f3e7e`, PID `37415`.
`sudo -n -l` then confirmed `codexdev` could not run sudo on this host. This was a host access
limitation, not an automatic approval-review rejection. No installation, restart,
trading run, timer change or broker request was attempted. The
[serveradmin installation command](../README.md#deploy-the-controller-wording-update)
was prepared. The later [scoped deployment verification](#verified-scoped-dashboard-deployment)
confirms successful installation of the wording update through the new helper.

## Scoped dashboard deployment access

On 20 November 2026 (Melbourne), the owner authorized scoping and implementing
a dashboard deployment command for `codexdev`, retaining the restricted dashboard
account. The [authority contract](DETAILED_DESIGN.md#dashboard-deployment-authority)
is implemented in the [fixed helper](../deploy/dashboard_deploy.py),
[administrator installer](../deploy/install_dashboard_deployer.py) and
[unprivileged request preparation](../deploy/prepare_dashboard_update.py).
The approved scope is dashboard releases and that service's restart, with no
generic sudo, trading controls, credentials, notebook writes or strategy changes.

The [68 focused checks](../var/verification/dashboard-delegation-20261120/checks.log)
pass: 28 deployment-boundary/setup checks plus the 40 dashboard checks. They cover
submitted Python remaining inert in the privileged helper, isolated interpreter
environment, rejected non-dashboard/path/duplicate/oversized submissions, stale
updates, protected-file checks, concurrent-deployment exclusion, trading-window
and active-run deferral, successive updates, failed-page/restart rollback and
explicit failed-rollback receipts. Installer failures withhold or revoke the grant
and restore the preceding override. These use controlled files/services; they do
not establish that the live sudo grant is installed. The host's `visudo-rs 0.2.13`
accepted the exact rule, and its installed manual confirms that the empty argument
string limits the command to no arguments.

The [frozen setup bundle](../var/prepared/dashboard-delegation-20261120/verification.json)
contains the verified helper, installer, service definition and a stdin request
for the four pending wording templates. Read-only host preflight confirmed the
active preceding dashboard release, all 47 protected release files, the unchanged
service definition, successful GETs for all three pages, an idle controller and
execution outside the trading window. No privileged mutation was attempted.

**Administrator installation is complete**, verified below. The
[one-time command](../README.md#enable-scoped-dashboard-deployment) installed the
fixed helper and exact sudo rule, then applied the wording update through
the same restricted helper. The earlier standalone wording installer is retained
as preparation history. Routine later updates use the new command as `codexdev`;
no repeat administrator handoff is needed for that scope.

### Dashboard deployment setup retry

The owner's first administrator invocation stopped in the trading-path ownership
preflight, before creating the helper, configuration, sudo grant or active-release
link and before any service changes. Read-only inspection identified exactly two
root-owned, root-group directories with mode `0775`:
`/opt/nnfx-practice/nnfx_practice` and `/opt/nnfx-practice/strategies`.
The original preflight had verified the separate dashboard release but omitted
these qualified-code parent-directory permissions.

Installer revision 2 validates all qualified-code files and directories before
any setup changes. It plans only these exact root:root `0775` to `0755` directory
changes and applies them after other preflight checks and sudo-rule validation.
It does not rewrite application files, alter ownership or touch notebooks/plans.
Other owners/groups, wider modes, links and writable descendants remain refused.
If a later setup step fails, the reduced directory permissions are retained; the
existing service rollback and permission-grant cleanup still apply. The installed
runtime helper and its strict ownership checks are unchanged.

All 68 focused checks pass, including the observed directory case, unchanged code
hashes and rejection of unrelated permission problems. The
[corrected host preflight](../var/verification/dashboard-delegation-20261120/retry-preflight.json)
confirms all 43 qualified application files match the previously verified hashes,
all other code-path metadata passes, the setup components are absent and the live
dashboard remains at PID `37415` on the preceding release. All three dashboard GETs
pass; trading controls remain unchanged. These inspections made no host changes.

The original installer/manifest and checks are retained in
[attempt-1](../var/prepared/dashboard-delegation-20261120/attempt-1/verification.json).
The updated bundle uses the **same administrator command and helper hash**.
The owner subsequently completed the retry; the resulting installation,
directory tightening, sudo grant and wording deployment are verified below.

### Verified scoped dashboard deployment

On **20 November 2026, 16:46 Melbourne**, verification after the owner's retry
confirmed successful installation. Receipt `20261120T054512457591.json` reports
`deployed`, from the previous layout release to
`dashboard-deploy-ae8979eace31f5a55da8c313`. The
[verification record](../var/verification/dashboard-delegation-deployed-20261120/verification.json)
retains its hash, exact template hashes, service settings and permission results.
All 47 release files match the preceding release plus the four prepared templates;
all 43 pinned qualified application files are unchanged. The installed helper
matches its reviewed hash, is root-owned, and both package directories are now
root:root `0755`.

The dashboard is active as `nnfx-view:nnfx-read`, PID `42854`, with working directory
`/opt/nnfx-dashboard/current`. Its restrictions match the pre-installation settings.
Six sudo permission-listing checks confirm only the exact no-argument helper is
allowed; helper arguments, direct Python/shell execution, dashboard restart and
trading-service start commands are denied. An actual `codexdev` invocation with
the current release identity and identical file contents succeeded without a new
receipt, release switch or dashboard restart. This confirms usable deployment
access without making another update.

The controller remains inactive, ordinary scheduling disabled/inactive, and
qualification scheduling enabled/active for the same next expiry,
**21 November 08:50 Melbourne / 20 November 16:50 New York**. No trading control
changed. The [live browser checks](../var/verification/dashboard-delegation-deployed-20261120/browser-checks.json)
passed the Controller, Notebooks, journal and current-run details at 320, 716 and
1280 pixels, with no errors or horizontal overflow before/after expanding details.
The Controller visibly shows “28 / 28 pairs checked”, “28 with no entry · 0 failed”
and its recorded reason. Verification used dashboard GETs, host/file reads and the
unchanged-content helper invocation; it did not access broker credentials, place
orders, change notebook data or restart services. These are deployment checks,
not additional OANDA execution evidence. The one-time installation is complete.

## Verification and limits

- **GitHub publication preparation, 20 November 2026 (Melbourne).** The combined
  checkout passed all 470 offline tests with `.venv/bin/python -m unittest discover -v`.
  The local log is `var/verification/github-publication/unittest.log`. A credential
  pattern scan of the 106 tracked files and 126 historical file versions found no
  matches. Private configuration, runtime records and the virtual environment are
  ignored and absent from Git history. All 397 local document file links resolve
  in this checkout; 227 point to private artifacts that remain local. `AGENTS.md`
  is 103 lines, within its 300-line limit. These are publication/offline checks,
  not additional deployment or broker execution evidence.
- **Source inspection.** Inspected the sibling indicator lab at commit
  `15e9a5beafe3c219eece80b6e7ebc35d236a00a4` for ATR, fresh signals,
  two-leg exit sequencing and server-rendered dashboard patterns. This inspection
  preceded strategy selection and numerical equivalence checks.
- **ATR history check.** Exercised the lab ATR calculation on a synthetic gap
  with only the fixed assessment length changed for the short windows. Fourteen
  completed bars plus the current bar matched the full history ATR. Fourteen
  total bars lost the previous close for the oldest true range and gave a
  different result.
- **Offline calendar check.** `systemd-analyze calendar` on the proposed host
  resolved the New York 16:50 timer to 21:50 UTC on Friday 6 March 2026 and
  20:50 UTC on Monday 9 March, then to 20:50 UTC on Friday 30 October and
  21:50 UTC on Monday 2 November. Both checks skipped the weekend. Timer
  installation and dispatch remain untested.
- **Broker documentation.** Reviewed current official OANDA API and FIFO
  documentation. The [integration section](ARCHITECTURE.md#integration-evidence-and-review-items)
  records the capabilities, account-dependent constraints and required checks.
  The [M04 run](#m04-read-only-preflight) records subsequent account
  authentication and data verification. Trading behaviour remains unverified.
- **Initial detailed-design checks.** Checked the initial draft against the brief,
  approved workflow and all 16 acceptance scenarios; its 43 local links across
  seven project documents passed, and `AGENTS.md` was 101 lines (limit 300).
  Checked navigation and draft approval status. Re-inspected the lab's
  ATR and signal helpers and checked the official OANDA account, trade,
  order, pricing and transaction definitions used in the design. These are
  source/document checks, not calculation-equivalence or execution tests.
- **Review revision.** Applied the four review fixes and both simplifications.
  Extended A03, A10, A12 and A14–A16 in the design with exact-window, next-run
  retry, maintenance-exclusion, reporting-boundary and derived-count checks.
  Rechecked consistency with the approved workflow and trading rules. All 46
  local links/anchors across seven project documents pass; all 16 acceptance
  scenarios remain mapped, and `AGENTS.md` remains 101 lines (limit 300).
  These scenarios are specified, not executed.
- **Risk conversion revision.** Aligned the design and architecture on returned
  `accountLoss` for every quote currency. Extended A05 to cover field selection,
  missing/invalid factors even for home-matching quotes, retained sizing evidence
  and the required practice-account preflight responses. The 1% per-leg budget,
  fixed sizing balance and margin rules are unchanged. Consistency and approval
  status checked; all 46 local links/anchors across seven documents pass, all
  16 acceptance scenarios remain mapped, and `AGENTS.md` is 101 lines (limit 300).
  These are documentation checks; the practice-account check and application
  scenarios remain unexecuted.
- **Verification applicability correction.** Aligned the design and architecture
  so an account is not blocked merely because no permitted pair quotes in its
  home currency. The EUR-account case uses the EUR conversion entry from
  EUR/USD to verify the factor of 1 while retaining USD for that pair's risk
  sizing. If the home currency appears in no permitted pair, that live identity
  check is also recorded as not applicable. Required conversion failures still
  prevent activation, and the controlled matching-quote test is retained.
  Checked applicability against the approved pair list for USD, EUR and a home
  currency absent from the list. The controlled A05 row is unchanged; all 16
  acceptance scenarios remain mapped, all 46 local links/anchors pass, and
  `AGENTS.md` remains 101 lines (limit 300). Consistency and review
  status checked. These are documentation checks; no practice check has been
  executed, and implementation planning had not yet started at that point.
- **Detailed-design approval.** The owner approved the revised design on
  16 November 2026 after the verification-applicability review. Approval covers
  the documented design and retains the pending strategy/lookback and
  practice-account qualification requirements. At that point implementation
  planning was deferred to a separate chat; the planning update below records
  its subsequent start.
- **Implementation planning.** Drafted ten ordered milestones with dependencies,
  exit checks and a mapping for every scenario A01–A16. Checked consistency with
  the brief, approved workflow, detailed-design state rules and review fixes.
  Kept strategy/lookback selection pending and two-leg execution conditional on
  intended-account qualification; separated offline, host, practice read-only
  and practice execution evidence. All 59 local links/anchors across eight
  documents pass; all 16 scenarios are mapped, all ten milestones identify
  dependencies and verification, and `AGENTS.md` is 103 lines (limit 300).
  Navigation and approval status are updated. These are documentation checks
  only: the plan awaits review, no runtime work or broker requests were performed,
  and no application scenario has been executed.
- **Implementation-plan review revision.** Addressed all three findings. Narrowed
  the no-fill exception to a wholly rejected set with neither leg opened and no
  open issue. Assigned qualification initialization/reporting and the atomic
  activation transition to M01/M02/M07, preserving one immutable binding and all
  history while separating the Q0 qualification and A0 ordinary reporting periods.
  Added controlled A12/A14/A16 transition checks and an explicit incomplete-set
  counterexample. Split M10 into initial account-path and final integration checks;
  initial execution requires the trading components and verified controller
  service controls, but not the dashboard. Rechecked dependencies, state rules,
  snapshot accounting and acceptance coverage against the approved design and
  checklist. All 61 local links/anchors across eight documents pass; A01–A16 remain
  mapped, all ten milestones retain dependencies and verification, and `AGENTS.md`
  remains 103 lines (limit 300). The brief, architecture, approved design and
  acceptance checklist are unchanged. The revised plan awaits review; these are
  documentation checks only, with no runtime implementation, application test
  execution or broker requests.
- **Implementation-plan approval and handover.** The owner approved the revised
  plan on 16 November 2026 and chose one requested milestone per new chat, with
  status updated and work stopped for review at each boundary. M01 is the first
  handover. Strategy/lookback selection and account qualification remain pending;
  approval is not broker execution evidence or authority to place orders in this
  planning chat. Approval status and navigation are consistent; all 62 local
  links/anchors across eight documents pass and `AGENTS.md` remains 103 lines.
  No implementation has started.
## M01 offline foundation

On 16 November 2026, `python3 -m unittest discover -v` passed all 16 checks with
Python 3.14.4 and SQLite 3.46.1. Inputs and assertions are in the
[controlled fixtures](../tests/support.py) and [M01 test suite](../tests/test_m01.py).
The fixture registry uses `controller-a` and `controller-b`, each with its own
notebook and account. The `fixture-v1` manifest with 50 candles is synthetic.
Its SHA-256 is `a2ccb86d63053fb221f46f6a45b92842617a9196c796e1cf5708e3cd86f36e38`.
The implementation and test sources were identified by SHA-256
`4ebdfff859ed183b0713b563fae1dd081b3f15c4383bd7c2442ca8ba39054a94`, using the
sorted package and test `.py` paths plus `nnfx_practice/schema.sql`, each path
followed by a NUL byte and the file contents.

| Scenario | Offline result |
| --- | --- |
| A12 | Passed. Failed commits left no reservation, planned legs or prepared attempt from the failed write. For `run-a` and `set-a`, the committed reservation retained both planned legs and blocked a second set for EUR-USD. An open leg or issue kept the pair blocked after the set was marked terminal in the controlled setup. Attempt `attempt-1` remained `prepared` on reopening after interruption before send. At the scripted send boundary, a separate reader saw the prepared record and the writer held no transaction. Duplicate client IDs were rejected. Fixture tokens, authorization headers and private account data were absent from tested attempt evidence and log output. |
| A15 | Passed. A read-only connection without `.env` saw three finished decisions, including one skip and one failure. It excluded the unfinished fourth decision, observed committed WAL updates and rejected writes. The unfinished master and both child rows were retained, with the Stage 2 expected count of 28. |
| A16 | Passed. Duplicate controller, notebook and account IDs, unsafe paths, insecure private-file permissions, changed account/currency/strategy rules/count and an unqualified count were rejected. Two separate notebook files retained independent run history. A missing second manifest left the first binding usable. Token rotation and display-name changes reopened the original binding. Unknown schemas preserved existing data. A synthetic qualification baseline `q0` at boundary `0010` retained its cursor, decimal text and nanosecond timestamp on reopening while ordinary activation fields stayed unset. |

Schema version 1 uses SQLite's `user_version`. Reopening retains records and
unsupported versions are rejected before writes. Future schema changes require an
explicit migration. The offline wheel build included the schema. All 66 local
links and anchors across eight documents passed, and `AGENTS.md` has 103 lines.
M01 adds storage for qualification and activation. The
initialization and activation operations and their interruption checks remain
assigned to M07. Full [acceptance](ACCEPTANCE.md), host verification and actual
practice-account evidence remain pending. No OANDA requests were made in M01.

## M02 offline broker reconciliation and ledger

On 17 November 2026, `python3 -m unittest tests.test_m01 -v` passed all 16
regression checks and `python3 -m unittest tests.test_m02 -v` passed all 21
M02 checks on Python 3.14.4 and SQLite 3.46.1. The M01 source digest matches
the recorded baseline. Schema version 1 already had the records M02 needed.
The combined source SHA-256 is
`0ad242c383ae0f0e02b6f622ed928cd2ac04cd796dbc504f1f87e1afd367fd54`,
using the same sorted-path procedure as M01. The broker-shaped fixtures and
assertions are in the [M02 suite](../tests/test_m02.py).

| Scenario | Offline result |
| --- | --- |
| A11 | Passed. Separate take-profit and stop-loss fills closed the two registered legs with their own broker order IDs, prices, causes and nanosecond times. A trade and stop lookup returning 404 preserved the missing leg's last confirmed units and opened an issue. A closing transaction referenced by both targeted reads was stored once. |
| A12 | Passed. Mocked HTTPS calls reused the pinned practice connection and applied connect/read timeouts. A three-page sparse interval committed both transaction IDs once. Missing boundaries, incomplete pages, conflicting duplicates and omissions of previously observed or confirmed IDs left the cursor at the prior boundary. Commit interruption before and after the write checked transactions, fills, ledger and cursor together. An older snapshot preserved newer close and stop facts. An interrupted entry was linked by exact broker evidence and remained blocked as an incomplete set. |
| A14 | Passed. Actual per-trade fixture prices produced +98 pips after weighted EUR-USD reductions and −3 pips on the USD-JPY short. Posted gains, losses, financing, commission, other charges and cash transfers reconciled separately. An open leg had no final exit. After a failed refresh the +100 close remained in the journal and joined the account summary only at the next covering snapshot. Unexplained transaction and snapshot balances recorded failures and preserved the last successful report. Qualification retained +100 at A0. Ordinary reporting opened at 1100 and posted the subsequent +20 once, closing at 1120. |
| A16 | Passed. Two independently bound notebooks retained separate request paths, currencies, cursors and ledger activity. A wrong notebook binding failed before the read. Wrong broker account, currency and transaction account were rejected. Stored evidence omitted fixture credentials and private account identifiers. Unexpected trades and orders blocked their pairs, and activity with no identifiable pair failed the snapshot. |

The [broker client](../nnfx_practice/broker.py) supports the approved GET paths.
[Reconciliation](../nnfx_practice/reconciliation.py) uses an unfiltered
`sinceid` read or bounded ID ranges and checks the returned boundary and known
transaction IDs. IDs may be sparse. An unobserved omission with no balance
effect or referenced broker ID cannot be inferred from the numeric sequence.
The [account and journal queries](../nnfx_practice/ledger.py) separate Q0 and A0
using committed baseline records seeded by the fixtures. M07 owns initialization
and activation, including interrupted transitions. M08 owns dashboard labels,
colours and refresh indicators.

All checks used a scripted transport or a mocked HTTPS connection. No OANDA
requests or broker mutations were made. Actual endpoint behavior for the intended
account, financing mode, charge mapping and two-leg execution remain unverified.

## M03 offline candle validation and reference checks

On 17 November 2026, `python3 -m unittest discover -v` passed all 48 checks
with Python 3.14.4 and SQLite 3.46.1. The 37 M01/M02 checks passed before and
after the change. The previously recorded M02 digest matches its original files.
The combined M03 source SHA-256 is
`32363c684d2ee5866a10d6c715bb2439cb92f0d8811106030c77fcce24de9100`,
using the same sorted-path procedure as M01. The [M03 fixtures](../tests/test_m03.py)
use a synthetic 50-candle manifest and scripted broker responses.

The [shared candle capture](../nnfx_practice/candles.py) uses the recorded run
date and exact bound count. Each evaluated pair and stage saves its own request
and response times, reported final candle start when aligned, received
count and validation result in `pair_decisions.capture_json`. Only the metadata
is stored. Earlier bars must be completed, ordered and aligned to 17:00 New York.
An earlier calendar date can be absent if the response still supplies the exact
count of valid bars. A response received at or after 17:00 New York is unavailable
for the intended run date, even when it reports the old candle as incomplete.

Eight [reference probes](../tests/check_m03_lab_reference.py) passed on the
original indicator lab at commit `cd64da9fbeb970ce3f1fecb79fcb5b67a24b6a9d`.
From the practice lab root, run them with the sibling lab's Python environment.

```sh
lab_reference_root="$(realpath ../nnfx-indicator-lab)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$lab_reference_root" \
  "$lab_reference_root/.venv/bin/python" -m unittest tests.check_m03_lab_reference -v
```

| Scenario | Offline result |
| --- | --- |
| A01 | Separate open and entry reads returned different partial-candle prices and saved separate capture metadata. Weekend runs had no intended input. A response at 16:59:59 New York passed and one at 17:00:00 failed. Completed-only responses and earlier or next-session partials failed. `systemd-analyze calendar` resolved weekday 16:50 to 21:50 UTC on 6 March and 20:50 UTC on 9 March, then 20:50 UTC on 30 October and 21:50 UTC on 2 November 2026. The fixture captures matched those dates and offsets. Actual timer dispatch and master duration verification are pending. |
| A02 | Original lab helpers on synthetic outputs distinguished fresh crossings, discrete transitions and directional events from continuing states. Probes covered equality at nine decimals, missing operands and rejection of simultaneous long and short outputs. At the practice calculation boundary, either fresh C1 direction with valid ATR was eligible. Integrated Stage 2 decisions and selected rule operands remain to be verified. |
| A03 | Both stages rejected counts of 0, 14, 49 and 51 against the fixture count of 50. Wrong instrument or granularity, malformed OHLC, incomplete history, duplicate or misaligned timestamps and run-binding mismatch failed. The lab probes checked missing current/prior initialization operands and true-range ties. A price gap gave identical final ATR for full history and 15 bars, zero for 14 bars and no ATR for 13, with only the lab's research-length guard adjusted for the short inputs. The [practice signal boundary](../nnfx_practice/signal_actions.py) kept a valid opposite exit actionable with invalid ATR and prevented entry. Frozen protective levels remain part of the later controller checks. |

The reference probes use the sibling checkout only for offline verification.
Runtime remains independent of it. The earlier 15-bar ATR fixture and 50-bar
capture fixture established the calculation and capture boundaries. The
selected strategy was qualified subsequently.

## M03 selected strategy qualification

On 18 November 2026 the owner selected **STD-Adaptive T3 Channel w/ Ehlers
Swiss Army Knife Mod. [Loxx]** as C1 and **[blackcat] L2 Ehlers Bandpass Filter**
as Exit. The saved Indicator Lab result `a3d408b1-b645-4b38-b3cd-a423e5c8d4a9`
matched the screen's 6,258.30000 pips, 61.09% original C1 average and event
rules. Its saved execution configuration identifies Lab commit
`40e27cfabb4130702716ec1e41db7fbbf6e0f404`. The
[manifest](../strategies/t3_bandpass_v1/manifest.json) records the exact result,
plan, dataset, conversions, transitive helpers, rule identities and defaults.

- **A02 and A03 equivalence.** The packaged conversions matched the frozen Lab
  outputs on identical inputs across 8,288 archived candles. Both accepted
  event series, true ranges and sizing ATR matched the saved observations.
  C1 uses `goLong` and `goShort`. Exit closes shorts on `longEntry` and longs
  on `shortEntry`. The practice run evaluates the saved Python conversion on
  the 16:50 snapshot. The conversion evaluates its supplied sample with
  `barOK=true` and retains the saved `confirmOnClose=true` parameter. The
  candle capture still records the current bar as partial.
- **A03 lookback.** 386 candles was the shortest window matching the current
  and prior C1 and Exit events across 6,748 eligible archived endpoints on
  EUR/USD, EUR/GBP, AUD/NZD and CHF/JPY. Current sizing ATR also matched at
  each endpoint. Every count from 15 through 385 had an event mismatch. At
  the EUR/USD endpoint beginning 14 May 2019 at 21:00 UTC, 385 candles
  produced an extra prior-bar `shortEntry`. Another 144 synthetic partial
  snapshots matched the frozen calculation on identical inputs and
  reproduced the full-history events and ATR on the 386-candle window.
  These comparisons establish the offline lookback under the tested inputs.
  [Qualification summary](../strategies/t3_bandpass_v1/qualification.json) ·
  [Exhaustive archived sweep](../var/m03/qualified-sweep.json)

Python 01's controller `practice-a` now loads version `t3_bandpass_v1` and
the bound lookback of 386. The canonical manifest SHA-256 is
`22a7aa2e743885ff70304f7a540324c5fe547398b91efa39ce83d71ad881f032`.
All 62 standard offline checks and 12 explicit Lab reference checks passed.
An installed-wheel check ran both indicators and ATR without the sibling
checkout or operating database. This qualification made zero broker requests
and created no notebook. M04 retains live candle coverage, and M07 and M10
retain initialization and execution qualification.
[Offline log](../var/m03/offline.log) · [Lab reference log](../var/m03/reference.log) ·
[Reference checks](../tests/check_m03_selected_reference.py) · [Wheel log](../var/m03/wheel.log)

From the practice project root, repeat the saved comparisons and sweep.

```sh
lab_reference_root="$(realpath ../nnfx-indicator-lab)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$lab_reference_root" \
  "$lab_reference_root/.venv/bin/python" -m unittest \
  tests.check_m03_lab_reference tests.check_m03_selected_reference -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$lab_reference_root" \
  "$lab_reference_root/.venv/bin/python" -m tests.check_m03_selected_reference --sweep
```

## M04 read-only preflight

On 17 November 2026, all 48 M01–M03 baseline checks and all 59 discovered
checks, including 11 new M04 checks, passed with Python 3.14.4 and SQLite
3.46.1. The combined source SHA-256 is
`5f8dbf5e9f7a6fbe14c8d20dc8487f8ae1424344a48941bcf3cfaf58e24f3864`, using
the same sorted-path procedure as M01. The controlled inputs and assertions
are in the [M04 suite](../tests/test_m04.py).
[Baseline log](../var/preflight/m04-baseline.log) ·
[Full offline run log](../var/preflight/m04-discovery.log)

| Scenario | Fixture result | Intended-account evidence |
| --- | --- | --- |
| A16 | The account pass ran without a manifest or count, matched the bound account and USD currency, and retained the returned balance, one open trade and one pending order. Wrong account or currency stopped before market-data reads. The report recorded a supplied division reference, MT4 client-extension restriction, protected-size guidance and hedging/protection fields. A missing division reference or inconsistent activity count left the pass incomplete. Evidence omitted fixture credentials and raw account IDs. | The owner confirmed OANDA Australia Pty Ltd. The response matched Python 01 and AUD. Balance was AUD 50,000.1007, with zero open trades and zero pending orders. The portal shows v20 netting. OANDA returned `hedgingEnabled=false` and `guaranteedStopLossOrderMode=ALLOWED`. Client-extension support and protected-trade restrictions remain items for execution review. |
| A05, A13 | All 28 instruments and prices passed in the complete fixture. One pricing GET used `includeHomeConversions=true` for the permitted set. Missing metadata and unavailable prices identified the affected pairs. For a USD home account, matching quotes used returned `accountLoss = 1` and cross-currency quotes used their own returned factors. For an EUR home account, EUR was base-only and the EUR identity factor was checked separately from the USD quote factor on EUR-USD. The SGD fixture recorded both live-case applicability reasons. Missing, ambiguous, zero, negative, malformed and non-finite factors failed; a positive home factor other than 1 also failed. | All 28 permitted instruments returned valid precision, size and margin metadata. All 28 prices were tradeable at the time of the GET and each required quote-currency `accountLoss` was finite and positive. AUD returned exactly 1. The live matching-quote check applied to GBP-AUD and EUR-AUD. The controlled matching-quote check remains in the suite for every configuration. |
| A01, A03, A13 | All 28 synthetic 50-candle windows passed at 16:50 New York in both standard and daylight-saving time. The report retained request and response UTC times, count and final partial candle start. A 49-bar response, HTTP 503, response at rollover and pairs left unread when rollover arrived were recorded with distinct reasons. Before the scheduled minute, after it or on a weekend, a candle pass made zero GETs. | Passed. All 28 pairs returned exactly 386 valid daily mid-price candles, including the intended final partial, before 17:00 New York. No unavailable windows were observed. |

The [preflight command](../README.md#run-the-read-only-practice-preflight) uses
account-scoped GETs on the pinned practice host and emits separate account and
candle reports. The account-details GET supplies identity, currency and activity.
The owner supplied the division for the intended account. The candle pass
records the manifest hash and reuses the M03 window validator. Both passes
leave the notebook untouched.
[OANDA account fields](https://developer.oanda.com/rest-live-v20/account-df/) ·
[OANDA pricing and candle endpoints](https://developer.oanda.com/rest-live-v20/pricing-ep/)

On 18 November 2026 the owner selected Python 01, supplied the practice token
in the owner-only `.env`, and authorised account-scoped GETs for this account
on `api-fxpractice.oanda.com`. The first pass at 10:08 UTC passed the GET
checks with the division pending. After the owner confirmed OANDA Australia
Pty Ltd, the account pass returned three HTTP 200 responses at 10:18 UTC and
passed in full. The redacted reports retain request IDs, timings and responses.
[Initial practice GET evidence](../var/preflight/account-2026-11-18-python-01-get.json) ·
[Completed account pass](../var/preflight/account-2026-11-18-python-01-division.json)

OANDA Australia documents that netting offsets opposite-direction trades in
the same instrument. OANDA's order definitions advise against client extensions
on MT4-associated accounts. The published unique-size FIFO guidance is scoped
to OANDA Corporation. The read-only account pass records the evidence
available for review. M10 still needs to establish how Python 01 handles two
separately identified, same-direction protected trades and targeted closes.
[OANDA Australia sub-account guide](https://help.oanda.com/au/en/faqs/create-additional-sub-accounts.htm) ·
[OANDA order definitions](https://developer.oanda.com/rest-live-v20/order-df/) ·
[OANDA Corporation FIFO guidance](https://help.oanda.com/us/en/faqs/fifo-requirement.htm)

A one-time read-only candle preflight ran on 18 November 2026 at
16:50 New York (19 November at 08:50 Melbourne). Its report started at
`2026-11-18T21:50:01.056016Z`. All 28 pairs returned HTTP 200 with exactly
386 valid candles. Each final partial started at `2026-11-17T22:00:00Z`
and was due to close at 17:00 New York. Candle responses arrived between
`21:50:02.681817Z` and `21:50:14.326247Z`, before rollover. Response
latencies ranged from 0.303 to 1.226 seconds. The report records each pair's
request ID, timings, received count, session and validation result. Its
manifest hash matches Python 01's qualified binding.
[Live candle report](../var/preflight/candles-2026-11-18-python-01.json)

The report SHA-256 is
`ec82389c7b4a0c92127459b1c81b879a55969a6750477133ab3af053739aace1`.
The capture and evidence save succeeded. The service exited with a failure
after its automatic status-update guard detected intervening milestone edits.
The saved report was independently verified and this M04 record was reconciled
with those edits. The one-time timer has finished. The current offline suite
passed all 264 tests, including the original M04 checks.
[Completion regression log](../var/preflight/m04-completion-offline.log)

## M05 Manage Open Trades

On 18 November 2026, the requested 62-test offline baseline passed before
implementation. The final `python3 -m unittest discover -v` passed all 102 tests,
including 40 new M05 checks, with Python 3.14.4 and SQLite 3.46.1.
[Baseline log](../var/verification/m05/baseline.log) ·
[Final offline log](../var/verification/m05/discovery.log) ·
[Controlled M05 inputs and assertions](../tests/test_m05.py) ·
[Evidence and representative request traces](../var/verification/m05/evidence.json)

The combined source SHA-256 is
`f1400d6afc2de0ee6e84e18bfe4fed3e283bdfa595a190a48e1bfc91a0891210`.
It hashes sorted relative paths for package, strategy and test `.py` files plus
`nnfx_practice/schema.sql`, each followed by a NUL byte and its file contents.
The evidence report retains the file list, qualified manifest identity, fixture
configuration identity, run/set IDs, ordered requests and committed records.
Representative notebooks passed SQLite integrity and foreign-key checks.
The [documentation check](../var/verification/m05/document-checks.json) passed
all 103 local links and anchors across eight project documents; `AGENTS.md`
remains 103 lines, below its 300-line limit. Approval status, milestone boundaries
and the remaining M04/M07/M10 dependencies were checked for consistency.
Fixture runs use `run-a` for the existing set and `manage-1`/`manage-2` for
management; registered sets are `set-0` and, in ordering cases, `set-1`.

The [Stage 1 module](../nnfx_practice/manage_open.py) reuses M01 notebook commits,
M02 transaction/ledger reconciliation and M03's unmodified `t3_bandpass_v1`
package with exactly 386 candles. It reads both registered legs, reconciles
closures, completes eligible stop processing before candles, and handles
surviving pairs in brief order. Observations include both independent event
results, operands, rule IDs, surviving leg state and all applicable triggers.
Stops use Trade 2's actual fill; closes address each eligible trade ID separately.
The [record contract](DETAILED_DESIGN.md#record-definitions) documents how
reconciliation stop attempts retain their set/leg/pair identity before the
surviving-pair decisions exist.

| Scenario | Offline result |
| --- | --- |
| A03 | Passed. The real selected strategy executes on the exact 386-bar window; 385 and 387 bars are unavailable. Changed bindings fail before requests. Zero/invalid ATR does not gate an opposite exit, and management never recalculates entry ATR or changes frozen ATR/original protection. |
| A07 | Passed. Long and short cases cover C1 alone, Exit alone, both triggers, unavailable/malformed peer calculations, same-direction and no-event results. Both reasons persist without duplicate closes. Reversed registration order still processes EUR-USD before GBP-USD. A separate reader sees committed observations and prepared attempts before sends, committed outcomes/history before the next mutation, and the completed pair before the next candle request. |
| A10 | Passed. Newly discovered and already recorded Trade 1 TP trigger one eligible move to Trade 2's own fill, including a different short fill. Every pair's stop processing precedes the first signal capture. Already-equal and already-closed cases send no stop request. Intervening closure records its actual cause without claiming a stop adjustment. Empty success and wrong returned price remain unconfirmed. Rejected, cancelled, prepared, pending and unknown prior attempts prevent reissue on subsequent runs; later confirmation leaves the operator issue open. |
| A11 | Passed. Both registered IDs are reconciled, including targeted trade/stop/transaction lookups. SL/SL, TP/SL and operator/SL outcomes preserve individual actual prices, times and causes. Absence/404 alone retains the prior open state and an issue; a confirmed survivor can still exit. An intervening second-leg close avoids a second request. |
| A12 | Passed. HTTP success alone, cancellation, pending requests, partial reductions, another leg's fill and timeouts never establish an unproved close. `CLOSE_WHEN_TRADEABLE` remains occupied and guarded. Failures in capture, observation, attempt, outcome and pair commits stop further actions; a post-send commit failure leaves the prepared intent for next-run reconciliation. Rejected/unresolved closes guard only their own leg, and protection failures preserve eligible exits. Response transactions, outcomes and issues commit together; full history is imported before the next dependent change. A history failure retains the response and stops the stage without advancing the cursor. Wrong-account evidence and authentication failure stop the stage and block Stage 2. |

These are scripted response/state checks, not observed OANDA execution.
The built-in transport remains account-scoped GET-only; M05 mutation methods
require an injected transport and have no live command. No practice GETs or
mutations were made during this milestone. Request shapes and the queued-trade
state were checked against the official
[trade endpoints](https://developer.oanda.com/rest-live-v20/trade-ep/) and
[trade definitions](https://developer.oanda.com/rest-live-v20/trade-df/).
This documentation check does not establish Python 01's execution capabilities.

## M06 sizing and candidate two-leg entry

On 18 November 2026, the requested 102-test offline baseline passed before
implementation. The final `python3 -m unittest discover -v` passed all 171 tests,
including 69 new M06 checks, with Python 3.14.4 and SQLite 3.46.1.
[Baseline log](../var/verification/m06/baseline.log) ·
[Final offline log](../var/verification/m06/discovery.log) ·
[Controlled inputs and assertions](../tests/test_m06.py) ·
[Evidence index and source identity](../var/verification/m06/evidence.json)

The combined source SHA-256 is
`b03504b3d4e61b0023fe1fb9da19d2e269618aa1553f7290d52abd1ae1bdbda5`.
It hashes sorted relative paths for package, strategy and test `.py` files plus
`nnfx_practice/schema.sql`, each followed by a NUL byte and its file contents.
The evidence index retains the file list, qualified manifest identity, fixture
configuration, run/set IDs and links to 57 candidate-case exports containing
ordered requests and committed notebook rows. All exported cases passed SQLite
integrity and foreign-key checks. For cases using subtest loops, the export is
the final variation; the test source retains every variation and assertion.
Set `NNFX_M06_EVIDENCE_DIR=var/verification/m06/cases` when running the suite to
recreate these exports. The run config/code hash fields are explicitly synthetic
fixture markers; the enclosing evidence index identifies the tested sources.

The [sizing module](../nnfx_practice/sizing.py) uses Decimal calculations from
the run's immutable 4.1 balance, rounded executable stop distance and the returned
quote `accountLoss`. Equal leg quantities are rounded down within the per-leg
budget, order limit and remaining combined instrument position limit. Margin
uses base `positionValue`, or the documented identity for a home-currency base,
with instrument rate and any returned account override. Both returned rates and
the selected source are recorded. The candidate applies the lower optional
account rate following the documented [account override contract](https://developer.oanda.com/rest-live-v20/account-df/);
M10 must still compare this estimate with actual intended-account margin.
No combined account risk cap or resized second-leg fallback is added.

The [entry module](../nnfx_practice/entry.py) provides
`enter_candidate(db, broker, run_id=..., pair=...)` for one fresh pair decision.
It reuses the bound 386-candle capture, unchanged `t3_bandpass_v1` calculations,
M01 reservations/attempt commits and M02 transaction/ledger imports. It reserves
both legs, sends Trade 1 with FOK/OPEN_ONLY and its stop, confirms its live stop,
sets and confirms the fill-relative target, checks survival and fresh remaining
margin, then sends Trade 2 with its stop and no target. Complete imported broker
batches establish whether both distinct protected fills existed together. The
response boundary alone never advances the history cursor. The M07 master,
full ordered pair loop, qualification lifecycle and operator disposition remain
unimplemented.

| Scenario | Offline result |
| --- | --- |
| A03 | Passed. Exact 386-candle selected-strategy capture/calculation; 385/387 candles and changed bindings fail before entry. Invalid ATR and continuing/no-event C1 cannot enter. Entry ATR, stop distance and original broker stops remain frozen. |
| A05 | Passed. Both directions, home-matching and cross-currency quotes, distinct conversion fields, missing/ambiguous/malformed/non-finite factors, fractional units, JPY ticks, rounding ties and min/max/remaining-position limits. Returned quote loss factors have no fallback. Base margin conversion and optional account rate are retained. Pre-set insufficiency skips without reservation; post-Trade-1 insufficiency blocks without resizing. Later margin-summary balances do not change the fixed sizing balance. |
| A06 | Passed for the M06 candidate boundary. Long and short traces have separate actual fills and correct protection, including different fills per leg. Blocked pairs make no requests; the same pair decision cannot resume. Other pairs' risk does not impose a combined cap. Full ordered processing of all 28 pairs and Stage 1/Stage 2 independence remain M07 checks. |
| A12 — rejection versus partial entry | Passed. A confirmed wholly rejected/cancelled no-fill first entry releases only after complete history and with no issue. A filled Trade 1 followed by rejected Trade 2 retains its issue and entry block even after Trade 1 later closes. Target rejection, empty/pending/unknown responses, timeouts, reductions, wrong units, duplicate identities and missing/wrong protection never complete a set or trigger repairs. |
| A12 — timing and state | Passed. Exits before the target, during survival/margin reads, before Trade 2 or in its establishment batch leave an incomplete set. A later price exit, including one first observed in the Trade 2 response, preserves historical completion and actual closure. Protection cancellation after establishment preserves that historical fact while creating an operator issue. |
| A12 — commits and interruption | Passed. Independent readers see both reserved legs and prepared intent before each send, and committed prior outcomes/history before the next mutation. Capture, sizing, reservation, attempt, all three response, establishment and pair-outcome failures stop progression. Crashes before send, after fill and after target leave durable evidence and no replay/replacement. A post-send write failure reconciles its fill on the next read while keeping the issue. History/authentication/account failures end the run; committed evidence and the last valid cursor remain. |

These are scripted results, not practice execution or account-path qualification.
The existing practice transport remains account-scoped GET-only; new entry and
target methods require an injected transport, with no live command. The candidate
request fields were checked against the official
[order definitions](https://developer.oanda.com/rest-live-v20/order-df/) and
[transaction/protection definitions](https://developer.oanda.com/rest-live-v20/transaction-df/).
No account restrictions or charge mapping are claimed from these checks.

The [documentation check](../var/verification/m06/document-checks.json) passed
all 112 local links/anchors across eight documents. It records approval/boundary
consistency and the unchanged 103-line
`AGENTS.md` (limit 300). The scheduled M04 candle report was absent when checked
at that handoff; Python 01's completed read-only account pass was
unchanged. Existing broker authorisation covers only Python 01 account-scoped
GETs on `api-fxpractice.oanda.com`.

## M07 master workflow and qualification lifecycle

On 18 November 2026, the requested 171-test offline baseline passed before
implementation. The final `python3 -m unittest discover -v` passed all 264 tests,
including 93 new M07 cases, with Python 3.14.4 and SQLite 3.46.1.
[Baseline log](../var/verification/m07/baseline-171.txt) ·
[Final offline log](../var/verification/m07/discovery.txt) ·
[Controlled assertions](../tests/test_m07.py) ·
[Account model and trace exporter](../tests/m07_support.py) ·
[Evidence index](../var/verification/m07/evidence.json)

The combined source SHA-256 is
`b1489677cbf855c9679c236b79ec23ee78e290818b50e9cb49e1d34b01c74362`.
It hashes sorted relative package, strategy and test Python paths plus both schema
SQL files, each path followed by a NUL byte and its contents. The evidence index
records per-file hashes, the qualified manifest, fixture configurations and all
93 case exports, including run/set IDs, ordered requests, independently observed
committed progress/attempts and final notebook rows. Existing databases in those
exports passed SQLite integrity and foreign-key checks; guard-only cases retain
the absence of a notebook. The two-controller case retains both notebooks.
Run config/code hashes are explicit fixture markers; the enclosing source hash
identifies tested code. Flow variations inject signals/ATR, while named real
strategy cases evaluate the unchanged selected package on exact 386-candle
windows. The selected package's implementation hashes still match its manifest.
These checks supplement M03 calculation qualification.

The [master](../nnfx_practice/master.py) calls M05 management, one 4.1 summary,
the [ordered entry loop](../nnfx_practice/manage_new.py), and final reconciliation.
Sizing-summary evidence is excluded from reporting snapshots; margin reads
remain on candidate decisions. Every pair outcome commits before advancing.
Blocked skips retain their related set/issue, and stages retain current step,
pair and derived outcome counts. Fatal account/history/balance errors block entry;
write failures stop requests and leave the last committed progress with a service
error. Interrupted runs are never resumed.

The [local disposition action](../nnfx_practice/disposition.py) uses fresh broker
reads and the [shared exclusion boundary](../nnfx_practice/control.py), submits no
orders, and records one evidence-backed issue resolution. It refuses unsupported
uncertainty, surviving incomplete entries and pending orders. It can confirm
restored protection while the surviving leg remains occupied. Reconciliation
alone keeps operator issues open. Unknown target attempts on confirmed closed
trades retain their prior outcome and terminal proof in the disposition.

The [lifecycle](../nnfx_practice/lifecycle.py) commits Q0/evidence/cursor together,
reconciles forward on reopening, records explicit qualification invocations, and
commits A0/history/cursor/evidence/time atomically. Repeated activation verifies
its original record. Schema 2 preserves legacy rows and adds invocation labels
and immutable baseline guards; interrupted migration rolls back. Ordinary startup
rejects missing activation; qualification startup rejects activation or missing
prerequisite references. Execution and activation still reject the built-in live
transport regardless of supplied references. These references record external
reviewed evidence; fabricated references are not live qualification.

| Scenario | Offline result |
| --- | --- |
| A02/A03 | Passed. Exact selected 386-candle captures, real flat-window calculations, invalid ATR isolated from required exits, and a fresh entry-stage C1/ATR independent of former direction and Stage 1 decisions. |
| A04/A05/A06 | Passed. No/confirmed/unconfirmed closes, exactly one fixed sizing balance, changing margin balances, long/short two-leg sets, all 28 pairs in order, blocked-pair silence, and committed outcomes before advancement. Unexplained/failed sizing balances and fatal management prevent entries. M06 sizing and precision cases also pass. |
| A07/A08/A09/A11 | Passed. Integrated signal and broker closures preserve actual causes. Thirty individually retained cases cross C1/Exit/TP/SL/mixed closures, both former directions, and fresh long/short/no event. Only the fresh entry signal controls the new outcome. M05's opposite/simultaneous/unavailable-event and missing-evidence variations also pass. |
| A10/A12/A13 | Passed. TP stop change; prior rejected stop/uncertain close not retried on later runs; later confirmation preserves the issue. Unavailable inputs never queue entries. Interrupted before-send/after-fill entries retain intent and do not replay. Account/history failures and sizing/response/pair-outcome write failures prevent further requests. All M06 interruption/protection cases pass. |
| A12/A16 — disposition/exclusion | Passed. Reconciliation preserves issues; matching closure, cancellation and restored-stop evidence can resolve only the specified issue. Acknowledgement, unsupported uncertainty, prepared entry, incomplete survivor or pending order cannot release it. Disposition writes are atomic. Active/pending service or an unpaused timer defers before reads; local launches are excluded, and prior timer state is restored after failure, including an initially paused timer. These are controlled adapter checks, not host service verification. |
| A12/A14/A16 — lifecycle | Passed. Interrupted/repeated Q0/A0 operations, denied commits, unresolved qualification issues/sets, missing prerequisites, binding/count mismatch, immutable bindings/baselines and preserved history. Qualification +100 remains qualification; ordinary opening balance includes it and subsequent ordinary profit is +20 exactly once. Independent controllers retain separate locks, accounts and records. |
| A15 | Passed for records only. Finished/skip/failure counts derive from committed outcomes; failed final refresh retains the preceding reconciled report and the original sizing balance. Dashboard implementation remains M08. |

The [wheel build](../var/verification/m07/wheel.txt) and
[artifact inspection](../var/verification/m07/package-check.json) verify that the
new modules and both schema files are packaged. The
[documentation check](../var/verification/m07/document-checks.json) records local
links, approval/boundary consistency and the unchanged 103-line `AGENTS.md`.
No actual notebook was created or migrated.

The scheduled M04 candle report was absent again at the M07 handoff.
The later [M04 completion record](#m04-read-only-preflight) records its result.
Python 01's completed account pass is unchanged. No practice request or mutation
was made during M07. Existing authority still covers only Python 01 account-scoped
GETs on `api-fxpractice.oanda.com`. Real service exclusion awaits M09. Execution,
account-specific restrictions, estimated-versus-broker margin and charge mapping
await M10 and separate authority. Scripted success is not practice verification.

## M08 observational dashboard

On 19 November 2026, the requested M01–M07 baseline passed all 264 tests
before implementation ([baseline log](../var/m08/baseline-264.log)). The final
[offline suite](../var/m08/full-suite.log) passed all 294 tests with Python
3.14.4, SQLite 3.46.1, Flask 3.1.3 and Jinja 3.1.6. The
[30 M08 checks](../tests/test_m08.py) use temporary accounts/notebooks and
scripted broker-shaped records. These are offline results, not host deployment
or practice execution evidence.

The [Flask application](../nnfx_practice/dashboard.py) provides only Controller,
Notebooks and notebook-detail GET views (plus automatic HEAD/OPTIONS).
It follows the approved reference's navigation, panels, badges and tables.
The [templates](../nnfx_practice/templates/notebook.html) include all journal
columns, fills/reductions, dated ledger activity, issues/dispositions and request
outcomes. Rules come from each immutable notebook manifest, including selected
indicator names, output bindings, rule identities and fixed parameters.
New York timestamps retain broker fractional precision and include zone/offset.

| Scenario | Offline result |
| --- | --- |
| A14 — fills and amounts | Passed. Long/short EUR and JPY pips use recorded instrument `pipLocation`, including a nonstandard-location countercheck. Missing metadata/amounts/unrealised values remain unavailable. The split-reduction case retains both fills, weighted exit 1.10980, final broker time, +98 pips and +110 trading result. Financing −1.5, commission −2, other charge −0.5 and cash +50 stay separate; allocations and duplicate delivery do not add extra account postings. Signed text uses green/red. Open/partly reduced legs have no final exit/pips/result. |
| A14/A15 — snapshot cutoff | Passed. Snapshot S retains balance 1000 and summary profit 0 while the later confirmed +100 close remains visible and explicitly labelled after the account snapshot during a failed refresh. The covering snapshot then displays balance 1100 and profit +100 once. Newer allocated financing labels its leg even without a trade-state change. Age, failed/pending refreshes, missing snapshots and the latest run remain visible; sizing-only snapshots do not replace reporting or appear as unfinished reporting refreshes. |
| A14/A16 — qualification and ordinary | Passed. Q0 qualification +100 remains capped at A0. Ordinary reporting opens at 1100 and records +20 once, ending at 1120. Before A0, ordinary figures are unavailable. Both summary periods expose their own snapshot/boundary/time; run, journal and dated activity labels retain qualification/ordinary meaning. |
| A15 — progress and time | Passed. Three committed final outcomes include one skip and one failure; the fourth unfinished decision does not count. Stage 1 reconciliation is distinct from surviving-pair progress; Stage 2 shows 3/28. Both stages display in workflow order. Completed, failed, error and unfinished masters/children persist. Missed weekday launches show staleness without creating runs; March/November offsets, weekends and nanosecond display pass. |
| A15 — observation boundary | Passed. GETs work with no `.env`, broker/network/controller access patched to fail, and notebook files/sidecars mode 0400 in a mode-0500 directory. POST/PUT/PATCH/DELETE return 405 on views; nonexistent activation/disposition/run endpoints return 404. Database contents remain unchanged, and URI read-only connections reject writes even after disabling `query_only`. The local entry point disables dotenv loading, debug and reloading. |
| A15/A16 — consistency and isolation | Passed. Requests hide uncommitted WAL changes, see the subsequent commit and retain one consistent snapshot when a writer commits between queries. Two notebooks keep separate currencies, totals and journals. Unknown IDs/path arguments, symlinks, registry-binding changes and old schemas cannot select, create, migrate or modify a notebook. An unavailable notebook does not suppress a valid independent notebook. Stored HTML is escaped. Existing binding/account checks also pass in the full baseline. |

The [retained fixture pages and records](../var/m08/fixtures/) identify each
test, controller/notebook, manifest/configuration hashes, run/set/transaction
IDs and committed outcomes; the [verification manifest](../var/m08/verification.json)
records source/evidence hashes and environment versions. The
[wheel build](../var/m08/wheel.log) and
[package check](../var/m08/package-check.json) verify the final code/templates
are packaged and all three views render outside the checkout without credentials
or notebook creation. The
[visual checks](../var/m08/visual-checks.json),
[Controller preview](../var/m08/controllers.png) and
[journal preview](../var/m08/journal.png) are offline Chromium renders of retained
fixture HTML. Desktop pages fit 1440 pixels and the mobile journal fits 390 pixels
with internal table scrolling. No browser script errors were observed.
The [document check](../var/m08/document-checks.json) records local links,
approval/boundary consistency and the AGENTS.md line limit.

[Local setup and dashboard commands](../README.md#run-the-local-observational-dashboard)
are available. The application reads only the public registry and bound schema-2
notebooks using SQLite `mode=ro`, `query_only` and short read transactions.
It does not load private credentials, construct a broker client, invoke a
controller or expose activation/disposition. There is no runtime dependency on
the sibling lab: it supplied the presentation reference and the installed browser
used for offline visual verification only.

M04's account and scheduled 386-candle passes for all 28 pairs remain complete;
they do not verify execution. M08 made no OANDA request and did not create or
activate an actual notebook or enable any timer. Existing authority remains
Python 01 account-scoped GETs on `api-fxpractice.oanda.com`. Deployed permissions
(including inability to read private credentials), real service/timer isolation,
dispatch and maintenance exclusion remain M09. Two-leg execution, account
restrictions, broker margin validation and actual charge mapping remain M10,
under separate authority. A14–A16 still require their applicable host/practice
evidence before full acceptance and ordinary activation.

### Controller layout update on dashboard-updates

On 20 November 2026 the owner accepted the account-first layout preview and
requested implementation on `dashboard-updates`. The Controller page now leads
with the notebook name, account-data freshness and outstanding issues, then the
latest run and two responsive stage summaries. Empty issue tables are replaced
by a short message. Native expandable details retain the original exact records;
history opens automatically when older runs contain errors or unfinished records.
The [detailed design](DETAILED_DESIGN.md#7-monetary-records-and-the-read-only-dashboard)
owns the accepted presentation and conservative summary rules.

The [37 focused checks](../var/verification/dashboard-layout-20261120/focused-checks-final.log)
pass: the 30 existing M08 tests, six new presentation/data-safety cases and the
M09 retained-WAL reader check. Coverage includes incomplete pair counts,
non-signal skip reasons, uncertain trade sets, referenced reconciliation state,
unhidden failures/unfinished history, exact values alongside rounded display,
New York DST offsets, escaping, rejected mutation routes and notebook isolation.
The [saved fixture pages and records](../var/verification/dashboard-layout-20261120/cases/)
are controlled offline data, not practice execution evidence.

The [browser checks](../var/verification/dashboard-layout-20261120/browser-checks.json)
pass at 320, 716 and 1280 pixels with no page-level horizontal overflow, both
with details collapsed and expanded. Keyboard disclosure, open-issue visibility,
failed-refresh visibility and expanded unfinished history were checked.
The [716-pixel preview](../var/verification/dashboard-layout-20261120/controller-716.png)
and [320-pixel preview](../var/verification/dashboard-layout-20261120/controller-320.png)
were visually reviewed. The existing lab's installed browser was used only as a
verification tool; no application dependency or lab change was introduced.
The [verification manifest](../var/verification/dashboard-layout-20261120/verification.json)
retains source identities and scope; full-system deployment and the complete
offline suite were not rerun for this presentation change.

No installed source, service, timer, actual notebook, credential or broker state
was changed. Other in-progress branch edits are preserved. Deployment of this
layout remains pending; loading the existing 8879 URL still shows the installed
version. Qualification and ordinary-activation gates retain their existing state.

The owner's subsequent history refinement is also implemented on this branch:
**Previous run history** now sits immediately below the latest run's **Run and
reconciliation details**, with **Account data details** following it. The option
shows the older-run count even when it is zero, with an expandable empty message.
Older runs remain newest-first, exclude the latest run and retain their full
details; error/unfinished history still opens by default. The
[36 dashboard checks](../var/verification/dashboard-history-20261120/checks.log)
pass after this change. The [focused browser checks](../var/verification/dashboard-history-20261120/browser-checks.json)
pass at 320, 716 and 1280 pixels for placement, empty-state keyboard access,
completed-history toggling, visible unfinished history and no horizontal overflow.
The [expanded-history preview](../var/verification/dashboard-history-20261120/history-expanded.png)
uses offline fixtures. The installed dashboard remains unchanged.

#### On-demand historical run pages

The owner then requested that each previous run open separately and load only
when opened. History now contains linked summary metadata (date/time, status,
duration, mode and problem flags), without embedded stage/decision/reconciliation
content. The initial request loads full detail only for the latest run. A new
GET-only route, `/controllers/<controller_id>/runs/<run_id>`, reads just the
selected run from its registered notebook in one read transaction. Links use a
new window/tab target with an isolated opener; browser preference determines
window versus tab. Historical errors/unfinished states remain flagged in the
summary list, which still opens automatically when attention is needed.

The [39 focused checks](../var/verification/dashboard-run-window-20261120/checks.log)
pass (38 M08 and the M09 retained-WAL check). Query traces confirm that historical
stages, decision reasons and reconciliation details are absent from the initial
load and read only for the selected run. Route tests cover missing/foreign IDs,
unavailable notebooks without file creation, escaping, no-store responses,
credential/broker/controller isolation and rejected mutation methods.
The [browser checks](../var/verification/dashboard-run-window-20261120/browser-checks.json)
used a temporary offline fixture server at 320, 716 and 1280 pixels: no run-page
request before selection, exactly one after the click, a separate window/tab,
unchanged original page, keyboard disclosure and no horizontal overflow.
The [history list](../var/verification/dashboard-run-window-20261120/history-links.png)
and [selected run](../var/verification/dashboard-run-window-20261120/previous-run-window.png)
are sample-data renders. The shared [rendered preview](../var/previews/controller-dashboard.html)
was updated with a linked [sample previous run](../var/previews/controller-previous-run.html);
these are rendered files, not Jinja source. The
[verification manifest](../var/verification/dashboard-run-window-20261120/verification.json)
records source identities. The temporary server was stopped. No production
service, trading control, actual notebook or broker state changed; deployment
of the dashboard branch remains pending.

### Notebooks overview update

On 20 November 2026 the owner requested the same usability review and improvement
for `/notebooks`. The overview now leads with the notebook/journal link, data
freshness and visible warnings/open-issue count, then balance, realised profit
and realised loss. It explains qualification versus ordinary reporting in plain
language. Balance is neutral; positive/negative trading results retain their
colours and signs, while zero stays neutral. Thousands separators preserve all
monetary decimals. Ordinary results remain separate from capped qualification
results after activation. Latest saved-run status and a controller link follow;
strategy/indicator names remain visible below. Full signal rules, parameters and
exact snapshot records move into native expandable details. Ledger calculations,
stored rules and trading behaviour are unchanged. The subsequent journal layout
update is recorded below.

The [40 focused checks](../var/verification/notebook-overview-20261120/checks.log)
pass (39 M08 plus the M09 retained-WAL reader check). Added/extended coverage
verifies exact balance precision and neutral presentation, qualification context,
open-issue visibility, separate ordinary/qualification results and retention of
the previous reconciled balance/results after a failed refresh. Existing isolation,
missing-data, escaping, history loading and rejected-mutation checks still pass.

The [browser checks](../var/verification/notebook-overview-20261120/browser-checks.json)
pass at 320, 716 and 1280 pixels: results appear above strategy settings, the full
balance remains visible, keyboard disclosures and journal navigation work, and
neither collapsed nor expanded details cause horizontal page overflow. A stale
fixture preserves the displayed balance and shows the warning. The
[716-pixel preview](../var/verification/notebook-overview-20261120/notebooks-716.png)
was visually reviewed. The [rendered sample preview](../var/previews/notebooks-overview.html)
links to sample journal/controller pages. These are offline fixture observations,
not new OANDA evidence; the [verification manifest](../var/verification/notebook-overview-20261120/verification.json)
retains source identities. The temporary preview server was stopped. No installed
dashboard, service, timer, credentials or actual notebook was modified. Dashboard
deployment remains pending on `dashboard-updates`.

### Trading journal layout update

On 20 November 2026 the owner requested a journal usability update consistent
with the Controller and Notebooks layouts. The journal now leads with freshness,
visible issues/latest saved-run status, balance, unrealised result and separate
realised profit/loss. Qualification and ordinary reporting remain separate;
charge/balance components and exact snapshot records are expandable.

Trades appear in compact paired sets, newest first within open/unconfirmed and
finished groups. A closed leg stays with its open partner; only sets whose legs
are all closed or confirmed not opened enter the finished group. Pair, direction,
entry time/status, prices/units, protection and final results are easy to scan.
Closed trades show that protection is no longer active rather than a misleading
missing-protection warning. Original protection, exact times, identifiers, final
exit evidence, charges and fills remain in per-trade disclosures. The original
phone layout stacked labelled fields; the [25 November table update](#journal-trade-table-and-filters)
replaces that layout. Strategy/configuration
details follow the trades, account activity and request outcomes.

Post-snapshot activity has a visible top warning and an expanded activity section;
uncertain/unsuccessful requests expand automatically. Stop-to-entry failures and
unknown statuses stay visible. Account postings remain distinct from informational
trade allocations. No accounting, broker, schema or trading behaviour changed.

The [41 focused checks](../var/verification/journal-layout-20261120/checks.log)
pass (40 M08 plus the M09 retained-WAL reader check). Added coverage verifies
mixed-state paired grouping and finished-set separation. Extended cases check
open/partially reduced trades have no final result, precise neutral balances,
newer-activity/request visibility and qualification/ordinary identity. Existing
snapshot-boundary, missing-data, isolation, escaping, lazy run-history and
read-only checks remain passing.

The [browser checks](../var/verification/journal-layout-20261120/browser-checks.json)
pass at 320, 716 and 1280 pixels with populated and empty sample notebooks.
Collapsed and expanded records fit without horizontal overflow; keyboard
disclosures and notebook navigation work. Unconfirmed requests, planned targets,
stop-to-entry uncertainty and newer-activity warnings remain visible. The
account summary retains its previous reconciled balance after a newer closure.
The [716-pixel render](../var/verification/journal-layout-20261120/journal-716.png)
was visually reviewed. A [rendered sample journal](../var/previews/trading-journal.html)
and the earlier [notebook-linked journal preview](../var/previews/notebook-journal.html)
show the new layout without opening template source. The
[verification manifest](../var/verification/journal-layout-20261120/verification.json)
retains source identities. Temporary preview servers were stopped. These are
offline fixture checks; the installed dashboard and actual notebooks are unchanged.
Deployment of `dashboard-updates` remains pending.

### Dashboard merge to main

On 20 November 2026 the owner approved merging the dashboard changes into `main`.
The merge contains the Controller, on-demand run history, Notebooks overview,
trading journal, focused tests and their documentation. Separate concurrent M10
changes remain uncommitted in the checkout, including their portions of shared
documents. The [41 focused checks](../var/verification/dashboard-merge-20261120/checks.log)
passed against an isolated copy of the exact dashboard merge contents, without
those concurrent changes. Existing responsive/browser evidence remains recorded
above. The merge changes the local Git history; live dashboard deployment remains
pending.

### Dashboard deployment preparation

On 20 November 2026 the owner requested deployment of the merged dashboard.
Live inspection at **16:04 Melbourne** confirmed the old dashboard active with
PID `11104`, all three views returning HTTP 200, automatic qualification still
enabled/waiting for **21 November 08:50 Melbourne**, the controller idle and the
ordinary timer disabled/inactive. The [predeployment record](../var/prepared/dashboard-a7d756b/predeployment.json)
retains those observations. `sudo -n -l` explicitly denied `codexdev`; this is a
host administrator-access limitation, not an automatic approval-review rejection.
No live deployment command or host modification was performed.

The frozen [deployment bundle](../var/prepared/dashboard-a7d756b/verification.json)
contains the exact installed M10 runtime (43 source files verified against the
previous deployment) plus only ten dashboard file changes from `a7d756b`, yielding
47 application files. The [41 dashboard checks](../var/prepared/dashboard-a7d756b/checks.log)
pass with the installed Python environment. The [eight initial deployment checks](../var/prepared/dashboard-a7d756b/attempt-1/deployment-checks.log)
pass with temporary paths and simulated services: successful isolation, failed-page
rollback, changed-payload/source rejection, active-controller refusal, unchanged
security, nonadministrator refusal and trading-window deferral. These are offline
checks; root deployment and live updated-page verification remain outstanding.

The trading permit pins all installed application files, including the old
dashboard. Therefore this update uses a separate administrator-owned dashboard
release and changes only the dashboard service's working directory. It retains
the existing interpreter, reader identity, port and security settings. The
qualified trading source/package, protected plan, notebook/history and schedules
stay unchanged; no permit or trade is created. Post-switch checks inspect the
three live pages and preservation fingerprints, with rollback to the previous
dashboard on verification failure. The [administrator command](../README.md#deploy-the-merged-dashboard-layouts)
is ready for the existing serveradmin terminal. A successful receipt and follow-up
read-only verification are required before describing this update as deployed.

#### Dashboard deployment retry

The administrator's first attempt at **16:06 Melbourne** installed the separate
release and received HTTP 200 with the new markup on all three dashboard pages.
The service-settings comparison then failed and the helper restored the previous
dashboard. Its [receipt](../var/prepared/dashboard-a7d756b/deployment-20261120T050623661159.json)
records the page results and successful rollback. The screenshot supplied on retry
shows the subsequent refusal to overwrite that retained release directory.
Read-only inspection confirms the restored service is active with PID `36705`,
working directory `/opt/nnfx-practice` and no dashboard override. Qualification
remains enabled/waiting, ordinary scheduling disabled and the controller idle.

The first comparison used exact strings for set-valued service properties, which
can reorder without changing the restrictions. The receipt did not retain the
individual values, so it does not identify the specific property that differed.
Revision 2 compares those collections by contents, retaining allow/deny polarity,
all rules and exact scalar comparisons. It now saves before/after settings and
names any actual difference. It also safely reuses the previous release only when
every file, owner, permission and type matches; changed/extra files or writable
paths are refused without overwriting them. The [existing-release inspection](../var/prepared/dashboard-a7d756b/existing-release-verification.json)
confirms all 47 files and protected ownership/permissions match.

The revised [14 offline deployment checks](../var/prepared/dashboard-a7d756b/deployment-checks.log)
pass, including successful retry after rollback without rewriting files, harmless
rule reordering, rejection of actual restriction changes, and modified/extra/
writable existing-release refusal. The original helper, manifest and checks are
preserved in [attempt-1](../var/prepared/dashboard-a7d756b/attempt-1/). Application
files and the passing 41-check log are unchanged. The revised
[manifest](../var/prepared/dashboard-a7d756b/verification.json) and
[administrator command](../README.md#deploy-the-merged-dashboard-layouts) are ready.
Host sudo remained unavailable to this account. The administrator subsequently
completed the corrected retry, verified below.

#### Verified dashboard layout deployment

The administrator completed the corrected deployment at **16:11 Melbourne on
20 November 2026**. The [successful receipt](../var/prepared/dashboard-a7d756b/deployment-20261120T051138897799.json)
reports `status: deployed`, reuse of the verified release, unchanged security,
qualified trading code, notebook/claim files and protected plan. The original
failed attempt and rollback remain retained. The retry's captured settings show
only `IPAddressAllow` enumeration order changed; its allowed networks are equal.

[Read-only verification at 16:12 Melbourne](../var/verification/dashboard-deployed-20261120/verification.json)
confirms the dashboard active with PID `37415`, working directory
`/opt/nnfx-dashboard/dashboard-a7d756b-7a3d198f3e7e`, and the single intended
working-directory override. All 47 release files match the prepared artifact.
All 43 qualified trading source files and their installed package copies still
match the M10 deployment. Service security matches the prior settings. Automatic
qualification remains enabled/waiting for **21 November 08:50 Melbourne**;
ordinary scheduling is disabled/inactive and the controller is idle.

Live Chromium checks against `192.168.51.10:8879` received HTTP 200 and the new
layout on Controller, Notebooks and the Python 01 journal at 320, 716 and 1280
pixels. Expanded/collapsed details fit without horizontal overflow; journal/back
navigation works, and the saved run's dedicated detail page returns 200. No
browser errors occurred. The [live journal screenshot](../var/verification/dashboard-deployed-20261120/notebooks-notebook-a-716.png)
was visually reviewed. It retains the exact AUD 50,000.1007 qualification balance,
completed saved run and empty trade history. These observations establish live
dashboard operation; they are not new OANDA execution evidence. Verification used
only dashboard GETs and read-only service/file checks, with no broker request or
trading-control change. The dashboard deployment is complete; do not rerun it.

## M09 host operation and maintenance exclusion

On 19 November 2026 the requested 294-test baseline passed again
([baseline log](../var/verification/m09/baseline.log)). The final
[offline suite](../var/verification/m09/full-suite.log) passed **319 tests**,
including the [25 M09 checks](../tests/test_m09.py). Environment: Python 3.14.4,
SQLite 3.46.1, systemd 259.9, Flask 3.1.3, Jinja 3.1.6 and Waitress 3.0.2.
The deployment package now requires Python 3.12+ for SQLite's connection
configuration interface. Neither the offline checks nor host fixtures are
practice execution evidence. M09 made no real broker request.

The [administrator installer](../deploy/install.py) prepares root-owned code
and a virtual environment in `/opt/nnfx-practice`, non-login writer/dashboard
users, a reader group, the public registry/manifests and setgid notebook storage
in `/var/lib/nnfx-practice`. It refuses active, enabled, masked or pending
controller units and a conflicting existing registry. It never copies credentials,
creates notebooks or starts/enables timers. Exact sudoers grants permit only
registered timers' start/stop and controller instances' runtime mask/unmask for
the writer's maintenance adapter. Actual administrator installation was not
possible in this session; these are supplied deployment artifacts.

The [oneshot template](../deploy/nnfx-practice@.service) uses one service per
controller, `Restart=no`, an unlimited startup duration and the shared notebook
lock. Its entry point rejects live execution before reading credentials; M10
must supply the separately authorized execution integration. The
[timer](../deploy/nnfx-practice@.timer) uses
`Mon..Fri *-*-* 16:50:00 America/New_York`, `AccuracySec=1s`, zero randomized
delay and `Persistent=false`. No ordinary instance was enabled or started.

The [real adapter](../nnfx_practice/host.py) stops the timer and runtime-masks
the exact service instance without stopping an active service. It then requires
inactivity and no service/timer job before maintenance broker reads or notebook
writes. The application lock spans the whole operation and restoration. The
notebook closes before the adapter removes its own mask and restores the timer's
previous state; another maintenance cannot race that restoration. Initially
paused timers stay paused, including after a failure. Existing masks are retained.
Restore failures are visible; an unmask failure leaves the timer stopped.
Abrupt process death leaves safe stopped/masked controls for operator review,
with no automated mutation retry or replay.

The separate [dashboard service](../deploy/nnfx-practice-dashboard.service)
runs Waitress as `nnfx-view`, with read-only storage, inaccessible `.env`, no
systemctl/sudo/system-bus access, and outgoing `connect` calls denied. It can
accept trusted-LAN HTTP connections and exposes the existing observational GET
views only. Shared writers opt in to group read-only database/WAL/SHM permissions
and retain those sidecars after closing. Normal WAL autocheckpointing remains
enabled. Default local notebooks stay private. Offline checks cover committed
WAL visibility both during a writer and after the last writer closes, with
filesystem writes denied; deployed enforcement remains unverified.

| Scenario | Offline result |
| --- | --- |
| A01 | Calendar output resolves Friday 6 March to 21:50 UTC and Monday 9 March to 20:50 UTC; Friday 30 October to 20:50 UTC and Monday 2 November to 21:50 UTC. Both skip the weekend. Retained [March](../var/verification/m09/calendar-march.log) and [November](../var/verification/m09/calendar-november.log) calculations do not prove dispatch. |
| A12/A16 | Passed. Adapter checks cover active service, pending job, busy application lock, missing/unstable units, stop/mask failure, unmask/start failure, timeout, exception/KeyboardInterrupt, prior masks, initially paused timers, external timer state changes and two independent controller locks. Broker-read and notebook-write phases are excluded; restoration occurs after notebook closure. |
| A15 | Passed. Shared notebook/WAL/SHM files are group-readable without group writes; `.env` remains mode 0600. Unsafe directory/group settings are rejected. The dashboard reads retained committed WAL after writer closure with read-only files/directory. M08's uncommitted/committed visibility, route restrictions and credential-free tests pass again. |
| A13/A16 | Passed through the full baseline for no queued entries, per-run candle/session selection and account/notebook binding isolation. The ordinary host command rejects before private access or notebook creation. Actual service/timer observations follow below. |

**Actual host evidence.** The
[prerequisite survey](../var/verification/m09/host-prerequisites.json)
confirms hostname `thinkbook-server`, Ubuntu 26.04.1, a running system manager,
`NTPSynchronized=yes`, active chrony and a lingering user manager. The host has
been up since 3 November; logind's lid actions are configured to ignore. Suspend
and hibernate targets are unmasked. System journal visibility is restricted, so
the absence of visible sleep entries is not a wakefulness pass. `sudo -n true`
is denied, and `/opt/nnfx-practice` and `/var/lib/nnfx-practice` are absent.

The final [host report](../var/verification/m09/nnfx-m09-probe-2194936/host-results.json)
contains timestamped systemctl calls, source hashes, actual process traces,
calendar/state properties and cleanup evidence. The
[probe harness](../tests/check_m09_host.py) uses separate `nnfx-m09-probe-*` units,
the approved timer template with temporary short UTC fixture expiries, and
broker-free workers. Its maintenance phases perform an injected scripted
account GET and a real commit to a synthetic bound notebook. No actual private
configuration or actual notebook is used.

| Host check | Observed result and limit |
| --- | --- |
| Actual dispatch — A01 | Passed in the real user manager. Timer launches a broker-free oneshot and records process start/end. Loaded properties confirm the approved New York calendar before fixture overrides, 1-second accuracy, no persistence and no restart. This is not a witnessed production 16:50 launch. |
| Missed launch — A13 | Passed. A timer inactive across its fixture calendar instant dispatches nothing when restarted; the next new calendar instant launches once. No catch-up or queued replay. |
| Restart/overlap/isolation — A12/A16 | Passed. A failing worker has zero restarts. Manual second start and timer expiry during a held oneshot create no duplicate. Controller B completes while A is held. Records and locks remain in their own synthetic notebook identities. |
| Active service — A12 | Passed. A held application lock defers maintenance without touching the timer. A separately active service without the application lock also defers before reads and completes without interruption. |
| Maintenance — A12/A16 | Passed. Real timer stop/runtime-mask blocks manual starts during both scripted broker-read and fixture notebook-write phases, across a scheduled fixture instant. Success/failure both restore a previously active timer without catch-up; success/failure both leave an initially paused timer inactive. |
| Dashboard restrictions — A15 | **Unmet.** Attempting the supplied restrictions in user scope exits `218/CAPABILITIES` before Python starts. The [journal](../var/verification/m09/nnfx-m09-probe-2194936/dashboard-journal.log) is retained. No production security setting was weakened to obtain a pass. Separate service-user permissions, deployed WAL/HTTP checks and broker/control exclusion require administrator deployment. |
| Startup/wakefulness — A01/A13 | **Unmet.** Linger, host uptime and lid configuration are inspection evidence only. System units have not been installed or observed across boot without login; continuous wakefulness through the intended scheduled window remains unverified. |

The report records `controller_probes_passed=true` and overall `passed=false`
because the dashboard host check is unmet. All fixture services/timers were
stopped and their manager links removed; cleanup found zero fixture unit files.
The earlier failed harness attempt (missing runtime directory) and intermediate
probe reports remain in `var/verification/m09`; the linked final report supersedes
them. No ordinary system units are installed or active.

The [wheel build](../var/verification/m09/wheel.log) and
[package check](../var/verification/m09/package-check.json) pass for the new
host/dashboard modules and Python/Waitress requirements. The
[unprivileged installer check](../var/verification/m09/installer-unprivileged.json)
rejects before installation. Unmodified
[unit verification](../var/verification/m09/unit-verification.log) fails on the
absent `/opt` virtual environment. The
[parser check](../var/verification/m09/unit-parser.log) succeeds with staged
copies pointing only the executable at the existing checkout environment;
unrelated Ubuntu XFS units emit deprecation warnings. This is syntax evidence,
not a deployment pass. The [verification manifest](../var/verification/m09/verification.json)
retains versions, source/evidence hashes and the
[document checks](../var/verification/m09/document-checks.json).

**Unmet dependencies before host acceptance/M10 execution:** administrator access
to install and validate the system units, separate non-login identities and exact
sudoers/permissions; deployed read-only WAL/dashboard/network/control checks;
observed startup without interactive login; confirmation of unattended
wakefulness and actual production-scope broker-free dispatch at the intended
schedule. Repeat maintenance/exclusion checks under that deployed system manager.
The essential controller controls in the plan are not fully qualified by the
user-scope probes alone. Working setup/run/maintenance commands and safe
manual recovery are in the [README](../README.md#ubuntu-deployment-and-host-operation).

M04's existing Python 01 account and scheduled 386-candle passes for all 28 pairs
remain successful read-only practice evidence; they do not verify execution.
Existing authority remains Python 01 account-scoped GETs on
`api-fxpractice.oanda.com`. Two-leg execution, account restrictions, actual broker
margin validation and charge mapping remain conditional M10 work under separate
authority. No actual notebook was initialized/activated and no real broker
mutation was enabled or attempted.

## M10 readiness preparation and blocked qualification

On 19 November 2026 the requested
[319-test baseline](../var/verification/m10/baseline.log) passed again. The
[final offline suite](../var/verification/m10/full-suite.log) passed **327 tests**,
including eight [M10 checks](../tests/test_m10.py). The
[focused log](../var/verification/m10/focused.log) and
[verification manifest](../var/verification/m10/verification.json) retain results,
source/evidence identities and pending outcomes. These are offline results,
not actual execution or completed A01–A16 acceptance.
The [document check](../var/verification/m10/document-checks.json) passed all
190 local links across eight documents; `AGENTS.md` remains 103 lines (limit 300).

**Review and authority at the initial M10 handoff.** The owner answered
**“Review still pending”** for M09 at that point; the subsequent
[deployment approval](#m09-deployment-approval) closes that review prerequisite
without waiving any host or execution evidence. The original M10 request permits
broker-free preparation and carries
forward unfinished M09 checks; it grants no mutation authority. Existing broker
authority remains Python 01 account-scoped GETs on `api-fxpractice.oanda.com`.
No broker request, live mutation, actual notebook initialization/activation or
service/timer dispatch was performed for M10. No live transport or executable
qualification/activation command was enabled. M10 execution has not begun.

**Guard discrepancy corrected.** The documentation described initialization as
scripted-only, but `initialize_qualification` lacked the guard already used for
execution/activation. Calling it directly with the built-in GET transport could
create an actual notebook and Q0 without completing M10 prerequisites. It now
rejects that transport before private configuration loading, maintenance controls,
broker reads, locks or notebook creation. Nonempty evidence references cannot
bypass the guard. New checks verify rejection before side effects; live reopen
and activation preserve an existing fixture's Q0/cursor/history; candidate
entries, targets, stops and targeted closes cannot reach the network; and the
GET transport rejects mutations, payloads and other accounts. Existing offline
Q0/A0 interruption, reporting and preservation checks pass again. This changes
no trading rule or strategy calculation.

**Fresh host inspection.** The
[final survey](../var/verification/m10/host-prerequisites-final.json) was collected
outside the filesystem/process sandbox using the system manager. It is read-only
inspection, not system dispatch or permission enforcement evidence. The new
[collector](../tests/check_m10_prerequisites.py) stats actual notebook paths and
private-file permissions without opening notebooks or reading credentials; it
also retains clock/calendar output, source hashes and unavailable commands. It
creates private new reports and refuses replacement/symlink destinations. The
initial report is retained separately: its comma-separated `timedatectl` property
argument returned no clock fields. The final report fixes that collection and
supersedes it; an empty result was never counted as synchronization evidence.

| Dependency / observation | Result and qualification limit |
| --- | --- |
| Administrator access | **Blocked.** The sandboxed sudo check encountered `no new privileges`; repeating outside the sandbox still returned a host sudo-policy denial. `sudo -n true` in the final survey returned status 1. No installation was attempted. |
| Deployed system identities/paths | **Absent.** `nnfx-run`, `nnfx-view`, `nnfx-read`, `/opt/nnfx-practice`, `/var/lib/nnfx-practice`, deployed unit files and the exact sudoers grant do not exist. Both controller units and the dashboard show `LoadState=not-found`; their default property values are not evidence of deployed settings. |
| Clock/calendar | Inspection confirms `NTPSynchronized=yes`, active chrony and New York calendar calculations spanning both DST transitions/weekends. **System scheduled dispatch remains pending.** |
| Ordinary scheduling and notebooks | The system timer is not found/inactive with no pending job. Actual notebook, lock and WAL/SHM paths are absent in the checkout and deployment location. `.env` metadata remains owner-only mode 0600; its contents were not read. No ordinary timer or actual Q0/A0 was created. |
| Single execution, no restart/overlap/catch-up, maintenance | Existing M09 user-manager fixture passes remain retained. **System checks remain pending:** repeat under the deployed manager/service identities, with exclusion through broker-free read/write phases, success/failure restoration and both initially active and paused timers. No user-scope result is promoted to a system pass. |
| Startup/wakefulness | **Pending.** Uptime and lid-ignore inspection do not prove startup without login or continuous wakefulness through the scheduled window. Sleep targets remain unmasked; restricted journal visibility cannot prove absence of suspension. |
| Dashboard deployment | **Pending.** M09's `218/CAPABILITIES` failure is not resolved. Verify deployed read-only WAL visibility during/after writer closure, filesystem/credential/control/network restrictions and HTTP views. This can follow the initial account-path check, but must pass for final qualification. |

**Retained practice read-only evidence.** The successful M04 account and
28-pair/386-candle reports remain unchanged, share the same recorded account
binding, and the candle report matches the current canonical strategy manifest.
This comparison does not reverify current private account configuration, market
availability or execution. Python 01's AUD home currency, Australia division,
portal netting indication and returned `hedgingEnabled=false` remain review
inputs. Client-extension support, same-direction distinct protected trades,
precision/close restrictions and broker margin require actual qualification;
no incompatibility is declared solely from these GETs. The proposed Trade 2
unit reduction remains unapproved and is not applied.

**Execution evidence still required.** All rows below remain pending for their
M10 practice-execution portion. The approved plan owns the full acceptance
mapping; controlled variations remain offline and unobserved outcomes remain
unknown. No synthetic fill or GET is relabelled as execution.

| Acceptance | Required observation after prerequisites and separately scoped authority |
| --- | --- |
| A01–A03, A13 | Weekday 16:50 New York qualification through the same controller service, both stages' own exact 386-candle partial captures on evaluated pairs, signals/rule identities, skips/availability and measured duration. No forced events or completed-candle substitution. |
| A04–A06 | Long, short and cross-currency two-leg sets; actual distinct IDs, fills, signed units and precision; own-fill stops and Trade 1 target; fixed 4.1 sizing balance, purpose-labelled current margin reads, estimated versus actual broker margin; ordered 28-pair outcomes and eligibility. |
| A07–A09 | Targeted surviving trade-ID closes with actual broker outcomes; preserve trigger evidence and fresh independent entry signals. Record any observed reversal separately; do not claim all controlled event combinations occurred live. |
| A10–A11 | Actual Trade 1 TP and scheduled confirmed Trade 2 stop at its own entry, or actual intervening closure. Closing transaction causes, fills and times must agree per leg. A requested change alone is not confirmation. |
| A12, A16 | Account restrictions and request/outcome/transaction correlation under the unchanged binding, durable attempts and issue handling. Unknown responses stay pending, with no replay, repair leg, automatic retry or resized Trade 2. Return incompatibilities/behaviour changes to owner review. |
| A14–A15 | Direct notebook reconciliation initially; final reporting through a broker snapshot, financing/daily postings, closure summaries and applicable charges without double counting, plus agreement with the deployed observational dashboard. |
| A12, A14, A16 activation | All required evidence reviewed, qualification trades/orders confirmed clear and issues evidenced/disposed; fresh reconciled A0 committed atomically while retaining Q0, bindings, history and cursor. Ordinary reporting begins after A0; activation is not authorized or performed in this handoff. |

Each observed variation must retain its acceptance ID, classification/date,
code/configuration/strategy identities, capture inputs, controller run and set IDs,
non-secret broker request/order/trade/transaction IDs, expected/actual outcomes,
notebook snapshot/cursor boundary and discrepancy or blocked reason. Qualification
captures belong in retained qualification evidence, not ordinary candle storage.

**Prepared scope at the initial handoff; authorization was not granted then.** The later
[conditional execution authorization](#conditional-m10-execution-authorization)
now supplies the owner's decision without waiving prerequisites. That handoff
proposed explicit account- and time/run-scoped authority for Python 01 / `practice-a` /
`notebook-a`, the unchanged `t3_bandpass_v1` strategy and the practice host. The
reviewable candidate operations are the approved controller's market/stop entries
(`POST /orders`), Trade 1 target and eligible Trade 2 stop-to-entry changes
(`PUT /trades/{id}/orders`), and required targeted `ALL` closes
(`PUT /trades/{id}/close`), all under that bound account and the brief's signals,
per-leg 1% sizing and 28-pair order. Record the granted limits/reference before
enabling any live mutation path. No authorization can be inferred from this scope,
evidence references or successful inspection. Live gated transport/qualification
service integration still requires implementation and verification under those
established prerequisites; removing the scripted guard alone is insufficient.

Initial account-path success would not complete M10. Final integration still
requires all remaining M09 checks, deployed dashboard evidence and the observed
scheduled run. Ordinary activation/scheduling remain gated separately. This is
an **incomplete M10 handoff for owner review**, not a completed milestone or an
activation recommendation.

## M09 owner review assistance

On 19 November, after requesting closure of the outstanding actions, the owner
asked for help understanding the M09 review. No approval was inferred from that
request; the later explicit decision is recorded below. A technical review of
the installer, controller/timer and dashboard
units, host adapter, shared exclusion, notebook permissions, disposition entry
point and M09/M10 checks found no new blocking code issue in the inspected paths.
The [327-test review regression](../var/verification/m09-review/baseline.log)
passed again; the [review record](../var/verification/m09-review/review.json)
retains inspected source identities and the recommendation. This is code/offline
review, not evidence of deployed host controls or account execution.
The [review document check](../var/verification/m09-review/document-checks.json)
also passes; `AGENTS.md` remains within its 300-line limit.

The review covered these operating choices, all already required by
the approved architecture/design:

| Review point | Implemented behaviour to accept for deployment and verification |
| --- | --- |
| Schedule and failures | One service per controller, weekday 16:50 New York with DST, no overlapping instance, no automatic restart and no replay of a missed launch. An unavailable run waits for the next regular schedule. |
| Maintenance | Pause the timer and exclude new launches; defer if a run is active without stopping it. Hold exclusion through broker reads/notebook writes; close the notebook before restoring the prior timer state on success/failure. An initially paused timer stays paused. Abrupt process death requires manual recovery. |
| Permissions and dashboard | Root-owned executable code, separate non-login writer/viewer identities, private credentials, writer-only notebook changes and committed WAL reads for the dashboard. The dashboard is observational on trusted-LAN port 8878, with broker/control access denied by its service restrictions. Actual enforcement and LAN/firewall deployment remain to be checked. |
| Deployment and gates | Install under `/opt/nnfx-practice` and `/var/lib/nnfx-practice`; do not initialize actual notebooks or start ordinary timers. Live execution and activation stay disabled. |
| Outstanding evidence | Approval accepts the implementation for administrator deployment and broker-free system verification. It does not mark system dispatch, permissions, startup without login, wakefulness, dashboard restrictions or M10 execution as passed. |

The technical recommendation was to approve M09's implementation for
administrator deployment and broker-free verification, retaining every unverified
host/account requirement. The original instruction requires owner review before
M10 execution; the explicit owner decision below now supplies that review.

Administrator access was checked again: sandboxed sudo encountered `no new
privileges`, and the required repeat outside the sandbox still received the
host sudo-policy denial. No alternate route or privilege change was attempted.
An administrator must perform the [documented installation](../README.md#ubuntu-deployment-and-host-operation)
or provide appropriate host access before system-level verification can proceed.
Broker mutation authority remains absent and must be scoped separately after
the essential controller prerequisites. No runtime source changed in this review;
no actual notebook, timer or broker action was initiated.

### M09 deployment approval

On 19 November 2026 the owner explicitly decided:

> I approve M09 for deployment and broker-free verification. Retain all outstanding qualification checks and keep trading disabled.

The [approval record](../var/verification/m09-approval/approval.json) retains the
decision and the exact deployment attempt. This closes the M09 implementation
review prerequisite and authorizes the documented installation and harmless
broker-free system checks. It does not establish a passed deployment, authorize
broker mutations or ordinary activation, or waive any A01–A16 evidence.

Administrator availability was checked outside the sandbox with `sudo -n true`;
it returned status 1 with a host-policy denial. The specifically approved command
`sudo -n python3 deploy/install.py --registry /home/codexdev/projects/nnfx-practice-lab/config.toml`
was then attempted outside the sandbox and independently received the same
host-policy denial, status 1, before the installer ran. No installation change
was made. This is an operating-system access block, not a missing owner approval.
No privilege-policy change or alternate privilege path was attempted.

An administrator must run the [documented installer](../README.md#ubuntu-deployment-and-host-operation)
on `thinkbook-server`, or provide appropriate administrator access for that
approved work. It creates code, service identities, public configuration and
units while leaving credentials unprovisioned, actual notebooks uninitialized
and ordinary trading timers inactive. After successful installation, retain
system-level fixture evidence for every required controller/maintenance and
dashboard restriction, then startup without login and wakefulness/scheduled
dispatch. The existing user-systemd fixture results remain insufficient.

The [approval-stage document check](../var/verification/m09-approval/document-checks.json)
passes. Runtime source is unchanged from the 327-test review regression; no
additional runtime test was needed for recording this approval. All actual
execution outcomes, Q0/A0 initialization and ordinary activation remain pending.

### Missing venv support during owner installation

On 19 November 2026 (Australia/Melbourne), the owner supplied a screenshot of
the approved installer failing at virtual-environment creation with `ensurepip`
unavailable. Local inspection confirms Python 3.14.4, no importable `ensurepip`,
and no installed `python3.14-venv` or `python3-venv` package. The package index
offers `python3.14-venv`; installing the version-matched package is the required
environment repair. This is a dependency failure, not a strategy/account finding.

The [read-only host survey](../var/verification/m10/host-venv-failure-20261119.json)
confirms a partial installation: `nnfx-run`, `nnfx-view` and `nnfx-read` now
exist, and `/opt/nnfx-practice` is root-owned mode 0755. The screenshot and local
inspection show a partial `.venv`. `/var/lib/nnfx-practice` and all three deployed
unit files remain absent; system units are `not-found`/inactive, with no pending
controller jobs. Actual notebook/lock/WAL/SHM paths remain absent. These facts
supersede the earlier absence-of-identities observation and do not qualify system
deployment or permissions enforcement.

The installer previously discovered this missing prerequisite only after
creating users and copying code. It now checks `ensurepip` before registry reads,
account creation or deployment writes and prints the matching Ubuntu venv package
and retry command when missing. Environment creation also uses the same
`sys.executable` whose Python/SQLite prerequisites were validated. The
[new regression](../tests/test_m09.py) verifies that missing `ensurepip` exits
before registry reads, subprocess operations or code copies. The
[focused run](../var/verification/m09-venv-fix/focused.log) passes all 26 M09
checks, and the [full suite](../var/verification/m09-venv-fix/full-suite.log)
passes **328 offline tests**. Neither result is a deployed execution pass.

The session attempted `sudo -n apt-get install -y python3.14-venv` outside the
sandbox under the approved deployment scope; host sudo policy denied it with
status 1 before apt ran. No package installation or root-file repair was
performed by this session. An administrator should run the package installation,
then rerun the [documented installer](../README.md#ubuntu-deployment-and-host-operation).
The existing partial environment and matching identities can be reused; no
deletion, notebook initialization or ordinary timer start is required.

The [repair record](../var/verification/m09-venv-fix/verification.json) retains
the supplied error identity, local prerequisite checks, denied package command,
source/evidence hashes and verification outcomes. The
[document checks](../var/verification/m09-venv-fix/document-checks.json) pass.
M09's owner approval remains valid for this prerequisite fix and broker-free
verification. All outstanding host checks, separately scoped broker authority,
actual practice execution and Q0/A0/ordinary activation gates remain open.

### Venv dependency installed; administrator path correction

On 19 November 2026 the owner supplied output showing successful installation of
`python3.14-venv` and its pip/setuptools wheel dependencies. The same screenshot
shows `cd /home/codexdev/projects/nnfx-practice-lab` was denied for `serveradmin`.
The shell therefore remained in `/home/serveradmin`, and the relative installer
command failed with `No such file or directory` for
`/home/serveradmin/deploy/install.py`. The package repair succeeded; the application
installer did not run on that retry.

Local inspection confirms `python3.14-venv` version `3.14.4-1ubuntu0.2` is now
installed and `ensurepip` is importable. A temporary, broker-free venv creation
with pip succeeded and the temporary fixture was removed. The
[verification record](../var/verification/m09-admin-path/verification.json)
retains the supplied error identity, package/venv checks and absent deployed
service/timer/data paths. This is prerequisite evidence only; system deployment
and all qualification checks remain open.

The previous relative-command guidance did not account for the separate
administrator's lack of directory access. The README now uses absolute installer,
registry and private provisioning source paths. The administrator can run the
approved installer from its own home directory through sudo without changing
checkout permissions. No runtime source changed in this correction; the 328-test
regression remains the latest offline suite. The
[document check](../var/verification/m09-admin-path/document-checks.json) passes.
No actual notebook initialization, ordinary timer start or broker request occurred.

### Installed system artifacts and prepared system probes

On 19 November 2026 the owner supplied successful installer output ending
“Installed. Dashboard is stopped; ordinary timers are not enabled or started.
M10 execution remains disabled.” This closes the installation step; it does
not complete M09's host acceptance or M10 qualification.

The [installed-host survey](../var/verification/m10/host-installed-20261119.json)
independently confirms loaded system units, `nnfx-run`/`nnfx-view` non-login
identities, the reader group, root-owned mode-0644 unit files and root-owned
mode-0440 sudoers file. The data root is `nnfx-run:nnfx-read`, mode 0750.
The controller is inactive (`Type=oneshot`, `Restart=no`); its timer is inactive
and disabled, with the New York weekday calendar, 1-second accuracy and no
persistence. The dashboard is inactive/disabled under `nnfx-view`. No job is
pending. These are loaded-property/metadata observations, not dispatch tests.

Unmodified installed unit verification passed outside the sandbox; the first
sandboxed attempt was blocked by socket restrictions. Two unrelated Ubuntu XFS
units emit ignored `CPUAccounting` warnings. Isolated import from the installed
virtual environment confirms Python 3.14.4, SQLite 3.46.1 with `NO_CKPT_ON_CLOSE`,
the packaged application, Flask 3.1.3, Jinja2 3.1.6 and Waitress 3.0.2. The
[installation record](../var/verification/m09-installed/verification.json)
retains output/source hashes and the supplied success-image identity.

This account cannot traverse the protected data directory. Actual notebook,
sidecar, credential-file and nested directory checks therefore report
`unavailable/PermissionError`, not absence or a permissions pass. No credential
content or actual notebook was opened. The installer creates neither credentials
nor actual notebooks; their required administrator/actor checks remain open.

The [system probe](../tests/check_m09_system.py) and
[staged worker](../tests/m09_system_worker.py) now prepare the required actual
system-manager checks using the installed identities/hardening, separate fixture
units and synthetic notebooks. The controller fixture makes no broker requests;
maintenance uses a strictly scripted GET. The temporary sudoers grant covers only
four exact operations on the generated fixture controller, with no ordinary unit
or wildcard grant. Maintenance runs as `nnfx-run`; dashboard isolation runs as
`nnfx-view`. The harness checks inactive ordinary units before/after and removes
fixture units/grants on completion; cleanup failures prevent a pass. Fixture data
and worker source remain retained separately from actual notebook storage.

The [eight new offline checks](../tests/test_m09_system.py) pass, covering
unprivileged refusal before host changes, isolated prefixes/permissions, retained
hardening/calendar, unreviewed command rejection, private-configuration exclusion,
actual-root rejection, absence of fixture Q0/A0/history and maintenance success/
failure/paused-timer restoration through real notebook functions. The
[focused log](../var/verification/m09-installed/system-harness-offline.log) and
[full suite](../var/verification/m09-installed/full-suite.log) retain **336 passing
offline tests**. No system-probe pass is inferred from these results.

Running the specific approved system probe through sudo was attempted outside
the sandbox. Host sudo policy denied it, status 1, before Python started; the
harness has not executed on the system manager. The administrator command is
ready in the [README](../README.md#broker-free-system-verification). Its successful
fixture result would still leave startup without login, unattended wakefulness,
the intended 16:50 system dispatch, actual credential provisioning/permissions
and production dashboard/practice-record comparison pending. The
[document checks](../var/verification/m09-installed/document-checks.json) pass.
Trading remains disabled and every actual execution/activation gate stays open.

### First system probe and dashboard fixture path fix

On 19 November 2026 the owner ran the administrator probe and supplied its
`fixture_checks_passed=false` output. The
[complete system report](../var/verification/m09-system/nnfx-m09-system-d21869ede7b1.json)
records actual system-manager fixture results, source identities, timestamped
commands and the dashboard journal. Overall qualification remains incomplete.

| System fixture case | Observed result |
| --- | --- |
| Clock and dispatch | Passed. `NTPSynchronized=yes`; the system timer launched the broker-free oneshot as `nnfx-run` (UID 999, GID 982). This was a short fixture UTC expiry, not the intended 16:50 New York dispatch. |
| No restart/catch-up | Passed. A failing oneshot had zero restarts; an inactive timer's missed fixture expiry was not replayed, and the next fixture expiry dispatched once. |
| Overlap, isolation and active deferral | Passed. A held service was not duplicated by a second start or timer expiry, controller B completed independently, and busy-lock/active-service maintenance deferred. |
| Maintenance restoration | Passed for all four active/paused × success/failure cases. Scheduled/manual starts were excluded through scripted broker-read and real synthetic notebook-write phases; notebook closure preceded restoration, with no catch-up. Initially paused timers stayed paused. |
| Dashboard | Failed before serving HTTP. The journal shows `FileNotFoundError` for a duplicated synthetic directory, so dashboard access/WAL checks remain unobserved. No security-setting relaxation was used. |
| Cleanup | Passed. Zero fixture unit files remained, the temporary fixture sudoers file was removed and `cleanup_errors=[]`. The follow-up survey confirms ordinary controller/timer and dashboard remain inactive, with the ordinary timer/dashboard disabled and no pending job. |

The root probe also confirmed matching deployed source and initial directory
ownership/modes, no actual notebook at the configured path, and **unprovisioned
actual credentials**. These metadata/control observations do not establish live
account execution, shared dashboard WAL visibility, boot-without-login behaviour,
unattended wakefulness or intended scheduled-window dispatch.

**Probe defect and correction.** `fixture_definition` inserted the synthetic
directory into `ExecStart`, then globally replaced `/var/lib/nnfx-practice` with
that directory. Because the new directory already contained that prefix, the
second substitution duplicated it. The dashboard read attempted a nonexistent
path before any isolation check or HTTP serving. The generator now translates
the original template first, then inserts the worker command. A new regression
requires exact, single fixture paths in `ExecStart`, `ReadOnlyPaths` and
`InaccessiblePaths`.

Review also corrected an unreliable helper assertion: `InaccessiblePaths` may
leave a stat-able placeholder, so pathname existence alone does not prove that a
control binary is accessible. The dashboard helper now verifies that executing
`systemctl --version` and `sudo --version` is denied (or hidden), and fails if
either command executes. These version-only checks have no control effect.
Two controlled cases cover denied-but-present/hidden binaries and a failed
isolation check when execution succeeds. The credential-file probe still
requires access denial; missing synthetic credentials remain a probe failure.
The service hardening and actual runtime application are unchanged.

Startup failures now stop the probe promptly with an explicit diagnostic and
include the error in its terminal summary; the fixture journal remains retained.
The [11 focused checks](../var/verification/m09-dashboard-path-fix/focused.log)
and [full suite](../var/verification/m09-dashboard-path-fix/full-suite.log) pass
**339 offline tests**. The [repair record](../var/verification/m09-dashboard-path-fix/verification.json)
retains the failure identity, source/evidence hashes and the successful partial
system results without promoting the dashboard or full host to a pass. The
[document checks](../var/verification/m09-dashboard-path-fix/document-checks.json)
pass. The original system report and synthetic fixtures are preserved.

The [follow-up host survey](../var/verification/m10/host-after-first-system-probe-20261119.json)
and direct path checks confirm no fixture unit/grant leftovers. No broker request,
actual notebook initialization/activation or ordinary trading dispatch occurred.
At that repair handoff the corrected probe still required administrator rerun;
the later successful result is recorded below. It staged the updated helper
source directly without an application reinstall. Every remaining qualification
and authorization gate stayed open.

### Successful system fixture verification

On 19 November 2026 the owner ran the corrected administrator probe. The
[successful system report](../var/verification/m09-system/nnfx-m09-system-a21870b78c7d.json)
records `fixture_checks_passed=true`, `error=null`, `cleanup_errors=[]` and
`host_qualification_complete=false`. The
[verification record](../var/verification/m09-system-passed/verification.json)
retains the supplied success-image identity and inspected source/evidence hashes.
This is actual **host** evidence using broker-free fixtures, not practice-account
execution evidence or complete host acceptance.

| Case | Observed successful system result |
| --- | --- |
| Clock, calendar and short-expiry dispatch | `NTPSynchronized=yes`; the loaded timer has the approved weekday New York calendar, 1-second accuracy and no persistence. A temporary UTC expiry dispatched the fixture as `nnfx-run`, UID 999/GID 982, at `11:18:10 UTC`. The intended 16:50 New York window is still unobserved. |
| No restart/catch-up/overlap | A failing worker had no restart; a missed inactive-timer expiry was not replayed; the next expiry dispatched once. A held service was not duplicated, another controller completed independently and active/busy maintenance deferred. |
| Maintenance | All four active/paused × success/failure cases passed. Manual and scheduled launches were excluded through scripted broker reads and real synthetic notebook commits; the notebook closed before restoration. Initially paused timers stayed paused and no missed launch was replayed. |
| Separate dashboard identity and restrictions | The dashboard ran as UID 995 (`nnfx-view`). Its journal confirms denied synthetic credential reads, filesystem writes, outgoing connects, controller/maintenance lock acquisition and execution of systemctl/sudo. Production security settings were preserved in the fixture unit. |
| Committed WAL visibility | The viewer saw the prior committed state while a writer transaction was uncommitted, saw the new state after commit and retained visibility after writer closure. DB/WAL/SHM files remained writer-owned, reader-group mode 0640. POST was refused with 405. |
| Cleanup and ordinary controls | Zero fixture unit files and no temporary fixture grant remained; cleanup had no errors. Ordinary controller/timer remained inactive with no pending job, and its timer stayed disabled. |

The probe confirmed identical reviewed/deployed package code and required directory
ownership/modes before creating fixtures. It also confirmed no actual notebook at
the configured path and **unprovisioned actual credentials**. The successful
dashboard proof uses a synthetic credential sentinel/notebook and loopback HTTP;
it does not verify the actual credential file, production LAN/firewall access or
future practice-record agreement. Startup without interactive login, unattended
wakefulness and the intended scheduled dispatch remain open.

The [post-pass host survey](../var/verification/m10/host-after-system-pass-20261119.json)
confirms ordinary controller/timer and production dashboard remain inactive;
the timer/dashboard are disabled and no job is pending. Both system reports and
their retained synthetic data remain preserved. No broker request, actual notebook
initialization/activation or ordinary trading dispatch occurred.

**Prepared next step: private provisioning and binding check.** A local source
configuration check matches the approved Python 01 account-binding digest and
qualified manifest without displaying credentials or contacting OANDA. The
[prepared administrator checker](../var/verification/m09-private/check_private.py)
then loads the deployed binding as `nnfx-run`, validates the exact strategy and
386-candle count against M04's retained references, checks owner-only mode 0600
and reader denial, and requires ordinary controls inactive and no actual notebook.
It opens no notebook, contacts no broker and displays no credential content.
Its report contains only metadata, with mode 0600 and checkout-owner ownership.
Syntax and [unprivileged refusal](../var/verification/m09-system-passed/private-checker-unprivileged.log)
were checked at preparation. The later administrator result below records its
actual execution under the [README commands](../README.md#provision-and-verify-the-private-connection).

The latest offline suite remains **339 passing tests**; no runtime application
source changed while recording this host result. The
[document check](../var/verification/m09-system-passed/document-checks.json) passes.
M09 and M10 remain incomplete. After private provisioning, arrange the remaining
boot/scheduled-window and production-dashboard checks. A startup observation
requires a planned server restart with other workloads accounted for; none was
requested or performed by this probe. Actual execution authorization remains
separate, and actual notebooks and ordinary scheduling remain gated.

### Private connection verification and observer preparation

On 19 November 2026 the owner provisioned the reviewed `.env` and ran the private
checker. Its [actual report](../var/verification/m09-private/private-5185eb0637bf.json)
records `private_checks_passed=true`, `broker_requests=0`, `execution_qualified=false`
and no actual notebook. The file is owned by UID 999 (`nnfx-run`), group 982
(`nnfx-read`), mode 0600; UID 995 (`nnfx-view`) cannot read it. The loaded
controller/notebook/account-binding digest, qualified manifest and 386-candle
count match Python 01's approved M04 evidence. This validates deployed local
configuration and actor permissions; it does not reauthenticate with OANDA or
establish execution/account-path support. Credential contents are absent from
the report and this record. The source references and private checker hashes
match the inspected files.

The [private verification record](../var/verification/m09-private-passed/verification.json)
retains the supplied success-image identity and evidence hashes. Both actual
notebook initialization/activation and ordinary trading remain gated. No real
broker request or mutation occurred for this step.

**Remaining boot/scheduled-window preparation.** The
[observer setup/check/cleanup](../tests/check_m09_observation.py) and
[credential-free worker](../tests/m09_observation_worker.py) use isolated persistent
`nnfx-m09-observe-*` units. They never reboot, alter power policy or start ordinary
services/timers. The scheduled fixture narrows the approved New York calendar to
its next weekday date, with the original accuracy/no-persistence/no-restart rules.
The boot marker is enabled for a later restart; it is not manually started during
preparation. The monitor is an exec service to avoid holding `multi-user.target`
for the whole observation interval. Scheduled/boot fixtures remain oneshots.

All observer roles run as the deployed writer with the production restrictions
plus inaccessible actual credentials/notebook storage and denied IP traffic.
They read public fixture configuration, write separate lock/JSON files and never
load credentials, open notebooks or construct a broker client. Setup preserves
metadata/source/unit hashes. The monitor samples boot identity, kernel, service
invocation and monotonic/boottime progress, with session-class counts around the
target. The 25-minute assessment window is 16:40–17:05 New York; it is a host
measurement interval, not a controller-duration limit or a new trading rule.

Startup passes only with a new boot ID, expected service UID/invocation and known
absence of user sessions at the boot marker. Unknown session metadata stays
pending. Scheduled dispatch must be observed within the expected 16:50 minute.
Wakefulness needs complete coverage, one boot, gaps at most 45 seconds, bounded
clock uncertainty and suspend-offset variation at most 250 ms. This is evidence
of no detected suspend through the observed window, not a guarantee about later
host behaviour. User sessions in that window require operator confirmation of
unattended conditions. A kernel change after restart requires repeating affected
host-security fixture checks before their evidence is reused.

The next target calculated during preparation is **Friday 20 November 2026 at
08:50 Australia/Melbourne** (Thursday 19 November at 16:50 New York / 21:50 UTC).
Setup calculates and prints the actual next target when executed. Ordinary
trading timers stay disabled; only the broker-free date-specific fixture timer
is enabled. No automatic catch-up or ordinary launch is introduced.

The [eight new observer checks](../tests/test_m09_observation.py) pass: DST/weekend
selection, isolated/hardened unit generation and non-blocking monitor type, new
boot/no-login requirements, expected dispatch minute, continuous wakefulness,
suspend/gap/reboot/uncertain sample rejection, unknown session handling and
unprivileged refusal. The [focused log](../var/verification/m09-observation/focused.log)
and [full suite](../var/verification/m09-observation/full-suite.log) record
**347 passing offline tests**. Rendered, uninstalled unit parser fixtures passed
`systemd-analyze verify`; unrelated XFS `CPUAccounting` warnings remain ignored.
These checks do not establish an observed boot or scheduled dispatch.

The read-only workload survey found two active existing user services,
`nnfx-dashboard.service` and `nnfx-dashboard-private.service`, and no queued
system jobs at inspection. It does not prove that every other workload is idle.
A restart will interrupt existing services and must be coordinated after the
observer is actually staged. No restart was requested or performed.

The specifically prepared observer command was attempted through sudo outside
the sandbox; host policy denied it, status 1, before Python started. Observer
setup has not run. Its [preparation record](../var/verification/m09-observation/verification.json)
retains source/evidence identities, denied command and target/window details.
The [document check](../var/verification/m09-observation/document-checks.json) passes.
The next administrator action is the [README preparation command](../README.md#observe-startup-and-the-intended-scheduled-window),
which arms the probes without rebooting or enabling trading. After setup, review
its metadata, agree the restart timing, and inspect actual boot/window observations
before removing only those observer units; retain all data/source evidence.

Production dashboard/LAN/firewall checks and practice-record comparison remain
separate. M09/M10 are incomplete, and no practice mutation or ordinary activation
authority is inferred from these host results.

### Observer armed and restart coordination

On 19 November the owner ran observer preparation. The
[immutable definition](../var/verification/m09-observation/nnfx-m09-observe-ba7d65c9bebd.json)
and [preparation result](../var/verification/m09-observation/nnfx-m09-observe-ba7d65c9bebd-prepared.json)
record `nnfx-m09-observe-ba7d65c9bebd`, target `2026-11-19T21:50:00Z`
(**Friday 20 November 2026, 08:50 Australia/Melbourne**), with a monitoring window
08:40–09:05 Melbourne. The writer's session metadata query succeeded. The four
user sessions present during preparation are expected while the operator is
logged in; they do not establish or fail the later new-boot/no-login observation.

Read-only system-manager inspection confirms:

- Boot fixture: loaded, enabled, inactive, oneshot; no manual boot-marker start.
- Monitor fixture: loaded, enabled, active/running, type exec, PID 2216578,
  `nnfx-run:nnfx-read`.
- Scheduled fixture timer: loaded, enabled, active/waiting for 21:50 UTC, exact
  New York date/time, 1-second accuracy and no persistence.
- Ordinary practice controller: inactive/static; ordinary timer:
  inactive/disabled with no pending launch. Production practice dashboard:
  inactive/disabled.

The definition's source hashes, staged worker hash and installed observer unit
hashes match inspected files. The [armed-observer record](../var/verification/m09-observation/armed-verification.json)
retains the supplied preparation-image identity and these observations. These
prove setup/active monitoring only; new boot, no-login startup, scheduled dispatch
and complete-window wakefulness remain pending. No reboot, broker request,
actual notebook initialization or ordinary trading dispatch occurred.

**Other workloads found.** The two existing indicator-lab dashboard services are
active and enabled. A read-only Python workload inspection also found
`nnfx.manual` (PID 2215077) and `nnfx.controller` (PID 2215089), both running in
the sibling indicator-lab checkout at inspection, plus long-running render/chart
processes. No arguments or credentials are included in the retained
[workload metadata](../var/verification/m09-observation/workloads-before-planned-restart.json).
An empty systemd job queue does not establish that these application runs are
idle. No sibling process or service was stopped or changed.

The owner chose **a later maintenance window** for the startup-test restart;
see the [recorded decision](../var/verification/m09-observation/restart-deferred.json).
No date is agreed and no reboot is requested. Do not restart automatically when
the sibling run finishes. The scheduled-window observer can continue without a
reboot; its results cannot establish startup without login. Agree the later
window and recheck active work immediately before that restart. This is downtime
coordination for the host; M09 implementation approval is already recorded and
does not need repeating. After a planned restart, leave time before interactive
sign-in for the boot marker, then use the exact definition path with the README
`check` command. If the kernel changed, repeat affected host-security fixture
checks. Retain the observer until its scheduled window and evidence review finish;
cleanup removes only its units and preserves data/source.

The [document check](../var/verification/m09-observation/armed-document-checks.json)
passes; no runtime source changed at this step. The latest offline suite remains
347 tests. All actual execution, final acceptance and ordinary activation gates
remain open.

The [deferred-restart document check](../var/verification/m09-observation/deferred-document-checks.json)
checks the documentation updated for the owner's timing decision. No service,
timer or runtime source was changed for this decision.

### Conditional M10 execution authorization

On 19 November 2026 the owner explicitly decided:

> I authorize controlled practice execution on Python 01 for M10 qualification once the required prerequisites are met. Keep ordinary scheduled trading disabled until qualification and activation review are complete.

The [authorization record](../var/verification/m10-authority/authorization.json)
retains this decision for Python 01 / `practice-a` / `notebook-a` on
`api-fxpractice.oanda.com`, under the unchanged `t3_bandpass_v1` strategy and
approved trading rules. It permits the controlled qualification operations
described in the approved M10 plan once their prerequisites are established;
it does not establish a passed check. Do not ask for this same execution
authorization again. Ordinary activation, recurring trading, other accounts and
strategy changes are outside this grant. The proposed Trade 2 unit reduction
remains unapplied and requires review.

The fresh [broker-free host survey](../var/verification/m10/host-after-execution-authorization-20261119.json)
confirms synchronized time, the ordinary controller inactive with no job or
restart, and its timer inactive/disabled with no pending launch. The
[prerequisite review](../var/verification/m10-authority/prerequisite-review.json)
compares the successful system fixture's recorded application/strategy/unit
hashes against the checkout, installed code, installed package and units: all
match. The kernel and boot identity are unchanged. The later successful private
metadata report supplies the actual credential/binding permission evidence that
was absent during the system fixture run. This session still receives the host
sudo-policy denial. Its inability to traverse deployed notebook paths is
`PermissionError`, not evidence that they are absent; the earlier administrator
report confirmed absence at its recorded time.

The [approved plan](IMPLEMENTATION_PLAN.md#m10--observed-practice-execution-and-activation-readiness)
separates the initial and final gates:

| Gate | Current evidence and next action |
| --- | --- |
| Owner review and controlled execution authority | M09 deployment review and the conditional Python 01 M10 grant are recorded. Neither needs repeating. |
| Essential controller controls before initial mutations | System dispatch/no-restart/no-catch-up/no-overlap, maintenance success/failure with initially active/paused timers, and private binding/permissions have recorded passes. Reuse depends on unchanged relevant code/account/host conditions; recheck affected controls after integration changes. |
| Initial account-path execution | Still pending. Implement and verify the gated live transport and qualification invocation through the same controller service; the installed command still rejects execution. Administrator deployment/service verification and fresh intended-account activity checks/resolution must precede Q0 and orders. Supplying references or this authorization record cannot bypass those steps. |
| Final M09 and integration qualification | Startup without login remains deferred to the later maintenance window. Intended scheduled dispatch/wakefulness, production dashboard and actual M10 execution/ledger/display evidence remain pending. These final checks are not newly imposed prerequisites for the initial account-path check. |
| Ordinary activation and scheduled trading | Disabled. Require completed qualification, all applicable acceptance evidence, clear qualification trades/orders/issues, preserved Q0/history and reconciled atomic A0, plus activation review/authorization. |

No broker request, mutation, notebook initialization/activation, service dispatch
or timer change was made when recording this authorization. The installed GET
transport and execution guards remain intact. The
[focused boundary checks](../var/verification/m10-authority/focused.log) pass;
the latest full offline suite remains 347 tests. The
[document check](../var/verification/m10-authority/document-checks.json)
verifies links and the guidance line limit. This is conditional authority and
readiness inspection, not execution evidence or a completed M10 handoff.

### Guarded M10 service integration and deployment handoff

The owner authorized implementation and deployment verification, retaining disabled
ordinary scheduling and requiring verified prerequisites before any order. The
[347-test baseline](../var/verification/m10-integration/baseline.log) passed before
changes. The [final regression](../var/verification/m10-integration/final-gate-regression.log)
passes **373 offline tests**, including 26 new
[M10 integration checks](../tests/test_m10_integration.py). The earlier intermediate
logs remain retained: they exposed a GET call-shape regression, the observer's
strict old command matcher, missing fixture directories and malformed clock
handling; those were corrected. None was a broker execution observation.

The [qualification module](../nnfx_practice/qualification.py) adds a root-protected
plan bound to one controller/notebook/account/manifest, code/registry hashes,
boot/kernel, explicit run ID and weekday 16:50 New York dispatch. It checks actual
evidence contents and hashes for strategy, account/candles, essential system
controls, private identity/reader denial, initial account resolution and the
recorded owner authority. Pending references, fixture preflights, stale code or
units, changed identities, writable evidence and symlinks cannot grant access.
Live dispatch also verifies the real system service PID/invocation, dedicated
writer, synchronized clock, absent unit overrides and disabled/inactive ordinary
timer. A pre-network durable session claim prevents replay, including after a
failed/interrupted run or a changed run ID. A missed dispatch is not caught up.

The existing controller service now routes to guarded `dispatch`; default broker
reads stay GET-only. Read-only qualification initialization reuses maintenance and
Q0 commit/reopen logic. Actual qualification reuses the master/children, frozen
sizing/protection and attempt/reconciliation contracts, with only accepted
account-bound request shapes allowed. Raw qualification responses/candles are
retained separately as private JSONL; no ordinary candle archive is added.
Ordinary invocation and A0 activation still reject a live qualification permit.
The [disabled example](../deploy/qualification-plan.example.json) has pending fields;
installation never provisions it or any execution plan. No strategy, signal, sizing,
Trade 2 unit reduction or automatic recovery rule changed.

The new offline checks cover stale/missing/pending evidence, account/code/kernel/
registry changes, service identity and clock, protected evidence paths, no replay,
GET-only Q0/reopen, ordinary/activation rejection, native JSON request/response
handling through mocked HTTP, uncertain requests/redirects without retry, and long,
short and cross-currency sets using the unchanged workflow. They retain 386-candle
captures for evaluated pairs in a temporary qualification fixture. These are
**offline checks, not fills or execution qualification**. Existing Q0/A0 history,
interruption, ledger and reconciliation checks pass in the full regression.

**Deployment attempt and limits.** The exact authorized installer was attempted
outside the sandbox with `sudo -n`; host policy denied `codexdev`, status 1,
before installation ran. This is a host access block, not an automatic approval
review rejection or missing owner authority. No alternate privilege route was
used. Installed application/unit hashes still match the prior M09 deployment,
and differ from this proposed integration. Its earlier fixture pass remains
historical evidence; it does not qualify the changed application. The
[fresh host survey](../var/verification/m10/host-after-guarded-integration-20261119.json)
confirms synchronized time and inactive/disabled ordinary scheduling. Nested
deployed notebook paths remain inaccessible to this session, not proven absent.
The updated [unit syntax check](../var/verification/m10-integration/unit-parser.log)
passes against host systemd; it starts no services and proves no deployment.
The [unprivileged boundary checks](../var/verification/m10-integration/unprivileged-boundaries.json)
also reject checkout dispatch before private access, reject ordinary execution and
refuse the administrator probe. These were repeated against host metadata outside
the sandbox; sandbox root ownership mapping changes the early rejection reason.
They are not a deployed-service pass.

Review also removed an overly broad prerequisite: the initial live gate checks
the essential controller observations independently of the fixture report's
overall dashboard result. A new offline case proves a final-dashboard failure
cannot waive those controls or unnecessarily block the initial check. Remaining
dashboard and host acceptance stays required for final qualification. The earlier
372-test run and its verification record are retained as intermediate evidence.

The new administrator-only [deployment probe](../tests/check_m10_deployment.py)
requires an unarmed deployment and absent actual notebooks. It temporarily denies
the actual service's network/private/notebook access, observes two independent
missing-plan failures with no restart, then removes its own drop-in while retaining
reports. Non-administrator refusal and safety preconditions pass offline; actual
execution of this probe is **pending**. The [README commands](../README.md#deploy-and-verify-the-guarded-qualification-service)
deploy the update, repeat the affected M09 system fixture checks, then run this
additional service-gate probe. Do not provision or enable a plan while those
reports are pending. No further execution authorization is requested.

The [final verification record](../var/verification/m10-integration/verification-final.json)
retains source/evidence identities, the denied deployment and outstanding
dependencies. The [document check](../var/verification/m10-integration/document-checks.json)
passes; guidance remains 103 lines. No real broker request, actual notebook/Q0/A0
initialization, ordinary timer start, qualification timer, protected plan or order
was created by this work. The existing broker-free observer is untouched and its
boot/window outcomes remain pending; its older worker/unit hashes describe only
that observation fixture. Its helper now renders the new controller command for
future preparation; existing check/cleanup still use the original stored metadata.
The reboot remains deferred to a later maintenance window.

This is an implemented, reviewable integration with **deployment verification
blocked**. All actual M10 long/short/cross-currency fill/protection/TP/stop/close,
margin/restriction and final scheduled/ledger/dashboard evidence remains pending.
Keep ordinary trading disabled through qualification and activation review, and
preserve Q0/history/cursor when initial prerequisites eventually permit Q0.

### Verified guarded system deployment and disabled-plan preparation

Reviewed on **20 November 2026, Australia/Melbourne** after the owner supplied
successful administrator output. The root reports themselves are dated
19 November at 12:59 UTC (23:59 Melbourne). The earlier sudo-denied attempt
remains historical; it is superseded by the owner's actual installation and
verification results, not by an inferred pass from a screenshot alone.

- The [updated M09 system report](../var/verification/m09-system/nnfx-m09-system-c7865da7339e.json)
  passes controller dispatch, no restart/catch-up/overlap, independent-controller
  and active-service deferral, all four active/paused timer × success/failure
  maintenance cases, and isolated dashboard/WAL fixtures. Cleanup errors are empty.
- The [actual unarmed-controller report](../var/verification/m10-integration/deployment-1053f8036c25.json)
  has `deployment_gate_checks_passed: true`, no cleanup errors and two distinct
  service invocation IDs. Each rejected the missing protected plan with exit 2
  and zero automatic restarts, under temporary network/private/notebook denial.
  Its barriers were removed, the controller returned inactive and ordinary timers
  remained disabled. Actual notebooks were absent at this administrator check.
- Independently compared both reports' 41 application/strategy hashes against
  the checkout, copied deployment and installed package (82 installed-file
  comparisons), as well as unit/probe identities: all match. No application or
  strategy code changed during this follow-up.
- The [fresh host survey](../var/verification/m10/host-after-successful-guarded-deployment-20261120.json)
  retains synchronized clock and current ordinary service/timer inspection.
  This session still cannot traverse deployed notebook paths; that inspection
  limitation is distinct from the administrator's observed absence.

These are **host, broker-free passes**. Both reports explicitly leave execution
and complete host qualification false and record zero broker requests. They do
not establish account fills, protection, precision/restrictions, margin or ledger
agreement. The existing private-binding report and M04 actual GET/candle passes
remain separate evidence. Startup/no-login, the intended observation window and
production dashboard/final practice comparison remain pending. The later-window
reboot decision is unchanged; no restart is scheduled or requested here.

The next reviewed step is the standalone
[disabled-plan preparation tool](../tests/check_m10_preparation.py), using the
already installed broker/control code and existing conditional Python 01 authority.
It is not installed application code and does not invalidate these runtime hashes.
It checks supplied deployment evidence, binding identities and a reviewed receipt
binding those reports/application hashes to the current boot/kernel, then uses the
dedicated writer and maintenance exclusion for one default GET-only account
request. It refuses account/currency/binding changes and opens no notebook.
Existing trades/orders or changed transaction/balance activity since reviewed M04
remain pending for owner review; nothing is adopted, closed or explained away.
Failed/uncertain reads and maintenance-restoration failures remain pending with
retained evidence. A zero-activity report is not assumed in advance.

Only after actual clearance and semantic prerequisite checks pass does the tool
copy root-protected evidence and write a plan with **`enabled: false`**. It performs
read-only plan inspection and retains private metadata. It creates no Q0/A0,
qualification timer or execution permit, sends no order, and preserves any existing
plan/report rather than replacing it. Its proposed instant is 19 November 21:50
UTC, **20 November 08:50 Melbourne**; this does not schedule trading. The separately
armed observer at that time remains broker-free. Actual preparation execution,
fresh account clearance and protected plan creation are still **pending**.

The [focused checks](../var/verification/m10-deployed/preparation-focused.log) and
[final suite](../var/verification/m10-deployed/host-context-suite.log) pass, now **383
offline tests** including ten preparation cases. These cover one GET under
exclusion with the paused timer preserved, existing/changed activity, failed
reads/restoration, binding mismatch before access, non-administrator refusal,
invalid timing, changed boot/kernel/report contexts and exclusive/private report creation. The prior 373-test result
remains retained; no actual account read was made in this follow-up. The
[verification record](../var/verification/m10-deployed/verification.json)
retains report/screenshot/source identities and the
[document check](../var/verification/m10-deployed/document-checks.json).
Use the [README preparation command](../README.md#prepare-a-disabled-python-01-qualification-plan)
from the administrator terminal; no application reinstall is needed. Keep ordinary
scheduled trading disabled through actual qualification and activation review.

### Verified account clearance and Q0 initialization handoff

On **20 November at 00:20 Melbourne**, the administrator ran the preparation
command. Its [account report](../var/verification/m10-preparation/m10-preparation-f98a28a3a85e.json)
records one actual account-scoped HTTP-200 GET under maintenance, bound to
Python 01 / `practice-a` / `notebook-a` and the unchanged qualified manifest.
It confirms zero open trades and pending orders, unchanged realised balance and
transaction boundary `2249`, and no maintenance error. Its
[prepared metadata](../var/verification/m10-preparation/m10-preparation-f98a28a3a85e-prepared.json)
records a valid root-protected plan with `enabled: false`, no notebook/Q0,
no timer and zero broker mutations. The original preparation helper and staged
worker hashes match the metadata. This is **practice read-only and host evidence**;
it is not fill, protection, margin or execution qualification.

The inspection's `qualification_ready: false` and `private_binding_checked: false`
are expected outputs of a broker-free plan inspector. Actual private binding was
checked separately by the dedicated writer before the GET, whose response also
verified account/currency. The disabled plan and missing Q0 still prevent dispatch.
The proposed instant remains 19 November 21:50 UTC, **20 November 08:50 Melbourne**.
No qualification timer has been created or armed. The broker-free observer and
deferred-reboot decision are unchanged; all remaining final M09 checks stay open.

Reviewed evidence now establishes the prerequisites for **initial** qualification
initialization: completed strategy/account/candle checks, essential controller
controls on the installed code, private binding/permissions, fresh empty-account
clearance and the recorded conditional execution authority. This does not waive
the remaining host/dashboard or actual execution requirements for final
qualification. No approval is requested again for the already authorized scope.

The standalone [Q0 initialization wrapper](../tests/initialize_m10_qualification.py)
is prepared for the next administrator action. It checks the exact prepared plan
hash, protected evidence and current controls, refuses existing notebooks and
sidecars, then temporarily sets the plan flag for a dedicated GET-only initializer.
It calls the existing lifecycle/maintenance path, verifies Q0's qualification
purpose, snapshot/transaction/cursor agreement, balance/binding and unactivated
state, and restores the original disabled plan bytes. Mutations are also rejected
by its broker subclass. It dispatches no controller and creates/starts no timer.
Changed or unknown Q0 facts stay pending; existing Q0/history is never reset,
deleted or retried automatically. Interrupted state is preserved for review.

The [focused checks](../var/verification/m10-prepared/initialization-focused-final.log)
and [full suite](../var/verification/m10-prepared/full-suite.log) pass: **392 offline
tests**, including nine new initialization cases. These cover exact plan
restoration on success/failure, concurrent-plan preservation, existing
notebook/sidecar refusal, the real lifecycle with fixture GETs, changed clearance,
non-administrator refusal, and rejection of fixture/changed Q0 evidence as actual
results. The initial focused run found a fixture controller-name mismatch, which
was corrected without changing application code. The installed application,
strategy and unit identities remain the ones that passed administrator probes;
no reinstall is needed for this standalone helper.

The [verification record](../var/verification/m10-prepared/verification.json)
retains report, supplied-image, source and host identities. Its
[document check](../var/verification/m10-prepared/document-checks.json) passes.
No additional broker request or actual Q0 initialization was performed in this
follow-up. Actual Q0 and the wrapper's administrator execution remain pending;
use the [README Q0 command](../README.md#initialize-qualification-q0-and-leave-the-plan-disabled).
After actual Q0 verification, a dated one-time qualification dispatch remains a
separate step under existing M10 authority. Ordinary activation and recurring
trading remain disabled until completed qualification and activation review.

### Verified Q0 and initial-session arming handoff

On **20 November at 00:43:43 Melbourne**, the administrator initialized Q0.
The [actual initialization report](../var/verification/m10-initialization/m10-q0-3a24c7c4771c.json)
has `status: passed`, `source: practice_get`, one broker GET and zero mutations.
Q0 `c245f517b15448cabb2edbb5336a53aa`, its transaction boundary and import cursor
agree at `2249`; balance/binding/manifest match the reviewed clearance. Ordinary
activation is unset. The original disabled plan hash
`5810f982e37625b7c669dc0ac919d2d6e56cec0dcc82b5fca60e873f74a0c7bd`
was restored, ordinary controls were verified inactive and no timer was created.
The [intent](../var/verification/m10-initialization/m10-q0-3a24c7c4771c-intent.json)
and report remain retained. This closes actual Q0 initialization; it does not
establish execution, fills or complete host qualification.

The next step is one explicit **initial account-path** qualification session under
the existing conditional Python 01 authority. The proposed instant is unchanged:
**20 November 08:50 Melbourne / 19 November 16:50 New York**. It is separate from
the broker-free host observer at that time. Deferred startup/no-login, intended
window/wakefulness, production dashboard and final integration/activation checks
remain pending; these final checks are not newly imposed prerequisites for the
initial account-path session. No further execution approval is requested.

The standalone [armer](../tests/arm_m10_qualification.py) is prepared and tested.
Before any plan/timer mutation it validates the actual Q0 metadata, protected
evidence and code/host identities, reads current Q0/manifest/cursor through
read-only SQL, checks the actual shared notebook/WAL/SHM ownership/permissions,
and refuses activation, prior qualification activity, an existing date claim or
an existing timer. It preserves Q0, all cursors and history. The runtime application,
strategy, service template and ordinary calendar are unchanged.

The administrator command will enable only the date-bound qualification plan and
start a separate **dated timer targeting the same controller service**. It may
permit actual practice orders at the reviewed time under the brief's unchanged
rules; it forces no signals. The timer is static, without boot installation or a
recurring calendar, with 1-second accuracy, zero random delay and no persistence.
The ordinary timer remains disabled/inactive. Actual dispatch retains writer/PID/
invocation checks, no restart, one-service exclusion and durable no-replay claims.
The armer itself sends no broker request. Failure before a start attempt cleans
up only confirmed unused setup; an uncertain start remains pending with its
evidence preserved, without automatic retry, service stop or notebook rewind.

The [392-test baseline](../var/verification/m10-arming/baseline.log) passed again.
The [final suite](../var/verification/m10-arming/final-suite.log) passes **406 offline
tests**, including 14 arming cases. The [focused checks](../var/verification/m10-arming/permissions-focused.log)
cover exact dated timing/DST, effective timer properties, actual evidence-kind and
activation checks, read-only Q0 inspection, permission changes, existing history/
claims, non-administrator refusal, successful single-timer start and both setup
failure/uncertain-start handling. Earlier fixture directory/controller-name
mismatches were corrected; no real deployment or broker failure is inferred from
them. The [host timer parser](../var/verification/m10-arming/unit-parser.log) passes
using an uninstalled synthetic timer definition; no unit was started by that check.

The [verification record](../var/verification/m10-arming/verification.json)
retains report/image/source identities, current host inspection and remaining
dependencies. The [document check](../var/verification/m10-arming/document-checks.json)
passes. No additional broker request, protected-plan enabling, qualification timer
creation/start or actual execution was performed in this follow-up. Actual arming
and all long/short/cross-currency fill/protection/TP/stop/close, restriction/margin,
notebook/charge and final dashboard observations remain pending. Use the
[README arming command](../README.md#arm-one-initial-practice-qualification-session)
from the administrator terminal; no application reinstall is required. Keep
ordinary scheduled trading disabled through completed qualification and
activation review.

### Verified initial-session arming

On **20 November at 07:58:25 Melbourne**, the administrator ran the reviewed
initial-session armer successfully. The [actual receipt](../var/verification/m10-arming/m10-arm-567a9f082b81.json)
has `status: armed`, `phase: initial_account_path`, and zero broker requests by
the armer. Its [intent](../var/verification/m10-arming/m10-arm-567a9f082b81-intent.json)
remains retained. The current Q0 audit passed: snapshot
`c245f517b15448cabb2edbb5336a53aa`, transaction boundary/cursor `2249`, query-only
inspection and no ordinary activation. The protected qualification plan is now
enabled with hash
`bb3605ca5664ec0ef65dba7ccb4b6f32638e2d10c2b869efec250e491d8ff880`;
the original disabled-plan identity remains recorded rather than replaced.

The single static dated timer
`nnfx-m10-qualify-m10-06c93a600843441c9ddeda9e2cb3926b.timer` targets the existing
`nnfx-practice@practice-a.service`. Its exact next expiry is **20 November 08:50
Melbourne / 19 November 21:50 UTC / 19 November 16:50 New York**. Effective
properties show `active/waiting`, 1-second accuracy, zero random delay, no
persistence, no drop-ins and no pending job. It is not installed for boot or
recurrence. Do not rerun the armer or start the controller manually.

Independent [read-only host inspection](../var/verification/m10-arming/host-after-arming-20261120.json)
at 07:59 Melbourne confirms the qualification timer definition/source hashes
match the receipt. The controller is inactive, with `Restart=no`, zero restarts,
the expected writer/readers identities and the guarded `dispatch practice-a`
command. The ordinary timer is disabled/inactive with no pending job. The
[supplemental inspection](../var/verification/m10-arming/host-after-arming-details-20261120.json)
at 08:00 confirms NTP synchronization, unchanged boot/kernel and all 41 application
hashes across checkout/copied deployment (82 comparisons). It also confirms the
exact `@scheduled.timer` broker-free observer is waiting for the same instant,
its monitor remains active, and the production practice dashboard remains
disabled/inactive. The first inspection included unused `@dispatch.timer` and
`nnfx-dashboard.service` names; their inactive/not-found observations do not
describe the deployed observer/dashboard. The supplemental record uses their
actual deployed names and correct separate `timedatectl` property options.

The [arming verification record](../var/verification/m10-arming/armed-verification.json)
retains receipt, intent, source, timer, host and screenshot identities. This
follow-up changed documentation/evidence only; it made no broker request and did
not change the protected plan, notebook, service or timer. The 406-test offline
suite remains applicable because runtime/helper source is unchanged. The
[current document check](../var/verification/m10-arming/armed-document-checks.json)
verifies local links and the working-guidance line limit; current status and
command descriptions were also reviewed for consistency.
Execution, fills and all remaining M10 acceptance outcomes remain pending. The
broker-free monitoring window ends at **09:05 Melbourne**; collect and review its
evidence after that time without interpreting scheduler arming as qualification.
Startup/no-login remains deferred to the owner's later maintenance window.
No A0 or ordinary activation is authorized by this result.

### Post-window host review and protected evidence collection

On **20 November at 09:44 Melbourne**, read-only host inspection verified the
actual service dispatch. The [host record](../var/verification/m10-review-20261120/host-review.json)
shows `nnfx-practice@practice-a.service` started at **08:50:00** and exited at
**08:50:15 Melbourne**, `Result=success`, exit status 0, `Restart=no` and zero
restarts. Its invocation is `3867f55091c143b591e716df87df3074`. The approximately
15-second service interval is not yet the notebook's measured master-run duration.
The single qualification timer is `active/elapsed`, with its last trigger at
08:50 and **no next expiry**. No replay, rearm or manual run was requested.
The ordinary timer remains `disabled/inactive`, without a pending job.

The separate broker-free scheduled service started at **08:50:00** and exited at
**08:50:01**, status 0, invocation `1755780bda214eeb92cedbffc945863f`, with no
restart. Its dated timer also elapsed without a next expiry. The monitor exited
successfully at **09:05:00** with zero restarts. These host observations establish
dispatch/process completion only: wakefulness sampling coverage, suspend offsets,
session context and startup without login cannot be inferred from those exits.
Boot ID/kernel are unchanged and NTP remains synchronized. The production practice
dashboard is still disabled/inactive. Startup verification remains deferred to
the owner's later maintenance window; no reboot occurred.

This session cannot read the protected actual SQLite notebook, per-session claim,
broker captures or observer JSONL files. Each attempted metadata read returned
`PermissionError`. The [journal-access result](../var/verification/m10-review-20261120/journal-access.json)
contains no visible journal records for this user; it does not prove the journal
or broker activity is absent. Running the existing root observer checker with
`sudo -n` was denied by the host sudo policy. The
[access record](../var/verification/m10-review-20261120/administrator-access.json)
retains that unmet dependency. No account incompatibility, empty run, successful
fill, zero-order result or completed wakefulness check is inferred.

The [read-only collector](../var/verification/m10-review-20261120/collect_review.py)
is ready for the administrator terminal using the
[README command](../README.md#review-the-completed-qualification-session).
It reads the existing notebook through one query-only transaction, exports actual
run/stage/pair/attempt/fill/issue/snapshot/ledger records and qualification totals,
retains capture/claim/plan identities, and applies the existing observer assessment
to its protected samples. It checks ordinary inactivity before and after collection,
redacts private account values, and writes a new private export owned by the
checkout owner. It sends no broker request, reads no credentials, invokes no
controller, changes no plan/timer/service, repairs no files and never rewinds Q0.
It refuses a missing notebook or missing/incorrectly owned shared sidecars rather
than creating them. Collection status is distinct from qualification outcome.

The [five focused offline checks](../var/verification/m10-review-20261120/collector-checks.json)
passed: consistent read-only fixture export with unchanged notebook bytes/Q0/cursor,
private-value redaction, missing-notebook refusal, explicit malformed-capture
handling without source repair, and early non-administrator refusal. These are
exporter fixtures, not account results. Runtime/strategy/helper code covered by
the existing 406-test suite is unchanged; no application reinstall is required.
The [review record](../var/verification/m10-review-20261120/verification.json)
and [document check](../var/verification/m10-review-20261120/document-checks.json)
retain verification and remaining work. Actual protected export/assessment,
long/short/cross-currency sets, fills/protection/TP/stop/close, restrictions/margin,
ledger/charges/dashboard agreement and final M10 qualification remain pending.
No broker request, service start/stop, timer change or notebook write was made
in this review. Keep ordinary trading disabled.

### Reviewed no-entry session and observation results

On **20 November at 10:42 Melbourne**, the administrator collected both protected
evidence sets using the reviewed read-only collector. The
[actual export](../var/verification/m10-review-20261120/protected-review-d9980f9a89ee.json)
has `status: collected`, no collection errors, unchanged notebook/WAL file hashes
and verified inactive ordinary controls before and after collection. Its collector
source and arming receipt/plan/claim identities match. The screenshot and export
remain retained; the [review receipt](../var/verification/m10-review-20261120/collected-review-receipt.json)
records their identities and the owner's subsequent unattended-context answer.

The notebook records one **qualification** run,
`m10-06c93a600843441c9ddeda9e2cb3926b`, with `status: completed`, started
**08:50:01.217586** and ended **08:50:15.329639 Melbourne**, duration
**14.112094281 seconds**. Both stages completed without failure summaries.
Manage Open Trades had zero surviving pairs and therefore no pair candle capture
or Exit/stop/close action to perform; its measured duration was 0.820 seconds.
Manage New Trades processed all **28 pairs in the brief's exact order**, with
non-overlapping recorded pair intervals, in 12.722 seconds.

Every entry capture returned HTTP 200 and exactly **386 daily mid-price candles**,
with completed history and the correct final **partial** candle for the New York
19 November session. Captures occurred between **08:50:02.320365 and
08:50:15.006776 Melbourne**, before the 09:00 daily rollover. Every pair had valid
ATR, no indicator error and **no fresh C1 event**. All 28 decisions were recorded
as skipped for that reason. The [saved-data review](../var/verification/m10-review-20261120/review_collected.py)
revalidated each capture and recomputed the selected C1/ATR without contacting the
broker; all values, event observations and metadata match the notebook exactly.
The [per-pair replay evidence](../var/verification/m10-review-20261120/pair-replay.json)
and [collected verification](../var/verification/m10-review-20261120/collected-verification.json)
separate this offline calculation replay from the actual retained broker responses.
All 82 current checkout/copied-application comparisons also match the reviewed
deployment; recorded code/config/manifest identities match.

The actual controller made **31 successful GETs**: 28 candle reads, one initial
account reconciliation read, one 4.1 sizing summary and one final reporting account
read. There were **zero mutations, trade sets, legs, attempts, fills, issues or
new transactions/postings**. The `practice_execution` label on these captures
identifies the guarded qualification invocation; it is not evidence of a fill.
The export header's zero broker requests describes the collector itself, not
the earlier controller run. No entry signal was forced or strategy changed.

Q0 `c245f517b15448cabb2edbb5336a53aa` and the import cursor remain at **2249**.
The final reporting snapshot `d131ac88eac04b98870740e924c85b60` is reconciled at
that same boundary, with balance **AUD 50,000.1007**, zero open trades/orders and
zero unrealised P/L. Qualification realised P/L, financing, commission, other
charges and net postings since Q0 are all zero. The sizing snapshot remains
`pending` by design because 4.1 is sizing evidence rather than a reporting
reconciliation; it has no reconciliation error. Historical account lifetime
P/L/financing shown by raw broker responses predates Q0 and is not qualification
profit or a new posting. A0/ordinary activation remain unset, with ordinary totals
unavailable. This flat result does not exercise traded margin or charge mapping.

The broker-free observation assessment was recomputed from retained samples and
matches the collector result. Scheduled dispatch **passed** at
**08:50:01.051485 Melbourne**, UID 999, under the expected invocation and unchanged
boot/kernel. All deployed observer unit hashes and the staged worker hash match.
Wakefulness **passed** over the **08:40–09:05** window: 101 covering heartbeat
samples, maximum gap **15.014205 seconds**, suspend-offset range about **1.36
microseconds**, and maximum clock uncertainty about **4.05 microseconds**. No
suspend was detected within the 250 ms assessment tolerance; no sample was malformed.

Each covering sample recorded **four logged-in user sessions**. The owner answered
**Unsure** when asked whether the server ran without manual wake/start/keep-awake
intervention. Retain `operator_confirmation_required`; unattended operation is
**unconfirmed**, independently of the sampled wakefulness pass. No new boot marker
was collected. Startup without login remains **pending**, with its restart still
deferred to the owner's later maintenance window. Production dashboard/account
agreement remains pending; that service is disabled/inactive.

This is a verified **no-entry observation**, not completed initial execution or
final M10 qualification. Long/short/cross-currency two-leg fills, distinct trade IDs,
actual units, fill-relative protection, Trade 1 TP, confirmed Trade 2 stop-to-entry,
targeted closes, account restrictions/precision, traded margin and charge mapping
were not exercised. Both-stage candle evidence also remains pending because
Stage 1 correctly had no surviving pair to capture. A01–A04/A06/A14/A16 have the
specific corroboration described above; no entire acceptance case is closed by
this session alone. The 406-test offline suite remains applicable and no runtime
source changed. The [current document check](../var/verification/m10-review-20261120/collected-document-checks.json)
passes. No broker request, mutation, notebook write or service/timer/plan change
was made during this review. Ordinary trading remains disabled.

### Ordinary-trading target and immediate-restart checkpoint

The owner requested ordinary trading from **21 November** and asked to close
remaining work as soon as possible. The next eligible weekday New York slot is
**Saturday 21 November 08:50 Melbourne / Friday 20 November 16:50 New York**;
the following slot is **Tuesday 24 November 08:50 Melbourne / Monday 23 November
16:50 New York**. The requested date is a target, not evidence that qualification
or activation review passed. No gate was waived and ordinary trading remains
disabled.

Remaining work before ordinary trading is concrete:

1. **Observed execution:** actual long/short/cross-currency two-leg sets, distinct
   IDs, fills/units, fill-relative protection, Trade 1 TP and confirmed Trade 2
   stop-to-entry, targeted closes, precision/restrictions and traded margin.
   The completed no-entry run does not provide these facts. Natural entry/TP
   events cannot be promised by tomorrow; no signals or trade sizes will be
   changed to manufacture a pass.
2. **Host/dashboard acceptance:** startup without login, unconfirmed unattended
   context and production dashboard/account agreement. Sampled wakefulness and
   actual scheduled dispatch already passed. Finish both-stage/final integration
   and actual financing/charge reconciliation when exercised.
3. **Remaining ordinary integration:** the installed native `ordinary` command
   deliberately rejects; `dispatch` currently selects only the date-bound
   qualification path, and native `activate_ordinary` remains scripted-only.
   An ordinary timer toggle alone cannot provide normal trading. Implement and
   verify the production activation/ordinary path behind completed qualification
   evidence and authorization, without weakening the current gates.
4. **Final activation:** review completed M10/A01–A16 evidence, confirm all
   qualification trades/orders closed and issues resolved, reconcile/commit a
   fresh A0 under maintenance, preserve Q0/cursor/history, then enable the ordinary
   timer under applicable activation authority. No A0 was committed or ordinary
   schedule enabled by the requested target date alone.

The owner answered **"Let's do it now as there are no other services running"**
to the requested restart window. This supersedes the earlier maintenance-window
deferral and authorizes the startup-test reboot now. The
[pre-restart host check](../var/verification/m10-closeout/pre-restart-host.json)
at **12:38 Melbourne** confirms the prepared broker-free boot marker is enabled,
its worker and all observer unit hashes match, ordinary controller/timer are
inactive, and no ordinary launch is queued. Boot remains
`d54fa107-b746-4a74-9d36-2a7315e2f5ae`, kernel `7.0.0-42-generic` before restart.
Keep post-restart boot/login observations pending until collected. A changed
boot/kernel requires affected essential host evidence before another qualification
plan can be accepted; the old plan is already expired and cannot replay.

The [workload check](../var/verification/m10-closeout/pre-restart-workload-details.json)
found the two existing indicator-lab dashboards and sleeping visualization-check
helpers. No research batch worker was identified. These are existing sibling
workloads; none was stopped or modified. A host restart will interrupt the web
services and current connections. To obtain meaningful startup-without-login
evidence, leave clients that automatically reconnect disconnected until the boot
marker has run, then reconnect after allowing startup time. Logged-in/reconnected
sessions leave that outcome pending rather than presumed passed.

**Deployment discrepancy:** the sibling private research dashboard currently owns
**127.0.0.1:8878**. The practice dashboard's installed `0.0.0.0:8878` binding would
conflict, although earlier isolated dashboard fixture checks passed on a temporary
port. Do not stop or reconfigure the sibling service. Select an available practice
dashboard binding/port and update its bind restriction/commands together, then
verify the real service and LAN access against the actual notebook. Its production
deployment remains unverified and disabled. This is host deployment evidence,
not a trading-strategy or account incompatibility finding.

**Restart attempt blocked:** automatic approval review rejected the scoped reboot
request before any shell/`sudo` command ran. Its stated reason was that the host
inspection found active sibling research dashboards, while the owner's earlier
approval assumed none were running. The owner has now been asked specifically
whether to restart with interruptions to both dashboards and the idle visualization
helpers. The owner subsequently answered **"Restart now with those interruptions"**.
The [informed approval](../var/verification/m10-closeout/restart-informed-approval.json)
addresses the stated rejection reason; no workaround was attempted before that
approval. The [rejection record](../var/verification/m10-closeout/restart-approval-review.json)
preserves the outcome separately from earlier host sudo denials. The boot/login
result remains pending. Proceed within this recorded restart scope without asking again.

**Informed-approved retry:** at **13:06:58 Melbourne**, the scoped reboot attempt
passed automatic approval review. The [fresh preflight](../var/verification/m10-closeout/restart-approved-preflight.json)
confirmed unchanged boot/kernel, inactive controller, disabled/inactive ordinary
timer with no pending launch, enabled boot marker and matching observer source/
unit hashes. No new unreviewed research worker was identified. The
[intent](../var/verification/m10-closeout/restart-intent.json) was saved before
the command. The host then rejected `sudo -n /usr/bin/systemctl reboot`, exit 1,
with `sudo: I'm sorry codexdev. I'm afraid I can't do that`. The
[actual attempt](../var/verification/m10-closeout/restart-attempt.json) records
`request_accepted: false` and `reboot_verified: false`. This is a **host sudo-policy
denial**, not another automatic approval rejection. No service was stopped, no
reboot occurred and no alternative privilege route was attempted. Use the already
authorized administrator-terminal command in the README, then collect actual
post-restart boot/login evidence. No repeat permission request is needed.

**Prepared remedies, not deployed passes:** the practice dashboard unit now binds
port **8879**, with its socket restriction changed to the same port. No sibling
service or application/strategy runtime was changed. The revised system fixture
retains its default rejection of actual notebooks and adds explicit
`--preserve-existing-notebooks` mode: actual database/sidecar bytes, ownership,
permissions and identity are compared before/after, without opening actual SQLite,
creating files, resetting baselines or repairing changes. Fixture units additionally
deny actual credential/notebook paths; controller fixtures deny IP networking.
The report now retains boot/kernel context and refuses changed context during
checks. This permits the required post-restart essential checks while preserving Q0.

The [406-test baseline](../var/verification/m10-closeout/baseline-406.log) passed
again. The [focused suite](../var/verification/m10-closeout/focused.log) passes 17
cases; six additional cases cover the new port binding and missing/existing/changed
notebook data, no SQLite access/writes, default refusal, orphan sidecars, unsafe
permissions, symlinks and hardlinks. The [final offline suite](../var/verification/m10-closeout/final-suite.log)
passes **412 tests**. The [dashboard unit parser](../var/verification/m10-closeout/dashboard-unit-parser.log)
also passes. Original unit/probe sources are retained with hashes under
[pre-change evidence](../var/verification/m10-closeout/pre-change/hashes.json).
Actual root deployment, isolated system fixture passes after the change, port/LAN
access and dashboard/notebook agreement remain pending. Do not rerun the full
installer or missing-plan probe over the existing plan/notebook. The prepared
dashboard-only install and preserving probe commands are in the README.

The [closeout record](../var/verification/m10-closeout/readiness.json) retains the
requested target and remaining dependencies. Further ordinary/qualification
preparation remains authorized within the existing gates; no new session was
armed here and no execution result was invented. Do not rerun the initial clean-
notebook armer, remove Q0/history, or delete the old claim to make a new run possible.
The [preparation verification](../var/verification/m10-closeout/preparation-verification.json)
and [current document check](../var/verification/m10-closeout/document-checks.json)
retain the final source/evidence identities. Reboot and ordinary activation are
not reported as completed.

### Verified post-restart startup and kernel refresh handoff

The administrator completed the authorized restart and collected a new
[protected export](../var/verification/m10-review-20261120/protected-review-0113463688d3.json)
at **20 November 13:31:15 Melbourne**. Collection passed without errors, with
ordinary controls inactive before/after and no notebook/WAL changes during
collection. The [post-restart verification](../var/verification/m10-post-restart/verification.json)
retains report/image/source identities and the checks described below.

**Startup without login passed.** The broker-free boot marker ran at
**13:30:25.081894 Melbourne**, uptime **15.023 seconds**, UID 999, invocation
`58e405adcc0d4310a03b158d7805a3b0`. Session metadata was known and recorded **zero
user sessions**. Its boot ID is `2de69781-0280-4dd4-aac4-172f9c749447`, different
from setup, on **kernel 7.0.0-43-generic**. The deployed observer unit hashes and
staged worker hash match. Recomputing the existing assessment from captured rows
reproduces the pass. No further reboot is needed for this completed check.

Independent [host inspection](../var/verification/m10-post-restart/host-confirmation.json)
at **13:33 Melbourne** confirms that boot/kernel, expected boot-service invocation,
synchronized NTP, inactive controller and disabled/inactive ordinary timer with
no pending job. All 82 checkout/copied-application hash comparisons match the
reviewed deployment. The one-time qualification timer did not start the trading
service again after reboot; the notebook still contains exactly the same one run.
The expired plan and durable claim remain unchanged. No new session is scheduled.

The full exported notebook, original 31 GET captures and claim/plan equal the
pre-restart export. Q0 `c245f517b15448cabb2edbb5336a53aa`, cursor **2249**, the
completed no-entry run, decisions and reporting totals are preserved; A0 remains
unset. This confirms retained records, not a fresh broker account reading after
reboot. The collector and this review sent no broker request and made no notebook
write or trading-control change.

**Keep kernel scopes separate.** The prior 08:40–09:05 wakefulness and 08:50
dispatch pass belongs to the preceding **7.0.0-42** boot. Its evidence remains
valid for that observation, including the unresolved four-session unattended
context. It is not a new scheduled-window observation on -43. Refresh the affected
essential broker-free system/permission/maintenance controls on -43 before
accepting another qualification plan. Final current-host and unattended readiness
must retain any remaining unknown outcome. Old root plans also fail their reviewed
boot/kernel identity; do not edit them merely to bypass this gate.

**Dashboard deployment still pending.** The current-kernel port check shows the
research dashboards restored on 8877/8878 and port **8879 available**. The installed
practice unit still binds 8878 and is disabled/inactive. The prepared 8879 unit
was offered for dashboard-only installation, but the
[actual install attempt](../var/verification/m10-post-restart/dashboard-install-attempt.json)
was denied by host sudo policy, exit 1. The installed hash is unchanged. No reload,
dashboard start, sibling-service change or further privilege route was attempted.
Use the authorized administrator deployment/probe sequence in the README; no new
permission request is needed.

One probe hardening correction was made before that handoff: the appended actual-
path denial for the dashboard fixture had followed `[Install]`, where systemd
would ignore it. The fixture generator now explicitly enters `[Service]` before
adding restrictions. A focused regression checks the section semantics for both
controller and dashboard fixtures. This corrects the prepared probe; no deployed
trading/strategy code was changed. The [18 focused checks](../var/verification/m10-post-restart/focused.log)
and [413-test offline suite](../var/verification/m10-post-restart/final-suite.log)
pass on the current kernel. Systemd's [parser check](../var/verification/m10-post-restart/unit-parser.log)
passes for all three uninstalled synthetic unit definitions. These checks do not
replace actual root fixture execution. The [document check](../var/verification/m10-post-restart/document-checks.json)
passes.

Next, install only the prepared dashboard unit, reload systemd, run
`check_m09_system.py --preserve-existing-notebooks`, and start only the observational
dashboard after that probe succeeds. Then verify actual HTTP/LAN display and
notebook agreement. Ordinary timers remain disabled. Actual broker fills,
protection/management, account/margin/charges, final integration and native
ordinary activation/dispatch remain pending; startup success alone does not
complete M09/M10 or authorize A0.

### Verified current-kernel dashboard and no-entry continuation handoff

On **20 November at 13:37:54 Melbourne**, the administrator ran the updated
preserving system probe successfully. The
[actual report](../var/verification/m09-system/nnfx-m09-system-daed36cb06d3.json)
matches current boot `2de69781-0280-4dd4-aac4-172f9c749447` and kernel -43,
all application/source/unit hashes, and the public registry. Clock synchronization,
actual writer dispatch, no restart/catch-up/overlap, independent-controller
deferral, all four maintenance success/failure/paused cases, viewer isolation and
committed WAL visibility passed. Existing actual notebook/sidecar bytes, inode,
ownership and permissions were preserved; cleanup errors are empty and no fixture
units remain. The probe made zero broker requests. Its `host_qualification_complete:
false` is retained because these component fixtures do not establish all remaining
host/final-integration outcomes.

The administrator then enabled the actual observational dashboard. Independent
[host/HTTP inspection](../var/verification/m10-dashboard-20261120/host-http.json)
at **13:40 Melbourne** confirms it is `enabled/active/running` on **8879**, UID 995
(`nnfx-view`), group 982, zero restarts/capabilities, `NoNewPrivileges` and seccomp
active, and the reviewed read-only filesystem/broker/control restrictions. The
research services remain on 8877/8878. All three GET pages return HTTP 200 and
`Cache-Control: no-store` from loopback and the host's LAN address; POST to the
notebook view returns 405. The owner separately confirmed **"Yes, Python 01 loads"**
from their usual LAN device.

The [actual display comparison](../var/verification/m10-dashboard-20261120/display-comparison.json)
matches the completed run, both stages, 28/28 skipped pair progress, measured
duration, Q0, reporting snapshot/boundary and New York timestamps against the
retained actual notebook export. All ten displayed account figures match,
including AUD 50,000.1007 balance and zero qualification postings. Ordinary
figures correctly remain unavailable, with no registered legs, ledger activity
or issues. This closes the flat-record production display comparison, not traded
fills/charges/pips agreement. Ordinary controller/timer remain inactive/disabled.

The new [no-entry continuation helper](../tests/continue_m10_qualification.py)
is ready for the [README command](../README.md#continue-qualification-after-the-no-entry-session)
under the existing conditional Python 01 authority. It checks the old sealed
plan/claim, actual reviewed completed no-entry history and current read-only
notebook, current code/config/binding and successful current-boot controller
fixtures. It reuses the tested GET-only worker for one fresh account clearance
under maintenance. Changed account activity or uncertain reads remain pending;
there is no adoption, closure, reset or strategy/Trade 2 size change.

After a pass, the helper archives the old protected plan/review, preserves Q0,
cursor, every run and old claim, and builds a new date/run identity with current
boot/kernel and controller evidence. It starts only one static dated timer for
the same controller, preserving no restart, overlap, catch-up or replay. It does
not activate A0 or enable the ordinary timer. Known unused setup can be restored
before a start attempt; uncertain starts retain evidence without automatic retry,
rollback or service stop. Prior entries/attempts/issues or activation explicitly
block this narrow no-entry continuation and require their own reviewed path.

The [14 focused continuation checks](../var/verification/m10-dashboard-20261120/continuation-focused-final.log)
and [427-test offline suite](../var/verification/m10-dashboard-20261120/final-suite-complete.log)
pass. Cases cover actual-evidence kind, prior history/activation/issue rejection,
preserved Q0/cursor and claim, matching reconciled reporting boundaries, current read-only audit, changed account/history,
safe pre-start cleanup and uncertain-start preservation. The
[actual unprivileged check](../var/verification/m10-dashboard-20261120/continuation-unprivileged-refusal.json)
refuses before any broker/plan/timer action. Application/strategy runtime is
unchanged, so the current kernel fixture evidence remains applicable and no
reinstall is needed. The [verification record](../var/verification/m10-dashboard-20261120/verification.json)
and [document check](../var/verification/m10-dashboard-20261120/document-checks.json)
retain the evidence/source identities.

**Actual continuation arming is pending** administrator execution. The proposed
instant is **21 November 08:50 Melbourne / 20 November 16:50 New York**. It is a
qualification session, not ordinary activation. No new account GET, plan change,
timer start or broker mutation was performed in this follow-up. The old plan is
still expired. Real two-leg fills/protection, subsequent scheduled TP/stop-to-entry
management, restrictions/margin/charges, remaining current-host/unattended and
final integration, and guarded ordinary activation/dispatch remain pending.
With no qualifying trades yet, those later management observations are not
available for ordinary activation tomorrow. Do not force signals or treat the
requested start date as a passed gate.

### Verified qualification continuation arming

The administrator successfully ran the dated continuation at **20 November
13:58:05 Melbourne**. The [actual receipt](../var/verification/m10-continuation/m10-continuation-50b6c663b690.json)
has `status: armed` and phase `initial_account_path_continuation` for run
`m10-b51f50d1eae44c088721c3a675831798`. Its
[intent](../var/verification/m10-continuation/m10-continuation-50b6c663b690-intent.json)
and [fresh account clearance](../var/verification/m10-continuation/m10-continuation-50b6c663b690-account.json)
are retained. The clearance is an actual HTTP-200 account GET under maintenance,
one request and zero mutations, with no open trades/orders, balance **AUD
50,000.1007** and boundary **2249** unchanged. No account adoption or strategy/size
change was needed. Q0/cursor remain `c245f517b15448cabb2edbb5336a53aa` / `2249`;
ordinary activation is unset and no notebook write was performed.

The previous protected plan was archived under
`/etc/nnfx-practice/qualification/evidence/m10-continuation-50b6c663b690/previous-plan.json`.
Its identity `bb3605ca5664ec0ef65dba7ccb4b6f32638e2d10c2b869efec250e491d8ff880`
is retained with the old run/claim. The new active plan hash is
`db84be8d0d31928c16e8be512472553509cd5a675a2c83ebd53ae369ca84fdc5`, using the
current-kernel controller evidence. Archive creation was verified by the
administrator helper; this unprivileged inspection does not independently open
the protected archive.

Independent [live host inspection](../var/verification/m10-continuation-armed/host-confirmation.json)
confirms `nnfx-m10-qualify-m10-b51f50d1eae44c088721c3a675831798.timer` is
`active/waiting`, static, with exact expiry **21 November 08:50 Melbourne /
20 November 21:50 UTC / 20 November 16:50 New York**, 1-second accuracy, zero
random delay, no persistence/drop-ins/job and the existing controller as target.
Its definition/source/system-report/review hashes match the receipt; all 82
application comparisons and synchronized clock checks pass. The controller is
inactive, ordinary timer disabled/inactive and dashboard active. No repeat arming
or manual controller start is needed. Independent evidence is stored separately
without widening permissions on the administrator-owned arming-report directory.

The [arming verification](../var/verification/m10-continuation-armed/verification.json)
records receipt/image/account/source identities and pending outcomes. Actual
execution, signals, fills and reconciliation for this new session remain pending;
the arming receipt is not a qualification pass. This review made no broker
request or control change. The 427-test offline suite remains applicable because
the runtime and arming helper source are unchanged.

To capture the remaining scheduled-window evidence on **kernel -43**, the prior
broker-free observer can now be cleaned up after preserving its reviewed data,
then prepared again for the matching next window. The existing cleanup retains
all old data/code and touches only that observer's units; it does not touch the
armed qualification timer or ordinary controls. No further reboot is needed:
the completed startup-without-login pass is retained separately. Actual new
observer preparation/metadata remain pending administrator execution of the
[README sequence](../README.md#observe-the-armed-continuation-and-collect-its-results).

The [follow-up collector](../var/verification/m10-continuation-armed/collect_followup.py)
is prepared for this new run ID and its **20 November** New York claim/capture
file. It requires metadata for the matching observer window and current boot/
kernel; it will not treat an older completed run or older observation as this
session. The [seven focused checks](../var/verification/m10-continuation-armed/followup-checks.json)
pass for read-only data preservation/redaction, missing/malformed input, correct
run/date selection, observation context and non-administrator refusal. The original
collector remains unchanged and its [source copy](../var/verification/m10-continuation-armed/prior-collector.py)
is retained. No actual follow-up export has been collected before dispatch. The
[document check](../var/verification/m10-continuation-armed/document-checks.json)
passes. Ordinary activation and all remaining actual execution/management and
final integration gates stay open.

### Automatic qualification and native ordinary handoff

On **20 November 2026**, the owner requested automatic weekday qualification
through the same controller, subsequent scheduled management of qualification
trades, and completion of the guarded native ordinary path. This authorizes the
implementation/preparation; it does not authorize ordinary activation or waive
execution evidence. The request also retains existing M09 deployment and controlled
Python 01 practice execution authority.

**Observed before changes.** The project virtual environment passed all **427
baseline tests**. A first run with the host Python lacked project dependencies and
did not run the complete suite; its output is retained separately. Read-only system
inspection confirmed kernel `7.0.0-43-generic`, inactive controller, disabled/inactive
ordinary timer and active dashboard. Exact timer
`nnfx-m10-qualify-m10-b51f50d1eae44c088721c3a675831798.timer` remained waiting for
**21 November 08:50 Melbourne**, targeting the existing service with 1-second
accuracy and no persistence. Only the old `nnfx-m09-observe-ba7d65c9bebd` observer
was present; its scheduled timer was elapsed. No new observer preparation was
observed, and no reboot or repeat startup check was requested.

**Implementation.** Version-2 protected qualification plans use a separate automatic
weekday timer targeting the original service. They require scoped automatic
qualification authority and observed essential host controls, including independent
maintenance restoration for both timers. Runs use the current day's New York slot,
an exclusive durable date claim and a distinct daily run ID. Old claims, Q0,
current import cursor and all activity survive plan changes; a second invocation,
late dispatch, weekend or old claim cannot replay that session. Same-kernel reboot
resumption is supported; changed kernel/code/configuration requires relevant review.
Subsequent runs use the existing full master and manage open trades and issues;
no strategy, ATR, sizing, protection, entry ordering or repair rule changed.

Native ordinary activation now requires a protected final packet with completed
prerequisite observations, the exact reviewed notebook record digest, A01–A16
observations and named successful offline checks, final owner authorization,
actual complete long/short/cross-currency sets, IDs/units/historical protection,
margin records, TP/scheduled stop-to-entry and targeted-close attempts, daily
financing, both-stage final run, session claims/raw broker responses, current-kernel
host evidence and traded dashboard comparison. References/pass flags alone fail.
Activation runs under maintenance, reconciles a fresh A0, requires no remaining
trades/orders or unresolved activity, and commits atomically. Repetition preserves
A0 and its review. Ordinary dispatch requires that committed record and shares the
daily replay guard; it does not archive ordinary candles. Neither the new code nor
any check grants real ordinary authorization.

**Verification.** All **460 offline tests passed** in the isolated M10 source (33
new checks); the final log records the measured duration.
The prepared wheel matched all **43 application/strategy/resource files** and
imported the new modules successfully from an isolated extracted package. Final
read-only host inspection at **20 November 14:48 Melbourne** confirmed the dated
timer still waiting, ordinary scheduling disabled, synchronized clock and all
three dashboard ports listening. Test/package/document results and source identities
are retained in
[verification.json](../var/prepared/m10-automatic/var/verification/m10-automatic/verification.json) and its
linked logs. The new cases cover recurring idle sessions, later TP/stop management,
uncertain-stop non-retry, legacy/transition-day claims, DST/weekend/late launches,
scoped authority, same-kernel reboot and kernel changes, two-timer exclusion,
wrong/missing/stale/fixture evidence, final window gaps/intervention, native A0
failure/atomicity/repetition, and ordinary dispatch after activation. All broker,
service and activation successes in these tests are **offline fixtures**, not
actual OANDA execution or deployed automatic-schedule verification.

**Concurrent-work isolation.** During final verification, another chat began
changing dashboard code/templates and tests. The owner answered **"Yes—keep the
M10 deployment separate"**. That work was preserved in the shared checkout. M10
now has a frozen source folder at
`/home/codexdev/projects/nnfx-practice-lab/var/prepared/m10-automatic`, containing
only M10 changes and the prior installed dashboard. Dashboard files match the
retained M09 source hashes exactly; its original test file was recovered in the
bundle and verified against its recorded hash. The shared file was not reverted.
Intermediate verification affected by the concurrent edits is retained; final
verification and deployment use this isolated source. The two extra final checks
cover revocation during fresh A0 reads and rejection of simulated activation.

**Concrete handoff.** The [single migration command](../README.md#deploy-automatic-qualification-once)
uses a verified prebuilt wheel because the installed environment has pip but lacks
setuptools/wheel. Installation needs no package-index access or dependency changes.
It checks the exact existing protected plan, archives it with prior code/timer/policy,
excludes the controller, stops the dated trigger and preserves notebook/sidecar/
claim bytes and metadata. It installs the application and qualification timer,
runs updated broker-free system fixtures, then enables only the regular qualifier.
An active controller, imminent trading window, changed plan or failed check defers
or stops deployment. Failures retain evidence and leave scheduling stopped for
inspection; no automatic rollback/replay or history deletion occurs.

The [new collector](../tests/collect_m10_automatic.py) exports existing notebook,
claims and raw execution evidence without broker/control actions and independently
of the final host observer. It also retains claims with no run row. This replaces
the no-entry-only continuation workflow for future regular qualification sessions.
The [README](../README.md#automatic-m10-qualification-and-ordinary-activation)
documents deployment, collection, evidence schema and future gated activation.

**Not performed.** No sudo command was retried, host package deployed, plan replaced,
timer changed, notebook written, A0 initialized or broker request made in this turn.
The agent's known host sudo denial remains the reason for the administrator handoff;
no permission bypass was attempted. The old dated session stays armed until the
owner runs the reviewed migration. Actual deployment/system receipts and future
signal-dependent execution are pending. The earlier -43 essential controls and
startup pass remain valid for their observed versions; the migration tests changed
code and dual-timer controls for a concrete reason. Unrelated final observer or
traded-dashboard checks do not block initial qualification.

### Approved M10-only deployment attempt

On **20 November 2026 (Melbourne)**, the owner requested deployment of the prepared
changes while excluding the dashboard update in the other chat. The frozen M10
package passed its source, wheel and 460-test-log integrity checks again. All seven
dashboard files matched the installed version. The dashboard remained active with
PID `11104`; the controller was idle and ordinary scheduling was disabled.

The exact prepared migration was attempted once using `sudo -n`. Host sudo policy
denied `codexdev`, exit 1, **before Python or the migration started**. This was a
host access denial, not a failed migration or an automatic approval-review
rejection. No deployment receipt was created and no application, plan, timer,
notebook or broker state was changed. The frozen bundle and concurrent dashboard
work were preserved. The [attempt record](../var/verification/m10-deployment-attempt-20261120.json)
retains the command, denial and subsequent service observations.

The post-attempt check confirmed the original dated timer still waiting for
**21 November 08:50 Melbourne**, no recurring qualification timer installed, the
ordinary timer disabled/inactive and the same dashboard process running. The
remaining deployment step requires the existing serveradmin terminal; M10-only
deployment approval does not authorize ordinary activation or waive qualification.

### Verified M10 automatic qualification deployment

After the owner ran the command, read-only verification on **20 November 2026,
15:10 Melbourne** confirmed successful migration. Receipt
`m10-automatic-ebcd02e60445` reports `status: armed`, `files_preserved: true`, zero
broker requests and no ordinary activation. Its updated broker-free system report
passes dispatch, no restart/catch-up/overlap, independent dual-timer maintenance
restoration (four cases), dashboard isolation/WAL and notebook-file preservation,
with no cleanup errors.

The [verification record](../var/verification/m10-deployed-20261120/verification.json)
links the receipt and system report by hash. All 43 installed source/package files
match the isolated M10 artifact, and the installed controller/dashboard units and
new qualification timer match the prepared definitions. The seven dashboard files
retain their prior hashes in both installed locations. The dashboard continues with
the same PID `11104` and original start time; `/controllers`, `/notebooks` and
`/notebooks/notebook-a` on 8879 each return HTTP 200. The sibling dashboard ports
8877/8878 retain their prior listening addresses; no sibling service was changed.

Live `nnfx-practice-qualification@practice-a.timer` is `enabled/active/waiting`,
targets the original controller and uses `Mon..Fri *-*-* 16:50:00 America/New_York`,
one-second accuracy, no random delay and no persistence. Its next expiry is
**21 November 08:50 Melbourne / 20 November 16:50 New York**. The dated timer is
inactive with no next expiry. The ordinary timer is disabled/inactive with no
pending job, and the controller is idle with `Restart=no`.

The receipt's before/after notebook summaries agree exactly: existing Q0 and
cursor `2249`, one prior no-entry run, no trades/attempts/fills/issues and no A0.
The migration verified unchanged notebook/sidecar/claim bytes and metadata. This
turn performed only read-only host/package/page checks and local documentation
updates. It did not rerun deployment, change controls, contact OANDA or read private
credentials. Scheduled signal-dependent execution and final activation acceptance
remain pending; successful deployment does not complete M10.

## Python 02

On **27 November 2026**, the owner requested an additional independent test named
**Python 02**, using research result `a83ffe21-90eb-4674-99e3-7c80d6871a6c` and the
attached native-v20 AUD practice account named Python 2, ending 003. The owner
confirmed **OANDA Australia Pty Ltd**. Trading criteria and operating rules remain
unchanged. [Setup and deployment order](PYTHON_02.md) records the binding and
integration boundary; the versioned manifest owns the indicator definitions.

**Implementation.** `practice-b` / `notebook-b` uses Distributional Rank Momentum
(`BullishFlip` / `BearishFlip`) and L2 Ehlers Adaptive BandPass (`doLongExit` /
`doShortExit` with the accepted opposite-position mapping). Both saved conversions
and their exact Pine dependency are packaged locally. Explicit strategy selection
replaces Python 01-specific assumptions in management, entry, lifecycle and
qualification checks. Each binding still requires its immutable packaged manifest
and exact qualified count. Python 01's strategy files and manifest are unchanged.

**Archived qualification passed.** All output series and sizing ATR match the
archived four-pair result and original code. The **512-candle** window has zero
current/prior signal mismatches across **6,244 rolling windows** and **144 modified
partial-candle snapshots**. The [packaged report](../strategies/drm_adaptive_bandpass_v1/qualification.json)
and [reproducible comparison](../tests/check_python02_reference.py) retain the
scope. This is offline calculation evidence, not broker execution qualification.

**Account preflight passed.** The existing private token can access the specified
account. Read-only OANDA evidence confirms its name/currency, exact balance
**AUD 50,000.6603**, zero open trades and pending orders, all 28 instrument
definitions and required pricing/conversion coverage. Division confirmation is
owner evidence, distinct from the API response. The redacted
[account report](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/account-preflight.json)
is retained on USB. No order or account mutation was submitted.

**Prepared artifacts.** The USB [development notebook record](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/prepared-notebook.json)
confirms `practice-b`, `notebook-b`, AUD, the 512-candle strategy and SQLite integrity
`ok`; Q0 and activation are unset. Its connection file is owner-only. The
[wheel check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/package-check.json)
verifies all **60 application/resource files** and isolated imports of both
strategies at their respective 386/512 counts. Source, wheel, notebook and
verification data are separate under the mounted USB drive. The existing
checkout is on the new branch; unrelated documentation edits were preserved.

**Controller verification passed.** The [16 focused checks](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/final-tests.log)
cover both strategy manifests, exact windows, fresh-event and Exit direction
semantics, two-leg entry and subsequent opposite Exit, separate notebooks and
dashboard pages, Python 01 regression behavior and account/strategy qualification
gates. The [nine deployment/setup checks](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/deployment-tests.log)
cover registry/private-binding preservation, existing plan replay identities,
administrator refusal, next-weekday/DST scheduling, failed candle coverage,
initialization failure and non-replay. These are offline fixtures. A preliminary
test correctly rejected a reused fixture's account-A transactions for account B;
the fixture was corrected before the passing run. The interrupted broader
preliminary run is not claimed as an all-passing suite.

**Administrator installation completed.** The owner ran the
[read-only inspector](../deploy/inspect_python02_host.py), then the frozen
[scoped installer](../deploy/add_python02.py). Administrator execution was needed
because `codexdev` has only the dashboard-deployment sudo grant. The
[inspection](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/host-inspection.json)
captured the original protected Python 01 plan and notebook identities. The
[deployment receipt](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/python02-618a04984fb7-deployment.json)
confirms the installed shared application, separate native Python 02 notebook,
private binding and scheduled setup job. Python 01's notebook/sidecar/claim
files were preserved. Its protected plan retains its original schedule and
replay identity with updated code/configuration and host-control evidence;
its qualification timer is enabled, active and waiting. Deployment made no
broker requests and did not initialize Python 02's Q0 or start a trading run.

**Native and live verification passed at 22:14 Melbourne / 11:14 UTC.** The
[actual system-control fixtures](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/python02-618a04984fb7-system.json)
passed with existing notebook files preserved and no cleanup errors. The owner
restarted the observational dashboard to load the new registry. All four live
Controllers, Notebooks and individual notebook pages return HTTP 200; Python 02
shows its own selected indicators and an unrecorded Q0. Its private HTTPS
notebook page also returns HTTP 200 with normal certificate validation. The
[independent verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/post-deployment-check.json)
matches all **60 application/resource files** across working source, installed
source and installed package, and the installed bootstrap matches the frozen
release. Both controllers are idle; both ordinary timers remain disabled.
The source installer now includes the dashboard restart; the frozen executed
release and original deployment receipt remain unchanged. The
[final nine setup checks](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/final-setup-checks.log)
passed again after that addition.

**Scheduled initialization remains pending.** The one-time setup timer is
enabled, active and waiting for **28 November 08:50 Melbourne / 27 November
21:50 UTC**. It captures Python 02's own weekday **16:50 New York** 28-pair candle
evidence. Only a pass and a fresh clear account snapshot can proceed through
guarded Q0 initialization and enable the protected automatic qualification plan.
The first regular Python 02 qualification run would then be **1 December
08:50 Melbourne / 30 November 21:50 UTC**. The job never invokes a trading run
in the capture window and refuses to repeat an attempted setup. On failure,
inspect its protected `bootstrap-receipt.json` before any recovery.

Python 02's qualification timer is currently disabled, with Q0 and activation
unset. The screenshot balance was not used as Q0. Neither scheduled candle
coverage nor actual Python 02 trading execution has been claimed as verified.
Python 01's qualification continues under its existing rules. Do not rerun the
installer or manually invoke the one-time setup ahead of its scheduled window.

## Python 03

On **27 November 2026**, the owner requested **Python 03**, using research result
`18771091-9f76-4daf-bee9-a23f28634bae` and the attached native-v20 AUD account
named Python 3, ending 002. Existing OANDA details, trading rules and criteria
continue. The proposed `practice-c` / `notebook-c` binding and exact selected
confluence C1 / opposite-position Exit events are recorded in
[setup](PYTHON_03.md). No production controller or notebook has been added yet.

**Account preflight passed.** Read-only intended-account OANDA responses confirm
the alias and AUD currency, balance **50,000.9696**, no open trades or pending
orders, and all 28 instrument/pricing/conversion checks. The division is retained
from the owner's instruction that OANDA details remain the same, separately
from API evidence. The [account report](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/account-preflight.json)
is on USB. This balance is not Q0, and no order or account mutation was sent.

**Calculation investigation.** Both conversions and each role's exact registered
Pine dependency are frozen with import-path changes only. All archived output
series and sizing ATR match the saved four-pair result exactly. The C1 dependency
is an earlier version than Exit's, so they are deliberately separate. The
[reference check](../tests/check_python03_reference.py) verifies artifact and
dataset identities, original calculations, rolling current/prior event operands,
sizing ATR and modified partial snapshots.

Rolling counts 512, 1,024 and 1,536 failed sampled checks; the exhaustive
[1,792-candle check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/reference-1792.json)
also found Exit differences. The [1,972-candle archived check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/reference-1972.json)
passed all 404 available windows and 12 partial snapshots, but leaves only 101
comparison endpoints per pair. A larger sample was therefore required before
claiming qualification.

Read-only OANDA history retrieval retained 6,000 daily candles for each of the
four research pairs. On these identical inputs, original and packaged outputs
still agree exactly. However, the [1,972-candle extended check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-1972-probe.json)
found three EUR-GBP Exit mismatches across 508 sampled windows. A sampled
[5,000-candle check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-5000-probe.json)
passed 132 windows and 12 modified partial snapshots, but the subsequent
[exhaustive check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-5000.json)
found one missed EUR-USD Exit event, visible in the current/prior comparisons on
20 and 21 March 2023. These are offline calculations using retained market data,
not scheduled 16:50 candle coverage or actual trading execution.

**History support authorized.** The owner requested continuing with this exact
combination and extending history handling while preserving indicators, signals,
sizing and trading rules. The implementation pins the research first candle,
**1 January 2013 at 22:00 UTC**, within each 5,000-candle capture. It retains the
weekday history from that origin rather than resetting at a moving boundary.
Missing origin fails capture. Completed Friday/Saturday-start bars from OANDA's
older history are excluded, with the count recorded; strict current-candle and
OHLC validation remains. This normalization reproduces the archived **8,288
research timestamps and OHLC rows exactly** across all four pairs.
The [brief](../PROJECT_BRIEF.md#strategy-selection) owns the accepted history
rule; the manifest owns the exact origin and count. No schema migration or
persistent candle/indicator store is added.

All [28 intended-account history checks](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-availability.json)
passed with the required origin present. This was a daytime availability check,
not the required scheduled partial-candle qualification. The
[final normalized comparison](../strategies/eye_age_supertrend_v1/qualification.json)
passed **11,256 endpoints and 156 partial snapshots**. The initial 40 focused
checks and the [13 history/deployment/bootstrap guards](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/deployment-tests.log)
passed. The [42 final source checks](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/final-tests.log)
then passed in 431.407 seconds, including the normalized capture, missing-origin
entry block, both C1 directions, opposite-position Exit mapping, two-leg entry and
close, all three notebook views, existing Python 02 behavior and independent
qualification evidence. These are offline broker/service fixtures.

The [package check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/package-check.json)
matches all **72 application/resource files** and imports all three strategies
from the extracted wheel at 386/512/5,000 candles. The
[final development notebook](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/prepared-notebook.json)
has the qualified manifest, SQLite integrity `ok`, and Q0/activation unset.
Its rendered notebook page returns 200 with both selected indicators. The earlier
development notebook is retained separately under `preliminary-prepared`;
immutable bindings were not overwritten. Build tools were copied to a separate
USB directory and used directly without dependency downloads; preliminary
frontend invocations failed because that optional frontend is absent on the host.

The frozen release is ready for administrator installation; production is still
unchanged. Private candidate configuration and all development evidence are on USB
under `/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/`. Development
uses the existing checkout on `codex/python-03`, with no new worktree. Existing
documentation work was preserved.

**Deployment dependency.** The live login has only the scoped dashboard-deploy
sudo grant. Trading installation requires the administrator terminal. Python 02
has a pending one-time setup at **28 November 08:50 Melbourne**; shared-code and
registry changes must preserve that job and refresh its protected context as well
as Python 01's protected plan. The Python 02-only installer cannot add this third
experiment. No existing timer, protected plan, production notebook or dashboard
has been changed by this preparation.


## Next work

Review the [Python 02 scheduled setup result](#python-02) after 28 November
08:50 Melbourne, before its first possible regular qualification run on
1 December. Preserve any failed setup evidence and resolve it before retrying.

**Owner operating plan, agreed 20 November 2026.** Leave automatic qualification
running. The owner will check the dashboard **Tuesday–Saturday at 09:30 Melbourne**
for completed runs, refreshed/reconciled figures and unresolved errors, addressing
problems promptly. Automatic alerting is deferred in favour of those manual checks.
Review performance and M10 evidence together on **27 November 2026**. This records
the intended review date; no automated reminder or monitoring task was scheduled.

The owner prefers continuous performance from the original Q0 baseline, with
qualification completion recorded as a milestone. That lifecycle/reporting
simplification has been discussed but is not implemented. Current qualification
already accumulates results from Q0; keep it running and revisit the future
transition rules before any ordinary activation. Existing execution checks and
operator handling of unresolved issues remain in force.

Address the [21 November transaction-import failure](#transaction-import-failure-on-21-november)
before the next regular qualification run, **24 November 08:50 Melbourne /
23 November 16:50 New York**. Deploy the reviewed correction and handle the
existing incomplete entry through the normal operator process; no daily arming
is needed.
Do not rerun the full installer, migration, initial one-shot armer or no-entry
continuation, delete protection records, reset Q0, or manually invoke a trading run.

Let the unchanged strategy supply eligible signals and the same controller manage
trades on subsequent weekday qualification runs. Collect
actual fills/IDs/units/protection, TP and scheduled stop-to-entry, targeted closes,
restrictions/margin, reconciliation and financing/charge evidence. Preserve failures;
operator disposition remains required and any broker incompatibility or proposed
strategy/unit change returns to review. There is no daily administrator arming.

Retain the completed -43 startup proof. Inspect existing observer evidence before
preparing a matching current-kernel unattended window; preserve the old -42 scope.
Complete the traded dashboard and A01–A16 final review. Only after qualification,
clear qualification trades/orders/issues, protect the actual reviewed packet, obtain
final ordinary authority and reconcile fresh A0 under maintenance. Then, separately,
enable ordinary scheduling. Do not claim M10 complete before those outcomes exist.
[Approved implementation plan](IMPLEMENTATION_PLAN.md)
