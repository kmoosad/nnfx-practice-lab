"""Administrator read-only export for adding Python 02 to the shared deployment.

No credentials, broker requests, notebook SQL, service changes or plan writes.
The output contains public bindings, file hashes and current service states.
"""

import argparse
from datetime import UTC, datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib


CODE = Path("/opt/nnfx-practice")
DATA = Path("/var/lib/nnfx-practice")
PLANS = Path("/etc/nnfx-practice/qualification")


def inspect():
    registry = tomllib.loads((DATA / "config.toml").read_text())
    source = {}
    for directory in ("nnfx_practice", "strategies"):
        for path in sorted((CODE / directory).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix in (".py", ".json", ".sql", ".html", ".css"):
                source[str(path.relative_to(CODE))] = sha256(path.read_bytes()).hexdigest()
    plans = {}
    units = {}
    allowed = ("version", "enabled", "mode", "controller_id", "notebook_id", "account_binding_sha256",
               "manifest_sha256", "code_sha256", "config_sha256", "kernel", "boot_id", "schedule", "dispatch_at", "run_id")
    controllers = {row["controller_id"] for row in registry["experiments"]} | {"practice-b"}
    for controller in sorted(controllers):
        path = PLANS / (controller + ".json")
        if path.exists():
            raw = path.read_bytes()
            plan = json.loads(raw)
            plans[controller] = {"sha256": sha256(raw).hexdigest(), "identity": {k: plan.get(k) for k in allowed},
                                 "evidence_hashes": {k: v.get("sha256") for k, v in plan.get("evidence", {}).items()}}
        else:
            plans[controller] = None
        for unit in (f"nnfx-practice@{controller}.service", f"nnfx-practice@{controller}.timer",
                     f"nnfx-practice-qualification@{controller}.timer"):
            result = subprocess.run(["systemctl", "show", unit,
                                     "--property=LoadState,ActiveState,SubState,UnitFileState,Job,NextElapseUSecRealtime"],
                                    capture_output=True, text=True, check=True, timeout=15)
            units[unit] = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    notebooks = {}
    for path in sorted((DATA / "var/notebooks").glob("*")):
        if path.is_file() and not path.is_symlink():
            before = path.stat()
            digest = sha256(path.read_bytes()).hexdigest()
            after = path.stat()
            notebooks[path.name] = dict(size=after.st_size, uid=after.st_uid, gid=after.st_gid,
                                         mode=oct(after.st_mode & 0o777), sha256=digest,
                                         stable_during_read=(before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size))
    return dict(at=datetime.now(UTC).isoformat(), classification="read-only Python 02 deployment inspection",
                broker_requests=0, registry=registry, registry_sha256=sha256((DATA / "config.toml").read_bytes()).hexdigest(),
                source_hashes=source, plans=plans, units=units, notebook_files=notebooks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Administrator access is required to read the protected deployment; nothing changed")
    if args.output.exists() or args.output.is_symlink():
        parser.error("Use a new output filename; existing evidence is preserved")
    report = inspect()
    with args.output.open("x") as target:
        json.dump(report, target, indent=2)
        target.write("\n")
    args.output.chmod(0o644)
    print("Read-only deployment inspection saved to", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
