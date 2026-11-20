"""Redact structured request evidence before recording or reporting it."""

import json
import re


_SECRET_KEYS = {
    "authorization", "proxyauthorization", "headers", "requestheaders",
    "responseheaders", "cookie", "setcookie", "credentials", "password",
    "secret", "token", "apikey", "accesskey", "accountid",
}
_BEARER = re.compile(r"\bBearer\s+\S+", re.IGNORECASE)


def redact(value, private_values=()):
    if isinstance(value, str):
        value = _BEARER.sub("Bearer [redacted]", value)
        for private_value in private_values:
            value = value.replace(private_value, "[redacted]")
        return value
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if any(normalized.endswith(field) for field in _SECRET_KEYS):
                continue
            clean[redact(key, private_values)] = redact(item, private_values)
        return clean
    if isinstance(value, (list, tuple)):
        return [redact(item, private_values) for item in value]
    return value


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def encode_evidence(value, private_values):
    try:
        encoded = canonical_json(redact(value, private_values))
    except (TypeError, ValueError, AttributeError, RecursionError):
        raise ValueError("Evidence must be JSON data") from None
    if len(encoded) > 65536:
        raise ValueError("Evidence exceeds 64 KiB")
    return encoded
