# Host operations and authority

This document owns maintained host procedures and protected-review fields formerly
mixed into the README/design. [Status](STATUS.md) records dated observations;
[verification](VERIFICATION.md) links receipts. Procedures are not evidence that an
action ran or new authorization to trade. Development commands are in the
[README](../README.md#development-and-verification).

## Installed layout and scheduling

The standalone deployment uses root-owned `/opt/nnfx-practice` code/venv and
`/var/lib/nnfx-practice` registry, copied manifests, private `.env` and notebook data.
It does not depend on this checkout or the research lab. Python 3.12+, SQLite with
`SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`, New York tzdata, systemd and administrator
installation are required. Ubuntu's matching `python3-venv` provides ensurepip;
the original host needed `python3.14-venv`. Do not repeat its completed install.

Non-login `nnfx-run:nnfx-read` writes; `nnfx-view:nnfx-read` only reads. Executables
are root-owned. Notebook directory mode is 2750, DB/WAL/SHM 0640; private `.env`
is writer-owned 0600. `NNFX_NOTEBOOK_READ_GROUP=nnfx-read` enforces shared-reader
permissions; local notebooks remain private without it. Shared writers retain
WAL/SHM on close with NO_CKPT_ON_CLOSE; normal WAL autocheckpointing continues.

Each `nnfx-practice@<controller>.service` is oneshot, `Restart=no`, with no startup
timeout. Ordinary and qualification timer templates both target that single
service. Their calendar is `Mon..Fri *-*-* 16:50:00 America/New_York`,
`AccuracySec=1s`, `RandomizedDelaySec=0`, `Persistent=false`. Timer accuracy is not
a promise of exact Python start time. System services/timers use multi-user/timers
targets without interactive login. A paused timer never replays missed launches.

Qualification validates protected authority/account/strategy/code/configuration,
clock and process identity, and claims the New York date durably before network
activity. Ordinary requires separate activation/review. A same-kernel reboot can
resume version-2 qualification; changed kernel/code/configuration needs relevant
matching evidence. Keep earlier observations scoped to their actual versions.

The Waitress dashboard uses port 8879 and `/opt/nnfx-dashboard/current`; preserve
research listeners 8877/8878. Runtime has read-only files, no credentials,
systemctl/sudo/system-bus access or outbound connect calls, and no trading routes.
It sees committed WAL records. Trusted-LAN/firewall and tailnet restrictions remain;
[README access](../README.md#dashboard-access) owns client addresses. Old local
preview port 8880 never received the proposed production snapshot/HTTPS 8444;
its internal-storage snapshot setup is retired. New development data requires USB.

## Maintenance and evidence collection

Use the same notebook exclusion lock as the master. For initialization,
disposition or activation, pause both qualification and ordinary timers, preserving
their prior states independently; runtime-mask the exact controller service and
require inactive/failed state with no pending launch before any broker read or
notebook write. Busy lock, unstable timer, mask failure, active service or pending
job defers maintenance. Never stop a running controller to make it proceed.

Hold exclusion through reads, writes, notebook close, removal of only the operation's
own mask and timer restoration. Initially paused stays paused; restoration never
enables a timer at boot. Failures remain visible; unmask failure leaves schedules
stopped. Abrupt death can leave a runtime mask/stopped timers. Before operator
recovery, establish process exit, released notebook and inactive service/no jobs;
review the retained failure and restore only recorded prior state. No automatic
recovery or retry of uncertain mutations.

The [host adapter](../nnfx_practice/host.py) exposes `disposition` with controller,
`--issue-id`, `--operator-id`, `--explanation` and deployed `--root`. Run under
`nnfx-run` with its read-group setting and the installed interpreter. It reconciles
using account-scoped GET authority and records one evidenced disposition, without
orders or initialization of a missing notebook. [Design](DETAILED_DESIGN.md#failure-and-disposition)
owns what proof may resolve an issue. Dashboard controls cannot perform maintenance.

For backups use SQLite's backup facilities under an appropriate exclusion boundary;
never copy a DB alone while its WAL contains commits. The administrator
[qualification collector](../tests/collect_m10_automatic.py) instead holds the
controller lock, copies DB/WAL to a private temporary directory and reads that copy.
Even SQLite mode=ro can update writable original SHM read marks. The collector
records before/after hashes, distinguishes SHM from DB/WAL changes and preserves
an inspectable failure export. It reads no original notebook with SQLite and sends
no broker/control action. It exports records, source variants, raw captures and
all date claims, including claims without run rows; collection never grants acceptance.

Its CLI requires administrator access and accepts a new `--output` directory.
Choose a unique path under the mounted USB task evidence directory, including its
temporary copy; output is private and becomes checkout-owner-readable. **The CLI
currently collects `practice-a` only**; it has no controller selector. Supporting
Python 02/03 collection needs separate tooling work. Use current reviewed source,
not the frozen migration bundle's older collector. Never reset Q0 or delete claims.

## Host checks and unattended evidence

[check_m09_system.py](../tests/check_m09_system.py) is the administrator, installed-
interpreter broker-free probe. `--preserve-existing-notebooks` is required on this
populated deployment; it compares actual notebook/sidecar bytes and metadata
without opening or repairing them. It creates separately named synthetic units,
notebooks under `/var/lib/nnfx-practice/var/verification/<fixture-prefix>` and worker
copies under `/opt/nnfx-practice/verification/<fixture-prefix>`. Actual credential
and notebook paths are denied to fixtures. Use `--output` for a new USB report.
Native host fixture paths are part of this probe, not ordinary development storage.

The probe covers real writer dispatch, no overlap/restart/catch-up, independent
controllers, maintenance read/write exclusion and prior-state restoration, viewer
sandbox and WAL visibility during/after writes. Cleanup removes temporary units
and exact-unit grants; any cleanup error fails the check. Success requires
`fixture_checks_passed=true`, no error/cleanup errors and preserved actual files.
It deliberately does not claim full host qualification, private provisioning,
startup, unattended window or traded dashboard agreement.

[check_m10_prerequisites.py](../tests/check_m10_prerequisites.py) is read-only host
inspection, not a fixture or execution pass. It fixes its output to the source
checkout's `var/verification/m10`; `--output` cannot redirect outside that directory.
Run it from a reviewed USB checkout if needed. Do not repeat its old internal-
storage command; broader output support is a separate tooling follow-up. The
older user-systemd probe cannot replace actual system-manager verification.

The [observer](../tests/check_m09_observation.py) stages isolated boot/dispatch/
heartbeat units; it does not reboot, change power policy or start trading. Inspect
existing metadata, units and rows before preparing another window. Its report
requires known zero-user-session boot evidence for startup, and continuous samples
10 minutes before through 15 after a scheduled run for wakefulness. Gaps above
45 seconds, clock uncertainty above 10 ms, a reboot or suspend-offset movement
above 250 ms prevent a pass. Logged-in/unknown context requires explicit owner
confirmation about manual wake/start/keep-awake intervention; a wakefulness pass
alone is not unattended proof. Coordinate any restart with other workloads.
Retained -43 startup passed; the -42 window's unattended context remains unknown.

## Dashboard deployment authority

Owner authorized the narrow command on 20 November 2026; its installation was
verified. This grants neither general administrator nor trading permission.
The only sudo command for `codexdev` is root-owned
`/usr/local/sbin/nnfx-dashboard-deploy` **without arguments**, accepting bounded
JSON on stdin. No shell/Python/source script, generic service operation, timer,
dependency install or caller-selected path/executable/environment is granted.

[prepare_dashboard_update.py](../deploy/prepare_dashboard_update.py) prepares the
reviewed data payload with `--output` on USB. The installed helper copies data into
a protected release; only restricted `nnfx-view` executes submitted dashboard code.
Its fixed allowlist is `nnfx_practice/dashboard.py` plus the nine HTML/CSS names in
[dashboard_deploy.py](../deploy/dashboard_deploy.py). Strategy, broker/controller,
startup and dependency files cannot pass this interface. Root never imports/tests
submitted application code.

Releases are root-owned and immutable to login/service users. An atomic `current`
link switch and restart affect only `nnfx-practice-dashboard.service`, without
unit changes or manager reload. Preserve credential/control/network/LAN restrictions
and pinned qualified trading files. Reject stale releases, unknown/duplicate fields,
oversized input, unsafe ownership/modes/links/paths, non-allowlisted changes,
concurrent deployment, active runs/pending jobs and weekdays 16:35–17:10 New York.
The helper never pauses/enables/disables trading schedules.

Bounded fixed localhost GETs permit no proxy/redirect. Failed restart/page or
preservation checks restore the prior link/restart; receipts include hashes,
release identities and rollback outcome. Failed rollback needs administrator
attention. Receipts stay under `/var/lib/nnfx-dashboard-deploy`; old releases remain.
The helper does not open credentials, notebooks or protected plans.

The completed one-time installer validated protected ancestors/sudo rule and
could tighten only the two existing root:root 0775 application-package directories
to 0755. Those mode changes survive later failure; other unsafe paths are refused.
Setup and optional update are separate outcomes. Revoking its exact sudoers file
removes access without changing either service. New dependencies/service bindings,
qualified trading upgrades or allowlist expansion require separate administrator review.

**Coverage limit found during documentation inspection:** the source helper's
`CONTROLS` names only `practice-a`. Its documented active-run/pending-job guard has
not been generalized to the added controllers. Review multi-controller release
exclusion before relying on it for Python 02/03; no code change was made here.

## Ordinary review and activation

The ordinary adapter and [final verifier](../nnfx_practice/qualification_review.py)
exist. Actual final evidence/authority remain incomplete; do not activate or
enable ordinary scheduling on that basis.
[The plan](IMPLEMENTATION_PLAN.md#qualification-records-and-ordinary-activation)
owns lifecycle and reporting. This section owns the protected packet/procedure.

A version-2 ordinary plan has `mode: ordinary`, `enabled: true`, matching identities,
approved schedule, a run-ID prefix of at most 54 characters, `qualification_plan`
and `activation_review` as `{path, sha256}` references with protected root-owned
ancestors. The archived qualification plan must match the reviewed binding/code/
configuration and essential host observations. The review contains:

- Controller/notebook/account, manifest/code/configuration/kernel identities,
  collected `record_sha256` and `final_run_id`.
- `owner_authorization`: `reviewer`, `at`, `statement`, `reviewed_record_sha256`,
  and explicit `ordinary_activation` and `ordinary_scheduling` authority.
- Hashed full verbose passing `offline_suite`; each A01–A16 under `acceptance`
  with an accepted `conclusion`, `explanation`, named passed `offline_tests`
  and observations with artifact reference, JSON-key/index `pointer` and exact
  `observed` value. A flag/reference alone is insufficient.
- `runs` mapping actual execution/management run IDs to protected claim and raw
  JSONL capture references, matching committed mutation responses.
- `startup` raw rows with the retained current-kernel boot marker and
  `scheduled_window` continuous raw rows around the final run. Logged-in windows
  need explicit `operator_intervention: none` and owner statement; unknown is pending.
- `dashboard_comparison`: exact collected account_report, final run ID, GET/status
  evidence, owner_lan_confirmation and hashed HTML containing actual run/balance/
  trade identities.

The verifier checks actual complete long/short/cross-currency sets, distinct IDs/
units, historical fill-relative protection, sizing/margin, scheduled TP/stop change,
targeted closes, daily financing, both-stage final run, claims and raw responses.
Closed trades need historical protection proof, not currently active orders.
Stale/different records, simulated fills, missing observations, unresolved issues
or incomplete sets fail. Account exceptions return to review; no invented waiver.

After final review protect/archive the packet and ordinary plan, stop/disable
qualification and leave both timers disabled. Under writer identity and full
maintenance exclusion, `nnfx_practice.host`'s `ordinary-activate` verifies the
packet and reconciles fresh A0, requiring no trades/orders/unresolved activity.
A0/evidence/time commit together; repeats verify the same record. That command
never enables a timer. Only after successful reviewed A0 and maintenance release
may the authorized administrator enable the ordinary instance. Dispatch revalidates
the plan, activation and shared date claim. Ordinary candles are not archived.

Protocol references: [account endpoints](https://developer.oanda.com/rest-live-v20/account-ep/),
[orders](https://developer.oanda.com/rest-live-v20/order-df/) and
[transactions/protection](https://developer.oanda.com/rest-live-v20/transaction-df/).
They do not replace intended-account evidence.

## Completed procedures are not retries

Do not rerun the full installer, original M10 migration/dated armer/no-entry
continuation, GBP-CAD incident helpers, dashboard permission setup or Python 02/03
installers/bootstrap. Their receipts and failure archives remain discoverable via
[verification](VERIFICATION.md). Existing Q0, claims, history and bindings must not
be deleted to make old guards pass. Python 03's installer specifically assumes
Python 02 has not attempted setup; that assumption no longer holds.

Future experiments/upgrades need reviewed preservation of existing notebooks,
private bindings, protected plan/replay identities and schedules, plus refreshed
host controls for changed shared code. Inspect a failed bootstrap's protected
receipt before recovery; its exclusive attempt prevents replay. Setup captures
candles and Q0, never a trading run or ordinary activation.
