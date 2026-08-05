# Module 1 Demo: Multi-Agent Architecture and Communication Patterns

## Overview

This demo progressively demonstrates why multi-agent architectures are needed and how to implement them using the Strands Agents SDK with Amazon Bedrock.

All parts are **interactive chat loops** — you type queries as a customer and observe agent behavior in real time.

## Prerequisites

- Python 3.10+
- AWS credentials configured (region: `ap-southeast-1`)
- Install dependencies:

```bash
pip install strands-agents strands-agents-tools
```

## Demo Structure

| Part | File | Concept | Duration |
|------|------|---------|----------|
| 1 | `part1_single_agent.py` | Single agent limitations | ~5 min |
| 2 | `part2_multi_agent_orchestrator.py` | Framework-layer orchestration | ~10 min |
| 3 | `part3_agent_as_tool.py` | Agent-as-tool / MCP pattern | ~8 min |
| 4 | `part4_shared_memory.py` | Memory sharing across agents | ~8 min |

---

## How to Run

```bash
cd demos/module1-multi-agent

python part1_single_agent.py    # Single agent struggling
python part2_multi_agent_orchestrator.py   # Orchestrator routing
python part3_agent_as_tool.py   # Agent-as-tool reuse
python part4_shared_memory.py   # Shared memory collaboration
```

Type `quit` or `exit` to end any session.

---

## Suggested Prompts for Each Part

### Part 1: Single Agent (Show the Problem)

The goal is to demonstrate cognitive load by asking multi-domain queries in sequence, forcing the single agent to juggle billing, tech support, and product knowledge.

**Prompt sequence (use these in order):**

```
1. Hi, I was charged $9.99 but I cancelled my subscription last week. Order TM-78432.

2. Also, my TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3.

3. While we sort that out, I need a laptop for my daughter starting college. Budget $600-800, she'll do writing and light video editing.

4. Back to my subscription — since I was incorrectly billed, can I also get a refund on the express shipping?

5. If I buy the TechMart Pro 15, will it work with my Hub that keeps disconnecting? Can I apply my refund credit toward the purchase?
```

**What to point out:**
- By query 3-4, the agent starts mixing up billing procedures with other domains
- The agent can't go deep on any topic because it's maintaining breadth
- Context window fills up with cross-domain history, reducing response quality

---

### Part 2: Multi-Agent Orchestrator (Show the Solution)

Use the **same prompts as Part 1** to directly compare behavior. The orchestrator will route each query to the appropriate specialist.

**Prompt sequence:**

```
1. Hi, I was charged $9.99 but I cancelled my subscription last week. Order TM-78432.

2. My TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3.

3. I need a laptop for my daughter. Budget $600-800, writing and light video editing.

4. Since I was incorrectly billed, can I also get a refund on my express shipping?

5. If I buy the TechMart Pro 15, will it work with my Hub? Can I use my refund as credit?
```

**What to point out:**
- Watch the routing indicators: 📋 (billing), 🔧 (tech), 🛍️ (product)
- Each specialist gives deeper, more accurate domain answers
- Query 5 gets decomposed and sent to multiple specialists
- Specialists don't get polluted by unrelated domain context

---

### Part 3: Agent-as-Tool (Show Reusability)

You choose between a Sales Agent or Support Agent. Both reuse the same underlying tools (product_lookup, compatibility_check, order_status).

**Sales Agent prompts (choose option 1):**

```
1. I want to set up a smart home. Will the TechMart Hub work with your cameras?

2. I also have a TechMart Air laptop — can I use it as a controller for the Hub?

3. What about the TechMart Titan? How does it compare for smart home use?
```

**Support Agent prompts (choose option 2):**

```
1. My order TM-78432 arrived but the motion sensors aren't showing up on my Hub. Are they compatible?

2. Can you look up the specs on the TechMart Hub? I want to know what firmware it needs.

3. I'm thinking of adding cameras too. Will the Smart Camera work with my Hub?
```

**What to point out:**
- Both agents call the same `product_lookup` and `compatibility_check` tools
- The tools have clear input/output contracts (like MCP tool interfaces)
- You could swap the internal implementation without changing the consumer agents
- This is how AgentCore Gateway exposes tools to multiple agents

---

### Part 4: Shared Memory (Show Collaboration)

You describe a technical issue, then 3 agents collaborate in sequence (Diagnose → Resolve → Follow-up), sharing findings via memory.

**Suggested issue descriptions:**

```
Option A: My TechMart Hub (firmware v2.1.3) keeps dropping Wi-Fi every few minutes. I also added 2 motion sensors yesterday and they aren't appearing in the app.

Option B: My smart cameras keep going offline at night. I have 3 cameras connected through my TechMart Hub. The Hub seems fine otherwise.

Option C: I just set up my TechMart Hub but it won't pair with my motion sensors. The LED on the sensors blinks red instead of blue.
```

**What to point out:**
- Watch 💾 (memory write) and 📖 (memory read) indicators
- The Resolution Agent reads the diagnosis from memory — it never saw the original customer message
- The Follow-up Agent reconstructs the full case from memory alone
- The final "Shared Memory — Final State" shows the audit trail with distinct `actor_id`s
- This maps directly to AgentCore Memory: shared `memory_id`, unique `actor_id` per agent

---

## Scenario

All parts use the same fictional company: **TechMart** (electronics e-commerce).

Products:
- TechMart Air ($599) — lightweight laptop
- TechMart Pro 15 ($799) — mid-range with video editing
- TechMart Titan ($1,299) — gaming/creative pro
- TechMart Hub ($149) — smart home controller
- Smart Camera ($79) — 1080p, night vision
- Motion Sensor ($29) — Zigbee, 120° detection

---

## Key Takeaways by Part

| Part | Concept | Takeaway |
|------|---------|----------|
| 1 | Single agent limits | Cognitive overload degrades quality across all domains |
| 2 | Orchestrator pattern | Centralized routing + specialized agents = deep expertise |
| 3 | Agent-as-tool | Clear interfaces enable reuse across different systems |
| 4 | Shared memory | Agents collaborate via memory without coupling |
| 5 | Graph & Swarm (app only) | Deterministic pipelines (Graph) vs. autonomous collaboration (Swarm) |

---

## Adjusting the Model

The demos use `apac.anthropic.claude-sonnet-4-20250514-v1:0` (APAC inference profile for ap-southeast-1).

To use a different region or model, update the `MODEL_ID` variable at the top of each file:

```python
# US region example:
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"

# Global example:
MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
```
