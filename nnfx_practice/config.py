"""Load the experiment registry without passing private settings to readers."""

from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tomllib

from .evidence import canonical_json, redact


PERMITTED_PAIRS = (
    "EUR-USD", "GBP-USD", "AUD-USD", "NZD-USD", "USD-CHF", "USD-JPY", "USD-CAD",
    "EUR-CHF", "GBP-CHF", "AUD-CHF", "NZD-CHF", "CAD-CHF", "EUR-GBP", "GBP-JPY",
    "GBP-AUD", "GBP-CAD", "GBP-NZD", "EUR-JPY", "CAD-JPY", "AUD-JPY", "CHF-JPY",
    "NZD-JPY", "EUR-AUD", "EUR-NZD", "AUD-NZD", "EUR-CAD", "AUD-CAD", "NZD-CAD",
)


_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_PREFIX = re.compile(r"[A-Z][A-Z0-9_]*")
_ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
_COMMIT = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")
_SHA256 = re.compile(r"[a-f0-9]{64}")


class ConfigurationError(ValueError):
    """A configuration error suitable for service logs."""


@dataclass(frozen=True)
class Experiment:
    controller_id: str
    notebook_id: str
    notebook_name: str
    strategy_version: str
    connection_key: str

    def notebook_path(self, root: Path) -> Path:
        if not _SLUG.fullmatch(self.notebook_id):
            raise ConfigurationError("Invalid notebook ID")
        data = root.resolve() / "var"
        directory = data / "notebooks"
        path = directory / f"{self.notebook_id}.sqlite3"
        sidecars = [path.with_name(path.name + suffix) for suffix in ("-wal", "-shm", "-journal")]
        for part in (data, directory, path, *sidecars):
            if part.is_symlink():
                raise ConfigurationError("Notebook path must not contain symbolic links")
        if path.exists() and (not path.is_file() or path.stat().st_nlink != 1):
            raise ConfigurationError("Notebook path must identify one regular file")
        return path


@dataclass(frozen=True, repr=False)
class AccountConnection:
    account_id: str
    token: str
    home_currency: str


@dataclass(frozen=True, repr=False)
class PrivateConnection(AccountConnection):
    lookback_candles: int


@dataclass(frozen=True)
class StrategyManifest:
    body: str = field(repr=False)
    hash: str
    lookback_candles: int


@dataclass(frozen=True)
class AccountBinding:
    experiment: Experiment
    connection: AccountConnection = field(repr=False)


@dataclass(frozen=True)
class Binding(AccountBinding):
    connection: PrivateConnection = field(repr=False)
    manifest: StrategyManifest


def read_registry(root: Path) -> dict[str, Experiment]:
    """Read the public registry, suitable for use by an observational reader."""
    try:
        document = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))
        rows = document["experiments"]
        if set(document) != {"experiments"} or not isinstance(rows, list) or not rows:
            raise ValueError
        experiments = [Experiment(**row) for row in rows]
    except (OSError, KeyError, TypeError, ValueError):
        raise ConfigurationError("Invalid config.toml experiment registry") from None

    by_controller = {}
    notebooks = set()
    for experiment in experiments:
        for value, pattern in (
            (experiment.controller_id, _SLUG), (experiment.notebook_id, _SLUG),
            (experiment.strategy_version, _SLUG), (experiment.connection_key, _PREFIX),
        ):
            if not isinstance(value, str) or not pattern.fullmatch(value):
                raise ConfigurationError("Invalid experiment identifier")
        if not isinstance(experiment.notebook_name, str) or not experiment.notebook_name.strip():
            raise ConfigurationError("A notebook display name is required")
        if experiment.controller_id in by_controller or experiment.notebook_id in notebooks:
            raise ConfigurationError("Duplicate controller or notebook ID")
        experiment.notebook_path(root)
        by_controller[experiment.controller_id] = experiment
        notebooks.add(experiment.notebook_id)
    return by_controller


def read_private_settings(path: Path) -> dict[str, str]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, encoding="utf-8") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ConfigurationError("The .env file must be owner-only")
            settings = {}
            for line in source:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if not sep or not _PREFIX.fullmatch(key) or key in settings:
                    raise ConfigurationError("Invalid or duplicate .env field")
                if value.startswith(("'", '"')):
                    if len(value) < 2 or value[-1] != value[0]:
                        raise ConfigurationError("Invalid quoted .env value")
                    value = value[1:-1]
                settings[key] = value
    except (OSError, UnicodeError):
        raise ConfigurationError("Cannot read the private .env file") from None
    return settings


