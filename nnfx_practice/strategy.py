"""Explicit, immutable strategy selection for independent practice experiments."""

from hashlib import sha256
import json
from pathlib import Path

from strategies import drm_adaptive_bandpass_v1, eye_age_supertrend_v1, t3_bandpass_v1

from .config import ConfigurationError
from .evidence import canonical_json


STRATEGIES = {
    "t3_bandpass_v1": t3_bandpass_v1,
    "drm_adaptive_bandpass_v1": drm_adaptive_bandpass_v1,
    "eye_age_supertrend_v1": eye_age_supertrend_v1,
}


def manifest_for_hash(digest):
    for strategy in STRATEGIES.values():
        manifest = json.loads(Path(strategy.__file__).with_name("manifest.json").read_bytes())
        if sha256(canonical_json(manifest).encode()).hexdigest() == digest:
            return manifest
    raise ConfigurationError("Strategy manifest does not match a qualified packaged version")


def select_strategy(binding):
    strategy = STRATEGIES.get(binding.experiment.strategy_version)
    if strategy is None:
        raise ConfigurationError("Unknown qualified strategy version")
    packaged = json.loads(Path(strategy.__file__).with_name("manifest.json").read_bytes())
    if (binding.manifest.body != canonical_json(packaged)
            or binding.manifest.hash != sha256(binding.manifest.body.encode()).hexdigest()
            or binding.manifest.lookback_candles != strategy.LOOKBACK_CANDLES
            or binding.connection.lookback_candles != strategy.LOOKBACK_CANDLES):
        raise ConfigurationError("Strategy requires its exact qualified manifest and candle count")
    return strategy
