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


# Known-good model/inference-profile IDs valid in ap-southeast-1. Used to reject
# stale session-state values (e.g. from an older model list) that would cause
# "The provided model identifier is invalid" ValidationExceptions.
_VALID_MODEL_IDS = {
    "global.anthropic.claude-haiku-5-5",
    "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "apac.amazon.nova-micro-v1:0",
    "apac.amazon.nova-lite-v1:0",
    "apac.amazon.nova-pro-v1:0",
}
_DEFAULT_JUDGE_MODEL_ID = "global.anthropic.claude-haiku-5-5"


def _get_judge_model_id():
    """Get judge model ID from session state, validated against known-good IDs.

    Falls back to the default if the session value is missing or stale/invalid,
    so a leftover selection from an older model list can't crash evaluations.
    """
    try:
        import streamlit as st
        val = (st.session_state.get("cfg_JUDGE_MODEL_ID", "") or "").strip()
        if val in _VALID_MODEL_IDS:
            return val
    except Exception:
        pass
    return _DEFAULT_JUDGE_MODEL_ID


def _get_max_tokens(default: int = 2048) -> int:
    """Resolve max_tokens from session state (Home page selector), else default."""
    try:
        import streamlit as st
        val = st.session_state.get("cfg_max_tokens", None)
        if val is not None:
            return val
    except Exception:
        pass
    return default


def make_model(purpose: str = "generation", model_id: str | None = None, **overrides) -> BedrockModel:
    """Central factory for Bedrock model instances.

    Resolves the model id with precedence:
      explicit `model_id` arg > session_state (cfg_MODEL_ID for generation,
      cfg_JUDGE_MODEL_ID for judge) > default global.anthropic.claude-haiku-5-5.

    The resolved id is validated against `_VALID_MODEL_IDS`; if it is not in the
    allow-list it falls back to the default (for judge, `_DEFAULT_JUDGE_MODEL_ID`)
    so a stale/invalid selection can't crash model construction.

    `region_name` is always set from the AWS_REGION env var (else ap-southeast-1).
    `max_tokens` honors session_state cfg_max_tokens (default 2048) unless
    overridden. **overrides are merged last, so callers can pass max_tokens,
    cache_tools, etc. `temperature` is NEVER set — claude-haiku-5.x rejects it.
    """
    default_id = _DEFAULT_JUDGE_MODEL_ID if purpose == "judge" else "global.anthropic.claude-haiku-5-5"

    # Resolve the model id by precedence.
    if model_id and model_id.strip():
        resolved = model_id.strip()
    elif purpose == "judge":
        resolved = _get_judge_model_id()
    else:
        resolved = _get_model_id()

    # Validate against the allow-list; fall back to the (purpose-specific) default.
    if resolved not in _VALID_MODEL_IDS:
        resolved = default_id

    kwargs = {
        "model_id": resolved,
        "region_name": os.environ.get("AWS_REGION") or "ap-southeast-1",
        "max_tokens": _get_max_tokens(),
    }
    # Callers may override max_tokens / add cache_tools etc. — merge last.
    kwargs.update(overrides)
    # Hard guarantee: never pass temperature (claude-haiku-5.x rejects it).
    kwargs.pop("temperature", None)

    return BedrockModel(**kwargs)


def get_model():
    """Get the Bedrock model instance (generation purpose)."""
    return make_model("generation")


def create_agent(system_prompt: str, tools: list = None, name: str = None) -> Agent:
    """Create a Strands agent with the given prompt and tools."""
    kwargs = {"model": get_model(), "system_prompt": system_prompt}
    if tools:
        kwargs["tools"] = tools
    if name:
        kwargs["name"] = name
    return Agent(**kwargs)


def _default_metrics() -> dict:
    """Standard metrics dict with all keys present (defaulted to 0) so callers
    can safely use m["inputTokens"] etc. without KeyError."""
    return {
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
        "cacheReadInputTokens": 0,
        "cacheWriteInputTokens": 0,
        "latencyMs": 0,
    }


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
    "\n\n> ⚠ _Response was cut off because this single reply reached the max output tokens "
    "limit. Raise **Max tokens** on the Home page, or ask for a shorter answer._"
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
        metrics = _default_metrics()
        metrics["maxTokensReached"] = True
        return text, metrics

    return str(response), _metrics_from_result(response)


def _metrics_from_result(response) -> dict:
    """Per-turn metrics dict from a Strands AgentResult (defaults when unavailable)."""
    # Always start from defaults so callers can safely use m["inputTokens"] etc.
    metrics = _default_metrics()
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
    return metrics


