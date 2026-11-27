"""Capture and validate one daily mid-price window for a New York session."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
import json
import re
from zoneinfo import ZoneInfo

from .broker import BrokerError, instrument, money
from .config import ConfigurationError
from .evidence import encode_evidence
from .notebook import _check_binding, transaction


_NEW_YORK = ZoneInfo("America/New_York")
_DAILY_ALIGNMENT = time(17)
_CANDLE_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:00:00(?:\.0{1,9})?Z")


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int | None


@dataclass(frozen=True)
class CandleCapture:
    candles: tuple[Candle, ...] | None
    metadata: dict


def _candle_start(row, *, historical_weekend=False):
    value = row.get("time") if isinstance(row, dict) else None
    if isinstance(value, str) and _CANDLE_TIME.fullmatch(value):
        try:
            start = datetime.fromisoformat(value)
            local = start.astimezone(_NEW_YORK)
        except (OverflowError, ValueError):
            pass
        else:
            # The Sunday opening bar is Monday's session. Friday and Saturday
            # evenings do not start FX daily sessions.
            if local.time() == _DAILY_ALIGNMENT and (historical_weekend or local.weekday() not in (4, 5)):
                return start
    raise ValueError("Invalid daily candle start")


def _candle(row, *, complete, historical_weekend=False):
    start = _candle_start(row, historical_weekend=historical_weekend)
    if row.get("complete") is not complete:
        raise ValueError("Expected completed history and a final partial candle")
    mid = row.get("mid")
    if not isinstance(mid, dict):
        raise ValueError("Missing mid-price candle")
    opening, high, low, close = (money(mid.get(key)) for key in ("o", "h", "l", "c"))
    if not 0 < low <= min(opening, close) <= max(opening, close) <= high:
        raise ValueError("Invalid mid-price candle range")
    volume = row.get("volume")
    if "volume" in row and (type(volume) is not int or volume < 0):
        raise ValueError("Invalid candle volume")
    return Candle(start, float(opening), float(high), float(low), float(close), volume)


def anchored_history(candles, origin):
    """Use the lab's weekday series from its immutable first candle."""
    starts = [i for i, candle in enumerate(candles) if candle.timestamp == origin]
    if len(starts) != 1:
        raise ValueError("Required indicator history start candle is unavailable")
    history = tuple(c for c in candles[starts[0]:] if c.timestamp.astimezone(_NEW_YORK).weekday() not in (4, 5))
    if len(history) < 15 or history[0].timestamp != origin:
        raise ValueError("Required indicator history start candle is unavailable")
    return history


def capture_daily_candles(broker, pair, *, session_date: date) -> CandleCapture:
    """Read the bound count once, returning metadata even for unavailable data."""
    count = broker.binding.manifest.lookback_candles
    if count != broker.binding.connection.lookback_candles:
        raise ConfigurationError("Configured lookback differs from the qualified count")
    name = instrument(pair)
    metadata = {
        "session_date": session_date.isoformat(),
        "requested_at": None, "responded_at": None,
        "http_status": None, "request_id": None,
        "received_count": None, "signal_candle_start": None,
        "validation": "unavailable", "reason": None,
    }
    if session_date.weekday() >= 5:
        metadata["reason"] = "Run date has no weekday FX session"
        return CandleCapture(None, metadata)
    start = datetime.combine(session_date - timedelta(days=1), _DAILY_ALIGNMENT, _NEW_YORK).astimezone(UTC)
    end = datetime.combine(session_date, _DAILY_ALIGNMENT, _NEW_YORK).astimezone(UTC)
    try:
        read = broker.candles(pair)
    except BrokerError as failure:
        evidence = failure.evidence or {}
        for key in ("requested_at", "responded_at", "http_status", "request_id"):
            metadata[key] = evidence.get(key)
        metadata["reason"] = str(failure)
        return CandleCapture(None, metadata)

    metadata.update(requested_at=read.requested_at, responded_at=read.responded_at,
                    http_status=read.status, request_id=read.request_id)
    rows = read.body.get("candles")
    if isinstance(rows, list):
        metadata["received_count"] = len(rows)
        if rows:
            try:
                _candle_start(rows[-1])
            except ValueError:
                pass
            else:
                metadata["signal_candle_start"] = rows[-1]["time"]

    try:
        if read.body.get("instrument") != name or read.body.get("granularity") != "D":
            raise ValueError("Broker candle instrument or granularity differs from the request")
        if not isinstance(rows, list):
            raise ValueError("Broker candle array is missing or malformed")
        if len(rows) != count:
            raise ValueError("Received candle count differs from the qualified count")
        requested = datetime.fromisoformat(read.requested_at)
        responded = datetime.fromisoformat(read.responded_at)
        if not start <= requested <= responded < end:
            raise ValueError("Capture time falls outside the intended session")
        history = json.loads(broker.binding.manifest.body).get("history_initialization")
        candles = tuple(_candle(row, complete=index < count - 1,
                               historical_weekend=history is not None and index < count - 1)
                        for index, row in enumerate(rows))
        if candles[-1].timestamp != start:
            raise ValueError("Final candle belongs to a different session")
        if any(prior.timestamp >= current.timestamp for prior, current in zip(candles, candles[1:])):
            raise ValueError("Daily candles are duplicated or out of order")
        if history is not None:
            if (not isinstance(history, dict) or set(history) != {"mode", "start", "calendar"}
                    or history["mode"] != "anchored" or not isinstance(history["start"], str)
                    or history["calendar"] != "new_york_weekdays"):
                raise ValueError("Unsupported indicator history initialization")
            origin = datetime.fromisoformat(history["start"])
            metadata["indicator_history_start"] = history["start"]
            metadata["indicator_candle_count"] = len(anchored_history(candles, origin))
            metadata["excluded_non_session_candles"] = sum(
                c.timestamp.astimezone(_NEW_YORK).weekday() in (4, 5) for c in candles)
    except ValueError as failure:
        metadata["reason"] = str(failure)
        return CandleCapture(None, metadata)

    metadata["validation"] = "valid"
    return CandleCapture(candles, metadata)


def capture_pair_candles(db, broker, *, run_id, stage, pair) -> CandleCapture:
    """Use the recorded run session and save capture evidence before calculation."""
    if db.in_transaction:
        raise ValueError("Capture requires an open notebook outside a write transaction")
    binding = broker.binding
    _check_binding(db, binding)
    decision = db.execute("""
        SELECT session_date, runs.lookback_candles, runs.strategy_hash
        FROM pair_decisions JOIN runs USING (run_id)
        WHERE run_id = ? AND stage = ? AND pair = ? AND runs.status = 'running'
              AND outcome IS NULL AND capture_json IS NULL
    """, (run_id, stage, pair)).fetchone()
    if decision is None:
        raise ValueError("Expected one unfinished pair decision without a candle capture")
    if (decision["lookback_candles"] != binding.manifest.lookback_candles
            or decision["strategy_hash"] != binding.manifest.hash):
        raise ConfigurationError("Run candle count or strategy differs from the binding")

    capture = capture_daily_candles(broker, pair, session_date=date.fromisoformat(decision["session_date"]))
    evidence = encode_evidence(capture.metadata, broker.private_values)
    with transaction(db):
        updated = db.execute("""
            UPDATE pair_decisions SET capture_json = ?
            WHERE run_id = ? AND stage = ? AND pair = ? AND outcome IS NULL AND capture_json IS NULL
        """, (evidence, run_id, stage, pair))
        if updated.rowcount != 1:
            raise ValueError("Pair decision changed during candle capture")
    return capture
