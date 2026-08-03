"""
Test: Part 5 — Tool Design (Verbose vs Optimized)

Compares token consumption between verbose and optimized tool responses.

Usage:
    python tests/test_part5.py
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part5_tool_design import (
    verbose_customer_lookup,
    verbose_order_lookup,
    optimized_customer_lookup,
    optimized_order_lookup,
)

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Colors
BLUE = "\033[1;34m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;44m"
VERBOSE_COLOR = "\033[0;91m"   # Red for verbose
OPTIMIZED_COLOR = "\033[0;92m"  # Green for optimized


def estimate_tokens(agent: Agent) -> int:
    total_chars = 0
    if hasattr(agent, "messages"):
        for msg in agent.messages:
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and "text" in block:
                        total_chars += len(block["text"])
            elif isinstance(msg.get("content"), str):
                total_chars += len(msg["content"])
    return total_chars // 4


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 5 — Tool Design (Verbose vs Optimized)                   {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Look up customer CUST-44821 and summarize their account status.",
        "What was in order TM-78432? Is it within return window?",
    ]

    system_prompt = "You are a customer service agent. Use tools to look up info and provide concise answers."

    # --- Verbose ---
    print(f"  {VERBOSE_COLOR}{'━' * 68}{RESET}")
    print(f"  {VERBOSE_COLOR}🗒️  VERBOSE TOOLS{RESET}\n")

    agent_verbose = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
        tools=[verbose_customer_lookup, verbose_order_lookup],
    )

    verbose_timings = []
    for i, query in enumerate(queries, 1):
        print(f"    {PROMPT_COLOR}Query {i}: {query}{RESET}")
        start = time.time()
        try:
            response = agent_verbose(query)
            elapsed = time.time() - start
            verbose_timings.append(("PASS", elapsed))
            print(f"    {TIMING}⏱ {elapsed:.1f}s{RESET}")
            resp = str(response)
            print(f"    {RESPONSE_COLOR}{resp[:120]}...{RESET}\n")
        except Exception as e:
            elapsed = time.time() - start
            verbose_timings.append(("FAIL", elapsed))
            print(f"    {FAIL}ERROR: {e}{RESET}\n")

    verbose_tokens = estimate_tokens(agent_verbose)
    print(f"    {VERBOSE_COLOR}📊 Total context: ~{verbose_tokens:,} tokens{RESET}\n")

    # --- Optimized ---
    print(f"  {OPTIMIZED_COLOR}{'━' * 68}{RESET}")
    print(f"  {OPTIMIZED_COLOR}⚡ OPTIMIZED TOOLS{RESET}\n")

    agent_optimized = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
        tools=[optimized_customer_lookup, optimized_order_lookup],
    )

    optimized_timings = []
    for i, query in enumerate(queries, 1):
        print(f"    {PROMPT_COLOR}Query {i}: {query}{RESET}")
        start = time.time()
        try:
            response = agent_optimized(query)
            elapsed = time.time() - start
            optimized_timings.append(("PASS", elapsed))
            print(f"    {TIMING}⏱ {elapsed:.1f}s{RESET}")
            resp = str(response)
            print(f"    {RESPONSE_COLOR}{resp[:120]}...{RESET}\n")
        except Exception as e:
            elapsed = time.time() - start
            optimized_timings.append(("FAIL", elapsed))
            print(f"    {FAIL}ERROR: {e}{RESET}\n")

    optimized_tokens = estimate_tokens(agent_optimized)
    print(f"    {OPTIMIZED_COLOR}📊 Total context: ~{optimized_tokens:,} tokens{RESET}\n")

    # --- Comparison ---
    print(f"  {BLUE}{'═' * 68}{RESET}")
    print(f"  {BLUE}COMPARISON{RESET}\n")

    savings = ((verbose_tokens - optimized_tokens) / verbose_tokens * 100) if verbose_tokens > 0 else 0

    print(f"    {'Metric':<20} {VERBOSE_COLOR}{'Verbose':>12}{RESET} {OPTIMIZED_COLOR}{'Optimized':>12}{RESET} {'Savings':>10}")
    print(f"    {'─' * 56}")
    print(f"    {'Context tokens':<20} {verbose_tokens:>12,} {optimized_tokens:>12,} {savings:>9.0f}%")

    # Tool output sizes — call decorated tools directly
    v_cust = verbose_customer_lookup("CUST-44821")
    o_cust = optimized_customer_lookup("CUST-44821")
    v_order = verbose_order_lookup("TM-78432")
    o_order = optimized_order_lookup("TM-78432")

    cust_savings = (1 - len(o_cust) / len(v_cust)) * 100
    order_savings = (1 - len(o_order) / len(v_order)) * 100

    print(f"    {'Customer lookup':<20} {len(v_cust):>10} ch {len(o_cust):>10} ch {cust_savings:>9.0f}%")
    print(f"    {'Order lookup':<20} {len(v_order):>10} ch {len(o_order):>10} ch {order_savings:>9.0f}%")

    # Results
    print(f"\n  {BLUE}{'═' * 68}{RESET}")
    print(f"  {BLUE}RESULTS{RESET}\n")

    all_passed = True
    all_timings = verbose_timings + optimized_timings
    for status, _ in all_timings:
        if status != "PASS":
            all_passed = False

    verbose_pass = all(s == "PASS" for s, _ in verbose_timings)
    optimized_pass = all(s == "PASS" for s, _ in optimized_timings)

    icon_v = "✅" if verbose_pass else "❌"
    icon_o = "✅" if optimized_pass else "❌"
    print(f"    {icon_v} {VERBOSE_COLOR}Verbose agent: {'PASS' if verbose_pass else 'FAIL'}{RESET}")
    print(f"    {icon_o} {OPTIMIZED_COLOR}Optimized agent: {'PASS' if optimized_pass else 'FAIL'}{RESET}")
    print(f"    📊 Token reduction: {savings:.0f}%")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 5 test passed — optimized tools reduce context significantly.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 5 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
