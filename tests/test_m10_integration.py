"""Offline M10 permit/service/wire integration. All HTTP is mocked."""

from copy import deepcopy
from datetime import datetime, timedelta
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import stat
import unittest
from unittest.mock import Mock, patch

from nnfx_practice import host
from nnfx_practice import qualification as q
from nnfx_practice.broker import PracticeBroker
from nnfx_practice.config import ConfigurationError, PERMITTED_PAIRS
from nnfx_practice.lifecycle import activate_ordinary, initialize_qualification, require_invocation
from nnfx_practice.master import run_master
from strategies import t3_bandpass_v1 as selected
from .m07_support import EVIDENCE, M07Case
from .support import TOKEN, ACCOUNT
from . import check_m10_deployment as deployment


class PermitCase(M07Case):
    def setUp(self):
        super().setUp()
        self.protected = self.root / 'protected'
        self.protected.mkdir()
        self.enterContext(patch.object(q, 'PLAN_DIRECTORY', self.protected))
        self.enterContext(patch.object(q, 'DATA_ROOT', self.root))
        self.seal = self.enterContext(patch.object(q, 'sealed_bytes', side_effect=lambda p: Path(p).read_bytes()))
        self.controls = self.enterContext(patch.object(q, 'host_controls'))
        self.enterContext(patch.object(q, 'host_identity', return_value=('fixture-boot', 'fixture-kernel')))
        self.enterContext(patch.object(q.pwd, 'getpwnam', side_effect=lambda name: Mock(
            pw_uid=os.getuid() + (name == 'nnfx-view'), pw_gid=os.getgid())))
        self.units = {'nnfx-practice@.service': 'a' * 64, 'nnfx-practice@.timer': 'b' * 64}
        self.enterContext(patch.object(q, 'deployed_unit_hashes', side_effect=lambda: self.units))
        self.digest = q.account_identity(self.bound)
        self.plan = dict(version=1, enabled=True, controller_id='controller-a', notebook_id='notebook-a',
                         host=q.PRACTICE_HOST, account_binding_sha256=self.digest,
                         manifest_sha256=self.bound.manifest.hash, code_sha256=q.code_identity(),
                         config_sha256=sha256((self.root / 'config.toml').read_bytes()).hexdigest(),
                         boot_id='fixture-boot', kernel='fixture-kernel', run_id=self.run_id,
                         dispatch_at=self.clock.now().isoformat(), evidence={})
        account = dict(source='practice_get', host=q.PRACTICE_HOST, phase='account', status='passed',
                       account_binding_sha256=self.digest, controller_id='controller-a', notebook_id='notebook-a')
        results = dict(clock='NTPSynchronized=yes\n', system_timer_dispatch=[
            dict(phase=phase, uid=os.getuid(), gid=os.getgid(), pid=12345) for phase in ('start', 'end')])
        for name in ('fixture_checks_passed', 'no_automatic_restart', 'inactive_missed_no_catch_up',
                     'no_overlap_independent_controller_active_deferral', 'active-True-failure-False',
                     'active-True-failure-True', 'active-False-failure-False', 'active-False-failure-True'):
            results[name] = True
        authority = dict(account_label='Python 01', account_binding_sha256=self.digest,
                         controller_id='controller-a', notebook_id='notebook-a', practice_host=q.PRACTICE_HOST,
                         manifest_sha256=self.bound.manifest.hash, strategy_version='t3_bandpass_v1',
                         owner_statement='Offline owner-authority fixture; no real broker authority')
        for name in ('ordinary_scheduled_trading_authorized', 'ordinary_activation_authorized',
                     'strategy_changes_authorized', 'trade_2_unit_reduction_authorized'):
            authority[name] = False
        self.documents = {
            'strategy_qualification': json.loads(Path(selected.__file__).with_name('qualification.json').read_text()),
            'account_preflight': account,
            'candle_preflight': dict(account, phase='candles', manifest_sha256=self.bound.manifest.hash,
                                     lookback_candles=386, valid_windows=28, pairs=dict.fromkeys(PERMITTED_PAIRS, {})),
            'initial_account_resolution': dict(status='passed', account_binding_sha256=self.digest,
                                               explanation='Offline empty account fixture'),
            'execution_authority': authority,
            'private_connection': dict(private_checks_passed=True,
                                       binding=dict(account_binding_sha256=self.digest,
                                                    manifest_sha256=self.bound.manifest.hash,
                                                    uid=os.getuid(), private_uid=os.getuid(),
                                                    private_gid=os.getgid(), private_mode=0o600),
                                       viewer=dict(uid=os.getuid()+1, credential_readable=False)),
            'm09_controller_controls': dict(classification='system-manager broker-free fixtures', cleanup_errors=[],
                                            registry_sha256=self.plan['config_sha256'],
                                            results=results, deployed_source_hashes=q.code_hashes(),
                                            source_hashes={'deploy/' + k: v for k, v in self.units.items()}),
        }
        self.save()

    def save(self):
        for name, value in self.documents.items():
            path = self.protected / (name + '.json')
            raw = json.dumps(value).encode()
            if name == 'strategy_qualification':
                raw = Path(selected.__file__).with_name('qualification.json').read_bytes()
            path.write_bytes(raw)
            self.plan['evidence'][name] = dict(status='passed', path=str(path), sha256=sha256(raw).hexdigest())
        self.plan_path = self.protected / 'controller-a.json'
        self.plan_path.write_text(json.dumps(self.plan))

    def permit(self, operation='run', now=None):
        return q.load_permit(self.root, 'controller-a', operation, now=self.clock.now() if now is None else now)

    def claim(self, permit):
        with patch.object(q, 'datetime', wraps=datetime) as clock:
            clock.now.return_value = self.clock.now()
            return permit.claim(self.root)

    def native(self, permit):
        """Run native serialization/response parsing against the offline World."""
        connection = Mock()
        connection.sock = Mock()
        latest = []

        def request(method, path, *, body=None, headers):
            payload = json.loads(body) if body is not None else None
            latest[:] = [self.world.request(method, path, payload)]

        def response():
            reply = latest[0]
            result = Mock(status=reply.status)
            result.read.return_value = json.dumps(reply.body).encode()
            result.getheader.return_value = reply.request_id
            return result

        connection.request.side_effect = request
        connection.getresponse.side_effect = response
        self.enterContext(patch('nnfx_practice.broker.HTTPSConnection', return_value=connection))
        return connection

