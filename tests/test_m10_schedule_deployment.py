"""Offline schedule and migration boundaries; never access host controls or a broker."""

from copy import deepcopy
from datetime import UTC, datetime
import io
import unittest
from unittest.mock import patch

from deploy import upgrade_m10 as upgrade
from nnfx_practice import qualification as q
from nnfx_practice.config import ConfigurationError
from . import collect_m10_automatic as collector


class ScheduleControlsChecks(unittest.TestCase):
    def states(self, ordinary=False, running=True):
        primary='nnfx-practice@controller-a.timer'
        qualifier=q.qualification_timer('controller-a')
        active=primary if ordinary else qualifier
        states={unit:dict(LoadState='loaded',ActiveState='active' if running and unit==active else 'inactive',
            UnitFileState='enabled' if running and unit==active else 'disabled',Job='',DropInPaths='',
            Unit='nnfx-practice@controller-a.service',Persistent='no',AccuracyUSec='1s',RandomizedDelayUSec='0',
            TimersCalendar='{ OnCalendar='+q.SCHEDULE+' ; next_elapse=future }') for unit in (primary,qualifier)}
        states['nnfx-practice@controller-a.service']=dict(TriggeredBy=primary+' '+qualifier)
        return states

    def check(self,states,**kwargs):
        def command(*args):
            return states[args[2]]
        with patch.object(q,'_command',side_effect=command):
            q.schedule_controls('controller-a',**kwargs)

    def test_only_matching_schedule_targets_existing_controller(self):
        for ordinary in (False,True):
            for running in (False,True):
                self.check(self.states(ordinary,running),ordinary=ordinary,running=running)

    def test_modified_or_competing_schedule_rejected(self):
        states=self.states()
        selected=q.qualification_timer('controller-a')
        for key,value in (('Persistent','yes'),('RandomizedDelayUSec','1min'),('AccuracyUSec','1min'),
                          ('Unit','some-other.service'),('TimersCalendar','{ OnCalendar=*-*-* 17:00:00 ; }'),
                          ('DropInPaths','/tmp/override.conf'),('Job','12'),('ActiveState','inactive')):
            changed=deepcopy(states); changed[selected][key]=value
            with self.subTest(key=key),self.assertRaises(ConfigurationError):self.check(changed)
        for key,value in (('ActiveState','active'),('UnitFileState','enabled'),('Job','12')):
            changed=deepcopy(states); changed['nnfx-practice@controller-a.timer'][key]=value
            with self.subTest(key=key),self.assertRaises(ConfigurationError):self.check(changed)

    def test_old_one_shot_must_be_stopped_before_recurring_dispatch(self):
        states=self.states()
        states['nnfx-practice@controller-a.service']['TriggeredBy']+=' old.timer'
        states['old.timer']=dict(ActiveState='active',Job='')
        with self.assertRaises(ConfigurationError):self.check(states)
        states['old.timer']['ActiveState']='inactive'
        self.check(states)

    def test_activation_requires_both_schedules_disabled(self):
        for ordinary in (False,True):
            with self.assertRaises(ConfigurationError):self.check(self.states(ordinary),ordinary=True,running=False)


class UpgradeChecks(unittest.TestCase):
    def test_nonadministrator_rejected_before_plan_network_or_controls(self):
        with patch('sys.argv',['upgrade','--expected-plan-sha256','a'*64,'--verification','unused']), \
                patch.object(upgrade.os,'geteuid',return_value=1000),patch.object(upgrade,'command') as command, \
                patch.object(upgrade,'notebook_state') as notebook,patch('sys.stderr',new_callable=io.StringIO), \
                self.assertRaises(SystemExit):upgrade.main()
        command.assert_not_called();notebook.assert_not_called()

    def test_protected_identity_change_cannot_rearm(self):
        old=dict(version=1,controller_id='practice-a',notebook_id='notebook-a',config_sha256='b'*64,kernel='kernel')
        kwargs=dict(now=datetime.now(UTC),expected='a'*64,digest='a'*64,registry_hash='b'*64,kernel='kernel')
        upgrade.qualify_current(old,**kwargs)
        for field,value in (('version',2),('mode','ordinary'),('controller_id','other'),('kernel','changed'),('config_sha256','c'*64)):
            with self.subTest(field=field),self.assertRaises(ValueError):upgrade.qualify_current(dict(old,**{field:value}),**kwargs)
        with self.assertRaises(ValueError):upgrade.qualify_current(old,**dict(kwargs,digest='c'*64))

    def test_migration_candidate_preserves_old_plan_and_original_evidence(self):
        old=dict(version=1,run_id='old',dispatch_at='2026-11-20T21:50:00+00:00',
                 evidence={'execution_authority':{'path':'existing','sha256':'a'*64},'m09_controller_controls':{'path':'old'}})
        original=deepcopy(old)
        new=upgrade.candidate(old,code_hash='b'*64,boot='new-boot',kernel='kernel',controls_ref={'path':'new'},authority_ref={'path':'owner'})
        self.assertEqual(old,original)
        self.assertEqual(new['evidence']['execution_authority'],old['evidence']['execution_authority'])
        self.assertEqual(new['dispatch_at'],old['dispatch_at'])
        self.assertFalse(new['enabled']);self.assertEqual(new['mode'],'qualification')
        self.assertEqual(new['schedule'],q.SCHEDULE)

    def test_deployment_defers_around_trading_without_stopping_service(self):
        for at in ('2026-11-20T21:35:00+00:00','2026-11-20T21:50:00+00:00','2026-11-20T22:10:00+00:00'):
            with self.subTest(at=at),self.assertRaises(ValueError):upgrade.quiet_window(datetime.fromisoformat(at),q.NY)
        upgrade.quiet_window(datetime.fromisoformat('2026-11-20T20:00:00+00:00'),q.NY)

    def test_collector_does_not_require_final_host_observer_or_allow_nonadministrator(self):
        with patch('sys.argv',['collect']),patch.object(collector.os,'geteuid',return_value=1000), \
                patch.object(collector,'collect') as collect,patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit):collector.main()
        collect.assert_not_called()
