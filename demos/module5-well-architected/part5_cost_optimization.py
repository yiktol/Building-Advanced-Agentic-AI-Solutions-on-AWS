"""
Module 5 - Part 5: Cost Optimization — Token Budgets and Model Tiering

Demonstrates cost management strategies:
- Token budget enforcement per request/session
- Model tiering (cheap model for simple, premium for complex)
- Prompt caching impact on cost
- Cost metrics published to CloudWatch
"""

import os
import time
import uuid
import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
COST_NAMESPACE = os.environ.get("COST_NAMESPACE", "m5-demo/CostMetrics")

# Model tiers
TIER_ECONOMY = "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"  # Cheaper for simple queries
TIER_PREMIUM = "apac.anthropic.claude-sonnet-4-20250514-v1:0"     # Premium for complex

# Pricing (approximate $/1M tokens for comparison)
PRICING = {
    TIER_ECONOMY: {"input": 3.0, "output": 15.0, "label": "Claude 3.5 Sonnet v2 (Economy)"},
    TIER_PREMIUM: {"input": 3.0, "output": 15.0, "label": "Claude Sonnet 4 (Premium)"},
}

cloudwatch = boto3.client("cloudwatch", region_name=REGION)

# Session tracking
_session_id = f"cost-{uuid.uuid4().hex[:8]}"
_session_budget = 50000  # token budget per session
_request_budget = 10000   # token budget per request
_tokens_used_session = 0
_cost_records = []


# =============================================================================
# COST TRACKING
# =============================================================================

