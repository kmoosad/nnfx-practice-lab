"""Owner-authorized, one-attempt practice close for the 20 November failed entry.

Run with the installed interpreter as administrator. This incident-only action
does not run the controller, migrate/write its notebook or clear its issue.
The --inspect-only option reads account/trade evidence without a mutation guard.
Reruns only inspect OANDA after an attempt has been durably claimed, including
after rejection or lost response. The normal controller permits are unchanged.
"""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import pwd
import signal
import stat
import subprocess
import sys
import tempfile
from uuid import uuid4

from nnfx_practice.broker import BrokerError, _PracticeTransport, broker_id, money
from nnfx_practice.config import load_account_binding
from nnfx_practice.control import maintenance
from nnfx_practice.evidence import redact
from nnfx_practice.host import controller_service
from nnfx_practice.qualification import account_identity


ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/var/lib/nnfx-practice')
PYTHON = Path('/opt/nnfx-practice/.venv/bin/python')
CONTROLLER = 'practice-a'
TRADE = '2251'
ACCOUNT_DIGEST = 'e7672a6e291ad80d603c429326e1d881faf10ad4c8dcf9083f81a67ee9343b87'
ACTION = 'close-gbpcad-2251-20261121'
OPEN_TIME = '2026-11-20T21:50:08.840363542Z'
SUCCESS = ('confirmed_closed', 'inspection_complete')


def _directory(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_mode & 0o077):
        raise ValueError('Operator evidence directory must be private and owned by the executing administrator')


