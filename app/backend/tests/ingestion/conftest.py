"""Ingestion tests: put ``app/backend/ingestion`` on ``sys.path`` only."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent.parent
_ing = str(_BACKEND / "ingestion")
if _ing not in sys.path:
    sys.path.insert(0, _ing)
