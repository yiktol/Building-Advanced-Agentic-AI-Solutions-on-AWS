"""
Test: Part 1 — Context Exhaustion

Sends 5 progressively complex queries and tracks token growth.

Usage:
    python tests/test_part1.py
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part1_context_exhaustion import SYSTEM_PROMPT, estimate_tokens

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Colors
YELLOW = "\033[1;33m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;43m"


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 1 — Context Exhaustion (Token Growth)                    {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Plan a corporate retreat for 50 people in Bali for March. Include team building activities.",
        "Budget is $150,000. Break it down: accommodation, activities, meals, transport.",
        "12 people are vegetarian, 3 have mobility issues. Adjust the plan.",
        "Compare this with doing it in Thailand instead. Same requirements.",
        "Give me a day-by-day itinerary for the Bali option with time slots.",
    ]

    print(f"  {YELLOW}Creating agent...{RESET}")
    agent = Agent(model=BedrockModel(model_id=MODEL_ID), system_prompt=SYSTEM_PROMPT)
    print(f"  {YELLOW}Sending {len(queries)} queries to watch context grow.{RESET}\n")

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
            tokens = estimate_tokens(agent)
            resp_str = str(response)
            lines = resp_str.strip().split("\n")
            for line in lines[:5]:
                print(f"    {RESPONSE_COLOR}{line}{RESET}")
            if len(lines) > 5:
                print(f"    {DIM}... ({len(lines) - 5} more lines){RESET}")
            print(f"\n    {TIMING}⏱ {elapsed:.1f}s │ ~{tokens:,} tokens in context{RESET}\n")
            results.append(("PASS", elapsed, tokens))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed, 0))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {YELLOW}{'═' * 68}{RESET}")
    print(f"  {YELLOW}CONTEXT GROWTH{RESET}\n")

    all_passed = True
    for i, (status, elapsed, tokens) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        bar = "█" * (tokens // 500) if tokens else ""
        print(f"    {icon} {color}Query {i}{RESET}: {TIMING}{elapsed:.1f}s{RESET} │ ~{tokens:,} tokens {DIM}{bar}{RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 1 test passed — context growth tracked.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 1 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
