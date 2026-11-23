"""Client for the deployed TechMart agent on AgentCore Runtime.

Covers the four things the Module 4 page needs from the real service:
  * invoke the runtime and parse its streamed response (text, tool calls, token usage)
  * download that session's OpenTelemetry spans from CloudWatch (``aws/spans`` + runtime logs)
  * run AgentCore Evaluations (on-demand ``Evaluate``) with built-in evaluators
  * read the online evaluation results the service writes to CloudWatch Logs

Runtime and online-eval identifiers come from the CloudFormation outputs of the
``AgentCore-techmartagent-default`` stack (see ``agents/techmartagent``), or from env vars.
"""
from __future__ import annotations

import json
import os
import time
import uuid

REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

# Built-in evaluators and the level they score at.
BUILTIN_EVALUATORS = [
    ("Builtin.Correctness", "TRACE", "Factual accuracy of the response"),
    ("Builtin.Helpfulness", "TRACE", "How useful and actionable the response is"),
    ("Builtin.Coherence", "TRACE", "Logical consistency of the response"),
    ("Builtin.ToolSelectionAccuracy", "TOOL_CALL", "Whether the right tool was chosen"),
    ("Builtin.GoalSuccessRate", "SESSION", "Whether the user's overall goal was achieved"),
]


def _cfg(key: str, env: str = "") -> str:
    val = os.environ.get(env or key, "")
    if val:
        return val
    try:
        from agentcore_utils import _get_config
        return _get_config(key)
    except Exception:
        return ""


def runtime_arn() -> str:
    return _cfg("TechmartRuntimeArn", "TECHMART_RUNTIME_ARN")


def runtime_id() -> str:
    arn = runtime_arn()
    return arn.split("/")[-1] if arn else ""


def online_eval_id() -> str:
    return _cfg("TechmartOnlineEvalId", "TECHMART_ONLINE_EVAL_ID")


def is_configured() -> bool:
    return bool(runtime_arn())


def new_session_id() -> str:
    """Runtime session IDs must be at least 33 characters."""
    return "app-" + uuid.uuid4().hex + uuid.uuid4().hex[:8]


def runtime_log_group() -> str:
    return f"/aws/bedrock-agentcore/runtimes/{runtime_id()}-DEFAULT"


def online_eval_log_group() -> str:
    return f"/aws/bedrock-agentcore/evaluations/results/{online_eval_id()}"


# --------------------------------------------------------------------------- invoke
def invoke_runtime(prompt: str, session_id: str, on_text=None) -> dict:
    """Invoke the runtime and parse the SSE stream.

    Returns {text, tool_calls: [names], usage: {inputTokens, outputTokens, totalTokens},
             latencyMs, modelLatencyMs, session_id}. ``on_text(chunk)`` is called for each text delta.
    """
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    started = time.time()
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn(), runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt}).encode(), qualifier="DEFAULT",
    )
    text, tools = [], []
    usage = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}
    model_ms = 0
    for raw in resp["response"].iter_lines():
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip()).get("event", {})
        except Exception:
            continue
        start = event.get("contentBlockStart", {}).get("start", {})
        if isinstance(start, dict) and "toolUse" in start:
            tools.append(start["toolUse"].get("name", "?"))
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            text.append(delta["text"])
            if on_text:
                on_text(delta["text"])
        meta = event.get("metadata")
        if meta:
            for k in usage:
                usage[k] += int(meta.get("usage", {}).get(k, 0))
            model_ms += int(meta.get("metrics", {}).get("latencyMs", 0))
    return {
        "text": "".join(text), "tool_calls": tools, "usage": usage,
        "latencyMs": int((time.time() - started) * 1000), "modelLatencyMs": model_ms,
        "session_id": session_id,
    }


