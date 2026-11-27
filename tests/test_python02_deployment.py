"""Fail-before-mutation checks for the administrator's scoped addition."""

from copy import deepcopy
from datetime import UTC, datetime
import io
import unittest
from unittest.mock import patch

from deploy import add_python02 as deployment
from deploy.python02_bootstrap import next_slot


class DeploymentChecks(unittest.TestCase):
    def test_bootstrap_uses_next_weekday_without_catching_up_or_trading_in_capture_window(self):
        friday = datetime(2026, 11, 27, 21, 49, tzinfo=UTC)
        capture = next_slot(friday)
        self.assertEqual(capture, datetime(2026, 11, 27, 21, 50, tzinfo=UTC))
        self.assertEqual(next_slot(capture), datetime(2026, 11, 30, 21, 50, tzinfo=UTC))
        self.assertEqual(next_slot(datetime(2026, 7, 1, 12, tzinfo=UTC)), datetime(2026, 7, 1, 20, 50, tzinfo=UTC))

    def test_registry_preserves_existing_experiment_exactly(self):
        old = {'experiments': [dict(controller_id='practice-a', notebook_name='Python 01')]}
        new = {'experiments': [*old['experiments'], dict(controller_id='practice-b', notebook_id='notebook-b',
            notebook_name='Python 02', strategy_version='drm_adaptive_bandpass_v1', connection_key='PRACTICE_B')]}
        deployment.registry_change(old, new)
        for change in ('existing', 'new', 'extra'):
            changed = deepcopy(new)
            if change == 'existing':
                changed['experiments'][0]['notebook_name'] = 'Changed'
            elif change == 'new':
                changed['experiments'][1]['strategy_version'] = 't3_bandpass_v1'
            else:
                changed['experiments'].append(dict(changed['experiments'][1]))
            with self.assertRaises(ValueError):
                deployment.registry_change(old, changed)

    def test_private_change_preserves_existing_values_and_requires_distinct_account(self):
        old = {'PRACTICE_A_ACCOUNT_ID': 'fixture-a', 'PRACTICE_A_TOKEN': 'fixture-secret'}
        new = {**old, 'PRACTICE_B_ACCOUNT_ID': 'fixture-b', 'PRACTICE_B_TOKEN': 'fixture-secret',
               'PRACTICE_B_HOME_CURRENCY': 'AUD', 'PRACTICE_B_LOOKBACK_CANDLES': '512'}
        deployment.private_change(old, new)
        for key, value in (('PRACTICE_A_TOKEN', 'changed'), ('PRACTICE_B_ACCOUNT_ID', 'fixture-a'),
                           ('PRACTICE_B_LOOKBACK_CANDLES', '386'), ('PRACTICE_B_TOKEN', ''), ('EXTRA', 'field')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                deployment.private_change(old, {**new, key: value})

    def test_private_parser_never_evaluates_shell_and_rejects_duplicates(self):
        self.assertEqual(deployment.private_fields(b"KEY='$(echo secret)'\n"), {'KEY': '$(echo secret)'})
        for raw in (b'KEY=x\nKEY=y\n', b'KEY=\"missing\n', b'lowercase=x\n'):
            with self.assertRaises(ValueError):
                deployment.private_fields(raw)

    def test_plan_update_preserves_schedule_authority_and_replay_identity(self):
        old = dict(version=2, enabled=True, controller_id='practice-a', notebook_id='notebook-a',
                   run_id='original-prefix', dispatch_at='original-date', schedule='original-schedule',
                   account_binding_sha256='account', manifest_sha256='manifest',
                   automatic_schedule_authority={'sha256': 'authority'},
                   evidence={'m09_controller_controls': {'sha256': 'old'}, 'account_preflight': {'sha256': 'account'}})
        baseline = deepcopy(old)
        plan = deployment.updated_plan(old, 'new-code', 'new-config', {'sha256': 'new-controls'})
        self.assertEqual(old, baseline)
        for key in ('run_id', 'dispatch_at', 'schedule', 'account_binding_sha256', 'manifest_sha256', 'automatic_schedule_authority'):
            self.assertEqual(plan[key], old[key])
        self.assertEqual(plan['evidence']['account_preflight'], old['evidence']['account_preflight'])
        self.assertTrue(plan['enabled'])
        for changes in ({'version': 1}, {'enabled': False}, {'controller_id': 'practice-b'}):
            with self.assertRaises(ValueError):
                deployment.updated_plan({**old, **changes}, 'code', 'config', {})

    def test_nonadministrator_refused_before_accessing_deployment(self):
        with (patch.object(deployment.os, 'geteuid', return_value=1000),
              patch.object(deployment.sys, 'argv', ['add-python02']),
              patch.object(deployment.sys, 'stderr', io.StringIO()),
              patch.object(deployment.Path, 'resolve', side_effect=AssertionError('Unexpected filesystem access'))):
            with self.assertRaises(SystemExit) as raised:
                deployment.main()
        self.assertEqual(raised.exception.code, 2)
