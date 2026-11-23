"""
Run every Module 1 concept test and print a combined summary.

Usage (from module1-multi-agent/):  python test_concept/run_all_concepts.py
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from helpers import PASS, FAIL, DIM, RESET, STAGE_BG, run

TESTS = [
    ("Part 1: Single Agent", "test_single_agent_concept.py"),
    ("Part 2: Orchestrator", "test_orchestrator_concept.py"),
    ("Part 3: Agent-as-Tool", "test_agent_as_tool_concept.py"),
    ("Part 4: Shared Memory", "test_shared_memory_concept.py"),
]


def main():
    start, results = time.time(), []
    for name, script in TESTS:
        t = time.time()
        code = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=os.path.join(HERE, "..")).returncode
        results.append((name, code, time.time() - t))
        if code == 130:
            sys.exit(130)
    print(f"\n{STAGE_BG[6]}{'#' * 72}{RESET}\n{STAGE_BG[6]}  MODULE 1 - ALL CONCEPT TESTS{' ' * 43}{RESET}\n{STAGE_BG[6]}{'#' * 72}{RESET}\n")
    for name, code, el in results:
        icon, color = ("✅", PASS) if code == 0 else ("❌", FAIL)
        print(f"  {icon} {color}{name}{RESET} {DIM}({el:.1f}s){RESET}")
    print(f"\n  {DIM}Total: {time.time() - start:.1f}s{RESET}\n")
    sys.exit(0 if all(c == 0 for _, c, _ in results) else 1)


if __name__ == "__main__":
    run(main)