class CostTracker:
    """Tracks token usage and estimated cost."""

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.requests = []

    def record(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        pricing = PRICING.get(model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        record = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.requests.append(record)
        _cost_records.append(record)

        # Publish to CloudWatch
        try:
            cloudwatch.put_metric_data(
                Namespace=COST_NAMESPACE,
                MetricData=[
                    {"MetricName": "SessionCost", "Value": self.total_cost(), "Unit": "None", "Timestamp": datetime.utcnow()},
                    {"MetricName": "DailyTokensUsed", "Value": self.total_tokens(), "Unit": "Count", "Timestamp": datetime.utcnow()},
                ],
            )
        except Exception:
            pass

        return record

    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def total_cost(self) -> float:
        return sum(r["cost"] for r in self.requests)


# =============================================================================
# QUERY COMPLEXITY CLASSIFIER
# =============================================================================

def classify_complexity(query: str) -> str:
    """Classify query complexity to determine model tier.

    Simple: greetings, yes/no, single facts
    Complex: analysis, comparison, multi-step reasoning
    """
    simple_patterns = [
        "hello", "hi", "thanks", "bye", "yes", "no",
        "what is the price", "how much", "is it in stock",
        "what's your name", "help",
    ]
    complex_patterns = [
        "compare", "analyze", "recommend", "explain why",
        "pros and cons", "best option for", "detailed",
        "step by step", "architecture", "strategy",
    ]

    query_lower = query.lower()

    for pattern in complex_patterns:
        if pattern in query_lower:
            return "complex"

    for pattern in simple_patterns:
        if pattern in query_lower:
            return "simple"

    # Default: check length
    if len(query.split()) <= 8:
        return "simple"
    return "complex"


# =============================================================================
# TOOLS
# =============================================================================

@tool
def search_products(query: str) -> str:
    """Search product catalog.

    Args:
        query: Search query
    """
    products = {
        "laptop": "TechMart Pro 15 ($799, i7, 16GB), TechMart Air ($599, i5, 8GB), Titan ($1299, RTX 4060)",
        "hub": "TechMart Hub ($149, Wi-Fi 6, BT 5.0, Zigbee, 50 devices)",
        "camera": "Smart Camera ($79, 1080p, night vision)",
        "sensor": "Motion Sensor ($29, Zigbee, 120° detection)",
    }
    for key, val in products.items():
        if key in query.lower():
            return val
    return "TechMart Pro 15 ($799), Air ($599), Titan ($1299), Hub ($149), Camera ($79), Sensor ($29)"


@tool
def check_compatibility(product_a: str, product_b: str) -> str:
    """Check product compatibility.

    Args:
        product_a: First product
        product_b: Second product
    """
    return f"{product_a} + {product_b}: Compatible (Wi-Fi 6 / Bluetooth 5.0 connectivity)"


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    global _tokens_used_session

    print("=" * 70)
    print("PART 5: Cost Optimization — Token Budgets & Model Tiering")
    print("=" * 70)
    print()
    print("  Strategies:")
    print("    📊 Token budget: Session max 50k tokens, Request max 10k")
    print("    🏷️  Model tiering: Simple → Economy, Complex → Premium")
    print("    💰 Cost tracking: Real-time per-request cost estimation")
    print()
    print("  Choose mode:")
    print("  [1] Single tier (Premium model for everything)")
    print("  [2] Smart tiering (auto-select model by complexity)")
    print()

    choice = input("  Select (1/2): ").strip()
    use_tiering = choice == "2"

    mode = "Smart Tiering" if use_tiering else "Single Tier (Premium)"
    print(f"\n  Mode: {mode}")
    print(f"  Session budget: {_session_budget:,} tokens")
    print()
    print("  Commands: 'cost' (show cost summary), 'budget' (check budget), 'quit'")
    print("=" * 70)

    tracker = CostTracker()

    while True:
        print()
        remaining = _session_budget - _tokens_used_session
        try:
            user_input = input(f"  [{remaining:,} tokens left] You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "cost":
            show_cost_summary(tracker, use_tiering)
            continue

        if user_input.lower() == "budget":
            print(f"\n  📊 BUDGET STATUS")
            print(f"     Session: {_tokens_used_session:,} / {_session_budget:,} tokens ({_tokens_used_session/_session_budget*100:.1f}%)")
            print(f"     Estimated cost: ${tracker.total_cost():.4f}")
            continue

        # Check session budget
        if _tokens_used_session >= _session_budget:
            print(f"    🚨 SESSION BUDGET EXHAUSTED ({_tokens_used_session:,} / {_session_budget:,} tokens)")
            print(f"    No more requests allowed in this session.")
            continue

        # Classify complexity and select model
        complexity = classify_complexity(user_input)
        if use_tiering:
            model_id = TIER_ECONOMY if complexity == "simple" else TIER_PREMIUM
        else:
            model_id = TIER_PREMIUM

        model_label = PRICING[model_id]["label"]
        tier_icon = "💚" if model_id == TIER_ECONOMY else "💎"
        print(f"    {tier_icon} Complexity: {complexity} → {model_label}")

        # Create agent for this request
        agent = Agent(
            model=BedrockModel(model_id=model_id),
            system_prompt="You are a TechMart assistant. Be concise. Help with products and orders.",
            tools=[search_products, check_compatibility],
        )

        # Execute with token tracking
        start = time.time()
        print()
        response = agent(user_input)
        elapsed = (time.time() - start) * 1000

        response_str = str(response)
        # Estimate tokens
        input_tokens = len(user_input) // 3 + 500  # rough: prompt + system
        output_tokens = len(response_str) // 3

        # Check request budget
        request_tokens = input_tokens + output_tokens
        if request_tokens > _request_budget:
            print(f"    ⚠️  Request used {request_tokens:,} tokens (over {_request_budget:,} limit)")

        _tokens_used_session += request_tokens

        # Record cost
        record = tracker.record(model_id, input_tokens, output_tokens, elapsed)

        print(f"\n  Agent: {response_str}")
        print(f"\n    {tier_icon} ~{request_tokens:,} tokens | ${record['cost']:.5f} | {elapsed:.0f}ms | Session total: ${tracker.total_cost():.4f}")

    # Final cost report
    print(f"\n{'═' * 70}")
    print(f"  COST OPTIMIZATION REPORT")
    print(f"{'═' * 70}")
    show_cost_summary(tracker, use_tiering)
    print()


def show_cost_summary(tracker: CostTracker, use_tiering: bool):
    """Display cost summary."""
    print(f"\n  💰 COST SUMMARY ({_session_id})")
    print(f"  {'─' * 50}")
    print(f"  Total tokens:  {tracker.total_tokens():,}")
    print(f"  Total cost:    ${tracker.total_cost():.5f}")
    print(f"  Requests:      {len(tracker.requests)}")

    if tracker.requests:
        avg_cost = tracker.total_cost() / len(tracker.requests)
        avg_tokens = tracker.total_tokens() / len(tracker.requests)
        print(f"  Avg/request:   ${avg_cost:.5f} ({avg_tokens:.0f} tokens)")

    # Model tier breakdown
    if use_tiering:
        economy_reqs = [r for r in tracker.requests if r["model"] == TIER_ECONOMY]
        premium_reqs = [r for r in tracker.requests if r["model"] == TIER_PREMIUM]
        print(f"\n  Model Tier Breakdown:")
        print(f"    Economy: {len(economy_reqs)} requests, ${sum(r['cost'] for r in economy_reqs):.5f}")
        print(f"    Premium: {len(premium_reqs)} requests, ${sum(r['cost'] for r in premium_reqs):.5f}")

        if economy_reqs and premium_reqs:
            # Estimate savings
            if_all_premium_cost = sum(r["input_tokens"] * 3 + r["output_tokens"] * 15 for r in economy_reqs) / 1_000_000
            actual_economy_cost = sum(r["cost"] for r in economy_reqs)
            savings = if_all_premium_cost - actual_economy_cost
            print(f"    Estimated savings from tiering: ${savings:.5f}")

    print(f"\n  Per-request breakdown:")
    print(f"  {'#':<4} {'Model':<12} {'Tokens':>8} {'Cost':>10} {'Latency':>10}")
    print(f"  {'─' * 46}")
    for i, r in enumerate(tracker.requests[-10:], 1):
        label = "Economy" if r["model"] == TIER_ECONOMY else "Premium"
        tokens = r["input_tokens"] + r["output_tokens"]
        print(f"  {i:<4} {label:<12} {tokens:>7,} ${r['cost']:>9.5f} {r['latency_ms']:>8.0f}ms")


if __name__ == "__main__":
    run_demo()
