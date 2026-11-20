"""Local, read-only broker reconciliation followed by evidenced issue disposition."""

import json

from .broker import broker_id, money
from .control import maintenance
from .evidence import encode_evidence, redact
from .lifecycle import bound_broker
from .notebook import open_notebook
from .reconciliation import _release_closed_sets, reconcile_snapshot


class DispositionRequired(ValueError):
    pass


def _registered_evidence(db, issue, snapshot):
    legs = db.execute('SELECT * FROM trade_legs WHERE set_id = ? ORDER BY leg_no', (issue['set_id'],)).fetchall()
    if len(legs) != 2:
        raise DispositionRequired('Both registered legs must be accounted for')
    terminal_targets = []
    for leg in legs:
        if leg['broker_state'] == 'closed' and leg['exit_transaction_id'] and leg['broker_trade_id'] not in snapshot.trades:
            # A dependent target cannot remain queued after its trade is closed.
            # Keep the old uncertain response and the explicit disposition proof.
            for attempt in db.execute('''SELECT * FROM broker_attempts WHERE set_id = ? AND leg_no = ?
                AND purpose = 'entry_target' AND outcome IN ('prepared', 'pending', 'unknown')''',
                (leg['set_id'], leg['leg_no'])).fetchall():
                terminal_targets.append({'attempt_id': attempt['attempt_id'], 'prior_outcome': attempt['outcome'],
                                         'closing_transaction_id': leg['exit_transaction_id']})
                db.execute("UPDATE broker_attempts SET outcome = 'cancelled', broker_transaction_id = ? WHERE attempt_id = ?",
                           (leg['exit_transaction_id'], attempt['attempt_id']))
    attempts = db.execute('SELECT * FROM broker_attempts WHERE set_id = ?', (issue['set_id'],)).fetchall()
    if any(a['outcome'] in ('prepared', 'pending', 'unknown') for a in attempts):
        raise DispositionRequired('Broker evidence has not resolved every sent attempt')
    proof = {'trade_ids': [], 'transaction_ids': [], 'unsent_legs': [], 'terminal_targets': terminal_targets}
    allowed_orders = set()
    for leg in legs:
        identifier = leg['broker_trade_id']
        entries = [a for a in attempts if a['leg_no'] == leg['leg_no'] and a['purpose'] == 'entry']
        if identifier is None:
            if entries and not all(a['outcome'] in ('rejected', 'cancelled') and a['broker_transaction_id'] for a in entries):
                raise DispositionRequired('No-fill evidence is missing')
            # No prepared entry means this expected leg could not have been sent.
            if not entries:
                proof['unsent_legs'].append(leg['leg_no'])
            proof['transaction_ids'].extend(a['broker_transaction_id'] for a in entries)
            db.execute("UPDATE trade_legs SET broker_state = 'not_opened' WHERE set_id = ? AND leg_no = ?",
                       (leg['set_id'], leg['leg_no']))
        elif leg['broker_state'] == 'closed' and leg['exit_transaction_id'] and leg['exit_price']:
            if identifier in snapshot.trades:
                raise DispositionRequired('Closed leg still appears in the broker open list')
            proof['trade_ids'].append(identifier)
            proof['transaction_ids'].append(leg['exit_transaction_id'])
        elif leg['broker_state'] == 'open' and issue['code'] in ('stop_to_entry', 'missing_protection', 'unresolved_attempt'):
            trade = snapshot.trades.get(identifier)
            if not trade or trade.get('state') != 'OPEN':
                raise DispositionRequired('Surviving trade is not confirmed open')
            stop = trade.get('stopLossOrder') or snapshot.orders.get(leg['current_stop_order_id'])
            target = trade.get('takeProfitOrder') or snapshot.orders.get(leg['target_order_id'])
            if (not stop or stop.get('state') != 'PENDING' or stop.get('type') != 'STOP_LOSS'
                    or stop.get('id') != leg['current_stop_order_id']):
                raise DispositionRequired('Surviving trade has no confirmed protection')
            # Resolve only the failed action, not an arbitrary replacement stop.
            relevant = [a for a in attempts if a['attempt_id'] == issue['attempt_id']]
            stop_change = issue['code'] == 'stop_to_entry' or any(a['purpose'] == 'stop_to_entry' for a in relevant)
            if relevant and any(a['purpose'] != 'stop_to_entry' for a in relevant):
                raise DispositionRequired('A failed close or incomplete entry requires confirmed closure')
            expected = leg['entry_price'] if stop_change and leg['leg_no'] == 2 else leg['original_stop']
            if (expected is None or money(stop.get('price')) != money(expected)
                    or (leg['leg_no'] == 1 and (not target or target.get('state') != 'PENDING' or target.get('type') != 'TAKE_PROFIT'
                        or leg['intended_target'] is None or money(target.get('price')) != money(leg['intended_target'])))):
                raise DispositionRequired('Required protective levels have not been restored')
            proof['trade_ids'].append(identifier)
            proof['transaction_ids'].append(leg['broker_state_transaction_id'])
            allowed_orders.add(stop['id'])
            if target:
                allowed_orders.add(target['id'])
        else:
            raise DispositionRequired('Incomplete entry or unresolved leg requires confirmed closure')
    registered_ids = {leg['broker_trade_id'] for leg in legs if leg['broker_trade_id']}
    if any((order.get('instrument', '').replace('_', '-') == issue['pair'] or order.get('tradeID') in registered_ids)
           and order['id'] not in allowed_orders for order in snapshot.orders.values()):
        raise DispositionRequired('An order still affects this pair')
    if any(trade.get('instrument', '').replace('_', '-') == issue['pair']
           and identifier not in proof['trade_ids'] for identifier, trade in snapshot.trades.items()):
        raise DispositionRequired('Unregistered activity still affects this pair')
    _release_closed_sets(db, snapshot.read.responded_at)
    return proof


