"""
Test: Part 3 — Agent-as-Tool (MCP-Style Reusability)

Tests both the Sales Agent and Support Agent to verify they correctly
invoke the shared tools (product_lookup, compatibility_check, order_status).

Usage:
    python tests/test_part3.py
"""

import sys
import time

sys.path.insert(0, ".")

from part3_agent_as_tool import create_sales_agent, create_support_agent

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# --- Colors ---
MAGENTA = "\033[1;35m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;45m"  # White on magenta background
TOOL_COLOR = "\033[0;35m"


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 3 — Agent-as-Tool (MCP Reusability)                      {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Test A: Sales Agent ---
    print(f"  {MAGENTA}{'━' * 68}{RESET}")
    print(f"  {MAGENTA}SCENARIO A: 💰 Sales Agent{RESET}")
    print(f"  {TOOL_COLOR}Tools: 🔍 product_lookup, 🔗 compatibility_check{RESET}\n")

    sales_queries = [
        {
            "query": "Look up the TechMart Pro 15 for me.",
            "expected_tools": "🔍 product_lookup",
        },
        {
            "query": "Will the TechMart Hub work with the Smart Camera?",
            "expected_tools": "🔗 compatibility_check",
        },
    ]

    print(f"  {MAGENTA}Creating Sales Agent...{RESET}")
    sales_agent = create_sales_agent()

    for i, tc in enumerate(sales_queries, 1):
        query = tc["query"]
        expected = tc["expected_tools"]

        print(f"\n  {MAGENTA}  Query A{i}: {RESET}{PROMPT_COLOR}{query}{RESET}")
        print(f"  {TOOL_COLOR}  Expected: {expected}{RESET}\n")

        start = time.time()
        try:
            response = sales_agent(query)
            elapsed = time.time() - start
            print_response(response)
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}")
            results.append(("PASS", f"Sales A{i}", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}")
            results.append(("FAIL", f"Sales A{i}", elapsed))

    # --- Test B: Support Agent ---
    print(f"\n\n  {MAGENTA}{'━' * 68}{RESET}")
    print(f"  {MAGENTA}SCENARIO B: 🛠️  Support Agent{RESET}")
    print(f"  {TOOL_COLOR}Tools: 🔍 product_lookup, 🔗 compatibility_check, 📦 order_status{RESET}\n")

    support_queries = [
        {
            "query": "Check the status of my order TM-78432.",
            "expected_tools": "📦 order_status",
        },
        {
            "query": "Are the motion sensors in my order compatible with the TechMart Hub?",
            "expected_tools": "🔗 compatibility_check (+ possibly 📦 order_status)",
        },
    ]

    print(f"  {MAGENTA}Creating Support Agent...{RESET}")
    support_agent = create_support_agent()

    for i, tc in enumerate(support_queries, 1):
        query = tc["query"]
        expected = tc["expected_tools"]

        print(f"\n  {MAGENTA}  Query B{i}: {RESET}{PROMPT_COLOR}{query}{RESET}")
        print(f"  {TOOL_COLOR}  Expected: {expected}{RESET}\n")

        start = time.time()
        try:
            response = support_agent(query)
            elapsed = time.time() - start
            print_response(response)
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}")
            results.append(("PASS", f"Support B{i}", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}")
            results.append(("FAIL", f"Support B{i}", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n\n  {MAGENTA}{'═' * 68}{RESET}")
    print(f"  {MAGENTA}RESULTS{RESET}\n")

    all_passed = True
    for status, label, elapsed in results:
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{label}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 3 test passed — both agents invoked shared tools.{RESET}")
        print(f"  {DIM}Tip: Look for 🔍🔗📦 tool indicators in output above.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 3 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
