"""Run the disruption evaluation through the deployed UI and log it to MLflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import statistics
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from http.client import RemoteDisconnected
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import mlflow
from mlflow import MlflowClient
from mlflow.entities import Feedback, Link, SpanType
from mlflow.exceptions import MlflowException
from mlflow.genai import make_judge, scorer
from mlflow.genai.scorers import (
    RelevanceToQuery,
    RetrievalGroundedness,
    RetrievalRelevance,
    RetrievalSufficiency,
    Safety,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, Response, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from evaluation.ui.scorers import (
    answer_is_non_empty,
    expected_impact_value_mentioned,
    expected_tool_used,
    highest_value_entity_named,
    no_cross_scenario_leakage,
)

LOGGER = logging.getLogger("supply_chain_disruption_eval")
DEFAULT_DATASET = (
    Path(__file__).resolve().parent / "datasets" / "seeded-disruptions.json"
)
DEFAULT_OUTPUT_DIR = Path(os.getenv("TMPDIR", "/tmp")) / "supply-chain-agent-eval"
CHAT_PATH = "/api/v1/chat"
SIMULATION_PATH = "/api/v1/general-simulation/query"
_ENTITY_LIMIT_IN_CHAT_CONTEXT = 12
_ENTITY_LIMIT_IN_JUDGE_CONTEXT = 100
_JUDGE_SNAPSHOT_ANSWER_LIMIT = 6000
_JUDGE_KB_CONTEXT_LIMIT = 6000
_TRACE_VISIBILITY_WAIT_SECONDS = 30
_TRACE_VISIBILITY_POLL_SECONDS = 2
_TRACE_ROOT_VISIBILITY_WAIT_SECONDS = 10
_JUDGE_RETRY_DELAYS_SECONDS = (10, 30, 120)
_JUDGE_TRANSIENT_RETRIES = min(
    len(_JUDGE_RETRY_DELAYS_SECONDS),
    max(0, int(os.getenv("EVAL_JUDGE_TRANSIENT_RETRIES", "3"))),
)
_EVALUATION_SCORER_NAMES = (
    "correctness",
    "builtin_relevance_to_query",
    "builtin_safety",
    "builtin_retrieval_sufficiency",
    "builtin_retrieval_relevance",
    "builtin_retrieval_groundedness",
    "retrieval_relevance",
    "retrieval_groundedness",
    "disruption_grounding",
    "answer_is_non_empty",
    "no_cross_scenario_leakage",
    "expected_impact_value_mentioned",
    "highest_value_entity_named",
    "expected_tool_used",
)
_PORT_RESILIENCE_KB_FACT = (
    "The knowledge base identifies pre-negotiated alternate gateways, safety stock at "
    "inland hubs, and flexible intermodal contracts as resilience measures."
)
_PORT_RESILIENCE_ANY_KB_FACT = (
    "The knowledge base identifies pre-negotiated alternate gateways, safety stock at "
    "inland hubs, and flexible intermodal contracts as resilience measures; the answer "
    "may mention one or more."
)
_PORT_ALTERNATE_GATEWAY_CHECK_FACT = (
    "The answer names either Oakland or Prince Rupert as an alternate gateway and advises "
    "checking inland transport capacity, delays, and freight costs before choosing."
)
_PORT_KB_EXPECTATION_MIGRATIONS = {
    "The knowledge base names Oakland and Prince Rupert as reroute options and says "
    "they add multi-day rail delays and higher inland freight costs.": _PORT_ALTERNATE_GATEWAY_CHECK_FACT,
    _PORT_RESILIENCE_KB_FACT: _PORT_RESILIENCE_ANY_KB_FACT,
}
_SUEZ_MITIGATION_EITHER_FACT = (
    "The knowledge base lists safety stock at a key European hub such as Rotterdam "
    "and pre-planned Cape routings with bunker hedges as mitigation measures; the "
    "answer may mention either one."
)
_SUEZ_MIXED_EXPECTATION_MIGRATIONS = {
    (
        "The knowledge base recommends safety stock at key European hubs such as "
        "Rotterdam."
    ): _SUEZ_MITIGATION_EITHER_FACT,
    (
        "The knowledge base recommends safety stock at key European hubs such as "
        "Rotterdam to buffer the added transit time."
    ): _SUEZ_MITIGATION_EITHER_FACT,
    (
        "The knowledge base says carriers with pre-planned Cape routings and bunker "
        "hedges recover schedules faster."
    ): _SUEZ_MITIGATION_EITHER_FACT,
    (
        "The knowledge base says pre-planned Cape routings and bunker hedges help "
        "carriers recover schedules faster."
    ): _SUEZ_MITIGATION_EITHER_FACT,
    (
        "The knowledge base lists pre-planned Cape routings and bunker hedges as "
        "mitigation measures."
    ): _SUEZ_MITIGATION_EITHER_FACT,
}
_MIXED_SOURCE_KB_EXPECTED_FACTS = {
    "supply-chain-port-strike-la": (
        _PORT_ALTERNATE_GATEWAY_CHECK_FACT,
    ),
    "supply-chain-suez-blockage": (
        "The knowledge base estimates that a Cape of Good Hope reroute adds roughly 12 to 15 days and significant extra fuel burn.",
        _SUEZ_MITIGATION_EITHER_FACT,
    ),
    "opensky-uk-closure-001": (
        "The knowledge base says carriers should have pre-approved diversion airports and fuel contingencies.",
        "The knowledge base warns that alternate European airports may be constrained by ramp capacity, customs, and crew duty-time limits.",
    ),
}


class EvaluationError(RuntimeError):
    """An evaluation setup or UI interaction failed."""


class BrowserNetworkCapture:
    """Capture evaluation request metadata, excluding headers and credentials."""

    def __init__(self, page: Page):
        self.requests: list[dict[str, Any]] = []
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)

    @staticmethod
    def _path(url: str) -> str:
        return urlsplit(url).path

    @staticmethod
    def _post_data(request: Any) -> dict[str, Any]:
        raw = request.post_data
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _on_request(self, request: Any) -> None:
        path = self._path(request.url)
        if request.method != "POST" or path not in (CHAT_PATH, SIMULATION_PATH):
            return
        record = {
            "path": path,
            "method": request.method,
            "payload": self._post_data(request),
            "status": None,
            "response": None,
            "failure": None,
        }
        self.requests.append(record)

    def _on_response(self, response: Response) -> None:
        path = self._path(response.url)
        record = next(
            (
                candidate
                for candidate in reversed(self.requests)
                if candidate["path"] == path and candidate["status"] is None
            ),
            None,
        )
        if record:
            record["status"] = response.status
            record["response"] = response

    def _on_request_failed(self, request: Any) -> None:
        path = self._path(request.url)
        record = next(
            (
                candidate
                for candidate in reversed(self.requests)
                if candidate["path"] == path
                and candidate["status"] is None
                and candidate["failure"] is None
            ),
            None,
        )
        if record:
            record["failure"] = request.failure or "unknown browser network failure"

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {
                "path": record["path"],
                "method": record["method"],
                "payload": record["payload"],
                "status": record["status"],
                "failure": record["failure"],
            }
            for record in self.requests
        ]

    def latest(
        self,
        path: str,
        *,
        scenario_id: str | None = None,
        after: int = 0,
    ) -> dict[str, Any] | None:
        for record in reversed(self.requests[after:]):
            if record["path"] != path:
                continue
            if (
                scenario_id is not None
                and record["payload"].get("scenario_id") != scenario_id
            ):
                continue
            return record
        return None


def _load_dataset(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EvaluationError(f"Cannot read dataset {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"Dataset is not valid JSON: {path}: {exc}") from exc
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise EvaluationError("Dataset must contain a non-empty 'scenarios' list.")
    return payload


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _value_breakdown(impact_result: dict[str, Any]) -> list[dict[str, Any]]:
    solver = impact_result.get("solver")
    rows = solver.get("value_breakdown", []) if isinstance(solver, dict) else []
    ranked: list[tuple[float, dict[str, Any]]] = []
    if not isinstance(rows, list):
        return []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("entity_id") or "").strip():
            continue
        value = _safe_float(row.get("value_usd"))
        if value is not None and value > 0:
            ranked.append((value, row))
    ranked.sort(key=lambda entry: entry[0], reverse=True)
    return [row for _, row in ranked]


def _compact_impact_snapshot(
    impact_snapshot: Any,
    *,
    include_mitigation_options: bool = False,
) -> dict[str, Any]:
    """Keep only the impact evidence needed by judge prompts."""
    if not isinstance(impact_snapshot, dict):
        return {}

    solver = impact_snapshot.get("solver")
    solver = solver if isinstance(solver, dict) else {}
    affected_entities = impact_snapshot.get("affected_entities")
    affected_entities = affected_entities if isinstance(affected_entities, list) else []

    compact_solver = {
        key: solver[key]
        for key in (
            "currency",
            "total_value_at_risk",
            "impact_score",
            "affected_count",
        )
        if key in solver
    }
    compact_solver["value_breakdown"] = [
        {
            "entity_id": row.get("entity_id"),
            "value_usd": row.get("value_usd"),
        }
        for row in _value_breakdown(impact_snapshot)[:3]
    ]

    explanation = solver.get("explanation")
    if isinstance(explanation, str) and explanation:
        compact_solver["explanation"] = explanation[:500]

    if include_mitigation_options:
        snapshot_answer = impact_snapshot.get("answer")
        if isinstance(snapshot_answer, str) and snapshot_answer:
            compact_solver["snapshot_answer"] = snapshot_answer[
                :_JUDGE_SNAPSHOT_ANSWER_LIMIT
            ]

        reroutes = solver.get("recommended_reroutes")
        if isinstance(reroutes, list):
            compact_solver["recommended_reroutes"] = [
                {
                    key: (value[:240] if isinstance(value, str) else value)
                    for key in ("entity_id", "target_id", "target_label", "rationale")
                    if (value := reroute.get(key)) is not None
                }
                for reroute in reroutes[:_ENTITY_LIMIT_IN_JUDGE_CONTEXT]
                if isinstance(reroute, dict)
            ]

        response_options = solver.get("response_options")
        if isinstance(response_options, list):
            compact_solver["response_options"] = [
                {
                    key: (value[:300] if isinstance(value, str) else value)
                    for key in (
                        "rank",
                        "label",
                        "description",
                        "estimated_impact_reduction",
                    )
                    if (value := option.get(key)) is not None
                }
                for option in response_options[:3]
                if isinstance(option, dict)
            ]

    return {
        "scenario_id": impact_snapshot.get("scenario_id"),
        "success": impact_snapshot.get("success"),
        "affected_entities": affected_entities[
            : _ENTITY_LIMIT_IN_JUDGE_CONTEXT
            if include_mitigation_options
            else _ENTITY_LIMIT_IN_CHAT_CONTEXT
        ],
        "solver": compact_solver,
    }


def _derive_expectations(
    scenario: dict[str, Any], turn: dict[str, Any], impact_result: dict[str, Any]
) -> dict[str, Any]:
    solver = (
        impact_result.get("solver")
        if isinstance(impact_result.get("solver"), dict)
        else {}
    )
    currency = str(solver.get("currency") or "USD")
    total_value = solver.get("total_value_at_risk")
    expected_facts = [
        *turn.get("expected_facts", []),
        *turn.get("kb_expected_facts", []),
    ]
    if turn.get("check_value_at_risk"):
        if total_value is None:
            expected_facts.append(
                "The impact snapshot does not provide a total value at risk."
            )
        else:
            expected_facts.append(f"Total value at risk is {total_value} {currency}.")

    expected_top_entity: str | None = None
    expected_turn_value: Any = total_value if turn.get("check_value_at_risk") else None
    if turn.get("check_top_value_entity"):
        breakdown = _value_breakdown(impact_result)
        if breakdown:
            expected_top_entity = str(breakdown[0].get("entity_id"))
            expected_turn_value = breakdown[0].get("value_usd")
            expected_facts.append(
                f"The highest value-breakdown entity is {expected_top_entity}, with a value of "
                f"{expected_turn_value} {currency}."
            )
        else:
            expected_facts.append(
                "The impact snapshot contains no positive per-entity value breakdown."
            )

    expectations = {
        "expected_facts": expected_facts,
        "expected_tool": turn.get("expected_tool", ""),
        "expected_tools": turn.get("expected_tools"),
        "expected_top_entity_id": expected_top_entity,
        "expected_value": expected_turn_value,
        "expected_currency": currency if expected_turn_value is not None else None,
        "forbidden_terms": (
            []
            if turn.get("category") == "news_retrieval"
            else scenario.get("forbidden_terms", [])
        ),
    }
    # MLflow converts each expectation entry into an Assessment and rejects
    # None values. Missing numeric/entity expectations mean "not applicable".
    return {key: value for key, value in expectations.items() if value is not None}


def _capture_sse_metadata(response: Response | None) -> dict[str, Any]:
    if response is None:
        return {}
    try:
        body = response.text()
    except PlaywrightError as exc:
        return {"body_capture_error": type(exc).__name__}
    metadata: dict[str, Any] = {}
    for block in body.split("\n\n"):
        data_lines = [
            line[5:].strip() for line in block.splitlines() if line.startswith("data:")
        ]
        for line in data_lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "done":
                completion = event.get("completion")
                if isinstance(completion, dict):
                    metadata["usage"] = completion.get("usage")
                    metadata["model"] = completion.get("model")
                if event.get("tool"):
                    metadata["tool"] = event["tool"]
                if event.get("simulation"):
                    metadata["simulation_returned"] = True
    return metadata


def _wait_for_dashboard(page: Page, ui_url: str, timeout_ms: int) -> None:
    page.set_default_timeout(timeout_ms)
    page.goto(ui_url.rstrip("/") + "/", wait_until="domcontentloaded")
    page.get_by_role("heading", name="Supply Chain Command Center").wait_for(
        state="visible"
    )
    # Wait for the API-backed scenario list to finish loading before the
    # scenario-specific lookup. An active button alone is not a readiness
    # signal for the full list the evaluator needs to select from.
    page.get_by_text("Loading scenarios…", exact=True).wait_for(state="detached")


def _close_chat_dialog(page: Page, timeout_ms: int) -> None:
    dialog = page.get_by_role("dialog", name="AI Assistant")
    if not dialog.count() or not dialog.is_visible():
        return
    close_button = dialog.get_by_role("button", name="Close dialog")
    close_button.click(timeout=min(timeout_ms, 5_000))
    dialog.wait_for(state="hidden", timeout=min(timeout_ms, 5_000))


def _run_scenario(
    page: Page,
    capture: BrowserNetworkCapture,
    scenario: dict[str, Any],
    timeout_ms: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Chat opens in a modal. Leaving it open after one scenario blocks clicks
    # on the scenario picker for the next scenario in this same browser page.
    _close_chat_dialog(page, timeout_ms)

    scenario_id = str(scenario["scenario_id"])
    scenario_label = str(scenario["label"])
    scenario_button = page.get_by_role("button", name=scenario_label, exact=True)
    if scenario_button.count() == 0:
        # Give the rendered scenario list a short grace period in case the UI
        # has finished its loading state but React has not committed the target
        # button yet. A genuinely absent scenario should still fail promptly.
        try:
            scenario_button.wait_for(state="visible", timeout=min(timeout_ms, 10_000))
        except PlaywrightTimeoutError:
            pass
    if scenario_button.count() != 1:
        buttons = page.locator('[aria-labelledby="impact-scenario-label"] button')
        available = []
        for index in range(buttons.count()):
            button = buttons.nth(index)
            label = (button.inner_text() or "").strip()
            title = button.get_attribute("title")
            available.append(f"{label!r}" + (f" ({title})" if title else ""))
        available_text = ", ".join(available) if available else "<none>"
        raise EvaluationError(
            f"Expected one scenario button named {scenario_label!r} for scenario ID "
            f"{scenario_id!r}; found {scenario_button.count()}. "
            f"Scenario buttons currently shown by the deployed UI: {available_text}. "
            "The UI gets these scenarios from general-sim-api; check that the seeded "
            "scenario exists in the namespace used by this deployment."
        )

    request_count_before_click = len(capture.requests)
    try:
        with page.expect_response(
            lambda response: (
                urlsplit(response.url).path == SIMULATION_PATH
                and response.request.method == "POST"
            ),
            timeout=timeout_ms,
        ) as response_info:
            scenario_button.click()
    except PlaywrightTimeoutError as exc:
        request = capture.latest(
            SIMULATION_PATH,
            scenario_id=scenario_id,
            after=request_count_before_click,
        )
        if request is None:
            detail = (
                "the scenario button click did not issue a POST for this scenario; "
                "the click may have been blocked by an open dialog or disabled control"
            )
        elif request.get("failure"):
            detail = f"the browser request failed: {request['failure']}"
        elif request.get("status") is not None:
            detail = (
                f"the browser capture saw HTTP {request['status']}, but Playwright did not "
                "match that response to its waiter"
            )
        else:
            detail = (
                "the browser sent the POST but received no response before the timeout"
            )
        raise EvaluationError(
            f"Impact query for {scenario_label} did not complete within {timeout_ms}ms; "
            f"{detail}. Playwright: {str(exc).splitlines()[0]}"
        ) from exc
    impact_response = response_info.value
    if impact_response.status != 200:
        raise EvaluationError(
            f"Impact query for {scenario_label} returned HTTP {impact_response.status}."
        )
    impact_result = impact_response.json()
    if not isinstance(impact_result, dict) or impact_result.get("success") is False:
        raise EvaluationError(
            f"Impact query failed for {scenario_label}: {impact_result!r}"
        )
    if impact_result.get("scenario_id") != scenario_id:
        raise EvaluationError(
            f"Impact query returned scenario {impact_result.get('scenario_id')!r}; expected {scenario_id!r}."
        )

    result_panel = page.locator(".impact-results-panel")
    result_panel.get_by_text("Value at risk", exact=True).wait_for(state="visible")
    kb_status = page.locator(".chat-kb-status__text").first
    kb_status.wait_for(state="visible")
    kb_text = kb_status.inner_text().strip()
    if not kb_text.startswith("Knowledge base:") or kb_text.endswith("None"):
        raise EvaluationError(
            f"No scenario knowledge base is active for {scenario_label}: {kb_text!r}"
        )
    expected_terms = [
        term.casefold() for term in scenario.get("expected_kb_name_terms", [])
    ]
    if expected_terms and not any(
        term in kb_text.casefold() for term in expected_terms
    ):
        raise EvaluationError(
            f"Knowledge base does not appear to match {scenario_label}. "
            f"Expected one of {expected_terms}; UI displayed {kb_text!r}."
        )

    simulation_request = capture.latest(SIMULATION_PATH)
    if simulation_request is None or simulation_request.get("status") != 200:
        raise EvaluationError(
            f"Could not capture successful impact request for {scenario_label}."
        )

    interactions: list[dict[str, Any]] = []
    for turn_index, turn in enumerate(scenario.get("turns", [])):
        previous_chat_count = len(
            [record for record in capture.requests if record.get("path") == CHAT_PATH]
        )
        started = time.perf_counter()
        visible_inputs = [
            page.get_by_label("Chat reply input"),
            page.get_by_label("Chat input"),
        ]
        chat_input = next(
            (locator for locator in visible_inputs if locator.is_visible()), None
        )
        if chat_input is None:
            raise EvaluationError(
                "Could not find a visible chat input in the dashboard."
            )
        chat_input.fill(str(turn["question"]))
        if chat_input.input_value() != str(turn["question"]):
            raise EvaluationError(
                f"Chat input did not commit the question for {turn['id']}."
            )
        chat_started_at_ms = int(time.time() * 1000)
        with page.expect_response(
            lambda response: (
                urlsplit(response.url).path == CHAT_PATH
                and response.request.method == "POST"
            ),
            timeout=timeout_ms,
        ) as chat_response_info:
            chat_input.press("Enter")
        chat_response = chat_response_info.value
        if chat_response.status >= 400:
            raise EvaluationError(
                f"Chat request for {turn['id']} returned HTTP {chat_response.status}."
            )

        page.get_by_role("heading", name="AI Assistant").wait_for(state="visible")
        page.locator(".chat-modal-overlay .muted").filter(has_text="Thinking").wait_for(
            state="hidden", timeout=timeout_ms
        )
        ai_messages = page.locator(".chat-modal-overlay .chat-message.ai")
        ai_message = ai_messages.nth(turn_index)
        ai_message.wait_for(state="visible", timeout=timeout_ms)
        answer = ai_message.inner_text().strip()
        if not answer:
            raise EvaluationError(f"The UI displayed an empty answer for {turn['id']}.")
        chat_finished_at_ms = int(time.time() * 1000)
        elapsed_ms = (time.perf_counter() - started) * 1000

        chat_request = capture.latest(CHAT_PATH)
        if (
            chat_request is None
            or len(
                [
                    record
                    for record in capture.requests
                    if record.get("path") == CHAT_PATH
                ]
            )
            != previous_chat_count + 1
        ):
            raise EvaluationError(
                f"Could not capture the chat request for {turn['id']}."
            )
        request_payload = chat_request.get("payload", {})
        request_impact = request_payload.get("impact_result")
        if request_payload.get("input") != turn["question"]:
            raise EvaluationError(
                f"Chat request for {turn['id']} did not contain the submitted question."
            )
        if request_payload.get("scenario_id") != scenario_id:
            raise EvaluationError(
                f"Chat request for {turn['id']} omitted the selected scenario ID."
            )
        if not request_payload.get("vector_store_id"):
            raise EvaluationError(
                f"Chat request for {turn['id']} omitted the matched vector store ID."
            )
        if (
            not isinstance(request_impact, dict)
            or request_impact.get("scenario_id") != scenario_id
        ):
            raise EvaluationError(
                f"Chat request for {turn['id']} omitted the active impact result."
            )

        expectation = _derive_expectations(scenario, turn, impact_result)
        interaction = {
            "turn_id": turn["id"],
            "category": turn.get("category", "general"),
            "requires_kb_context": bool(turn.get("requires_kb_context", False)),
            "kb_expected_facts": turn.get("kb_expected_facts", []),
            "expected_tool": turn.get("expected_tool", ""),
            "expected_tools": turn.get("expected_tools", []),
            "question": str(turn["question"]),
            "answer": answer,
            "expectations": expectation,
            "latency_ms": elapsed_ms,
            "chat_started_at_ms": chat_started_at_ms,
            "chat_finished_at_ms": chat_finished_at_ms,
            "chat_http_status": chat_response.status,
            "chat_request": {
                "scenario_id": request_payload.get("scenario_id"),
                "vector_store_id": request_payload.get("vector_store_id"),
                "impact_scenario_id": request_impact.get("scenario_id"),
                "chat_history_turns": len(request_payload.get("chat_history") or []),
            },
            "completion_metadata": _capture_sse_metadata(chat_response),
        }
        interactions.append(interaction)

    _close_chat_dialog(page, timeout_ms)

    capture_row = {
        "scenario_id": scenario_id,
        "label": scenario_label,
        "knowledge_base_status": kb_text,
        "impact_query": simulation_request.get("payload", {}).get("question"),
        "impact_result": impact_result,
        "impact_snapshot_sha256": _stable_json_sha256(impact_result),
        "interactions": interactions,
    }
    return capture_row, interactions


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(
        0, min(len(sorted_values) - 1, round((len(sorted_values) - 1) * percentile))
    )
    return sorted_values[index]


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _log_artifact_safely(path: Path, artifact_path: str) -> bool:
    try:
        mlflow.log_artifact(str(path), artifact_path=artifact_path)
        return True
    except Exception as exc:  # noqa: BLE001 - artifact upload must not fail the evaluation
        LOGGER.warning(
            "Could not upload MLflow artifact %s (%s).",
            path.name,
            type(exc).__name__,
        )
        return False


def _stable_json_sha256(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _root_span(trace: Any) -> Any | None:
    spans = getattr(getattr(trace, "data", None), "spans", None) or []
    return next((span for span in spans if span.parent_id is None), None)


def _search_all_traces(
    client: MlflowClient,
    experiment_id: str,
    filter_string: str,
    *,
    order_by: list[str],
) -> list[Any]:
    traces: list[Any] = []
    page_token: str | None = None
    while True:
        page = client.search_traces(
            locations=[experiment_id],
            filter_string=filter_string,
            max_results=500,
            order_by=order_by,
            page_token=page_token,
            include_spans=True,
        )
        traces.extend(page)
        page_token = page.token
        if not page_token:
            return traces


def _read_backend_traces(
    experiment_name: str,
    evaluation_started_at_ms: int,
) -> tuple[list[Any], dict[str, Any]]:
    """Read chat traces with autologged model spans and the latest backend session."""
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise EvaluationError(f"MLflow experiment {experiment_name!r} does not exist.")
    client = MlflowClient()
    startup_traces = client.search_traces(
        locations=[experiment.experiment_id],
        filter_string="trace.name = 'agent.backend.startup'",
        max_results=1,
        order_by=["timestamp_ms DESC"],
        include_spans=True,
    )
    if not startup_traces:
        raise EvaluationError(
            "No backend startup trace was found. Enable backend MLflow tracing and restart "
            "the backend before running the evaluation."
        )

    startup_trace = startup_traces[0]
    startup_root = _root_span(startup_trace)
    startup_outputs = startup_root.outputs if startup_root is not None else {}
    startup_outputs = startup_outputs if isinstance(startup_outputs, dict) else {}
    session_id = str(startup_outputs.get("backend_session_id") or "")
    started_at_ms = int(startup_trace.info.request_time)
    if not session_id:
        raise EvaluationError("The latest backend startup trace has no session ID.")
    if started_at_ms > evaluation_started_at_ms:
        raise EvaluationError(
            "The backend restarted after this evaluation began. Rerun after the backend is stable."
        )

    trace_filter = (
        f"trace.timestamp_ms >= {max(started_at_ms, evaluation_started_at_ms)}"
    )
    model_traces = _search_all_traces(
        client,
        experiment.experiment_id,
        trace_filter,
        order_by=["timestamp_ms ASC"],
    )
    session = {
        "backend_session_id": session_id,
        "backend_started_at_ms": started_at_ms,
        "startup_trace_id": startup_trace.info.trace_id,
        "evaluation_started_at_ms": evaluation_started_at_ms,
    }
    return model_traces, session


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    for method_name in ("model_dump", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                result = method()
            except Exception:
                LOGGER.debug(
                    "Could not serialize trace value with %s",
                    method_name,
                    exc_info=True,
                )
                continue
            if isinstance(result, dict):
                return result
    if isinstance(value, str):
        try:
            result = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return result if isinstance(result, dict) else {}
    return {}


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts).strip()
    if isinstance(content, dict) and isinstance(content.get("text"), str):
        return content["text"].strip()
    return ""


def _trace_question_and_answer(trace: Any) -> tuple[str, str]:
    """Extract the latest user message and assistant text from an OpenAI trace."""
    spans = getattr(getattr(trace, "data", None), "spans", None) or []
    spans = sorted(spans, key=lambda span: span.start_time_ns or 0)
    question = ""
    answer = ""
    for span in spans:
        inputs = _as_mapping(span.inputs)
        messages = inputs.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    question = _content_text(message.get("content"))
                    break

        output = _as_mapping(span.outputs)
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            choice = _as_mapping(choices[0])
            message = _as_mapping(choice.get("message"))
            candidate = _content_text(message.get("content")) or _content_text(
                message.get("refusal")
            )
            if candidate:
                answer = candidate
        elif isinstance(span.outputs, str):
            answer = span.outputs.strip()
    return question, answer


def _trace_knowledge_base_context(trace: Any) -> str:
    """Extract the retrieved KB passages embedded in OpenAI system prompts."""
    marker = "Relevant context from the knowledge base:\n"
    news_marker = "\n\n[Recent News Context]"
    spans = getattr(getattr(trace, "data", None), "spans", None) or []
    contexts: list[str] = []
    seen: set[str] = set()
    for span in spans:
        messages = _as_mapping(span.inputs).get("messages")
        if not isinstance(messages, list):
            continue
        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "system":
                continue
            content = _content_text(message.get("content"))
            if marker not in content:
                continue
            context = content.split(marker, 1)[1]
            if news_marker in context:
                context = context.split(news_marker, 1)[0]
            context = context.strip()
            if context and context not in seen:
                contexts.append(context)
                seen.add(context)
    return "\n\n".join(contexts)


def _trace_llm_call_metrics(trace: Any) -> tuple[int, float]:
    """Count autologged LLM spans and return their combined duration in milliseconds."""
    spans = getattr(getattr(trace, "data", None), "spans", None) or []
    llm_spans = [span for span in spans if str(span.span_type).upper() == "LLM"]
    duration_ms = sum(
        max(0, span.end_time_ns - span.start_time_ns) / 1_000_000
        for span in llm_spans
        if span.start_time_ns is not None and span.end_time_ns is not None
    )
    return len(llm_spans), duration_ms


def _build_trace_evaluation_rows(
    captured_scenarios: list[dict[str, Any]],
    model_traces: list[Any],
) -> tuple[list[dict[str, Any]], list[Any]]:
    """Use model-trace questions and answers, correlating them to UI turns by time."""
    trace_messages = [
        (
            trace,
            *_trace_question_and_answer(trace),
            _trace_knowledge_base_context(trace),
        )
        for trace in model_traces
    ]
    evaluation_rows: list[dict[str, Any]] = []
    selected_traces: dict[str, Any] = {}
    missing_turns: list[str] = []

    for scenario_result in captured_scenarios:
        for interaction in scenario_result["interactions"]:
            expected_question = str(interaction["question"]).strip()
            start_ms = int(interaction["chat_started_at_ms"])
            finish_ms = int(interaction["chat_finished_at_ms"])
            matches = [
                (trace, question, answer, kb_context)
                for trace, question, answer, kb_context in trace_messages
                if question == expected_question
                and start_ms <= int(trace.info.request_time) <= finish_ms
            ]
            final_calls = [
                (trace, question, answer, kb_context)
                for trace, question, answer, kb_context in matches
                if answer
            ]
            if not final_calls:
                exact_question_count = sum(
                    question == expected_question
                    for _, question, _, _ in trace_messages
                )
                missing_turns.append(
                    f"{scenario_result['scenario_id']}: {expected_question} "
                    f"[exact-question traces={exact_question_count}, "
                    f"in-window traces={len(matches)}, text answers={len(final_calls)}]"
                )
                continue

            # A tool loop may produce multiple model-call spans in one chat
            # trace. Score the last text completion and retain the full trace.
            answer_trace, trace_question, answer, _ = max(
                final_calls, key=lambda row: row[0].info.request_time
            )
            trace_ids = [trace.info.trace_id for trace, _, _, _ in matches]
            for trace, _, _, _ in matches:
                selected_traces[trace.info.trace_id] = trace
            kb_contexts = list(
                dict.fromkeys(
                    kb_context for _, _, _, kb_context in matches if kb_context
                )
            )
            kb_context = "\n\n".join(kb_contexts)
            llm_call_metrics = [
                _trace_llm_call_metrics(trace) for trace, _, _, _ in matches
            ]
            llm_call_span_count = sum(count for count, _ in llm_call_metrics)
            llm_call_duration_ms = sum(duration for _, duration in llm_call_metrics)

            evaluation_rows.append(
                {
                    "inputs": {
                        "question": trace_question,
                        "scenario_id": scenario_result["scenario_id"],
                        "disruption": scenario_result["label"],
                        "category": interaction["category"],
                        "knowledge_base_required": interaction["requires_kb_context"],
                        "knowledge_base_context": kb_context,
                        "knowledge_base_expected_facts": interaction[
                            "kb_expected_facts"
                        ],
                        "expected_tool": interaction.get("expected_tool", ""),
                        "expected_tools": interaction.get("expected_tools", []),
                        "tool_used": interaction.get("completion_metadata", {}).get(
                            "tool", ""
                        ),
                        "vector_store_id": interaction["chat_request"][
                            "vector_store_id"
                        ],
                        "impact_snapshot": scenario_result["impact_result"],
                        "runtime_trace_ids": trace_ids,
                    },
                    "outputs": answer,
                    "expectations": interaction["expectations"],
                    "trace": answer_trace,
                    "trace_id": answer_trace.info.trace_id,
                    "trace_timestamp_ms": answer_trace.info.request_time,
                    "trace_execution_ms": llm_call_duration_ms,
                    "model_call_span_count": llm_call_span_count,
                }
            )

    if missing_turns:
        missing = "; ".join(missing_turns)
        raise EvaluationError(
            "Could not find an autologged model question and text answer in the chat traces "
            "for these UI turns: "
            f"{missing}. Confirm MLflow OpenAI autologging is enabled and inspect the backend traces."
        )
    return evaluation_rows, list(selected_traces.values())


def _read_and_correlate_backend_traces(
    experiment_name: str,
    evaluation_started_at_ms: int,
    captured_scenarios: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Any], dict[str, Any]]:
    """Wait for chat answers and their root spans to become available in MLflow."""
    deadline = time.monotonic() + _TRACE_VISIBILITY_WAIT_SECONDS
    client = MlflowClient()
    while True:
        model_traces, backend_trace_session = _read_backend_traces(
            experiment_name,
            evaluation_started_at_ms,
        )
        try:
            trace_rows, selected_traces = _build_trace_evaluation_rows(
                captured_scenarios,
                model_traces,
            )
            _wait_for_evaluation_trace_roots(
                trace_rows,
                selected_traces,
                client,
            )
            return trace_rows, selected_traces, backend_trace_session
        except EvaluationError as exc:
            if not str(exc).startswith(
                "Could not find an autologged model question and text answer"
            ):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            LOGGER.info(
                "Some UI answers are not searchable in MLflow yet (%d traces visible); "
                "retrying in up to %ds",
                len(model_traces),
                min(_TRACE_VISIBILITY_POLL_SECONDS, int(remaining + 0.999)),
            )
            time.sleep(min(_TRACE_VISIBILITY_POLL_SECONDS, remaining))


def _wait_for_evaluation_trace_roots(
    trace_rows: list[dict[str, Any]],
    selected_traces: list[Any],
    client: MlflowClient,
) -> None:
    """Refresh rootless chat traces briefly before passing them to MLflow evaluation."""

    def rootless_trace_ids() -> list[str]:
        return [
            str(row.get("trace_id") or row["trace"].info.trace_id)
            for row in trace_rows
            if row.get("trace") is not None and _root_span(row["trace"]) is None
        ]

    missing_root_ids = rootless_trace_ids()
    if not missing_root_ids:
        return

    deadline = time.monotonic() + _TRACE_ROOT_VISIBILITY_WAIT_SECONDS
    LOGGER.info(
        "Waiting up to %ds for root spans on %d chat trace(s): %s",
        _TRACE_ROOT_VISIBILITY_WAIT_SECONDS,
        len(missing_root_ids),
        ", ".join(missing_root_ids),
    )
    refreshed_by_id: dict[str, Any] = {}
    while missing_root_ids:
        for trace_id in missing_root_ids:
            try:
                refreshed_by_id[trace_id] = client.get_trace(trace_id, display=False)
            except MlflowException as exc:
                LOGGER.debug(
                    "Could not refresh chat trace %s while waiting for its root span (%s)",
                    trace_id,
                    type(exc).__name__,
                )

        for row in trace_rows:
            trace_id = str(row.get("trace_id") or "")
            refreshed = refreshed_by_id.get(trace_id)
            if refreshed is None:
                continue
            row["trace"] = refreshed

        for index, trace in enumerate(selected_traces):
            refreshed = refreshed_by_id.get(str(trace.info.trace_id))
            if refreshed is not None:
                selected_traces[index] = refreshed

        missing_root_ids = rootless_trace_ids()
        if not missing_root_ids:
            LOGGER.info("All evaluated chat traces now have root spans")
            return

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(_TRACE_VISIBILITY_POLL_SECONDS, remaining))

    LOGGER.warning(
        "Proceeding with %d chat trace(s) still missing root spans after waiting %ds: %s. "
        "Evaluation inputs and outputs are available separately.",
        len(missing_root_ids),
        _TRACE_ROOT_VISIBILITY_WAIT_SECONDS,
        ", ".join(missing_root_ids),
    )


def _is_transient_judge_connection_error(error: BaseException) -> bool:
    """Recognize connection drops that can succeed on a later judge attempt."""
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    transient_markers = (
        "remote end closed connection without response",
        "connection aborted",
        "connection reset",
        "read timed out",
    )

    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, (ConnectionError, TimeoutError, RemoteDisconnected)):
            return True
        module = type(current).__module__
        exception_name = type(current).__name__.casefold()
        if module.startswith(("requests.", "urllib3.")) and exception_name in {
            "connectionerror",
            "timeout",
            "protocolerror",
            "readtimeouterror",
            "newconnectionerror",
        }:
            return True
        if any(marker in str(current).casefold() for marker in transient_markers):
            return True
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        if current.__context__ is not None:
            pending.append(current.__context__)
    return False


def _build_scorers(judge_model: str, judge_endpoint: str) -> list[Any]:
    def judge(name: str, instructions: str) -> Any:
        judge_scorer = make_judge(
            name=name,
            instructions=instructions,
            model=judge_model,
            base_url=judge_endpoint,
            feedback_value_type=Literal["yes", "no"],
            inference_params={"temperature": 0},
        )

        @scorer(name=name)
        def judge_with_transient_retries(
            *,
            inputs: Any = None,
            outputs: Any = None,
            expectations: dict[str, Any] | None = None,
            trace: Any = None,
        ):
            source_inputs = inputs if isinstance(inputs, dict) else {}
            judge_inputs: Any = None
            judge_outputs = outputs
            judge_expectations = None

            if name == "correctness":
                expected_facts = (expectations or {}).get("expected_facts", [])
                if not expected_facts:
                    raise EvaluationError(
                        "Correctness cannot be evaluated because this row has no expected facts."
                    )
                judge_expectations = {"expected_facts": expected_facts}
                judge_inputs = {
                    key: source_inputs[key]
                    for key in ("question", "scenario_id", "disruption", "category")
                    if key in source_inputs
                }
            elif name in {"retrieval_relevance", "retrieval_groundedness"}:
                if source_inputs.get("knowledge_base_required") is not True:
                    # An absent assessment keeps the applicable yes/no values typed as
                    # binary in MLflow, so its table can render Pass/Fail and rationale.
                    return None

                # Keep retrieval judges focused on the evidence sources they
                # are meant to score, instead of passing unrelated trace data.
                judge_inputs = {
                    "question": source_inputs.get("question"),
                    "knowledge_base_required": source_inputs.get(
                        "knowledge_base_required"
                    ),
                    "knowledge_base_context": source_inputs.get(
                        "knowledge_base_context"
                    ),
                    "knowledge_base_expected_facts": source_inputs.get(
                        "knowledge_base_expected_facts"
                    ),
                }
                if name == "retrieval_groundedness":
                    judge_inputs["impact_snapshot"] = _compact_impact_snapshot(
                        source_inputs.get("impact_snapshot")
                    )
                else:
                    judge_outputs = None
            elif name == "disruption_grounding":
                if source_inputs.get("category") in {
                    "knowledge_base_retrieval",
                    "news_retrieval",
                }:
                    return None
                kb_required = source_inputs.get("knowledge_base_required") is True
                kb_context = (
                    source_inputs.get("knowledge_base_context") if kb_required else ""
                )
                kb_context = kb_context if isinstance(kb_context, str) else ""
                kb_expected_facts = (
                    source_inputs.get("knowledge_base_expected_facts")
                    if kb_required
                    else []
                )
                kb_expected_facts = (
                    kb_expected_facts if isinstance(kb_expected_facts, list) else []
                )
                judge_inputs = {
                    "question": source_inputs.get("question"),
                    "scenario_id": source_inputs.get("scenario_id"),
                    "disruption": source_inputs.get("disruption"),
                    "knowledge_base_required": kb_required,
                    "knowledge_base_context": kb_context[:_JUDGE_KB_CONTEXT_LIMIT],
                    "knowledge_base_expected_facts": kb_expected_facts,
                    "impact_snapshot": _compact_impact_snapshot(
                        source_inputs.get("impact_snapshot"),
                        include_mitigation_options=True,
                    ),
                }

            for attempt in range(_JUDGE_TRANSIENT_RETRIES + 1):
                try:
                    result = judge_scorer(
                        inputs=judge_inputs,
                        outputs=judge_outputs,
                        expectations=judge_expectations,
                        # Keep the judge assessment linked to its source trace in MLflow.
                        # The prompt uses only the compact inputs above; it does not
                        # interpolate {{trace}}, so the full trace is not sent as context.
                        trace=trace,
                    )
                    if attempt:
                        LOGGER.info(
                            "Judge scorer %s succeeded on retry %d/%d",
                            name,
                            attempt,
                            _JUDGE_TRANSIENT_RETRIES,
                        )
                    return result
                except Exception as exc:
                    if not _is_transient_judge_connection_error(exc):
                        raise
                    if attempt >= _JUDGE_TRANSIENT_RETRIES:
                        LOGGER.error(
                            "Judge scorer %s failed after %d retries: %s",
                            name,
                            attempt,
                            exc,
                        )
                        raise
                    delay = _JUDGE_RETRY_DELAYS_SECONDS[attempt]
                    LOGGER.warning(
                        "Judge scorer %s hit a transient connection error; "
                        "retry %d/%d in %.1fs: %s",
                        name,
                        attempt + 1,
                        _JUDGE_TRANSIENT_RETRIES,
                        delay,
                        exc,
                    )
                    if delay:
                        time.sleep(delay)

        return judge_with_transient_retries

    scorers = [
        judge(
            "correctness",
            "Check whether the assistant answer in {{outputs}} supports every fact in "
            "the expected_facts list from {{expectations}}. Treat the question in {{inputs}} "
            "as context: do not require the answer to repeat facts already stated in the "
            "question. Judge semantic support rather than exact wording, and credit an "
            "explicitly named recommendation even when the answer paraphrases it. "
            "When an expected fact says 'either' or 'one or more', accept any listed option; "
            "do not require every option. "
            "Do not require benefits or causal explanations that are not part of an expected fact. "
            "Before returning no, verify that each failed fact is truly absent or contradicted; "
            "do not call a named recommendation missing merely because its benefit is not "
            "restated. "
            "Compare numeric values by magnitude, accepting equivalent formats "
            "such as 3.1e+06 and 3,100,000. Affected entity selection and numeric values "
            "are checked separately; do not require a predetermined subset of affected IDs. "
            "Use only supplied expectations and inputs, and do not fill gaps with outside "
            "knowledge. Return yes only when all applicable expected facts are supported; "
            "otherwise return no.",
        ),
        judge(
            "retrieval_relevance",
            "Assess only the question, knowledge_base_context, and "
            "knowledge_base_expected_facts in {{inputs}}. Ignore the answer and any "
            "impact-snapshot facts. Return yes when the retrieved knowledge-base context "
            "contains useful evidence for the expected knowledge-base facts; return no "
            "when the context is empty or unrelated. Do not judge answer correctness or "
            "whether impact data is present in the knowledge base.",
        ),
        judge(
            "retrieval_groundedness",
            "Assess the answer in {{outputs}} using the two supplied evidence sources in "
            "{{inputs}}. Compare claims about knowledge-base facts, especially those in "
            "knowledge_base_expected_facts or attributed to the knowledge base, only against "
            "knowledge_base_context. Compare affected entities and numeric impact claims "
            "against impact_snapshot; do not fail those claims merely because they are absent "
            "from the knowledge-base context. Return no only for a KB-specific claim that is "
            "unsupported or contradicted by the retrieved KB context, or an impact claim that "
            "contradicts the impact snapshot. Otherwise return yes. Do not use outside knowledge.",
        ),
        judge(
            name="disruption_grounding",
            instructions=(
                "Assess whether the answer in {{outputs}} is grounded in the named disruption "
                "and the supplied evidence in {{inputs}}. Use impact_snapshot as the source for "
                "affected entities, impact values, and scenario-specific diversion results. When "
                "knowledge_base_required is true, verify KB guidance and planning facts against "
                "knowledge_base_context. Use knowledge_base_expected_facts only to identify the "
                "relevant KB facts; they are not evidence by themselves. "
                "Do not reject a fact merely because it appears in one source but not the other. "
                "Treat advice phrased as something operators should verify as a recommendation, "
                "not as a claim that the condition is currently true. Fail only when the answer "
                "states a concrete impact or KB fact that contradicts or is unsupported by its "
                "corresponding supplied source, or presents an assumption as an observed current "
                "condition. If a source does not establish a detail, the answer should identify "
                "it as needing verification or say it is unavailable. Return yes when these "
                "conditions are met and no otherwise."
            ),
        ),
        answer_is_non_empty,
        no_cross_scenario_leakage,
        expected_impact_value_mentioned,
        highest_value_entity_named,
        expected_tool_used,
    ]

    LOGGER.info(
        "Adding MLflow built-in relevance, safety, and retrieval judges using "
        "the configured MaaS model and endpoint"
    )
    scorers.extend(_make_builtin_judge_scorers(judge_model))

    return scorers


def _make_builtin_judge_scorers(model_uri: str) -> list[Any]:
    """Wrap MLflow's built-in judges for the configured endpoint and retry policy."""
    relevance_judge = RelevanceToQuery(
        name="builtin_relevance_to_query", model=model_uri
    )
    safety_judge = Safety(name="builtin_safety", model=model_uri)
    retrieval_sufficiency_judge = RetrievalSufficiency(
        name="builtin_retrieval_sufficiency", model=model_uri
    )
    retrieval_relevance_judge = RetrievalRelevance(
        name="builtin_retrieval_relevance", model=model_uri
    )
    retrieval_groundedness_judge = RetrievalGroundedness(
        name="builtin_retrieval_groundedness", model=model_uri
    )

    @scorer(name="builtin_relevance_to_query")
    def builtin_relevance_to_query(*, inputs: Any = None, outputs: Any = None):
        source_inputs = inputs if isinstance(inputs, dict) else {}
        question = source_inputs.get("question")
        judge_inputs = {"question": question} if question else inputs
        return _invoke_builtin_judge_with_retries(
            "builtin_relevance_to_query",
            lambda: relevance_judge(inputs=judge_inputs, outputs=outputs),
        )

    @scorer(name="builtin_safety")
    def builtin_safety(*, outputs: Any = None):
        return _invoke_builtin_judge_with_retries(
            "builtin_safety",
            lambda: safety_judge(outputs=outputs),
        )

    @scorer(name="builtin_retrieval_sufficiency")
    def builtin_retrieval_sufficiency(
        *,
        inputs: Any = None,
        expectations: dict[str, Any] | None = None,
        trace: Any = None,
    ):
        source_inputs = inputs if isinstance(inputs, dict) else {}
        if source_inputs.get("knowledge_base_required") is not True:
            return None
        kb_facts = source_inputs.get("knowledge_base_expected_facts") or []
        if not kb_facts:
            return Feedback(
                value="no",
                rationale=(
                    "This turn requires knowledge-base retrieval, but no expected KB facts "
                    "are configured for the sufficiency check."
                ),
            )
        feedbacks = _invoke_builtin_judge_with_retries(
            "builtin_retrieval_sufficiency",
            lambda: retrieval_sufficiency_judge(
                trace=trace,
                expectations={"expected_facts": kb_facts},
            ),
        )
        return _aggregate_builtin_retrieval_feedback(
            "builtin_retrieval_sufficiency",
            feedbacks,
            empty_rationale="No retriever context was available to assess KB sufficiency.",
        )

    @scorer(name="builtin_retrieval_relevance")
    def builtin_retrieval_relevance(*, inputs: Any = None, trace: Any = None):
        source_inputs = inputs if isinstance(inputs, dict) else {}
        if source_inputs.get("knowledge_base_required") is not True:
            return None
        feedbacks = _invoke_builtin_judge_with_retries(
            "builtin_retrieval_relevance",
            lambda: retrieval_relevance_judge(trace=trace),
        )
        return _aggregate_builtin_retrieval_feedback(
            "builtin_retrieval_relevance",
            feedbacks,
            empty_rationale="No retrieved KB chunks were available to assess relevance.",
        )

    @scorer(name="builtin_retrieval_groundedness")
    def builtin_retrieval_groundedness(*, inputs: Any = None, trace: Any = None):
        source_inputs = inputs if isinstance(inputs, dict) else {}
        if (
            source_inputs.get("knowledge_base_required") is not True
            or source_inputs.get("category") != "knowledge_base_retrieval"
        ):
            # This built-in judge checks the whole answer against only the retriever
            # context. Mixed impact/KB questions use the source-aware custom judge instead.
            return None
        feedbacks = _invoke_builtin_judge_with_retries(
            "builtin_retrieval_groundedness",
            lambda: retrieval_groundedness_judge(trace=trace),
        )
        return _aggregate_builtin_retrieval_feedback(
            "builtin_retrieval_groundedness",
            feedbacks,
            empty_rationale="No retrieved KB context was available to assess groundedness.",
        )

    return [
        builtin_relevance_to_query,
        builtin_safety,
        builtin_retrieval_sufficiency,
        builtin_retrieval_relevance,
        builtin_retrieval_groundedness,
    ]


