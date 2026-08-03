"""
Test: Part 2 — Cedar Policy + Cognito Identity (ALLOW/DENY)

Authenticates as Spider-Man via Cognito, then tests:
  - $300 refund → ALLOW (within max_refund limit)
  - $700 refund → DENY  (exceeds max_refund limit)

Usage:
    python tests/test_part2.py

Requires:
    - Cognito User Pool + Verified Permissions deployed
    - Env vars: COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, POLICY_STORE_ID
"""

import sys
import time

sys.path.insert(0, ".")

from part3_cognito_identity import authenticate, check_authorization

# --- Configuration ---
DEFAULT_PASSWORD = "Hero$ecure1!"
TEST_USER = "peter.parker@bugle.com"  # Spider-Man, agent/support, max_refund=500

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


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 2 — Cedar Policy (Cognito AuthN → AVP AuthZ)             {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Authenticate as Spider-Man ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 1: Authenticate as Spider-Man{RESET}")
    print(f"  {PROMPT_COLOR}Email: {TEST_USER}{RESET}\n")

    start = time.time()
    try:
        auth_result = authenticate(TEST_USER, DEFAULT_PASSWORD)
        elapsed = time.time() - start

        if auth_result["success"]:
            user = auth_result["user"]
            print(f"    {RESPONSE_COLOR}✅ Authenticated: {user.get('hero_name', 'Unknown')}{RESET}")
            print(f"    {RESPONSE_COLOR}   Role: {user.get('role', '?')} | Max Refund: ${user.get('max_refund', 0)}{RESET}")
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Authentication failed: {auth_result.get('error', 'Unknown')}{RESET}")
            print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 2: $300 refund (should ALLOW) ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 2: Check $300 refund authorization (expect ALLOW){RESET}")
    print(f"  {PROMPT_COLOR}Action: ProcessRefund, Amount: $300{RESET}\n")

    start = time.time()
    try:
        decision = check_authorization("ProcessRefund", {
            "type": "Order",
            "id": "ORD-5001",
            "amount": 300,
            "customer_id": "CUST-1001",
            "status": "delivered",
        })
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}Decision: {decision['decision']}{RESET}")
        print(f"    {RESPONSE_COLOR}Reasons: {decision.get('reasons', [])}{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if decision["decision"] == "ALLOW":
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Expected ALLOW but got {decision['decision']}{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 3: $700 refund (should DENY) ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 3: Check $700 refund authorization (expect DENY){RESET}")
    print(f"  {PROMPT_COLOR}Action: ProcessRefund, Amount: $700{RESET}\n")

    start = time.time()
    try:
        decision = check_authorization("ProcessRefund", {
            "type": "Order",
            "id": "ORD-5002",
            "amount": 700,
            "customer_id": "CUST-1002",
            "status": "delivered",
        })
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}Decision: {decision['decision']}{RESET}")
        print(f"    {RESPONSE_COLOR}Reasons: {decision.get('reasons', [])}{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if decision["decision"] == "DENY":
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Expected DENY but got {decision['decision']}{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {RED}{'═' * 68}{RESET}")
    print(f"  {RED}RESULTS{RESET}\n")

    step_names = ["Authentication", "$300 Refund (ALLOW)", "$700 Refund (DENY)"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 2 test passed — Cedar policies enforce ALLOW/DENY correctly.{RESET}")
        print(f"  {DIM}Tip: Spider-Man can refund ≤$500 but not $700.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 2 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