def _save(path, document, *, append=False):
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    flags |= os.O_APPEND if append else os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, 'a' if append else 'w') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_uid != os.geteuid() or info.st_mode & 0o077):
            raise ValueError('Unexpected operator evidence file permissions or type')
        stream.write(json.dumps(document, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _trade(body):
    trade = body.get('trade', {}) if isinstance(body, dict) else {}
    if (trade.get('id') != TRADE or trade.get('instrument') != 'GBP_CAD'
            or money(trade.get('initialUnits')) != -42665
            or money(trade.get('price')) != money('1.87722')
            or trade.get('openTime') != OPEN_TIME):
        raise ValueError('Broker trade does not match the confirmed failed-entry fill')
    units = money(trade.get('currentUnits'))
    if not ((trade.get('state') == 'OPEN' and -42665 <= units < 0)
            or (trade.get('state') == 'CLOSED' and units == 0)):
        raise ValueError('Unexpected broker trade state or remaining units')
    return trade


def execute(root, binding, service, *, transport_factory=_PracticeTransport, inspect_only=False):
    if account_identity(binding) != ACCOUNT_DIGEST:
        raise ValueError('Account binding differs from the investigated practice account')
    with maintenance(root, binding, service):
        parent = root / 'var/operator-actions'
        _directory(parent)
        directory = parent / ACTION
        _directory(directory)
        journal, claim = directory / 'responses.jsonl', directory / 'request.json'
        private = (binding.connection.account_id, binding.connection.token)
        account_path = '/v3/accounts/' + binding.connection.account_id
        used = False

        def record(event):
            _save(journal, redact(dict(at=datetime.now(UTC).isoformat(), **event), private), append=True)

        def guard(method, path, payload):
            nonlocal used
            if (used or method != 'PUT' or path != f'/trades/{TRADE}/close'
                    or payload != {'units': 'ALL'}):
                raise ValueError('Only one close of the specified practice trade is authorized')
            _save(claim, dict(action=ACTION, account_binding_sha256=ACCOUNT_DIGEST,
                             method=method, path=path, payload=payload,
                             at=datetime.now(UTC).isoformat(),
                             authority='Owner requested exit of the failed GBP-CAD entry'))
            used = True

        transport = transport_factory(binding.connection, 5, 15,
                                      mutation_guard=None if inspect_only else guard)
        try:
            def request(method, path, payload=None):
                record(dict(event='request', method=method, path=path, payload=payload))
                reply = transport.request(method, account_path + path, payload)
                record(dict(event='response', method=method, path=path, status=reply.status,
                            request_id=reply.request_id, body=reply.body))
                return reply

            def get(path):
                reply = request('GET', path)
                if reply.status != 200 or not isinstance(reply.body, dict):
                    raise BrokerError('Operator verification read failed', status=reply.status,
                                      evidence={'method':'GET', 'path':path})
                return reply.body

            def summary():
                account = get('/summary').get('account', {})
                if (account.get('id') != binding.connection.account_id
                        or account.get('currency') != binding.connection.home_currency):
                    raise ValueError('Broker account summary does not match the bound account')
                return account

            summary()
            trade = _trade(get(f'/trades/{TRADE}'))
            response = None
            if trade['state'] == 'OPEN' and not inspect_only and not os.path.lexists(claim):
                try:
                    response = request('PUT', f'/trades/{TRADE}/close', {'units': 'ALL'})
                except BrokerError:
                    # A lost response must not lead to a second mutation.
                    record(dict(event='close_response_uncertain', retry_allowed=False))
                trade = _trade(get(f'/trades/{TRADE}'))
            result = dict(action=ACTION, broker_state=trade['state'],
                          mode='inspect_only' if inspect_only else 'close',
                          current_units=trade['currentUnits'], request_sent_this_invocation=used,
                          earlier_attempt_exists=claim.exists() and not used,
                          notebook_writes=False, issue_cleared=False, retry_allowed=False)
            if trade['state'] == 'CLOSED':
                ids = trade.get('closingTransactionIDs')
                if not isinstance(ids, list) or not ids:
                    raise ValueError('Closed trade is missing its closing transaction identifiers')
                closing_id = broker_id(ids[-1])
                closing = get('/transactions/' + closing_id).get('transaction', {})
                if (closing.get('id') != closing_id or closing.get('type') != 'ORDER_FILL'
                        or not any(row.get('tradeID') == TRADE
                                   for row in closing.get('tradesClosed', []))):
                    raise ValueError('Closing transaction does not confirm the specified trade exit')
                result.update(outcome='confirmed_closed', closing_transaction_id=closing_id)
                summary()
            elif inspect_only:
                result.update(outcome='inspection_complete', account_read_verified=True,
                              stop_loss_order={key:trade.get('stopLossOrder', {}).get(key)
                                               for key in ('id','state','price')})
            else:
                body = response.body if response and isinstance(response.body, dict) else {}
                result.update(outcome='still_open', close_http_status=response.status if response else None,
                              broker_reason=body.get('errorCode') or
                              body.get('orderRejectTransaction', {}).get('rejectReason') or
                              body.get('orderCancelTransaction', {}).get('reason'))
            record(dict(event='result', result=result))
            return result
        finally:
            transport.close()


def failure(error, phase):
    # Never serialize arbitrary exception text, subprocess stderr or private
    # settings. The phase identifies failures before any broker operation.
    result = dict(outcome='inspection_required', error_type=type(error).__name__,
                  phase=phase, retry_allowed=False, notebook_writes=False, issue_cleared=False)
    if phase in ('service_identity', 'configuration'):
        result.update(broker_requests=0, broker_mutations=0)
    if isinstance(error, BrokerError):
        result['http_status'] = error.status
        if isinstance(error.evidence, dict):
            result['request_path'] = error.evidence.get('path')
    return result


def worker(*, inspect_only=False):
    phase = 'service_identity'
    try:
        uid = pwd.getpwnam('nnfx-run').pw_uid
        if os.getuid() != uid or os.geteuid() != uid:
            raise ValueError('The dedicated trading account must load its private settings')
        phase = 'configuration'
        binding = load_account_binding(DATA, CONTROLLER)
        phase = 'account_close'
        return execute(DATA, binding, controller_service(CONTROLLER), inspect_only=inspect_only)
    except Exception as error:
        return failure(error, phase)


def run_worker(*, inspect_only=False):
    # Use the same service identity boundary as the deployed administrator
    # preparation tools. Root never loads, copies or changes the private .env.
    # A temporary root-owned copy is readable by the service group even when
    # the source checkout's home directory cannot be traversed by nnfx-run.
    group = pwd.getpwnam('nnfx-run').pw_gid
    with tempfile.TemporaryDirectory(prefix='nnfx-operator-close-') as temporary:
        directory = Path(temporary)
        os.chown(directory, 0, group)
        directory.chmod(0o750)
        script = directory / 'close.py'
        script.write_bytes(Path(__file__).read_bytes())
        os.chown(script, 0, group)
        script.chmod(0o640)
        process = subprocess.Popen(
            ['/usr/sbin/runuser', '-u', 'nnfx-run', '--', str(PYTHON), '-I', '-B', str(script), '--worker',
             *(['--inspect-only'] if inspect_only else [])],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
            cwd='/', env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL':'C'})
        try:
            stdout, _ = process.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            raise ValueError('Worker timed out; inspect its retained attempt and maintenance state') from None
        if process.returncode not in (0, 2):
            raise ValueError('Worker failed; inspect its retained attempt and maintenance state')
        result = json.loads(stdout)
        if (not isinstance(result, dict)
                or result.get('outcome') not in (*SUCCESS, 'still_open', 'inspection_required')
                or (process.returncode == 0) != (result['outcome'] in SUCCESS)):
            raise ValueError('Worker did not return a consistent close result')
        return result


def main():
    os.umask(0o077)
    if sys.argv[1:] not in ([], ['--inspect-only'], ['--worker'], ['--worker','--inspect-only']):
        raise SystemExit('Unexpected command arguments')
    inspect_only = '--inspect-only' in sys.argv[1:]
    if '--worker' in sys.argv[1:]:
        result = worker(inspect_only=inspect_only)
        print(json.dumps(result), flush=True)
        return 0 if result['outcome'] in SUCCESS else 2
    if os.geteuid() != 0:
        raise SystemExit('Administrator access is needed to run the close under the trading account and export evidence')
    output = ROOT / 'var/verification/operator-close-2251' / ('inspection-' + uuid4().hex[:12])
    output.mkdir(mode=0o700, parents=True)
    try:
        result = run_worker(inspect_only=inspect_only)
    except Exception as error:
        result = failure(error, 'worker_launch_or_result')
    directory = DATA / 'var/operator-actions' / ACTION
    for name in ('request.json', 'responses.jsonl'):
        source = directory / name
        if source.is_file() and not source.is_symlink():
            (output / name).write_bytes(source.read_bytes())
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    owner = ROOT.stat()
    for path in output.iterdir():
        path.chmod(0o600)
        os.chown(path, owner.st_uid, owner.st_gid)
    os.chown(output, owner.st_uid, owner.st_gid)
    print(json.dumps(dict(result, output=str(output / 'result.json'))), flush=True)
    return 0 if result['outcome'] in SUCCESS else 2


if __name__ == '__main__':
    raise SystemExit(main())