def _aggregate_builtin_retrieval_feedback(
    scorer_name: str,
    feedbacks: Any,
    *,
    empty_rationale: str,
) -> Feedback:
    """Combine a built-in retrieval judge's span/chunk feedback into one row score."""
    if isinstance(feedbacks, Feedback):
        feedbacks = [feedbacks]
    if not isinstance(feedbacks, (list, tuple)) or not feedbacks:
        return Feedback(value="no", rationale=empty_rationale)

    details: list[str] = []
    span_ids: set[str] = set()
    passed = True
    for feedback in feedbacks:
        value = getattr(feedback, "value", None)
        if isinstance(value, str):
            item_passed = value.strip().casefold() in {"yes", "true", "pass", "passed"}
        else:
            try:
                item_passed = math.isfinite(float(value)) and float(value) == 1.0
            except (TypeError, ValueError):
                item_passed = False
        passed = passed and item_passed
        label = getattr(feedback, "name", None) or scorer_name
        rationale = getattr(feedback, "rationale", None) or "No rationale returned."
        details.append(f"{label}: {value}; {rationale}")
        span_id = getattr(feedback, "span_id", None)
        if span_id:
            span_ids.add(str(span_id))

    result = Feedback(
        value="yes" if passed else "no",
        rationale=(
            f"MLflow's built-in {scorer_name} judge assessed {len(feedbacks)} retrieval result(s). "
            + " ".join(details)
        ),
    )
    if len(span_ids) == 1:
        result.span_id = next(iter(span_ids))
    return result


