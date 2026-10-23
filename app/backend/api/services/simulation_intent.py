"""Resolve scenario IDs and build simulation context for chat prompts."""

from __future__ import annotations

import re
from typing import Any, Optional

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

# Narrative context mirroring frontend ``SCENARIO_QUESTIONS`` so general chat
# always knows what the active simulation is about (without calling the tool).
_SCENARIO_DESCRIPTIONS: dict[str, str] = {
    "opensky-uk-closure-001": (
        "UK airspace is closed due to a NATS GPS failure. Operators need to "
        "understand affected aircraft, diversions, and estimated cost of impact."
    ),
    "supply-chain-port-strike-la": (
        "Port of Los Angeles and Long Beach are closed by a strike. Operators need "
        "to understand affected vessels, cargo, inland facilities, and estimated cost."
    ),
    "supply-chain-suez-blockage": (
        "The Suez Canal is blocked. Operators need to understand delayed vessels "
        "and cargoes, impact on European ports, and estimated cost of impact."
    ),
}

_MAX_AFFECTED_ENTITIES_IN_CONTEXT = 12
_MAX_VALUE_BREAKDOWN_ROWS = 15


def scenario_context_block(
    scenario_id: str = "",
    *,
    impact: Optional[dict[str, Any]] = None,
    user_text: str = "",
) -> str:
    """Return a system-prompt block for the active simulation, or ``""``.

    Always prefers an explicit ``scenario_id``. When missing, infers a seeded
    scenario from ``user_text``. When a recent Impact Query ``impact`` payload
    is provided, appends a compact snapshot so chat stays grounded without
    calling the general_simulation tool.
    """
    sid = (scenario_id or "").strip() or resolve_scenario_id(user_text)
    impact_data = impact if isinstance(impact, dict) else None
    if not sid and not impact_data:
        return ""

    parts: list[str] = []
    if sid:
        label = _SCENARIO_LABELS.get(sid)
        if label:
            parts.append(f"Active simulation scenario: {sid} ({label}).")
        else:
            parts.append(f"Active simulation scenario: {sid}.")
        description = _SCENARIO_DESCRIPTIONS.get(sid)
        if description:
            parts.append(f"Scenario context: {description}")
        else:
            parts.append(
                "Scenario context: treat this as the active disruption the operator "
                "is investigating on the Simulation page."
            )

    snapshot = format_impact_snapshot(impact_data) if impact_data else ""
    if snapshot:
        parts.append(
            "A Latest Impact Query result is included below. Treat it as authoritative "
            "for the current map state and answer impact questions from it "
            "(including per-entity values). Do not redirect the user to Impact Query "
            "when this snapshot already answers the question."
        )
        parts.append(snapshot)
    else:
        parts.append(
            "Ground answers in this active simulation when relevant. "
            "No Impact Query snapshot is loaded yet — if the operator needs a fresh "
            "what-if impact run, direct them to Impact Query on the Simulation page."
        )
    return "\n".join(parts)


def format_impact_snapshot(impact: Optional[dict[str, Any]]) -> str:
    """Compact latest Impact Query result for the chat system prompt."""
    if not isinstance(impact, dict) or not impact:
        return ""

    scenario_id = str(impact.get("scenario_id") or "").strip()
    question = str(impact.get("question") or "").strip()
    answer = str(impact.get("answer") or "").strip()
    entities = impact.get("affected_entities") or []
    if not isinstance(entities, list):
        entities = []
    entity_ids = [str(e).strip() for e in entities if str(e).strip()]
    solver = impact.get("solver") if isinstance(impact.get("solver"), dict) else {}

    lines = ["Latest Impact Query result (authoritative for current map state):"]
    if scenario_id:
        lines.append(f"- scenario_id: {scenario_id}")
    if question:
        lines.append(f"- question: {question}")
    if answer:
        # Keep the prompt bounded; full narrative can be long.
        clipped = answer if len(answer) <= 1200 else answer[:1197].rstrip() + "..."
        lines.append(f"- answer: {clipped}")
    lines.append(f"- affected_entities ({len(entity_ids)}): {_format_entity_list(entity_ids)}")
    if solver:
        score = solver.get("impact_score", "N/A")
        var_ = solver.get("total_value_at_risk", "N/A")
        currency = solver.get("currency", "USD")
        lines.append(f"- impact_score: {score}")
        lines.append(f"- total_value_at_risk: {var_} {currency}")
        breakdown_lines = _format_value_breakdown(
            solver.get("value_breakdown"),
            currency=str(currency or "USD"),
        )
        if breakdown_lines:
            lines.append(
                f"- value_breakdown (top {len(breakdown_lines)} by value_usd, "
                "aircraft=flight revenue, cargo-*=shipment value):"
            )
            lines.extend(f"  - {row}" for row in breakdown_lines)
    return "\n".join(lines)


def _format_value_breakdown(
    breakdown: Any,
    *,
    currency: str = "USD",
) -> list[str]:
    """Return ranked value_breakdown lines for the prompt (highest value first)."""
    if not isinstance(breakdown, list) or not breakdown:
        return []

    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in breakdown:
        if not isinstance(row, dict):
            continue
        entity_id = str(row.get("entity_id") or "").strip()
        if not entity_id:
            continue
        try:
            value = float(row.get("value_usd"))
        except (TypeError, ValueError):
            continue
        if not (value > 0):
            continue
        ranked.append((value, row))

    ranked.sort(key=lambda item: item[0], reverse=True)
    rows = ranked[:_MAX_VALUE_BREAKDOWN_ROWS]
    out: list[str] = []
    for value, row in rows:
        entity_id = str(row.get("entity_id") or "").strip()
        kind = "cargo" if entity_id.startswith("cargo-") else "flight"
        extras: list[str] = []
        for key in ("callsign", "call_sign", "route", "label"):
            raw = row.get(key)
            if raw is None:
                continue
            text = str(raw).strip()
            if text:
                extras.append(f"{key}={text}")
        extra = f" ({', '.join(extras)})" if extras else ""
        out.append(f"{entity_id} [{kind}]{extra}: {value:g} {currency}")
    return out


def _format_entity_list(entity_ids: list[str]) -> str:
    if not entity_ids:
        return "none"
    if len(entity_ids) <= _MAX_AFFECTED_ENTITIES_IN_CONTEXT:
        return ", ".join(entity_ids)
    head = entity_ids[:_MAX_AFFECTED_ENTITIES_IN_CONTEXT]
    remaining = len(entity_ids) - len(head)
    return f"{', '.join(head)} (+{remaining} more)"


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
