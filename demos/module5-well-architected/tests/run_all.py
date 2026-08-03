"""
Run all Module 5 (Well-Architected) tests sequentially with a final summary.

Usage:
    python tests/run_all.py
"""

import subprocess
import sys
import time

# --- Colors ---
BOLD = "\033[1m"
RESET = "\033[0m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
TIMING = "\033[0;90m"
HEADER_BG = "\033[1;97;42m"  # White on green

TESTS = [
    ("Part 1: E-Commerce System", "tests/test_part1.py"),
    ("Part 2: Reliability", "tests/test_part2.py"),
    ("Part 3: Ops Excellence", "tests/test_part3.py"),
    ("Part 5: Cost Optimization", "tests/test_part5.py"),
]


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  MODULE 5 — RUN ALL TESTS                                            {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    # Run from the module5-well-architected directory
    cwd = sys.path[0] + "/.."

    total_start = time.time()
    results = []

    for name, script in TESTS:
        print(f"  {BOLD}Running: {name}...{RESET}")
        start = time.time()
        proc = subprocess.run(
            [sys.executable, script],
            cwd=cwd,
        )
        elapsed = time.time() - start
        status = "PASS" if proc.returncode == 0 else "FAIL"
        results.append((name, status, elapsed))
        print()

    total_elapsed = time.time() - total_start

    # Final summary
    print(f"{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  FINAL SUMMARY                                                       {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    all_passed = True
    for name, status, elapsed in results:
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"  {icon} {color}{name}: {status}{RESET} {TIMING}({elapsed:.0f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n  {TIMING}Total elapsed: {total_elapsed:.0f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}🎉 All tests passed!{RESET}\n")
    else:
        print(f"\n  {FAIL}⚠️  Some tests failed.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
