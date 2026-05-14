"""API tests: put ``app/backend/api`` on ``sys.path`` (``services.*`` from API)."""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent.parent
_api = str(_BACKEND / "api")
if _api not in sys.path:
    sys.path.insert(0, _api)
