# NNFX Practice Lab

Forward-test a manually selected NNFX C1/Exit combination on independent OANDA
practice accounts. A Python controller records actual broker results in SQLite;
the Flask/Jinja dashboard observes those records.

[Current status](docs/STATUS.md) separates checkout implementation, dated deployment
observations and routine follow-up. The practice application is running; the owner
has removed M10 from the delivery plan.

## Navigation

| Document | Purpose |
| --- | --- |
| [Brief](PROJECT_BRIEF.md) | Accepted product and trading rules |
| [Working guidance](AGENTS.md) | Safeguards, ownership and task reading routes |
| [Architecture](docs/ARCHITECTURE.md) | Runtime/workflow, candles/signals and dashboard presentation |
| [Detailed design](docs/DETAILED_DESIGN.md) | State, sizing, broker and accounting contracts |
| [Acceptance](docs/ACCEPTANCE.md) | Required scenarios and relevant tests |
| [Plan](docs/IMPLEMENTATION_PLAN.md) | Delivery history, operating checklist and reusable feature brief |
| [Operations](docs/OPERATIONS.md) | Host maintenance, deployment and activation gates |
| [Verification references](docs/VERIFICATION.md) | Retained evidence outside routine reading |
| [Python 02](docs/PYTHON_02.md) / [Python 03](docs/PYTHON_03.md) | Selected experiments and integration constraints |

## Code-and-test map

Use the requirement link for the contract and the test link for controlled cases.
★ marks three representative implementation/test pairs. These paths describe
coverage, not observed deployment or complete acceptance.

