"""Module 4 telemetry: write agent traces (spans) to CloudWatch Logs and metrics to CloudWatch.

The Streamlit page runs the agent in-process, so nothing reaches CloudWatch unless the page
sends it. ``publish_interaction`` does that after every agent call and returns what happened,
including any error, so the page can show it instead of failing silently.

Span shape matches demos/module4-observability/part1_tracing.py
(Session -> Trace -> Span, root operation ``InvokeAgentRuntime``).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone

REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
DEFAULT_SPANS_LOG_GROUP = "/m4-demo/agent-spans"
DEFAULT_NAMESPACE = "m4-demo/AgentMetrics"


def _cfn_or_default(env_key: str, cfn_key: str, default: str) -> str:
    val = os.environ.get(env_key, "")
    if val:
        return val
    try:
        from agentcore_utils import _get_config
        return _get_config(cfn_key) or default
    except Exception:
        return default


def spans_log_group() -> str:
    return _cfn_or_default("SPANS_LOG_GROUP", "AgentSpansLogGroupName", DEFAULT_SPANS_LOG_GROUP)


def metrics_namespace() -> str:
    return os.environ.get("METRICS_NAMESPACE") or DEFAULT_NAMESPACE


def new_session_id() -> str:
    return f"session-{uuid.uuid4().hex[:12]}"


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class ToolSpanRecorder:
    """Thread-safe collector for tool spans.

    Strands runs tools on a worker thread without a Streamlit script context, so tools must not
    touch st.session_state. A plain list shared by reference is safe to append to from there.
    """

    def __init__(self):
        self.spans: list[dict] = []

    def reset(self):
        self.spans.clear()

    def record(self, operation: str, started: float, attributes: dict | None = None, status: str = "OK", result: dict | None = None):
        self.spans.append({
            "operation": operation,
            "start": started,
            "end": time.time(),
            "attributes": attributes or {},
            "status": status,
            "result": result or {},
        })


def publish_interaction(session_id: str, trace_number: int, prompt: str, started: float, ended: float,
                        metrics: dict, tool_spans: list[dict], status: str = "OK") -> dict:
    """Write one trace (root + model + tool spans) to CloudWatch Logs and the metrics to CloudWatch.

    Returns {"ok" (spans written), "trace_id", "log_group", "spans", "error", "metrics_error"?}.
    """
    import boto3

    group = spans_log_group()
    trace_id = uuid.uuid4().hex
    root_id = uuid.uuid4().hex[:16]
    first_tool_start = min([s["start"] for s in tool_spans], default=started)

    spans = [{
        "session_id": session_id, "trace_id": trace_id, "span_id": root_id, "parent_span_id": None,
        "operation": "InvokeAgentRuntime", "start_time": _iso(started), "end_time": _iso(ended),
        "duration_ms": int((ended - started) * 1000), "status": status,
        "child_span_count": len(tool_spans) + 1, "trace_number": trace_number,
        "attributes": {"prompt_chars": len(prompt)},
    }, {
        "session_id": session_id, "trace_id": trace_id, "span_id": uuid.uuid4().hex[:16], "parent_span_id": root_id,
        "operation": "ModelInvocation", "start_time": _iso(started), "end_time": _iso(ended),
        "duration_ms": int(metrics.get("latencyMs", 0)) or int((ended - started) * 1000), "status": status,
        "attributes": {"input_tokens": metrics.get("inputTokens", 0), "output_tokens": metrics.get("outputTokens", 0),
                       "total_tokens": metrics.get("totalTokens", 0)},
    }]
    for s in tool_spans:
        spans.append({
            "session_id": session_id, "trace_id": trace_id, "span_id": uuid.uuid4().hex[:16], "parent_span_id": root_id,
            "operation": s["operation"], "start_time": _iso(s["start"]), "end_time": _iso(s["end"]),
            "duration_ms": int((s["end"] - s["start"]) * 1000), "status": s["status"],
            "attributes": s["attributes"], "result": s["result"],
        })

    out = {"ok": False, "trace_id": trace_id, "log_group": group, "spans": spans, "error": ""}
    try:
        logs = boto3.client("logs", region_name=REGION)
        stream = f"traces-{session_id}"
        try:
            logs.create_log_stream(logGroupName=group, logStreamName=stream)
        except logs.exceptions.ResourceAlreadyExistsException:
            pass
        base = int(time.time() * 1000)
        events = [{"timestamp": base + i, "message": json.dumps(sp)} for i, sp in enumerate(spans)]
        logs.put_log_events(logGroupName=group, logStreamName=stream, logEvents=events)

        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out
    try:
        _publish_metrics(boto3, session_id, trace_number, started, ended, metrics, len(tool_spans), status)
    except Exception as e:
        out["metrics_error"] = f"{type(e).__name__}: {e}"
    return out


def _publish_metrics(boto3, session_id, trace_number, started, ended, metrics, tool_calls, status):
    latency = float(metrics.get("latencyMs", 0)) or (ended - started) * 1000
    values = [
        ("ResponseLatency", latency, "Milliseconds"),
        ("InputTokens", float(metrics.get("inputTokens", 0)), "Count"),
        ("OutputTokens", float(metrics.get("outputTokens", 0)), "Count"),
        ("TokensUsed", float(metrics.get("totalTokens", 0)), "Count"),
        ("ToolInvocationCount", float(tool_calls), "Count"),
        ("ErrorCount", 0.0 if status == "OK" else 1.0, "Count"),
    ]
    if trace_number == 1:
        values.append(("SessionCount", 1.0, "Count"))
    now = datetime.now(timezone.utc)
    data = []
    for name, value, unit in values:
        # Dimensionless series feed the CloudWatch dashboard; the SessionId series allow per-session drill-down.
        data.append({"MetricName": name, "Value": value, "Unit": unit, "Timestamp": now})
        data.append({"MetricName": name, "Value": value, "Unit": unit, "Timestamp": now,
                     "Dimensions": [{"Name": "SessionId", "Value": session_id}]})
    boto3.client("cloudwatch", region_name=REGION).put_metric_data(Namespace=metrics_namespace(), MetricData=data)
