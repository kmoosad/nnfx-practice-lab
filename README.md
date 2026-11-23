# NNFX Practice Lab

Forward-test a manually selected NNFX indicator combination on OANDA practice
accounts, with an observational dashboard and a notebook of actual trades.

The [project brief](PROJECT_BRIEF.md) was finalised on 10 November 2026.
[Project status](docs/STATUS.md) records implementation progress and verification
against the approved plan.

## Project documents

| Document | Purpose |
| --- | --- |
| [Project brief](PROJECT_BRIEF.md) | Accepted product scope, trading rules, operating rules and acceptance criteria |
| [Working guidance](AGENTS.md) | Guidance for Codex and contributors; maximum 300 lines |
| [Status](docs/STATUS.md) | Current delivery state, verification and next work |
| [Architecture](docs/ARCHITECTURE.md) | Approved numbered workflow and architecture, with account-specific integration evidence pending |
| [Detailed design](docs/DETAILED_DESIGN.md) | Approved controller, record, broker and dashboard contracts with acceptance test mapping; qualification dependencies remain open |
| [Acceptance](docs/ACCEPTANCE.md) | Concrete verification scenarios derived from the brief |
| [Implementation plan](docs/IMPLEMENTATION_PLAN.md) | Approved milestones, dependencies, acceptance evidence mapping and handover boundaries |

The brief is the authoritative source for behaviour. Architecture and acceptance
documents explain how to deliver and verify that behaviour without changing it.

## Run the offline checks

Use Python 3.12 or later with SQLite 3.37 or later and the system's New York
timezone data. The dashboard adds Flask/Jinja and Waitress. With `uv` installed, prepare the
local environment from the project root (no credentials needed):

```sh
python3 -m venv --without-pip .venv
uv pip install --python .venv/bin/python -e .
```

Run the unittest suite in that environment:

```sh
.venv/bin/python -m unittest discover -v
```

The checks build their own temporary registry, private connection fixtures, strategy
manifest and notebooks. They exercise a scripted transport entirely in memory.

## Configuration and storage

The [registry example](config.example.toml) shows the format of `config.toml`.
The [private field example](.env.example) lists the names for a connection
prefix. Keep actual values in an owner-only `.env` file with mode `0600`.
Use one `KEY=value` assignment per line. Blank lines, whole-line comments and
matching single or double quotes are supported.

`load_binding` validates account uniqueness across the registry and loads the
requested controller's `strategies/<version>/manifest.json`. Python 01 uses the
[qualified T3 and Bandpass strategy](strategies/t3_bandpass_v1/manifest.json).
The manifest records the selected research result, fixed settings and
386-candle window. The package exposes `observe_c1`, `observe_exit` and
`sizing_atr` for an exact window.

The [notebook module](nnfx_practice/notebook.py) derives each database path as
`var/notebooks/<notebook-id>.sqlite3`. Explicit creation binds the notebook to its
account and exact manifest. The storage layer provides a writer and a read-only
connection.

