"""
Test: Part 4 — Context Isolation

Runs the isolated multi-agent pipeline (Research → Analyze → Write)
and verifies each stage produces output.

Usage:
    python tests/test_part4.py
"""

import sys
import time

sys.path.insert(0, ".")

from part4_context_isolation import run_isolated_pipeline, run_single_pipeline

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Colors
GREEN = "\033[1;32m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;42m"


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 4 — Context Isolation (Multi-Agent Boundaries)           {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    task = "Evaluate the viability of a 50MW solar farm in Vietnam for 2025-2027."

    print(f"  {PROMPT_COLOR}Task: {task}{RESET}\n")

    # --- Single Agent ---
    print(f"  {GREEN}{'━' * 68}{RESET}")
    print(f"  {GREEN}APPROACH A: Single Agent (accumulated context){RESET}\n")

    start = time.time()
    try:
        results_single = run_single_pipeline(task)
        elapsed_single = time.time() - start
        single_status = "PASS"
    except Exception as e:
        elapsed_single = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}")
        results_single = None
        single_status = "FAIL"

    if results_single:
        print(f"\n    {TIMING}Total: {elapsed_single:.1f}s{RESET}")
        for stage, t in results_single["timings"].items():
            resp = results_single["responses"][stage]
            print(f"    {GREEN}{stage}:{RESET} {TIMING}{t:.1f}s{RESET} │ {len(resp)} chars")

    # --- Isolated Agents ---
    print(f"\n  {GREEN}{'━' * 68}{RESET}")
    print(f"  {GREEN}APPROACH B: Isolated Agents (clean context per stage){RESET}\n")

    start = time.time()
    try:
        results_isolated = run_isolated_pipeline(task)
        elapsed_isolated = time.time() - start
        isolated_status = "PASS"
    except Exception as e:
        elapsed_isolated = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}")
        results_isolated = None
        isolated_status = "FAIL"

    if results_isolated:
        print(f"\n    {TIMING}Total: {elapsed_isolated:.1f}s{RESET}")
        for stage, t in results_isolated["timings"].items():
            resp = results_isolated["responses"][stage]
            print(f"    {GREEN}{stage}:{RESET} {TIMING}{t:.1f}s{RESET} │ {len(resp)} chars")

    # --- Comparison ---
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}COMPARISON{RESET}\n")

    if results_single and results_isolated:
        print(f"    {'Stage':<12} {'Single':>10} {'Isolated':>10}")
        print(f"    {'─' * 34}")
        for stage in ["research", "analysis", "writing"]:
            ts = results_single["timings"][stage]
            ti = results_isolated["timings"][stage]
            print(f"    {stage:<12} {ts:>9.1f}s {ti:>9.1f}s")
        print(f"    {'─' * 34}")
        print(f"    {'TOTAL':<12} {elapsed_single:>9.1f}s {elapsed_isolated:>9.1f}s")

    # Final summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    all_passed = True
    for label, status, elapsed in [("Single Agent", single_status, elapsed_single), ("Isolated Agents", isolated_status, elapsed_isolated)]:
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{label}: {status}{RESET} {TIMING}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 4 test passed — both pipelines produced output.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 4 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
