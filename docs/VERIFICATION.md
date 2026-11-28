# Retained verification references

Retained results for investigation, outside routine feature reading. [Status](STATUS.md) owns current state;
[acceptance](ACCEPTANCE.md) owns required scenarios. Dates below are Melbourne
unless UTC is explicit. Evidence paths are local/private and may require USB or
administrator access; their existence does not grant execution authority.

Raw reports, failed attempts, frozen releases and backups remain untouched.
Earlier committed source digests and superseded chronological narration remain
in Git at `a89e452:docs/STATUS.md`. Unique 28 November setup observations are retained in
[status](STATUS.md#python-02-and-python-03-scheduled-setup-verification).

## Approved decisions and offline milestones

Brief finalised 10 November, architecture refinements 15 November, detailed design
and plan approved 16 November. Design fixes retained exact windows, failed-attempt
guards, maintenance exclusion and snapshot-aligned totals. Plan fixes retained
the wholly-no-fill exception, Q0/A0 atomic lifecycle and initial/final M10 split.
M09 deployment approval is in the [19 November record](../var/verification/m09-approval/approval.json);
[Python 01 execution authority](../var/verification/m10-authority/authorization.json)
is conditional on prerequisites and does not authorize ordinary activation.
The 20 November recurring-qualification instruction superseded daily arming.

| Work / date | Retained result and source |
| --- | --- |
| M01, 16 Nov | 16 offline checks: immutable/independent bindings, pair reservation, durable intent, readonly WAL and redaction. Original digest/results are in the Git record; [fixtures](../tests/support.py). |
| M02, 17 Nov | 37 combined checks: sparse history, atomic cursor/fills/ledger, missing-leg evidence, snapshot cutoff, Q0/A0 and account isolation; [suite](../tests/test_m02.py). |
| M03 plumbing, 17 Nov | 48 checks plus 8 original-lab probes; DST/rollover, exact counts, events and ATR ties/history. Lab probe source at `cd64da9`; [reference probes](../tests/check_m03_lab_reference.py). |
| M05, 18 Nov | 102 suite/40 management checks; ordered exits, TP stops, per-leg guards and failed commits; [evidence/traces](../var/verification/m05/evidence.json), [log](../var/verification/m05/discovery.log). |
| M06, 18 Nov | 171 suite/69 entry checks; decimal sizing, establishment timing, whole rejection versus partial fill; [evidence](../var/verification/m06/evidence.json), [log](../var/verification/m06/discovery.log). |
| M07, 18 Nov | 264 suite; full workflow, reversals, Q0/A0, disposition and exclusion; [evidence/row exports](../var/verification/m07/evidence.json), [package](../var/verification/m07/package-check.json). |
| M08, 19 Nov | 294 suite/30 dashboard checks; monetary cutoff, WAL, permissions and views; [manifest/pages](../var/m08/verification.json), [visual review](../var/m08/visual-checks.json). |
| M09, 19 Nov | 319 offline tests; [manifest](../var/verification/m09/verification.json). User-manager controller probes passed but dashboard failed 218/CAPABILITIES; [report](../var/verification/m09/nnfx-m09-probe-2194936/host-results.json). Later system checks preserved security restrictions. |
| M10 integration, 19–20 Nov | Prerequisite, guarded service, initialization and arming fixtures progressed through 327/347/383/392/406 checks; [integration record](../var/verification/m10-integration/verification-final.json), [arming suite](../var/verification/m10-arming/final-suite.log). No simulated fill qualifies execution. |
| Automatic qualification, 20 Nov | 427 baseline and 460 isolated tests, 43-file wheel; [frozen verification](../var/prepared/m10-automatic/var/verification/m10-automatic/verification.json). Owner required isolation from concurrent dashboard work; frozen source remains intact. |

These counts refer to their recorded revisions, not a fresh all-checkout suite.
M01–M08 were reported ready for review; implementation/deployment does not imply
individual acceptance of every scenario. Test sources carry the controlled cases.

## Strategy comparisons

Python 01 selected 18 November: result `a3d408b1-b645-4b38-b3cd-a423e5c8d4a9`, lab
commit `40e27cfabb4130702716ec1e41db7fbbf6e0f404`, STD-Adaptive T3 C1 (`goLong/goShort`)
and L2 Ehlers Bandpass Exit (`longEntry` closes shorts, `shortEntry` closes longs).
[Manifest](../strategies/t3_bandpass_v1/manifest.json) owns exact settings; its hash
is `22a7aa2e743885ff70304f7a540324c5fe547398b91efa39ce83d71ad881f032`.
All outputs/ATR matched 8,288 archived bars. The shortest tested qualifying window,
386, matched 6,748 endpoints and 144 modified partials; every count 15–385 failed
an event check. Saved conversion keeps confirmOnClose=true and evaluates barOK=true
on supplied partial input; capture still records it as partial.
[Summary](../strategies/t3_bandpass_v1/qualification.json),
[exhaustive sweep](../var/m03/qualified-sweep.json), [reference log](../var/m03/reference.log)
and [wheel log](../var/m03/wheel.log) retain evidence. 62 standard and 12 explicit
reference checks passed. [Selected comparison](../tests/check_m03_selected_reference.py)
requires the sibling lab environment/database at its expected relative path;
[generic probes](../tests/check_m03_lab_reference.py) also need the lab on PYTHONPATH.

Python 02: all archived outputs/ATR match; 512 candles passed 6,244 windows and 144
modified partials. [Packaged summary](../strategies/drm_adaptive_bandpass_v1/qualification.json)
and [comparison tool](../tests/check_python02_reference.py) own reproducible inputs;
README entry 5 gives its command. [Setup](PYTHON_02.md) owns selection/binding.

Python 03: rolling 512/1,024/1,536/1,792 checks failed. Archived 1,972 passed
404 windows/12 partials but extended data found three EUR-GBP Exit mismatches.
A sampled 5,000 passed 132 windows/12 partials; exhaustive testing missed one
EUR-USD event (20–21 March 2023 current/prior comparison). These failures explain
the owner's fixed-origin decision; do not treat sampled passes as qualification.
[1,972 extended failure](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-1972-probe.json),
[5,000 exhaustive failure](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-5000.json)
and all shorter probes remain in the [evidence directory](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence).

Fixed-origin weekday normalization reproduces all 8,288 research timestamp/OHLC
rows exactly. The [final summary](../strategies/eye_age_supertrend_v1/qualification.json)
passes 11,256 endpoints/156 partials. [check_python03_anchored](../tests/check_python03_anchored.py)
takes `--lab`, `--inputs`, `--output`; default stride 1 is exhaustive. Inputs are
four retained `<PAIR>-extended.json` files in the [USB reference directory](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/reference).
Use the lab environment, practice checkout, USB temporary/output paths. The
[28-pair availability check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/history-availability.json)
passed, but daytime availability is not scheduled partial-candle qualification.

## Python 01 account and host evidence

18–19 November read-only preflight confirmed Python 01/AUD, owner-confirmed
OANDA Australia, clear account, AUD 50,000.1007, all 28 instruments/prices and
required accountLoss factors (AUD exactly 1; matching quotes GBP-AUD/EUR-AUD).
Portal said v20 netting; API hedgingEnabled=false and guaranteed-stop mode ALLOWED.
[Account pass](../var/preflight/account-2026-11-18-python-01-division.json) is separate
from [scheduled candle pass](../var/preflight/candles-2026-11-18-python-01.json):
19 November 08:50 Melbourne, all 28 exact 386 windows before rollover, 0.303–1.226 s
latencies. Its later status-update guard failed on concurrent prose edits; the
saved report itself passed and was independently verified (hash `ec82389c7b4a0c92127459b1c81b879a55969a6750477133ab3af053739aace1`).

System fixture failures and repairs remain in [system reports](../var/verification/m09-system)
and [path correction](../var/verification/m09-dashboard-path-fix/verification.json).
The corrected 19 November report `nnfx-m09-system-a21870b78c7d.json` passed real
controller/maintenance/dashboard sandbox/WAL checks with clean cleanup.
[Private binding check](../var/verification/m09-private/private-5185eb0637bf.json)
confirmed writer ownership/0600, correct binding and viewer denial without broker
access. These checks did not prove startup or unattended operation.

Q0 was initialized 20 November 00:43:43: [report](../var/verification/m10-initialization/m10-q0-3a24c7c4771c.json),
one GET/no mutations, snapshot `c245f517b15448cabb2edbb5336a53aa`, boundary 2249.
The [first observed qualification](../var/verification/m10-review-20261120/collected-verification.json)
at 08:50 lasted 14.112094281 s, processed 28 fresh valid captures/no C1 event,
31 successful GETs, zero mutations/sets/fills/issues. Stage 1 had no surviving pair,
so there was no Stage 1 candle or execution-path evidence.
[Replay](../var/verification/m10-review-20261120/pair-replay.json) matched saved C1/ATR;
[protected collection](../var/verification/m10-review-20261120/protected-review-d9980f9a89ee.json)
retains the actual records. Q0/balance/cursor were unchanged; A0 unset.

The old kernel -42 dispatch/wakefulness window passed (101 samples, max gap
15.014205 s) but four user sessions and the owner's “Unsure” leave unattended
context unconfirmed. On 20 November 13:30:25, kernel **7.0.0-43** startup at uptime
15.023 s had zero user sessions: [startup verification](../var/verification/m10-post-restart/verification.json).
No repeat boot is required for that proof. Refreshed [system controls](../var/verification/m09-system/nnfx-m09-system-daed36cb06d3.json)
and [flat dashboard/LAN comparison](../var/verification/m10-dashboard-20261120/display-comparison.json)
passed; they do not replace the remaining current-kernel unattended/traded review.

20 November automatic qualification deployment receipt `m10-automatic-ebcd02e60445`
reported armed, 43 files matched, notebook/claims preserved, clean dual-timer host
fixtures and no broker request/A0: [deployment verification](../var/verification/m10-deployed-20261120/verification.json).
Old dated trigger stopped; only qualification scheduling enabled. Historical
[preparation/arming records](../var/verification/m10-arming) remain, not retry instructions.

## GBP-CAD incident and recovery

21 November 08:50 run `m10-auto-bfeea7da7de9-20261120` failed after 16/28 entry
checks. Order 2250 opened short trade/fill 2251, 42,665 units at 1.87722; broker stop
2252 was 1.88824. No target/Trade 2 was sent. History added five zero conversion
fields, triggering strict comparison and rolling import back to 2249. The
[original export](../var/verification/m10-automatic-collections/collection-c100b2e47ec0/progress.json)
and [broader exact replay](../var/verification/transaction-import-broader-20261121/replay-result.json)
retain facts. Owner agreed field-aware comparison; 520-test broader fix merged
as `5664c32`, with 49-file package verification in the [same directory](../var/verification/transaction-import-broader-20261121).
The [505-test precursor](../var/verification/transaction-import-20261121) remains.

Collector initially failed an all-file hash check without per-file diagnostics;
its exact difference is unknown. A copied DB/WAL read avoids possible SHM read-mark
changes. Four focused checks passed; the corrected actual collection preserved
all three source files. Frozen migration artifacts were not rewritten.

Later account reads returned HTTP 520, then public unauthenticated 401 while an
actual authenticated 21 November read returned 503 “System under maintenance”.
Maintenance is confirmed for that read, not a proven cause of all prior 520s.
[Investigation](../var/verification/oanda-520-investigation-20261121),
[22 November recovered read](../var/verification/oanda-maintenance-recheck-20261122/probe-084931.json)
and [close-helper attempts](../var/verification/operator-close-2251) preserve failures,
identity repair, 24 offline helper checks and market-closed skips without mutations.
The combined publication suite passed 544; publication was not runtime deployment.

23 November 11:04:13 administrator close sent one durably claimed request: order
2256/fill 2257/cancellation 2258. Post-close trade GET returned 404; matching fill
and fresh account independently established closure, not 404 alone. The
[close verification](../var/verification/operator-close-2251/postclose-20261123T000525Z/verification.json)
confirms all 42,665 units at 1.87819, -9.7 pips, AUD -43.8956; financing remained
separate. Retain the claim to prevent another close.

Owner funding 2259 was +50.03 cash, not trading profit. Closing fill's matching
-0.42844810179192 P/L conversion disclosures were already included in posted P/L;
`49993.8688 - 43.8956 = 49949.9732` independently reconciled. Only this qualified
single-close nonzero shape was accepted; other shapes remain blocked.
[Rehearsal and 555-test evidence](../var/verification/operator-reconcile-2251) preserve
schema migration/disposition checks. Final preparation reached 566 offline tests;
permission repair addressed 98 public paths without private-file changes.

23 November 21:01:29 [recovery receipt](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/result.json)
and [native controls](../var/prepared/gbpcad-reconciliation-permissions-20261123/var/verification/gbpcad-continue-b21faed3edcb/controller-controls.json)
confirm schema 3 through 2259, leg 1 closed, leg 2 not_opened/unsent, issue disposed,
Q0/failure/claims preserved, clean fixtures and restored qualification schedule.
[Independent completion](../var/verification/operator-reconcile-2251/completed-20261123T100526Z/verification.json)
confirmed zero trades/orders/positions, AUD 50,000.0032, loss -43.8956, financing
-6.2319, funding +50.03, net -0.0975 from Q0; commission/other/unrealised zero.
A0 stayed unset. Both failure archives and original backup remain in protected
recovery records; do not replay incident helpers or roll schema 3 back to old writers.

## Dashboard releases and access

20 November layouts/history/notebook views: [deployment](../var/verification/dashboard-deployed-20261120/verification.json),
41 focused/14 deployment checks, live 320/716/1280 px review. Earlier rollback and
corrected unordered-service-settings comparison remain in the [frozen bundle](../var/prepared/dashboard-a7d756b).
Scoped deployment/wording: 68 focused offline and 12 live browser checks;
[installed permission/release verification](../var/verification/dashboard-delegation-deployed-20261120/verification.json)
confirmed only the no-argument helper grant and successful unchanged-content use.
[Tailscale completion](../var/verification/tailscale-dashboards-20261120/completion.json)
retains HTTPS 443/8443 and owner-reported access; local verification used an explicit
DNS-to-tailnet-IP mapping with normal TLS after MagicDNS failure.

26 November 23:11 Melbourne / 12:11 UTC journal deployment includes the closed-
protection presentation correction `52fe994`, 74 focused plus 3 targeted checks,
12 saved trade rows/all amounts/fills matched and live 320/390/716/1280 px checks.
[Archived evidence](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/var/verification/journal-production-20261126)
contains final-host-verification.json, live-data-checks.json, browser-checks.json,
logs and screenshots. Receipt `20261126T121104461876.json`, release
`dashboard-deploy-47c54274a23e09eee665c3f0`, matched 47 dashboard files and preserved
49 qualified trading files, controls and restrictions. No broker/notebook write.
[Cleanup record](/mnt/nnfx-usb/development/archives/nnfx-practice-lab/deploy-journal-20261126/cleanup-record.json)
verified all 191 artifact files before archiving/removing the merged worktree.
The 12 rows are a dated count.

Python 02/03 installation, package and native-host evidence is retained with
their experiment-specific [Python 02](PYTHON_02.md#recorded-installation-evidence)
and [Python 03](PYTHON_03.md#recorded-installation-evidence) integration records.
