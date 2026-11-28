"""One executable mode, unchanged legacy identities, and preserved account history."""

from copy import deepcopy
import io
from unittest.mock import patch

from nnfx_practice import host, lifecycle, qualification as q
from nnfx_practice.broker import PracticeBroker
from nnfx_practice.config import ConfigurationError
from nnfx_practice.ledger import account_report
from nnfx_practice.master import run_master
from .m07_support import EVIDENCE, M07Case, record_legacy_activation
from .test_m10_automatic import AutomaticCase

schedule_controls = q.schedule_controls

class SingleModeChecks(M07Case):
    def test_default_run_keeps_q0_and_historical_a0_without_mode_transition(self):
        self.initialize()
        record_legacy_activation(self)
        before = dict(self.db.execute('SELECT * FROM notebook').fetchone())
        run_master(self.root, 'controller-a', self.broker, evidence=EVIDENCE,
                   run_id=self.run_id, config_hash='c' * 64, code_hash='d' * 64)
        self.assertEqual(dict(self.db.execute('SELECT * FROM notebook').fetchone()), before)
        self.assertEqual(self.db.execute('SELECT mode FROM run_invocations').fetchone()[0], 'qualification')
        self.assertEqual(account_report(self.db).opening_snapshot_id, before['qualification_snapshot_id'])
        self.assertFalse(hasattr(lifecycle, 'activate_ordinary'))

    def test_ordinary_cannot_start_even_with_legacy_activation(self):
        self.initialize()
        record_legacy_activation(self)
        before = '\n'.join(self.db.iterdump())
        self.world.calls.clear()
        with self.assertRaisesRegex(ConfigurationError, 'Only practice'):
            run_master(self.root, 'controller-a', self.broker, mode='ordinary', evidence=EVIDENCE,
                       config_hash='c' * 64, code_hash='d' * 64)
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        self.assertEqual(self.world.calls, [])

    def test_removed_commands_and_broker_permit_cannot_reach_private_configuration(self):
        for command in ('ordinary', 'ordinary-activate', 'ordinary-check'):
            with self.subTest(command=command), patch('sys.argv', ['host', command, 'controller-a']), \
                    patch('sys.stderr', new_callable=io.StringIO), \
                    patch.object(q, 'load_permit') as permit, self.assertRaises(SystemExit) as raised:
                host.main()
            self.assertEqual(raised.exception.code, 2)
            permit.assert_not_called()
        with patch('nnfx_practice.broker.HTTPSConnection') as network, self.assertRaises(TypeError):
            PracticeBroker(self.bound, ordinary=object())
        network.assert_not_called()


class PlanCompatibilityChecks(AutomaticCase):
    def test_practice_and_existing_plan_labels_share_claims_and_guard(self):
        first = self.permit()
        self.claim(first)
        self.plan['mode'] = 'practice'
        self.save()
        with self.assertRaisesRegex(ConfigurationError, 'already attempted'):
            self.claim(self.permit())
        self.plan['mode'] = 'ordinary'
        self.save()
        with patch.object(q, 'load_binding') as binding, self.assertRaises(ConfigurationError):
            self.permit()
        binding.assert_not_called()

    def test_absent_legacy_timer_is_safe_but_live_modified_or_pending_is_rejected(self):
        selected = dict(LoadState='loaded', ActiveState='active', UnitFileState='enabled', Job='',
                        DropInPaths='', Unit='nnfx-practice@controller-a.service', Persistent='no',
                        AccuracyUSec='1s', RandomizedDelayUSec='0',
                        TimersCalendar='{ OnCalendar=' + q.SCHEDULE + ' ; next_elapse=fixture }')
        absent = dict(LoadState='not-found', ActiveState='inactive', UnitFileState='', Job='', DropInPaths='')
        triggers = {'TriggeredBy': q.qualification_timer('controller-a')}
        with patch.object(q, '_command', side_effect=[selected, absent, triggers]):
            schedule_controls('controller-a')
        for key, value in (('ActiveState', 'active'), ('Job', '13'), ('DropInPaths', '/unexpected')):
            changed = deepcopy(absent)
            changed[key] = value
            with self.subTest(key=key), patch.object(q, '_command', side_effect=[selected, changed]), \
                    self.assertRaises(ConfigurationError):
                schedule_controls('controller-a')
