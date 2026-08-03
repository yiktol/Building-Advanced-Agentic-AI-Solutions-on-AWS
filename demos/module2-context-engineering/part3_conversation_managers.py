"""
Module 2 - Part 3: Context Compression with Conversation Managers

Demonstrates how Strands conversation managers automatically compress
context when it grows too large, preserving essential information.

Shows:
- NullConversationManager: No compression (baseline)
- SlidingWindowConversationManager: Drops oldest messages
- SummarizingConversationManager: Intelligently summarizes older context
"""

import time
from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import (
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

SYSTEM_PROMPT = """You are a senior software architect helping design a microservices system.

You have deep expertise in:
- Distributed systems architecture
- Database selection (SQL, NoSQL, graph, time-series)
- Event-driven architecture (Kafka, SQS, EventBridge)
- Container orchestration (ECS, EKS, Fargate)
- API design (REST, GraphQL, gRPC)
- Cloud-native patterns on AWS

When designing systems:
1. Ask clarifying questions when needed
2. Reference earlier decisions in the conversation
3. Build incrementally on previous architectural choices
4. Provide specific technology recommendations with rationale

Always maintain consistency with prior decisions in this conversation.
"""


def estimate_tokens(agent: Agent) -> int:
    """Estimate tokens from conversation message content."""
    total_chars = 0
    if hasattr(agent, "messages"):
        for msg in agent.messages:
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and "text" in block:
                        total_chars += len(block["text"])
            elif isinstance(msg.get("content"), str):
                total_chars += len(msg["content"])
    return total_chars // 4


def run_demo():
    print("=" * 70)
    print("PART 3: Context Compression with Conversation Managers")
    print("=" * 70)
    print()
    print("Compare three approaches to managing conversation context:")
    print("  [1] No compression (context grows unbounded)")
    print("  [2] Sliding window (drops oldest messages)")
    print("  [3] Summarizing (compresses older context intelligently)")
    print()

    # Let user choose
    while True:
        choice = input("  Select mode (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            break
        print("  Please enter 1, 2, or 3.")

    model = BedrockModel(model_id=MODEL_ID)

    if choice == "1":
        mode_name = "No Compression (NullConversationManager)"
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            conversation_manager=None,  # No compression
        )
    elif choice == "2":
        mode_name = "Sliding Window (keeps last 10 messages)"
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            conversation_manager=SlidingWindowConversationManager(window_size=10),
        )
    else:
        mode_name = "Summarizing (compresses after 6 messages, preserves recent 4)"
        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            conversation_manager=SummarizingConversationManager(
                summary_ratio=0.5,
                preserve_recent_messages=4,
            ),
        )

    print()
    print(f"  Mode: {mode_name}")
    print(f"{'─' * 70}")
    print("  Design a microservices system. Watch context metrics after each exchange.")
    print("  Type 'quit' to end. Type 'recall' to test memory of earlier decisions.")
    print(f"{'─' * 70}")

    exchange_count = 0
    timings = []

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "recall":
            user_input = "Briefly list all the key architectural decisions we've made so far in this conversation, including specific technologies chosen."

        exchange_count += 1
        start = time.time()
        print()
        response = agent(user_input)
        elapsed = time.time() - start
        timings.append(elapsed)

        token_est = estimate_tokens(agent)
        msg_count = len(agent.messages) if hasattr(agent, "messages") else 0

        print(f"\n  Architect: {response}")
        print(f"\n  ┌─────────────────────────────────────────────────┐")
        print(f"  │ Exchange #{exchange_count:<3} │ ⏱ {elapsed:.1f}s │ ~{token_est:,} tokens │ {msg_count} msgs │")
        print(f"  └─────────────────────────────────────────────────┘")

    # Summary
    if timings:
        print(f"\n{'═' * 70}")
        print(f"  SESSION SUMMARY — {mode_name}")
        print(f"{'═' * 70}")
        print(f"  Exchanges: {exchange_count}")
        print(f"  Final context: ~{estimate_tokens(agent):,} tokens in {len(agent.messages) if hasattr(agent, 'messages') else 0} messages")
        print(f"  Avg response time: {sum(timings)/len(timings):.1f}s")
        print()
        print("  Response time trend:")
        for i, t in enumerate(timings, 1):
            bar = "█" * int(t * 2)
            print(f"    {i:2d}: {bar} {t:.1f}s")
        print()

        if choice == "1":
            print("  💡 With no compression, context grows linearly.")
            print("     Try mode 3 (Summarizing) to see how it manages growth.")
        elif choice == "2":
            print("  💡 Sliding window keeps context bounded but LOSES early information.")
            print("     Try 'recall' after many messages — early decisions may be forgotten.")
        else:
            print("  💡 Summarizing compresses older messages into a structured summary.")
            print("     Earlier decisions are preserved in summary form, not lost entirely.")
        print()


if __name__ == "__main__":
    run_demo()
