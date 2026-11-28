# Retained verification references

Dated evidence; [status](STATUS.md) owns operation, [acceptance](ACCEPTANCE.md) scenarios.
Dates are Melbourne unless marked UTC. Local/private evidence may need USB/admin
access and grants no execution authority. Preserve raw reports, failed attempts,
frozen releases and backups; [completed procedures](OPERATIONS.md#completed-procedures-are-not-retries)
are not retries. Earlier digests/narrative remain at `a89e452:docs/STATUS.md`.

## Approved decisions and offline milestones

Brief finalised 10 November; architecture refined 15 November; design/plan approved
16 November. Design fixes retained exact windows, failed-attempt guards, maintenance
exclusion and snapshot-aligned totals; plan fixes retained the wholly-no-fill
exception, Q0/A0 atomic lifecycle and former initial/final M10 split.
M09 deployment approval: [19 November record](../var/verification/m09-approval/approval.json).
[Python 01 execution authority](../var/verification/m10-authority/authorization.json)
is conditional on prerequisites and does not authorize ordinary activation.
20 November recurring-qualification instruction superseded daily arming.

Historical offline counts, original dependencies and report links are consolidated
in the [delivery history](IMPLEMENTATION_PLAN.md#delivery-history). Those results
apply to their recorded revisions and do not establish account execution.

## Strategy comparisons

Python 01 selected 18 November: result `a3d408b1-b645-4b38-b3cd-a423e5c8d4a9`, lab
commit `40e27cfabb4130702716ec1e41db7fbbf6e0f404`, STD-Adaptive T3 C1 (`goLong/goShort`)
and L2 Ehlers Bandpass Exit (`longEntry` closes shorts, `shortEntry` closes longs).
[Manifest](../strategies/t3_bandpass_v1/manifest.json) owns exact settings; its canonical
hash is retained in the account/candle reports below.
All outputs/ATR matched 8,288 archived bars. Shortest tested qualifying window: 386
(6,748 endpoints, 144 modified partials matched); every count 15–385 failed an event
check. Saved conversion keeps confirmOnClose=true and evaluates barOK=true on supplied
partial input; capture records it as partial.
[Summary](../strategies/t3_bandpass_v1/qualification.json),
[exhaustive sweep](../var/m03/qualified-sweep.json), [reference log](../var/m03/reference.log)
and [wheel log](../var/m03/wheel.log): 62 standard/12 explicit reference checks passed.
[Selected comparison](../tests/check_m03_selected_reference.py) needs the sibling lab's
environment/database at the expected relative path; [generic probes](../tests/check_m03_lab_reference.py)
also need the lab on PYTHONPATH.

[Python 02](PYTHON_02.md#calculation-verification) and
[Python 03](PYTHON_03.md#calculation-verification) own comparison results,
failed alternatives and reproduction inputs.

## Python 01 account and host evidence

18–19 November read-only preflight confirmed Python 01/AUD, owner-confirmed
OANDA Australia, clear account, AUD 50,000.1007, all 28 instruments/prices and
required accountLoss factors (AUD exactly 1; matching quotes GBP-AUD/EUR-AUD).
Portal said v20 netting; API hedgingEnabled=false and guaranteed-stop mode ALLOWED.
[Account pass](../var/preflight/account-2026-11-18-python-01-division.json);
separate [scheduled candle pass](../var/preflight/candles-2026-11-18-python-01.json):
19 November 08:50 Melbourne, all 28 exact 386 windows before rollover, 0.303–1.226 s
latencies. The report independently passed; only its later status-update guard
failed on concurrent prose edits.

System fixture failures/repairs: [system reports](../var/verification/m09-system)
and [path correction](../var/verification/m09-dashboard-path-fix/verification.json).
Corrected 19 November report `nnfx-m09-system-a21870b78c7d.json` passed native
controller/maintenance/dashboard sandbox/WAL checks and cleanup.
[Private binding check](../var/verification/m09-private/private-5185eb0637bf.json)
confirmed writer ownership/0600, correct binding and viewer denial without broker
access. Startup/unattended operation remained unproven.

Q0 initialized 20 November 00:43:43: [report](../var/verification/m10-initialization/m10-q0-3a24c7c4771c.json),
one GET/no mutations, snapshot `c245f517b15448cabb2edbb5336a53aa`, boundary 2249.
The [first observed qualification](../var/verification/m10-review-20261120/collected-verification.json)
at 08:50 took 14.112094281 s: 28 fresh valid captures/no C1 event,
31 successful GETs, zero mutations/sets/fills/issues. No Stage 1 survivor meant
no Stage 1 candle or execution-path evidence.
[Replay](../var/verification/m10-review-20261120/pair-replay.json) matched saved C1/ATR;
[protected collection](../var/verification/m10-review-20261120/protected-review-d9980f9a89ee.json)
retains records: Q0/balance/cursor unchanged, A0 unset.

Old kernel -42 dispatch/wakefulness passed (101 samples, max gap 15.014205 s);
four user sessions and owner's “Unsure” leave unattended context unconfirmed.
On 20 November 13:30:25, kernel **7.0.0-43** startup at uptime
15.023 s had zero user sessions: [startup verification](../var/verification/m10-post-restart/verification.json).
No repeat boot needed for that proof. Refreshed [system controls](../var/verification/m09-system/nnfx-m09-system-daed36cb06d3.json)
and [flat dashboard/LAN comparison](../var/verification/m10-dashboard-20261120/display-comparison.json)
passed; they do not establish a current-kernel unattended/traded review.

20 November receipt `m10-automatic-ebcd02e60445`: automatic qualification armed,
43 files matched, notebook/claims preserved, clean dual-timer host fixtures,
no broker request/A0: [deployment verification](../var/verification/m10-deployed-20261120/verification.json).
Only qualification scheduling remained enabled; the dated trigger stopped.
Retain [preparation/arming records](../var/verification/m10-arming).

## Python 02 and Python 03 scheduled setup verification

**Observed 28 November 09:38–09:39 Melbourne / 27 November 22:38–22:39 UTC.**
Read-only live service properties/saved dashboard: both setup services had
Result=success, ExecMainCode=1 (normal exit), ExecMainStatus=0.

| Controller | Setup start → finish (28 Nov Melbourne) | Q0 AUD | Transaction |
| --- | --- | ---: | --- |
| Python 02 | 08:50:00 → 08:50:12 | 50,000.6603 | 773 |
| Python 03 | 08:50:00 → 08:50:22 | 50,000.9696 | 1662 |

Notebook Q0 records: `a71bc581a216485283d4b47bad7554ab` and
`21dd5295531e47bd8aaa197ce2990f8d`, refreshed respectively at 27 November
21:50:11.044964 and 21:50:21.302247 UTC. Port 8879 notebook GETs: 200, those balances,
no trade records/mutation requests/issues, ordinary activation unset. Services/Q0/enabled
timers confirmed guarded initialization.
Protected candle reports/setup receipts were **not reopened**; journal unreadable
to this login. Original notes cite no standalone observation export.

Python 02/03 qualification timers were enabled/active/waiting; all three shared the
next expiry: **Tuesday 1 December 08:50 Melbourne / 30 November 21:50 UTC**.
All three ordinary timers were disabled/inactive without expiry. Python 02/03 had
no trading-service start or previous qualification-timer trigger. Setup checks
candles/initializes Q0 without trading, explaining “No runs recorded”. This check
reran no setup, triggered no trading, changed no files/schedules and sent no broker
requests.

## GBP-CAD incident and recovery

21 November 08:50 run `m10-auto-bfeea7da7de9-20261120` failed after 16/28 entry
checks. Order 2250 opened short trade/fill 2251, 42,665 units at 1.87722; broker stop
2252 was 1.88824. No target/Trade 2 was sent. History added five zero conversion
fields, triggering strict comparison and rolling import back to 2249. The
[original export](../var/verification/m10-automatic-collections/collection-c100b2e47ec0/progress.json)
and [broader exact replay](../var/verification/transaction-import-broader-20261121/replay-result.json)
retain facts. Owner agreed field-aware comparison; 520-test broader fix merged
as `5664c32`; 49-file package verification in the [same directory](../var/verification/transaction-import-broader-20261121).
Retain the [505-test precursor](../var/verification/transaction-import-20261121).

Collector's initial hash failure lacked per-file diagnostics; the difference remains
unknown. Reading copied DB/WAL avoids changing original SHM read marks. Four focused
checks passed; corrected collection preserved all three source files and left
frozen migration artifacts unchanged.

Later account reads returned HTTP 520, then public unauthenticated 401; authenticated
21 November read returned 503 “System under maintenance”. This confirms maintenance
for that read, without proving the cause of all prior 520s.
[Investigation](../var/verification/oanda-520-investigation-20261121),
[22 November recovered read](../var/verification/oanda-maintenance-recheck-20261122/probe-084931.json)
and [close-helper attempts](../var/verification/operator-close-2251) retain failures,
identity repair, 24 offline helper checks and market-closed skips without mutations.
The combined publication suite passed 544; publication was not runtime deployment.

23 November 11:04:13 administrator close sent one durably claimed request: order
2256/fill 2257/cancellation 2258. Post-close trade GET returned 404; matching fill
and fresh account independently proved closure, not 404 alone.
[Close verification](../var/verification/operator-close-2251/postclose-20261123T000525Z/verification.json)
confirms all 42,665 units at 1.87819, -9.7 pips, AUD -43.8956; financing separate.
Preserve the claim.

Owner funding 2259 was +50.03 cash, not trading profit. Closing fill's matching
-0.42844810179192 P/L conversion disclosures were included in posted P/L;
`49993.8688 - 43.8956 = 49949.9732` independently reconciled. Only this qualified
single-close nonzero shape was accepted; other shapes remain blocked.
[Rehearsal and 555-test evidence](../var/verification/operator-reconcile-2251) preserve
schema migration/disposition checks. Final preparation reached 566 offline tests;
permission repair addressed 98 public paths without private-file changes.

23 November 21:01:29 [recovery receipt](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/result.json)
and [native controls](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/controller-controls.json)
confirm schema 3 through 2259, leg 1 closed, leg 2 not_opened/unsent, issue disposed,
Q0/failure/claims preserved, clean fixtures and restored qualification schedule.
21:05 [independent completion](../var/verification/operator-reconcile-2251/completed-20261123T100526Z/verification.json)
confirmed zero trades/orders/positions, AUD 50,000.0032, loss -43.8956, financing
-6.2319, funding +50.03, net -0.0975 from Q0; commission/other/unrealised zero.
A0 unset. Protected records retain both failure archives and original backup;
never roll schema 3 back to old writers.

## Dashboard releases and access

20 November layouts/history/notebook views: [deployment](../var/verification/dashboard-deployed-20261120/verification.json),
41 focused/14 deployment checks, live 320/716/1280 px review. Earlier rollback and
corrected unordered-service-settings comparison remain in the [frozen bundle](../var/prepared/dashboard-a7d756b).
Scoped deployment/wording: 68 focused offline and 12 live browser checks;
[installed permission/release verification](../var/verification/dashboard-delegation-deployed-20261120/verification.json)
confirmed only the no-argument helper grant and successful unchanged-content use.
[Tailscale completion](../var/verification/tailscale-dashboards-20261120/completion.json)
retains HTTPS 443/8443 and owner-reported access; after MagicDNS failure, local checks
used explicit DNS-to-tailnet-IP mapping with normal TLS.

26 November 23:11 Melbourne / 12:11 UTC: journal `52fe994`; 74 focused/3 targeted
checks, 12 saved rows/amounts/fills matched; live 320/390/716/1280 px checks.
[Archived evidence](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126)
retains host/data/browser receipts, logs and screenshots. Release
`dashboard-deploy-47c54274a23e09eee665c3f0` matched 47 dashboard/49 trading files,
preserving controls/restrictions without broker/notebook writes.
[Cleanup record](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/cleanup-record.json)
verified 191 artifacts before archiving/removing the worktree. Row count is dated.

Experiment installation evidence: [Python 02](PYTHON_02.md#recorded-installation-evidence)
and [Python 03](PYTHON_03.md#recorded-installation-evidence).

## Host cleanup

28 November 16:40 [completion verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/host-cleanup-20261128-ft4lhowm/completion-verification.json)
confirmed preview/obsolete M09/M10 units removed, port 8880 closed and 139 generated
build/packaging/bytecode files removed. Live identities, schedules and unit files
matched original snapshots; no reload pending; all five dashboard pages returned 200.
Administrator fingerprints preserved runtime data and all evidence, including the
collection unreadable to this login. Preview source/captures, retired unit copies
and the original failed receipt remain preserved.

## Single practice mode installation

28 November 21:50: installed for all three experiments.
[Independent verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/single-practice-mode-0oqfmwj5/evidence/final-verification.json)
matched 71 files across installed source/package/dashboard and 44 unchanged schema,
strategy, sizing, order, reconciliation and active schedule files. Native fixtures
passed with clean removal; five dashboard pages returned 200; restrictions and
narrow deployer permissions were unchanged. No broker requests or controller runs.

The administrator receipt preserved notebook/sidecar/claim/raw-capture fingerprints,
credentials and registry; protected originals remain at
`/etc/nnfx-practice/upgrades/single-mode-d82d9d8e1279`, unreadable to this login.
Independent saved-page comparisons matched all three Q0s, opening balances, account
totals and trade/ledger/request records. Dashboard restarted; reload cleared
Python 01's inactive invocation cache, preserving run history. All three timers
remained enabled/active/waiting with original calendars and next triggers
(1 December 08:50 Melbourne / 30 November 21:50 UTC).

[Offline validation](/mnt/nnfx-usb/development/data/nnfx-practice-lab/single-practice-mode-0oqfmwj5/evidence/validation.json)
retains 164 focused cases with corrected fixture reruns, upgrade guards and 40
preflight/deployment checks. Interrupted broader runs are not full-suite passes.
Failed preflight screenshot/source/partial backup remain preserved; the corrected
[procedure](OPERATIONS.md#single-practice-mode-upgrade) retains its review constraints.
