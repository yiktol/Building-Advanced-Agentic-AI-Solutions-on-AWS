"""
Test: Part 5 — Audit Trail (Structured Logging)

Creates an agent with audit logging tools, sends queries,
and verifies that audit records are written to the local cache.

Usage:
    python tests/test_part5.py

Requires:
    - AWS credentials for Bedrock
    - DynamoDB tables (m3-demo-customers, m3-demo-orders)
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from part5_audit_trail import (
    _audit_records,
    write_audit_log,
    get_customer,
    get_order,
    SYSTEM_PROMPT,
)

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
    print(f"{HEADER_BG}  TEST: Part 5 — Audit Trail (Structured Logging)                     {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    queries = [
        "Look up customer CUST-1001 and tell me their name.",
        "Show me order ORD-5001 details.",
    ]

    print(f"  {RED}Creating agent with audit logging tools...{RESET}")
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=SYSTEM_PROMPT,
        tools=[get_customer, get_order],
    )
    print(f"  {RED}Agent ready. Sending {len(queries)} queries with audit tracking.{RESET}\n")

    # Clear any existing audit records
    _audit_records.clear()

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
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | Audit records: {len(_audit_records)}{RESET}\n")
            results.append(("PASS", elapsed))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed))

    # --- Verify audit records ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Verification: Check audit records were written{RESET}\n")

    start = time.time()
    record_count = len(_audit_records)
    elapsed = time.time() - start

    print(f"    {RESPONSE_COLOR}Total audit records: {record_count}{RESET}")
    if _audit_records:
        print(f"    {RESPONSE_COLOR}Actions logged:{RESET}")
        for record in _audit_records[:6]:
            action = record.get("action", "unknown")
            resource = record.get("resource", "?")
            outcome = record.get("outcome", "?")
            icon = {"success": "✅", "initiated": "▶️", "not_found": "⚠️"}.get(outcome, "❓")
            print(f"      {RESPONSE_COLOR}{icon} {action} on {resource} → {outcome}{RESET}")

    print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

    if record_count > 0:
        results.append(("PASS", elapsed))
    else:
        print(f"    {FAIL}No audit records found — audit logging not working{RESET}")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {RED}{'═' * 68}{RESET}")
    print(f"  {RED}RESULTS{RESET}\n")

    step_names = ["Query 1 (Customer)", "Query 2 (Order)", "Audit Records Written"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 5 test passed — audit trail records actions.{RESET}")
        print(f"  {DIM}Tip: In production, logs go to CloudWatch for compliance queries.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 5 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
