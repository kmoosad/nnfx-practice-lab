"""Collect account-scoped, read-only M04 evidence outside the notebook."""

import argparse
from datetime import datetime, time
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .broker import PRACTICE_HOST, BrokerError, PracticeBroker, broker_id, instrument, money
from .candles import capture_daily_candles
from .config import Binding, ConfigurationError, PERMITTED_PAIRS, load_account_binding, load_binding
from .evidence import canonical_json, redact


_NEW_YORK = ZoneInfo("America/New_York")


def _report(broker, phase, started_at):
    experiment, connection = broker.binding.experiment, broker.binding.connection
    account_identity = [experiment.controller_id, experiment.notebook_id,
                        connection.account_id, connection.home_currency]
    return {
        "source": broker.evidence_source,
        "host": PRACTICE_HOST,
        "phase": phase,
        "started_at": started_at,
        "controller_id": experiment.controller_id,
        "notebook_id": experiment.notebook_id,
        "account_binding_sha256": sha256(canonical_json(account_identity).encode()).hexdigest(),
        "home_currency": connection.home_currency,
    }


def _result(reason=None, *, validation=None, **fields):
    return {"validation": validation or ("unavailable" if reason else "valid"),
            "reason": reason, **fields}


def _read_evidence(request):
    try:
        read = request()
    except BrokerError as failure:
        return None, _result(str(failure), evidence=failure.evidence)
    return read, _result(evidence=read.evidence())


def _account_state(account):
    for name, count_key in (("trades", "openTradeCount"), ("orders", "pendingOrderCount")):
        rows, count = account.get(name), account.get(count_key)
        if not isinstance(rows, list) or type(count) is not int or count != len(rows):
            raise BrokerError(f"Account {name} do not match the reported count")
        try:
            ids = {broker_id(row.get("id")) for row in rows if isinstance(row, dict)}
        except BrokerError:
            ids = set()
        if len(ids) != count:
            raise BrokerError(f"Account {name} have missing or duplicate IDs")
    money(account.get("marginAvailable"))
    if "marginRate" in account and not 0 < money(account["marginRate"]) <= 1:
        raise BrokerError("Account margin rate override is outside the valid range")


def _one_row(body, array, key, value):
    rows = body.get(array)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise BrokerError(f"Missing or malformed {array} array")
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise BrokerError(f"Expected one {array} entry for {value}")
    return matches[0]


def _instrument_check(body, pair):
    try:
        row = _one_row(body, "instruments", "name", instrument(pair))
        if row.get("type") != "CURRENCY":
            raise BrokerError("Instrument metadata is not for a currency pair")
        for field in ("displayPrecision", "tradeUnitsPrecision", "pipLocation"):
            if type(row.get(field)) is not int or (field != "pipLocation" and row[field] < 0):
                raise BrokerError(f"Invalid {field}")
        minimum = money(row.get("minimumTradeSize"))
        order_max = money(row.get("maximumOrderUnits"))
        position_max = money(row.get("maximumPositionSize"))
        if not (0 < minimum <= order_max and (position_max == 0 or position_max >= minimum)):
            raise BrokerError("Invalid instrument size limits")
        if not 0 < money(row.get("marginRate")) <= 1:
            raise BrokerError("Instrument margin rate is outside the valid range")
    except BrokerError as failure:
        return _result(str(failure))
    return _result()


def _tradeable_price(body, pair):
    try:
        row = _one_row(body, "prices", "instrument", instrument(pair))
        tradeable = row.get("tradeable", row.get("status") == "tradeable")
        if tradeable is not True:
            raise BrokerError("Broker price is unavailable or untradeable")
        timestamp = row.get("time")
        if not isinstance(timestamp, str) or datetime.fromisoformat(timestamp).utcoffset() is None:
            raise BrokerError("Missing or invalid broker price time")
        for side in ("bids", "asks"):
            buckets = row.get(side)
            if not isinstance(buckets, list) or not buckets:
                raise BrokerError(f"No {side} available for entry")
            if any(not isinstance(bucket, dict) or money(bucket.get("price")) <= 0 for bucket in buckets):
                raise BrokerError(f"Invalid {side} in broker price")
    except ValueError as failure:
        reason = str(failure) if isinstance(failure, BrokerError) else "Invalid broker price time"
        return _result(reason)
    return _result(price_time=timestamp)


def _loss_factor(body, currency, *, identity=False):
    factor = None
    try:
        conversion = _one_row(body, "homeConversions", "currency", currency)
        raw = conversion.get("accountLoss")
        try:
            value = money(raw)
        except BrokerError:
            raise BrokerError("Missing or invalid accountLoss") from None
        factor = raw
        if value <= 0:
            raise BrokerError("accountLoss must be positive")
        if identity and value != 1:
            raise BrokerError("Home-currency accountLoss must equal 1")
    except BrokerError as failure:
        return _result(str(failure), currency=currency, accountLoss=factor)
    return _result(currency=currency, accountLoss=factor)


def _pricing_checks(body, home):
    quotes = {pair: pair.split("-")[1] for pair in PERMITTED_PAIRS}
    matching = [pair for pair, quote in quotes.items() if quote == home]
    containing = [pair for pair in PERMITTED_PAIRS if home in pair.split("-")]
    pairs = {
        pair: {"tradeability": _tradeable_price(body, pair), "quote_loss": _loss_factor(body, quote)}
        for pair, quote in quotes.items()
    }
    identity = (_loss_factor(body, home, identity=True) if containing else
                _result("The home currency is absent from the permitted pairs",
                        validation="not_applicable", currency=home))
    matching_quote = (identity if matching else
                      _result("No permitted pair quotes in the home currency",
                              validation="not_applicable", currency=home))
    return {"pairs": pairs, "matching_quote": {**matching_quote, "pairs": matching},
            "home_identity": {**identity, "pairs": containing}}


