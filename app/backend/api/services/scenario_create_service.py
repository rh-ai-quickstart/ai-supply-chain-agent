"""Propose and create general-simulation scenarios from natural language."""

from __future__ import annotations

import json
import re
from typing import Any, Optional
from uuid import uuid4

from clients.general_simulation_client import GeneralSimulationClient
from clients.llama_stack_client import LlamaStackClient
from logging_config import getLogger

logger = getLogger(__name__)

_PROPOSE_SYSTEM_PROMPT = (
    "You design supply-chain / logistics disruption scenarios for a simulation engine. "
    "Given an operator's natural-language description, reply with ONLY a single JSON object "
    "(no markdown fences, no commentary) with these keys:\n"
    '- "name": short human-readable title\n'
    '- "scenario_id": lowercase slug with hyphens (letters, digits, hyphens only)\n'
    '- "description": 1-3 sentence disruption description for the simulation event\n'
    '- "affect_bbox": geographic envelope as "minLon,minLat,maxLon,maxLat" '
    "(decimal degrees, WGS84; min < max for each pair)\n"
    '- "place_summary": brief place/region covered by the bbox\n'
    '- "rationale": one short sentence explaining the bbox choice\n'
    "Choose a realistic bbox for the named place or region. "
    "Do not invent entity IDs."
)

_BBOX_RE = re.compile(
    r"^\s*"
    r"(-?\d+(?:\.\d+)?)\s*,\s*"
    r"(-?\d+(?:\.\d+)?)\s*,\s*"
    r"(-?\d+(?:\.\d+)?)\s*,\s*"
    r"(-?\d+(?:\.\d+)?)\s*$"
)
_SCENARIO_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_propose_json(raw: str) -> dict[str, Any]:
    """Extract and validate a propose draft from model text."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty model response")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model response did not contain a JSON object")

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")

    return normalize_draft(data)


def normalize_draft(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a scenario draft dict."""
    name = str(data.get("name") or "").strip()
    scenario_id = str(data.get("scenario_id") or "").strip().lower()
    description = str(data.get("description") or "").strip()
    affect_bbox = str(data.get("affect_bbox") or data.get("bbox") or "").strip()
    place_summary = str(data.get("place_summary") or "").strip()
    rationale = str(data.get("rationale") or "").strip()

    if not name:
        raise ValueError("name is required")
    if not scenario_id:
        scenario_id = _slugify(name)
    if not _SCENARIO_ID_RE.match(scenario_id):
        raise ValueError(
            "scenario_id must be a lowercase slug (letters, digits, hyphens)"
        )
    if not description:
        raise ValueError("description is required")

    affect_bbox = validate_bbox(affect_bbox)

    return {
        "name": name,
        "scenario_id": scenario_id,
        "description": description,
        "affect_bbox": affect_bbox,
        "place_summary": place_summary,
        "rationale": rationale,
    }


def validate_bbox(raw: str) -> str:
    match = _BBOX_RE.match(raw or "")
    if not match:
        raise ValueError(
            'affect_bbox must be "minLon,minLat,maxLon,maxLat" with four numbers'
        )
    min_lon, min_lat, max_lon, max_lat = (float(g) for g in match.groups())
    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise ValueError("longitude values must be between -180 and 180")
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise ValueError("latitude values must be between -90 and 90")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("affect_bbox requires minLon < maxLon and minLat < maxLat")
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or f"scenario-{uuid4().hex[:8]}"


class ScenarioCreateService:
    def __init__(
        self,
        llama_stack_client: Optional[LlamaStackClient] = None,
        general_simulation_client: Optional[GeneralSimulationClient] = None,
    ):
        self._llm = llama_stack_client or LlamaStackClient()
        self._gen_sim = general_simulation_client or GeneralSimulationClient()

    def propose(self, prompt: str) -> dict[str, Any]:
        text = (prompt or "").strip()
        if not text:
            return {"success": False, "error": "prompt is required"}

        answer = self._propose_with_llm(text)
        if answer.get("error"):
            return {"success": False, "error": answer["error"]}

        try:
            draft = parse_propose_json(answer["text"])
        except ValueError as exc:
            logger.warning(
                "Scenario propose parse failed: %s raw=%r",
                exc,
                answer.get("text", "")[:300],
            )
            return {
                "success": False,
                "error": f"Could not parse scenario draft: {exc}",
                "raw": answer.get("text"),
            }

        return {"success": True, "draft": draft, "completion": answer.get("completion")}

    def _propose_with_llm(self, prompt: str) -> dict[str, Any]:
        """Chat completion with the propose-only system prompt (single system message)."""
        messages = [
            {"role": "system", "content": _PROPOSE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            completion = self._llm._client.chat.completions.create(
                **self._llm._completion_kwargs(messages, stream=False),
            )
            text = completion.choices[0].message.content or ""
            return {
                "text": text,
                "completion": self._llm._completion_to_json(completion),
            }
        except Exception as exc:
            logger.error("Scenario propose LLM failed: %s", exc)
            return {"error": str(exc), "text": ""}

    def create(self, draft: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = normalize_draft(draft)
        except ValueError as exc:
            return {"success": False, "error": str(exc)}

        event_id = str(draft.get("event_id") or "").strip() or f"evt-{normalized['scenario_id']}"
        attributes: dict[str, Any] = {"name": normalized["name"]}
        if normalized.get("place_summary"):
            attributes["place_summary"] = normalized["place_summary"]
        if normalized.get("rationale"):
            attributes["rationale"] = normalized["rationale"]

        result = self._gen_sim.create_event(
            event_id=event_id,
            scenario_id=normalized["scenario_id"],
            description=normalized["description"],
            bbox=normalized["affect_bbox"],
            attributes=attributes,
        )
        if "error" in result:
            return {"success": False, "error": result["error"]}

        # Best-effort refresh (inject already syncs bbox; this covers multi-event scenarios).
        sync = self._gen_sim.sync_spatial(normalized["scenario_id"])
        if "error" in sync:
            logger.warning(
                "Scenario create: sync_spatial warning for %s: %s",
                normalized["scenario_id"],
                sync["error"],
            )

        return {
            "success": True,
            "scenario_id": normalized["scenario_id"],
            "event_id": result.get("event_id", event_id),
            "name": normalized["name"],
            "affect_bbox": result.get("affect_bbox", normalized["affect_bbox"]),
            "affected_count": result.get("affected_count"),
            "draft": normalized,
        }
