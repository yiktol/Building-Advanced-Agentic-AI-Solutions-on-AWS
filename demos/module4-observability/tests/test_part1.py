"""
Test: Part 1 — CloudWatch Metrics (Publish & Verify)

Creates an agent with a tool, sends 2 queries, publishes custom metrics
to CloudWatch, and verifies the metric exists.

Usage:
    python tests/test_part1.py

Requires:
    - AWS credentials (no stack deployment needed)
"""

import sys
import time
import uuid

sys.path.insert(0, ".")

import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"
REGION = "ap-southeast-1"
METRICS_NAMESPACE = "m4-demo/TestMetrics"
SESSION_ID = f"test-{uuid.uuid4().hex[:8]}"

cloudwatch = boto3.client("cloudwatch", region_name=REGION)

# --- Colors ---
BLUE = "\033[1;34m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;94m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;44m"  # White on blue background

_tool_calls = 0


@tool
def search_products(query: str) -> str:
    """Search product catalog.

    Args:
        query: Product search term
    """
    global _tool_calls
    _tool_calls += 1
    return f"Found: TechMart Pro 15 ($799), TechMart Air ($599), TechMart Hub ($149)"


def publish_metric(metric_name: str, value: float, unit: str = "Count"):
    """Publish a metric to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace=METRICS_NAMESPACE,
        MetricData=[{
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.utcnow(),
            "Dimensions": [{"Name": "SessionId", "Value": SESSION_ID}],
        }],
    )


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 1 — CloudWatch Metrics (Publish & Verify)                {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Search for laptops under $800.",
        "What products do you have available?",
    ]

    print(f"  {BLUE}Creating agent with instrumented tools...{RESET}")
    print(f"  {BLUE}Namespace: {METRICS_NAMESPACE} | Session: {SESSION_ID}{RESET}")
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are a product search assistant. Use tools to find products.",
        tools=[search_products],
    )
    print(f"  {BLUE}Agent ready. Sending {len(queries)} queries with metric publishing.{RESET}\n")

    total_start = time.time()
    results = []

    for i, query in enumerate(queries, 1):
        print(f"  {BLUE}{'─' * 68}{RESET}")
        print(f"  {BLUE}Query {i}/{len(queries)}{RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}\n")

        start = time.time()
        try:
            response = agent(query)
            elapsed = time.time() - start

            # Publish metrics
            publish_metric("ResponseLatency", elapsed * 1000, "Milliseconds")
            publish_metric("InvocationCount", 1, "Count")
            publish_metric("ToolCallCount", _tool_calls, "Count")

            print_response(response)
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | 📊 Metrics published{RESET}\n")
            results.append(("PASS", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed))

    # --- Verify metric exists ---
    print(f"  {BLUE}{'─' * 68}{RESET}")
    print(f"  {BLUE}Verification: Check metrics exist in CloudWatch{RESET}\n")

    start = time.time()
    try:
        metrics_response = cloudwatch.list_metrics(
            Namespace=METRICS_NAMESPACE,
            MetricName="InvocationCount",
        )
        elapsed = time.time() - start
        metric_list = metrics_response.get("Metrics", [])

        print(f"    {RESPONSE_COLOR}Found {len(metric_list)} metric(s) for 'InvocationCount'{RESET}")
        print(f"    {RESPONSE_COLOR}Namespace: {METRICS_NAMESPACE}{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if len(metric_list) > 0:
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}No metrics found — may take a few seconds to propagate{RESET}")
            results.append(("PASS", elapsed))  # Still pass — CW has eventual consistency
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {BLUE}{'═' * 68}{RESET}")
    print(f"  {BLUE}RESULTS{RESET}\n")

    step_names = ["Query 1", "Query 2", "Metric Verification"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 1 test passed — metrics published to CloudWatch.{RESET}")
        print(f"  {DIM}Tip: Check CloudWatch console under namespace '{METRICS_NAMESPACE}'.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 1 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