class PermitChecks(PermitCase):
    def test_disabled_or_missing_plan_rejects_before_private_or_network(self):
        self.plan['enabled'] = False
        self.save()
        with patch.object(q, 'load_binding', side_effect=AssertionError('private load')):
            with self.assertRaisesRegex(ConfigurationError, 'disabled'):
                self.permit()
        self.controls.assert_not_called()
        self.assertFalse((self.root / 'var').exists())

    def test_pending_reference_and_changed_evidence_never_grant_a_permit(self):
        self.plan['evidence']['m09_controller_controls']['status'] = 'pending'
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ConfigurationError, 'pending'):
            self.permit()
        self.save()
        Path(self.plan['evidence']['account_preflight']['path']).write_text('{}')
        with self.assertRaisesRegex(ConfigurationError, 'changed'):
            self.permit()
        self.assertFalse((self.root / 'var').exists())

    def test_fixture_preflight_wrong_account_or_manifest_is_not_a_pass(self):
        original = deepcopy(self.documents)
        for name, field, value in (
            ('account_preflight', 'source', 'fixture'),
            ('account_preflight', 'account_binding_sha256', 'a' * 64),
            ('candle_preflight', 'manifest_sha256', 'a' * 64),
            ('candle_preflight', 'valid_windows', 27),
            ('private_connection', 'private_checks_passed', False),
            ('execution_authority', 'ordinary_activation_authorized', True),
            ('initial_account_resolution', 'status', 'pending'),
        ):
            with self.subTest(name=name, field=field):
                self.documents = deepcopy(original)
                self.documents[name][field] = value
                self.save()
                with self.assertRaises(ConfigurationError):
                    self.permit()

    def test_each_essential_control_and_stale_code_blocks_execution(self):
        controls = self.documents['m09_controller_controls']
        for key in list(controls['results']):
            if key == 'fixture_checks_passed':
                continue  # Overall report also includes later dashboard checks.
            original = controls['results'][key]
            controls['results'][key] = False
            self.save()
            with self.subTest(control=key), self.assertRaises(ConfigurationError):
                self.permit()
            controls['results'][key] = original
        controls['deployed_source_hashes']['nnfx_practice/broker.py'] = 'a' * 64
        self.save()
        with self.assertRaisesRegex(ConfigurationError, 'stale'):
            self.permit()

    def test_final_dashboard_failure_does_not_replace_or_block_initial_controller_controls(self):
        report = self.documents['m09_controller_controls']
        report['results']['fixture_checks_passed'] = False
        report['results']['dashboard_system_sandbox_and_wal'] = False
        report['error'] = 'Offline final-dashboard failure fixture; essential controller checks passed'
        self.save()
        permit = self.permit()
        self.assertFalse(permit.claimed)
        self.assertFalse((self.root / 'var').exists())

    def test_registry_boot_kernel_or_code_change_requires_reverification(self):
        for key in ('config_sha256', 'code_sha256', 'boot_id', 'kernel'):
            original = self.plan[key]
            self.plan[key] = 'a' * 64
            self.save()
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                self.permit()
            self.plan[key] = original

    def test_only_explicit_weekday_1650_dispatch_minute_has_no_catch_up(self):
        for at in (self.clock.now() - timedelta(seconds=1), self.clock.now() + timedelta(minutes=1)):
            with self.subTest(at=at), self.assertRaisesRegex(ConfigurationError, 'no catch-up'):
                self.permit(now=at)
        self.plan['dispatch_at'] = '2026-11-21T21:50:00+00:00'
        self.save()
        with self.assertRaisesRegex(ConfigurationError, 'weekday'):
            self.permit()

    def test_inspection_stops_before_private_binding_and_never_claims_readiness(self):
        self.plan['enabled'] = False
        self.save()
        with patch.object(q, 'load_binding', side_effect=AssertionError('private load')):
            report = self.permit('inspect')
        self.assertTrue(report['plan_valid'])
        self.assertFalse(report['qualification_ready'])
        self.assertFalse(report['plan_enabled'])
        self.assertFalse((self.root / 'var').exists())

    def test_directly_constructed_permit_cannot_enable_network(self):
        permit = q.QualificationPermit(self.bound, self.plan, self.plan_path,
                                        sha256(self.plan_path.read_bytes()).hexdigest(), 'run', claimed=True)
        with patch('nnfx_practice.broker.HTTPSConnection') as connection, self.assertRaises(ConfigurationError):
            PracticeBroker(self.bound, qualification=permit)
        connection.assert_not_called()

    def test_initialization_is_get_only_and_preserves_q0_and_cursor_on_reopen(self):
        permit = self.permit('initialize')
        connection = self.native(permit)
        with PracticeBroker(self.bound, qualification=permit, now=self.clock.now) as broker:
            q0 = initialize_qualification(self.root, 'controller-a', broker, service=self.service,
                                           evidence=permit.references)
            again = initialize_qualification(self.root, 'controller-a', broker, service=self.service,
                                              evidence=permit.references)
            self.assertEqual(q0, again)
            with self.assertRaisesRegex(ConfigurationError, 'cannot send mutations'):
                broker.enter_trade('EUR-USD', units='10', distance='0.00150', client_id='offline')
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                activate_ordinary(self.root, 'controller-a', broker, service=self.service, evidence=EVIDENCE)
        self.assertTrue(all(call.args[0] == 'GET' for call in connection.request.call_args_list))
        self.assertEqual(self.service.events, ['pause', 'restore:True'] * 2)

    def test_session_claim_survives_failure_and_blocks_replay_with_a_new_run_id(self):
        permit = self.permit()
        directory = self.claim(permit)
        original = next(directory.glob('*.claim')).read_bytes()
        self.plan['run_id'] = 'different-attempt'
        self.save()
        second = self.permit()
        with self.assertRaisesRegex(ConfigurationError, 'already attempted'):
            self.claim(second)
        self.assertEqual(next(directory.glob('*.claim')).read_bytes(), original)

    def test_unclaimed_or_revoked_permit_never_sends_mutations(self):
        permit = self.permit()
        connection = self.native(permit)
        broker = PracticeBroker(self.bound, qualification=permit)
        with self.assertRaisesRegex(ConfigurationError, 'cannot send mutations'):
            broker.change_trade('42')
        self.claim(permit)
        self.plan_path.write_text('{}')
        with self.assertRaisesRegex(ConfigurationError, 'revoked'):
            broker.change_trade('42')
        connection.request.assert_not_called()

    def test_native_qualification_run_reuses_lifecycle_and_records_long_short_cross_sets(self):
        self.initialize()
        self.world.calls.clear()
        self.world.signals = {'EUR-USD': 'long', 'GBP-USD': 'short', 'EUR-GBP': 'long'}
        permit = self.permit()
        self.native(permit)
        directory = self.claim(permit)
        with q.RetainedBroker(permit, directory / 'responses.jsonl') as broker:
            broker._now = self.clock.now
            with patch.object(selected, 'observe_c1', side_effect=self.world.observe), \
                    patch.object(selected, 'observe_exit', return_value=selected.EventObservation(
                        'no_event', selected.EXIT_RULE_ID, selected.EXIT_OUTPUTS)), \
                    patch.object(selected, 'sizing_atr', return_value=selected.AtrObservation(self.world.atr)):
                run_master(self.root, 'controller-a', broker, mode='qualification', evidence=permit.references,
                           run_id=self.run_id, config_hash=permit.plan['config_sha256'],
                           code_hash=permit.plan['code_sha256'], elapsed=self.clock.monotonic)
            with self.assertRaisesRegex(ValueError, 'not enabled'):
                broker.require_scripted_execution()
        self.assertEqual(len(self.world.trades), 6)
        self.assertEqual(len(set(self.world.trades)), 6)
        self.assertEqual(self.db.execute('SELECT count(*) FROM trade_sets WHERE established_at IS NOT NULL').fetchone()[0], 3)
        self.assertIsNone(self.db.execute('SELECT activated_at FROM notebook').fetchone()[0])
        evidence = (directory / 'responses.jsonl').read_text()
        self.assertNotIn(TOKEN, evidence)
        self.assertNotIn(ACCOUNT, evidence)
        captures = [json.loads(line) for line in evidence.splitlines() if '/candles?' in json.loads(line)['path']]
        self.assertEqual(len(captures), 28)
        self.assertTrue(all(len(row['body']['candles']) == 386 for row in captures))

    def test_native_transport_does_not_retry_an_uncertain_mutation(self):
        permit = self.permit()
        self.claim(permit)
        connection = self.native(permit)
        connection.request.side_effect = TimeoutError('fixture timeout')
        broker = PracticeBroker(self.bound, qualification=permit)
        result = broker.change_trade('42')
        self.assertIsNone(result.status)
        self.assertEqual(connection.request.call_count, 1)
        connection.close.assert_called_once()

    def test_qualification_permit_cannot_run_ordinary_or_qualify_after_activation(self):
        self.initialize()
        activate_ordinary(self.root, 'controller-a', self.broker, service=self.service, evidence=EVIDENCE)
        permit = self.permit()
        connection = self.native(permit)
        broker = PracticeBroker(self.bound, qualification=permit)
        with self.assertRaisesRegex(ValueError, 'not enabled'):
            require_invocation(self.db, broker, 'ordinary', None)
        with self.assertRaisesRegex(ConfigurationError, 'unactivated'):
            require_invocation(self.db, broker, 'qualification', permit.references)
        connection.request.assert_not_called()

    def test_elapsed_dispatch_minute_cannot_create_a_session_claim(self):
        permit = self.permit()
        self.clock.advance(60)
        with self.assertRaisesRegex(ConfigurationError, 'no catch-up'):
            self.claim(permit)
        self.assertFalse((self.root / 'var').exists())

    def test_redirect_response_is_retained_without_following_or_retry(self):
        permit = self.permit()
        self.claim(permit)
        connection = self.native(permit)
        response = Mock(status=302)
        response.read.return_value = b'{}'
        response.getheader.return_value = 'fixture-request'
        connection.request.side_effect = None
        connection.getresponse.side_effect = None
        connection.getresponse.return_value = response
        broker = PracticeBroker(self.bound, qualification=permit)
        self.assertEqual(broker.change_trade('42').status, 302)
        self.assertEqual(connection.request.call_count, 1)

    def test_transport_rejects_other_accounts_routes_and_payloads(self):
        permit = self.permit()
        self.claim(permit)
        connection = self.native(permit)
        broker = PracticeBroker(self.bound, qualification=permit)
        base = '/v3/accounts/' + self.bound.connection.account_id
        for method, path, body in (
            ('POST', base + '/orders', {'order': {'type': 'LIMIT'}}),
            ('PUT', base + '/trades/42/close', {'units': '1'}),
            ('PUT', base + '/trades/42/orders', {'stopLoss': None}),
            ('DELETE', base + '/orders/42', {}),
            ('PUT', base + '/trades/42/close?unsafe=true', {'units': 'ALL'}),
            ('PUT', '/v3/accounts/other/trades/42/close', {'units': 'ALL'}),
        ):
            with self.subTest(path=path), self.assertRaises(ValueError):
                broker._transport.request(method, path, body)
        connection.request.assert_not_called()


