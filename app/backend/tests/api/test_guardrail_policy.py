"""``GuardrailPolicy`` word-boundary keyword matching."""

from services.guardrail_policy import GuardrailPolicy


def test_blocks_whole_word_match():
    policy = GuardrailPolicy()
    assert policy.is_blocked("Do you know a good pizza place?") is True


def test_does_not_match_substring_of_unrelated_word():
    """Regression for suggestions.md M5: "pizza" must not match "pizzazz"."""
    policy = GuardrailPolicy()
    assert policy.is_blocked("This dashboard has a lot of pizzazz!") is False


def test_does_not_match_supply_chain_terms_containing_keyword_substrings():
    policy = GuardrailPolicy()
    assert policy.is_blocked("What's the seafood export tariff risk?") is False


def test_allows_on_topic_query():
    policy = GuardrailPolicy()
    assert policy.is_blocked("What is the current inventory level?") is False


def test_blocked_response_shape():
    policy = GuardrailPolicy()
    out = policy.blocked_response()
    assert out["completion"] is None
    assert "supply chain" in out["answer"].lower()