# Illustrative per-model prices in USD per 1,000 tokens (input, output).
# ESTIMATED, NOT BILLING-ACCURATE — for in-app demonstration only. Real pricing
# depends on region, tier, and current AWS rate cards.
_PRICE_PER_1K = {
    "global.anthropic.claude-haiku-5-5": (0.001, 0.005),
    "global.anthropic.claude-haiku-4-5-20251001-v1:0": (0.001, 0.005),
    "apac.amazon.nova-micro-v1:0": (0.000035, 0.00014),
    "apac.amazon.nova-lite-v1:0": (0.00006, 0.00024),
    "apac.amazon.nova-pro-v1:0": (0.0008, 0.0032),
}
# Fallback rate for unknown model ids (input, output) per 1,000 tokens.
_DEFAULT_PRICE_PER_1K = (0.001, 0.005)


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the USD cost of a turn given token counts.

    Uses an illustrative per-model price table (ESTIMATED, NOT billing-accurate).
    Unknown model ids fall back to a default rate. Always returns a non-negative
    float.
    """
    in_rate, out_rate = _PRICE_PER_1K.get(model_id, _DEFAULT_PRICE_PER_1K)
    in_tok = max(int(input_tokens or 0), 0)
    out_tok = max(int(output_tokens or 0), 0)
    cost = (in_tok / 1000.0) * in_rate + (out_tok / 1000.0) * out_rate
    return max(cost, 0.0)


_STREAM_DONE = object()


def iter_stream_events(runner, message: str):
    """Synchronously iterate the events of ``runner.stream_async(message)``.

    Works for an Agent, Graph or Swarm. Strands only exposes an async stream, and
    Streamlit scripts are synchronous, so the async iterator runs in a background
    thread with its own event loop and events are handed over through a queue.
    The Streamlit script-run context is attached to that thread so Streamlit
    calls made from callbacks still resolve to this session. Exceptions raised
    by the stream (e.g. MaxTokensReachedException) are re-raised here.
    """
    import asyncio
    import queue
    import threading

    events: queue.Queue = queue.Queue()

    def _worker():
        async def _consume():
            async for event in runner.stream_async(message):
                events.put(event)

        try:
            asyncio.run(_consume())
        except BaseException as exc:  # propagate to the consumer thread
            events.put(exc)
        finally:
            events.put(_STREAM_DONE)

    thread = threading.Thread(target=_worker, daemon=True, name="strands-stream")
    try:
        from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
        add_script_run_ctx(thread, get_script_run_ctx())
    except Exception:  # not running under Streamlit
        pass
    thread.start()

    while True:
        item = events.get()
        if item is _STREAM_DONE:
            return
        if isinstance(item, BaseException):
            raise item
        yield item


def chat_stream(agent: Agent, message: str, holder: dict | None = None):
    """Stream a response from the agent. Yields text chunks for st.write_stream.

    If ``holder`` is given, the final AgentResult is stored in ``holder["result"]``
    so callers can read token metrics after the stream ends. Hitting the
    max-tokens limit keeps the text already streamed and appends a short note.
    """
    try:
        from strands.types.exceptions import MaxTokensReachedException
    except Exception:  # pragma: no cover
        MaxTokensReachedException = ()

    try:
        for event in iter_stream_events(agent, message):
            if not isinstance(event, dict):
                continue
            if event.get("data"):
                yield event["data"]
            elif "result" in event and holder is not None:
                holder["result"] = event["result"]
    except MaxTokensReachedException:
        if holder is not None:
            holder["max_tokens"] = True
        yield _MAX_TOKENS_NOTE


def stream_chat(agent: Agent, message: str, waiting_text: str = "Thinking...") -> tuple:
    """Render the agent's reply as a live stream in the current Streamlit container.

    Call inside ``with st.chat_message("assistant"):``. Shows a spinner with
    ``waiting_text`` until the first token arrives (tool calls / routing can take
    a while), then streams the text. Returns ``(text, metrics)``.
    """
    import itertools
    import streamlit as st

    holder: dict = {}
    chunks = chat_stream(agent, message, holder)
    with st.spinner(waiting_text):
        first = next(chunks, None)
    if first is None:
        text = "_(No response.)_"
        st.markdown(text)
    else:
        text = st.write_stream(itertools.chain([first], chunks))
        if not isinstance(text, str):
            text = "".join(str(t) for t in text)

    metrics = _metrics_from_result(holder["result"]) if "result" in holder else _default_metrics()
    if holder.get("max_tokens"):
        metrics["maxTokensReached"] = True
    return text, metrics


def stream_multiagent(runner, message: str, containers: dict, labels: dict | None = None,
                      on_node_start=None) -> tuple:
    """Stream a Graph/Swarm run, rendering each node's text live as it is produced.

    ``containers`` maps node_id -> Streamlit container to render that node into;
    the key ``"*"`` is the fallback for unlisted nodes. ``labels`` maps node_id
    -> heading shown above the node's output. ``on_node_start(node_id)`` is an
    optional hook (e.g. to update a status box). Returns ``(result, texts)``
    where ``texts`` maps node_id -> full streamed text, in execution order.
    """
    labels = labels or {}
    texts: dict = {}
    slots: dict = {}
    result = None
    for event in iter_stream_events(runner, message):
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "multiagent_node_start":
            node = event.get("node_id")
            if on_node_start:
                on_node_start(node)
            box = containers.get(node, containers.get("*"))
            if box is not None:
                if labels.get(node):
                    box.markdown(f"**{labels[node]}**")
                slots[node] = box.empty()
            texts.setdefault(node, "")
        elif kind == "multiagent_node_stream":
            node = event.get("node_id")
            data = (event.get("event") or {}).get("data")
            if data:
                texts[node] = texts.get(node, "") + data
                if node in slots:
                    slots[node].markdown(texts[node] + " ▌")
        elif kind == "multiagent_node_stop":
            node = event.get("node_id")
            if node in slots:
                slots[node].markdown(texts.get(node, "") or "_(no text output)_")
        elif kind == "multiagent_result":
            result = event.get("result")
    for node, slot in slots.items():  # drop any leftover cursor
        slot.markdown(texts.get(node, "") or "_(no text output)_")
    return result, texts
