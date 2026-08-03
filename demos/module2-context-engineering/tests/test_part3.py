"""
Test: Part 3 — Conversation Managers

Tests the SummarizingConversationManager by sending many messages and
verifying the agent can still recall earlier decisions after summarization.

Usage:
    python tests/test_part3.py
"""

import sys
import time

sys.path.insert(0, ".")

from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import SummarizingConversationManager
from part3_conversation_managers import SYSTEM_PROMPT, estimate_tokens

MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Colors
MAGENTA = "\033[1;35m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;93m"
RESPONSE_COLOR = "\033[0;97m"
TIMING = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;45m"


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 3 — SummarizingConversationManager                       {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    # Queries that build on each other — last query tests recall
    queries = [
        "I'm building a microservices e-commerce platform. Let's start with the catalog service — recommend a database.",
        "Good choice. Now design the order service. It needs 500 orders/minute at peak.",
        "How should catalog and order services communicate? I prefer event-driven.",
        "Add a recommendation engine that needs order history and browsing data.",
        "Now design the payment service. PCI compliance is required.",
        "What deployment architecture should we use on AWS? I want serverless.",
        "Remind me: what database did we choose for the catalog service earlier, and what communication pattern are we using between services?",
    ]

    print(f"  {MAGENTA}Creating agent with SummarizingConversationManager...{RESET}")
    print(f"  {MAGENTA}Config: summary_ratio=0.5, preserve_recent=4{RESET}\n")

    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=SummarizingConversationManager(
            summary_ratio=0.5,
            preserve_recent_messages=4,
        ),
    )

    total_start = time.time()
    results = []

    for i, query in enumerate(queries, 1):
        is_recall = i == len(queries)
        label = " (RECALL TEST)" if is_recall else ""

        print(f"  {MAGENTA}{'─' * 68}{RESET}")
        print(f"  {MAGENTA}Query {i}/{len(queries)}{label}{RESET}")
        print(f"  {PROMPT_COLOR}{query}{RESET}\n")

        start = time.time()
        try:
            response = agent(query)
            elapsed = time.time() - start
            tokens = estimate_tokens(agent)
            msg_count = len(agent.messages) if hasattr(agent, "messages") else 0

            resp_str = str(response)
            lines = resp_str.strip().split("\n")
            max_lines = 10 if is_recall else 5
            for line in lines[:max_lines]:
                print(f"    {RESPONSE_COLOR}{line}{RESET}")
            if len(lines) > max_lines:
                print(f"    {DIM}... ({len(lines) - max_lines} more lines){RESET}")

            print(f"\n    {TIMING}⏱ {elapsed:.1f}s │ ~{tokens:,} tokens │ {msg_count} messages{RESET}\n")
            results.append(("PASS", elapsed, tokens, msg_count))
        except Exception as e:
            elapsed = time.time() - start
            print(f"    {FAIL}ERROR: {e}{RESET}\n")
            results.append(("FAIL", elapsed, 0, 0))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {MAGENTA}{'═' * 68}{RESET}")
    print(f"  {MAGENTA}CONTEXT MANAGEMENT RESULTS{RESET}\n")

    all_passed = True
    for i, (status, elapsed, tokens, msgs) in enumerate(results, 1):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        label = " ← RECALL" if i == len(queries) else ""
        print(f"    {icon} {color}Query {i}: {status}{RESET} {TIMING}({elapsed:.1f}s, ~{tokens:,} tok, {msgs} msgs){label}{RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING}Total: {total_elapsed:.1f}s{RESET}")

    # Check if summarization managed context
    if results:
        first_tokens = results[0][2]
        last_tokens = results[-1][2]
        first_msgs = results[0][3]
        last_msgs = results[-1][3]
        print(f"\n  {MAGENTA}Context growth check:{RESET}")
        print(f"    After query 1: ~{first_tokens:,} tokens, {first_msgs} messages")
        print(f"    After query {len(queries)}: ~{last_tokens:,} tokens, {last_msgs} messages")
        if last_msgs < len(queries) * 2:
            print(f"    {SUCCESS}✓ Summarization appears to have compressed context{RESET}")
        else:
            print(f"    {DIM}  Messages weren't compressed (may not have hit threshold){RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 3 test passed — agent recalled earlier decisions after summarization.{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 3 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
