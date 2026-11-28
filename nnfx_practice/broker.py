"""Account-scoped OANDA practice reads and their redacted evidence."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from http.client import HTTPException, HTTPSConnection
import json
from math import isfinite
import re
from urllib.parse import urlencode

from .config import Binding, ConfigurationError
from .evidence import redact
from .notebook import utc_text


PRACTICE_HOST = "api-fxpractice.oanda.com"
_RANGE_SIZE = 1000
_MAX_RESPONSE = 16 * 1024 * 1024
_ID = re.compile(r"[0-9]{1,32}")
_DECIMAL = re.compile(r"[+-]?[0-9]+(?:\.[0-9]+)?")


class BrokerError(ValueError):
    """Read failure with a safe message and optional redacted response evidence."""

    def __init__(self, message, *, evidence=None, status=None):
        super().__init__(message)
        self.evidence = evidence
        self.status = status


def broker_id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise BrokerError("Invalid or missing broker ID")
    return str(int(value))


def money(value):
    if not isinstance(value, str) or len(value) > 38 or not _DECIMAL.fullmatch(value):
        raise BrokerError("Invalid or missing broker decimal")
    try:
        return Decimal(value)
    except InvalidOperation:
        raise BrokerError("Invalid broker decimal") from None


def instrument(pair):
    if not isinstance(pair, str) or not re.fullmatch(r"[A-Z]{3}-[A-Z]{3}", pair):
        raise ValueError("Expected an instrument in base-quote format")
    return pair.replace("-", "_")


def _json_float(text):
    value = float(text)
    return value if isfinite(value) else text


@dataclass(frozen=True)
class HTTPReply:
    status: int
    body: object = field(repr=False)
    request_id: str | None = None


class _PracticeTransport:
    def __init__(self, connection, connect_timeout, read_timeout, *, mutation_guard=None):
        self._token = connection.token
        self._account_path = f"/v3/accounts/{connection.account_id}"
        self._connection = HTTPSConnection(PRACTICE_HOST, timeout=connect_timeout)
        self._read_timeout = read_timeout
        self._mutation_guard = mutation_guard

    def close(self):
        self._connection.close()

    def request(self, method, path, payload=None):
        if path != self._account_path and not path.startswith(self._account_path + "/"):
            raise ValueError("Expected a read-only account request")
        body = None
        headers = {"Authorization": f"Bearer {self._token}"}
        if method == 'GET' and payload is None:
            pass
        elif self._mutation_guard is not None:
            self._mutation_guard(method, path.removeprefix(self._account_path), payload)
            body = json.dumps(payload, allow_nan=False).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        else:
            raise ValueError("Expected a read-only account request")
        conn = self._connection
        try:
            if conn.sock is None:
                conn.connect()
            conn.sock.settimeout(self._read_timeout)
            if body is None:
                conn.request(method, path, headers=headers)
            else:
                conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            raw = response.read(_MAX_RESPONSE + 1)
            if len(raw) > _MAX_RESPONSE:
                self.close()
                raise BrokerError("Broker response exceeds the read limit")
            try:
                # Keep malformed non-finite values reportable without emitting
                # them as JSON numbers or accepting them as broker decimals.
                body = json.loads(raw, parse_float=_json_float, parse_constant=str) if raw else None
            except (UnicodeError, ValueError, RecursionError):
                body = None
            return HTTPReply(response.status, body, response.getheader("RequestID"))
        except (HTTPException, OSError):
            self.close()
            raise BrokerError("Broker connection or read failed") from None


@dataclass(frozen=True)
class Read:
    requested_at: str
    responded_at: str
    status: int | None
    request_id: str | None
    path: str
    body: dict = field(repr=False)
    _private: tuple = field(repr=False)
    method: str = "GET"

    def evidence(self, body=None):
        body = self.body if body is None else body
        account = body.get("account")
        private = self._private
        if isinstance(account, dict):
            observed_id = account.get("id")
            if isinstance(observed_id, str) and observed_id:
                private = (*private, observed_id)
            body = {**body, "account": {key: value for key, value in account.items() if key != "id"}}
        return redact({
            "method": self.method, "path": self.path, "requested_at": self.requested_at,
            "responded_at": self.responded_at, "http_status": self.status,
            "request_id": self.request_id, "body": body,
        }, private)

    @property
    def boundary(self):
        return broker_id(self.body.get("lastTransactionID"))


class PracticeBroker:
    """Account reads by default; native practice mutations need a verified permit."""

    def __init__(self, binding, *, transport=None, now=None, connect_timeout=5, read_timeout=15,
                 qualification=None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", binding.connection.account_id):
            raise ValueError("Invalid broker account binding")
        if not all(isfinite(timeout) and timeout > 0 for timeout in (connect_timeout, read_timeout)):
            raise ValueError("Broker timeouts must be positive and finite")
        self._binding = binding
        self._qualification = qualification
        if qualification is not None:
            from .qualification import QualificationPermit
            if type(qualification) is not QualificationPermit or transport is not None:
                raise ConfigurationError('Expected a verified qualification permit and native practice transport')
            qualification.check(binding)
        self._now = now if now is not None else lambda: datetime.now(UTC)
        self._owns_transport = transport is None
        self._transport = (
            _PracticeTransport(binding.connection, connect_timeout, read_timeout,
                               mutation_guard=qualification.guard if qualification is not None else None)
            if transport is None else transport
        )

    @property
    def binding(self):
        return self._binding

    @property
    def evidence_source(self):
        if self._qualification is not None:
            return 'practice_execution' if self._qualification.operation == 'run' else 'practice_get'
        return "practice_get" if self._owns_transport else "fixture"

    @property
    def private_values(self):
        return self.binding.connection.token, self.binding.connection.account_id

    def now(self):
        return utc_text(self._now())

    def close(self):
        if self._owns_transport:
            self._transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _get(self, path="", **query):
        relative = path + ("?" + urlencode(query) if query else "")
        target = f"/v3/accounts/{self.binding.connection.account_id}{relative}"
        started = self.now()
        try:
            reply = self._transport.request("GET", target)
        except (BrokerError, HTTPException, OSError):
            failed = Read(started, self.now(), None, None,
                          relative or "/", {}, self.private_values)
            raise BrokerError("Broker connection or read failed", evidence=failed.evidence()) from None
        body = reply.body if isinstance(reply.body, dict) else {}
        request_id = redact(reply.request_id, self.private_values)
        read = Read(started, self.now(), reply.status, request_id,
                    relative or "/", body, self.private_values)
        if not 200 <= reply.status < 300:
            raise BrokerError(f"Broker GET returned HTTP {reply.status}",
                              evidence=read.evidence(), status=reply.status)
        if not isinstance(reply.body, dict):
            raise BrokerError("Broker response is not a JSON object", evidence=read.evidence())
        return read

    def _account(self, path=""):
        read = self._get(path)
        account = read.body.get("account")
        connection = self.binding.connection
        if (not isinstance(account, dict) or account.get("id") != connection.account_id
                or account.get("currency") != connection.home_currency):
            raise BrokerError("Broker account identity or currency differs from the binding",
                              evidence=read.evidence())
        try:
            boundary = read.boundary
            if "lastTransactionID" in account and broker_id(account["lastTransactionID"]) != boundary:
                raise BrokerError("Broker account transaction boundaries disagree")
            money(account.get("balance"))
        except BrokerError as failure:
            raise BrokerError(str(failure), evidence=read.evidence()) from None
        return read

    def account(self):
        return self._account()

    def summary(self):
        return self._account("/summary")

    def instruments(self, pairs=()):
        names = ",".join(map(instrument, pairs))
        return self._get("/instruments", **({"instruments": names} if names else {}))

    def pricing(self, pair):
        return self.pricing_for((pair,))

    def pricing_for(self, pairs):
        names = ",".join(map(instrument, pairs))
        return self._get("/pricing", instruments=names, includeHomeConversions="true")

    def candles(self, pair):
        if not isinstance(self.binding, Binding):
            raise ConfigurationError("Candle requests require the qualified strategy binding")
        return self._get(f"/instruments/{instrument(pair)}/candles", price="M", granularity="D",
                         count=self.binding.connection.lookback_candles, smooth="false",
                         dailyAlignment=17, alignmentTimezone="America/New_York")

    def require_scripted_execution(self):
        if self._owns_transport:
            raise ValueError("Live trade mutations are not enabled; use a scripted transport")

    def require_qualification_execution(self):
        if self._qualification is not None:
            self._qualification.check(self.binding)
        else:
            self.require_scripted_execution()

    def require_controller_execution(self):
        self.require_qualification_execution()

    def change_trade(self, trade_id, *, stop_price=None):
        """Send once. The caller commits intent and interprets broker evidence."""
        self.require_controller_execution()
        trade_id = broker_id(trade_id)
        if stop_price is not None and money(stop_price) <= 0:
            raise ValueError("Expected a positive stop price")
        path = f"/trades/{trade_id}/" + ("close" if stop_price is None else "orders")
        payload = ({"units": "ALL"} if stop_price is None else
                   {"stopLoss": {"price": stop_price, "timeInForce": "GTC"}})
        return self._mutate("PUT", path, payload)

    def enter_trade(self, pair, *, units, distance, client_id):
        """Native-v20 candidate; account capability remains subject to qualification."""
        if money(units) == 0 or money(distance) <= 0 or not re.fullmatch(r"[A-Za-z0-9_-]+", client_id):
            raise ValueError("Invalid candidate entry request")
        return self._mutate("POST", "/orders", {"order": {
            "type": "MARKET", "instrument": instrument(pair), "units": units,
            "timeInForce": "FOK", "positionFill": "OPEN_ONLY",
            "clientExtensions": {"id": client_id}, "tradeClientExtensions": {"id": client_id},
            "stopLossOnFill": {"distance": distance, "timeInForce": "GTC"},
        }})

    def set_target(self, trade_id, price):
        if money(price) <= 0:
            raise ValueError("Invalid target price")
        return self._mutate("PUT", f"/trades/{broker_id(trade_id)}/orders",
                            {"takeProfit": {"price": price, "timeInForce": "GTC"}})

    def _mutate(self, method, path, payload):
        self.require_controller_execution()
        started = self.now()
        try:
            reply = self._transport.request(
                method, f"/v3/accounts/{self.binding.connection.account_id}{path}", payload)
        except (BrokerError, HTTPException, OSError):
            return Read(started, self.now(), None, None, path, {}, self.private_values, method)
        body = reply.body if isinstance(reply.body, dict) else {}
        return Read(started, self.now(), reply.status, redact(reply.request_id, self.private_values),
                    path, body, self.private_values, method)

    def trade(self, trade_id):
        return self._identified("trades", "trade", trade_id)

    def order(self, order_id):
        return self._identified("orders", "order", order_id)

    def transaction(self, transaction_id):
        return self._identified("transactions", "transaction", transaction_id)

    def _identified(self, endpoint, key, identifier):
        identifier = broker_id(identifier)
        read = self._get(f"/{endpoint}/{identifier}")
        obj = read.body.get(key)
        if not isinstance(obj, dict) or broker_id(obj.get("id")) != identifier:
            raise BrokerError("Broker returned a different object ID", evidence=read.evidence())
        if key == "transaction":
            self.verify_transaction(obj)
        return read

    def verify_transaction(self, body):
        if not isinstance(body, dict) or body.get("accountID") != self.binding.connection.account_id:
            raise BrokerError("Broker transaction account differs from the binding")
        if not isinstance(body.get("type"), str) or not body["type"]:
            raise BrokerError("Broker transaction type is missing")

    def history(self, cursor, boundary, *, deferred=None):
        """Yield unfiltered, account-validated transactions inside the requested interval."""
        start, end = int(broker_id(cursor)), int(broker_id(boundary))
        if start > end:
            raise BrokerError("Broker snapshot predates imported history")
        if start == end:
            return
        ranges = end - start > _RANGE_SIZE
        for first in range(start + 1, end + 1, _RANGE_SIZE):
            last = min(first + _RANGE_SIZE - 1, end)
            read = (self._get("/transactions/idrange", **{"from": first, "to": last})
                    if ranges else self._get("/transactions/sinceid", id=start))
            records = read.body.get("transactions")
            watermark = int(read.boundary)
            if watermark < last:
                raise BrokerError("Broker history response is behind the requested interval",
                                  evidence=read.evidence({}))
            if not isinstance(records, list) or read.body.get("pages"):
                raise BrokerError("Broker history response is incomplete", evidence=read.evidence({}))
            for body in records:
                self.verify_transaction(body)
                number = int(broker_id(body.get("id")))
                if number > watermark or number < first or (ranges and number > last):
                    raise BrokerError("Transaction falls outside its broker history page")
                if number <= end:
                    yield body
                elif deferred is not None:
                    deferred.add(str(number))
