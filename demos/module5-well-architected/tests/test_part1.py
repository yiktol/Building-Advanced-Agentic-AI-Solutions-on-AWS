"""
Test: Part 1 — E-Commerce Multi-Agent System (Routing)

Creates an orchestrator with 4 specialist agents and verifies
query routing (product query → product agent, billing query → billing agent).

Usage:
    python tests/test_part1.py

Requires:
    - AWS credentials for Bedrock
    - DynamoDB table 'm5-demo-products' (or agent uses inline knowledge)
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"

# --- Colors ---
GREEN = "\033[1;32m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;92m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;42m"  # White on green background

# --- Track routing ---
_routes = []


def create_specialist(name: str, prompt: str) -> Agent:
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=prompt,
    )


# Lightweight specialist agents for testing
billing_agent = create_specialist("billing",
    "You are a billing specialist. Handle refunds and payment questions. "
    "Rules: 30-day full refund, 60-day store credit. Be concise.")

product_agent = create_specialist("product",
    "You are a product specialist. TechMart Pro 15 $799 (i7, 16GB), "
    "Air $599 (i5, 8GB), Titan $1299 (RTX 4060), Hub $149. Be concise.")

tech_agent = create_specialist("tech",
    "You are tech support. TechMart Hub v2.1.x has Wi-Fi bug (update to v3.0.1). Be concise.")

shipping_agent = create_specialist("shipping",
    "You are shipping specialist. Standard 5-7 days, Express 2 days ($12.99). Be concise.")


@tool
def ask_billing(query: str) -> str:
    """Route to billing specialist for refunds, charges, payments.

    Args:
        query: Billing-related query
    """
    _routes.append("billing")
    return str(billing_agent(query))


@tool
def ask_product_specialist(query: str) -> str:
    """Route to product specialist for recommendations and comparisons.

    Args:
        query: Product-related query
    """
    _routes.append("product")
    return str(product_agent(query))


@tool
def ask_tech_support(query: str) -> str:
    """Route to tech support for device issues, firmware, connectivity.

    Args:
        query: Technical support query
    """
    _routes.append("tech")
    return str(tech_agent(query))


@tool
def ask_shipping(query: str) -> str:
    """Route to shipping specialist for order status and delivery.

    Args:
        query: Shipping/delivery query
    """
    _routes.append("shipping")
    return str(shipping_agent(query))


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    global _routes

    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 1 — E-Commerce Multi-Agent System (Routing)              {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        ("What laptops do you have under $800?", "product"),
        ("I was charged twice for order ORD-7001. Can I get a refund?", "billing"),
    ]

    print(f"  {GREEN}Creating orchestrator with 4 specialist agents...{RESET}")
    orchestrator = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are the Customer Service Orchestrator for TechMart e-commerce.
Route queries to the appropriate specialist:
- Billing (refunds, charges, payments) → ask_billing
- Tech Support (devices, firmware, connectivity) → ask_tech_support
- Products (recommendations, comparisons, specs) → ask_product_specialist
- Shipping (order status, delivery, tracking) → ask_shipping
Always route to exactly one specialist per query.""",
        tools=[ask_billing, ask_product_specialist, ask_tech_support, ask_shipping],
    )
    print(f"  {GREEN}Orchestrator ready. Sending {len(queries)} queries.{RESET}\n")

    total_start = time.time()
    results = []

    for i, (query, expected_route) in enumerate(queries, 1):
        _routes = []  # Reset routing tracker

        print(f"  {GREEN}{'─' * 68}{RESET}")
        print(f"  {GREEN}Query {i}/{len(queries)} (expect → {expected_route}){RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}\n")

        start = time.time()
        try:
            response = orchestrator(query)
            elapsed = time.time() - start
            print_response(response)

            # Check routing
            routed_to = _routes[-1] if _routes else "none"
            route_correct = expected_route in _routes
            route_info = f"Routed → {', '.join(_routes)}"
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | {route_info}{RESET}")

            if route_correct:
                print(f"    {SUCCESS}✓ Correct routing to '{expected_route}'{RESET}\n")
                results.append(("PASS", elapsed))
            else:
                print(f"    {FAIL}✗ Expected '{expected_route}' but got '{routed_to}'{RESET}\n")
                results.append(("FAIL", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    all_passed = True
    for i, (status, elapsed) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}Query {i}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 1 test passed — orchestrator routes correctly.{RESET}")
        print(f"  {DIM}Tip: Product → product agent, billing → billing agent.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 1 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
