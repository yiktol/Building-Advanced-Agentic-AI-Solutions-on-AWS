# Module 2 Demo: Context Engineering and Performance Optimization

## Overview

This demo progressively demonstrates how **context accumulates** in agentic systems
and the strategies to manage it effectively using the Strands Agents SDK with Amazon Bedrock.

All parts are **interactive chat loops** — type queries and observe context behavior in real time.

## Prerequisites

- Python 3.10+
- AWS credentials configured (region: `ap-southeast-1`)
- Install dependencies:

```bash
pip install strands-agents strands-agents-tools
```

## Demo Structure

| Part | File | Concept | Strategy |
|------|------|---------|----------|
| 1 | `part1_context_exhaustion.py` | Context as finite resource | Show the problem |
| 2 | `part2_prompt_caching.py` | Prompt caching with Bedrock | Write (cache static context) |
| 3 | `part3_conversation_managers.py` | Summarizing/sliding window | Compress context |
| 4 | `part4_context_isolation.py` | Multi-agent boundaries | Isolate context |
| 5 | `part5_tool_design.py` | Information-dense tools | Select relevant context |

---

## How to Run

```bash
cd demos/module2-context-engineering

python part1_context_exhaustion.py
python part2_prompt_caching.py
python part3_conversation_managers.py
python part4_context_isolation.py
python part5_tool_design.py
```

Type `quit` or `exit` to end any session.

---

## Suggested Prompts

### Part 1: Context Exhaustion (Show the Problem)

Build up a long conversation to watch token counts grow and quality degrade:

```
1. I need help planning a corporate retreat for 50 people in Bali for next March.
2. We need team building activities, preferably water sports and cultural experiences.
3. Budget is $150,000. Break down accommodation, activities, meals, and transport.
4. Actually, 12 of the team are vegetarian and 3 have mobility issues. Adjust the plan.
5. Now compare this with doing it in Thailand instead. Same requirements.
6. Add a detailed day-by-day itinerary for the Bali option with time slots.
7. What are the visa requirements for a team coming from US, UK, India, and Brazil?
8. Summarize everything we've discussed so far in a one-page executive brief.
```

**Observe:** Token counts rising, response time increasing, later answers losing details from early queries.

### Part 2: Prompt Caching

The demo runs automatically — comparing cached vs uncached latency. No prompts needed.

### Part 3: Conversation Managers

```
1. I'm building a microservices architecture for an e-commerce platform.
2. The catalog service needs to handle 10,000 products with real-time inventory.
3. What database should I use for the catalog? Consider read-heavy workloads.
4. Now design the order service. It needs to handle 500 orders per minute at peak.
5. How should the catalog and order services communicate? Events vs direct calls?
6. Add a recommendation engine. It needs access to order history and browsing data.
7. What about the payment service? PCI compliance is required.
8. Design the deployment architecture on AWS using ECS Fargate.
9. What's our database choice from earlier? (tests if summarization retained this)
10. Summarize the full architecture we've designed.
```

**Observe:** The summarizer kicks in after several messages — agent still remembers earlier decisions.

### Part 4: Context Isolation

```
1. Research renewable energy market trends for 2025-2026 in Southeast Asia.
2. Analyze the financial viability of solar vs wind for a 50MW project in Vietnam.
3. Write a 3-paragraph executive summary combining the research and analysis.
```

**Observe:** Each sub-agent gets only its relevant context, not the full history.

### Part 5: Tool Design

Compare verbose vs optimized tool responses with:

```
1. Look up customer order TM-78432 and their full account history.
2. What products are compatible with the TechMart Hub?
3. Show me the customer's support ticket history and current open issues.
```

**Observe:** Token difference between verbose and optimized tool outputs.

---

## Key Takeaways

| Part | Takeaway |
|------|----------|
| 1 | Context is finite — quality degrades as it fills |
| 2 | Cache static content to save cost and reduce latency |
| 3 | Conversation managers compress history intelligently |
| 4 | Multi-agent boundaries keep each agent's context lean |
| 5 | Tool design directly impacts token efficiency |

---

## Adjusting the Model

Update `MODEL_ID` at the top of each file:

```python
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
```
