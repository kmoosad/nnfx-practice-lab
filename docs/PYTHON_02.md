# Python 02 experiment

Owner selected [research result a83ffe21-90eb-4674-99e3-7c80d6871a6c](http://192.168.51.10:8877/exit/results/a83ffe21-90eb-4674-99e3-7c80d6871a6c)
on 27 November 2026 under unchanged [practice rules](../PROJECT_BRIEF.md).
This document owns selection, integration boundaries, comparison and installation evidence;
[status](STATUS.md#python-02) owns current operation.

| Binding | Selection |
| --- | --- |
| Display / controller / notebook | Python 02 / `practice-b` / `notebook-b` |
| Strategy | `drm_adaptive_bandpass_v1`, 512 candles |
| C1 | Distributional Rank Momentum \| NAL: BullishFlip long / BearishFlip short |
| Exit | L2 Ehlers Adaptive BandPass: doLongExit closes shorts / doShortExit closes longs |
| Account / division | Native-v20 AUD Python 2 ending 003; owner-confirmed OANDA Australia Pty Ltd |
| Private prefix | `PRACTICE_B` |

The [installed registry entry](../deploy/python02-experiment.toml) and immutable
[manifest](../strategies/drm_adaptive_bandpass_v1/manifest.json) own exact parameters,
signal/source/dependency identities and count. Account/token remain private; a
screenshot balance never establishes Q0.

## Integration boundary

Saved conversions change import paths only; retain the exact registered Pine
dependency. Trade-sizing ATR remains the lab simple ATR(14), distinct from the
Exit indicator's internal ATR. Evaluate the saved completed-input confirmation
flags on the practice partial candle as accepted. Indicator position state is a
calculation input, not OANDA position evidence.

Explicit packaged strategy selection is used by management, entry, lifecycle and
qualification; no automatic/default selection or runtime lab import. The original
Python 01 manifest/files are unchanged.

## Calculation verification

All archived outputs/ATR match; 512 candles passed 6,244 windows and 144 modified
partials. The [packaged summary](../strategies/drm_adaptive_bandpass_v1/qualification.json)
and [comparison tool](../tests/check_python02_reference.py) own reproducible inputs;
[README command 5](../README.md#development-and-verification) gives the offline command.

## Installation and setup boundary

The [scoped installer](../deploy/add_python02.py) required original Python 01
protected-plan identity, unchanged binding, distinct verified account, matching
wheel and passing checks. Shared-code maintenance preserves existing notebook,
Q0/claims/schedules and refreshes protected code/configuration and host evidence.
Failure leaves scheduling stopped for investigation, not blind retry. The old
single-account installer/M10 migration cannot add another experiment.

Its [one-time bootstrap](../deploy/python02_bootstrap.py) captures its own 28-pair
weekday 16:50 New York evidence as native writer; daytime reads cannot substitute.
Only passed matching capture and fresh clear account permit guarded Q0 and a
protected qualification plan starting the next weekday. It never trades during
setup or enables ordinary activation. An exclusive receipt prevents replay after
failure/interruption; inspect it before recovery. Administrator execution is
separate from the login's dashboard-only deployment grant.

## Recorded installation evidence

On 27 November at 22:14 Melbourne, [USB evidence](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence)
retained clear intended-account AUD preflight (50,000.6603), 16 controller/9 setup
checks, 60-file wheel, native-system pass and receipt
`python02-618a04984fb7-deployment.json`. [Post-install check](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/post-deployment-check.json)
matched installed/source/package files and HTTP/HTTPS pages. Python 01 notebook,
sidecars/claims, authority, replay identity and schedule were preserved. Installation
made no broker requests, initialized no Q0 and started no trading run.

The owner restarted the dashboard manually in the frozen executed release; source
later included that restart and nine setup checks passed again. The interrupted
preliminary broader run is not an all-passing suite; its cross-account fixture
rejection was corrected before the focused pass. Development notebook integrity
was ok, Q0/A0 unset; those prepared records are not production initialization.

The [28 November observation](VERIFICATION.md#python-02-and-python-03-scheduled-setup-verification)
confirmed completed setup, Q0 and a timer awaiting its first trading run; no trading
execution had occurred. Status owns the recorded next expiry. Installation/bootstrap
are complete: do not rerun them. New evidence/private data belongs under the mounted
USB task path; the retained root is `/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/`.
