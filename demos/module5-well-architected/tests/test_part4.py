"""
Test: Part 4 — Reliability (Fault Tolerance & Graceful Degradation)

Exercises the real CircuitBreaker and call_specialist routing from
part4_reliability to verify fault isolation: a broken specialist trips its
breaker and routes to the fallback agent, while healthy specialists keep
serving.

Usage:
    python tests/test_part4.py

Requires:
    - AWS credentials for Bedrock (no stack needed)
"""

import sys
import time

sys.path.insert(0, ".")

import part4_reliability as rel
from part4_reliability import CircuitBreaker

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"

# --- Colors ---
GREEN = "\033[1;32m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;92m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;42m"  # White on green background


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def _reset_state():
    """Clear fault flags and reset every circuit breaker to healthy."""
    for name in rel._faults:
        rel._faults[name] = False
    for breaker in rel._breakers.values():
        breaker.failure_count = 0
        breaker.state = "CLOSED"
        breaker.last_failure_time = None


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 4 — Reliability (Fault Tolerance & Degradation)          {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Test 1: CircuitBreaker state machine ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 1: CircuitBreaker opens after the failure threshold{RESET}\n")

    start = time.time()
    try:
        cb = CircuitBreaker("unit", failure_threshold=3, recovery_timeout=30)
        assert cb.can_execute() and cb.state == "CLOSED", "should start CLOSED"
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "CLOSED", "should stay CLOSED below threshold"
        cb.record_failure()  # 3rd failure hits threshold
        assert cb.state == "OPEN", "should OPEN at threshold"
        assert not cb.can_execute(), "OPEN breaker should block execution"
        cb.record_success()
        assert cb.state == "CLOSED" and cb.failure_count == 0, "success should reset"
        elapsed = time.time() - start
        print(f"    {SUCCESS}✓ CLOSED → (3 failures) → OPEN → (success) → CLOSED{RESET}\n")
        results.append(("PASS", elapsed))
    except AssertionError as e:
        elapsed = time.time() - start
        print(f"    {FAIL}✗ {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Test 2: Half-open recovery after timeout ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 2: OPEN breaker moves to HALF_OPEN after recovery timeout{RESET}\n")

    start = time.time()
    try:
        cb = CircuitBreaker("recovery", failure_threshold=1, recovery_timeout=0.2)
        cb.record_failure()
        assert cb.state == "OPEN", "single failure should OPEN (threshold 1)"
        # Within the recovery window the breaker stays OPEN and blocks calls.
        assert not cb.can_execute() and cb.state == "OPEN", "should block during recovery window"
        # Once the window elapses, the next check moves to HALF_OPEN for a trial call.
        time.sleep(0.25)
        can = cb.can_execute()
        assert can and cb.state == "HALF_OPEN", "should allow a trial call in HALF_OPEN"
        elapsed = time.time() - start
        print(f"    {SUCCESS}✓ OPEN → HALF_OPEN trial allowed after timeout{RESET}\n")
        results.append(("PASS", elapsed))
    except AssertionError as e:
        elapsed = time.time() - start
        print(f"    {FAIL}✗ {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Test 3: Fault injection routes to fallback (graceful degradation) ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 3: Broken billing specialist degrades to fallback{RESET}")

    _reset_state()
    rel._faults["billing"] = True
    threshold = rel._breakers["billing"].failure_threshold
    query = "I need a refund for order ORD-7001, charged $50 extra."
    print(f"  {PROMPT_COLOR}{query}{RESET}")
    print(f"  {DIM}💥 Billing fault ACTIVE (threshold: {threshold} failures){RESET}\n")

    start = time.time()
    try:
        # Call until the breaker trips and routing switches to the fallback agent.
        response_text = ""
        for _ in range(threshold):
            response_text = rel.call_specialist("billing", rel.billing_agent, query)
        elapsed = time.time() - start
        print_response(response_text)

        degraded_indicators = ["DEGRADED", "fallback", "unavailable", "⚠️"]
        has_degraded = any(ind.lower() in response_text.lower() for ind in degraded_indicators)
        breaker_open = rel._breakers["billing"].state == "OPEN"
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | Billing breaker: "
              f"{rel._breakers['billing'].state}{RESET}\n")

        if breaker_open and has_degraded:
            print(f"    {SUCCESS}✓ Billing breaker OPEN and fallback engaged{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ Expected OPEN breaker + degraded response "
                  f"(open={breaker_open}, degraded={has_degraded}){RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Test 4: Fault isolation — healthy specialist still serves ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Test 4: Healthy product specialist unaffected by billing fault{RESET}")

    # Keep billing broken; product stays healthy.
    query = "What laptops do you have?"
    print(f"  {PROMPT_COLOR}{query}{RESET}\n")

    start = time.time()
    try:
        response_text = rel.call_specialist("product", rel.product_agent, query)
        elapsed = time.time() - start
        print_response(response_text)

        degraded_indicators = ["DEGRADED", "fallback", "unavailable", "⚠️"]
        is_degraded = any(ind.lower() in response_text.lower() for ind in degraded_indicators)
        product_closed = rel._breakers["product"].state == "CLOSED"
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | Product breaker: "
              f"{rel._breakers['product'].state}{RESET}\n")

        if product_closed and not is_degraded:
            print(f"    {SUCCESS}✓ Product served normally — failure domain isolated{RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}✗ Product affected by billing fault "
                  f"(closed={product_closed}, degraded={is_degraded}){RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))
    finally:
        _reset_state()

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    step_names = [
        "Circuit Breaker State Machine",
        "Half-Open Recovery",
        "Fault Injection (DEGRADED)",
        "Fault Isolation",
    ]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 4 test passed — fault tolerance & graceful degradation work.{RESET}")
        print(f"  {DIM}Tip: Per-specialist breakers keep one failure from sinking the system.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 4 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
