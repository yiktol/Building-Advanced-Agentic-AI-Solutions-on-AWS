"""Shared agent creation utilities."""

import os
from strands import Agent, tool
from strands.models import BedrockModel

MODEL_ID = os.environ.get("MODEL_ID", "apac.amazon.nova-micro-v1:0")


def _get_model_id():
    """Get model ID from session state (sidebar selector) or env var."""
    try:
        import streamlit as st
        val = st.session_state.get("cfg_MODEL_ID", "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass
    return MODEL_ID


def _get_judge_model_id():
    """Get judge model ID from session state or default to generation model."""
    try:
        import streamlit as st
        val = st.session_state.get("cfg_JUDGE_MODEL_ID", "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass
    return _get_model_id()


def get_model():
    """Get the Bedrock model instance, with guardrail and inference params if configured."""
    from agentcore_utils import get_guardrail_config
    guardrail = get_guardrail_config()
    model_id = _get_model_id()

    # Get inference parameters from session state
    kwargs = {}
    try:
        import streamlit as st
        temp = st.session_state.get("cfg_temperature", None)
        max_tokens = st.session_state.get("cfg_max_tokens", None)
        if temp is not None:
            kwargs["temperature"] = temp
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
    except Exception:
        pass

    if guardrail:
        kwargs.update(guardrail)
    return BedrockModel(model_id=model_id, **kwargs)


def create_agent(system_prompt: str, tools: list = None) -> Agent:
    """Create a Strands agent with the given prompt and tools."""
    kwargs = {"model": get_model(), "system_prompt": system_prompt}
    if tools:
        kwargs["tools"] = tools
    return Agent(**kwargs)


def chat_response(agent: Agent, message: str) -> str:
    """Get a response from the agent and return as string."""
    response = agent(message)
    return str(response)


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