def _invoke_builtin_judge_with_retries(name: str, invoke: Any) -> Any:
    """Apply the evaluator's transient-connection retry policy to a built-in judge call."""
    for attempt in range(_JUDGE_TRANSIENT_RETRIES + 1):
        try:
            result = invoke()
            if attempt:
                LOGGER.info(
                    "Judge scorer %s succeeded on retry %d/%d",
                    name,
                    attempt,
                    _JUDGE_TRANSIENT_RETRIES,
                )
            return result
        except Exception as exc:
            if not _is_transient_judge_connection_error(exc):
                raise
            if attempt >= _JUDGE_TRANSIENT_RETRIES:
                LOGGER.error(
                    "Judge scorer %s failed after %d retries: %s",
                    name,
                    attempt,
                    exc,
                )
                raise
            delay = _JUDGE_RETRY_DELAYS_SECONDS[attempt]
            LOGGER.warning(
                "Judge scorer %s hit a transient connection error; retry %d/%d in %.1fs: %s",
                name,
                attempt + 1,
                _JUDGE_TRANSIENT_RETRIES,
                delay,
                exc,
            )
            if delay:
                time.sleep(delay)

    raise AssertionError("unreachable")


@contextmanager
def _route_builtin_judges_to_endpoint(judge_endpoint: str):
    """Route MLflow 3.13 built-in judges to the configured OpenAI-compatible endpoint.

    These built-in classes don't expose `base_url` consistently. Patch the shared
    invocation aliases used by the built-in judge, scorer, and instructions modules for
    the duration of evaluate(), so the MaaS key is never sent to public OpenAI.
    """
    from unittest.mock import patch

    from mlflow.genai.judges import builtin as builtin_judges
    from mlflow.genai.judges import instructions_judge
    from mlflow.genai.scorers import builtin_scorers

    original_invoke = builtin_judges.invoke_judge_model

    def invoke_with_endpoint(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("base_url") is None:
            kwargs["base_url"] = judge_endpoint
        return original_invoke(*args, **kwargs)

    with (
        patch.object(builtin_judges, "invoke_judge_model", invoke_with_endpoint),
        patch.object(builtin_scorers, "invoke_judge_model", invoke_with_endpoint),
        patch.object(instructions_judge, "invoke_judge_model", invoke_with_endpoint),
    ):
        yield


def _evaluation_failures(results: Any) -> list[str]:
    """Return row-level scorer failures; skipped/not-applicable scores are ignored."""
    result_df = getattr(results, "result_df", None)
    failures: list[str] = []
    evaluated_scores = 0

    def is_missing(value: Any) -> bool:
        if value is None:
            return True
        if type(value).__name__ in {"NAType", "NaTType"}:
            return True
        if isinstance(value, str):
            return value.strip().casefold() in {
                "",
                "null",
                "none",
                "nan",
                "not_applicable",
                "not applicable",
                "n/a",
                "na",
            }
        try:
            return math.isnan(value)
        except (TypeError, ValueError):
            return False

    def score_passed(value: Any) -> bool | None:
        """Return None for skipped scores, otherwise whether the score passed."""
        if is_missing(value):
            return None
        if isinstance(value, bool) or type(value).__name__ == "bool_":
            return bool(value)
        if isinstance(value, (int, float)):
            return math.isfinite(float(value)) and float(value) == 1.0
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"yes", "true", "pass", "passed", "ok"}:
                return True
            if normalized in {"no", "false", "fail", "failed", "error"}:
                return False
            try:
                return float(normalized) == 1.0
            except ValueError:
                return False
        return False

    if result_df is not None and hasattr(result_df, "columns"):
        value_columns = [
            f"{name}/value"
            for name in _EVALUATION_SCORER_NAMES
            if f"{name}/value" in result_df.columns
        ]
        for column in value_columns:
            for row_index, value in enumerate(result_df[column].tolist(), start=1):
                passed = score_passed(value)
                if passed is None:
                    continue
                evaluated_scores += 1
                if not passed:
                    failures.append(f"{column} failed on evaluation row {row_index}")

        error_columns = [
            f"{name}/error"
            for name in _EVALUATION_SCORER_NAMES
            if f"{name}/error" in result_df.columns
        ]
        for column in error_columns:
            for row_index, error in enumerate(result_df[column].tolist(), start=1):
                if not is_missing(error):
                    failures.append(f"{column} on evaluation row {row_index}: {error}")

        # MLflow 3.13 stores scorer invocation failures as error assessments with a
        # null value, rather than in a separate `<scorer>/error` result column.
        # Read those assessments from the trace so they fail the quality gate too.
        current_run_id = getattr(results, "run_id", None)
        if "trace" in result_df.columns:
            for row_index, trace in enumerate(result_df["trace"].tolist(), start=1):
                trace_info = getattr(trace, "info", None)
                for assessment in getattr(trace_info, "assessments", None) or []:
                    scorer_name = getattr(assessment, "name", None)
                    error = getattr(assessment, "error", None)
                    if scorer_name not in _EVALUATION_SCORER_NAMES or error is None:
                        continue
                    assessment_run_id = getattr(assessment, "run_id", None)
                    if (
                        current_run_id
                        and assessment_run_id
                        and assessment_run_id != current_run_id
                    ):
                        continue
                    error_message = getattr(error, "error_message", None) or str(error)
                    failures.append(
                        f"{scorer_name} scorer errored on evaluation row {row_index}: "
                        f"{error_message}"
                    )

    if evaluated_scores == 0 and not failures:
        metrics = getattr(results, "metrics", None) or {}
        scorer_metrics = {
            name: value
            for name, value in metrics.items()
            if str(name).endswith("/mean")
        }
        if scorer_metrics:
            for name, value in scorer_metrics.items():
                passed = score_passed(value)
                if passed is not True:
                    failures.append(
                        f"{name} did not report a perfect pass rate ({value})"
                    )
        else:
            failures.append(
                "No scorer results were available to determine whether evaluation passed"
            )

    return failures


