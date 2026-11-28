"""Protected practice permits, retaining legacy plan, timer and claim identities.

Legacy dated sessions and automatic weekdays share one execution path. Existing
qualification spellings and authority records remain compatible; no ordinary mode.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import pwd
import re
import stat
import subprocess
from zoneinfo import ZoneInfo

from .broker import PRACTICE_HOST, PracticeBroker, broker_id, money
from .config import ConfigurationError, PERMITTED_PAIRS, load_binding
from .evidence import canonical_json
from .lifecycle import EXECUTION_REQUIREMENTS, initialize_qualification, validate_strategy
from .strategy import manifest_for_hash


PLAN_DIRECTORY = Path('/etc/nnfx-practice/qualification')
CODE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path('/var/lib/nnfx-practice')
NY = ZoneInfo('America/New_York')
_SHA = re.compile(r'[a-f0-9]{64}')
_RUN = re.compile(r'[a-z0-9][a-z0-9_-]{0,63}')
PLAN_REQUIREMENTS = (*EXECUTION_REQUIREMENTS, 'private_connection')
_VERIFIED = object()
SCHEDULE = 'Mon..Fri *-*-* 16:50:00 America/New_York'


def dispatch_slot(plan, operation, now):
    """The scheduler chooses the day; this guard rejects late/manual catch-up."""
    try:
        first = datetime.fromisoformat(plan['dispatch_at'])
        local = first.astimezone(NY)
        if first.utcoffset() != timedelta(0) or local.weekday() >= 5 or (
                local.hour, local.minute, local.second, local.microsecond) != (16, 50, 0, 0):
            raise ValueError
        if plan['version'] == 2:
            if plan.get('schedule') != SCHEDULE or operation == 'initialize':
                _fail('automatic qualification requires the approved schedule and existing Q0')
            today = now.astimezone(NY)
            slot = today.replace(hour=16, minute=50, second=0, microsecond=0).astimezone(UTC)
            if operation == 'run' and (today.weekday() >= 5 or slot < first):
                _fail('outside an eligible weekday session')
        else:
            slot = first
    except (KeyError, TypeError, ValueError):
        _fail('dispatch must be an explicit weekday 16:50 New York UTC instant')
    if operation == 'run' and not slot <= now < slot + timedelta(minutes=1):
        _fail('outside the explicit dispatch minute; no catch-up')
    if plan['version'] == 1 and now >= slot + timedelta(minutes=1):
        _fail('outside the explicit dispatch minute; no catch-up')
    return slot


def qualification_timer(controller):
    return 'nnfx-practice-qualification@' + controller + '.timer'


def schedule_controls(controller, *, running=True):
    """Exactly one reviewed recurring trigger, targeting the existing service."""
    stem = 'nnfx-practice@' + controller
    selected = qualification_timer(controller)
    other = stem + '.timer'
    for unit in (selected, other):
        state = _command('systemctl', 'show', unit,
                         '--property=LoadState,ActiveState,UnitFileState,Job,DropInPaths,Unit,Persistent,AccuracyUSec,RandomizedDelayUSec,TimersCalendar')
        if unit == other and _retired_timer_absent(state):
            continue
        if (state.get('LoadState') != 'loaded' or state.get('Job') not in ('', '0')
                or state.get('DropInPaths') != ''):
            _fail('recurring timer is unavailable, modified or has a pending job')
        if unit == selected:
            if (state.get('Unit') != stem + '.service' or state.get('Persistent') != 'no'
                    or state.get('AccuracyUSec') != '1s' or state.get('RandomizedDelayUSec') != '0'
                    or state.get('TimersCalendar', '').count('OnCalendar=') != 1
                    or 'OnCalendar=' + SCHEDULE + ' ;' not in state['TimersCalendar']
                    or (running and state.get('ActiveState') != 'active')):
                _fail('recurring timer differs from the approved schedule')
        if unit == other or not running:
            if state.get('ActiveState') != 'inactive' or state.get('UnitFileState') != 'disabled':
                _fail('inactive schedule must be disabled with no pending launch')
    triggers = _command('systemctl', 'show', stem + '.service', '--property=TriggeredBy')
    for unit in triggers.get('TriggeredBy', '').split():
        if unit in (selected, other):
            continue
        state = _command('systemctl', 'show', unit, '--property=ActiveState,Job')
        if state.get('ActiveState') != 'inactive' or state.get('Job') not in ('', '0'):
            _fail('another controller trigger is still active')


def _fail(reason):
    raise ConfigurationError('Practice trading blocked: ' + reason)


def _retired_timer_absent(state):
    return (state.get('LoadState') == 'not-found' and state.get('ActiveState') == 'inactive'
            and state.get('UnitFileState') in ('', None) and state.get('Job') in ('', '0')
            and state.get('DropInPaths') == '')


def sealed_bytes(path):
    """Root-owned regular file, no writable ancestors, symlinks or hard links."""
    path = Path(path)
    if not path.is_absolute():
        _fail('evidence paths must be absolute')
    try:
        for directory in reversed(path.parents):
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                _fail('plan/evidence directory is not protected by root')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022
                    or info.st_nlink != 1 or info.st_size > 32 * 1024 * 1024):
                _fail('plan/evidence file is not protected by root')
            return source.read(32 * 1024 * 1024 + 1)
    except OSError:
        _fail('required protected plan/evidence file is unavailable')


def _document(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail('duplicate JSON field')
            result[key] = value
        return result
    try:
        result = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, RecursionError):
        _fail('invalid plan/evidence JSON')
    if not isinstance(result, dict):
        _fail('expected a plan/evidence object')
    return result


def code_hashes():
    paths = []
    for name in ('nnfx_practice', 'strategies'):
        for path in (CODE_ROOT / name).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix in (
                    '.py', '.sql', '.json', '.html', '.css'):
                paths.append(path)
    return {str(path.relative_to(CODE_ROOT)): sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def code_identity():
    return sha256(canonical_json(code_hashes()).encode()).hexdigest()


def host_identity():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip(), platform.release()


def deployed_unit_hashes():
    names = ['nnfx-practice@.service', 'nnfx-practice-qualification@.timer']
    if Path('/etc/systemd/system/nnfx-practice@.timer').exists():
        names.append('nnfx-practice@.timer')
    return {name: sha256(Path('/etc/systemd/system', name).read_bytes()).hexdigest() for name in names}


def account_identity(binding):
    # Same private identifier digest used by M04; never write the identifier.
    identity = [binding.experiment.controller_id, binding.experiment.notebook_id,
                binding.connection.account_id, binding.connection.home_currency]
    return sha256(canonical_json(identity).encode()).hexdigest()


def _command(*command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        _fail('host control inspection unavailable')
    if result.returncode:
        _fail('host control inspection failed')
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def host_controls(controller, operation):
    if _command('timedatectl', 'show', '--property=NTPSynchronized').get('NTPSynchronized') != 'yes':
        _fail('clock is not confirmed synchronized')
    stem = 'nnfx-practice@' + controller
    timer = _command('systemctl', 'show', stem + '.timer',
                     '--property=LoadState,ActiveState,UnitFileState,Job,DropInPaths')
    if not _retired_timer_absent(timer) and (timer.get('LoadState') != 'loaded' or timer.get('ActiveState') != 'inactive'
            or timer.get('UnitFileState') != 'disabled' or timer.get('Job') not in ('', '0')
            or timer.get('DropInPaths') != ''):
        _fail('legacy timer must be absent or disabled, inactive and without a job')
    host_service(controller, operation, clock_checked=True)


def host_service(controller, operation, *, clock_checked=False):
    if not clock_checked and _command('timedatectl', 'show', '--property=NTPSynchronized').get('NTPSynchronized') != 'yes':
        _fail('clock is not confirmed synchronized')
    stem = 'nnfx-practice@' + controller
    service = _command('systemctl', 'show', stem + '.service',
                       '--property=LoadState,ActiveState,MainPID,InvocationID,User,Group,Type,Restart,DropInPaths')
    if any(service.get(key) != value for key, value in (
            ('LoadState', 'loaded'), ('User', 'nnfx-run'), ('Group', 'nnfx-read'),
            ('Type', 'oneshot'), ('Restart', 'no'), ('DropInPaths', ''))):
        _fail('controller service contract differs')
    if operation == 'run':
        invocation = os.environ.get('INVOCATION_ID')
        if (service.get('ActiveState') not in ('active', 'activating')
                or service.get('MainPID') != str(os.getpid()) or not invocation
                or service.get('InvocationID') != invocation):
            _fail('qualification must run through its bound system controller service')
    elif service.get('ActiveState') not in ('inactive', 'failed'):
        _fail('controller must be inactive for qualification initialization/inspection')


def _evidence(plan):
    references = plan.get('evidence')
    if not isinstance(references, dict) or set(references) != set(PLAN_REQUIREMENTS):
        _fail('required qualification evidence is missing')
    documents = {}
    for name, ref in references.items():
        if (not isinstance(ref, dict) or ref.get('status') != 'passed'
                or not isinstance(ref.get('path'), str)
                or not isinstance(ref.get('sha256'), str) or not _SHA.fullmatch(ref['sha256'])):
            _fail('prerequisite evidence is pending or invalid: ' + name)
        raw = sealed_bytes(ref['path'])
        if sha256(raw).hexdigest() != ref['sha256']:
            _fail('prerequisite evidence changed: ' + name)
        documents[name] = _document(raw)
    return documents


def automatic_authority(plan):
    ref = plan.get('automatic_schedule_authority', {})
    if (not isinstance(ref, dict) or not isinstance(ref.get('path'), str)
            or not isinstance(ref.get('sha256'), str) or not _SHA.fullmatch(ref['sha256'])):
        _fail('automatic qualification schedule authority is missing')
    raw = sealed_bytes(ref['path'])
    authority = _document(raw)
    if (sha256(raw).hexdigest() != ref['sha256'] or any(authority.get(k) != plan.get(k) for k in
            ('controller_id', 'notebook_id', 'account_binding_sha256', 'schedule'))
            or not authority.get('statement') or authority.get('ordinary_activation_authorized') is not False
            or authority.get('ordinary_scheduled_trading_authorized') is not False):
        _fail('automatic qualification authority differs from this binding and scope')


def validate_evidence(plan, documents):
    """Check recorded observations, not just nonempty evidence references."""
    digest = plan['account_binding_sha256']
    manifest = manifest_for_hash(plan['manifest_sha256'])
    for name, phase in (('account_preflight', 'account'), ('candle_preflight', 'candles')):
        doc = documents[name]
        if any(doc.get(key) != value for key, value in (
                ('source', 'practice_get'), ('host', PRACTICE_HOST), ('status', 'passed'),
                ('phase', phase), ('account_binding_sha256', digest),
                ('controller_id', plan['controller_id']), ('notebook_id', plan['notebook_id']))):
            _fail('intended-account preflight is not a recorded pass: ' + name)
    candles = documents['candle_preflight']
    if (candles.get('manifest_sha256') != plan['manifest_sha256']
            or candles.get('lookback_candles') != manifest['qualified_total_candle_count']
            or candles.get('valid_windows') != 28
            or not isinstance(candles.get('pairs'), dict) or set(candles['pairs']) != set(PERMITTED_PAIRS)):
        _fail('qualified 28-pair candle preflight differs')
    strategy_ref = plan['evidence']['strategy_qualification']
    if strategy_ref['sha256'] != manifest.get('qualification_report_sha256'):
        _fail('strategy qualification differs from the packaged manifest')
    resolution = documents['initial_account_resolution']
    # An explicit root-reviewed resolution is required, even when M04 was clear.
    if (resolution.get('status') != 'passed' or resolution.get('account_binding_sha256') != digest
            or not isinstance(resolution.get('explanation'), str) or not resolution['explanation'].strip()):
        _fail('initial account activity resolution is missing')
    private = documents['private_connection']
    writer, viewer = pwd.getpwnam('nnfx-run'), pwd.getpwnam('nnfx-view')
    info = private.get('binding', {})
    if (private.get('private_checks_passed') is not True
            or info.get('account_binding_sha256') != digest
            or info.get('manifest_sha256') != plan['manifest_sha256']
            or info.get('uid') != writer.pw_uid or info.get('private_uid') != writer.pw_uid
            or info.get('private_gid') != writer.pw_gid or info.get('private_mode') != 0o600
            or viewer.pw_uid == writer.pw_uid or private.get('viewer', {}).get('uid') != viewer.pw_uid
            or private.get('viewer', {}).get('credential_readable') is not False):
        _fail('private binding and reader-denial evidence is missing')
    authority = documents['execution_authority']
    if (not isinstance(authority.get('account_label'), str) or not authority['account_label'].strip()
            or authority.get('account_binding_sha256') != digest
            or authority.get('controller_id') != plan['controller_id']
            or authority.get('notebook_id') != plan['notebook_id']
            or authority.get('practice_host') != PRACTICE_HOST
            or authority.get('manifest_sha256') != plan['manifest_sha256']
            or authority.get('strategy_version') != manifest['strategy_version']
            or not authority.get('owner_statement')
            or any(authority.get(key) is not False for key in (
                'ordinary_scheduled_trading_authorized', 'ordinary_activation_authorized',
                'strategy_changes_authorized', 'trade_2_unit_reduction_authorized'))):
        _fail('controlled practice-account owner authority differs')
    controls = documents['m09_controller_controls']
    results = controls.get('results', {})
    if not isinstance(results, dict):
        _fail('essential controller observations are malformed')
    dispatch = results.get('system_timer_dispatch')
    if (not isinstance(dispatch, list) or len(dispatch) != 2
            or any(not isinstance(row, dict) or row.get('uid') != writer.pw_uid
                   or row.get('gid') != writer.pw_gid or type(row.get('pid')) is not int
                   or row['pid'] <= 0 for row in dispatch)
            or [row.get('phase') for row in dispatch] != ['start', 'end']
            or dispatch[0]['pid'] != dispatch[1]['pid']):
        _fail('actual system-writer dispatch start/end evidence is missing')
    if (controls.get('classification') != 'system-manager broker-free fixtures'
            or controls.get('cleanup_errors') != [] or not results.get('system_timer_dispatch')
            or controls.get('registry_sha256') != plan['config_sha256']
            or results.get('clock') not in ('NTPSynchronized=yes', 'NTPSynchronized=yes\n')
            or any(results.get(key) is not True for key in (
                'no_automatic_restart', 'inactive_missed_no_catch_up',
                'no_overlap_independent_controller_active_deferral',
                'active-True-failure-False', 'active-True-failure-True',
                'active-False-failure-False', 'active-False-failure-True'))
            or controls.get('deployed_source_hashes') != code_hashes()):
        _fail('essential system-controller evidence is missing or stale')
    for name, observed in deployed_unit_hashes().items():
        expected = controls.get('source_hashes', {}).get('deploy/' + name)
        if not expected or observed != expected:
            _fail('controller unit differs from the tested system fixture')
    if plan['version'] == 2:
        dual = results.get('dual_timer_maintenance', [])
        expected = [(False, True, False), (False, True, True), (True, False, False), (False, False, True)]
        if (not isinstance(dual, list) or len(dual) != len(expected)
                or [(r.get('ordinary'), r.get('qualification'), r.get('failed')) for r in dual] != expected
                or any(r.get('outcome', {}).get('outcome') != ('intentional_failure' if r['failed'] else 'completed')
                       or r['outcome'].get('uid') != writer.pw_uid for r in dual)):
            _fail('automatic schedule requires observed dual-timer maintenance evidence')


@dataclass
class QualificationPermit:
    binding: object = field(repr=False)
    plan: dict = field(repr=False)
    path: Path
    digest: str
    operation: str
    claimed: bool = False
    pid: int = field(default_factory=os.getpid)
    slot: datetime | None = None
    _verification: object = field(default=None, init=False, repr=False)

    @property
    def references(self):
        return {name: ref['path'] + '#sha256=' + ref['sha256'] for name, ref in self.plan['evidence'].items()}

    @property
    def run_id(self):
        if self.plan['version'] == 1:
            return self.plan['run_id']
        return self.plan['run_id'] + '-' + self.slot.astimezone(NY).strftime('%Y%m%d')

    def check(self, binding):
        if (self._verification is not _VERIFIED or binding != self.binding or os.getpid() != self.pid
                or sha256(sealed_bytes(self.path)).hexdigest() != self.digest):
            _fail('permit binding/process changed or plan was revoked')

    def guard(self, method, path, payload):
        self.check(self.binding)
        if self.operation != 'run' or not self.claimed:
            _fail('initialization/inspection cannot send mutations')
        if method == 'POST' and path == '/orders' and isinstance(payload, dict) and set(payload) == {'order'}:
            order = payload['order']
            keys = {'type', 'instrument', 'units', 'timeInForce', 'positionFill', 'clientExtensions',
                    'tradeClientExtensions', 'stopLossOnFill'}
            if isinstance(order, dict) and set(order) == keys:
                protection = order['stopLossOnFill']
                client = order['clientExtensions']
                if (order['type'] == 'MARKET' and order['timeInForce'] == 'FOK'
                        and order['positionFill'] == 'OPEN_ONLY'
                        and order['instrument'] in {pair.replace('-', '_') for pair in PERMITTED_PAIRS}
                        and money(order['units']) != 0 and isinstance(protection, dict)
                        and set(protection) == {'distance', 'timeInForce'}
                        and protection['timeInForce'] == 'GTC' and money(protection['distance']) > 0
                        and isinstance(client, dict) and set(client) == {'id'}
                        and isinstance(client['id'], str) and re.fullmatch(r'[A-Za-z0-9_-]+', client['id'])
                        and order['tradeClientExtensions'] == client):
                    return
        match = re.fullmatch(r'/trades/([0-9]{1,32})/(close|orders)', path)
        if method == 'PUT' and match and isinstance(payload, dict):
            broker_id(match[1])
            if match[2] == 'close' and payload == {'units': 'ALL'}:
                return
            if match[2] == 'orders' and set(payload) in ({'stopLoss'}, {'takeProfit'}):
                value = next(iter(payload.values()))
                if (isinstance(value, dict) and set(value) == {'price', 'timeInForce'}
                        and value['timeInForce'] == 'GTC' and money(value['price']) > 0):
                    return
        _fail('request is outside the approved controller operation set')

    def claim(self, root):
        """Durable pre-network claim: a crash/failure never replays this session."""
        self.check(self.binding)
        if self.operation != 'run' or self.claimed or Path(root) != DATA_ROOT:
            _fail('expected one unclaimed qualification dispatch')
        slot = self.slot or datetime.fromisoformat(self.plan['dispatch_at'])
        if not slot <= datetime.now(UTC) < slot + timedelta(minutes=1):
            _fail('dispatch minute elapsed before claim; no catch-up')
        directory = Path(root) / 'var/qualification' / self.plan['controller_id']
        for path in (Path(root) / 'var', directory.parent, directory):
            if path.is_symlink():
                _fail('qualification evidence directory must not be a symlink')
            path.mkdir(mode=0o700, exist_ok=True)
        session = slot.astimezone(NY).date().isoformat()
        path = directory / (session + '.claim')
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            _fail('qualification session already attempted; inspect evidence, never replay')
        with os.fdopen(fd, 'w') as target:
            target.write(canonical_json({'run_id': self.run_id, 'plan_sha256': self.digest}) + '\n')
            target.flush()
            os.fsync(target.fileno())
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.claimed = True
        return directory


def load_permit(root, controller, operation, *, now=None):
    if (Path(root) != DATA_ROOT or not _RUN.fullmatch(controller)
            or operation not in ('initialize', 'run', 'inspect')):
        _fail('expected the deployed data root and explicit qualification operation')
    path = PLAN_DIRECTORY / (controller + '.json')
    raw = sealed_bytes(path)
    plan = _document(raw)
    if (type(plan.get('version')) is not int or plan['version'] not in (1, 2)
            or type(plan.get('enabled')) is not bool
            or (operation != 'inspect' and plan['enabled'] is not True)
            or plan.get('controller_id') != controller or plan.get('mode', 'qualification') not in ('practice', 'qualification')):
        _fail('qualification plan is missing, disabled or mismatched')
    for name in ('account_binding_sha256', 'manifest_sha256', 'code_sha256', 'config_sha256'):
        if not isinstance(plan.get(name), str) or not _SHA.fullmatch(plan[name]):
            _fail('invalid qualification identity: ' + name)
    if not isinstance(plan.get('run_id'), str) or not _RUN.fullmatch(plan['run_id']):
        _fail('explicit qualification run ID is required')
    if plan['version'] == 2 and len(plan['run_id']) > 54:
        _fail('automatic run prefix is too long')
    if (plan.get('host') != PRACTICE_HOST or plan.get('code_sha256') != code_identity()
            or plan.get('config_sha256') != sha256((Path(root) / 'config.toml').read_bytes()).hexdigest()
            or plan.get('kernel') != host_identity()[1]
            or (plan['version'] == 1 and plan.get('boot_id') != host_identity()[0])):
        _fail('account host, code, registry, boot or kernel differs from reviewed plan')
    now = datetime.now(UTC) if now is None else now
    slot = dispatch_slot(plan, operation, now)
    documents = _evidence(plan)
    validate_evidence(plan, documents)
    if plan['version'] == 2:
        automatic_authority(plan)
    host_controls(controller, operation)
    if plan['version'] == 2:
        schedule_controls(controller, running=operation == 'run')
    if operation == 'inspect':
        return {'plan_valid': True, 'qualification_ready': False, 'private_binding_checked': False,
                'plan_enabled': plan['enabled'],
                'dispatch_at': plan['dispatch_at'], 'ordinary_trading_enabled': False}
    if os.getuid() != pwd.getpwnam('nnfx-run').pw_uid:
        _fail('qualification requires the dedicated system writer identity')
    binding = load_binding(root, controller)
    validate_strategy(binding)
    if (account_identity(binding) != plan['account_binding_sha256']
            or binding.manifest.hash != plan['manifest_sha256']
            or binding.experiment.notebook_id != plan.get('notebook_id')):
        _fail('current private account/strategy/notebook binding differs')
    permit = QualificationPermit(binding, plan, path, sha256(raw).hexdigest(), operation, slot=slot)
    permit._verification = _VERIFIED
    return permit


class RetainedBroker(PracticeBroker):
    """Retain practice captures/responses with the existing evidence and fsync rules."""

    def __init__(self, permit, destination):
        self.destination = destination
        super().__init__(permit.binding, qualification=permit)

    def _retain_evidence(self, evidence):
        fd = os.open(self.destination, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as target:
            target.write(canonical_json({'source': self.evidence_source, **evidence}) + '\n')
            target.flush()
            os.fsync(target.fileno())

    def _retain(self, read):
        self._retain_evidence(read.evidence())
        return read

    def _get(self, *args, **kwargs):
        from .broker import BrokerError
        try:
            return self._retain(super()._get(*args, **kwargs))
        except BrokerError as error:
            self._retain_evidence(error.evidence or {'error': 'Broker read failed'})
            raise

    def _mutate(self, *args, **kwargs):
        return self._retain(super()._mutate(*args, **kwargs))


def execute(root, controller, operation):
    permit = load_permit(root, controller, operation)
    from .host import controller_service
    from .master import run_master
    if operation == 'initialize':
        # Read-only transport: a Q0 operation cannot place or change an order.
        with PracticeBroker(permit.binding, qualification=permit) as broker:
            return initialize_qualification(root, controller, broker, service=controller_service(controller),
                                            evidence=permit.references)
    directory = permit.claim(root)
    with RetainedBroker(permit, directory / (permit.run_id + '.jsonl')) as broker:
        return run_master(root, controller, broker, mode='practice', evidence=permit.references,
                          code_hash=permit.plan['code_sha256'], config_hash=permit.plan['config_sha256'],
                          run_id=permit.run_id)
