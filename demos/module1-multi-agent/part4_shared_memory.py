"""
Module 1 - Part 4: Shared Memory Across Agents

Demonstrates how multiple agents can share state and context using
a shared memory store — analogous to AgentCore Memory with shared
memory_id and unique actor_ids.

This solves the problem of agents needing to collaborate without
duplicating context in each agent's context window.

Benefits shown:
- Agents share discoveries without bloating each other's context
- Each agent maintains its own identity (actor_id) while accessing shared state
- Handoffs between agents preserve continuity
- Memory persists across interactions
"""

import json
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# SIMULATED SHARED MEMORY (In production, this would be AgentCore Memory)
# =============================================================================

class SharedMemoryStore:
    """
    Simulates AgentCore Memory behavior:
    - Shared memory_id across agents
    - Unique actor_id per agent
    - Session-scoped short-term memory
    - Queryable by any agent in the session
    """

    def __init__(self, memory_id: str, session_id: str):
        self.memory_id = memory_id
        self.session_id = session_id
        self.records: list[dict] = []

    def write(self, actor_id: str, content: dict, memory_type: str = "observation"):
        """Write a memory record (like AgentCore Memory put_memory_record)."""
        record = {
            "memory_id": self.memory_id,
            "session_id": self.session_id,
            "actor_id": actor_id,
            "content": content,
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
        }
        self.records.append(record)
        return record

    def read_all(self) -> list[dict]:
        """Read all memory records in this session."""
        return self.records

    def read_by_actor(self, actor_id: str) -> list[dict]:
        """Read records written by a specific agent."""
        return [r for r in self.records if r["actor_id"] == actor_id]

    def read_by_type(self, memory_type: str) -> list[dict]:
        """Read records of a specific type."""
        return [r for r in self.records if r["memory_type"] == memory_type]

    def summary(self) -> str:
        """Get a human-readable summary of all shared memory."""
        if not self.records:
            return "No shared memories yet."
        lines = []
        for r in self.records:
            lines.append(
                f"  [{r['actor_id']}] ({r['memory_type']}): "
                f"{json.dumps(r['content'], indent=None)}"
            )
        return "\n".join(lines)


# Global shared memory instance for this demo session
shared_memory = SharedMemoryStore(
    memory_id="customer-session-memory",
    session_id="session-demo-001"
)


# =============================================================================
# TOOLS THAT INTERACT WITH SHARED MEMORY
# =============================================================================

@tool
def save_to_shared_memory(actor_id: str, observation: str, memory_type: str) -> str:
    """Save an observation or finding to shared memory so other agents can access it.

    Args:
        actor_id: The identity of the agent saving (e.g., "billing-agent", "tech-agent")
        observation: What was discovered or decided
        memory_type: Type of memory - "observation", "diagnosis", "action_taken", or "recommendation"
    """
    record = shared_memory.write(
        actor_id=actor_id,
        content={"observation": observation},
        memory_type=memory_type,
    )
    print(f"    💾 [Memory Write] {actor_id} saved: {observation[:60]}...")
    return f"Saved to shared memory: {observation}"


@tool
def read_shared_memory() -> str:
    """Read all observations from shared memory to understand what other agents have discovered."""
    summary = shared_memory.summary()
    print(f"    📖 [Memory Read] Retrieving shared context...")
    return f"Shared memory contents:\n{summary}"


# =============================================================================
# SPECIALIZED AGENTS WITH MEMORY ACCESS
# =============================================================================

def create_diagnostic_agent() -> Agent:
    """Agent that diagnoses technical issues and shares findings."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a Diagnostic Agent for TechMart technical issues.

Your role:
1. Diagnose technical problems based on customer description
2. Save your findings to shared memory so other agents can use them
3. Check shared memory for context from other agents

DIAGNOSTIC KNOWLEDGE:
- TechMart Hub firmware v2.1.x: KNOWN BUG causing Wi-Fi dropouts (fix: update to v3.0.1)
- Motion sensors require Zigbee pairing mode (hold button 5s until LED blinks blue)
- Smart cameras on Wi-Fi 5 networks may have 2-3s lag vs Wi-Fi 6

When you diagnose an issue:
1. Read shared memory first to see if other agents have relevant context
2. Perform your diagnosis
3. Save your diagnosis to shared memory with actor_id="diagnostic-agent"

Be thorough but concise in your diagnoses.
""",
        tools=[save_to_shared_memory, read_shared_memory],
    )