def _account_connection(settings, prefix, account):
    try:
        token = settings[f"{prefix}_TOKEN"]
        currency = settings[f"{prefix}_HOME_CURRENCY"]
        if not token or not token.isascii() or not token.isprintable() or " " in token:
            raise ValueError
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError
    except (KeyError, ValueError):
        raise ConfigurationError("Missing or invalid private connection fields") from None
    return AccountConnection(account, token, currency)


def _configured_count(settings, prefix):
    try:
        count_text = settings[f"{prefix}_LOOKBACK_CANDLES"]
        if not re.fullmatch(r"[0-9]+", count_text):
            raise ValueError
        count = int(count_text)
        if not 15 <= count < 2**63:
            raise ValueError
    except (KeyError, ValueError):
        raise ConfigurationError("Missing or invalid private connection fields") from None
    return count


def _unique_json_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError
    return result


def _load_manifest(root: Path, version: str, token: str) -> StrategyManifest:
    path = root / "strategies" / version / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
        if manifest["strategy_version"] != version:
            raise ValueError
        count = manifest["qualified_total_candle_count"]
        if type(count) is not int or count < 15:
            raise ValueError
        if not manifest["research_result_id"].strip() or not _COMMIT.fullmatch(manifest["source_commit"]):
            raise ValueError
        for name in ("implementation_hashes", "conversion_hashes", "dependency_hashes"):
            hashes = manifest[name]
            if not isinstance(hashes, dict) or (name == "implementation_hashes" and not hashes):
                raise ValueError
            if any(not key or not _SHA256.fullmatch(value) for key, value in hashes.items()):
                raise ValueError
        if not isinstance(manifest["parameters"], dict) or not manifest["lab_numeric_semantics"]:
            raise ValueError
        for name in ("output_bindings", "signal_rules"):
            if not isinstance(manifest[name], dict) or not all(manifest[name].get(k) for k in ("c1", "exit")):
                raise ValueError
        evidence = manifest["qualification_evidence"]
        if not isinstance(evidence, list) or not evidence or not all(ref.strip() for ref in evidence):
            raise ValueError
        if redact(manifest, (token,)) != manifest:
            raise ValueError
        body = canonical_json(manifest)
    except (AttributeError, KeyError, OSError, TypeError, ValueError, RecursionError):
        raise ConfigurationError("Missing or invalid strategy manifest") from None
    return StrategyManifest(body, sha256(body.encode()).hexdigest(), count)


def _account_configuration(root, controller_id):
    registry = read_registry(root)
    if controller_id not in registry:
        raise ConfigurationError("Controller is missing from the experiment registry")
    settings = read_private_settings(root / ".env")
    accounts = {
        key: settings.get(f"{experiment.connection_key}_ACCOUNT_ID", "")
        for key, experiment in registry.items()
    }
    if any(not _ACCOUNT.fullmatch(account) for account in accounts.values()):
        raise ConfigurationError("Missing or invalid private account ID")
    if len(set(accounts.values())) != len(accounts):
        raise ConfigurationError("Duplicate account binding")

    experiment = registry[controller_id]
    connection = _account_connection(settings, experiment.connection_key, accounts[controller_id])
    return AccountBinding(experiment, connection), settings


def load_account_binding(root: Path, controller_id: str) -> AccountBinding:
    """Validate the registry and private connection for read-only account preflight."""
    binding, _ = _account_configuration(root, controller_id)
    return binding


def load_binding(root: Path, controller_id: str) -> Binding:
    """Check registry-wide identity and load the requested controller's strategy."""
    binding, settings = _account_configuration(root, controller_id)
    experiment, account = binding.experiment, binding.connection
    connection = PrivateConnection(account.account_id, account.token, account.home_currency,
                                   _configured_count(settings, experiment.connection_key))
    manifest = _load_manifest(root, experiment.strategy_version, connection.token)
    if manifest.lookback_candles != connection.lookback_candles:
        raise ConfigurationError("Configured lookback differs from the qualified count")
    return Binding(experiment, connection, manifest)