def record_disposition(root, controller_id, broker, *, service, issue_id, operator_id, explanation):
    """Resolve one issue using fresh broker facts. Never acknowledge uncertainty away.

    Registered issues require closed/no-fill legs, or a confirmed restored stop.
    Unregistered trade/order issues require their targeted terminal broker record
    plus reconciled closing/cancellation transactions. Unsupported uncertainty is
    left open for investigation; no repair, cancellation or close is submitted.
    """
    if not all(isinstance(value, str) and value.strip() for value in (issue_id, operator_id, explanation)):
        raise ValueError('Issue, operator and explanation are required')
    binding = bound_broker(root, controller_id, broker)
    with maintenance(root, binding, service):
        with open_notebook(root, binding) as db:
            issue = db.execute('SELECT * FROM issues WHERE issue_id = ?', (issue_id,)).fetchone()
            if issue is None:
                raise ValueError('Unknown notebook issue')
            if issue['status'] == 'resolved':
                return json.loads(issue['disposition_evidence_json'])
            external = None
            if issue['set_id'] is None:
                saved = json.loads(issue['broker_evidence_json'])
                if issue['code'] == 'unexpected_trade' and saved.get('trade_id'):
                    external = broker.trade(broker_id(saved['trade_id']))
                elif issue['code'] == 'unexpected_order' and saved.get('order_id'):
                    external = broker.order(broker_id(saved['order_id']))
                else:
                    raise DispositionRequired('Issue has no supported matching broker identity')

            result = {}

            def commit_disposition(identifier, snapshot):
                if external is None:
                    proof = _registered_evidence(db, issue, snapshot)
                else:
                    trade = external.body.get('trade')
                    order = external.body.get('order')
                    if trade is not None:
                        ids = trade.get('closingTransactionIDs', [])
                        if (trade.get('state') != 'CLOSED' or trade['id'] in snapshot.trades or not ids
                                or trade.get('instrument', '').replace('_', '-') != issue['pair']):
                            raise DispositionRequired('Unexpected trade has no confirmed closure')
                        for tid in ids:
                            if not db.execute("SELECT 1 FROM fills WHERE transaction_id = ? AND broker_trade_id = ? AND effect = 'close'",
                                              (broker_id(tid), trade['id'])).fetchone():
                                raise DispositionRequired('Closing transaction is not reconciled')
                        proof = {'trade_ids': [trade['id']], 'transaction_ids': ids, 'read': external.evidence()}
                    else:
                        cancelled = order.get('state') == 'CANCELLED'
                        tid = order.get('cancellingTransactionID' if cancelled else 'fillingTransactionID')
                        if order.get('state') not in ('CANCELLED', 'FILLED') or order['id'] in snapshot.orders or not tid:
                            raise DispositionRequired('Unexpected order has no confirmed terminal outcome')
                        record = db.execute('SELECT body_json FROM broker_transactions WHERE transaction_id = ?', (broker_id(tid),)).fetchone()
                        kind = 'ORDER_CANCEL' if cancelled else 'ORDER_FILL'
                        if not record or json.loads(record[0]).get('orderID') != order['id'] or json.loads(record[0]).get('type') != kind:
                            raise DispositionRequired('Terminal transaction is not reconciled')
                        if not cancelled and any(r[0] in snapshot.trades for r in db.execute(
                            "SELECT broker_trade_id FROM fills WHERE transaction_id = ? AND effect = 'open'", (tid,)
                        )):
                            raise DispositionRequired('Unexpected order still has an open trade')
                        proof = {'order_ids': [order['id']], 'transaction_ids': [tid], 'read': external.evidence()}
                result.update(snapshot_id=identifier, boundary=snapshot.boundary, source=broker.evidence_source, **proof)
                db.execute('''UPDATE issues SET status = 'resolved', operator_disposition = ?, operator_id = ?,
                              resolved_at = ?, disposition_evidence_json = ? WHERE issue_id = ? AND status = 'open' ''',
                           (redact(explanation, broker.private_values), redact(operator_id, broker.private_values), broker.now(),
                            encode_evidence(result, broker.private_values), issue_id))

            reconcile_snapshot(db, broker, purpose='disposition', on_reconciled=commit_disposition)
            return result