def _evaluation_failure_details(results: Any) -> list[dict[str, Any]]:
    """Collect the failed scorer, question, response, and assessment rationale per row."""
    result_df = getattr(results, "result_df", None)
    if result_df is None or not hasattr(result_df, "iterrows"):
        return []

    def is_missing(value: Any) -> bool:
        if value is None or type(value).__name__ in {"NAType", "NaTType"}:
            return True
        if isinstance(value, str):
            return value.strip().casefold() in {
                "",
                "null",
                "none",
                "nan",
                "not_applicable",
                "not applicable",
                "n/a",
                "na",
            }
        try:
            return math.isnan(value)
        except (TypeError, ValueError):
            return False

    def failed_score(value: Any) -> bool:
        if is_missing(value):
            return False
        if isinstance(value, bool) or type(value).__name__ == "bool_":
            return not bool(value)
        if isinstance(value, (int, float)):
            return not math.isfinite(float(value)) or float(value) != 1.0
        if isinstance(value, str):
            normalized = value.strip().casefold()
            if normalized in {"no", "false", "fail", "failed", "error"}:
                return True
            if normalized in {"yes", "true", "pass", "passed", "ok"}:
                return False
            try:
                return float(normalized) != 1.0
            except ValueError:
                return True
        return True

    def assessment_field(assessment: Any, field: str) -> Any:
        if isinstance(assessment, dict):
            value = assessment.get(field)
            if value is None and field in {"value", "rationale"}:
                feedback = assessment.get("feedback")
                if isinstance(feedback, dict):
                    value = feedback.get(field)
            return value
        return getattr(assessment, field, None)

    def request_question(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        request = _as_mapping(value)
        question = request.get("question")
        if isinstance(question, str) and question.strip():
            return question.strip()
        messages = request.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    question = _content_text(message.get("content"))
                    if question:
                        return question
        return ""

    def response_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        response = _as_mapping(value)
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            choice = _as_mapping(choices[0])
            message = _as_mapping(choice.get("message"))
            content = _content_text(message.get("content"))
            if content:
                return content
        return _content_text(response.get("content"))

    current_run_id = getattr(results, "run_id", None)
    failure_details: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()

    for row_index, (_, row) in enumerate(result_df.iterrows(), start=1):
        trace = row.get("trace")
        trace_info = getattr(trace, "info", None)
        assessments = list(getattr(trace_info, "assessments", None) or [])
        row_assessments = row.get("assessments")
        if isinstance(row_assessments, list):
            assessments.extend(row_assessments)

        request = row.get("inputs")
        if is_missing(request):
            request = row.get("request")
        question = request_question(request)
        response = row.get("outputs")
        if is_missing(response):
            response = row.get("response")
        response = response_text(response)

        if not question and trace is not None:
            root_span = _root_span(trace)
            if root_span is not None:
                question = request_question(root_span.inputs)
                if not response:
                    response = response_text(root_span.outputs)

        row_trace_id = row.get("trace_id")
        if is_missing(row_trace_id) and trace_info is not None:
            row_trace_id = getattr(trace_info, "trace_id", None)

        def add_failure(
            scorer_name: str,
            score: Any,
            error: Any = None,
            *,
            row_index: int,
            assessments: list[Any],
            row_trace_id: Any,
            question: str,
            response: str,
        ) -> None:
            key = (row_index, scorer_name, str(error or "score"))
            if key in seen:
                return
            seen.add(key)

            matching_assessments = []
            for assessment in assessments:
                name = assessment_field(assessment, "name")
                if not name and isinstance(assessment, dict):
                    name = assessment.get("assessment_name")
                if name != scorer_name:
                    continue
                assessment_run_id = assessment_field(assessment, "run_id")
                if (
                    current_run_id
                    and assessment_run_id
                    and assessment_run_id != current_run_id
                ):
                    continue
                matching_assessments.append(assessment)

            rationale = next(
                (
                    assessment_field(assessment, "rationale")
                    for assessment in reversed(matching_assessments)
                    if assessment_field(assessment, "rationale")
                ),
                None,
            )
            assessment_error = next(
                (
                    assessment_field(assessment, "error")
                    for assessment in reversed(matching_assessments)
                    if assessment_field(assessment, "error")
                ),
                None,
            )
            error_text = error
            if error_text is None and assessment_error is not None:
                error_text = (
                    getattr(assessment_error, "error_message", None)
                    or _as_mapping(assessment_error).get("error_message")
                    or str(assessment_error)
                )
            analysis = str(rationale).strip() if rationale else ""
            if not analysis and error_text is not None:
                analysis = f"Scorer error: {error_text}"
            if not analysis:
                analysis = "No judge or scorer rationale was recorded for this failure."

            failure_details.append(
                {
                    "row": row_index,
                    "trace_id": str(row_trace_id or ""),
                    "scorer": scorer_name,
                    "score": "error"
                    if error is not None or assessment_error is not None
                    else str(score),
                    "question": question
                    or "Question unavailable in the evaluation result.",
                    "response": response
                    or "Response unavailable in the evaluation result.",
                    "analysis": analysis,
                }
            )

        for scorer_name in _EVALUATION_SCORER_NAMES:
            value_column = f"{scorer_name}/value"
            if value_column in result_df.columns:
                value = row.get(value_column)
                if failed_score(value):
                    add_failure(
                        scorer_name,
                        value,
                        row_index=row_index,
                        assessments=assessments,
                        row_trace_id=row_trace_id,
                        question=question,
                        response=response,
                    )

            error_column = f"{scorer_name}/error"
            if error_column in result_df.columns:
                error = row.get(error_column)
                if not is_missing(error):
                    add_failure(
                        scorer_name,
                        "error",
                        error,
                        row_index=row_index,
                        assessments=assessments,
                        row_trace_id=row_trace_id,
                        question=question,
                        response=response,
                    )

        for assessment in assessments:
            scorer_name = assessment_field(assessment, "name")
            if not scorer_name and isinstance(assessment, dict):
                scorer_name = assessment.get("assessment_name")
            error = assessment_field(assessment, "error")
            assessment_run_id = assessment_field(assessment, "run_id")
            if (
                scorer_name in _EVALUATION_SCORER_NAMES
                and error is not None
                and not (
                    current_run_id
                    and assessment_run_id
                    and assessment_run_id != current_run_id
                )
            ):
                error_text = (
                    getattr(error, "error_message", None)
                    or _as_mapping(error).get("error_message")
                    or str(error)
                )
                add_failure(
                    scorer_name,
                    "error",
                    error_text,
                    row_index=row_index,
                    assessments=assessments,
                    row_trace_id=row_trace_id,
                    question=question,
                    response=response,
                )

    return failure_details


def _format_evaluation_failure_report(
    failure_details: list[dict[str, Any]],
    scorer_failures: list[str],
) -> str:
    """Render detailed scorer failures for console logs and the MLflow artifact."""

    def block(label: str, value: Any) -> str:
        content = str(value or "")
        fence = "```"
        while fence in content:
            fence += "`"
        return f"**{label}**\n{fence}text\n{content}\n{fence}"

    lines = ["# Evaluation failures", ""]
    if failure_details:
        lines.append(f"{len(failure_details)} scorer failure(s):")
        lines.append("")
        for index, failure in enumerate(failure_details, start=1):
            trace_suffix = (
                f" — trace `{failure['trace_id']}`" if failure["trace_id"] else ""
            )
            lines.extend(
                [
                    f"## {index}. `{failure['scorer']}` — row {failure['row']}{trace_suffix}",
                    f"Score: `{failure['score']}`",
                    "",
                    block("Question", failure["question"]),
                    "",
                    block("Response", failure["response"]),
                    "",
                    block("Judge / scorer analysis", failure["analysis"]),
                    "",
                ]
            )
    else:
        lines.extend(["No row-level details were available.", ""])
    if scorer_failures:
        lines.extend(["## Failure summary", ""])
        lines.extend(f"- {failure}" for failure in scorer_failures)
    return "\n".join(lines).rstrip() + "\n"


def _find_saved_evaluation_rows(
    output_dir: Path, source_run_id: str | None
) -> tuple[Path, str]:
    if source_run_id:
        rows_path = output_dir / source_run_id / "evaluation-rows.jsonl"
        if not rows_path.is_file():
            raise EvaluationError(
                f"Saved evaluation rows not found for source run {source_run_id}: {rows_path}"
            )
        return rows_path, source_run_id

    candidates = list(output_dir.glob("*/evaluation-rows.jsonl"))
    if not candidates:
        raise EvaluationError(
            f"No saved evaluation rows found under {output_dir}. Run make run-eval first, "
            "or set EVAL_SOURCE_RUN_ID to a run with local evaluation artifacts."
        )
    rows_path = max(candidates, key=lambda path: path.stat().st_mtime)
    return rows_path, rows_path.parent.name


def _normalize_saved_row_expectations(row: dict[str, Any]) -> None:
    """Migrate saved rows to current expectations and source-aware checks."""
    inputs = row.get("inputs") if isinstance(row.get("inputs"), dict) else {}
    expectations = row.get("expectations")
    if not isinstance(expectations, dict):
        return

    # The general news question accepts either registered news source. Apply
    # this migration to saved rows as well as new dataset rows so judge-only
    # reruns use the same tool-selection contract.
    if (
        inputs.get("scenario_id") == "supply-chain-port-strike-la"
        and inputs.get("category") == "news_retrieval"
        and expectations.get("expected_tool") == "news_knowledge_base"
    ):
        accepted_news_tools = ["news_knowledge_base", "fetch_news"]
        expectations["expected_tools"] = accepted_news_tools
        inputs["expected_tools"] = accepted_news_tools

    # Older rows required a carrier schedule-recovery fact that the Suez question
    # did not ask for. Keep judge-only reruns aligned with the corrected dataset.
    old_suez_fact = (
        "The knowledge base says pre-planned Cape routings and bunker hedges "
        "help carriers recover schedules faster."
    )
    current_suez_fact = (
        "The knowledge base says multi-source suppliers, such as near-shore or "
        "Mediterranean alternatives, reduce exposure to reliance on a single "
        "Asia-Europe sea lane."
    )
    is_suez_evidence_row = (
        inputs.get("scenario_id") == "supply-chain-suez-blockage"
        and inputs.get("category") == "evidence_and_mitigation"
    )
    is_port_scenario = inputs.get("scenario_id") == "supply-chain-port-strike-la"
    is_port_evidence_row = (
        is_port_scenario and inputs.get("category") == "evidence_and_mitigation"
    )
    kb_expected_facts = inputs.get("knowledge_base_expected_facts")
    if isinstance(kb_expected_facts, list):
        if is_suez_evidence_row:
            inputs["knowledge_base_expected_facts"] = [
                _SUEZ_MIXED_EXPECTATION_MIGRATIONS.get(fact, fact)
                if isinstance(fact, str)
                else fact
                for fact in kb_expected_facts
                if fact != current_suez_fact
            ]
        elif is_port_scenario:
            inputs["knowledge_base_expected_facts"] = [
                _PORT_KB_EXPECTATION_MIGRATIONS.get(fact, fact)
                if isinstance(fact, str)
                else fact
                for fact in kb_expected_facts
                if not (is_port_evidence_row and fact == _PORT_RESILIENCE_KB_FACT)
            ]
        else:
            inputs["knowledge_base_expected_facts"] = [
                current_suez_fact if fact == old_suez_fact else fact
                for fact in kb_expected_facts
            ]

    expectations.pop("expected_entity_ids", None)
    expectations.pop("allowed_entity_ids", None)

    scenario = inputs.get("disruption")
    scenario_fact = f"The active disruption is {scenario}." if scenario else None
    expected_facts = expectations.get("expected_facts")
    if not isinstance(expected_facts, list):
        expected_facts = []
    if is_suez_evidence_row:
        expected_facts = [
            _SUEZ_MIXED_EXPECTATION_MIGRATIONS.get(fact, fact)
            if isinstance(fact, str)
            else fact
            for fact in expected_facts
            if fact != current_suez_fact
        ]
    if is_port_scenario:
        expected_facts = [
            _PORT_KB_EXPECTATION_MIGRATIONS.get(fact, fact)
            if isinstance(fact, str)
            else fact
            for fact in expected_facts
            if not (is_port_evidence_row and fact == _PORT_RESILIENCE_KB_FACT)
        ]

    if inputs.get("category") == "evidence_and_mitigation":
        # Older mixed-source Port Strike rows required broad resilience measures
        # that the route-choice question did not ask for. Those facts are now
        # checked by the dedicated knowledge-base resilience question.
        if inputs.get("scenario_id") == "supply-chain-port-strike-la":
            expected_facts = [
                fact for fact in expected_facts if fact != _PORT_RESILIENCE_KB_FACT
            ]
            existing_kb_facts = inputs.get("knowledge_base_expected_facts")
            if isinstance(existing_kb_facts, list):
                inputs["knowledge_base_expected_facts"] = [
                    fact
                    for fact in existing_kb_facts
                    if fact != _PORT_RESILIENCE_KB_FACT
                ]

        mixed_source_kb_facts = _MIXED_SOURCE_KB_EXPECTED_FACTS.get(
            str(inputs.get("scenario_id"))
        )
        if mixed_source_kb_facts:
            inputs["knowledge_base_required"] = True
            existing_kb_facts = inputs.get("knowledge_base_expected_facts")
            if not isinstance(existing_kb_facts, list):
                existing_kb_facts = []
            inputs["knowledge_base_expected_facts"] = list(
                dict.fromkeys([*existing_kb_facts, *mixed_source_kb_facts])
            )
            expected_facts.extend(
                fact for fact in mixed_source_kb_facts if fact not in expected_facts
            )

    normalized_facts: list[str] = []
    has_total_value_fact = False
    has_top_entity_fact = False
    expected_value = expectations.get("expected_value")
    expected_currency = str(expectations.get("expected_currency") or "USD")
    expected_top_entity = expectations.get("expected_top_entity_id")
    for fact in expected_facts:
        if not isinstance(fact, str):
            continue
        if fact == old_suez_fact:
            fact = (
                _SUEZ_MIXED_EXPECTATION_MIGRATIONS[fact]
                if is_suez_evidence_row
                else current_suez_fact
            )
        if scenario_fact and fact == scenario_fact:
            continue
        if fact.startswith("The impact snapshot lists these affected entity IDs:"):
            continue
        if (
            fact.startswith("Total value at risk is ")
            and expectations.get("expected_value") is not None
        ):
            normalized_facts.append(
                f"Total value at risk is {expected_value} {expected_currency}."
            )
            has_total_value_fact = True
            continue
        if (
            fact.startswith("The highest value-breakdown entity is ")
            and expected_top_entity
        ):
            value_suffix = (
                f", with a value of {expected_value} {expected_currency}"
                if expected_value is not None
                else ""
            )
            normalized_facts.append(
                f"The highest value-breakdown entity is {expected_top_entity}{value_suffix}."
            )
            has_top_entity_fact = True
            continue
        normalized_facts.append(fact)

    # Older saved rows omitted these positive facts because deterministic checks
    # covered the same values. Keep custom correctness active on judge-only reruns.
    if (
        inputs.get("category") == "impact_summary"
        and expected_value is not None
        and not has_total_value_fact
    ):
        normalized_facts.append(
            f"Total value at risk is {expected_value} {expected_currency}."
        )
    if expected_top_entity and not has_top_entity_fact:
        if expected_value is not None:
            normalized_facts.append(
                f"The highest value-breakdown entity is {expected_top_entity}, with a value of "
                f"{expected_value} {expected_currency}."
            )
        else:
            normalized_facts.append(
                f"The highest value-breakdown entity is {expected_top_entity}."
            )
    expectations["expected_facts"] = normalized_facts


def _load_saved_evaluation_rows(rows_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with rows_path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("inputs"), dict):
                    raise EvaluationError(
                        f"Saved evaluation row {line_number} in {rows_path} is missing inputs."
                    )
                if "outputs" not in row:
                    raise EvaluationError(
                        f"Saved evaluation row {line_number} in {rows_path} is missing outputs."
                    )
                _normalize_saved_row_expectations(row)
                rows.append(row)
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(
            f"Could not read saved evaluation rows from {rows_path}: {exc}"
        ) from exc
    if not rows:
        raise EvaluationError(f"Saved evaluation rows file is empty: {rows_path}")
    return rows


def _create_judge_rerun_traces(
    rows: list[dict[str, Any]], client: MlflowClient, source_run_id: str
) -> int:
    """Create run-scoped traces for saved answers, linked to their source traces."""
    created = 0
    for row in rows:
        inputs = row.get("inputs", {})
        source_trace_id = inputs.get("agent_trace_id")
        source_root = None
        if source_trace_id:
            try:
                source_root = _root_span(client.get_trace(str(source_trace_id)))
            except MlflowException as exc:
                LOGGER.warning(
                    "Could not load source trace %s for the judge-only rerun (%s); "
                    "the evaluation trace will retain its source ID without a span link",
                    source_trace_id,
                    type(exc).__name__,
                )

        with mlflow.start_span(
            name="saved_answer_for_judge_rerun",
            span_type=SpanType.CHAIN,
        ) as span:
            question = str(inputs.get("question") or "")
            span.set_inputs({"messages": [{"role": "user", "content": question}]})
            span.set_attribute("evaluation.kind", "judge-only-rerun")
            span.set_attribute("evaluation.source_run_id", source_run_id)
            if source_trace_id:
                span.set_attribute("evaluation.source_trace_id", str(source_trace_id))
            if source_root is not None:
                span.add_link(
                    Link(
                        trace_id=str(source_trace_id),
                        span_id=source_root.span_id,
                        attributes={"relationship": "source_application_trace"},
                    )
                )
            if inputs.get("knowledge_base_required") is True:
                context = inputs.get("knowledge_base_context")
                context = context if isinstance(context, str) else ""
                with mlflow.start_span(
                    name="knowledge_base.search.saved_for_eval",
                    span_type=SpanType.RETRIEVER,
                ) as retrieval_span:
                    retrieval_span.set_inputs(
                        {
                            "query": question,
                            "vector_store_id": inputs.get("vector_store_id"),
                        }
                    )
                    retrieval_span.set_outputs(
                        [
                            {
                                "page_content": context,
                                "metadata": {
                                    "vector_store_id": inputs.get("vector_store_id")
                                },
                            }
                        ]
                        if context.strip()
                        else []
                    )
            span.set_outputs(row.get("outputs"))
            evaluation_trace_id = span.trace_id

        if not evaluation_trace_id:
            raise EvaluationError(
                "MLflow did not create a trace for a saved answer; cannot isolate rerun scores."
            )
        created += 1
        try:
            client.set_trace_tag(
                evaluation_trace_id,
                "evaluation.kind",
                "judge-only-rerun",
            )
            client.set_trace_tag(
                evaluation_trace_id,
                "evaluation.source_run_id",
                source_run_id,
            )
            if source_trace_id:
                client.set_trace_tag(
                    evaluation_trace_id,
                    "evaluation.source_trace_id",
                    str(source_trace_id),
                )
        except MlflowException as exc:
            LOGGER.warning(
                "Could not tag evaluation trace %s with source metadata (%s)",
                evaluation_trace_id,
                type(exc).__name__,
            )

        try:
            row["trace"] = client.get_trace(
                evaluation_trace_id,
                display=False,
                flush=True,
            )
        except Exception as exc:
            raise EvaluationError(
                f"Could not load run-scoped evaluation trace {evaluation_trace_id}: {exc}"
            ) from exc
    return created


def _rerun_saved_evaluation(
    args: argparse.Namespace,
    judge_model: str,
    judge_endpoint: str,
) -> int:
    rows_path, source_run_id = _find_saved_evaluation_rows(
        args.output_dir, args.source_run_id
    )
    evaluation_rows = _load_saved_evaluation_rows(rows_path)
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    client = MlflowClient()
    try:
        source_run = client.get_run(source_run_id)
    except Exception as exc:
        raise EvaluationError(
            f"Could not find source MLflow run {source_run_id!r}; saved rows are at {rows_path}."
        ) from exc

    source_scenario_ids = sorted(
        {
            str(row["inputs"].get("scenario_id"))
            for row in evaluation_rows
            if row["inputs"].get("scenario_id")
        }
    )
    source_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"judge-rerun-{source_run_id[:8]}-{source_stamp}"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with mlflow.start_run(
        experiment_id=source_run.info.experiment_id,
        run_name=run_name,
    ) as active_run:
        mlflow.set_tags(
            {
                "evaluation.kind": "judge-only-rerun",
                "evaluation.status": "running",
                "evaluation.source_run_id": source_run_id,
                "evaluation.answer_source": "saved_evaluation_rows",
                "evaluation.judge_model": judge_model,
                "evaluation.scenario_ids": ",".join(source_scenario_ids),
            }
        )
        mlflow.log_params(
            {
                "source_run_id": source_run_id,
                "source_rows_file": rows_path.name,
                "evaluation_row_count": len(evaluation_rows),
                "judge_model": judge_model,
            }
        )
        evaluation_trace_count = _create_judge_rerun_traces(
            evaluation_rows, client, source_run_id
        )
        LOGGER.info(
            "Created %d/%d run-scoped evaluation traces from saved answers",
            evaluation_trace_count,
            len(evaluation_rows),
        )
        LOGGER.info(
            "Re-evaluating %d saved answers from %s without launching Playwright or making app requests",
            len(evaluation_rows),
            source_run_id,
        )
        with _route_builtin_judges_to_endpoint(judge_endpoint):
            results = mlflow.genai.evaluate(
                data=evaluation_rows,
                scorers=_build_scorers(judge_model, judge_endpoint),
            )
        scorer_failures = _evaluation_failures(results)
        failure_report = None
        if scorer_failures:
            failure_report = _format_evaluation_failure_report(
                _evaluation_failure_details(results),
                scorer_failures,
            )
            LOGGER.error(
                "Evaluation quality gate failed with %d scorer failure(s): %s",
                len(scorer_failures),
                "; ".join(scorer_failures[:10]),
            )
            LOGGER.error("Per-failure details:\n%s", failure_report)

        run_dir = args.output_dir / active_run.info.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        rerun_rows_path = run_dir / "evaluation-rows.jsonl"
        saved_rows = [
            {key: value for key, value in row.items() if key != "trace"}
            for row in evaluation_rows
        ]
        _write_jsonl(rerun_rows_path, saved_rows)
        uploads = [_log_artifact_safely(rerun_rows_path, "evaluation")]
        if failure_report is not None:
            failure_path = run_dir / "failure-details.md"
            failure_path.write_text(failure_report, encoding="utf-8")
            uploads.append(_log_artifact_safely(failure_path, "evaluation"))
        if getattr(results, "result_df", None) is not None:
            scores_path = run_dir / "scored-answers.csv"
            results.result_df.to_csv(scores_path, index=False)
            uploads.append(_log_artifact_safely(scores_path, "evaluation"))
        if getattr(results, "metrics", None) is not None:
            metrics_path = run_dir / "scorer-metrics.json"
            _write_json(metrics_path, results.metrics)
            uploads.append(_log_artifact_safely(metrics_path, "evaluation"))
        mlflow.set_tag(
            "evaluation.artifact_upload_status",
            "uploaded" if all(uploads) else "partial_or_unsupported",
        )
        mlflow.set_tag(
            "evaluation.status",
            "failed" if scorer_failures else "finished",
        )
        if scorer_failures:
            mlflow.set_tag("evaluation.failure_type", "scorer_failures")

    print(f"MLflow experiment ID: {source_run.info.experiment_id}")
    print(f"Source MLflow run ID: {source_run_id}")
    print(f"MLflow run name: {run_name}")
    print(f"MLflow run ID: {active_run.info.run_id}")
    print("Results artifact directory: evaluation/")
    return 1 if scorer_failures else 0


def _judge_chat_endpoint(base_url: str) -> str:
    """Convert the configured OpenAI-compatible API base into MLflow's chat endpoint URL."""
    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise EvaluationError(
            "EVAL_JUDGE_MODEL_URL must be an HTTP(S) OpenAI-compatible API base URL, "
            "for example https://<MaaS-route>/v1."
        )

    path = parsed.path.rstrip("/")
    if path.endswith("/chat/completions"):
        endpoint_path = path
    elif path.endswith("/v1/chat"):
        endpoint_path = f"{path}/completions"
    elif path.endswith("/v1"):
        endpoint_path = f"{path}/chat/completions"
    else:
        endpoint_path = f"{path}/v1/chat/completions"

    return urlunsplit((parsed.scheme, parsed.netloc, endpoint_path, parsed.query, ""))


def _require_configuration(
    args: argparse.Namespace, *, require_ui_url: bool = True
) -> tuple[str, str, str]:
    ui_url = args.ui_url or os.getenv("EVAL_UI_URL", "")
    if require_ui_url and not ui_url:
        raise EvaluationError(
            "Set EVAL_UI_URL to the deployed frontend route or local UI URL."
        )
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
    if not tracking_uri.startswith(("https://", "http://")):
        raise EvaluationError(
            "Set MLFLOW_TRACKING_URI to the OpenShift AI MLflow endpoint. "
            "The runner refuses to silently log to a local file store."
        )
    judge_model = args.judge_model or os.getenv("EVAL_JUDGE_MODEL", "")
    if not judge_model:
        raise EvaluationError(
            "Set EVAL_JUDGE_MODEL to an approved MLflow judge model, e.g. openai:/<model-id>."
        )
    judge_base_url = args.judge_base_url or os.getenv("EVAL_JUDGE_MODEL_URL", "")
    if not judge_base_url:
        raise EvaluationError(
            "Set EVAL_JUDGE_MODEL_URL to the OpenAI-compatible judge API base URL, "
            "for example https://<MaaS-route>/v1. The evaluator will not fall back to public OpenAI."
        )
    return ui_url, judge_model, _judge_chat_endpoint(judge_base_url)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--scenario", action="append", help="Scenario ID to run; may be repeated."
    )
    parser.add_argument("--ui-url", help="Dashboard URL; defaults to EVAL_UI_URL.")
    parser.add_argument(
        "--judge-model", help="Judge model; defaults to EVAL_JUDGE_MODEL."
    )
    parser.add_argument(
        "--judge-base-url",
        help="OpenAI-compatible judge API base URL; defaults to EVAL_JUDGE_MODEL_URL.",
    )
    parser.add_argument(
        "--rerun-eval-only",
        action="store_true",
        help="Re-score saved evaluation rows without launching Playwright or calling the application.",
    )
    parser.add_argument(
        "--source-run-id",
        default=os.getenv("EVAL_SOURCE_RUN_ID"),
        help="Source MLflow run ID; defaults to the newest local saved evaluation rows.",
    )
    parser.add_argument(
        "--experiment",
        default=os.getenv("EVAL_MLFLOW_EXPERIMENT", "supply-chain-disruption-evals"),
    )
    parser.add_argument(
        "--headed", action="store_true", help="Show the Chromium browser window."
    )
    parser.add_argument(
        "--timeout-ms", type=int, default=int(os.getenv("EVAL_UI_TIMEOUT_MS", "180000"))
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(os.getenv("EVAL_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))),
    )
    parser.add_argument(
        "--storage-state",
        type=Path,
        default=Path(os.environ["EVAL_STORAGE_STATE"])
        if os.getenv("EVAL_STORAGE_STATE")
        else None,
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=os.getenv("EVAL_LOG_LEVEL", "INFO"))
    args = _parse_args()
    try:
        ui_url, judge_model, judge_endpoint = _require_configuration(
            args, require_ui_url=not args.rerun_eval_only
        )
        endpoint_parts = urlsplit(judge_endpoint)
        LOGGER.info(
            "Using MLflow judge endpoint %s://%s%s",
            endpoint_parts.scheme,
            endpoint_parts.hostname,
            endpoint_parts.path,
        )
        if args.rerun_eval_only:
            return _rerun_saved_evaluation(args, judge_model, judge_endpoint)

        dataset = _load_dataset(args.dataset)
        scenarios = dataset["scenarios"]
        if args.scenario:
            selected = set(args.scenario)
            scenarios = [
                scenario
                for scenario in scenarios
                if scenario.get("scenario_id") in selected
            ]
            missing = selected - {scenario.get("scenario_id") for scenario in scenarios}
            if missing:
                raise EvaluationError(
                    f"Scenario IDs not found in dataset: {', '.join(sorted(missing))}"
                )
        if not scenarios:
            raise EvaluationError("No scenarios selected.")

        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
        mlflow.set_experiment(args.experiment)
        commit = os.getenv("GIT_COMMIT", "unknown")
        run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_name = (
            f"{dataset.get('suite_version', 'disruptions')}-{commit[:8]}-{run_stamp}"
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        captured_scenarios: list[dict[str, Any]] = []
        evaluation_rows: list[dict[str, Any]] = []
        model_trace_objects: list[Any] = []
        backend_trace_session: dict[str, Any] = {}
        capture: BrowserNetworkCapture | None = None

        with mlflow.start_run(run_name=run_name) as active_run:
            mlflow.set_tags(
                {
                    "evaluation.kind": "ui-disruption-evaluation",
                    "evaluation.suite_version": str(
                        dataset.get("suite_version", "unknown")
                    ),
                    "evaluation.scenario_ids": ",".join(
                        scenario["scenario_id"] for scenario in scenarios
                    ),
                    "evaluation.commit": commit,
                    "evaluation.judge_model": judge_model,
                    "evaluation.dataset_sha256": _stable_json_sha256(dataset),
                }
            )
            mlflow.log_params(
                {
                    "scenario_count": len(scenarios),
                    "ui_url_host": urlsplit(ui_url).netloc,
                    "dataset_file": args.dataset.name,
                    "judge_model": judge_model,
                }
            )
            try:
                evaluation_started_at_ms = int(time.time() * 1000)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=not args.headed)
                    context_options: dict[str, Any] = {
                        "viewport": {"width": 1920, "height": 1080}
                    }
                    if args.storage_state:
                        if not args.storage_state.is_file():
                            raise EvaluationError(
                                f"Storage state file not found: {args.storage_state}"
                            )
                        context_options["storage_state"] = str(args.storage_state)
                    context = browser.new_context(**context_options)
                    page = context.new_page()
                    capture = BrowserNetworkCapture(page)
                    try:
                        _wait_for_dashboard(page, ui_url, args.timeout_ms)

                        for scenario in scenarios:
                            LOGGER.info(
                                "Evaluating disruption: %s (%s)",
                                scenario["label"],
                                scenario["scenario_id"],
                            )
                            captured, _ = _run_scenario(
                                page, capture, scenario, args.timeout_ms
                            )
                            captured_scenarios.append(captured)
                    except Exception:
                        failure_screenshot = (
                            args.output_dir / f"{active_run.info.run_id}-failure.png"
                        )
                        try:
                            page.screenshot(
                                path=str(failure_screenshot), full_page=True
                            )
                            mlflow.log_artifact(
                                str(failure_screenshot),
                                artifact_path="evaluation/failures",
                            )
                        except Exception:
                            LOGGER.exception("Could not save failure screenshot")
                        raise

                trace_rows, model_trace_objects, backend_trace_session = (
                    _read_and_correlate_backend_traces(
                        args.experiment,
                        evaluation_started_at_ms,
                        captured_scenarios,
                    )
                )
                evaluation_rows = [
                    {
                        "inputs": {
                            **row["inputs"],
                            "agent_trace_id": row["trace_id"],
                            "trace_timestamp_ms": row["trace_timestamp_ms"],
                            "trace_execution_ms": row["trace_execution_ms"],
                            "model_call_span_count": row["model_call_span_count"],
                        },
                        "outputs": row["outputs"],
                        "expectations": row["expectations"],
                        "trace": row["trace"],
                    }
                    for row in trace_rows
                ]
                if not evaluation_rows:
                    raise EvaluationError(
                        "No chat traces with OpenAI model spans were found."
                    )
                mlflow.set_tags(
                    {
                        "evaluation.answer_source": "mlflow_openai_autolog",
                        "evaluation.backend_session_id": backend_trace_session[
                            "backend_session_id"
                        ],
                        "evaluation.backend_started_at_ms": str(
                            backend_trace_session["backend_started_at_ms"]
                        ),
                        "evaluation.backend_startup_trace_id": backend_trace_session[
                            "startup_trace_id"
                        ],
                        "evaluation.started_at_ms": str(
                            backend_trace_session["evaluation_started_at_ms"]
                        ),
                    }
                )
                mlflow.log_param("backend_chat_trace_count", len(model_trace_objects))

                scorer_list = _build_scorers(judge_model, judge_endpoint)
                LOGGER.info(
                    "Scoring %d question/answer pairs from MLflow chat traces",
                    len(evaluation_rows),
                )
                with _route_builtin_judges_to_endpoint(judge_endpoint):
                    results = mlflow.genai.evaluate(
                        data=evaluation_rows, scorers=scorer_list
                    )
                scorer_failures = _evaluation_failures(results)
                failure_report = None
                if scorer_failures:
                    failure_report = _format_evaluation_failure_report(
                        _evaluation_failure_details(results),
                        scorer_failures,
                    )
                    LOGGER.error(
                        "Evaluation quality gate failed with %d scorer failure(s): %s",
                        len(scorer_failures),
                        "; ".join(scorer_failures[:10]),
                    )
                    LOGGER.error("Per-failure details:\n%s", failure_report)

                answers = [
                    interaction
                    for scenario in captured_scenarios
                    for interaction in scenario["interactions"]
                ]
                latencies = [float(answer["latency_ms"]) for answer in answers]
                aggregate_metrics = {
                    "ui_chat_latency_ms_mean": statistics.fmean(latencies),
                    "ui_chat_latency_ms_p50": _percentile(latencies, 0.50),
                    "ui_chat_latency_ms_p95": _percentile(latencies, 0.95),
                    "ui_chat_request_count": len(answers),
                    "ui_chat_error_count": sum(
                        1 for answer in answers if answer["chat_http_status"] >= 400
                    ),
                    "openai_autolog_model_call_span_count": sum(
                        _trace_llm_call_metrics(trace)[0]
                        for trace in model_trace_objects
                    ),
                }
                trace_latencies = [
                    float(row["trace_execution_ms"]) for row in trace_rows
                ]
                if trace_latencies:
                    aggregate_metrics["model_trace_latency_ms_mean"] = statistics.fmean(
                        trace_latencies
                    )
                simulation_entity_counts: list[float] = []
                simulation_values: list[float] = []
                simulation_impact_scores: list[float] = []
                for scenario_result in captured_scenarios:
                    impact = scenario_result["impact_result"]
                    affected = impact.get("affected_entities")
                    simulation_entity_counts.append(
                        float(len(affected)) if isinstance(affected, list) else 0.0
                    )
                    solver = (
                        impact.get("solver")
                        if isinstance(impact.get("solver"), dict)
                        else {}
                    )
                    value_at_risk = _safe_float(solver.get("total_value_at_risk"))
                    impact_score = _safe_float(solver.get("impact_score"))
                    if value_at_risk is not None:
                        simulation_values.append(value_at_risk)
                    if impact_score is not None:
                        simulation_impact_scores.append(impact_score)
                aggregate_metrics["simulation_affected_entities_mean"] = (
                    statistics.fmean(simulation_entity_counts)
                )
                if simulation_values:
                    aggregate_metrics["simulation_value_at_risk_mean"] = (
                        statistics.fmean(simulation_values)
                    )
                if simulation_impact_scores:
                    aggregate_metrics["simulation_impact_score_mean"] = (
                        statistics.fmean(simulation_impact_scores)
                    )
                mlflow.log_metrics(aggregate_metrics)
                mlflow.set_tag(
                    "evaluation.impact_snapshot_hashes",
                    ",".join(
                        f"{scenario['scenario_id']}:{scenario['impact_snapshot_sha256']}"
                        for scenario in captured_scenarios
                    ),
                )

                run_dir = args.output_dir / active_run.info.run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                capture_path = run_dir / "scenario-results.json"
                rows_path = run_dir / "evaluation-rows.jsonl"
                _write_json(capture_path, captured_scenarios)
                _write_jsonl(
                    rows_path,
                    [
                        {key: value for key, value in row.items() if key != "trace"}
                        for row in evaluation_rows
                    ],
                )
                traces_path = run_dir / "openai-autolog-traces.json"
                _write_json(
                    traces_path, [trace.to_dict() for trace in model_trace_objects]
                )
                artifact_uploads = [
                    _log_artifact_safely(capture_path, "evaluation"),
                    _log_artifact_safely(rows_path, "evaluation"),
                    _log_artifact_safely(traces_path, "evaluation"),
                ]
                if failure_report is not None:
                    failure_path = run_dir / "failure-details.md"
                    failure_path.write_text(failure_report, encoding="utf-8")
                    artifact_uploads.append(
                        _log_artifact_safely(failure_path, "evaluation")
                    )
                if getattr(results, "result_df", None) is not None:
                    scores_path = run_dir / "scored-answers.csv"
                    results.result_df.to_csv(scores_path, index=False)
                    artifact_uploads.append(
                        _log_artifact_safely(scores_path, "evaluation")
                    )
                if getattr(results, "metrics", None) is not None:
                    metrics_path = run_dir / "scorer-metrics.json"
                    _write_json(metrics_path, results.metrics)
                    artifact_uploads.append(
                        _log_artifact_safely(metrics_path, "evaluation")
                    )
                mlflow.set_tag(
                    "evaluation.artifact_upload_status",
                    "uploaded" if all(artifact_uploads) else "partial_or_unsupported",
                )
                mlflow.set_tag(
                    "evaluation.status",
                    "failed" if scorer_failures else "finished",
                )
                if scorer_failures:
                    mlflow.set_tag("evaluation.failure_type", "scorer_failures")
            except Exception as exc:
                mlflow.set_tag("evaluation.status", "failed")
                mlflow.set_tag("evaluation.failure_type", type(exc).__name__)
                if capture is not None:
                    diagnostics_path = (
                        args.output_dir
                        / f"{active_run.info.run_id}-browser-requests.json"
                    )
                    try:
                        _write_json(diagnostics_path, capture.snapshot())
                        mlflow.log_artifact(
                            str(diagnostics_path), artifact_path="evaluation/failures"
                        )
                    except Exception:
                        LOGGER.exception("Could not save browser request diagnostics")
                if captured_scenarios:
                    partial_path = (
                        args.output_dir
                        / f"{active_run.info.run_id}-partial-results.json"
                    )
                    try:
                        _write_json(partial_path, captured_scenarios)
                        mlflow.log_artifact(
                            str(partial_path), artifact_path="evaluation/failures"
                        )
                    except Exception:
                        LOGGER.exception("Could not save partial results")
                raise
            print(f"MLflow experiment: {args.experiment}")
            print(f"MLflow run name: {run_name}")
            print(f"MLflow run ID: {active_run.info.run_id}")
            print("Results artifact directory: evaluation/")
        return 1 if scorer_failures else 0
    except (EvaluationError, PlaywrightTimeoutError) as exc:
        LOGGER.error("Evaluation failed: %s", exc)
        return 1
    except Exception:
        LOGGER.exception("Evaluation failed unexpectedly")
        return 1


if __name__ == "__main__":
    sys.exit(main())