def check_account(broker, *, division=None, profile_reference=None, platform=None):
    """Collect account and pricing evidence, even while strategy qualification is pending."""
    report = _report(broker, "account", broker.now())
    report["status"] = "incomplete"
    account, report["account"] = _read_evidence(broker.account)
    if account is None:
        return redact(report, broker.private_values)

    state = account.body["account"]
    try:
        _account_state(state)
    except BrokerError as failure:
        report["account"].update(_result(str(failure)))

    # The account details endpoint does not identify the OANDA division or MT4
    # association. Keep the account profile reference distinct from GET evidence.
    profile_known = bool(division and division.strip() and profile_reference and profile_reference.strip())
    report["division"] = _result(
        None if profile_known else "Account division and its account-profile evidence reference are required",
        name=division, reference=profile_reference,
    )
    report["execution_review"] = {
        "platform": platform or "unconfirmed",
        "client_extensions": ("Avoid on MT4-associated accounts" if platform == "mt4-associated" else
                              "Confirm account association and client-extension support for execution"),
        "protected_trade_sizes": (
            "OANDA Corporation documents unique sizes for protected trades, including practice accounts"
            if profile_known and division.strip().casefold() == "oanda corporation" else
            "Confirm any protected-trade size and FIFO restrictions for this account"
        ),
        "hedging_enabled": state.get("hedgingEnabled"),
        "guaranteed_stop_mode": state.get("guaranteedStopLossOrderMode"),
        "existing_activity": bool(state.get("trades") or state.get("orders")),
    }

    instruments, report["instruments"] = _read_evidence(lambda: broker.instruments(PERMITTED_PAIRS))
    if instruments is not None:
        checks = {pair: _instrument_check(instruments.body, pair) for pair in PERMITTED_PAIRS}
        report["instruments"]["pairs"] = checks
        if any(check["validation"] != "valid" for check in checks.values()):
            report["instruments"].update(_result("Instrument metadata coverage is incomplete"))

    pricing, report["pricing"] = _read_evidence(lambda: broker.pricing_for(PERMITTED_PAIRS))
    if pricing is not None:
        checks = _pricing_checks(pricing.body, report["home_currency"])
        report["pricing"].update(checks)
        if (checks["home_identity"]["validation"] == "unavailable" or
                any(check["validation"] != "valid"
                    for pair_checks in checks["pairs"].values() for check in pair_checks.values())):
            report["pricing"].update(_result("Pricing or required conversion coverage is incomplete"))

    if all(report[key]["validation"] == "valid" for key in ("account", "division", "instruments", "pricing")):
        report["status"] = "passed"
    return redact(report, broker.private_values)


def check_candles(broker):
    """Check one 16:50 launch using the separately qualified strategy binding."""
    started = broker.now()
    report = _report(broker, "candles", started)
    report["status"] = "incomplete"
    binding = broker.binding
    if not isinstance(binding, Binding):
        return redact({**report, "reason": "Candle coverage requires the qualified M03 manifest"},
                      broker.private_values)
    count = binding.manifest.lookback_candles
    report.update(manifest_sha256=binding.manifest.hash, lookback_candles=count)
    if count != binding.connection.lookback_candles or not 15 <= count <= 5000:
        return redact({**report, "reason": "Qualified count must match the binding and fit the OANDA candle request"},
                      broker.private_values)

    local = datetime.fromisoformat(started).astimezone(_NEW_YORK)
    session_date = local.date()
    report["session_date"] = session_date.isoformat()
    if local.weekday() >= 5 or (local.hour, local.minute) != (16, 50):
        return redact({**report, "reason": "Candle coverage requires a weekday 16:50 New York launch"},
                      broker.private_values)

    account, report["account"] = _read_evidence(broker.account)
    if account is None:
        return redact(report, broker.private_values)

    end = datetime.combine(session_date, time(17), _NEW_YORK)
    pairs = {}
    for pair in PERMITTED_PAIRS:
        if datetime.fromisoformat(broker.now()) >= end:
            pairs[pair] = _result("Rollover reached before request", requested_at=None, responded_at=None)
        else:
            pairs[pair] = capture_daily_candles(broker, pair, session_date=session_date).metadata
    report["pairs"] = pairs
    report["valid_windows"] = sum(pair["validation"] == "valid" for pair in pairs.values())
    if report["valid_windows"] == len(PERMITTED_PAIRS):
        report["status"] = "passed"
    return redact(report, broker.private_values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("controller")
    parser.add_argument("--candles", action="store_true", help="run the qualified weekday 16:50 candle pass")
    parser.add_argument("--division", help="OANDA division from the intended account profile")
    parser.add_argument("--profile-reference", help="non-secret reference to the reviewed account profile")
    parser.add_argument("--platform", choices=("native-v20", "mt4-associated"))
    args = parser.parse_args(argv)
    try:
        load = load_binding if args.candles else load_account_binding
        binding = load(Path.cwd(), args.controller)
    except ConfigurationError as failure:
        parser.exit(2, f"{failure}\n")
    with PracticeBroker(binding) as broker:
        report = (check_candles(broker) if args.candles else
                  check_account(broker, division=args.division, profile_reference=args.profile_reference,
                                platform=args.platform))
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
