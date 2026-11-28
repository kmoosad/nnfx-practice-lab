"""M07 offline account model: broker-shaped facts, never practice evidence."""

from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlsplit

from nnfx_practice.broker import PracticeBroker
from nnfx_practice.config import PERMITTED_PAIRS
from nnfx_practice.control import MaintenanceDeferred, controller_exclusion
from nnfx_practice.evidence import redact
from nnfx_practice.lifecycle import EXECUTION_REQUIREMENTS, initialize_qualification
from nnfx_practice.notebook import open_notebook
from strategies import t3_bandpass_v1 as selected
from .support import ACCOUNT, TOKEN, Call, NotebookCase
from .test_m02 import ROOT, account, event, history, open_trade, order_fill, protection, reply
from .test_m03 import daily_body
from .test_m04 import instruments_body, pricing_body


EVIDENCE = {key: 'offline-fixture:' + key for key in EXECUTION_REQUIREMENTS}


def record_legacy_activation(case):
    """Build an archived A0 fixture; the application no longer creates these."""
    from nnfx_practice.notebook import transaction
    from nnfx_practice.reconciliation import reconcile_snapshot
    with controller_exclusion(case.root, case.bound):
        identifier = reconcile_snapshot(case.db, case.broker, purpose='activation')
        snapshot = case.db.execute('SELECT * FROM account_snapshots WHERE snapshot_id=?', (identifier,)).fetchone()
        with transaction(case.db):
            case.db.execute('UPDATE notebook SET activation_snapshot_id=?, activation_transaction_id=?, activation_evidence_json=?, activated_at=?',
                            (identifier, snapshot['last_transaction_id'], '{"source":"fixture","references":{}}', case.broker.now()))
    return identifier


class Service:
    def __init__(self):
        self.timer, self.active, self.pending = True, False, False
        self.events = []
        self.pause_fails = False

    def timer_active(self):
        return self.timer

    def pause_timer(self):
        self.events.append('pause')
        if not self.pause_fails:
            self.timer = False

    def service_active(self):
        return self.active

    def launch_pending(self):
        return self.pending

    def restore_timer(self, prior):
        self.events.append('restore:' + str(prior))
        self.timer = prior


class World:
    def __init__(self, case):
        self.case = case
        self.calls, self.traces = [], []
        self.records, self.trades, self.orders, self.closed = [], {}, {}, {}
        self.cursor = 100
        self.balance = '1000.00'
        self.summary_balances = []
        self.margin = '100000'
        self.candle_count = {}
        self.signals = {}
        self.open_signal = 'no_event'
        self.exit_signal = 'no_event'
        self.atr = 0.001
        self.on_call = None
        self.capture = None
        self.known_binding = case.bound

    def add(self, kind, **values):
        self.cursor += 1
        body = event(self.cursor, kind, **values)
        self.records.append(body)
        return body

    def add_fill(self, trade, *, pl='0', reason='MARKET_ORDER_TRADE_CLOSE'):
        self.cursor += 1
        body = order_fill(self.cursor, trade['id'], units=trade['currentUnits'], name=trade['instrument'], pl=pl, reason=reason)
        self.records.append(body)
        from decimal import Decimal
        self.balance = str(Decimal(self.balance) + Decimal(pl))
        self.trades.pop(trade['id'], None)
        self.closed[trade['id']] = {**trade, 'state': 'CLOSED', 'closingTransactionIDs': [body['id']]}
        return body

    def snapshot(self):
        return account(self.cursor, self.balance, account_id=self.known_binding.connection.account_id,
                       currency=self.known_binding.connection.home_currency, trades=self.trades.values(), orders=self.orders.values())

    def request(self, method, path, payload=None):
        call = Call(method, path, deepcopy(payload))
        self.calls.append(call)
        # The transport is reached only after the launch/maintenance lock.
        try:
            with controller_exclusion(self.case.root, self.known_binding):
                raise AssertionError('Broker read/write was outside controller exclusion')
        except MaintenanceDeferred:
            pass
        db = getattr(self.case, 'db', None)
        if db is not None:
            decisions = [dict(r) for r in db.execute('SELECT run_id,stage,pair,outcome FROM pair_decisions')]
            attempts = [dict(r) for r in db.execute('SELECT purpose,outcome FROM broker_attempts')]
            self.traces.append({'call': asdict(call), 'committed_decisions': decisions, 'committed_attempts': attempts})
        if self.on_call:
            result = self.on_call(call)
            if result is not None:
                return result
        url = urlsplit(path)
        relative = url.path.removeprefix('/v3/accounts/' + self.known_binding.connection.account_id)
        query = parse_qs(url.query)
        if method == 'GET':
            if relative in ('', '/summary'):
                body = self.snapshot()
                body['account']['marginAvailable'] = self.margin
                if relative == '/summary' and self.summary_balances:
                    body['account']['balance'] = self.summary_balances.pop(0)
                return reply(body)
            if relative == '/instruments':
                return reply(instruments_body())
            if relative == '/pricing':
                return reply(pricing_body(self.known_binding.connection.home_currency))
            if relative.endswith('/candles'):
                pair = relative.split('/')[2].replace('_', '-')
                stage = db.execute("SELECT status FROM stages WHERE run_id = ? AND stage = 'manage_new'", (self.case.run_id,)).fetchone()
                stage = 'new' if stage and stage[0] == 'running' else 'open'
                self.capture = pair, stage
                body = daily_body(self.case.clock.now().date(), count=self.candle_count.get(pair, 386))
                body['instrument'] = pair.replace('-', '_')
                for candle in body['candles']:
                    candle['mid'] = dict.fromkeys(('o', 'h', 'l', 'c'), '1.10000')
                return reply(body)
            if relative == '/transactions/sinceid':
                return reply(history(self.cursor, *(b for b in self.records if int(b['id']) > int(query['id'][0]))))
            kind, identifier = relative.strip('/').split('/')
            if kind == 'trades':
                trade = self.trades.get(identifier) or self.closed.get(identifier)
                return reply({'trade': deepcopy(trade), 'lastTransactionID': str(self.cursor)})
            if kind == 'orders':
                return reply({'order': deepcopy(self.orders[identifier]), 'lastTransactionID': str(self.cursor)})
            if kind == 'transactions':
                return reply({'transaction': next(b for b in self.records if b['id'] == identifier)})
        if method == 'POST' and relative == '/orders':
            order = payload['order']
            create = self.add('MARKET_ORDER', **{k: v for k, v in order.items() if k not in ('type', 'stopLossOnFill', 'tradeClientExtensions')})
            self.cursor += 1
            identifier = str(self.cursor)
            fill = order_fill(self.cursor, identifier, effect='open', units=order['units'], name=order['instrument'],
                              reason='MARKET_ORDER', order_id=create['id'])
            self.records.append(fill)
            from decimal import Decimal
            stop_price = str(Decimal('1.1') + Decimal(order['stopLossOnFill']['distance']) * (-1 if Decimal(order['units']) > 0 else 1))
            stop = self.add('STOP_LOSS_ORDER', tradeID=identifier, price=stop_price, timeInForce='GTC')
            for body in (create, fill, stop):
                body['batchID'] = create['id']
            trade = open_trade(identifier, units=order['units'], initial=order['units'], name=order['instrument'],
                               stop_id=stop['id'], stop_price=stop_price)
            trade['stopLossOrder']['timeInForce'] = 'GTC'
            self.trades[identifier] = trade
            return self.response(create, fill, stop)
        if method == 'PUT':
            identifier = relative.split('/')[2]
            if relative.endswith('/close'):
                return self.response(self.add_fill(self.trades[identifier]))
            key = 'takeProfit' if 'takeProfit' in payload else 'stopLoss'
            kind = 'TAKE_PROFIT' if key == 'takeProfit' else 'STOP_LOSS'
            body = self.add(kind + '_ORDER', tradeID=identifier, **payload[key])
            self.trades[identifier][key + 'Order'] = protection(body['id'], identifier, kind, payload[key]['price'], timeInForce='GTC')
            return self.response(body)
        raise AssertionError(f'Unsupported offline request {method} {relative}')

    def response(self, *bodies):
        return reply({'lastTransactionID': str(self.cursor), **{f't{i}Transaction': b for i, b in enumerate(bodies)}})

    def observe(self, candles):
        assert len(candles) == 386
        pair, stage = self.capture
        direction = self.open_signal if stage == 'open' else self.signals.get(pair, 'no_event')
        return selected.EventObservation(direction, selected.C1_RULE_ID, selected.C1_OUTPUTS,
                                         (direction == 'long', direction == 'short'), (False, False))


