"""Resolve scenario IDs for general_simulation tool calls."""

from __future__ import annotations

import re
from typing import Optional

# Map free-text clues → seeded scenario IDs (used when request has no scenario_id).
_SCENARIO_CLUES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\b(uk|nats|gps|airspace|opensky)\b", re.IGNORECASE),
        "opensky-uk-closure-001",
    ),
    (
        re.compile(r"\b(port\s+strike|los\s+angeles|long\s+beach|\bla\b)\b", re.IGNORECASE),
        "supply-chain-port-strike-la",
    ),
    (
        re.compile(r"\b(suez|canal\s+block)\b", re.IGNORECASE),
        "supply-chain-suez-blockage",
    ),
]

KNOWN_SCENARIO_IDS: frozenset[str] = frozenset(sid for _, sid in _SCENARIO_CLUES)

# Friendly labels mirroring the frontend ``SCENARIO_LABELS`` so the system
# prompt can name the active scenario for the model.
_SCENARIO_LABELS: dict[str, str] = {
    "opensky-uk-closure-001": "UK Airspace Closure",
    "supply-chain-port-strike-la": "Port Strike LA",
    "supply-chain-suez-blockage": "Suez Blockage",
}


def scenario_context_block(scenario_id: str = "") -> str:
    """Return a system-prompt block naming the active scenario, or ``""``."""
    sid = (scenario_id or "").strip()
    if not sid:
        return ""
    label = _SCENARIO_LABELS.get(sid)
    if label:
        return f"Active scenario: {sid} ({label})."
    return f"Active scenario: {sid}."


def resolve_scenario_id(text: str, preferred: Optional[str] = None) -> str:
    """Prefer explicit/active scenario; otherwise infer from the user text."""
    if preferred and preferred.strip():
        return preferred.strip()
    for pattern, scenario_id in _SCENARIO_CLUES:
        if pattern.search(text or ""):
            return scenario_id
    return ""


def normalize_scenario_id(
    model_scenario_id: str = "",
    *,
    active_scenario_id: str = "",
    question: str = "",
) -> str:
    """Resolve a tool ``scenario_id``, fixing labels invented by small models.

    Prefer the UI-selected scenario. Accept known seeded IDs from the model.
    Otherwise map free-text labels (e.g. ``\"UK NATS GPS failure\"``) via clues.
    """
    active = (active_scenario_id or "").strip()
    if active:
        return active
    raw = (model_scenario_id or "").strip()
    if raw in KNOWN_SCENARIO_IDS:
        return raw
    return resolve_scenario_id(f"{raw} {question}".strip())