| Feature area | Authoritative requirement | Implementation entry point | Tests |
| --- | --- | --- | --- |
| Bindings and storage | [Configuration/records](docs/DETAILED_DESIGN.md#configuration-and-records) | [config](nnfx_practice/config.py), [notebook](nnfx_practice/notebook.py) | [M01](tests/test_m01.py) |
| Candles and strategies | [Calculation contract](docs/ARCHITECTURE.md#candle-and-signal-inputs) | [candles](nnfx_practice/candles.py), [strategy](nnfx_practice/strategy.py) | [selected strategy](tests/test_m03_selected.py), [anchored history](tests/test_python03.py) |
| Broker reconciliation ★ | [Import policy](docs/DETAILED_DESIGN.md#reconciliation-procedure) | [reconciliation ★](nnfx_practice/reconciliation.py), [transaction comparison](nnfx_practice/transaction_records.py) | [M02 ★](tests/test_m02.py), [transaction variants](tests/test_transaction_import.py) |
| Open-trade management | [Management rules](PROJECT_BRIEF.md#manage-open-trades) | [manage_open](nnfx_practice/manage_open.py) | [M05](tests/test_m05.py) |
| Sizing and entry | [Sizing/protection](docs/DETAILED_DESIGN.md#sizing-and-two-leg-entry) | [sizing](nnfx_practice/sizing.py), [entry](nnfx_practice/entry.py) | [M06](tests/test_m06.py) |
| Master and disposition ★ | [State rules](docs/DETAILED_DESIGN.md#state-rules) | [master ★](nnfx_practice/master.py), [disposition](nnfx_practice/disposition.py) | [M07 ★](tests/test_m07.py) |
| Qualification and activation | [Lifecycle](docs/IMPLEMENTATION_PLAN.md#qualification-records-and-ordinary-activation) | [qualification](nnfx_practice/qualification.py), [ordinary](nnfx_practice/ordinary.py) | [automatic qualification](tests/test_m10_automatic.py), [lifecycle](tests/test_m07.py) |
| Ledger and dashboard ★ | [Accounting](docs/DETAILED_DESIGN.md#monetary-records) / [presentation](docs/ARCHITECTURE.md#notebook-dashboard) | [ledger](nnfx_practice/ledger.py), [dashboard ★](nnfx_practice/dashboard.py) | [M08 ★](tests/test_m08.py), [M02](tests/test_m02.py) |
| Host and releases | [Operations](docs/OPERATIONS.md) | [host](nnfx_practice/host.py), [dashboard deployer](deploy/dashboard_deploy.py) | [M09](tests/test_m09.py), [deployer](tests/test_dashboard_deploy.py) |
| Independent experiments | [Python 02](docs/PYTHON_02.md) / [Python 03](docs/PYTHON_03.md) | [Python 02 installer](deploy/add_python02.py), [Python 03 installer](deploy/add_python03.py) | [Python 02](tests/test_python02.py), [Python 03](tests/test_python03.py) |

## Development and verification

Use Python 3.12+, SQLite 3.37+, New York tzdata and the dependencies in
[pyproject.toml](pyproject.toml). Native shared-WAL operation also needs
`SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`. Commands below are established from existing
scripts/configuration, not rerun for this documentation change. New USB paths
are source-checked but unexecuted. Use a unique task directory, never overwrite
evidence. Commands 2–6 use the checkout as working directory; 7–8 use the isolated
configuration root. No command below deploys or trades.

1. **Workspace/environment (setup; package access required).** Stop if the mount
   check fails. Reuse the installed checkout environment where suitable; for a
   new environment install the declared dependencies in a USB venv.

   ```sh
   cd /home/codexdev/projects/nnfx-practice-lab
   mountpoint -q /mnt/nnfx-usb || exit 1
   export NNFX_TASK_DATA=/mnt/nnfx-usb/development/data/nnfx-practice-lab/your-task
   umask 077
   mkdir -p "$NNFX_TASK_DATA"/tmp "$NNFX_TASK_DATA"/evidence "$NNFX_TASK_DATA"/root
   export TMPDIR="$NNFX_TASK_DATA/tmp" PYTHONDONTWRITEBYTECODE=1
   export UV_CACHE_DIR="$NNFX_TASK_DATA/cache/uv" PYTHONPATH="$PWD"
   export NNFX_PYTHON="$PWD/.venv/bin/python"
   # Only if a new environment is needed (requires uv):
   python3 -m venv --without-pip "$NNFX_TASK_DATA/venv"
   uv pip install --python "$NNFX_TASK_DATA/venv/bin/python" \
     'Flask>=3.1,<4' 'waitress>=3,<4'
   export NNFX_PYTHON="$NNFX_TASK_DATA/venv/bin/python"
   ```

2. **Offline suite.** Temporary notebooks use `TMPDIR`; success ends with `OK`.

   ```sh
   "$NNFX_PYTHON" -m unittest discover -v
   ```

3. **Offline trading/reconciliation focus.** Real components with scripted broker
   replies; success is `OK`, not account execution evidence.

   ```sh
   "$NNFX_PYTHON" -m unittest tests.test_m02 tests.test_transaction_import tests.test_m05 tests.test_m06 tests.test_m07 -v
   ```

4. **Offline dashboard focus.** Saves synthetic pages/rows on USB; success is `OK`.

   ```sh
   NNFX_M08_EVIDENCE_DIR="$NNFX_TASK_DATA/evidence/dashboard" \
     "$NNFX_PYTHON" -m unittest tests.test_m08 -v
   ```

5. **Offline Python 02 reference comparison.** Requires the retained sibling lab
   data and its environment; expected JSON `status: passed`. Other strategy
   comparison entry points and inputs are linked in [verification](docs/VERIFICATION.md#strategy-comparisons).

   ```sh
   /home/codexdev/projects/nnfx-indicator-lab/.venv/bin/python \
     -m tests.check_python02_reference --lab /home/codexdev/projects/nnfx-indicator-lab \
     --count 512 --output "$NNFX_TASK_DATA/evidence/reference-512.json"
   ```

6. **Local dashboard (service, no broker).** Requires an isolated registry and
   compatible fixture notebook under the USB root; missing data shows unavailable.
   GET `/controllers` and `/notebooks` should return 200. Stop with Ctrl-C.

   ```sh
   "$NNFX_PYTHON" -m nnfx_practice.dashboard --root "$NNFX_TASK_DATA/root" --port 8881
   ```

7. **Read-only account preflight (network/private credentials).** With existing
   intended-account authority and reviewed profile values, expect `status: passed`,
   exit 0; incomplete/configuration failures exit 1/2.

   ```sh
   cd "$NNFX_TASK_DATA/root"
   "$NNFX_PYTHON" -m nnfx_practice.preflight practice-a \
     --division "OANDA division from account profile" \
     --profile-reference "non-secret reviewed profile reference" --platform native-v20 \
     > "$NNFX_TASK_DATA/evidence/account.json"
   ```

8. **Read-only candle preflight (network).** Requires the qualified manifest/count
   and weekday 16:50 New York launch. Expect 28 valid windows and exit 0.

   ```sh
   "$NNFX_PYTHON" -m nnfx_practice.preflight practice-a --candles \
     > "$NNFX_TASK_DATA/evidence/candles.json"
   ```

Use [config.example.toml](config.example.toml) and [.env.example](.env.example) for
field formats, not runnable strategy defaults. The isolated root needs its own
`config.toml`, selected `strategies/<version>/manifest.json` and, only for broker
reads, an owner-only mode-0600 `.env`. Never copy live notebooks casually; see
[backup and maintenance](docs/OPERATIONS.md#maintenance-and-evidence-collection).
Host probes require separate systemd/admin access and are described in operations.

## Dashboard access

Connect through Tailscale to the [practice Controllers page](https://thinkbook-server.tail57730c.ts.net:8443/controllers)
or [Python 01 journal](https://thinkbook-server.tail57730c.ts.net:8443/notebooks/notebook-a).
The [indicator lab](https://thinkbook-server.tail57730c.ts.net/) has its own root.
Recorded setup forwards HTTPS 8443 to practice port 8879 and HTTPS 443 to lab
port 8878; trusted-LAN practice access is [port 8879](http://192.168.51.10:8879/controllers).
These are saved deployment addresses, not a new availability check.
