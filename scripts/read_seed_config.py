#!/usr/bin/env python3
"""Read the laptop ``seed`` block from a Helm values file and print JSON.

Run with general-simulation's environment so PyYAML is available:

    uv run python scripts/read_seed_config.py <repo_root> <values_file>

Stdout is a single JSON object:

    {"networkFiles": [...], "opensky": {"enabled": bool, "max": int, "timeoutSeconds": float}}

Paths in ``seed.networkFiles`` are resolved against ``repo_root``. A missing
file, a missing ``seed`` key, or an empty file list with OpenSky disabled
exits non-zero. Diagnostics go to stderr so stdout stays machine-readable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _require_int(value: object, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        fail(f"{label} must be an integer >= {minimum}")
    return value


def _require_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        fail("seed.opensky.timeoutSeconds must be a number > 0")
    return float(value)


def load_seed_config(repo_root: Path, values_path: Path) -> dict:
    if not values_path.is_file():
        fail(f"Values file not found: {values_path}")

    document = yaml.safe_load(values_path.read_text()) or {}
    if not isinstance(document, dict) or "seed" not in document:
        fail(f"{values_path} has no top-level 'seed' key")

    seed = document["seed"]
    if not isinstance(seed, dict):
        fail("'seed' must be a mapping")

    raw_files = seed.get("networkFiles", [])
    if raw_files is None:
        raw_files = []
    if not isinstance(raw_files, list):
        fail("seed.networkFiles must be a list")

    network_files: list[str] = []
    for entry in raw_files:
        if not isinstance(entry, str) or not entry.strip():
            fail("seed.networkFiles entries must be non-empty paths")
        path = Path(entry)
        if not path.is_absolute():
            path = repo_root / path
        if not path.is_file():
            fail(f"Network YAML not found: {path}")
        network_files.append(str(path.resolve()))

    opensky = seed.get("opensky") or {}
    if not isinstance(opensky, dict):
        fail("seed.opensky must be a mapping")

    if "enabled" in opensky and not isinstance(opensky["enabled"], bool):
        fail("seed.opensky.enabled must be true or false")
    enabled = bool(opensky.get("enabled", False))

    max_entities = _require_int(opensky.get("max", 50), "seed.opensky.max", minimum=0)
    timeout_seconds = _require_timeout(opensky.get("timeoutSeconds", 60))

    if not network_files and not enabled:
        fail(
            "seed.networkFiles is empty and seed.opensky.enabled is false; nothing to seed"
        )

    return {
        "networkFiles": network_files,
        "opensky": {
            "enabled": enabled,
            "max": max_entities,
            "timeoutSeconds": timeout_seconds,
        },
    }


def main() -> None:
    if len(sys.argv) != 3:
        fail("Usage: read_seed_config.py <repo_root> <values_file>")
    config = load_seed_config(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
    json.dump(config, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
