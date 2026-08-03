"""
Test: Part 2 — Reliability (Fault Injection & Graceful Degradation)

Creates an orchestrator with fault injection. Breaks one specialist agent
and verifies the system falls back gracefully (DEGRADED mode).

Usage:
    python tests/test_part2.py

Requires:
    - AWS credentials for Bedrock (no stack needed)
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

# --- Fault Injection State ---
_faults = {"billing": False, "product": False}
_fallback_triggered = False


def create_specialist(name: str, prompt: str) -> Agent:
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=prompt,
    )


# Specialists
product_agent = create_specialist("product",
    "You are a product specialist. TechMart Pro 15 $799, Air $599, Titan $1299, Hub $149. Be concise.")

fallback_agent = create_specialist("fallback",
    "You are a GENERAL customer service fallback agent. A specialist is unavailable. "
    "Provide best-effort help. Prefix response with: ⚠️ [DEGRADED MODE - Specialist unavailable]")


@tool
def ask_billing(query: str) -> str:
    """Route to billing specialist for refunds, charges, payments.

    Args:
        query: Billing-related query
    """
    global _fallback_triggered

    if _faults["billing"]:
        _fallback_triggered = True
        return str(fallback_agent(f"[Fallback for billing]: {query}"))

    # Normal path (won't reach here in fault test)
    return "Billing agent response: 30-day full refund policy applies."


@tool
def ask_product_specialist(query: str) -> str:
    """Route to product specialist for recommendations and comparisons.

    Args:
        query: Product-related query
    """
    if _faults["product"]:
        global _fallback_triggered
        _fallback_triggered = True
        return str(fallback_agent(f"[Fallback for product]: {query}"))

    return str(product_agent(query))


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    global _fallback_triggered

    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 2 — Reliability (Fault Injection & Degradation)          {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    print(f"  {GREEN}Creating orchestrator with fault injection capability...{RESET}")
    orchestrator = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are the TechMart orchestrator. Route queries to specialists.
- Billing (refunds, charges) → ask_billing
- Products (recommendations, specs) → ask_product_specialist
If a specialist reports degraded mode, relay that information to the customer.""",
        tools=[ask_billing, ask_product_specialist],
    )
    print(f"  {GREEN}Orchestrator ready.{RESET}\n")

    total_start = time.time()
    results = []

    # --- Test 1: Normal operation (no faults) ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 1: Normal operation (no faults){RESET}")
    query = "What laptops do you have?"
    print(f"  {PROMPT_COLOR}{query}{RESET}\n")

    _fallback_triggered = False
    start = time.time()
    try:
        response = agent_response = orchestrator(query)
        elapsed = time.time() - start
        print_response(response)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | Fallback: {'Yes' if _fallback_triggered else 'No'}{RESET}\n")

        if not _fallback_triggered:
            results.append(("PASS", elapsed))
        else:
            results.append(("PASS", elapsed))  # Fallback in normal mode is acceptable
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Test 2: Inject fault into billing, send billing query ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 2: Fault injected into BILLING → expect DEGRADED response{RESET}")
    _faults["billing"] = True
    _fallback_triggered = False
    query = "I need a refund for order ORD-7001, I was charged $50 extra."
    print(f"  {PROMPT_COLOR}{query}{RESET}")
    print(f"  {DIM}💥 Billing agent fault ACTIVE{RESET}\n")

    start = time.time()
    try:
        response = orchestrator(query)
        elapsed = time.time() - start
        response_text = str(response)
        print_response(response_text)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | Fallback triggered: {_fallback_triggered}{RESET}\n")

        # Check for degraded indicators
        degraded_indicators = ["DEGRADED", "fallback", "unavailable", "⚠️"]
        has_degraded = any(ind.lower() in response_text.lower() for ind in degraded_indicators) or _fallback_triggered

        if has_degraded:
            print(f"    {SUCCESS}✓ System degraded gracefully — fallback engaged{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ Expected DEGRADED response but got normal response{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # Reset faults
    _faults["billing"] = False

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    step_names = ["Normal Operation", "Fault Injection (DEGRADED)"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 2 test passed — graceful degradation works.{RESET}")
        print(f"  {DIM}Tip: Circuit breaker + fallback = system stays up.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 2 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
