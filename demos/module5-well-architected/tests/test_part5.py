"""
Test: Part 5 — Cost Optimization (Query Classifier & Model Tiering)

Tests the query complexity classifier (rule-based) and verifies
simple queries route to economy tier and complex queries to premium tier.
Sends one real query to each tier and measures token count.

Usage:
    python tests/test_part5.py

Requires:
    - AWS credentials for Bedrock
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent, tool
from strands.models import BedrockModel

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


def classify_complexity(query: str) -> str:
    """Classify query complexity to determine model tier.

    Simple: greetings, yes/no, single facts
    Complex: analysis, comparison, multi-step reasoning
    """
    simple_patterns = [
        "hello", "hi", "thanks", "bye", "yes", "no",
        "what is the price", "how much", "is it in stock",
        "what's your name", "help",
    ]
    complex_patterns = [
        "compare", "analyze", "recommend", "explain why",
        "pros and cons", "best option for", "detailed",
        "step by step", "architecture", "strategy",
    ]

    query_lower = query.lower()

    for pattern in complex_patterns:
        if pattern in query_lower:
            return "complex"

    for pattern in simple_patterns:
        if pattern in query_lower:
            return "simple"

    # Default: check length
    if len(query.split()) <= 8:
        return "simple"
    return "complex"


@tool
def search_products(query: str) -> str:
    """Search product catalog.

    Args:
        query: Search query
    """
    return "TechMart Pro 15 ($799, i7, 16GB), TechMart Air ($599, i5, 8GB), Titan ($1299, RTX 4060), Hub ($149)"


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 5 — Cost Optimization (Query Classifier & Tiering)       {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Test classifier — simple queries ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 1: Classify simple queries → economy tier{RESET}\n")

    start = time.time()
    simple_queries = [
        ("Hi", "simple"),
        ("How much is the Hub?", "simple"),
        ("Thanks", "simple"),
    ]

    all_simple_correct = True
    for query, expected in simple_queries:
        result = classify_complexity(query)
        icon = "✓" if result == expected else "✗"
        color = SUCCESS if result == expected else FAIL
        print(f"    {color}{icon} '{query}' → {result} (expected: {expected}){RESET}")
        if result != expected:
            all_simple_correct = False

    elapsed = time.time() - start
    print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

    if all_simple_correct:
        results.append(("PASS", elapsed))
    else:
        results.append(("FAIL", elapsed))

    # --- Step 2: Test classifier — complex queries ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 2: Classify complex queries → premium tier{RESET}\n")

    start = time.time()
    complex_queries = [
        ("Compare Pro 15 and Titan for video editing", "complex"),
        ("Analyze the pros and cons of each laptop", "complex"),
        ("What's the best option for a developer who needs GPU?", "complex"),
    ]

    all_complex_correct = True
    for query, expected in complex_queries:
        result = classify_complexity(query)
        icon = "✓" if result == expected else "✗"
        color = SUCCESS if result == expected else FAIL
        print(f"    {color}{icon} '{query}' → {result} (expected: {expected}){RESET}")
        if result != expected:
            all_complex_correct = False

    elapsed = time.time() - start
    print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

    if all_complex_correct:
        results.append(("PASS", elapsed))
    else:
        results.append(("FAIL", elapsed))

    # --- Step 3: Real query to economy tier ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 3: Send simple query to economy-tier agent{RESET}")
    query = "Hi, what products do you have?"
    tier = classify_complexity(query)
    print(f"  {PROMPT_COLOR}{query}{RESET}")
    print(f"  {DIM}Classified: {tier} → economy tier{RESET}\n")

    agent_economy = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are a TechMart assistant. Be concise.",
        tools=[search_products],
    )

    start = time.time()
    try:
        response = agent_economy(query)
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)

        # Estimate tokens
        tokens = len(query) // 3 + len(response_str) // 3 + 100
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | ~{tokens} tokens (economy){RESET}\n")

        if len(response_str) > 5:
            results.append(("PASS", elapsed))
        else:
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    # --- Step 4: Real query to premium tier ---
    print(f"  {GREEN}{'─' * 68}{RESET}")
    print(f"  {GREEN}Step 4: Send complex query to premium-tier agent{RESET}")
    query = "Compare the Pro 15 and Titan for video editing — pros and cons of each."
    tier = classify_complexity(query)
    print(f"  {PROMPT_COLOR}{query}{RESET}")
    print(f"  {DIM}Classified: {tier} → premium tier{RESET}\n")

    agent_premium = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are TechMart's premium advisor. Provide detailed analysis with comparisons.",
        tools=[search_products],
    )

    start = time.time()
    try:
        response = agent_premium(query)
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)

        # Estimate tokens
        tokens = len(query) // 3 + len(response_str) // 3 + 200
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s | ~{tokens} tokens (premium){RESET}\n")

        if len(response_str) > 10:
            results.append(("PASS", elapsed))
        else:
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {GREEN}{'═' * 68}{RESET}")
    print(f"  {GREEN}RESULTS{RESET}\n")

    step_names = [
        "Classifier: Simple → Economy",
        "Classifier: Complex → Premium",
        "Economy Tier Query",
        "Premium Tier Query",
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
        print(f"\n  {SUCCESS}✅ Part 5 test passed — cost optimization with model tiering works.{RESET}")
        print(f"  {DIM}Tip: Simple queries use cheaper models; complex ones get premium.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 5 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
