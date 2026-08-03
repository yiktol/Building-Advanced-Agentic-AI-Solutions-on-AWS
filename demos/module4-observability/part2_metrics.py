"""
Module 4 - Part 2: Custom CloudWatch Metrics and Dashboards

Publishes real-time custom metrics for agent performance to CloudWatch.
Metrics include latency, token usage, tool invocations, and error rates.

Shows:
- Custom metric emission via CloudWatch PutMetricData
- Real-time dashboard updates
- Metric dimensions for filtering (by tool, session, etc.)
"""

import os
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

cloudwatch = boto3.client("cloudwatch", region_name=REGION)

# Session tracking
_session_id = f"session-{uuid.uuid4().hex[:8]}"
_session_start = time.time()
_invocation_count = 0
_total_tokens = 0
_tool_calls = 0
_errors = 0


def publish_metric(metric_name: str, value: float, unit: str = "None", dimensions: list = None):
    """Publish a metric to CloudWatch."""
    metric_data = {
        "MetricName": metric_name,
        "Value": value,
        "Unit": unit,
        "Timestamp": datetime.utcnow(),
        "Dimensions": dimensions or [{"Name": "SessionId", "Value": _session_id}],
    }

    try:
        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=[metric_data],
        )
    except Exception as e:
        print(f"    ⚠️  Metric publish failed: {e}")


def publish_batch_metrics(metrics: list):
    """Publish multiple metrics at once."""
    metric_data = []
    for m in metrics:
        metric_data.append({
            "MetricName": m["name"],
            "Value": m["value"],
            "Unit": m.get("unit", "None"),
            "Timestamp": datetime.utcnow(),
            "Dimensions": m.get("dimensions", [{"Name": "SessionId", "Value": _session_id}]),
        })

    try:
        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=metric_data,
        )
    except Exception as e:
        print(f"    ⚠️  Batch metric publish failed: {e}")


# =============================================================================
# INSTRUMENTED TOOLS
# =============================================================================

@tool
def search_products(query: str) -> str:
    """Search product catalog.

    Args:
        query: Product search query
    """
    global _tool_calls
    _tool_calls += 1

    start = time.time()
    # Simulate search
    time.sleep(0.2)
    result = f"Found: TechMart Pro 15 ($799), TechMart Air ($599), TechMart Hub ($149)"
    elapsed = (time.time() - start) * 1000

    publish_metric("ToolInvocationCount", 1, "Count", [
        {"Name": "ToolName", "Value": "search_products"},
    ])
    publish_metric("ToolLatency", elapsed, "Milliseconds", [
        {"Name": "ToolName", "Value": "search_products"},
    ])

    print(f"    📊 [Metric] search_products: {elapsed:.0f}ms")
    return result


@tool
def check_inventory(product_id: str) -> str:
    """Check product inventory levels.

    Args:
        product_id: Product to check
    """
    global _tool_calls
    _tool_calls += 1

    start = time.time()
    time.sleep(0.15)
    result = f"{product_id}: 142 units in stock, 23 reserved, 119 available"
    elapsed = (time.time() - start) * 1000

    publish_metric("ToolInvocationCount", 1, "Count", [
        {"Name": "ToolName", "Value": "check_inventory"},
    ])
    publish_metric("ToolLatency", elapsed, "Milliseconds", [
        {"Name": "ToolName", "Value": "check_inventory"},
    ])

    print(f"    📊 [Metric] check_inventory: {elapsed:.0f}ms")
    return result


