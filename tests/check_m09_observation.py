"""Stage/check/remove broker-free boot and intended-calendar observations.

Administrator setup only enables isolated observation units. It never reboots,
changes power policy, reads credentials, opens notebooks or starts ordinary units.
"""

import argparse
from datetime import UTC, datetime, timedelta
import grp
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
from uuid import uuid4
from zoneinfo import ZoneInfo

from nnfx_practice.config import read_registry


ROOT = Path(__file__).resolve().parents[1]
CODE, DATA = Path('/opt/nnfx-practice'), Path('/var/lib/nnfx-practice')
PYTHON = CODE / '.venv/bin/python'
NEW_YORK = ZoneInfo('America/New_York')
MELBOURNE = ZoneInfo('Australia/Melbourne')


def next_slot(now):
    local = now.astimezone(NEW_YORK)
    candidate = local.replace(hour=16, minute=50, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def valid_prefix(prefix):
    if not isinstance(prefix, str) or not re.fullmatch(r'nnfx-m09-observe-[a-f0-9]{12}', prefix):
        raise ValueError('Expected isolated observation prefix')
    return prefix


def unit_texts(service, timer, *, prefix, fixture, worker, target):
    valid_prefix(prefix)
    original = f'ExecStart={PYTHON} -m nnfx_practice.host --root {DATA} dispatch %i'
    if service.count(original) != 1:
        raise ValueError('Unreviewed controller command')
    service = service.replace(original, f'ExecStart={PYTHON} -I -B {worker} {fixture} %i').rstrip() + '\n'
    service = service.replace('Description=NNFX practice controller %i', 'Description=NNFX broker-free host observation %i')
    # Additional observer barriers; production settings are not changed.
    service += f'InaccessiblePaths=-{DATA}/.env {DATA}/var/notebooks\nIPAddressDeny=any\n\n[Install]\nWantedBy=multi-user.target\n'
    calendar = target.astimezone(NEW_YORK).strftime('%Y-%m-%d 16:50:00 America/New_York')
    old_calendar = 'OnCalendar=Mon..Fri *-*-* 16:50:00 America/New_York'
    if timer.count(old_calendar) != 1:
        raise ValueError('Unreviewed controller calendar')
    timer = timer.replace(old_calendar, 'OnCalendar=' + calendar)
    timer = timer.replace('Unit=nnfx-practice@%i.service', f'Unit={prefix}@%i.service')
    # An exec monitor reaches active immediately and cannot hold boot targets
    # waiting for the whole overnight sampling window like a oneshot would.
    monitor = '[Service]\nType=exec\n'
    return service, timer, monitor


def assess(metadata, rows, now):
    target = datetime.fromisoformat(metadata['target'])
    start = datetime.fromisoformat(metadata['window_start'])
    end = datetime.fromisoformat(metadata['window_end'])
    uid = metadata['writer_uid']
    good = [row for row in rows if row.get('uid') == uid and row.get('invocation_id')
            and isinstance(row.get('boot_id'), str) and row['boot_id']]
    boots = [row for row in good if row.get('phase') == 'boot_marker'
             and row.get('boot_id') != metadata['setup_boot_id']
             and row.get('logins', {}).get('known') is True
             and row['logins'].get('user_sessions') == 0]
    dispatch = [row for row in good if row.get('phase') == 'dispatch'
                and target <= datetime.fromisoformat(row['at']) < target + timedelta(minutes=1)]
    samples = sorted((row for row in good if row.get('phase') == 'heartbeat'), key=lambda row: row['at'])
    before = [row for row in samples if datetime.fromisoformat(row['at']) <= start]
    after = [row for row in samples if datetime.fromisoformat(row['at']) >= end]
    wake = 'pending'
    reason = 'Await complete monitoring window'
    unattended = 'pending'
    if before and after:
        first, last = before[-1], after[0]
        selected = [row for row in samples if first['at'] <= row['at'] <= last['at']]
        times = [datetime.fromisoformat(row['at']) for row in selected]
        offsets = [row.get('suspend_offset') for row in selected]
        uncertainties = [row.get('clock_uncertainty') for row in selected]
        numeric = all(type(value) in (int, float) and math.isfinite(value) for value in offsets + uncertainties)
        gaps_ok = all(0 < (b-a).total_seconds() <= 45 for a,b in zip(times,times[1:]))
        same_boot = len({row.get('boot_id') for row in selected}) == 1
        if (numeric and same_boot and gaps_ok and min(uncertainties) >= 0 and max(uncertainties) <= 0.01
                and max(offsets)-min(offsets) <= 0.25):
            wake, reason = 'passed', 'Continuous window samples; no detected suspend (offset tolerance 250 ms)'
        else:
            wake, reason = 'not_proven', 'Sampling gap, reboot, clock uncertainty or detected suspend in window'
        context = [row.get('logins', {}) for row in selected]
        unattended = ('no_user_sessions_observed' if all(row.get('known') is True and row.get('user_sessions') == 0 for row in context)
                      else 'operator_confirmation_required')
    elif now >= end:
        wake, reason = 'not_proven', 'Window ended without covering samples'
    return dict(startup_without_login='passed' if boots else 'pending',
                scheduled_dispatch='passed' if dispatch else 'not_observed' if now >= target+timedelta(minutes=1) else 'pending',
                wakefulness=wake, wakefulness_reason=reason,
                unattended_context=unattended,
                boot_markers=boots, dispatch_markers=dispatch,
                kernel_changed=any(row.get('kernel') != metadata['setup_kernel'] for row in good))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('prepare')
    for action in ('check', 'cleanup'):
        commands.add_parser(action).add_argument('metadata', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Administrator access is required; nothing was changed')
    evidence = ROOT / 'var/verification/m09-observation'
    evidence.mkdir(parents=True, exist_ok=True)

    def run(values, *, check=True):
        return subprocess.run([str(v) for v in values], capture_output=True, text=True, check=check, timeout=30)

    def ctl(*values, check=True):
        return run(['systemctl', '--no-ask-password', *values], check=check)

    def ordinary_inactive():
        for controller in read_registry(DATA):
            for kind in ('service', 'timer'):
                result = ctl('show', f'nnfx-practice@{controller}.{kind}', '--property=LoadState,ActiveState,UnitFileState,Job')
                state = dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
                if (state.get('LoadState') != 'loaded' or state.get('ActiveState') not in ('inactive','failed')
                        or state.get('Job') not in ('','0') or 'enabled' in state.get('UnitFileState','')):
                    raise ValueError('Ordinary controller/timer is not safely inactive')

    def save(path, body):
        with path.open('x') as target:
            json.dump(body, target, indent=2)
            target.write('\n')
        os.chown(path, ROOT.stat().st_uid, ROOT.stat().st_gid)
        path.chmod(0o600)

    if args.action == 'prepare':
        ordinary_inactive()
        if list(Path('/etc/systemd/system').glob('nnfx-m09-observe-*')):
            raise ValueError('An observation is already staged; check or clean it before preparing another')
        if run(['timedatectl','show','--property=NTPSynchronized']).stdout.strip() != 'NTPSynchronized=yes':
            raise ValueError('Synchronized clock is required')
        target = next_slot(datetime.now(UTC))
        prefix = valid_prefix('nnfx-m09-observe-' + uuid4().hex[:12])
        fixture = DATA / 'var/verification' / prefix
        staged = CODE / 'verification' / prefix
        writer = pwd.getpwnam('nnfx-run')
        group = grp.getgrnam('nnfx-read').gr_gid
        for directory, mode in ((fixture,0o750),(fixture/'var',0o750),(fixture/'var/notebooks',0o2750)):
            directory.mkdir(mode=mode)
            os.chown(directory,writer.pw_uid,group)
            directory.chmod(mode)
        staged.mkdir(parents=True,mode=0o755)
        worker = staged / 'm09_observation_worker.py'
        shutil.copyfile(ROOT/'tests/m09_observation_worker.py',worker)
        worker.chmod(0o644)
        session_program = ('import json,runpy; print(json.dumps(runpy.run_path('
                           + repr(str(worker)) + ',run_name="observation_preflight")["login_state"]()))')
        session_preflight = json.loads(run(['runuser','-u','nnfx-run','--',PYTHON,'-I','-B','-c',session_program]).stdout)
        if session_preflight.get('known') is not True:
            raise ValueError('Writer cannot establish session metadata; review before scheduling a restart')
        (fixture/'config.toml').write_text(''.join(
            f'[[experiments]]\ncontroller_id="{role}"\nnotebook_id="observer-{role}"\nnotebook_name="Host observation {role}"\n'
            f'strategy_version="t3_bandpass_v1"\nconnection_key="OBS_{role.upper()}"\n'
            for role in ('boot','monitor','scheduled')))
        os.chown(fixture/'config.toml',0,group)
        (fixture/'config.toml').chmod(0o640)
        metadata = dict(prefix=prefix,fixture=str(fixture),staged_worker=str(worker),writer_uid=writer.pw_uid,
                        target=target.isoformat(),target_melbourne=target.astimezone(MELBOURNE).isoformat(),
                        window_start=(target-timedelta(minutes=10)).isoformat(),
                        window_end=(target+timedelta(minutes=15)).isoformat(),
                        setup_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        setup_kernel=os.uname().release,created_at=datetime.now(UTC).isoformat(),
                        session_metadata_preflight=session_preflight,
                        broker_requests=0,ordinary_units_started=False,reboot_requested=False,
                        source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()).hexdigest() for p in
                                       (Path(__file__),ROOT/'tests/m09_observation_worker.py')})
        save(fixture/'observation.json',metadata)
        # Worker reads only this non-secret observation manifest.
        os.chown(fixture/'observation.json',0,group)
        (fixture/'observation.json').chmod(0o640)
        service_path=Path('/etc/systemd/system/nnfx-practice@.service')
        timer_path=Path('/etc/systemd/system/nnfx-practice@.timer')
        if (service_path.read_bytes() != (ROOT/'deploy/nnfx-practice@.service').read_bytes()
                or timer_path.read_bytes() != (ROOT/'deploy/nnfx-practice@.timer').read_bytes()):
            raise ValueError('Installed controller units differ from reviewed templates')
        service,timer,monitor=unit_texts(service_path.read_text(),timer_path.read_text(),prefix=prefix,
                                       fixture=fixture,worker=worker,target=target)
        paths = {Path('/etc/systemd/system')/(prefix+'@.service'):service,
                 Path('/etc/systemd/system')/(prefix+'@.timer'):timer,
                 Path('/etc/systemd/system')/(prefix+'@monitor.service.d/observer.conf'):monitor}
        manifest=evidence/(prefix+'.json')
        metadata['unit_hashes']={str(path):sha256(body.encode()).hexdigest() for path,body in paths.items()}
        metadata['definition_only']=True
        save(manifest,metadata)
        enabled=[prefix+'@boot.service',prefix+'@monitor.service',prefix+'@scheduled.timer']
        created=[]
        try:
            for path,body in paths.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('x') as file:
                    file.write(body)
                path.chmod(0o644)
                created.append(path)
            ctl('daemon-reload')
            ctl('enable',*enabled)
            ctl('start','--no-block',prefix+'@monitor.service',prefix+'@scheduled.timer')
            ordinary_inactive()
            metadata['preparation_status']='staged; observation pending'
        except BaseException:
            ctl('stop',*enabled,prefix+'@scheduled.service',check=False)
            ctl('disable',*enabled,check=False)
            for path in reversed(created):
                path.unlink()
            dropin=Path('/etc/systemd/system')/(prefix+'@monitor.service.d')
            if dropin.exists():
                dropin.rmdir()
            ctl('daemon-reload',check=False)
            raise
        # Preserve immutable setup manifest; append a separate preparation result.
        save(evidence/(prefix+'-prepared.json'),dict(metadata=metadata,host_qualification_complete=False))
        print(json.dumps(dict(metadata=str(manifest),target_melbourne=metadata['target_melbourne'],
                              reboot_requested=False,ordinary_trading_enabled=False,observation='pending')),flush=True)
        return

    metadata=json.loads(args.metadata.read_text())
    prefix=valid_prefix(metadata['prefix'])
    fixture=DATA/'var/verification'/prefix
    if metadata.get('fixture') != str(fixture):
        raise ValueError('Observation data path differs from isolated fixture')
    units=[prefix+'@boot.service',prefix+'@monitor.service',prefix+'@scheduled.timer']
    if args.action == 'cleanup':
        ctl('stop',*units,prefix+'@scheduled.service')
        ctl('disable',*units)
        expected=[Path('/etc/systemd/system')/(prefix+'@.service'),Path('/etc/systemd/system')/(prefix+'@.timer'),
                  Path('/etc/systemd/system')/(prefix+'@monitor.service.d/observer.conf')]
        for path in expected:
            if path.exists():
                if sha256(path.read_bytes()).hexdigest() != metadata['unit_hashes'][str(path)]:
                    raise ValueError('Observation unit changed; review before removing')
                path.unlink()
        dropin=expected[-1].parent
        if dropin.exists():
            dropin.rmdir()
        ctl('daemon-reload')
        output=evidence/(prefix+'-cleanup-'+uuid4().hex[:6]+'.json')
        save(output,dict(cleanup_complete=not list(Path('/etc/systemd/system').glob(prefix+'*')),
                         retained_data=str(fixture),broker_requests=0))
        print(json.dumps(dict(report=str(output),fixture_data_retained=True)),flush=True)
        return

    ordinary_inactive()
    rows=[]
    for role in ('boot','monitor','scheduled'):
        path=fixture/'var'/f'{role}.jsonl'
        if path.exists():
            rows.extend(json.loads(line) for line in path.read_text().splitlines())
    result=assess(metadata,rows,datetime.now(UTC))
    result.update(metadata=str(args.metadata),host_qualification_complete=False,execution_qualified=False,
                  broker_requests=0,ordinary_trading_enabled=False,
                  note='If kernel changed after reboot, repeat the system fixture probe before reusing its host-security evidence.')
    output=evidence/(prefix+'-check-'+uuid4().hex[:6]+'.json')
    save(output,dict(result=result,metadata=metadata,observations=rows,
                     units=ctl('show',*units,'--property=Id,ActiveState,UnitFileState,MainPID').stdout))
    print(json.dumps(dict(report=str(output),**result)),flush=True)


if __name__ == '__main__':
    main()
