#!/usr/bin/env python3
"""Run API and ingestion tests in separate processes.

``app/backend/api`` and ``app/backend/ingestion`` each expose a top-level
``services`` package. Loading both onto ``sys.path`` in one pytest process
breaks imports, so this script runs two ``pytest`` invocations.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_PYTEST = [
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "--tb=short",
    "-p",
    "no:xdist",
    "-p",
    "no:asyncio",
]
_COV_BASE = [
    "--cov-report=term-missing",
]


def main() -> int:
    extra = sys.argv[1:]
    use_cov = "--no-cov" not in extra
    if use_cov:
        extra = [a for a in extra if a != "--no-cov"]

    api_cov = (
        ["--cov=api", f"--cov-config={_ROOT / 'pytest.ini'}", *_COV_BASE]
        if use_cov
        else []
    )
    ingestion_cov = (
        [
            "--cov=ingestion",
            f"--cov-config={_ROOT / 'pytest-ingestion.ini'}",
            *_COV_BASE,
        ]
        if use_cov
        else []
    )

    r1 = subprocess.call(
        _PYTEST + api_cov + [str(_ROOT / "tests" / "api")] + extra
    )
    r2 = subprocess.call(
        _PYTEST
        + ingestion_cov
        + [str(_ROOT / "tests" / "ingestion"), "-c", str(_ROOT / "pytest-ingestion.ini")]
        + extra
    )
    return r1 or r2


if __name__ == "__main__":
    raise SystemExit(main())
