"""Shared agent creation utilities."""

import os
from strands import Agent, tool
from strands.models import BedrockModel

MODEL_ID = os.environ.get("MODEL_ID", "global.anthropic.claude-haiku-5-5")


def _get_model_id():
    """Get model ID from session state (sidebar selector) or env var."""
    try:
        import streamlit as st
        val = st.session_state.get("cfg_MODEL_ID", "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass
    return MODEL_ID or "global.anthropic.claude-haiku-5-5"


def _get_judge_model_id():
    """Get judge model ID from session state or default to nova pro."""
    try:
        import streamlit as st
        val = st.session_state.get("cfg_JUDGE_MODEL_ID", "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass
    return "apac.amazon.nova-pro-v1:0"


def get_model():
    """Get the Bedrock model instance."""
    model_id = "global.anthropic.claude-haiku-5-5"

    # Try to get from session state (Home page selector)
    try:
        import streamlit as st
        val = st.session_state.get("cfg_MODEL_ID", "")
        if val and val.strip():
            model_id = val.strip()
    except Exception:
        pass

    # Note: `temperature` is intentionally not passed. Claude Haiku 5.x (the
    # default) deprecated it and rejects it with a ValidationException.
    kwargs = {"max_tokens": 2048, "region_name": "ap-southeast-1"}
    try:
        import streamlit as st
        max_tokens = st.session_state.get("cfg_max_tokens", None)
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
    except Exception:
        pass

    return BedrockModel(model_id=model_id, **kwargs)


def create_agent(system_prompt: str, tools: list = None, name: str = None) -> Agent:
    """Create a Strands agent with the given prompt and tools."""
    kwargs = {"model": get_model(), "system_prompt": system_prompt}
    if tools:
        kwargs["tools"] = tools
    if name:
        kwargs["name"] = name
    return Agent(**kwargs)


def _partial_text_from_agent(agent: Agent) -> str:
    """Recover the partial assistant text Strands appended before hitting the
    max-tokens limit. Returns '' if nothing usable is found."""
    try:
        for msg in reversed(getattr(agent, "messages", []) or []):
            if msg.get("role") != "assistant":
                continue
            parts = [c.get("text", "") for c in msg.get("content", []) if isinstance(c, dict) and c.get("text")]
            if parts:
                return "".join(parts)
    except Exception:
        pass
    return ""


_MAX_TOKENS_NOTE = (
    "\n\n> ⚠️ _Response was cut off because it hit the max-tokens limit. "
    "This is expected in this demo as the context grows — raise **Max tokens** "
    "on the Home page, or start a new conversation._"
)


def chat_response(agent: Agent, message: str) -> str:
    """Get a response from the agent and return as string.

    Gracefully handles the max-tokens limit (common in the context-growth demos)
    by returning the partial text instead of raising.
    """
    try:
        from strands.types.exceptions import MaxTokensReachedException
    except Exception:  # pragma: no cover
        MaxTokensReachedException = ()

    try:
        response = agent(message)
        return str(response)
    except MaxTokensReachedException:
        partial = _partial_text_from_agent(agent)
        return (partial or "_(No output before the token limit was reached.)_") + _MAX_TOKENS_NOTE


def chat_response_with_metrics(agent: Agent, message: str) -> tuple:
    """Get a response from the agent and return (text, metrics_dict).

    metrics_dict contains: inputTokens, outputTokens, totalTokens, latencyMs,
    cacheReadInputTokens, cacheWriteInputTokens

    Gracefully handles the max-tokens limit by returning the partial text.
    """
    try:
        from strands.types.exceptions import MaxTokensReachedException
    except Exception:  # pragma: no cover
        MaxTokensReachedException = ()

    try:
        response = agent(message)
    except MaxTokensReachedException:
        partial = _partial_text_from_agent(agent)
        text = (partial or "_(No output before the token limit was reached.)_") + _MAX_TOKENS_NOTE
        return text, {"maxTokensReached": True}

    text = str(response)
    metrics = {}
    try:
        # Get per-turn metrics from the last invocation (not accumulated across all turns)
        invocations = response.metrics.agent_invocations
        if invocations:
            last_invocation = invocations[-1]
            usage = last_invocation.usage
        else:
            usage = response.metrics.accumulated_usage
        metrics["inputTokens"] = usage.get("inputTokens", 0)
        metrics["outputTokens"] = usage.get("outputTokens", 0)
        metrics["totalTokens"] = usage.get("totalTokens", 0)
        metrics["cacheReadInputTokens"] = usage.get("cacheReadInputTokens", 0)
        metrics["cacheWriteInputTokens"] = usage.get("cacheWriteInputTokens", 0)
        acc_metrics = response.metrics.accumulated_metrics
        metrics["latencyMs"] = acc_metrics.get("latencyMs", 0)
    except Exception:
        pass
    return text, metrics


def chat_stream(agent: Agent, message: str):
    """Stream a response from the agent. Yields text chunks for st.write_stream."""
    try:
        for event in agent.stream(message):
            if "data" in event:
                yield event["data"]
    except (AttributeError, TypeError):
        # Fallback: if streaming not supported, yield full response
        response = agent(message)
        yield str(response)
