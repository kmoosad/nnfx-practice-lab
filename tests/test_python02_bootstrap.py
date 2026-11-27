"""Offline orchestration checks for the one-time, non-trading setup job."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from deploy import python02_bootstrap as bootstrap
from nnfx_practice import qualification as q


class BootstrapChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / 'config.toml').write_text('fixture registry')
        self.context_path = self.root / 'context.json'
        context = dict(code_sha256='code', kernel='kernel', config_sha256=sha256((self.root / 'config.toml').read_bytes()).hexdigest(),
                       bootstrap_sha256=sha256(Path(bootstrap.__file__).read_bytes()).hexdigest(),
                       account_binding_sha256='account-b', manifest_sha256='manifest-b', evidence={}, owner_statement='Offline fixture')
        self.context_path.write_text(json.dumps(context))
        self.enterContext(patch.object(bootstrap, 'DATA', self.root))
        self.enterContext(patch.object(q, 'PLAN_DIRECTORY', self.root))
        self.enterContext(patch.object(q, 'sealed_bytes', side_effect=lambda p: Path(p).read_bytes()))
        self.enterContext(patch.object(q, 'code_identity', return_value='code'))
        self.enterContext(patch.object(q, 'host_identity', return_value=('boot', 'kernel')))
        self.enterContext(patch.object(q, '_evidence', return_value={}))
        self.validate = self.enterContext(patch.object(q, 'validate_evidence'))
        self.enterContext(patch.object(q, 'automatic_authority'))
        self.enterContext(patch.object(bootstrap.os, 'geteuid', return_value=0))
        self.enterContext(patch.object(bootstrap.os, 'chown'))
        self.enterContext(patch.object(bootstrap.os, 'fchown'))
        self.enterContext(patch.object(bootstrap.pwd, 'getpwnam', side_effect=lambda name: SimpleNamespace(pw_uid=100 + (name == 'nnfx-view'), pw_gid=200)))
        clock = self.enterContext(patch.object(bootstrap, 'datetime', wraps=datetime))
        clock.now.return_value = datetime(2026, 11, 27, 21, 50, 10, tzinfo=UTC)
        self.enterContext(patch('sys.argv', ['bootstrap', '--context', str(self.context_path)]))
        self.enterContext(patch.object(bootstrap.subprocess, 'run', return_value=SimpleNamespace(returncode=1)))
        self.capture = dict(status='passed', valid_windows=28, account_binding_sha256='account-b', manifest_sha256='manifest-b',
                            account={'evidence': {'body': {'account': dict(trades=[], orders=[], openTradeCount=0, pendingOrderCount=0)}}})
        self.native = self.enterContext(patch.object(bootstrap, 'native', side_effect=lambda program, **kwargs:
            json.dumps(self.capture if 'check_candles' in program else dict(account_binding_sha256='account-b'))))
        self.commands = []
        self.fail_initialize = False
        def command(*args, **kwargs):
            self.commands.append(tuple(map(str, args)))
            if self.fail_initialize and 'qualification-initialize' in args:
                raise RuntimeError('Offline initialization failure')
            return 'ActiveState=active\nSubState=waiting\nUnitFileState=enabled\n' if 'show' in args else ''
        self.enterContext(patch.object(bootstrap, 'run', side_effect=command))

    def test_success_initializes_then_schedules_next_weekday_without_a_trading_dispatch(self):
        bootstrap.main()
        record = json.loads((self.root / 'bootstrap-receipt.json').read_bytes())
        self.assertTrue(record['q0_initialized'])
        self.assertFalse(record['trading_run_invoked'])
        self.assertEqual(record['first_dispatch'], '2026-11-30T21:50:00+00:00')
        commands = self.commands
        initialization = next(i for i, c in enumerate(commands) if 'qualification-initialize' in c)
        scheduling = next(i for i, c in enumerate(commands) if 'enable' in c)
        self.assertLess(initialization, scheduling)
        self.assertFalse(any('dispatch' in c or 'qualification-run' in c or 'ordinary-activate' in c for c in commands))

    def test_incomplete_candles_never_initialize_or_enable(self):
        self.capture.update(status='incomplete', valid_windows=27)
        with self.assertRaisesRegex(ValueError, 'did not pass'):
            bootstrap.main()
        self.assertFalse(any('qualification-initialize' in c or 'enable' in c for c in self.commands))
        self.assertFalse((self.root / 'initial-plan.json').exists())
        record = json.loads((self.root / 'bootstrap-receipt.json').read_bytes())
        self.assertEqual(record['candle_report']['status'], 'incomplete')

    def test_initialization_failure_is_retained_and_cannot_replay(self):
        self.fail_initialize = True
        with self.assertRaisesRegex(RuntimeError, 'initialization failure'):
            bootstrap.main()
        self.assertFalse(any('enable' in c for c in self.commands))
        calls = self.native.call_count
        with self.assertRaises(FileExistsError):
            bootstrap.main()
        self.assertEqual(self.native.call_count, calls)
