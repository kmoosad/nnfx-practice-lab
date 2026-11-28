"""Systemd maintenance exclusion and deployment entry points.

One practice execution path retains the established guarded schedule and claims.
No timer operation enables a timer at boot or changes its calendar.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess

from .config import ConfigurationError
from .control import MaintenanceDeferred
from .broker import BrokerError
from .disposition import DispositionRequired


class SystemdService:
    """Pause timer, runtime-mask this instance, then verify inactivity/jobs.

    Runtime masking does not stop a running service. Existing masks are preserved.
    A crash leaves the timer stopped and service masked for operator recovery.
    System mutations use the deployment's narrowly scoped sudoers grants. User
    scope is for broker-free host probes, not a substitute for system deployment.
    """

    def __init__(self, controller_id, *, user=False, prefix='nnfx-practice', runner=subprocess.run, extra_timers=(), timer=None):
        if not all(re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', value)
                   for value in (controller_id, prefix)):
            raise ConfigurationError('Invalid systemd controller identifier')
        self.service = f'{prefix}@{controller_id}.service'
        self.timer = timer or f'{prefix}@{controller_id}.timer'
        if any(not re.fullmatch(r'[a-z0-9_-]+@[a-z0-9_-]+\.timer', unit) for unit in (self.timer, *extra_timers)):
            raise ConfigurationError('Invalid additional controller timer')
        self.timers = (self.timer, *extra_timers)
        self._prior_timers = {}
        self.user, self.runner = user, runner
        self._mask_owned = False
        self._paused = False

    def _call(self, *args, mutate=False):
        command = ['systemctl', '--no-ask-password']
        if self.user:
            command.append('--user')
        elif mutate:
            command = ['sudo', '-n', '/usr/bin/systemctl', '--no-ask-password']
        try:
            result = self.runner([*command, *args], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            raise MaintenanceDeferred('Systemd operation unavailable; inspect service and timer before recovery') from None
        if result.returncode:
            # Never log subprocess output: unit definitions/environment can contain private fields.
            raise MaintenanceDeferred('Systemd operation failed; inspect service and timer before recovery')
        return result.stdout.strip()

    def _properties(self, unit):
        output = self._call('show', unit, '--property=LoadState,ActiveState,Job')
        values = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
        if (values.get('LoadState') not in ('loaded', 'masked')
                or values.get('ActiveState') not in ('active', 'inactive', 'activating', 'deactivating',
                                                       'failed', 'reloading', 'refreshing')
                or 'Job' not in values):
            raise MaintenanceDeferred('Required systemd unit or state is unavailable')
        return values

    def timer_active(self):
        states = {}
        for unit in self.timers:
            state = self._properties(unit)
            if state['ActiveState'] not in ('active', 'inactive') or self._pending(state):
                raise MaintenanceDeferred('Timer is not in a stable active or inactive state')
            states[unit] = state['ActiveState'] == 'active'
        if not self._paused:
            self._prior_timers = states
        return any(states.values())

    @staticmethod
    def _pending(state):
        return state['Job'] not in ('', '0')

    def pause_timer(self):
        state = self._properties(self.service)
        self._paused = True
        for unit in self.timers:
            self._call('stop', unit, mutate=True)
        if state['LoadState'] != 'masked':
            # Mark before calling: even a timeout can have applied the mask.
            self._mask_owned = True
            self._call('mask', '--runtime', self.service, mutate=True)
        if self._properties(self.service)['LoadState'] != 'masked':
            raise MaintenanceDeferred('Service mask did not exclude external launches')

    def service_active(self):
        return self._properties(self.service)['ActiveState'] not in ('inactive', 'failed')

    def launch_pending(self):
        return any(self._pending(self._properties(unit)) for unit in (self.service, *self.timers))

    def restore_timer(self, prior_state):
        # On unmask failure do not start the timer. Leave a visible safe failure.
        if self._mask_owned:
            self._call('unmask', '--runtime', self.service, mutate=True)
            self._mask_owned = False
        if self._paused:
            for unit in self.timers:
                active = self._prior_timers.get(unit, prior_state)
                self._call('start' if active else 'stop', unit, mutate=True)
        self._paused = False


def controller_service(controller):
    from .qualification import qualification_timer
    # Keep the installed trigger's identity. Exclude an old disabled trigger too
    # while upgrading a legacy host; new installations only have the practice timer.
    if Path('/etc/systemd/system/nnfx-practice-qualification@.timer').exists():
        legacy = (f'nnfx-practice@{controller}.timer',) if Path('/etc/systemd/system/nnfx-practice@.timer').exists() else ()
        return SystemdService(controller, timer=qualification_timer(controller), extra_timers=legacy)
    return SystemdService(controller)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/var/lib/nnfx-practice'))
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in (
        ('dispatch', 'guarded practice trading through the existing service'),
        ('practice-initialize', 'guarded opening record under maintenance'),
        ('practice-check', 'broker-free protected-plan inspection; never arms execution'),
        ('qualification-initialize', 'compatibility alias for practice-initialize'),
        ('qualification-check', 'compatibility alias for practice-check'),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument('controller_id')
    disposition = commands.add_parser('disposition', help='GET-only reconciliation and local issue disposition')
    disposition.add_argument('controller_id')
    disposition.add_argument('--issue-id', required=True)
    disposition.add_argument('--operator-id', required=True)
    disposition.add_argument('--explanation', required=True)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', args.controller_id):
            raise ConfigurationError('Invalid controller identifier')
        if args.command in ('dispatch', 'practice-initialize', 'practice-check',
                            'qualification-initialize', 'qualification-check'):
            from .qualification import execute, load_permit
            if args.command in ('practice-check', 'qualification-check'):
                print(json.dumps(load_permit(args.root, args.controller_id, 'inspect')))
            else:
                identifier = execute(args.root, args.controller_id,
                                     'run' if args.command == 'dispatch' else 'initialize')
                print(json.dumps({'practice_result_id': identifier, 'qualification_result_id': identifier,
                                  'ordinary_trading_enabled': False}))
            return
        from .broker import PracticeBroker
        from .config import load_binding
        from .disposition import record_disposition
        binding = load_binding(args.root, args.controller_id)
        with PracticeBroker(binding) as broker:
            record_disposition(args.root, args.controller_id, broker,
                               service=controller_service(args.controller_id), issue_id=args.issue_id,
                               operator_id=args.operator_id, explanation=args.explanation)
    except (ConfigurationError, MaintenanceDeferred, BrokerError) as error:
        parser.exit(2, f'{error}\n')
    except DispositionRequired:
        parser.exit(2, 'Disposition requires further broker evidence; issue remains open\n')


if __name__ == '__main__':
    main()
