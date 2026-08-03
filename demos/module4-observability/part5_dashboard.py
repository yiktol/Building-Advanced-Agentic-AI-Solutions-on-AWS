"""
Module 4 - Part 5: End-to-End Observability Dashboard

Combines all signals — tracing, metrics, evaluation, and loop detection —
into a unified observability session. Runs a comprehensive agent workload
and shows how all monitoring components work together.

Shows:
- All metrics emitted in a single session
- CloudWatch Insights queries across all log groups
- Alarm state checking
- Dashboard URL for visual inspection
"""

import os
import json
import time
import uuid
import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
METRICS_NAMESPACE = os.environ.get("METRICS_NAMESPACE", "m4-demo/AgentMetrics")
SPANS_LOG_GROUP = os.environ.get("SPANS_LOG_GROUP", "/m4-demo/agent-spans")
METRICS_LOG_GROUP = os.environ.get("METRICS_LOG_GROUP", "/m4-demo/agent-metrics")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)
logs_client = boto3.client("logs", region_name=REGION)

_session_id = f"e2e-{uuid.uuid4().hex[:8]}"
_metrics_emitted = 0
_spans_emitted = 0


def emit_metric(name: str, value: float, unit: str = "None", dimensions: list = None):
    """Emit metric to CloudWatch."""
    global _metrics_emitted
    try:
        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[{
                "MetricName": name,
                "Value": value,
                "Unit": unit,
                "Timestamp": datetime.utcnow(),
                "Dimensions": dimensions or [{"Name": "SessionId", "Value": _session_id}],
            }],
        )
        _metrics_emitted += 1
    except Exception:
        pass


def emit_span(operation: str, duration_ms: float, status: str = "OK", attrs: dict = None):
    """Emit span to CloudWatch Logs."""
    global _spans_emitted
    span = {
        "session_id": _session_id,
        "trace_id": uuid.uuid4().hex[:32],
        "span_id": uuid.uuid4().hex[:16],
        "operation": operation,
        "duration_ms": duration_ms,
        "status": status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "attributes": attrs or {},
    }

    try:
        stream_name = f"e2e-{_session_id}"
        try:
            logs_client.create_log_stream(logGroupName=SPANS_LOG_GROUP, logStreamName=stream_name)
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass

        logs_client.put_log_events(
            logGroupName=SPANS_LOG_GROUP,
            logStreamName=stream_name,
            logEvents=[{"timestamp": int(time.time() * 1000), "message": json.dumps(span)}],
        )
        _spans_emitted += 1
    except Exception:
        pass


# =============================================================================
# FULLY INSTRUMENTED TOOLS
# =============================================================================

@tool
def lookup_product(name: str) -> str:
    """Look up product information.

    Args:
        name: Product name to search
    """
    start = time.time()
    time.sleep(0.2)
    result = f"{name}: Available, $799, in stock (142 units)"
    elapsed = (time.time() - start) * 1000

    emit_span("ToolCall:lookup_product", elapsed, "OK", {"product": name})
    emit_metric("ToolInvocationCount", 1, "Count", [{"Name": "ToolName", "Value": "lookup_product"}])
    emit_metric("ToolLatency", elapsed, "Milliseconds", [{"Name": "ToolName", "Value": "lookup_product"}])
    return result


@tool
def check_compatibility(product_a: str, product_b: str) -> str:
    """Check if two products are compatible.

    Args:
        product_a: First product
        product_b: Second product
    """
    start = time.time()
    time.sleep(0.15)
    result = f"{product_a} + {product_b}: Compatible via Wi-Fi 6 and Bluetooth 5.0"
    elapsed = (time.time() - start) * 1000

    emit_span("ToolCall:check_compatibility", elapsed, "OK", {"a": product_a, "b": product_b})
    emit_metric("ToolInvocationCount", 1, "Count", [{"Name": "ToolName", "Value": "check_compatibility"}])
    emit_metric("ToolLatency", elapsed, "Milliseconds", [{"Name": "ToolName", "Value": "check_compatibility"}])
    return result


