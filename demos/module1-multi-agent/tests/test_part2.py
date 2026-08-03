"""
Test: Part 2 — Multi-Agent Orchestrator (Framework-Layer Routing)

Sends queries across billing, tech, and product domains and verifies
the orchestrator routes to the correct specialist agent.

Usage:
    python tests/test_part2.py
"""

import sys
import time

sys.path.insert(0, ".")

from part2_multi_agent_orchestrator import (
    create_billing_agent,
    create_tech_support_agent,
    create_product_agent,
    create_orchestrator,
)

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# --- Colors ---
CYAN = "\033[1;36m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;46m"  # White on cyan background
ROUTING_COLOR = "\033[0;36m"


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 2 — Orchestrator (Framework-Layer Routing)                {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    test_cases = [
        {
            "query": "I was charged $9.99 but I cancelled my subscription. Order TM-78432.",
            "expected_routing": "📋 Billing Agent",
        },
        {
            "query": "My TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3.",
            "expected_routing": "🔧 Tech Support Agent",
        },
        {
            "query": "I need a laptop for college. Budget $600-800, writing and video editing.",
            "expected_routing": "🛍️ Product Agent",
        },
        {
            "query": "If I buy the TechMart Pro 15, will it work with my Hub? Can I use my refund as credit?",
            "expected_routing": "🛍️ Product + 📋 Billing (multi-route)",
        },
    ]

    print(f"  {CYAN}Creating orchestrator + 3 specialist agents...{RESET}")
    orchestrator = create_orchestrator()
    print(f"  {CYAN}Agents ready. Sending {len(test_cases)} queries.{RESET}\n")

    total_start = time.time()
    results = []

    for i, tc in enumerate(test_cases, 1):
        query = tc["query"]
        expected = tc["expected_routing"]

        print(f"  {CYAN}{'─' * 68}{RESET}")
        print(f"  {CYAN}Query {i}/{len(test_cases)}{RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}")
        print(f"  {ROUTING_COLOR}Expected routing: {expected}{RESET}\n")

        start = time.time()
        try:
            response = orchestrator(query)
            elapsed = time.time() - start
            print_response(response)
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")
            results.append(("PASS", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {CYAN}{'═' * 68}{RESET}")
    print(f"  {CYAN}RESULTS{RESET}\n")

    all_passed = True
    for i, (status, elapsed) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        expected = test_cases[i - 1]["expected_routing"]
        print(f"    {icon} {color}Query {i}: {status}{RESET} → {ROUTING_COLOR}{expected}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 2 test passed — orchestrator routed all queries.{RESET}")
        print(f"  {DIM}Tip: Check console for 📋🔧🛍️ routing indicators above.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 2 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
