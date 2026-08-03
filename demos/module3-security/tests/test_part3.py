"""
Test: Part 3 — Cognito Identity (Authentication & Claims)

Authenticates as Spider-Man via Cognito and verifies JWT claims
are correctly decoded (hero_name, role, department).

Usage:
    python tests/test_part3.py

Requires:
    - Cognito User Pool deployed
    - Env vars: COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID
"""

import os
import sys
import time

sys.path.insert(0, ".")

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"
TEST_USER = "peter.parker@bugle.com"
DEFAULT_PASSWORD = "Hero$ecure1!"

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
    print(f"{HEADER_BG}  TEST: Part 3 — Cognito Identity (Authentication & Claims)           {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    # Check env vars
    user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
    client_id = os.environ.get("COGNITO_CLIENT_ID", "")

    if not user_pool_id or not client_id:
        print(f"  {DIM}⚠️  COGNITO_USER_POOL_ID or COGNITO_CLIENT_ID not set.{RESET}")
        print(f"  {DIM}   Skipping Cognito test (infrastructure not deployed).{RESET}")
        print(f"  {DIM}   Deploy with: ./scripts/deploy.sh{RESET}\n")
        sys.exit(0)

    from part3_cognito_identity import authenticate

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
            print(f"    {RESPONSE_COLOR}   Role: {user.get('role', '?')} | Department: {user.get('department', '?')}{RESET}")
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

    # --- Step 2: Verify hero_name ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 2: Verify hero_name = Spider-Man{RESET}\n")

    start = time.time()
    try:
        user = auth_result["user"]
        hero_name = user.get("hero_name", "")
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}hero_name: '{hero_name}'{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if hero_name == "Spider-Man":
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Expected 'Spider-Man' but got '{hero_name}'{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 3: Verify role = agent ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 3: Verify role = agent{RESET}\n")

    start = time.time()
    try:
        role = user.get("role", "")
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}role: '{role}'{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if role == "agent":
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Expected 'agent' but got '{role}'{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 4: Verify department = support ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 4: Verify department = support{RESET}\n")

    start = time.time()
    try:
        department = user.get("department", "")
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}department: '{department}'{RESET}")
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if department == "support":
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}Expected 'support' but got '{department}'{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {RED}{'═' * 68}{RESET}")
    print(f"  {RED}RESULTS{RESET}\n")

    step_names = ["Authentication", "hero_name=Spider-Man", "role=agent", "department=support"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 3 test passed — Cognito identity verified.{RESET}")
        print(f"  {DIM}Tip: JWT claims flow into Cedar policies for fine-grained authz.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 3 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
