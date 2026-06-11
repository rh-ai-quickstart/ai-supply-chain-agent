"""API tests: put ``app/backend/api`` on ``sys.path`` (``services.*`` from API)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# main.py reads this at import time; tests do not start a real Llama Stack server.
os.environ.setdefault("LLAMA_STACK_OPENAI_MODEL", "external-model/test-model")

_BACKEND = Path(__file__).resolve().parent.parent.parent
_api = str(_BACKEND / "api")
if _api not in sys.path:
    sys.path.insert(0, _api)