# --------------------------------------------------------------------------- spans
def _run_insights(logs, group: str, query: str, lookback_min: int = 90) -> list[dict]:
    end = int(time.time())
    qid = logs.start_query(logGroupName=group, startTime=end - lookback_min * 60, endTime=end + 60, queryString=query)["queryId"]
    for _ in range(60):
        res = logs.get_query_results(queryId=qid)
        if res["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
            break
        time.sleep(1)
    if res["status"] != "Complete":
        raise RuntimeError(f"CloudWatch Logs Insights query {res['status']}")
    out = []
    for row in res["results"]:
        for f in row:
            if f["field"] == "@message" and f["value"].strip().startswith("{"):
                try:
                    out.append(json.loads(f["value"]))
                except Exception:
                    pass
    return out


def fetch_session_spans(session_id: str) -> list[dict]:
    """Spans + runtime log records for one session, in the shape the Evaluate API expects."""
    import boto3

    logs = boto3.client("logs", region_name=REGION)
    query = (
        "fields @timestamp, @message "
        "| filter ispresent(scope.name) and ispresent(attributes.session.id) "
        f'| filter attributes.session.id = "{session_id}" '
        "| sort @timestamp asc | limit 10000"
    )
    spans = _run_insights(logs, "aws/spans", query)
    try:
        spans += _run_insights(logs, runtime_log_group(), query)
    except Exception:
        pass  # the runtime log group only adds the gen_ai message events; spans alone can still be scored
    return spans


def spans_ready(spans: list[dict]) -> bool:
    """True once the agent's own spans are present.

    Records for a session can arrive in pieces: the runtime service span and log records may land
    before the Strands agent spans. Evaluate rejects input without model/agent invocation spans
    ("Provided input has no spans to evaluate"), so wait for an invoke_agent span and a chat span.
    """
    names = [str(s.get("name", "")) for s in spans if "spanId" in s and "kind" in s]
    return any(n.startswith("invoke_agent") for n in names) and any(n.startswith("chat") for n in names)


def wait_for_spans(session_id: str, timeout_s: int = 300, interval_s: int = 15, on_tick=None) -> list[dict]:
    """Poll until the session's agent spans are in CloudWatch and the count has stopped growing.

    Ingestion usually takes 1 to 3 minutes. Returns whatever was found when the timeout expires
    (check ``spans_ready`` on the result).
    """
    deadline = time.time() + timeout_s
    spans: list[dict] = []
    last = -1
    while time.time() < deadline:
        spans = fetch_session_spans(session_id)
        if on_tick:
            on_tick(len(spans))
        if spans_ready(spans) and len(spans) == last:
            return spans  # complete: agent spans present and nothing new since the last poll
        last = len(spans) if spans_ready(spans) else -1
        time.sleep(interval_s)
    return spans


# --------------------------------------------------------------------------- evaluate
def evaluate(spans: list[dict], evaluator_ids: list[str]) -> list[dict]:
    """Run on-demand AgentCore evaluations. One row per evaluator result."""
    import boto3

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    rows = []
    for ev in evaluator_ids:
        try:
            r = client.evaluate(evaluatorId=ev, evaluationInput={"sessionSpans": spans})
        except Exception as e:
            rows.append({"evaluator": ev, "value": None, "label": "", "explanation": "", "error": f"{type(e).__name__}: {e}"})
            continue
        for x in r.get("evaluationResults", []):
            ctx = x.get("context", {}).get("spanContext", {})
            rows.append({
                "evaluator": ev, "value": x.get("value"), "label": x.get("label", ""),
                "explanation": x.get("explanation", ""), "trace_id": ctx.get("traceId", ""),
                "span_id": ctx.get("spanId", ""), "error": x.get("errorMessage", ""),
                "tokens": x.get("tokenUsage", {}).get("totalTokens", 0),
            })
    return rows


# --------------------------------------------------------------------------- online evaluation
def fetch_online_results(session_id: str, lookback_min: int = 240) -> list[dict]:
    """Online evaluation results for one session, as {evaluator, value, label, explanation}.

    Uses FilterLogEvents rather than Logs Insights so freshly written results are visible at once.
    """
    import boto3

    if not online_eval_id():
        return []
    logs = boto3.client("logs", region_name=REGION)
    kwargs = {
        "logGroupName": online_eval_log_group(),
        "filterPattern": f'"{session_id}"',
        "startTime": int((time.time() - lookback_min * 60) * 1000),
    }
    rows = []
    try:
        while True:
            page = logs.filter_log_events(**kwargs)
            for ev in page.get("events", []):
                try:
                    rec = json.loads(ev["message"])
                except Exception:
                    continue
                a = rec.get("attributes", {})
                if a.get("session.id") != session_id:
                    continue
                rows.append({
                    "evaluator": a.get("gen_ai.evaluation.name", ""),
                    "value": a.get("gen_ai.evaluation.score.value"),
                    "label": a.get("gen_ai.evaluation.score.label", ""),
                    "explanation": a.get("gen_ai.evaluation.explanation", ""),
                    "trace_id": a.get("trace.id", rec.get("traceId", "")),
                })
            if not page.get("nextToken"):
                break
            kwargs["nextToken"] = page["nextToken"]
    except logs.exceptions.ResourceNotFoundException:
        return []  # the results log group is created on the first evaluation
    return rows
