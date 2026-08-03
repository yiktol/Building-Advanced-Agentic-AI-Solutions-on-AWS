"""
Test: Part 2 — Prompt Caching

Runs 3 queries with caching enabled and verifies responses work.
(Actual cache hit metrics depend on Bedrock's internal caching behavior.)

Usage:
    python tests/test_part2.py
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part2_prompt_caching import (
    SYSTEM_PROMPT_CONTENT,
    get_stock_price,
    get_quarterly_metrics,
    get_competitor_analysis,
)

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Colors
CYAN = "\033[1;36m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;46m"


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 2 — Prompt Caching                                      {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "What is GlobalTech's revenue breakdown by segment?",
        "How does our AI segment compare with TechNova?",
        "What was Q3-2025 performance and what's our stock price?",
    ]

    print(f"  {CYAN}Creating cached agent (cache_tools + system prompt cache point)...{RESET}")

    model = BedrockModel(model_id=MODEL_ID, cache_tools="default")
    system_with_cache = [
        {"text": SYSTEM_PROMPT_CONTENT},
        {"cachePoint": {"type": "default"}},
    ]
    agent = Agent(
        model=model,
        system_prompt=system_with_cache,
        tools=[get_stock_price, get_quarterly_metrics, get_competitor_analysis],
    )
    print(f"  {CYAN}Agent ready. Sending {len(queries)} queries.{RESET}\n")

    total_start = time.time()
    results = []

    for i, query in enumerate(queries, 1):
        label = "(cold)" if i == 1 else "(should be cached)"
        print(f"  {CYAN}{'─' * 68}{RESET}")
        print(f"  {CYAN}Query {i}/{len(queries)} {label}{RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}\n")

        start = time.time()
        try:
            response = agent(query)
            elapsed = time.time() - start
            resp_str = str(response)
            lines = resp_str.strip().split("\n")
            for line in lines[:6]:
                print(f"    {RESPONSE_COLOR}{line}{RESET}")
            if len(lines) > 6:
                print(f"    {DIM}... ({len(lines) - 6} more lines){RESET}")
            print(f"\n    {TIMING}⏱ {elapsed:.1f}s{RESET}\n")
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
        label = "(cold)" if i == 1 else "(cached)"
        print(f"    {icon} {color}Query {i} {label}: {status}{RESET} {TIMING}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 2 test passed — cached agent responded to all queries.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 2 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
