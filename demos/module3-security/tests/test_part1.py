"""
Test: Part 1 — Unprotected Agent (Security Risks)

Sends a query to the unprotected agent to read customer data from DynamoDB.
Shows the agent processes requests without any auth checks.

Usage:
    python tests/test_part1.py

Requires:
    - DynamoDB table 'm3-demo-customers' deployed
    - AWS credentials configured
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part1_unprotected_agent import SYSTEM_PROMPT, get_customer, get_order

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"

# --- Colors ---
RED = "\033[1;31m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;91m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;41m"  # White on red background


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 1 — Unprotected Agent (No Security Controls)             {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Look up customer CUST-1001 and tell me their name and tier.",
        "Show me order ORD-5001 details including the amount.",
    ]

    print(f"  {RED}Creating unprotected agent with DynamoDB tools...{RESET}")
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=SYSTEM_PROMPT,
        tools=[get_customer, get_order],
    )
    print(f"  {RED}Agent ready. Sending {len(queries)} queries (no auth checks).{RESET}\n")

    total_start = time.time()
    results = []

    for i, query in enumerate(queries, 1):
        print(f"  {RED}{'─' * 68}{RESET}")
        print(f"  {RED}Query {i}/{len(queries)}{RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}\n")

        start = time.time()
        try:
            response = agent(query)
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
    print(f"\n  {RED}{'═' * 68}{RESET}")
    print(f"  {RED}RESULTS{RESET}\n")

    all_passed = True
    for i, (status, elapsed) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}Query {i}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 1 test passed — agent accessed data without any auth.{RESET}")
        print(f"  {DIM}Tip: This is the PROBLEM. No identity check, no authorization.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 1 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