class HostContractChecks(unittest.TestCase):
    def facts(self):
        timer = dict(LoadState='loaded', ActiveState='inactive', UnitFileState='disabled', Job='', DropInPaths='')
        service = dict(LoadState='loaded', ActiveState='activating', MainPID=str(os.getpid()), InvocationID='fixture',
                       User='nnfx-run', Group='nnfx-read', Type='oneshot', Restart='no', DropInPaths='')
        return timer, service

    def test_real_service_pid_invocation_and_inactive_ordinary_timer_are_required(self):
        timer, service = self.facts()
        with patch.dict(os.environ, INVOCATION_ID='fixture'):
            for obj, key, value in ((timer, 'ActiveState', 'active'), (timer, 'UnitFileState', 'enabled'),
                                    (timer, 'Job', '12'), (service, 'MainPID', '0'),
                                    (service, 'InvocationID', 'other'), (service, 'Restart', 'always'),
                                    (service, 'DropInPaths', '/unsafe/override.conf')):
                original = obj[key]
                obj[key] = value
                with self.subTest(key=key), patch.object(q, '_command', side_effect=[
                        {'NTPSynchronized': 'yes'}, timer, service]), self.assertRaises(ConfigurationError):
                    q.host_controls('controller-a', 'run')
                obj[key] = original
            with patch.object(q, '_command', side_effect=[{'NTPSynchronized': 'yes'}, timer, service]):
                q.host_controls('controller-a', 'run')

    def test_clock_unknown_and_user_scope_never_qualify(self):
        with patch.object(q, '_command', return_value={}), self.assertRaises(ConfigurationError):
            q.host_controls('controller-a', 'run')

    def test_dispatch_missing_plan_rejects_without_private_notebook_or_network_access(self):
        with patch('sys.argv', ['host', 'dispatch', 'practice-a']), \
                patch.object(q, 'sealed_bytes', side_effect=ConfigurationError('missing protected plan')), \
                patch.object(q, 'load_binding') as binding, patch.object(q, 'PracticeBroker') as broker, \
                patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
            host.main()
        self.assertEqual(error.exception.code, 2)
        binding.assert_not_called()
        broker.assert_not_called()

    def test_root_evidence_boundary_rejects_writer_owned_or_writable_directories(self):
        for mode, uid in ((stat.S_IFDIR | 0o755, 1001), (stat.S_IFDIR | 0o777, 0),
                          (stat.S_IFLNK | 0o777, 0)):
            info = Mock(st_mode=mode, st_uid=uid)
            with self.subTest(mode=mode, uid=uid), patch.object(Path, 'lstat', return_value=info), \
                    patch.object(q.os, 'open') as opened, self.assertRaises(ConfigurationError):
                q.sealed_bytes('/etc/nnfx-practice/qualification/practice-a.json')
            opened.assert_not_called()

    def test_duplicate_json_fields_are_rejected(self):
        with self.assertRaises(ConfigurationError):
            q._document('{"enabled": false, "enabled": true}')

    def test_deployment_probe_rejects_nonadministrator_before_host_changes(self):
        with patch.object(deployment.os, 'geteuid', return_value=1001), \
                patch.object(deployment, 'command') as command, \
                patch.object(deployment.Path, 'mkdir') as mkdir, self.assertRaises(SystemExit):
            deployment.main()
        command.assert_not_called()
        mkdir.assert_not_called()

    def test_deployment_probe_defers_active_or_enabled_ordinary_controls(self):
        for change in ({'ActiveState': 'active'}, {'UnitFileState': 'enabled'}, {'Job': '12'}):
            service = dict(LoadState='loaded', ActiveState='inactive', Job='')
            timer = dict(LoadState='loaded', ActiveState='inactive', UnitFileState='disabled', Job='', **{})
            timer.update(change)
            with self.subTest(change=change), patch.object(deployment, 'properties', side_effect=[service, timer]), \
                    self.assertRaises(RuntimeError):
                deployment.require_inactive('service', 'timer')

    def test_deployment_probe_denies_actual_network_credentials_and_notebooks(self):
        self.assertIn('IPAddressDeny=any', deployment.DROPIN)
        self.assertIn('InaccessiblePaths=-/var/lib/nnfx-practice/.env /var/lib/nnfx-practice/var/notebooks',
                      deployment.DROPIN)
        self.assertNotIn('ExecStart=', deployment.DROPIN)
