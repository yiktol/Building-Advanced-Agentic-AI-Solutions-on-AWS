"""
Test: Part 4 — Shared Memory (Multi-Agent Collaboration)

Runs the full 3-agent workflow (Diagnose → Resolve → Follow-up)
and verifies shared memory accumulates records from all agents.

Usage:
    python tests/test_part4.py
"""

import sys
import time

sys.path.insert(0, ".")

from part4_shared_memory import (
    SharedMemoryStore,
    create_diagnostic_agent,
    create_resolution_agent,
    create_followup_agent,
)
import part4_shared_memory

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# --- Colors ---
GREEN = "\033[1;32m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;42m"  # White on green background
MEMORY_COLOR = "\033[0;32m"
DIAG_COLOR = "\033[1;34m"     # Blue for diagnostic
RESOLVE_COLOR = "\033[1;33m"  # Yellow for resolution
FOLLOWUP_COLOR = "\033[1;36m" # Cyan for follow-up


def print_response(text: str, max_lines: int = 10):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 4 — Shared Memory (Multi-Agent Collaboration)            {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    issue = "My TechMart Hub firmware v2.1.3 keeps dropping Wi-Fi every few minutes. I also added 2 motion sensors yesterday and they aren't appearing in the app."

    # Create fresh shared memory
    shared_memory = SharedMemoryStore(
        memory_id="test-memory",
        session_id="test-session-001",
    )
    # Inject into the module so tools use this instance
    part4_shared_memory.shared_memory = shared_memory

    print(f"  {GREEN}Shared Memory initialized:{RESET}")
    print(f"    {MEMORY_COLOR}memory_id: {shared_memory.memory_id}{RESET}")
    print(f"    {MEMORY_COLOR}session_id: {shared_memory.session_id}{RESET}")
    print(f"\n  {PROMPT_COLOR}Issue: {issue}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Diagnostic Agent ---
    print(f"  {GREEN}{'━' * 68}{RESET}")
    print(f"  {DIAG_COLOR}STEP 1: 🔬 Diagnostic Agent{RESET}")
    print(f"  {DIM}Analyzing issue and saving findings to shared memory...{RESET}\n")

    start = time.time()
    try:
        diag_agent = create_diagnostic_agent()
        response = diag_agent(
            f"Customer reports: {issue}\n\nDiagnose the root cause(s). Save your findings to shared memory."
        )
        elapsed = time.time() - start
        print_response(response)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}")

        # Verify memory was written
        diag_records = shared_memory.read_by_actor("diagnostic-agent")
        if diag_records:
            print(f"    {MEMORY_COLOR}💾 Memory records written: {len(diag_records)}{RESET}\n")
            results.append(("PASS", "Diagnostic Agent", elapsed))
        else:
            print(f"    {FAIL}⚠️  No memory records written!{RESET}\n")
            results.append(("FAIL", "Diagnostic Agent", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", "Diagnostic Agent", elapsed))

    # --- Step 2: Resolution Agent ---
    print(f"  {GREEN}{'━' * 68}{RESET}")
    print(f"  {RESOLVE_COLOR}STEP 2: 🔧 Resolution Agent{RESET}")
    print(f"  {DIM}Reading diagnosis from memory, providing fix...{RESET}\n")

    start = time.time()
    try:
        resolution_agent = create_resolution_agent()
        response = resolution_agent(
            "Check shared memory for the diagnosis and provide step-by-step resolution. Save your resolution plan to shared memory."
        )
        elapsed = time.time() - start
        print_response(response)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}")

        # Verify memory was written
        resolve_records = shared_memory.read_by_actor("resolution-agent")
        if resolve_records:
            print(f"    {MEMORY_COLOR}💾 Memory records written: {len(resolve_records)}{RESET}\n")
            results.append(("PASS", "Resolution Agent", elapsed))
        else:
            print(f"    {FAIL}⚠️  No memory records written!{RESET}\n")
            results.append(("FAIL", "Resolution Agent", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", "Resolution Agent", elapsed))

    # --- Step 3: Follow-up Agent ---
    print(f"  {GREEN}{'━' * 68}{RESET}")
    print(f"  {FOLLOWUP_COLOR}STEP 3: ✅ Follow-up Agent{RESET}")
    print(f"  {DIM}Reading full history, summarizing, suggesting prevention...{RESET}\n")

    start = time.time()
    try:
        followup_agent = create_followup_agent()
        response = followup_agent(
            "Review shared memory for the complete case history. Provide a summary and suggest preventive measures. Save your summary to shared memory."
        )
        elapsed = time.time() - start
        print_response(response)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}")

        # Verify memory was written
        followup_records = shared_memory.read_by_actor("followup-agent")
        if followup_records:
            print(f"    {MEMORY_COLOR}💾 Memory records written: {len(followup_records)}{RESET}\n")
            results.append(("PASS", "Follow-up Agent", elapsed))
        else:
            print(f"    {FAIL}⚠️  No memory records written!{RESET}\n")
            results.append(("FAIL", "Follow-up Agent", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", "Follow-up Agent", elapsed))

    total_elapsed = time.time() - total_start

    # --- Shared Memory Audit Trail ---
    print(f"  {GREEN}{'━' * 68}{RESET}")
    print(f"  {GREEN}📝 SHARED MEMORY — Audit Trail{RESET}\n")

    all_records = shared_memory.read_all()
    for r in all_records:
        actor = r["actor_id"]
        mtype = r["memory_type"]
        obs = r["content"].get("observation", "")[:90]
        icon_map = {
            "diagnostic-agent": f"{DIAG_COLOR}🔬",
            "resolution-agent": f"{RESOLVE_COLOR}🔧",
            "followup-agent": f"{FOLLOWUP_COLOR}✅",
        }
        icon = icon_map.get(actor, f"{DIM}📝")
        print(f"    {icon} [{actor}] ({mtype}){RESET}")
        print(f"      {DIM}{obs}...{RESET}")

    print(f"\n    {MEMORY_COLOR}Total records: {len(all_records)}{RESET}")

    # --- Summary ---
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    all_passed = True
    for status, label, elapsed in results:
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{label}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    # Verification checks
    print(f"\n  {GREEN}VERIFICATION:{RESET}")
    checks = [
        ("Diagnostic records exist", len(shared_memory.read_by_actor("diagnostic-agent")) > 0),
        ("Resolution records exist", len(shared_memory.read_by_actor("resolution-agent")) > 0),
        ("Follow-up records exist", len(shared_memory.read_by_actor("followup-agent")) > 0),
        ("Multiple actor_ids used", len(set(r["actor_id"] for r in all_records)) >= 3),
    ]
    for label, passed in checks:
        icon = "✅" if passed else "❌"
        color = SUCCESS if passed else FAIL
        print(f"    {icon} {color}{label}{RESET}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 4 test passed — 3 agents collaborated via shared memory.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 4 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
