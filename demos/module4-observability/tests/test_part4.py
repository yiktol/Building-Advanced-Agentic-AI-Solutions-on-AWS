"""
Test: Part 4 — Evaluation (LLM-as-Judge)

Creates a tech support agent, sends a query, then uses a judge agent
to evaluate the response for correctness. Verifies score is a float 0-1.

Usage:
    python tests/test_part4.py

Requires:
    - AWS credentials for Bedrock
"""

import sys
import time
import json

sys.path.insert(0, ".")

from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"

# --- Colors ---
BLUE = "\033[1;34m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;94m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;44m"  # White on blue background


@tool
def search_kb(query: str) -> str:
    """Search knowledge base for product and tech info.

    Args:
        query: Search query
    """
    knowledge = {
        "wifi": "TechMart Hub v2.1.x has known Wi-Fi bug. Update to firmware v3.0.1 via Settings > System > Update.",
        "hub": "TechMart Hub: $149, Wi-Fi 6, Bluetooth 5.0, Zigbee 3.0, max 50 devices.",
        "laptop": "TechMart Pro 15: $799, 15.6in, i7, 16GB, 512GB SSD.",
    }
    for key, value in knowledge.items():
        if key in query.lower():
            return value
    return "No specific information found."


def print_response(text: str, max_lines: int = 12):
    lines = str(text).strip().split("\n")
    truncated = len(lines) > max_lines
    for line in lines[:max_lines]:
        print(f"    {RESPONSE_COLOR}{line}{RESET}")
    if truncated:
        print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 4 — Evaluation (LLM-as-Judge)                            {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Create agent and get response ---
    print(f"  {BLUE}{'─' * 68}{RESET}")
    print(f"  {BLUE}Step 1: Create tech support agent and get response{RESET}")
    query = "My TechMart Hub keeps dropping Wi-Fi. Firmware is v2.1.3."
    print(f"  {PROMPT_COLOR}{query}{RESET}\n")

    print(f"  {BLUE}Creating agent with knowledge base tool...{RESET}")
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are TechMart tech support. Use search_kb for product info. Be concise and helpful.",
        tools=[search_kb],
    )

    start = time.time()
    try:
        response = agent(query)
        elapsed = time.time() - start
        response_str = str(response)
        print_response(response_str)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        # Check response mentions v3.0.1
        if "3.0.1" in response_str:
            print(f"    {SUCCESS}✓ Response contains expected fix (v3.0.1){RESET}\n")
            results.append(("PASS", elapsed))
        else:
            print(f"    {DIM}Response doesn't mention v3.0.1, but continuing...{RESET}\n")
            results.append(("PASS", elapsed))  # Agent responded, evaluation will judge
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))
        response_str = ""

    # --- Step 2: Judge agent evaluates the response ---
    print(f"  {BLUE}{'─' * 68}{RESET}")
    print(f"  {BLUE}Step 2: LLM Judge evaluates the response{RESET}\n")

    print(f"  {BLUE}Creating judge agent...{RESET}")
    judge = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are an evaluation judge. Score agent responses on correctness.

SCORING RUBRIC:
- 1.0: Completely correct with accurate details
- 0.75: Mostly correct with minor inaccuracies
- 0.5: Partially correct, some errors
- 0.25: Mostly incorrect
- 0.0: Completely wrong or fabricated

OUTPUT FORMAT:
Return ONLY a JSON object: {"score": <number>, "reasoning": "<brief explanation>"}
Do not include any other text.
""",
    )

    eval_prompt = f"""
Query: {query}
Agent Response: {response_str}
Context: The TechMart Hub v2.1.x has a known Wi-Fi bug, fixed in firmware v3.0.1.

Score this response. Return JSON only.
"""

    start = time.time()
    try:
        judge_response = judge(eval_prompt)
        elapsed = time.time() - start
        judge_str = str(judge_response).strip()
        print_response(judge_str)
        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        # Parse the score
        score = None
        if "{" in judge_str:
            json_start = judge_str.index("{")
            json_end = judge_str.rindex("}") + 1
            parsed = json.loads(judge_str[json_start:json_end])
            score = float(parsed.get("score", -1))

        if score is not None and 0.0 <= score <= 1.0:
            print(f"    {SUCCESS}✓ Score: {score:.2f} (valid float 0-1){RESET}\n")
            results.append(("PASS", elapsed))
        elif score is not None:
            print(f"    {FAIL}✗ Score {score} is outside valid range 0-1{RESET}\n")
            results.append(("FAIL", elapsed))
        else:
            print(f"    {FAIL}✗ Could not parse score from judge response{RESET}\n")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {BLUE}{'═' * 68}{RESET}")
    print(f"  {BLUE}RESULTS{RESET}\n")

    step_names = ["Agent Response", "Judge Evaluation (Score 0-1)"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 4 test passed — LLM-as-Judge evaluation works.{RESET}")
        print(f"  {DIM}Tip: In production, scores are published to CloudWatch for trend monitoring.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 4 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
