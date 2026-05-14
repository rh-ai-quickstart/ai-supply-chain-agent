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


def main() -> int:
    extra = sys.argv[1:]
    r1 = subprocess.call(_PYTEST + [str(_ROOT / "tests" / "api")] + extra)
    r2 = subprocess.call(_PYTEST + [str(_ROOT / "tests" / "ingestion")] + extra)
    return r1 or r2


if __name__ == "__main__":
    raise SystemExit(main())