@tool
def process_order(product: str, quantity: int) -> str:
    """Place a product order.

    Args:
        product: Product to order
        quantity: Number of units
    """
    start = time.time()
    time.sleep(0.3)
    order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    result = f"Order {order_id}: {quantity}x {product} — confirmed"
    elapsed = (time.time() - start) * 1000

    emit_span("ToolCall:process_order", elapsed, "OK", {"product": product, "quantity": quantity, "order_id": order_id})
    emit_metric("ToolInvocationCount", 1, "Count", [{"Name": "ToolName", "Value": "process_order"}])
    emit_metric("ToolLatency", elapsed, "Milliseconds", [{"Name": "ToolName", "Value": "process_order"}])
    return result


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a TechMart sales agent. Help customers find products,
check compatibility, and place orders. Use all available tools."""


def run_demo():
    print("=" * 70)
    print("PART 5: End-to-End Observability Dashboard")
    print("=" * 70)
    print()
    print(f"  Session: {_session_id}")
    print(f"  Metrics → {METRICS_NAMESPACE}")
    print(f"  Spans   → {SPANS_LOG_GROUP}")
    print()

    if DASHBOARD_URL:
        print(f"  📊 Dashboard: {DASHBOARD_URL}")
    else:
        print(f"  📊 Dashboard: https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#dashboards:name=m4-demo-agent-observability")
    print()

    print("  Commands:")
    print("    'alarms'  — check CloudWatch alarm states")
    print("    'metrics' — show metrics emitted this session")
    print("    'query'   — run Insights query on spans")
    print("    'quit'    — end session")
    print()
    print("=" * 70)

    # Emit session start
    emit_metric("SessionCount", 1, "Count")
    session_start = time.time()

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[lookup_product, check_compatibility, process_order],
    )

    invocation_count = 0

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "alarms":
            check_alarms()
            continue
        if user_input.lower() == "metrics":
            show_metrics_summary(invocation_count, session_start)
            continue
        if user_input.lower() == "query":
            run_insights_query()
            continue

        invocation_count += 1
        start = time.time()

        # Emit request span
        print()
        response = agent(user_input)
        elapsed = (time.time() - start) * 1000

        # Emit trace-level metrics
        emit_span("InvokeAgentRuntime", elapsed, "OK", {"invocation": invocation_count})
        emit_metric("ResponseLatency", elapsed, "Milliseconds")
        token_est = len(str(response)) // 4 + len(user_input) // 4
        emit_metric("TokensUsed", token_est, "Count")
        emit_metric("SessionDuration", (time.time() - session_start) * 1000, "Milliseconds")

        print(f"\n  Agent: {response}")
        print(f"\n    📊 {elapsed:.0f}ms | ~{token_est} tokens | Metrics: {_metrics_emitted} | Spans: {_spans_emitted}")

    # Final session metrics
    emit_metric("SessionDuration", (time.time() - session_start) * 1000, "Milliseconds")

    print(f"\n{'═' * 70}")
    print(f"  END-TO-END SESSION COMPLETE")
    print(f"{'═' * 70}")
    show_metrics_summary(invocation_count, session_start)
    print()
    print("  View all data in CloudWatch:")
    if DASHBOARD_URL:
        print(f"  📊 {DASHBOARD_URL}")
    print(f"  📋 Logs: {SPANS_LOG_GROUP}")
    print(f"  📈 Metrics: {METRICS_NAMESPACE}")
    print()


def check_alarms():
    """Check current state of all demo alarms."""
    print(f"\n  🚨 ALARM STATUS")
    print(f"  {'─' * 50}")

    alarm_names = [
        "m4-demo-high-latency",
        "m4-demo-high-error-rate",
        "m4-demo-loop-detected",
        "m4-demo-long-session",
        "m4-demo-token-spike",
        "m4-demo-quality-regression",
    ]

    try:
        response = cloudwatch.describe_alarms(AlarmNames=alarm_names)
        alarms = response.get("MetricAlarms", [])

        for alarm in alarms:
            name = alarm["AlarmName"].replace("m4-demo-", "")
            state = alarm["StateValue"]
            icon = {"OK": "🟢", "ALARM": "🔴", "INSUFFICIENT_DATA": "⚪"}.get(state, "❓")
            print(f"    {icon} {name}: {state}")

        if not alarms:
            print("    No alarms found (deploy cfn-alarms.yaml first)")
    except Exception as e:
        print(f"    ⚠️  Could not check alarms: {e}")


def show_metrics_summary(invocations: int, start_time: float):
    """Show metrics emitted this session."""
    duration = time.time() - start_time
    print(f"\n  📊 METRICS SUMMARY ({_session_id})")
    print(f"  {'─' * 50}")
    print(f"  Duration:        {duration:.1f}s")
    print(f"  Invocations:     {invocations}")
    print(f"  Metrics emitted: {_metrics_emitted}")
    print(f"  Spans emitted:   {_spans_emitted}")
    print(f"  Namespace:       {METRICS_NAMESPACE}")


def run_insights_query():
    """Run CloudWatch Insights query on span data."""
    print(f"\n  📋 CloudWatch Insights Query")
    print(f"  {'─' * 50}")

    query = f"""
fields @timestamp, operation, duration_ms, status, session_id
| filter session_id = '{_session_id}'
| sort @timestamp desc
| limit 20
"""
    print(f"  Query: filter session_id = '{_session_id}'")

    try:
        response = logs_client.start_query(
            logGroupName=SPANS_LOG_GROUP,
            startTime=int((time.time() - 3600) * 1000),
            endTime=int(time.time() * 1000),
            queryString=query,
        )
        query_id = response["queryId"]

        print("  Waiting for results...")
        for _ in range(10):
            time.sleep(1)
            result = logs_client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                break

        results = result.get("results", [])
        if results:
            print(f"\n  Results ({len(results)} spans):")
            for row in results[:10]:
                fields = {f["field"]: f["value"] for f in row}
                op = fields.get("operation", "?")
                dur = fields.get("duration_ms", "?")
                status = fields.get("status", "?")
                print(f"    {op:<30} {dur}ms  {status}")
        else:
            print("  No results yet (logs may need time to ingest)")
    except Exception as e:
        print(f"  ⚠️  Query failed: {e}")


if __name__ == "__main__":
    run_demo()
