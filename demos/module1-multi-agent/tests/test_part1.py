"""
Test: Part 1 — Single Agent (Cognitive Load Limitations)

Sends multiple multi-domain queries to a single overloaded agent
and shows how it juggles billing, tech support, and product knowledge.

Usage:
    python tests/test_part1.py
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part1_single_agent import SYSTEM_PROMPT

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# --- Colors ---
YELLOW = "\033[1;33m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;43m"  # White on yellow background


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 1 — Single Agent (Cognitive Load)                        {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Hi, I was charged $9.99 but I cancelled my subscription last week. Order TM-78432.",
        "Also, my TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3.",
        "I need a laptop for my daughter. Budget $600-800, writing and light video editing.",
        "Back to my subscription — can I also get a refund on the express shipping?",
        "If I buy the TechMart Pro 15, will it work with my Hub? Can I use my refund as credit?",
    ]

    print(f"  {YELLOW}Creating single agent...{RESET}")
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=SYSTEM_PROMPT,
    )
    print(f"  {YELLOW}Agent ready. Sending {len(queries)} queries.{RESET}\n")

    total_start = time.time()
    results = []

    for i, query in enumerate(queries, 1):
        print(f"  {YELLOW}{'─' * 68}{RESET}")
        print(f"  {YELLOW}Query {i}/{len(queries)}{RESET}")
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
    print(f"\n  {YELLOW}{'═' * 68}{RESET}")
    print(f"  {YELLOW}RESULTS{RESET}\n")

    all_passed = True
    for i, (status, elapsed) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}Query {i}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 1 test passed — all queries processed.{RESET}")
        print(f"  {DIM}Tip: Review responses for domain confusion across queries.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 1 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