@tool
def place_order(product: str, quantity: int) -> str:
    """Place an order for a product.

    Args:
        product: Product name
        quantity: Number of units
    """
    global _tool_calls
    _tool_calls += 1

    start = time.time()
    time.sleep(0.3)
    order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    result = f"Order {order_id} placed: {quantity}x {product}"
    elapsed = (time.time() - start) * 1000

    publish_metric("ToolInvocationCount", 1, "Count", [
        {"Name": "ToolName", "Value": "place_order"},
    ])
    publish_metric("ToolLatency", elapsed, "Milliseconds", [
        {"Name": "ToolName", "Value": "place_order"},
    ])

    print(f"    📊 [Metric] place_order: {elapsed:.0f}ms")
    return result


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a product sales agent for TechMart.
Help customers find products, check availability, and place orders.
Use tools for all lookups — never guess inventory or availability.
"""


def run_demo():
    global _invocation_count, _total_tokens, _errors

    print("=" * 70)
    print("PART 2: Custom CloudWatch Metrics")
    print("=" * 70)
    print()
    print(f"  Namespace: {METRICS_NAMESPACE}")
    print(f"  Session:   {_session_id}")
    print()
    print("  Metrics published on every interaction:")
    print("    • ResponseLatency (ms)")
    print("    • TokensUsed / InputTokens / OutputTokens")
    print("    • ToolInvocationCount (per tool)")
    print("    • ToolLatency (per tool)")
    print("    • SessionDuration (ms)")
    print("    • ErrorCount")
    print()
    print("  Type 'stats' to see session metrics.")
    print("  Type 'dashboard' to get the dashboard URL.")
    print("  Type 'quit' to end.")
    print("=" * 70)

    # Publish session start
    publish_metric("SessionCount", 1, "Count")

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_products, check_inventory, place_order],
    )

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "stats":
            show_stats()
            continue

        if user_input.lower() == "dashboard":
            url = os.environ.get("DASHBOARD_URL", f"https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}#dashboards:name=m4-demo-agent-observability")
            print(f"\n  📊 Dashboard: {url}")
            continue

        _invocation_count += 1
        start = time.time()

        print()
        try:
            response = agent(user_input)
            elapsed = (time.time() - start) * 1000

            # Estimate tokens (rough)
            resp_tokens = len(str(response)) // 4
            input_tokens = len(user_input) // 4
            _total_tokens += resp_tokens + input_tokens

            # Publish metrics
            publish_batch_metrics([
                {"name": "ResponseLatency", "value": elapsed, "unit": "Milliseconds"},
                {"name": "TokensUsed", "value": resp_tokens + input_tokens, "unit": "Count"},
                {"name": "InputTokens", "value": input_tokens, "unit": "Count"},
                {"name": "OutputTokens", "value": resp_tokens, "unit": "Count"},
                {"name": "SessionDuration", "value": (time.time() - _session_start) * 1000, "unit": "Milliseconds"},
            ])

            print(f"\n  Agent: {response}")
            print(f"\n    📊 Latency: {elapsed:.0f}ms | Tokens: ~{resp_tokens + input_tokens} | Tools: {_tool_calls}")

        except Exception as e:
            _errors += 1
            elapsed = (time.time() - start) * 1000
            publish_metric("ErrorCount", 1, "Count")
            publish_metric("ResponseLatency", elapsed, "Milliseconds")
            print(f"\n    ❌ Error: {e}")
            print(f"    📊 Error published to CloudWatch")

    # Final session metrics
    session_duration = (time.time() - _session_start) * 1000
    publish_metric("SessionDuration", session_duration, "Milliseconds")

    print(f"\n{'═' * 70}")
    print(f"  SESSION COMPLETE")
    print(f"{'═' * 70}")
    show_stats()
    print()


def show_stats():
    """Display current session statistics."""
    duration = time.time() - _session_start
    print(f"\n  📊 SESSION METRICS ({_session_id})")
    print(f"  {'─' * 50}")
    print(f"  Duration:      {duration:.1f}s")
    print(f"  Invocations:   {_invocation_count}")
    print(f"  Tool calls:    {_tool_calls}")
    print(f"  Est. tokens:   ~{_total_tokens}")
    print(f"  Errors:        {_errors}")
    print(f"  Avg latency:   {'N/A' if _invocation_count == 0 else f'{duration/_invocation_count:.1f}s/request'}")
    print(f"  Namespace:     {METRICS_NAMESPACE}")


if __name__ == "__main__":
    run_demo()
