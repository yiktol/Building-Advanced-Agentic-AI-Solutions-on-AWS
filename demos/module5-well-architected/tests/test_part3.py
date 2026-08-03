"""
Test: Part 3 — Operational Excellence (Deployment & Health Check)

Creates two agent versions (v1 basic, v2 enhanced) and runs health
checks on each. Verifies both respond successfully (deployment simulation).

Usage:
    python tests/test_part3.py

Requires:
    - AWS credentials for Bedrock
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


@tool
def lookup_product(name: str) -> str:
    """Look up product info.

    Args:
        name: Product name
    """
    products = {
        "TechMart Pro 15": "$799, 15.6in, i7, 16GB RAM",
        "TechMart Hub": "$149, Wi-Fi 6, Bluetooth 5.0, Zigbee",
        "TechMart Air": "$599, 14in, i5, 8GB RAM",
    }
    for key, val in products.items():
        if name.lower() in key.lower():
            return f"{key}: {val}"
    return f"Product '{name}' not found."


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 3 — Ops Excellence (Deployment & Health Check)           {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Deploy v1 and health check ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 1: Deploy Agent v1.0.0 (basic prompt) — Health Check{RESET}\n")

    print(f"  {GREEN}Creating v1 agent...{RESET}")
    agent_v1 = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are a helpful TechMart product assistant. Help customers find products. Be concise.",
        tools=[lookup_product],
    )

    start = time.time()
    try:
        response = agent_v1("Respond with exactly: HEALTHY")
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if "HEALTHY" in response_str.upper() or len(response_str) > 0:
            print(f"    {SUCCESS}✓ v1.0.0 health check passed{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ v1.0.0 health check failed — empty response{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 2: Deploy v2 and health check ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 2: Deploy Agent v2.0.0 (enhanced prompt) — Health Check{RESET}\n")

    print(f"  {GREEN}Creating v2 agent (enhanced with proactive suggestions)...{RESET}")
    agent_v2 = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are TechMart's premium product assistant (v2.0).
Improvements over v1: More detailed responses, proactive compatibility suggestions.
Always mention related products and compatibility when answering.
Help customers find products and check availability.""",
        tools=[lookup_product],
    )

    start = time.time()
    try:
        response = agent_v2("Respond with exactly: HEALTHY")
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if "HEALTHY" in response_str.upper() or len(response_str) > 0:
            print(f"    {SUCCESS}✓ v2.0.0 health check passed{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ v2.0.0 health check failed — empty response{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 3: Functional test on v2 ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 3: Functional test — v2 answers a real query{RESET}")
    query = "What laptops do you have?"
    print(f"  {PROMPT_COLOR}{query}{RESET}\n")

    start = time.time()
    try:
        response = agent_v2(query)
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if len(response_str) > 10:
            print(f"    {SUCCESS}✓ v2 returned meaningful response{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ Response too short{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    step_names = ["v1.0.0 Health Check", "v2.0.0 Health Check", "v2 Functional Test"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 3 test passed — deployment & health checks work.{RESET}")
        print(f"  {DIM}Tip: Blue/green deploys with health checks prevent bad rollouts.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 3 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
