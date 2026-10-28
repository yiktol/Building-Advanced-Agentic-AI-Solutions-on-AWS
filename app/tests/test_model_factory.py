"""Offline smoke tests for the Bedrock model factory (agent_utils.make_model).

BedrockModel construction is offline-safe (no network until the model is
invoked), so these run without AWS.
"""

import agent_utils


def test_make_model_generation_returns_bedrockmodel():
    model = agent_utils.make_model("generation")
    assert type(model).__name__ == "BedrockModel"


def test_make_model_judge_returns_bedrockmodel():
    model = agent_utils.make_model("judge")
    assert type(model).__name__ == "BedrockModel"


def test_make_model_bogus_id_falls_back():
    # A bogus explicit id must not raise; the factory falls back to a valid id.
    model = agent_utils.make_model("generation", model_id="bogus-id")
    assert type(model).__name__ == "BedrockModel"


def test_make_model_never_passes_temperature(monkeypatch):
    # claude-haiku-5.x rejects the temperature param — the factory must never
    # forward it, even when a caller passes it as an override.
    captured = {}

    def fake_bedrockmodel(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(agent_utils, "BedrockModel", fake_bedrockmodel)

    agent_utils.make_model("generation", temperature=0.7)
    assert "temperature" not in captured
    # Sanity: the resolved id stays in the allow-list.
    assert captured.get("model_id") in agent_utils._VALID_MODEL_IDS


def test_judge_model_id_in_allow_list():
    assert agent_utils._get_judge_model_id() in agent_utils._VALID_MODEL_IDS