The [Manage Open Trades module](nnfx_practice/manage_open.py) implements M05
as `manage_open(db, broker, run_id=...)` for a newly recorded run. It reconciles
registered legs and due stops, then evaluates and closes surviving pairs using
the qualified strategy. The default practice connection remains GET-only;
execution requires an offline scripted transport or the guarded M10 permit
described below. The M07 master calls this stage. See [M05 evidence](docs/STATUS.md#m05-manage-open-trades)
for coverage and remaining dependencies.

The [candidate entry module](nnfx_practice/entry.py) implements M06 as
`enter_candidate(db, broker, run_id=..., pair=...)` for one pair. It requires a
matching run with its committed 4.1 balance and the qualified strategy, records
fresh C1/ATR inputs, sizes with Decimal arithmetic, and checks the conditional
two-leg sequence through scripted broker evidence. It returns a committed
completed/skipped/failed pair outcome; fatal account/history failures raise and
stop the run, and write failures leave the last durable intent. It has no live
command. M07 supplies master orchestration, the ordered 28-pair loop and the
qualification/activation lifecycle. See [M06 evidence](docs/STATUS.md#m06-sizing-and-candidate-two-leg-entry).

## Master and local maintenance interfaces

The [master](nnfx_practice/master.py) provides
`run_master(root, controller_id, broker, mode=..., config_hash=..., code_hash=...)`.
It records both children, runs management, saves one immutable 4.1 balance,
processes all 28 pairs through the candidate component, then reconciles final
reporting. `mode="ordinary"` requires committed activation;
`mode="qualification"` requires an initialized, unactivated notebook and explicit
prerequisite evidence references. Qualification can use the guarded M10 permit;
native ordinary invocation now has a separate protected final-review gate.
Automatic qualification is deployed and scheduled; ordinary scheduling remains
disabled. The deployment record below retains verification and remaining gates.

The [lifecycle functions](nnfx_practice/lifecycle.py) provide
`initialize_qualification(...)` and `activate_ordinary(...)`. Both take
`root, controller_id, broker` and keyword arguments `service, evidence`.
Initialization rejects an unpermitted practice transport before loading private
configuration, touching service controls or creating Q0. With a scripted transport
or verified read-only initialization permit,
it commits Q0, its evidence and cursor together; reopening reconciles forward.
Activation commits A0, the history import, evidence and time atomically;
repeating activation verifies the original record. The required evidence keys
are listed in that module. References identify externally reviewed prerequisites;
nonempty references alone do not establish live qualification. Native activation requires the protected final review and completed execution
evidence described below; references alone cannot authorize it. Qualification and ordinary reports remain separate in
`account_report(db, "qualification" | "ordinary")`.

The [local disposition action](nnfx_practice/disposition.py) is
`record_disposition(root, controller_id, broker, service=..., issue_id=...,
operator_id=..., explanation=...)`. It reconciles current broker evidence and
resolves only that issue when matching terminal or restored-protection evidence
exists. It submits no orders. Missing proof leaves the issue open; resolving an
issue never overrides a surviving leg or another issue.

All three maintenance actions use the same local exclusion lock as the master.
The [systemd adapter](nnfx_practice/host.py) supplies `timer_active`, `pause_timer`,
`service_active`, `launch_pending` and `restore_timer(prior_state)`. It stops the
timer and runtime-masks the exact controller service instance, then requires an
inactive/failed service and no pending service or timer job before broker reads.
It never stops a running controller. After the notebook closes, it removes only
its own mask and restores the timer's previous active/inactive state. The local
lock remains held during restoration to exclude another maintenance operation.
No timer is enabled at boot by maintenance. See the deployment commands below;
guarded qualification initialization and native ordinary activation are described
below. Once installed, maintenance excludes both qualification and ordinary timers.

Notebook schema 2 added run invocation labels and immutable Q0/A0 guards.
Schema 3 adds retained transaction response variants alongside cumulative accepted
facts. Opening a version-1 or version-2 writer migrates atomically after checking
its binding and preserves existing records. Updated readers accept schemas 2 and
3 without writing or migrating. Deploy the compatible dashboard reader before
the controller upgrades their shared notebook; a schema-2-only reader cannot read
schema 3. The [incident status](docs/STATUS.md#notebook-reconciliation-for-the-closed-gbp-cad-trade)
records actual reader/writer deployment and migration separately.

To recreate the M07 trace and committed-row exports with the full offline suite:

```sh
NNFX_M07_EVIDENCE_DIR=var/verification/m07/cases .venv/bin/python -m unittest discover -v
```

See [M07 evidence and dependencies](docs/STATUS.md#m07-master-workflow-and-qualification-lifecycle).

## Run the local observational dashboard

From the project root:

```sh
.venv/bin/python -m nnfx_practice.dashboard --root "$PWD" --port 8879
```

Open <http://127.0.0.1:8879/controllers> or
<http://127.0.0.1:8879/notebooks>. Notebook links open the journal. Previous-run
links open a separate read-only page in a new window or tab; the selected run's
details are loaded only when opened. Reload a page to see committed changes. The local command uses
Flask's development server without debug, reloading or dotenv loading. The separate
trusted-LAN service uses Waitress and the permissions described below.

The dashboard reads `config.toml` and matching schema-2/schema-3 notebook paths through
SQLite `mode=ro` and `query_only`, using one short read transaction per notebook.
It does not read `.env` or contact OANDA. Missing, incompatible or unreadable
notebooks show an unavailable message; GET requests never create or migrate them.
Initialization and ordinary activation are separate reviewed maintenance actions;
the dashboard performs neither. The journal's current state can postdate the displayed reconciled
account snapshot; those rows are labelled and excluded from summary totals until
a covering refresh. Qualification totals stop at A0, and ordinary totals begin
after A0. Pips use instrument metadata retained with the set's entry decision;
missing metadata leaves pips unavailable.

Retain the M08 rendered fixture pages and committed-row evidence with:

```sh
NNFX_M08_EVIDENCE_DIR=var/m08/fixtures .venv/bin/python -m unittest tests.test_m08 -v
```

See [M08 evidence and dependencies](docs/STATUS.md#m08-observational-dashboard).

### Deploy the merged dashboard layouts

The owner completed live dashboard deployment on 20 November 2026, verified at
16:12 Melbourne. The [deployment record](docs/STATUS.md#verified-dashboard-layout-deployment)
confirms all three live pages, mobile/desktop checks and preserved trading controls.
The frozen
release in `var/prepared/dashboard-a7d756b` combines the verified installed M10
runtime with only the ten dashboard files from commit `a7d756b`. Its 41 dashboard
checks pass using the installed Python environment; 14 separate offline
deployment checks cover rejection and rollback. The
[manifest](var/prepared/dashboard-a7d756b/verification.json) identifies all 47
application files and the exact deployment helper. Do not rebuild from unrelated
checkout changes or rerun the M10 migration.

**Completed—do not rerun.** The owner ran this command from the **serveradmin**
terminal on `thinkbook-server`; it is retained as deployment history:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/dashboard-a7d756b/deploy.py \
  --manifest-sha256 7590f9988e99ede5325dcac2f238d132f4e9275dfa35dd69206d0bdfeaf43368
```

The [helper](var/prepared/dashboard-a7d756b/deploy.py) installs an administrator-owned
release under `/opt/nnfx-dashboard`. A dashboard-only systemd override selects
that working directory, retaining the existing Python environment, reader identity,
port 8879 and service restrictions. The qualified `/opt/nnfx-practice` source and
package remain unchanged, so the scheduled trading code identity stays valid.
Only the dashboard is restarted. The helper refuses an active controller or the
trading window, verifies all three pages, checks unchanged trading controls and
notebook/plan fingerprints, and restores the previous dashboard if post-switch
verification fails. It does not alter timers, credentials, strategies or notebook
data. Receipts are saved beside the prepared helper; require `status: deployed`.
The first attempt restored the old dashboard after a service-setting comparison
failed. The corrected helper compares unordered rules by content while retaining
all restrictions, and safely reuses the existing release only after verifying
every file, owner and permission. The prior helper/manifest remain in `attempt-1`
beside its receipt. The administrator completed the corrected retry; its receipt
reports `deployed`. That release was served from
`/opt/nnfx-dashboard/dashboard-a7d756b-7a3d198f3e7e` on port 8879; the later
wording release below now runs through the protected `current` link.

### Deploy the Controller wording update

The 20 November wording update is **deployed and verified**.
It changes four templates in the separate dashboard release. The
[status record](docs/STATUS.md#controller-wording-update) retains 40 dashboard,
21 fixture-browser and 16 initial deployment checks. The
[live verification](docs/STATUS.md#verified-scoped-dashboard-deployment) confirms
12 browser checks and the new wording on port 8879. The one-time setup below is
complete; do not rerun it or the earlier standalone wording installer.

### Enable scoped dashboard deployment

The owner authorized this scope on 20 November 2026. The command is **installed
and verified on the host**. The
[status record](docs/STATUS.md#scoped-dashboard-deployment-access) retains 68 passing
focused checks and the verified installation. The runtime remains `nnfx-view`;
`codexdev` has only the fixed no-argument deployment command, with no generic
sudo, service control or trading permissions.

**Completed—do not rerun.** The owner ran this once from the **serveradmin** terminal
on `thinkbook-server`; it is retained as installation history:

```sh
sudo /usr/bin/python3 -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/dashboard-delegation-20261120/install_dashboard_deployer.py \
  --helper-sha256 7e4048385743bb7157e8145e5b31c80a1f75e683045b9a4da37cbe16e320003f \
  --apply /home/codexdev/projects/nnfx-practice-lab/var/prepared/dashboard-delegation-20261120/update.json
```

The corrected retry removed group-write permission from the two existing
root:root `0775` application package directories, making them `0755`.
Application file contents and trading schedules are unchanged. The first attempt
installed nothing and did not restart
the dashboard. The [retry record](docs/STATUS.md#dashboard-deployment-setup-retry)
contains the corrected host inspection and retained first-attempt evidence.

The [frozen bundle](var/prepared/dashboard-delegation-20261120/verification.json)
pins the helper and four changed templates. Setup installs the administrator-owned
helper, baseline configuration and exact sudo rule, switches the dashboard to a
protected `current` release link and verifies the existing restrictions. The
optional update used the installed helper. Receipt `20261120T054512457591.json`
reports `deployed`; effective permissions, protected ownership, live pages and
unchanged trading controls passed verification. Neither the M10 migration nor
the full installer was part of this setup.

Prepare and apply subsequent reviewed dashboard changes as
`codexdev` from this checkout:

```sh
.venv/bin/python -m deploy.prepare_dashboard_update --output var/prepared/dashboard-update.json
sudo -n /usr/local/sbin/nnfx-dashboard-deploy < var/prepared/dashboard-update.json
```

The helper accepts only its ten named dashboard files as stdin data, creates a
protected release, switches the link and restarts only the dashboard. It never
executes submitted code as root. It preserves service restrictions and qualified
trading code, defers during active runs/the trading window, and restores the
previous release if page or preservation checks fail. Receipts are under
`/var/lib/nnfx-dashboard-deploy`. Existing releases are retained. New dependencies,
service changes, trading upgrades and files outside the allowlist remain separate
administrator work. To revoke deployment access, an administrator removes only
`/etc/sudoers.d/nnfx-dashboard-deploy`; that does not stop either service.

## Ubuntu deployment and host operation

M09 supplies the [installer](deploy/install.py), per-controller
[service](deploy/nnfx-practice@.service), ordinary
[timer](deploy/nnfx-practice@.timer), and separate
[dashboard service](deploy/nnfx-practice-dashboard.service). The installed dashboard
is running on **8879**; preserve the sibling research dashboards on 8877/8878.
Startup without login and essential system/maintenance/dashboard fixtures passed
on kernel `7.0.0-43-generic`. Ordinary scheduling remains disabled. Automatic
qualification is deployed; [project status](docs/STATUS.md#current-position)
records its current state and next scheduled run.

**The completed M10 migration below is retained as history; do not rerun it.** The full
installer intentionally refuses an existing qualification plan. Do not delete
plans, Q0, claims or notebook history to make installation succeed. The following
full-install commands are for an initial installation only. Existing M09 deployment
and controlled Python 01 execution approvals remain valid; no repeat approval is
required for their scope. General administrator access remains unavailable;
scoped dashboard updates use the restricted command above.

The administrator setup uses `/opt/nnfx-practice` for root-owned code and its
virtual environment, and `/var/lib/nnfx-practice` for the public registry, copied
strategy manifests, private `.env` and `var/notebooks`. It has no dependency on
this checkout or the sibling indicator lab. Prerequisites are Python 3.12+ with
SQLite `SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`, `python3-venv`, pip, sudo/visudo,
systemd, New York timezone data and package-index access during installation.
Ubuntu splits pip bootstrapping (`ensurepip`) into the version-matched venv
package. For this host's Python 3.14, install it from an administrator terminal:

```sh
sudo apt-get install python3.14-venv
```

The installer checks for `ensurepip` before creating service users or changing
deployment files. If an earlier attempt stopped during venv creation, install
that package and rerun the command below. It reuses the partial environment and
matching service identities; deletion or notebook initialization is unnecessary.

From any directory in an administrator-capable terminal on `thinkbook-server`,
install the reviewed sources and registry using absolute paths (no credentials
are copied and no notebook or timer is initialized):

```sh
sudo python3 /home/codexdev/projects/nnfx-practice-lab/deploy/install.py \
  --registry /home/codexdev/projects/nnfx-practice-lab/config.toml
```

If this session's account cannot run sudo, an administrator must execute that
command in an administrator-capable terminal on `thinkbook-server`. The approval
is already recorded. These absolute paths work when `serveradmin` cannot enter
the private `codexdev` checkout: sudo gives Python access to the source and registry.
This session has no general administrator access.
The installer leaves the dashboard stopped and ordinary trading timers inactive.

The installer creates non-login users `nnfx-run` and `nnfx-view`, both with the
`nnfx-read` group. Executable code belongs to root. Notebook storage is owned by
`nnfx-run:nnfx-read`, with a setgid mode-2750 directory and mode-0640 databases,
WAL and SHM files. Only the writer has filesystem write permission. The writer's
`NNFX_NOTEBOOK_READ_GROUP=nnfx-read` setting checks ownership and grants group
read access; local notebooks without that setting stay private. Shared writers
retain WAL/SHM after closing, using SQLite's
[NO_CKPT_ON_CLOSE option](https://www.sqlite.org/c3ref/c_dbconfig_defensive.html);
normal WAL autocheckpointing continues. This lets read-only dashboard connections
work between runs as well as during committed WAL updates. Do not delete or copy
a database independently of its WAL; use SQLite backup facilities for a backup.

Provision the private fields separately, with the same reviewed Python 01 binding:

```sh
sudo install -o nnfx-run -g nnfx-read -m 0600 /home/codexdev/projects/nnfx-practice-lab/.env /var/lib/nnfx-practice/.env
sudo systemd-analyze verify /etc/systemd/system/nnfx-practice@.service /etc/systemd/system/nnfx-practice@.timer /etc/systemd/system/nnfx-practice-dashboard.service
systemctl show nnfx-practice@practice-a.timer -p ActiveState -p UnitFileState
```

The ordinary timer must remain inactive and disabled until completed qualification,
applicable authorization and committed ordinary activation. The installed `dispatch`
entry point rejects a missing protected plan before loading private configuration,
and accepts only a verified explicit M10 qualification plan. `ordinary` remains
disabled. No live ordinary activation CLI is supplied.
Each controller has one oneshot
service instance; its master and maintenance also share a notebook lock.
Independent controllers use distinct registry/account/notebook bindings and
locks. The timer uses weekday 16:50 `America/New_York`, `AccuracySec=1s`,
`RandomizedDelaySec=0`, `Persistent=false`; the service uses `Restart=no` and no
startup timeout. Restoring a stopped timer does not replay a missed launch.
Systemd's timer accuracy window is not a guarantee of Python process start time.

The practice dashboard is now installed, enabled and running on **8879**, with
matching socket restrictions. It preserves the sibling research services on
8877/8878. The post-reboot preserving system probe passed as
[`nnfx-m09-system-daed36cb06d3.json`](var/verification/m09-system/nnfx-m09-system-daed36cb06d3.json),
and actual HTTP figures agree with the notebook. The owner confirmed LAN access
at <http://192.168.51.10:8879/controllers>. Ordinary trading remains disabled.

The completed dashboard-only deployment procedure is retained below; no repeat
is needed for this installation. The full installer refuses an existing
qualification plan:

```sh
sudo install -o root -g root -m 0644 /home/codexdev/projects/nnfx-practice-lab/deploy/nnfx-practice-dashboard.service /etc/systemd/system/nnfx-practice-dashboard.service
sudo systemctl daemon-reload
```

Repeat the broker-free system fixture with existing notebook preservation before
claiming updated deployed security evidence:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_system.py --preserve-existing-notebooks
```

That flag permits only byte/ownership comparisons of the existing notebook and
sidecars; it never opens actual SQLite, changes Q0/history or repairs files.
Fixture services additionally deny access to actual credentials/notebook paths.
Only synthetic fixture units/records are exercised. Missing or changed actual
files leave the probe failed for review, without automatic restoration.
After deployment and verification, start only the observational dashboard:

```sh
sudo systemctl enable --now nnfx-practice-dashboard.service
systemctl status nnfx-practice-dashboard.service --no-pager
journalctl -u nnfx-practice-dashboard.service -n 40 --no-pager
```

The deployed dashboard listens on trusted-LAN port 8879. Restrict host firewall access to
the intended trusted LAN. Its service has a read-only filesystem, cannot read
`.env`, cannot access systemctl/sudo or the system buses, and denies outgoing
`connect` calls. It can accept HTTP connections but cannot contact a broker.
It has no trading/maintenance endpoints and cannot obtain the writer's lock.
Verify these restrictions as `nnfx-view`, including committed WAL visibility
while a writer is open and after it closes, before claiming deployed A15.
Missing actual notebooks display unavailable figures.

System services use `multi-user.target` and timers use `timers.target`; they do
not depend on interactive login. Still retain an actual boot-without-login check
after installation. Confirm `timedatectl show -p NTPSynchronized`, the time
service, lid/idle/suspend policies and unattended wakefulness through a scheduled
window. Host inspection found synchronized chrony and lid-ignore settings, but
sleep targets are unmasked; this does not establish future wakefulness. Do not
enable ordinary scheduling until M10 and atomic ordinary activation have passed.

## Notebook maintenance on the deployed host

With an existing initialized notebook and a recorded issue, and only under the
existing Python 01 account-scoped GET authority, run the local disposition as
the writer. This command reconciles broker facts and records disposition; it
sends no orders and does not initialize a missing notebook:

```sh
sudo -u nnfx-run env NNFX_NOTEBOOK_READ_GROUP=nnfx-read /opt/nnfx-practice/.venv/bin/python -m nnfx_practice.host --root /var/lib/nnfx-practice disposition practice-a --issue-id ISSUE_ID --operator-id OPERATOR --explanation "Broker resolution and evidence reference"
```

The failed GBP-CAD entry's [incident recovery is complete](docs/STATUS.md#verified-notebook-reconciliation-and-restored-schedule):
the schema-3 notebook is reconciled through `2259`, the close and AUD 50.03 funding
are recorded separately, and the matching issue is resolved. Compatible reader,
writer permissions and affected host controls are verified; the existing
qualification schedule is restored and ordinary trading remains disabled. Both
failure archives, original backup, Q0 and failed-run history are retained. Do not
rerun the incident deployment/recovery commands, original installation or M10
migration. Future issues use the normal evidenced maintenance action above.

The installer grants `nnfx-run` only exact sudo systemctl operations for registered
controller timers and runtime service masks. The dashboard user receives no such
grant. Maintenance defers before broker reads if the local lock is busy, the
timer cannot be paused/masked, the service is active, or a launch is pending.
Do not manually launch or change units during maintenance. Exceptions restore
the prior timer state after the notebook closes; an initially paused timer stays
paused. Failed restoration is visible and leaves the timer stopped when unmasking
fails. Abrupt process death can leave the timer stopped/service runtime-masked;
there is no automatic recovery or request replay.

For operator recovery, first confirm the maintenance process has exited, the
notebook is released and the service is inactive with no pending job:

```sh
systemctl show nnfx-practice@practice-a.service nnfx-practice@practice-a.timer -p LoadState -p ActiveState -p Job
sudo systemctl unmask --runtime nnfx-practice@practice-a.service
```

Restore only the recorded prior timer state, after reviewing the failure. Ordinary
timers remain stopped for this milestone; a future start requires completed M10
and committed ordinary activation. Do not retry an uncertain broker mutation.

To repeat the harmless host checks from this checkout with host-systemd access:

```sh
.venv/bin/python tests/check_m09_prerequisites.py
.venv/bin/python tests/check_m09_host.py
```

These create separately named `nnfx-m09-probe-*` fixture units and synthetic
notebooks under `var/verification/m09`, run scripted broker reads only, and remove
their manager links afterward. The report distinguishes controller probes from
the dashboard security prerequisite; `passed=false` is expected while that
prerequisite is unavailable. Production timers and actual notebooks are untouched.

### Broker-free system verification

After installation, run the [administrator system probe](tests/check_m09_system.py)
from the `serveradmin` terminal using absolute paths:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_system.py
```

It checks the installed identities, permissions, synchronized clock and matching
code, then exercises separately named `nnfx-m09-system-*` units with the deployed
service restrictions. It tests timer dispatch, no restart/catch-up/overlap,
independent controllers, active-service deferral and maintenance success/failure
with initially active and paused fixture timers. Both read and write phases are
excluded; notebook closure precedes timer restoration. A synthetic dashboard
checks separate-user restrictions and committed WAL visibility during and after
the writer. Only in-memory broker fixtures are used.

The probe creates synthetic notebooks under
`/var/lib/nnfx-practice/var/verification/<fixture-prefix>` and root-owned worker
copies under `/opt/nnfx-practice/verification/<fixture-prefix>`. A temporary exact-unit
sudoers grant permits the writer to pause/mask only its fixture controller; the
fixture units and grant are removed in cleanup. Ordinary services/timers are
checked inactive before and after; no actual notebook or credential content is
opened. Fixture data and code remain as evidence. The credential-free report is
written under this checkout's `var/verification/m09-system/`, and its path is
printed at the end. A failed cleanup is reported as a failure, not a pass.

The corrected administrator probe passed the controller/maintenance and dashboard
sandbox/WAL checks under the system manager. The
[successful report](docs/STATUS.md#successful-system-fixture-verification)
retains actual process identities and cleanup evidence. The earlier failure and
its path-construction repair remain preserved; no service security setting was
relaxed. Repeat affected checks if the relevant deployed code/configuration changes.
The report always leaves full host qualification incomplete: startup
without login, unattended wakefulness/intended 16:50 dispatch, private credential
provisioning and the production dashboard/final practice comparison remain separate.
The earlier user-systemd probe cannot substitute for this system-manager check.

### Provision and verify the private connection

The installer deliberately leaves the deployed `.env` absent. From the
`serveradmin` terminal, copy the reviewed connection with writer-only permissions,
then run the prepared read-only checker:

```sh
sudo install -o nnfx-run -g nnfx-read -m 0600 /home/codexdev/projects/nnfx-practice-lab/.env /var/lib/nnfx-practice/.env
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/var/verification/m09-private/check_private.py
```

The [checker](var/verification/m09-private/check_private.py) runs configuration
validation as `nnfx-run`, compares the deployed account/strategy binding with
the approved Python 01 M04 references and checks that `nnfx-view` cannot read
the credential file. It displays no credentials, contacts no broker, opens no
notebook and starts no service/timer. A successful result writes a private
metadata report owned by the checkout owner under `var/verification/m09-private/`.
The administrator check passed: the private file is writer-owned mode 0600,
the approved account/strategy binding matches and the viewer cannot read it.
It does not initialize Q0/A0 or authorize trading. Retain the private report and
repeat affected checks after a configuration change.

### Observe startup and the intended scheduled window

**Completed:** the administrator restarted the host and collected
[`protected-review-0113463688d3.json`](var/verification/m10-review-20261120/protected-review-0113463688d3.json).
Startup without login passed on **7.0.0-43-generic**: the boot marker ran about
15 seconds after boot with zero user sessions. Q0/history and disabled ordinary
controls are preserved. **Do not repeat the reboot for this completed check.**
Affected system fixtures have since passed on the current kernel with actual
notebook files preserved, and the deployed dashboard/LAN checks passed as described
above. Prior wakefulness samples
belong to kernel -42; unattended scheduled-window conditions remain unconfirmed.

The restart sequence below is retained as historical procedure, not another
request to restart:

The owner requested the previously deferred startup-test reboot **now** on
20 November, initially assuming no other services were active. Inspection found
the existing research dashboards and idle visualization helpers. **Automatic
approval review initially rejected the reboot pending informed approval of those
concrete interruptions. The owner has now answered "Restart now with those
interruptions"; that approval is recorded.** The boot observer is enabled and its hashes were checked;
the ordinary timer remains disabled. The informed-approved attempt passed
automatic review, but the host denied `codexdev`'s sudo command. No reboot occurred.
Use your existing `serveradmin` terminal after closing other clients that would
automatically reconnect; no additional approval is needed:

```sh
sudo systemctl reboot
```

Wait at least two minutes before reconnecting to SSH/Codex so the boot marker can
record whether startup occurred without a user session. A reconnect/login before
the marker leaves this check unproved. After reconnecting, run the existing
[read-only collection command](#review-the-completed-qualification-session)
again to retain the new boot marker and changed kernel/boot identity. Existing
scheduled-window evidence remains retained. Repeat affected system fixtures
after a kernel change, using `check_m09_system.py --preserve-existing-notebooks`
with the prepared dashboard unit installed. This mode was checked offline and
preserves actual notebook/sidecar bytes. Do not rerun the installer or the
uninitialized-deployment probe over the existing plan/notebook.

The setup procedure below is retained for reference; an observer already exists.

Prepare the [broker-free observer](tests/check_m09_observation.py) from the
`serveradmin` terminal:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_observation.py prepare
```

It enables only isolated `nnfx-m09-observe-*` boot/monitor/timer units and prints
the metadata path and next weekday 16:50 New York target in Melbourne time. It
does not reboot, change power policy or start ordinary trading. The scheduled
fixture uses the approved calendar's next date, 1-second accuracy and no
persistence, so it will not replay a missed launch or recur on later dates.
The monitor runs as an exec service so it does not hold boot targets waiting for
the observation window. Other fixture launches remain oneshots with no restart.

The observer cannot access actual credentials/notebook storage and has IP traffic
denied. It uses public fixture configuration and separate lock/JSON files only.
The monitor records UTC, kernel/boot identity, service invocation and monotonic/
boottime samples until 15 minutes after the target. Assessment requires continuous
samples from 10 minutes before the target, no detected suspend (250 ms tolerance),
no reboot within that window and no sample gap over 45 seconds. Unknown login
metadata never establishes startup without login. Existing user sessions during
the window require operator confirmation of unattended conditions.

After setup, coordinate a server restart around other workloads; the preparation
command never restarts the server. Leave time after boot before signing in so the
boot marker can record startup without a user session. Check the captured result
from the administrator terminal using the exact metadata path printed by setup:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_observation.py check METADATA_PATH
```

After evidence review, remove only the observation units; data/code are retained:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_observation.py cleanup METADATA_PATH
```

If the restart changes the kernel, repeat the system fixture probe before reusing
its security evidence. The observer is now armed as `nnfx-m09-observe-ba7d65c9bebd`:
boot marker enabled, one-time timer dispatched at 20 November 08:50 Melbourne
and monitor finished at 09:05. Protected collection/review passed scheduled
dispatch and sampled wakefulness. Four logged-in sessions and the owner's
Unsure answer leave unattended conditions unconfirmed; startup without login
remains deferred. Its metadata is
`var/verification/m09-observation/nnfx-m09-observe-ba7d65c9bebd.json` in this checkout.
An indicator-lab run was active at inspection, so coordinate the restart after
that work completes or at another agreed maintenance window. Check/cleanup and
actual boot/window outcomes remain pending. Neither an armed observer nor
its eventual host result establishes practice execution or ordinary activation.

## Automatic M10 qualification and ordinary activation

The owner requested automatic weekday practice qualification on 20 November 2026.
The isolated M10 package passes **460 offline tests**, including 33 new schedule/activation/deployment
checks. The checkout supports it through the same controller service, including
management of trades opened on earlier qualification days. It keeps the agreed
16:50 New York partial candle, strategy, ATR, balance/margin and protection rules.
There is no daily administrator arming, signal forcing, resized Trade 2 or automatic
repair of failed/uncertain requests. Those issues remain visible for operator
disposition, while eligible work follows the existing controller rules.

**Current host:** M10 was deployed on 20 November. Automatic qualification is
enabled and waiting for **21 November 08:50 Melbourne / 20 November 16:50 New York**,
then follows Monday–Friday at 16:50 New York. The old dated timer is stopped.
The installed dashboard files and running process are unchanged. Ordinary trading
remains disabled and the deployment receipt confirms A0 is unset, with notebook
history and claims preserved. The [deployment verification](docs/STATUS.md#verified-m10-automatic-qualification-deployment)
records the successful host checks and remaining dependencies. No daily arming is
needed; the dated arming/continuation procedures below are retained for history.

### Deploy automatic qualification once

The deployment source is frozen at
`/home/codexdev/projects/nnfx-practice-lab/var/prepared/m10-automatic`. Per the owner’s
instruction, it retains the verified installed dashboard and its original tests;
concurrent dashboard work stays in the shared checkout and is excluded from this
deployment. Do not rebuild this package from the changing shared checkout.

**Completed—do not rerun.** The owner ran this M10-only migration from the
**serveradmin** terminal after the agent's host sudo denial. Receipt
`m10-automatic-ebcd02e60445` confirms `armed`, successful updated system fixtures
and preserved files. This command is retained as deployment history; the existing
dashboard was preserved:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/prepared/m10-automatic/deploy/upgrade_m10.py \
  --expected-plan-sha256 db84be8d0d31928c16e8be512472553509cd5a675a2c83ebd53ae369ca84fdc5 \
  --verification /home/codexdev/projects/nnfx-practice-lab/var/prepared/m10-automatic/var/verification/m10-automatic/verification.json
```

The [migration](deploy/upgrade_m10.py) checks the exact retained plan and current
service/trigger state, defers around the trading window or an active controller,
and archives the old plan, dated timer, code and policy. It stops the dated trigger,
holds the existing notebook lock, installs the verified local wheel without
network/dependency installation, adds the qualification timer and narrow maintenance
permissions, and runs the updated broker-free system fixtures. The fixtures verify
both timer states restore independently and preserve actual notebook files.
Only after those checks does it enable
`nnfx-practice-qualification@practice-a.timer`. The ordinary timer stays disabled.
No broker request, notebook reset, trade closure or A0 activation occurs during
migration. It preserves existing trades, attempts, Q0, cursors, claims and evidence.
A prior executed session does not need a no-entry-only continuation.

Require a receipt with `status: armed`, `files_preserved: true`, a successful system
report and the recurring timer `enabled/active/waiting`. Receipts go under
`var/verification/m10-automatic-deployment` within that prepared source folder; archives stay protected under
`/etc/nnfx-practice/qualification/evidence/`. The installer verifies the package
against the recorded application hashes and records the next expiry. The source
and verification artifact must remain unchanged until deployment.

On failure, preserve the receipt and archive and inspect the reported stage.
The migration leaves schedules stopped (the recurring timer disabled on cleanup),
never stops a running controller, and does not restore obsolete code or replay a
session automatically. A changed plan hash requires inspection; do not simply
substitute a new hash and rerun. Repeating a completed migration is rejected.

Qualification then runs Monday–Friday at 16:50 New York, with DST, no missed-launch
catch-up, no restart and one durable claim per New York date. The same date claim
blocks a duplicate from an old dated timer or ordinary activation on that day.
A same-kernel reboot can resume the regular schedule without login. A new kernel,
code/configuration or strategy identity blocks the permit pending relevant review;
it does not silently inherit qualification. Ordinary scheduling remains separate.

### Collect qualification progress without daily arming

After deployment, use this read-only collector when reviewing progress:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/collect_m10_automatic.py
```

It exports the notebook, run/attempt/fill/issue records, reconciled figures, retained
raw responses and all claims, including claims left before a run row was created.
It reports concrete execution evidence and missing requirements. It sends no broker
request, changes no controls and creates no notebook sidecars. No host-observer
file is required to collect execution progress. A `practice_execution_qualified:
false` field remains intentional: collection is not final owner acceptance.
Each collection uses a new private output directory owned by the checkout owner
so it can be reviewed without another administrator handoff. The actual notebook
and protected evidence keep their existing permissions and ownership.
The corrected collector reads a temporary database/WAL copy under controller
exclusion. It never opens the original notebook with SQLite, which can update
writable shared-memory read marks even through a read-only connection. The export
records before/after source hashes, distinguishes SHM changes from database/WAL
changes, and preserves an inspectable export before refusing changed database/WAL
evidence. Use the command above, not the frozen migration bundle's older collector.

The -43 startup-without-login pass remains valid. The old wakefulness window belongs
to -42, and a refreshed -43 observer has not been observed. Its remaining unattended
window evidence and traded dashboard comparison are **final activation gates**,
not reasons to block otherwise eligible qualification. Do not repeat the completed
startup check or reboot for it. Existing observer instructions below remain available
for a matching future qualification window after inspecting any already prepared
observer. Eligible signals must arise from the unchanged strategy; their timing
and the later TP/stop/close observations cannot be promised.

### Guarded native ordinary activation

Ordinary activation and dispatch are implemented in
[ordinary.py](nnfx_practice/ordinary.py), with the
[review verifier](nnfx_practice/qualification_review.py). **Do not run activation
or enable the ordinary timer now.** Actual long/short/cross-currency execution,
management, restrictions/margin, charges, final integration and final owner
review/ordinary authority remain incomplete.

Once that evidence exists, the owner-reviewed protected ordinary plan uses version
2, `mode: ordinary`, `enabled: true`, the same identity fields and approved weekday
schedule, a run-ID prefix (at most 54 characters), `qualification_plan` and
`activation_review` references. Both references are `{path, sha256}` objects pointing
to root-owned files with protected ancestors. The archived qualification plan must
match the qualified code/configuration/account/strategy and its essential host
observations. The final review contains:

- Matching controller/notebook/account, manifest, code, configuration and kernel
  identities; `record_sha256` from the reviewed collection and `final_run_id`.
- `owner_authorization` with `reviewer`, `at`, `statement`, `reviewed_record_sha256`,
  and explicit `ordinary_activation` and `ordinary_scheduling` authorization.
- A hashed full verbose `offline_suite` log, and every `A01`–`A16` under
  `acceptance`, with an accepted conclusion, explanation, named passed
  `offline_tests`, and concrete observations. Each observation supplies an artifact
  reference, a list of JSON keys/indexes in `pointer`, and its exact `observed`
  value. Boolean/pass flags do not count as observations.
- `runs` mapping the selected execution/management run IDs to protected `claim`
  and raw JSONL `captures` references. The verifier checks their actual source and
  matches committed mutation responses, rather than accepting simulated fills.
- `startup` pointing to raw `rows` containing the retained current-kernel boot
  marker; `scheduled_window` pointing to continuous raw monitor `rows` around the
  final run (10 minutes before to 15 after). Unknown intervention stays pending;
  logged-in windows need an explicit `operator_intervention: none` and owner
  statement in that artifact.
- `dashboard_comparison` with the exact collected `account_report`, final run ID,
  GET/status evidence, `owner_lan_confirmation`, and a hashed retained `html`
  response containing the actual run, balance and trade identities.

A fabricated pass flag, nonempty reference, stale source, missing observation,
unresolved issue, incomplete set or changed reviewed history cannot satisfy this
gate. Historical protection is checked from establishment and transactions because
closed trades correctly no longer have current protective orders. Account-specific
exceptions or incompatible broker behavior must return to review; the code does
not invent waivers or adjust strategy/units.

After final review, protect/archive the reviewed artifacts and ordinary plan,
disable/stop qualification scheduling, and leave both timers disabled. Under the
writer identity and maintenance exclusion, the command is:

```sh
sudo -u nnfx-run env NNFX_NOTEBOOK_READ_GROUP=nnfx-read \
  /opt/nnfx-practice/.venv/bin/python -I -B -m nnfx_practice.host ordinary-activate practice-a
```

It verifies the final packet against the notebook, reconciles a fresh A0 and
requires no remaining trades/orders or unresolved activity. A failed commit leaves
ordinary activation unset. A repeated request verifies the same A0 and review.
This command never enables scheduling. Only after the successful reviewed A0 and
maintenance release may the authorized administrator enable the ordinary timer:

```sh
sudo systemctl enable --now nnfx-practice@practice-a.timer
```

Ordinary dispatch revalidates its protected plan and committed activation and uses
the existing master, while retaining no ordinary candle archive. The qualifier
cannot run after activation. A0 opens ordinary reporting; Q0/history and all
qualification results remain preserved and separately labeled.

## M10 readiness preparation

The owner has [authorized controlled Python 01 execution for M10 qualification](docs/STATUS.md#conditional-m10-execution-authorization)
once its required prerequisites are met. Ordinary scheduled trading stays disabled
until qualification and activation review are complete. M09 deployment is approved,
installation completed and the system fixture/private connection checks passed.
The initial account-path check can follow the essential controller controls;
remaining startup/wakefulness, intended scheduled-window and production dashboard
checks are required for final qualification. Gated live transport and same-service
qualification integration are now implemented, installed and verified with broker-free
system fixtures and actual unarmed-service checks. Fresh account clearance and
disabled-plan preparation and Q0 initialization have now passed. The actual
notebook has its qualification baseline at transaction `2249`; ordinary activation
is unset. The administrator has now armed the single dated initial qualification
session for 20 November 08:50 Melbourne. Its service started on time and exited
with status 0 at 08:50:15; the dated timer has elapsed with no next expiry.
Protected review confirms a completed 14.112-second no-entry run: all 28 pairs
had valid captures and no fresh C1 event, with 31 successful GETs and zero orders,
fills or issues. Actual execution qualification remains incomplete. The ordinary recurring
timer remains disabled/inactive.
The [M10 handoff](docs/STATUS.md#m10-readiness-preparation-and-blocked-qualification)
retains the earlier blocked state and execution evidence still required.

Collect a fresh broker-free host inspection from the checkout, retaining a new
filename each time:

```sh
.venv/bin/python tests/check_m10_prerequisites.py --output var/verification/m10/host-YYYYMMDD-HHMMSS.json
```

The survey uses the system manager and records clock/calendar output, administrator
availability, service identities, unit properties, permission metadata, notebook
file presence and source hashes. It never opens notebooks, reads `.env` contents,
starts services, changes timers or contacts OANDA. It creates a mode-0600 report
and refuses to overwrite prior evidence. Successful collection is inspection
evidence; it does not establish deployment, execution qualification or activation
readiness. Run with host-systemd access; unavailable commands remain explicit in
the report. The M09 user-scope probe command above still cannot qualify a system
deployment.

The additional offline boundary checks can be run independently:

```sh
.venv/bin/python -m unittest tests.test_m10 -v
```

### Deploy and verify the guarded qualification service

The [guarded M10 implementation](nnfx_practice/qualification.py) uses the existing
`nnfx-practice@practice-a.service`, master, children, notebook and lifecycle. The
default broker stays GET-only. Live qualification additionally requires a
root-owned plan at `/etc/nnfx-practice/qualification/practice-a.json`. Installation
never creates that plan, initializes Q0, activates a notebook or starts timers.
The [disabled example](deploy/qualification-plan.example.json) deliberately has
pending identities/evidence and cannot authorize execution.

Run these commands **from the administrator terminal**, in order, proceeding
only after the previous command succeeds. They deploy code and run broker-free
checks; they do not arm qualification or send orders:

```sh
sudo python3 /home/codexdev/projects/nnfx-practice-lab/deploy/install.py --registry /home/codexdev/projects/nnfx-practice-lab/config.toml
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_system.py
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m10_deployment.py
```

Retain both JSON reports. Require `fixture_checks_passed: true` with no cleanup
errors, then `deployment_gate_checks_passed: true` with no cleanup errors. The
second probe requires absent qualification plans, inactive controllers, disabled
ordinary timers and absent actual notebooks. It temporarily denies all network,
credential and notebook access on the actual controller, observes two missing-plan
rejections with exit status 2 and no restart, then removes only its own runtime
drop-in. It does not substitute for the M09 controller/maintenance fixture probe.
Unverified or failed host results remain pending. The owner has now completed
these commands successfully: system report `nnfx-m09-system-c7865da7339e.json` and
unarmed-service report `deployment-1053f8036c25.json` both passed with no cleanup
errors. This session's own sudo denial remains an access limitation; it does not
invalidate the owner's administrator results. Do not repeat deployment for the
standalone preparation tool below; application/strategy code is unchanged.

The preparation tool below copies reviewed evidence to root-owned regular files
under `/etc/nnfx-practice/qualification/evidence`, readable by `nnfx-read`. It uses
root-owned directories with no group/other write access (for example root:
nnfx-read mode 0750) and files mode 0640. All ancestors must also be root-owned
and protected; checkout paths, symlinks and hard links are rejected. Keep the
plan disabled while completing its identities and reviewing each prerequisite.
The account digest is the M04/private report's binding digest, never a credential.
`code_sha256` is `qualification.code_identity()` from the installed package;
`config_sha256` hashes the deployed public registry. Bind the current boot/kernel,
unchanged canonical manifest, account/notebook and an explicit run ID and weekday
16:50 New York instant expressed in UTC.

Each evidence entry must have its actual file hash and reviewed `status: passed`.
The service also checks the document contents: qualified strategy/386-candle and
28-pair account preflights, unchanged essential system-controller code/units and
observed writer dispatch/maintenance, private binding/reader denial, the recorded
conditional Python 01 owner authority and initial account-activity resolution.
The resolution document needs `status`, `account_binding_sha256` and a meaningful
`explanation`; fresh Q0 broker reads still reject outstanding trades or orders.
Changing code, registry, binding, boot/kernel, evidence or units requires review
and affected re-verification. A root-reviewed status cannot replace an unobserved
result. Remaining final M09 checks stay open independently.

This command checks the protected plan and host controls without loading private
settings, opening notebooks, contacting OANDA or arming execution. A valid disabled
plan may be inspected; the report always says `qualification_ready: false`
because private binding and Q0 have not been checked:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B -m nnfx_practice.host qualification-check practice-a
```

After the initial prerequisites are verified, use the Q0 initialization wrapper
below. It uses the existing maintenance exclusion and a GET-only initialization
permit, verifies the saved Q0 against the reviewed clearance, and restores the
original disabled plan. Ordinary activation remains unavailable.

Reopening preserves Q0/history/cursor and reconciles forward. For an initialized,
unactivated notebook, a **dated one-time timer** must dispatch the same controller
service at the plan's 16:50 instant, with `AccuracySec=1s`, `Persistent=false`
and no restart. The ordinary recurring timer stays disabled/inactive. No such
qualification timer has been prepared or started at this handoff. Manual shell
execution cannot qualify: dispatch checks the actual system service PID and
invocation ID, writer identity and start minute. A durable claim consumes that
controller's session before broker access; failure, process death or a new run ID
cannot replay it. Reconcile and review uncertain outcomes rather than retrying.

Qualification responses and per-stage raw candle captures are kept as private
JSONL under `/var/lib/nnfx-practice/var/qualification/<controller>/<run-id>.jsonl`,
separate from notebook storage. Requests use only the accepted account-bound
market/stop, target/stop-update and targeted-close operations, JSON payloads and
the practice host; redirects and uncertain requests are not retried. The
[OANDA order](https://developer.oanda.com/rest-live-v20/order-ep/),
[trade](https://developer.oanda.com/rest-live-v20/trade-ep/) and
[development](https://developer.oanda.com/rest-live-v20/development-guide/)
contracts were rechecked. Account-specific compatibility, actual fills/protection,
margin and reconciliation remain execution checks, including Trade 1 TP and
confirmed Trade 2 stop-to-entry. No Trade 2 resizing fallback is added.
Ordinary execution and activation remain blocked even with a qualification permit.

### Prepare a disabled Python 01 qualification plan

The [administrator preparation tool](tests/check_m10_preparation.py) checks the
current installed/source identities and supplied deployment reports, then stages
a writer-only account check through the existing maintenance exclusion. The
default GET-only broker makes **one account-scoped GET**. No notebook is opened,
no Q0/A0 is created and no order or timer is enabled. The private binding must
match reviewed M04 before that request. Existing trades/orders or a transaction
boundary/balance change since M04 leaves account clearance pending for owner
review; the tool does not close, adopt or explain away activity. Failed/uncertain
reads and maintenance failures remain pending and are retained.

If all initial prerequisite checks pass, the tool copies the actual reviewed
evidence, fills identities/hashes and writes the protected plan with
`enabled: false`. It then inspects that disabled plan without loading credentials
or obtaining an execution permit. Existing plans and reports are never replaced.
The current reviewed receipt binds those reports and application hashes to the
inspected boot/kernel. A changed host context requires affected re-verification;
preparation cannot silently inherit evidence from before a restart or upgrade.
The account report and preparation metadata are retained privately under
`var/verification/m10-preparation` in this checkout. Administrator execution has
now passed as `m10-preparation-f98a28a3a85e`: one HTTP-200 account GET, zero open
trades/orders, unchanged transaction/balance boundary and a valid disabled plan.
These are practice read-only and host results; actual execution remains pending.
The preparation-time `qualification_ready: false` inspection flag was expected
and does not describe subsequent Q0 initialization/arming. Preserve this completed preparation rather than
running the creation command again against its existing plan.

The completed preparation used the following command. It requires an absent
plan; preserve the existing preparation and Q0 rather than recreating either:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/check_m10_preparation.py \
  --system-report /home/codexdev/projects/nnfx-practice-lab/var/verification/m09-system/nnfx-m09-system-c7865da7339e.json \
  --deployment-report /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-integration/deployment-1053f8036c25.json \
  --dispatch-at 2026-11-19T21:50:00+00:00
```

That UTC instant is **Friday 20 November 2026 at 08:50 Melbourne**, Thursday at
16:50 New York. It binds a proposed disabled qualification plan; it does not
schedule a qualification run. The separate broker-free observer remains armed
for that window. A past instant is rejected without catch-up. After preparation,
review the actual clearance/inspection results before any later enabling, Q0
initialization or explicit one-time qualification dispatch. Ordinary scheduled
trading stays disabled throughout qualification and activation review.

### Initialize qualification Q0 and leave the plan disabled

The [initialization wrapper](tests/initialize_m10_qualification.py) checks the exact
prepared plan hash, protected clearance, all initial evidence and current host
controls. It refuses any existing notebook or sidecar, preserving interrupted
attempts for review. It temporarily sets the plan flag for the dedicated writer's
GET-only initialization permit, calls the existing lifecycle under maintenance,
then restores the original disabled plan bytes. The initializer also rejects
broker mutations independently of that flag. No controller dispatch or timer
creation/start occurs. Ordinary activation remains unset.

From the administrator terminal, initialize the reviewed preparation:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/initialize_m10_qualification.py \
  --prepared /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-preparation/m10-preparation-f98a28a3a85e-prepared.json
```

Require `status: passed`, `matches_reviewed_clearance: true`,
`disabled_plan_restored: true`, inactive ordinary controls and no ordinary
activation. The wrapper retains its intent and result privately under
`var/verification/m10-initialization`. Its read-only verification checks Q0's
purpose, reconciliation status, snapshot/transaction/cursor agreement, unchanged
balance/binding and empty run/attempt/issue records. Changed or unknown results
remain pending. It never deletes a notebook, resets Q0/cursor/history or retries
an interrupted attempt; inspect preserved state before recovery.

The administrator ran this wrapper successfully as `m10-q0-3a24c7c4771c`: Q0
`c245f517b15448cabb2edbb5336a53aa` and cursor `2249` agree, the clearance/binding
matches, ordinary activation is unset and the disabled plan was restored. Preserve
that notebook and report; do not rerun the initial creation path. The separate
dated one-time qualification timer is now armed as recorded below under the
existing M10 authority. The ordinary recurring timer stays disabled, and
remaining final host checks, actual execution evidence and activation review
remain required.

### Arm one initial practice qualification session

The [initial-session armer](tests/arm_m10_qualification.py) uses the existing M10
authority. It checks the actual Q0 report, protected plan/evidence and current
notebook through read-only SQL before enabling anything. It verifies the original
baseline, cursor, binding/manifest, actual writer/readers permissions and absence
of activation, prior runs/attempts/issues or a session claim. Changed code, host
context, metadata or prior activity blocks this initial-session path; it does not
reset history or rearm an existing attempt.

The administrator completed this step on 20 November at 07:58 Melbourne. Its
[actual receipt](var/verification/m10-arming/m10-arm-567a9f082b81.json) and independent
[timer inspection](var/verification/m10-arming/host-after-arming-20261120.json)
confirmed the dated timer was waiting; it has since dispatched and elapsed.
**Do not rerun this command or start the
controller manually.** The command remains documented for the retained procedure:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/arm_m10_qualification.py \
  --initialization /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-initialization/m10-q0-3a24c7c4771c.json
```

**This command arms practice execution for Friday 20 November 2026 at 08:50
Melbourne (19 November 16:50 New York).** It enables the date-bound qualification
plan and starts one new dated timer targeting `nnfx-practice@practice-a.service`.
That service may place Python 01 practice orders under the unchanged selected
strategy, 28-pair sequence and per-leg risk rules. The armer itself sends no broker
request. It never starts or enables the ordinary recurring timer, changes strategy
or activates A0. No additional execution approval is required for this recorded
scope; verify the actual receipt and live prerequisites before proceeding.

Require `status: armed`, inactive ordinary controls, a static qualification timer
in `active/waiting` state and an exact next expiry at the plan's instant. The
timer has 1-second accuracy, no random delay, no persistence, no recurring calendar
and no boot-install target. The service retains `Restart=no`, PID/invocation
checks, the existing notebook lock and durable per-session claim. A past date or
attempted session cannot be replayed. No signal is forced for qualification.

Intent/result metadata is retained privately under `var/verification/m10-arming`.
Failures before any start attempt restore the disabled plan/remove only confirmed
unused artifacts when state is known safe. After an uncertain start the tool
preserves evidence and leaves actual service control to investigation; it does
not retry, stop a possible trading run or rewind Q0. Review pending outcomes.
This armer has passed offline, unit-parser and actual administrator checks. The
single initial session completed without entry signals or orders. Actual traded
execution outcomes remain unexercised. No
application reinstall is needed. Remaining M09 checks and final integration/
activation review still apply. The separate broker-free observation window ends
at 09:05 Melbourne; collection/review passed sampled wakefulness and dispatch,
while unattended conditions/startup and final qualification remain open.

### Review the completed qualification session

The administrator completed protected collection as
[`protected-review-d9980f9a89ee.json`](var/verification/m10-review-20261120/protected-review-d9980f9a89ee.json).
Review confirms a completed **14.112-second** run, 28 ordered valid entry captures,
and no fresh C1 event on any pair: **zero orders/fills/issues**. All saved C1/ATR
calculations replay exactly. Account balance and cursor remain unchanged from Q0.
Broker-free dispatch and sampled wakefulness passed; unattended conditions remain
unconfirmed (owner Unsure). Startup without login has since passed on kernel -43
after the administrator restart; repeat affected system checks on that kernel.

The ordinary timer remains disabled/inactive. The first qualification timer has
elapsed, and the reviewed continuation below is now armed for 21 November 08:50
Melbourne. Actual two-leg execution,
management, restrictions/margin, charges and dashboard/final integration remain
pending. Preserve Q0/history and the completed run; the initial-session armer
cannot be reused against existing run history. Use the
[prepared no-entry continuation](#continue-qualification-after-the-no-entry-session)
under the existing conditional authority.

The retained read-only collection command is below; no repeat is needed for this
completed export. It collects both protected evidence sets without contacting the broker:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-review-20261120/collect_review.py
```

The collector opens the existing notebook in read-only/query-only mode, exports
its records and qualification ledger totals, retains broker capture identities,
and assesses the broker-free observer samples. It verifies inactive ordinary
controls before and after collection, redacts private values and saves a private
report in `var/verification/m10-review-20261120`. It reads no credentials, sends no
broker request, changes no service/timer/plan, and creates or repairs no notebook
or sidecar. Missing/unknown evidence remains pending. `status: collected` confirms
collection only; review actual run/attempt/fill/issue and observation results
before any qualification finding. Do not rearm, retry orders or activate A0 from
this result. No application reinstall is required.

### Continue qualification after the no-entry session

The [continuation command](tests/continue_m10_qualification.py) has now passed
actual administrator execution as
[`m10-continuation-50b6c663b690.json`](var/verification/m10-continuation/m10-continuation-50b6c663b690.json).
One fresh account GET passed with no trades/orders and unchanged balance/boundary.
Independent inspection confirms the dated timer is waiting; ordinary trading
remains disabled. **Do not rerun the arming command.** It is restricted
to reviewed completed no-entry history. It checks the existing protected plan/
claim, current notebook through read-only SQL, current application identity and
successful current-boot system fixtures. It refuses prior entries/attempts/issues,
activation, changed history or an already claimed target session.

The command makes **one account-scoped GET under maintenance**, using the existing
GET-only worker. Trades/orders or a changed balance/transaction boundary leave
the continuation pending for review. On a pass it archives the old protected
plan and review, retains Q0/cursor/all runs/old claims, and creates a fresh dated
plan with current boot/kernel/controller evidence. It starts one static timer for
the existing controller service, with no persistence, restart, boot installation
or recurring schedule. Before-start failures restore only confirmed safe unused
setup; uncertain starts preserve evidence without automatic retry or service stop.

The completed command is retained for review:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B \
  /home/codexdev/projects/nnfx-practice-lab/tests/continue_m10_qualification.py \
  --previous-review /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-review-20261120/protected-review-0113463688d3.json \
  --system-report /home/codexdev/projects/nnfx-practice-lab/var/verification/m09-system/nnfx-m09-system-daed36cb06d3.json \
  --dispatch-at 2026-11-20T21:50:00+00:00 \
  --arm
```

**This arms Python 01 practice qualification for 21 November 08:50 Melbourne
(20 November 16:50 New York), not ordinary trading.** The future service can place
authorized practice orders if the unchanged strategy supplies an eligible fresh
signal. The command itself sends no mutation and forces no signal. Require
`status: armed`, exact `active/waiting` next expiry and inactive ordinary controls;
retain the receipt under `var/verification/m10-continuation`. No application
reinstall is needed. A later session with actual trades or unresolved activity
requires its own reviewed continuation; this narrow no-entry path will refuse it.
Actual fills/protection, scheduled TP/stop management, remaining final integration
and guarded ordinary activation/dispatch still have to be completed. Tomorrow's
qualification session is not a promise of ordinary activation by that time.

### Observe the armed continuation and collect its results

The qualification timer is now waiting for **21 November 08:50 Melbourne**.
The earlier wakefulness samples belong to kernel -42. Capture the corresponding
window on the current -43 kernel with a fresh isolated observer. Startup without
login already passed; **do not reboot again** for this step.

From the administrator terminal, remove only the reviewed old observer units
(its data/code remain retained), then prepare the next broker-free window:

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_observation.py cleanup /home/codexdev/projects/nnfx-practice-lab/var/verification/m09-observation/nnfx-m09-observe-ba7d65c9bebd.json &&
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/tests/check_m09_observation.py prepare
```

This sequence sends no broker request and changes neither the armed qualification
timer nor ordinary controls. Require the printed target to match **21 November
08:50 Melbourne** and retain the new metadata path. New observer setup is pending
until its actual receipt is reviewed. Leave the server running through 09:05;
record actual intervention/session context honestly when reviewing the result.

After **21 November 09:05 Melbourne**, use the
[new-run read-only collector](var/verification/m10-continuation-armed/collect_followup.py)
with `--observation` followed by that exact new metadata path. The earlier
collector above remains the original-session procedure; this collector selects
run `m10-b51f50d1eae44c088721c3a675831798` and the **20 November New York** claim/
capture, verifies the current plan identity, and reports the requested run
separately from older completed runs. It requires the matching window and current
boot/kernel. Example (replace the metadata argument with the printed path):

```sh
sudo /opt/nnfx-practice/.venv/bin/python -I -B /home/codexdev/projects/nnfx-practice-lab/var/verification/m10-continuation-armed/collect_followup.py --observation NEW_METADATA_PATH
```

It reads existing notebook/claim/captures and observer samples without loading
credentials, contacting the broker or changing controls. Missing/uncertain
outcomes remain pending. A new observer's pending startup marker does not erase
the separately retained completed startup-without-login proof. `status: collected`
is evidence collection, not completed M10 or ordinary activation.

## Run the read-only practice preflight

With the owner's read-only authorisation and intended dedicated practice account,
run the account pass from the project root. Set the selected controller's private
account ID, token and home currency in `.env`. The account pass can run while M03
strategy qualification is pending. Obtain the division from the intended account's
portal or broker confirmation and pass a non-secret evidence reference. If that
source identifies the platform, pass `--platform native-v20` or
`--platform mt4-associated`.

```sh
umask 077
mkdir -p var/preflight
python3 -m nnfx_practice.preflight practice-a \
  --division "OANDA division from account profile" \
  --profile-reference "non-secret account-profile evidence reference" \
  > var/preflight/account-YYYY-MM-DD.json
```

Once M03 has a qualified manifest and matching configured lookback, start the
candle pass during the weekday 16:50 New York minute. Use a new report filename
for each attempt.

```sh
python3 -m nnfx_practice.preflight practice-a --candles \
  > var/preflight/candles-YYYY-MM-DD.json
```

The reports share an account binding hash and give the result for each pass.
An incomplete pass exits with status 1. A configuration error exits with
status 2. Keep actual account evidence private under `var/preflight/`. See the
[M04 verification record](docs/STATUS.md#m04-read-only-preflight).
