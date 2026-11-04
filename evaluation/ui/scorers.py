"""MLflow scorers for disruption-context chat answers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from mlflow.entities import Feedback
from mlflow.genai import scorer

_NUMBER_WITH_SCALE = re.compile(
    r"(?<![\w.])(?:USD\s*|[$€£])?\s*"
    r"(-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*"
    r"(thousand|million|billion|[KMB])?"
    r"(?:\s*(?:USD|EUR|GBP))?(?!\w)",
    re.IGNORECASE,
)

_SCALE = {
    "": Decimal(1),
    "k": Decimal(1_000),
    "thousand": Decimal(1_000),
    "m": Decimal(1_000_000),
    "million": Decimal(1_000_000),
    "b": Decimal(1_000_000_000),
    "billion": Decimal(1_000_000_000),
}


def _as_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _numbers_in(text: str) -> list[Decimal]:
    values: list[Decimal] = []
    for number, scale in _NUMBER_WITH_SCALE.findall(text or ""):
        parsed = _as_decimal(number)
        if parsed is not None:
            values.append(parsed * _SCALE[scale.casefold()])
    return values


@scorer
def answer_is_non_empty(*, outputs: Any) -> Feedback:
    answer = outputs if isinstance(outputs, str) else str(outputs or "")
    passed = bool(answer.strip())
    return Feedback(
        value=passed,
        rationale="The assistant returned an answer."
        if passed
        else "The assistant returned no answer.",
    )


@scorer
def no_cross_scenario_leakage(
    *, outputs: Any, expectations: dict[str, Any] | None
) -> Feedback:
    answer = outputs if isinstance(outputs, str) else str(outputs or "")
    forbidden = (expectations or {}).get("forbidden_terms", [])
    matches = [
        term for term in forbidden if term and term.casefold() in answer.casefold()
    ]
    passed = not matches
    rationale = (
        "No terms from another disruption scenario were found."
        if passed
        else f"Answer contains terms associated with another scenario: {', '.join(matches)}."
    )
    return Feedback(value=passed, rationale=rationale)


@scorer
def expected_impact_value_mentioned(
    *, outputs: Any, expectations: dict[str, Any] | None
) -> Feedback | None:
    expected = _as_decimal((expectations or {}).get("expected_value"))
    if expected is None:
        return None
    answer = outputs if isinstance(outputs, str) else str(outputs or "")
    candidates = _numbers_in(answer)
    tolerance = max(abs(expected) * Decimal("0.0001"), Decimal("0.01"))
    matched = any(abs(candidate - expected) <= tolerance for candidate in candidates)
    expected_currency = str((expectations or {}).get("expected_currency") or "").upper()
    currency_present = (
        not expected_currency
        or expected_currency in answer.upper()
        or {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
        }.get(expected_currency, "")
        in answer
    )
    passed = matched and currency_present
    return Feedback(
        value=passed,
        rationale=(
            f"The answer includes the expected value {expected} {expected_currency}."
            if passed
            else f"Expected {expected} {expected_currency}; parsed answer values were {candidates}."
        ),
    )


@scorer
def highest_value_entity_named(
    *, outputs: Any, expectations: dict[str, Any] | None
) -> Feedback | None:
    expected = (expectations or {}).get("expected_top_entity_id")
    if not expected:
        return Feedback(
            value="not_applicable",
            rationale="The impact snapshot has no positive entity value breakdown.",
        )
    answer = outputs if isinstance(outputs, str) else str(outputs or "")
    passed = str(expected).casefold() in answer.casefold()
    return Feedback(
        value=passed,
        rationale=(
            f"The answer names the highest-value entity {expected}."
            if passed
            else f"The expected highest-value entity {expected} was not named."
        ),
    )


@scorer
def expected_tool_used(
    *, inputs: Any, expectations: dict[str, Any] | None
) -> Feedback | None:
    expected = (expectations or {}).get("expected_tools") or (
        expectations or {}
    ).get("expected_tool")
    if not expected:
        return Feedback(
            value="not_applicable",
            rationale="This turn does not require a specific tool.",
        )
    expected_tools = (
        [str(tool) for tool in expected if str(tool).strip()]
        if isinstance(expected, (list, tuple, set))
        else [str(expected)]
    )
    expected_tools = [tool.strip() for tool in expected_tools if tool.strip()]
    if not expected_tools:
        return Feedback(
            value="not_applicable",
            rationale="This turn does not require a specific tool.",
        )
    source_inputs = inputs if isinstance(inputs, dict) else {}
    used = str(source_inputs.get("tool_used") or "").strip()
    passed = used in expected_tools
    expected_label = (
        expected_tools[0]
        if len(expected_tools) == 1
        else "one of " + ", ".join(expected_tools)
    )
    if passed and len(expected_tools) == 1:
        rationale = f"The assistant used the expected tool: {used}."
    elif passed:
        rationale = f"The assistant used accepted tool {used} (expected {expected_label})."
    else:
        rationale = (
            f"Expected the assistant to use {expected_label}; "
            f"observed tool: {used or 'none'}."
        )
    return Feedback(
        value=passed,
        rationale=rationale,
    )
