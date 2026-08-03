"""
Module 2 - Part 1: Context as a Finite Resource

Demonstrates how context accumulates with each interaction and how
performance degrades as the context window fills up.

Shows:
- Token count growing with each exchange
- Response time increasing as context grows
- Context failure modes (distraction, losing earlier details)
"""

import time
from strands import Agent
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

SYSTEM_PROMPT = """You are an expert travel planner and corporate event coordinator.
You help companies plan retreats, team-building events, and corporate travel.

You have deep knowledge of:
- Destinations worldwide (logistics, visa requirements, weather patterns)
- Team building activities (water sports, cultural, adventure, indoor)
- Budget planning (accommodation, transport, meals, activities breakdown)
- Dietary requirements and accessibility accommodations
- Day-by-day itinerary planning with time management

Always provide detailed, specific answers with numbers, dates, and logistics.
Reference earlier parts of our conversation when relevant.
"""


def count_messages(agent: Agent) -> int:
    """Count messages in the agent's conversation history."""
    if hasattr(agent, "messages"):
        return len(agent.messages)
    return 0


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
    # Rough approximation: ~4 chars per token
    return total_chars // 4


def run_demo():
    print("=" * 70)
    print("PART 1: Context as a Finite Resource")
    print("=" * 70)
    print()
    print("Watch how context accumulates with each exchange.")
    print("Token count and response time are tracked per message.")
    print()
    print("Type 'quit' or 'exit' to end. Type 'stats' to see context stats.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

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

        if user_input.lower() == "stats":
            print(f"\n  📊 Context Statistics:")
            print(f"     Messages: {count_messages(agent)}")
            print(f"     Est. tokens: ~{estimate_tokens(agent):,}")
            print(f"     Exchanges: {exchange_count}")
            if timings:
                print(f"     Avg response time: {sum(timings)/len(timings):.1f}s")
                print(f"     First response: {timings[0]:.1f}s")
                print(f"     Last response: {timings[-1]:.1f}s")
            continue

        exchange_count += 1
        start = time.time()
        print()
        response = agent(user_input)
        elapsed = time.time() - start
        timings.append(elapsed)

        token_est = estimate_tokens(agent)
        msg_count = count_messages(agent)

        print(f"\n  Agent: {response}")
        print(f"\n  ┌─────────────────────────────────────────┐")
        print(f"  │ 📊 Exchange #{exchange_count:<3} │ ⏱ {elapsed:.1f}s │ 🎯 ~{token_est:,} tokens │")
        print(f"  │    Messages in context: {msg_count:<16}│")
        print(f"  └─────────────────────────────────────────┘")

    # Final stats
    if timings:
        print(f"\n{'=' * 70}")
        print("CONTEXT GROWTH SUMMARY")
        print(f"{'=' * 70}")
        print(f"  Total exchanges: {exchange_count}")
        print(f"  Final token estimate: ~{estimate_tokens(agent):,}")
        print(f"  Response time trend:")
        for i, t in enumerate(timings, 1):
            bar = "█" * int(t * 2)
            print(f"    Query {i:2d}: {bar} {t:.1f}s")
        print()
        print("  Observation: As context grows, response time typically increases")
        print("  and the agent may lose details from earlier exchanges.")
    print()


if __name__ == "__main__":
    run_demo()
