"""Offline checks for the explicitly requested one-trade operator exit."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nnfx_practice.broker import BrokerError, HTTPReply, _PracticeTransport
from nnfx_practice.control import MaintenanceDeferred
from nnfx_practice.config import ConfigurationError, load_account_binding
from nnfx_practice.qualification import account_identity
from . import close_failed_gbpcad_2251 as close
from .m07_support import Service
from .support import NotebookCase


class OperatorCloseTests(NotebookCase):
    def setUp(self):
        super().setUp()
        self.bound = self.binding()
        self.enterContext(patch.object(close, 'ACCOUNT_DIGEST', account_identity(self.bound)))
        self.service = Service()
        self.trade = dict(id='2251', instrument='GBP_CAD', initialUnits='-42665',
                          currentUnits='-42665', price='1.87722', openTime=close.OPEN_TIME,
                          state='OPEN', stopLossOrder=dict(id='2252', price='1.88824'))
        self.closed = dict(self.trade, state='CLOSED', currentUnits='0', closingTransactionIDs=['2254'])
        self.fill = dict(id='2254', type='ORDER_FILL', tradesClosed=[dict(tradeID='2251', units='42665')])
        self.summary = dict(id=self.bound.connection.account_id, currency=self.bound.connection.home_currency)
        self.calls = []
        self.replies = []
        self.transport = None

    @property
    def directory(self):
        return self.root / 'var/operator-actions' / close.ACTION

    def factory(self, connection, connect_timeout, read_timeout, *, mutation_guard):
        transport = Mock()
        self.transport = transport

        def request(method, path, payload=None):
            suffix = path.removeprefix('/v3/accounts/' + connection.account_id)
            if method != 'GET':
                mutation_guard(method, suffix, payload)
                self.assertTrue((self.directory / 'request.json').is_file())
            self.calls.append((method, suffix, payload))
            reply = self.replies.pop(0)
            if isinstance(reply, BaseException):
                raise reply
            return reply

        transport.request.side_effect = request
        transport.guard = mutation_guard
        return transport

    @staticmethod
    def reply(body, status=200):
        return HTTPReply(status, deepcopy(body), 'offline-request-id')

    def setup_open(self, response=None, *, after=None):
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.trade)),
                        response or self.reply(dict(orderFillTransaction=self.fill)),
                        self.reply(dict(trade=after or self.closed))]
        if (after or self.closed)['state'] == 'CLOSED':
            self.replies += [self.reply(dict(transaction=self.fill)), self.reply(dict(account=self.summary))]

    def run_close(self):
        return close.execute(self.root, self.bound, self.service, transport_factory=self.factory)

    def puts(self):
        return [call for call in self.calls if call[0] == 'PUT']

    def test_close_has_one_exact_request_durable_intent_and_retained_proof(self):
        self.setup_open()
        result = self.run_close()
        self.assertEqual(result['outcome'], 'confirmed_closed')
        self.assertEqual(result['closing_transaction_id'], '2254')
        self.assertEqual(self.puts(), [('PUT', '/trades/2251/close', {'units':'ALL'})])
        self.assertEqual(self.service.events, ['pause', 'restore:True'])
        self.assertFalse(self.bound.experiment.notebook_path(self.root).exists())
        records = (self.directory / 'responses.jsonl').read_text()
        self.assertNotIn(self.bound.connection.account_id, records)
        self.assertNotIn(self.bound.connection.token, records)
        self.assertIn('2252', records)
        self.assertIn('2254', records)
        self.assertEqual((self.directory / 'request.json').stat().st_mode & 0o777, 0o600)
        self.transport.close.assert_called_once()

    def test_already_closed_only_reads_evidence(self):
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.closed)),
                        self.reply(dict(transaction=self.fill)), self.reply(dict(account=self.summary))]
        self.assertEqual(self.run_close()['outcome'], 'confirmed_closed')
        self.assertFalse(self.puts())
        self.assertFalse((self.directory / 'request.json').exists())

    def test_rejection_is_retained_and_repeat_does_not_resubmit(self):
        self.setup_open(self.reply(dict(errorCode='MARKET_HALTED'), 400), after=self.trade)
        result = self.run_close()
        self.assertEqual((result['outcome'], result['broker_reason']), ('still_open', 'MARKET_HALTED'))
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.trade))]
        self.assertTrue(self.run_close()['earlier_attempt_exists'])
        self.assertEqual(len(self.puts()), 1)

    def test_http_success_with_cancel_is_not_a_confirmed_close(self):
        self.setup_open(self.reply(dict(orderCancelTransaction=dict(reason='MARKET_HALTED'))), after=self.trade)
        self.assertEqual(self.run_close()['outcome'], 'still_open')

    def test_lost_response_can_be_confirmed_by_fresh_reads(self):
        self.setup_open(BrokerError('Lost response'))
        self.assertEqual(self.run_close()['outcome'], 'confirmed_closed')
        self.assertEqual(len(self.puts()), 1)

    def test_lost_response_and_failed_verification_never_resubmits(self):
        self.setup_open(BrokerError('Lost response'))
        self.replies[3] = BrokerError('Read unavailable')
        with self.assertRaises(BrokerError):
            self.run_close()
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.trade))]
        self.assertEqual(self.run_close()['outcome'], 'still_open')
        self.assertEqual(len(self.puts()), 1)
        self.assertTrue(self.service.timer)

    def test_interruption_after_intent_is_not_retried(self):
        self.setup_open(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.run_close()
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.trade))]
        self.assertFalse(self.run_close()['request_sent_this_invocation'])
        self.assertEqual(len(self.puts()), 1)

    def test_trade_identity_and_state_mismatches_prevent_mutation(self):
        for field, value in [('id','2259'), ('instrument','EUR_USD'), ('initialUnits','42665'),
                             ('price','1.87723'), ('openTime','2026-11-19T00:00:00Z'),
                             ('currentUnits','-42666'), ('currentUnits','1'), ('state','CLOSE_WHEN_TRADEABLE')]:
            with self.subTest(field=field, value=value):
                self.replies = [self.reply(dict(account=self.summary)),
                                self.reply(dict(trade=dict(self.trade, **{field:value})))]
                with self.assertRaises(ValueError):
                    self.run_close()
        self.assertFalse(self.puts())

    def test_partial_remaining_short_is_closed_in_full(self):
        self.trade['currentUnits'] = '-100'
        self.setup_open()
        self.assertEqual(self.run_close()['outcome'], 'confirmed_closed')
        self.assertEqual(self.puts()[0][2], {'units':'ALL'})

    def test_wrong_account_binding_or_summary_prevents_mutation(self):
        with patch.object(close, 'ACCOUNT_DIGEST', '0'*64), self.assertRaises(ValueError):
            self.run_close()
        self.assertFalse(self.calls)
        self.assertFalse(self.service.events)
        self.replies = [self.reply(dict(account=dict(self.summary, id='wrong-account')))]
        with self.assertRaises(ValueError):
            self.run_close()
        self.assertFalse(self.puts())

    def test_active_controller_or_unpaused_timer_prevents_all_requests(self):
        for field in ('active','pending','pause_fails'):
            with self.subTest(field=field):
                self.service = Service()
                setattr(self.service, field, True)
                with self.assertRaises(MaintenanceDeferred):
                    self.run_close()
                self.assertTrue(self.service.timer)
        self.assertFalse(self.calls)

    def test_bad_exit_proof_does_not_confirm_closure(self):
        self.setup_open()
        self.replies[4] = self.reply(dict(transaction=dict(self.fill, tradesClosed=[dict(tradeID='other')])))
        with self.assertRaises(ValueError):
            self.run_close()
        self.assertTrue((self.directory / 'request.json').exists())

    def test_claim_write_failure_prevents_mutation(self):
        self.setup_open()
        original = close._save

        def save(path, document, **kwargs):
            if path.name == 'request.json':
                raise OSError('Offline disk failure')
            return original(path, document, **kwargs)

        with patch.object(close, '_save', side_effect=save), self.assertRaises(OSError):
            self.run_close()
        self.assertFalse(self.puts())
        self.assertTrue(self.service.timer)

    def test_guard_blocks_other_mutations_and_a_second_close(self):
        self.setup_open()
        self.run_close()
        for method, path, payload in [('POST','/orders',{}), ('PUT','/trades/2252/close',{'units':'ALL'}),
                                      ('PUT','/trades/2251/close',{'units':'ALL'})]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.transport.guard(method, path, payload)

    def test_native_transport_uses_practice_host_and_the_guard(self):
        # Exercise the installed transport path, without opening any network socket.
        self.setup_open()
        with patch('nnfx_practice.broker.HTTPSConnection') as connection:
            def response():
                reply = self.replies.pop(0)
                body = Mock(status=reply.status)
                body.read.return_value = json.dumps(reply.body).encode()
                body.getheader.return_value = 'offline-request-id'
                return body
            connection.return_value.getresponse.side_effect = response
            result = close.execute(self.root, self.bound, self.service, transport_factory=_PracticeTransport)
            self.assertEqual(result['outcome'], 'confirmed_closed')
            connection.assert_called_once_with('api-fxpractice.oanda.com', timeout=5)
            mutations = [call for call in connection.return_value.request.call_args_list if call.args[0] == 'PUT']
            self.assertEqual(len(mutations), 1)
            self.assertEqual(json.loads(mutations[0].kwargs['body']), {'units':'ALL'})
            self.assertTrue((self.directory / 'request.json').exists())

    def test_private_settings_require_their_owner_then_worker_can_close(self):
        # Reproduce the production failure through the actual private-settings
        # loader, then run that loader and the close with the correct identity.
        uid = os.getuid()
        with patch('nnfx_practice.config.os.getuid', return_value=uid + 1):
            with self.assertRaisesRegex(ConfigurationError, 'owner-only'):
                load_account_binding(self.root, 'controller-a')
        self.setup_open()
        original = close.execute
        with patch.object(close, 'DATA', self.root), patch.object(close, 'CONTROLLER', 'controller-a'), \
                patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=uid)), \
                patch.object(close, 'controller_service', return_value=self.service), \
                patch.object(close, 'execute', side_effect=lambda root, binding, service, **kwargs:
                             original(root, binding, service, transport_factory=self.factory, **kwargs)):
            result = close.worker()
        self.assertEqual(result['outcome'], 'confirmed_closed')
        self.assertEqual(len(self.puts()), 1)
        self.assertEqual((self.root / '.env').stat().st_uid, uid)
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)

    def test_worker_rejects_wrong_identity_before_loading_private_settings(self):
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid()+1)), \
                patch.object(close, 'load_account_binding') as load:
            result = close.worker()
        load.assert_not_called()
        self.assertEqual(result['phase'], 'service_identity')
        self.assertEqual(result['broker_requests'], 0)

    def test_worker_configuration_failure_reports_phase_without_private_text(self):
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid())), \
                patch.object(close, 'load_account_binding', side_effect=ConfigurationError('private-secret')), \
                patch.object(close, 'execute') as execute:
            result = close.worker()
        execute.assert_not_called()
        self.assertEqual(result['phase'], 'configuration')
        self.assertEqual(result['broker_mutations'], 0)
        self.assertNotIn('private-secret', json.dumps(result))

    def test_administrator_launch_uses_sealed_copy_and_installed_service_identity(self):
        result = dict(outcome='confirmed_closed', closing_transaction_id='2254')
        process = Mock(returncode=0)
        copied = []

        def launch(args, **kwargs):
            self.assertEqual(args[:7], ['/usr/sbin/runuser', '-u', 'nnfx-run', '--', str(close.PYTHON), '-I', '-B'])
            self.assertEqual(args[8:], ['--worker'])
            path = Path(args[7])
            copied.append(path)
            self.assertEqual(path.read_bytes(), Path(close.__file__).read_bytes())
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o750)
            self.assertEqual(kwargs['cwd'], '/')
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(set(kwargs['env']), {'PATH','LC_ALL'})
            process.communicate.return_value = (json.dumps(result), 'never export stderr')
            return process

        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=os.getgid())), \
                patch.object(close.os, 'chown') as chown, patch.object(close.subprocess, 'Popen', side_effect=launch):
            self.assertEqual(close.run_worker(), result)
        self.assertEqual(chown.call_count, 2)
        self.assertTrue(all(call.args[1:] == (0, os.getgid()) for call in chown.call_args_list))
        self.assertFalse(copied[0].exists())

    def test_administrator_does_not_accept_inconsistent_worker_success(self):
        process = Mock(returncode=0)
        process.communicate.return_value = (json.dumps(dict(outcome='still_open')), '')
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=os.getgid())), \
                patch.object(close.os, 'chown'), patch.object(close.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(ValueError, 'consistent'):
                close.run_worker()

    def test_worker_timeout_terminates_group_without_relaunch(self):
        process = Mock(pid=12345)
        process.communicate.side_effect = [subprocess.TimeoutExpired('offline',600), ('','')]
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=os.getgid())), \
                patch.object(close.os, 'chown'), patch.object(close.subprocess, 'Popen', return_value=process) as launch, \
                patch.object(close.os, 'killpg') as kill:
            with self.assertRaisesRegex(ValueError, 'timed out'):
                close.run_worker()
        launch.assert_called_once()
        kill.assert_called_once_with(12345, close.signal.SIGTERM)

    def test_inspect_only_has_no_mutation_guard_or_close_claim(self):
        self.replies = [self.reply(dict(account=self.summary)), self.reply(dict(trade=self.trade))]
        result = close.execute(self.root, self.bound, self.service,
                               transport_factory=self.factory, inspect_only=True)
        self.assertEqual(result['outcome'], 'inspection_complete')
        self.assertEqual(result['mode'], 'inspect_only')
        self.assertEqual(result['stop_loss_order']['id'], '2252')
        self.assertEqual(self.calls, [('GET','/summary',None), ('GET','/trades/2251',None)])
        self.assertIsNone(self.transport.guard)
        self.assertFalse((self.directory/'request.json').exists())

    def test_inspect_flag_reaches_worker_and_transport_boundary(self):
        process = Mock(returncode=0)
        process.communicate.return_value = (json.dumps(dict(outcome='inspection_complete', mode='inspect_only')), '')
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=os.getgid())), \
                patch.object(close.os, 'chown'), patch.object(close.subprocess, 'Popen', return_value=process) as launch:
            self.assertEqual(close.run_worker(inspect_only=True)['outcome'], 'inspection_complete')
        self.assertEqual(launch.call_args.args[0][-2:], ['--worker','--inspect-only'])
        with patch.object(close.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid())), \
                patch.object(close, 'load_account_binding', return_value=self.bound), \
                patch.object(close, 'controller_service', return_value=self.service), \
                patch.object(close, 'execute', return_value={}) as execute:
            close.worker(inspect_only=True)
        execute.assert_called_once_with(close.DATA, self.bound, self.service, inspect_only=True)

    def test_failed_account_read_exposes_status_and_never_claims_close(self):
        self.replies = [self.reply(None, 520)]
        with self.assertRaises(BrokerError) as raised:
            self.run_close()
        result = close.failure(raised.exception, 'account_close')
        self.assertEqual(result['http_status'], 520)
        self.assertEqual(result['request_path'], '/summary')
        self.assertFalse(self.puts())
        self.assertFalse((self.directory/'request.json').exists())
        self.assertTrue(self.service.timer)
