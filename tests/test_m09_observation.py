"""Offline calendar, boot/session and suspend-observation acceptance checks."""

from datetime import UTC, datetime, timedelta
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from . import check_m09_observation as observer
from . import m09_observation_worker as worker


class ObservationChecks(unittest.TestCase):
    def metadata(self):
        target=datetime(2026,11,19,21,50,tzinfo=UTC)
        return dict(target=target.isoformat(),window_start=(target-timedelta(minutes=10)).isoformat(),
                    window_end=(target+timedelta(minutes=15)).isoformat(),writer_uid=999,
                    setup_boot_id='before',setup_kernel='old')

    def row(self, phase, at, **values):
        return dict(phase=phase,at=at.isoformat(),uid=999,boot_id='after',invocation_id='systemd-fixture',
                    kernel='old',suspend_offset=0.001,clock_uncertainty=0.000001,
                    logins=dict(known=True,user_sessions=0),**values)

    def samples(self):
        start=datetime.fromisoformat(self.metadata()['window_start'])
        return [self.row('heartbeat',start+timedelta(seconds=i)) for i in range(0,25*60+1,15)]

    def test_calendar_preserves_new_york_dst_weekends_and_next_day(self):
        cases=(('2026-03-06T22:00:00+00:00','2026-03-09T20:50:00+00:00'),
               ('2026-10-30T22:00:00+00:00','2026-11-02T21:50:00+00:00'),
               ('2026-11-19T11:40:00+00:00','2026-11-19T21:50:00+00:00'),
               ('2026-11-19T21:50:00+00:00','2026-11-20T21:50:00+00:00'))
        for before,after in cases:
            with self.subTest(before=before):
                self.assertEqual(observer.next_slot(datetime.fromisoformat(before)),datetime.fromisoformat(after))

    def test_unit_profiles_keep_real_units_untouched_and_monitor_does_not_block_boot(self):
        prefix='nnfx-m09-observe-0123456789ab'
        service=(observer.ROOT/'deploy/nnfx-practice@.service').read_text()
        timer=(observer.ROOT/'deploy/nnfx-practice@.timer').read_text()
        fixture=Path('/var/lib/nnfx-practice/var/verification')/prefix
        a,b,monitor=observer.unit_texts(service,timer,prefix=prefix,fixture=fixture,
                                      worker=Path('/opt/nnfx-practice/verification')/prefix/'worker.py',
                                      target=datetime.fromisoformat(self.metadata()['target']))
        self.assertIn('Type=oneshot',a)
        self.assertIn('Type=exec',monitor)
        self.assertIn('Restart=no',a)
        self.assertIn('NoNewPrivileges=yes',a)
        self.assertIn('ProtectHome=yes',a)
        self.assertIn('InaccessiblePaths=-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks',a)
        self.assertIn('IPAddressDeny=any',a)
        self.assertIn('OnCalendar=2026-11-19 16:50:00 America/New_York',b)
        self.assertIn('Persistent=false',b)
        self.assertIn('AccuracySec=1s',b)
        self.assertIn(f'Unit={prefix}@%i.service',b)
        self.assertNotIn('ordinary %i',a)
        for bad in ('nnfx-practice','../other','nnfx-m09-observe-INVALID'):
            with self.assertRaises(ValueError):
                observer.valid_prefix(bad)

    def test_boot_requires_new_boot_real_service_identity_and_known_no_user_sessions(self):
        meta=self.metadata()
        row=self.row('boot_marker',datetime.fromisoformat(meta['window_start']))
        now=datetime.fromisoformat(meta['window_end'])
        self.assertEqual(observer.assess(meta,[row],now)['startup_without_login'],'passed')
        for update in (dict(boot_id='before'),dict(invocation_id=None),dict(uid=0),
                       dict(logins=dict(known=False,user_sessions=None)),dict(logins=dict(known=True,user_sessions=1))):
            with self.subTest(update=update):
                self.assertEqual(observer.assess(meta,[{**row,**update}],now)['startup_without_login'],'pending')

    def test_dispatch_requires_actual_expected_minute_and_service_identity(self):
        meta=self.metadata()
        target=datetime.fromisoformat(meta['target'])
        now=target+timedelta(minutes=2)
        row=self.row('dispatch',target+timedelta(seconds=2))
        self.assertEqual(observer.assess(meta,[row],now)['scheduled_dispatch'],'passed')
        for update in (dict(at=(target-timedelta(seconds=1)).isoformat()),
                       dict(at=(target+timedelta(minutes=1)).isoformat()),dict(uid=0),dict(invocation_id=None)):
            self.assertEqual(observer.assess(meta,[{**row,**update}],now)['scheduled_dispatch'],'not_observed')

    def test_covered_wakefulness_window_passes_without_suspension_or_gaps(self):
        meta=self.metadata()
        result=observer.assess(meta,self.samples(),datetime.fromisoformat(meta['window_end']))
        self.assertEqual(result['wakefulness'],'passed')
        self.assertEqual(result['unattended_context'],'no_user_sessions_observed')
        self.assertEqual(result['startup_without_login'],'pending')

    def test_suspend_gap_reboot_and_bad_clock_samples_do_not_pass(self):
        meta=self.metadata()
        now=datetime.fromisoformat(meta['window_end'])
        for cause in ('suspend','gap','reboot','uncertain','invalid'):
            rows=self.samples()
            if cause=='suspend':
                rows[-1]['suspend_offset']+=10
            elif cause=='gap':
                rows=rows[:5]+rows[10:]
            elif cause=='reboot':
                rows[-1]['boot_id']='another'
            elif cause=='uncertain':
                rows[-1]['clock_uncertainty']=1
            else:
                rows[-1]['suspend_offset']=None
            with self.subTest(cause=cause):
                self.assertEqual(observer.assess(meta,rows,now)['wakefulness'],'not_proven')
        self.assertEqual(observer.assess(meta,self.samples()[1:-1],now)['wakefulness'],'not_proven')

    def test_unknown_login_metadata_is_not_an_absence_of_login_proof(self):
        for stdout in ('not-json','{}','[{"class":null}]','[{"class":"unknown"}]'):
            runner=Mock(return_value=subprocess.CompletedProcess([],0,stdout,''))
            self.assertFalse(worker.login_state(runner)['known'])
        runner=Mock(return_value=subprocess.CompletedProcess([],0,json.dumps([dict(class_name='manager')]),''))
        self.assertFalse(worker.login_state(runner)['known'])
        runner=Mock(return_value=subprocess.CompletedProcess([],0,'[{"class":"manager"}]',''))
        self.assertEqual(worker.login_state(runner)['user_sessions'],0)

    def test_unprivileged_setup_cannot_change_host_or_start_a_reboot(self):
        with patch('sys.argv',['observe','prepare']),patch.object(observer.os,'geteuid',return_value=1001), \
                patch.object(observer.subprocess,'run') as command,patch.object(observer.Path,'mkdir') as mkdir, \
                patch('sys.stderr',new_callable=io.StringIO),self.assertRaises(SystemExit) as error:
            observer.main()
        self.assertEqual(error.exception.code,2)
        command.assert_not_called()
        mkdir.assert_not_called()