class M07Case(NotebookCase):
    def setUp(self):
        super().setUp()
        registry = self.root / 'config.toml'
        registry.write_text(registry.read_text().replace('"fixture-v1"', '"t3_bandpass_v1"'))
        manifest = self.root / 'strategies/t3_bandpass_v1/manifest.json'
        manifest.parent.mkdir()
        manifest.write_bytes(Path(selected.__file__).with_name('manifest.json').read_bytes())
        self.write_private(count=386)
        self.bound = self.binding()
        self.service = Service()
        self.world = World(self)
        self.broker = PracticeBroker(self.bound, transport=self.world, now=self.clock.now)
        self.run_id = 'master-1'
        self.transports = [self.world]

    def initialize(self):
        identifier = initialize_qualification(self.root, 'controller-a', self.broker, service=self.service, evidence=EVIDENCE)
        if not hasattr(self, 'db'):
            self.db = self.enterContext(open_notebook(self.root, self.bound))
        return identifier

    def tearDown(self):
        destination = os.environ.get('NNFX_M07_EVIDENCE_DIR')
        if destination:
            db = getattr(self, 'db', None)
            extra = None
            path = self.bound.experiment.notebook_path(self.root)
            if db is None and path.exists():
                extra = db = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
                db.row_factory = sqlite3.Row
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")] if db else []
            data = {'classification': 'offline', 'test': self.id(), 'run_id': self.run_id,
                    'manifest_hash': self.bound.manifest.hash, 'lookback': 386,
                    'tables': {t: [dict(r) for r in db.execute(f'SELECT * FROM {t}')] for t in tables},
                    'second_notebook': getattr(self, 'second_notebook_evidence', None),
                    'inputs': {'signals': self.world.signals, 'management_c1': self.world.open_signal,
                               'management_exit': self.world.exit_signal, 'atr': self.world.atr,
                               'candle_counts': self.world.candle_count},
                    'calls': [asdict(c) for w in self.transports for c in w.calls],
                    'traces': [t for w in self.transports for t in w.traces],
                    'service_events': self.service.events,
                    'integrity': db.execute('PRAGMA integrity_check').fetchone()[0] if db else 'not_created',
                    'foreign_keys': [list(r) for r in db.execute('PRAGMA foreign_key_check')] if db else []}
            if extra:
                extra.close()
            path = Path(destination) / (self.id().split('.')[-1] + '.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(redact(data, (TOKEN, ACCOUNT)), indent=2) + '\n')
        super().tearDown()