def create_resolution_agent() -> Agent:
    """Agent that resolves issues based on diagnoses from other agents."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a Resolution Agent for TechMart.

Your role:
1. Check shared memory for diagnoses from the Diagnostic Agent
2. Provide step-by-step resolution based on the diagnosis
3. Save the resolution steps to shared memory for records

RESOLUTION PLAYBOOKS:
- Firmware update: Settings > System > Check Updates > Install > Restart (5 min)
- Zigbee re-pairing: Hub Settings > Devices > Add > Hold sensor button 5s > Confirm
- Wi-Fi channel optimization: Hub Settings > Network > Auto-Channel > Apply
- Factory reset (last resort): Hold Hub power button 15s > Reconfigure

When resolving:
1. ALWAYS read shared memory first to get the diagnosis
2. Match diagnosis to the appropriate playbook
3. Provide clear, numbered steps to the customer
4. Save your resolution to shared memory with actor_id="resolution-agent"

Never guess — if no diagnosis exists in shared memory, ask for one first.
""",
        tools=[save_to_shared_memory, read_shared_memory],
    )


def create_followup_agent() -> Agent:
    """Agent that handles follow-up and checks if the issue was resolved."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a Follow-up Agent for TechMart.

Your role:
1. Review the full history in shared memory (diagnosis + resolution)
2. Summarize what was done for the customer
3. Suggest preventive measures
4. Offer additional help if needed

When following up:
1. Read shared memory to see the full journey
2. Summarize: what was the problem, what was diagnosed, what was done
3. Add preventive recommendations
4. Save your summary with actor_id="followup-agent"

Be warm and helpful. Make the customer feel their issue was fully handled.
""",
        tools=[save_to_shared_memory, read_shared_memory],
    )


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 4: Shared Memory Across Agents")
    print("=" * 70)
    print()
    print("Three agents collaborate via shared memory:")
    print("  🔬 Diagnostic Agent — identifies the root cause")
    print("  🔧 Resolution Agent — provides fix based on diagnosis")
    print("  ✅ Follow-up Agent — summarizes and suggests prevention")
    print()
    print("Shared Memory simulates AgentCore Memory with:")
    print(f"  memory_id: {shared_memory.memory_id}")
    print(f"  session_id: {shared_memory.session_id}")
    print()
    print("Describe a technical issue to start the multi-agent workflow.")
    print("Type 'quit' or 'exit' to end the conversation.")
    print("=" * 70)

    # --- Step 1: Get the customer issue ---
    print()
    try:
        user_issue = input("  Describe your issue: ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if not user_issue or user_issue.lower() in ("quit", "exit"):
        return

    # --- Step 2: Diagnostic Agent ---
    print(f"\n{'━' * 70}")
    print("  STEP 1: 🔬 Diagnostic Agent analyzing your issue...")
    print(f"{'━' * 70}\n")

    diag_agent = create_diagnostic_agent()
    response = diag_agent(
        f"Customer reports: {user_issue}\n\n"
        "Diagnose the root cause(s). Save your findings to shared memory."
    )
    print(f"\n  Diagnostic Agent: {response}\n")

    # --- Step 3: Resolution Agent ---
    print(f"\n{'━' * 70}")
    print("  STEP 2: 🔧 Resolution Agent providing fix...")
    print(f"{'━' * 70}\n")

    resolution_agent = create_resolution_agent()
    response = resolution_agent(
        "A customer needs help. Check shared memory for the diagnosis and "
        "provide step-by-step resolution. Save your resolution plan to shared memory."
    )
    print(f"\n  Resolution Agent: {response}\n")

    # --- Step 4: Follow-up Agent ---
    print(f"\n{'━' * 70}")
    print("  STEP 3: ✅ Follow-up Agent summarizing...")
    print(f"{'━' * 70}\n")

    followup_agent = create_followup_agent()
    response = followup_agent(
        "Review shared memory for the complete case history. "
        "Provide a summary for the customer and suggest preventive measures. "
        "Save your summary to shared memory."
    )
    print(f"\n  Follow-up Agent: {response}\n")

    # --- Show final memory state ---
    print(f"\n{'━' * 70}")
    print("  📝 SHARED MEMORY — Final State (Audit Trail)")
    print(f"{'━' * 70}\n")
    print(shared_memory.summary())

    # --- Optional follow-up chat ---
    print(f"\n{'━' * 70}")
    print("  You can now ask follow-up questions (any agent can respond).")
    print("  Type 'quit' or 'exit' to end.")
    print(f"{'━' * 70}")

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

        print()
        response = followup_agent(user_input)
        print(f"\n  Follow-up Agent: {response}")

    print("\n" + "=" * 70)
    print("END OF PART 4")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
