# Host operations and authority

This document owns host procedures and protected-review fields.
[Status](STATUS.md) records dated observations;
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
timeout. The existing `nnfx-practice-qualification@` timer targets that single
service; its name is retained for compatibility. Their calendar is `Mon..Fri *-*-* 16:50:00 America/New_York`,
`AccuracySec=1s`, `RandomizedDelaySec=0`, `Persistent=false`. Timer accuracy is not
a promise of exact Python start time. System services/timers use multi-user/timers
targets without interactive login. A paused timer never replays missed launches.

The [lifecycle contract](IMPLEMENTATION_PLAN.md#practice-lifecycle)
owns account checks and date claims. A same-kernel reboot can resume
version-2 practice schedules; changed kernel/code/configuration needs relevant matching
evidence. Keep earlier observations scoped to their actual versions.

The Waitress dashboard uses port 8879 and `/opt/nnfx-dashboard/current`; preserve
research listeners 8877/8878. Runtime has read-only files, no credentials,
systemctl/sudo/system-bus access or outbound connect calls, and no trading routes.
It sees committed WAL records. Trusted-LAN/firewall and tailnet restrictions remain;
[README access](../README.md#dashboard-access) owns client addresses.
[Completed cleanup](VERIFICATION.md#host-cleanup) records the retired preview/M09/M10
units and closed port 8880. Preserve their source, captures and unit copies.
The proposed production snapshot/HTTPS 8444 was never installed. New development
data requires USB.

## Maintenance and evidence collection

Use the same notebook exclusion lock as the master. For initialization or
disposition, pause the practice timer and any remaining legacy timer, preserving
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
all date claims, including claims without run rows; collection never grants execution authority.

Its CLI requires administrator access and accepts a new `--output` directory.
Choose a unique path under the mounted USB task evidence directory, including its
temporary copy; output is private and becomes checkout-owner-readable. **The CLI
currently collects `practice-a` only**; it has no controller selector. Use current
reviewed source, not the frozen migration bundle's older collector. Never reset
Q0 or delete claims.

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
storage command. The older user-systemd probe cannot replace actual system-manager
verification.

The retired [observer](../tests/check_m09_observation.py) and unarmed M10 deployment
probe describe earlier host layouts. Preserve their source and
[dated evidence](VERIFICATION.md#python-01-account-and-host-evidence), including its unattended
limits; do not replay them against the populated single-mode deployment.

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
submitted application code. [Deployer checks](../tests/test_dashboard_deploy.py)
cover this interface offline.

Releases are root-owned and immutable to login/service users. An atomic `current`
link switch and restart affect only `nnfx-practice-dashboard.service`, without
unit changes or manager reload. Preserve credential/control/network/LAN restrictions
and pinned qualified trading files. Reject stale releases, unknown/duplicate fields,
oversized input, unsafe ownership/modes/links/paths, non-allowlisted changes,
concurrent deployment, `practice-a` runs/pending jobs and weekdays 16:35–17:10 New York.
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

The installed helper's activity/job checks cover `practice-a` only. This is a
conservative dashboard-deployment policy; its expansion was dropped by the owner
on 28 November. Keep the installed helper and its permissions unchanged.

## Single practice mode upgrade

This completed 28 November upgrade implements the accepted
[lifecycle](IMPLEMENTATION_PLAN.md#practice-lifecycle). It changes no strategy,
account binding, trading rule or schedule and grants no manual trade.
Retain this procedure for review of future upgrades; do not replay it.

Use the reviewed [upgrade script](../deploy/single_practice_mode.py) from its frozen USB release,
with its passing offline suite, matching wheel and source hashes. Administrator
execution is required because this changes shared trading code and protected plans;
the narrow dashboard helper cannot perform it. Do not rerun the original installer
or account bootstrap. [Verification](VERIFICATION.md#single-practice-mode-installation)
retains preparation, installation and failed-attempt evidence.

Outside the dispatch window, require all three controllers idle with no pending
jobs. Preserve their enabled/active timer states, exclude launches and hold every
notebook lock. Archive the old code, plans, unit and dashboard configuration before
replacement. Never stop a running controller or open original notebooks with SQLite.

Preflight uses the frozen installed-code baseline matched to all protected plans;
older dashboard-only trading pins may predate that shared release. Pin the current
dashboard configuration and active release separately. Tighten only the two known
root:root package directories from 0775 to 0755 before the unchanged strict host
check, recording their prior modes. Other owners, modes or symlinks are rejected.
Preflight receipts identify the archive even when no service change has begun.

Install the verified package, retire the unused ordinary timer template and update
the dashboard release without widening its runtime permissions or deployer allowlist.
Run isolated native host controls and refresh only the code/control references in
all three protected practice plans; retain their authority, binding, start date,
schedule, run prefix and claim namespace. Verify notebook/sidecar/claim hashes,
credentials/configuration, ledger/history and next scheduled times remain unchanged.
Restore original timer states only after all checks pass. Preserve failed attempts;
a failure leaves trading safely excluded for administrator investigation.

Protocol references: [account endpoints](https://developer.oanda.com/rest-live-v20/account-ep/),
[orders](https://developer.oanda.com/rest-live-v20/order-df/) and
[transactions/protection](https://developer.oanda.com/rest-live-v20/transaction-df/).
They do not replace intended-account evidence.

## Completed procedures are not retries

Do not rerun the full installer, original M10 migration/dated armer/no-entry
continuation, GBP-CAD incident helpers, dashboard permission setup or Python 02/03
installers/bootstrap, or the completed single-mode upgrade. Receipts and failure archives remain available via
[verification](VERIFICATION.md). Existing Q0, claims, history and bindings must not
be deleted to make old guards pass. Python 03's installer specifically assumes
Python 02 has not attempted setup; that assumption no longer holds.

Future experiments/upgrades need reviewed preservation of existing notebooks,
private bindings, protected plan/replay identities and schedules, plus refreshed
host controls for changed shared code. Inspect a failed bootstrap's protected
receipt before recovery; its exclusive attempt prevents replay. Setup captures
candles and Q0, never a trading run or ordinary activation.
