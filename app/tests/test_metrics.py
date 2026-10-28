"""Offline tests for the metrics defaults and cost estimation helpers."""

import pytest

import agent_utils

_EXPECTED_METRIC_KEYS = {
    "inputTokens",
    "outputTokens",
    "totalTokens",
    "cacheReadInputTokens",
    "cacheWriteInputTokens",
    "latencyMs",
}


def test_default_metrics_has_all_keys():
    metrics = agent_utils._default_metrics()
    assert _EXPECTED_METRIC_KEYS.issubset(set(metrics))


def test_estimate_cost_non_negative_for_known_ids():
    for model_id in agent_utils._VALID_MODEL_IDS:
        cost = agent_utils.estimate_cost(model_id, 1000, 500)
        assert isinstance(cost, float)
        assert cost >= 0


def test_estimate_cost_non_negative_for_unknown_id():
    cost = agent_utils.estimate_cost("some-unknown-model", 1000, 500)
    assert isinstance(cost, float)
    assert cost >= 0


@pytest.mark.live
def test_chat_response_live_returns_text():
    # Live Bedrock round-trip; skipped offline. Asserts a non-empty response.
    agent = agent_utils.create_agent("You are a helpful assistant. Answer briefly.")
    resp = agent_utils.chat_response(agent, "Say hello in one word.")
    assert isinstance(resp, str)
    assert resp.strip()
