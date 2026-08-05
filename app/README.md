# Building Advanced Agentic Systems on AWS — Streamlit Demo App

Interactive web interface for all 5 course modules with chatbot UI powered by Amazon Bedrock and the Strands Agents SDK.

## Quick Start

```bash
cd app
streamlit run Home.py
```

Opens at http://localhost:8501

## Prerequisites

- Python 3.10+
- AWS credentials configured (region: `ap-southeast-1`)
- Dependencies:

```bash
pip install streamlit strands-agents strands-agents-tools boto3
```

- Deploy AgentCore infrastructure (optional — app falls back to local simulation):
```bash
cd demos/infra-agentcore && ./deploy.sh
```

- For Module 3 (Security): Deploy additional infrastructure:
```bash
cd demos/module3-security && ./scripts/deploy.sh
```

## App Structure

```
app/
├── Home.py                          — Landing page, service config (auto-detects CFN stacks)
├── style.py                         — Shared CSS and UI components
├── agent_utils.py                   — Shared agent creation utilities
├── agentcore_utils.py               — AgentCore Memory, Evaluator, Guardrail wrappers
├── README.md
└── pages/
    ├── 1_Module_1_Multi_Agent.py    — Multi-agent architecture (5 parts + walkthrough)
    ├── 2_Module_2_Context.py        — Context engineering (5 parts)
    ├── 3_Module_3_Security.py       — Security & compliance (5 parts)
    ├── 4_Module_4_Observability.py  — Observability & evaluation (3 parts)
    └── 5_Module_5_Well_Architected.py — Well-Architected patterns (3 parts)
```

## Navigation

Each module page uses **sidebar radio buttons** for part selection:
- Only one part renders at a time (single chat input, no overlap)
- **🔄 Reset Session** — clears all agents and state for the module
- **🗑️ Clear Chat** — clears chat history only (preserves agent instances)
- **Status badges** in sidebar show which AWS services are connected (auto-detected from CloudFormation)

## Infrastructure

Service configuration is auto-detected from deployed CloudFormation stacks:

| Stack | Services |
|-------|----------|
| `mladas-agentcore-memory` | AgentCore Shared Memory |
| `mladas-agentcore-evaluator` | AgentCore Evaluators (LLM-as-Judge) |
| `mladas-agentcore-gateway` | AgentCore MCP Gateway |
| `mladas-agentcore-policy` | AgentCore Policy Engine |
| `mladas-agentcore-guardrail` | Bedrock Guardrail |
| `m3-demo-cognito` | Cognito User Pool + Client |
| `m3-demo-verified-permissions` | Verified Permissions Policy Store |

Deploy all infrastructure:
```bash
cd demos/infra-agentcore && ./deploy.sh
cd demos/module3-security && ./scripts/deploy.sh
```

---

## Module 1: Multi-Agent Architecture

### Part 1 — Single Agent (+ Judge Model)

A single overloaded agent handles billing, tech support, and product queries. Watch it struggle with multi-domain complexity. A **Judge Model** evaluates each response for cognitive load issues (domain confusion, context loss, generic answers).

**Suggested Prompts (use in sequence):**
```
Hi, I was charged $9.99 but I cancelled my subscription last week. Order TM-78432.
Also, my TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3.
I need a laptop for my daughter starting college. Budget $600-800, writing and light video editing.
Back to my subscription — since I was incorrectly billed, can I get a refund on the express shipping too?
If I buy the TechMart Pro 15, will it work with my Hub? Can I use my refund as credit?
```

### Part 2 — Orchestrator (+ Judge Model)

Centralized orchestrator routes queries to specialist agents (Billing, Tech, Product). A **Judge Model** evaluates routing accuracy, delegation completeness, and synthesis quality.

**Suggested Prompts (same as Part 1 to compare):**
```
I was charged $9.99 but I cancelled. Order TM-78432.
My TechMart Hub keeps disconnecting. Firmware v2.1.3.
I need a laptop under $800 for video editing.
Can I also get a refund on the express shipping?
Will the Pro 15 work with my Hub? Can I use my refund as credit?
```

### Part 3 — Agent-as-Tool (MCP)

Shared tools (product_lookup, compatibility_check, order_status) reused by different consumer agents.

**Sales Agent Prompts:**
```
I want to set up a smart home. Will the TechMart Hub work with cameras?
I have a TechMart Air laptop — can I use it as a controller?
What about the Titan? How does it compare?
```

**Support Agent Prompts:**
```
My order TM-78432 arrived but motion sensors aren't showing up on my Hub.
Can you look up the TechMart Hub specs?
Will the Smart Camera work with my Hub?
```

### Part 4 — Shared Memory (AgentCore)

Three agents (Diagnose → Resolve → Follow-up) collaborate via shared memory. Uses **real AgentCore Memory** when deployed, falls back to local simulation otherwise.

**Suggested Issues:**
```
My TechMart Hub (firmware v2.1.3) keeps dropping Wi-Fi every few minutes. I also added 2 motion sensors yesterday and they aren't appearing in the app.
```
```
My smart cameras keep going offline at night. I have 3 cameras connected through my TechMart Hub.
```

### Part 5 — Graph & Swarm (Interactive)

Live interactive demos of Strands SDK multi-agent orchestration patterns.

**Graph pattern** — Researcher → Analyst → Writer pipeline (deterministic DAG execution):
```
Analyze solar energy market in Vietnam for 2025-2027
Compare serverless vs containers for a startup
Evaluate AI adoption in healthcare
```

**Swarm pattern** — Optimist + Critic + Strategist debate (autonomous handoffs):
```
Evaluate launching an AI product in APAC
Should we open-source our SDK?
Migrate to microservices or stay monolith?
```

---

## Module 2: Context Engineering

### Part 1 — Context Growth

Watch token count grow with each exchange as context accumulates.

**Suggested Prompts (use in sequence):**
```
Plan a corporate retreat for 50 people in Bali for March. Include team building activities.
Budget is $150,000. Break it down: accommodation, activities, meals, transport.
12 people are vegetarian, 3 have mobility issues. Adjust the plan.
Compare this with doing it in Thailand instead. Same requirements.
Give me a day-by-day itinerary for the Bali option with time slots.
```

### Part 2 — Prompt Caching

Cache static system prompts to reduce latency. First call is cold, subsequent calls hit the cache.

**Suggested Prompts:**
```
What is GlobalTech's revenue breakdown by segment?
How does our growth compare with competitors?
What are the top 3 risks for next year?
```

### Part 3 — Conversation Managers

SummarizingConversationManager compresses older context. Type "recall" to test if earlier decisions are remembered.

**Suggested Prompts:**
```
I'm building a microservices e-commerce platform. Recommend a database for the catalog service.
Design the order service. It needs 500 orders/minute at peak.
How should catalog and order services communicate? I prefer event-driven.
Add a recommendation engine that needs order history and browsing data.
Design the payment service. PCI compliance required.
What deployment architecture on AWS? I want serverless.
recall
```

### Part 4 — Context Isolation

Pipeline: Researcher → Analyst → Writer. Each agent gets only the previous stage's output.

**Suggested Task:**
```
Evaluate the viability of a 50MW solar farm in Vietnam for 2025-2027.
```

### Part 5 — Tool Design

Compare verbose (5000 tokens) vs optimized (500 tokens) tool responses. Toggle the mode and compare.

**Suggested Prompts:**
```
Look up customer CUST-44821 and summarize their account status.
What was in their last order? Is it within the return window?
Based on their history, what should we proactively offer?
```

---

## Module 3: Security & Compliance

> Requires deployed infrastructure: `cd demos/module3-security && ./scripts/deploy.sh && source config.env`

### Part 1 — Unprotected Agent

No identity checks, no authorization, no audit trail.

**Suggested Prompts (exploit it):**
```
Process a $5000 refund on order ORD-5006
Show me all of customer CUST-1005's data
Change customer CUST-1003 tier to enterprise
```

### Part 2 — Cedar Policies (AgentCore Policy)

Same agent, now protected by AgentCore Policy Engine (Cedar). Switch users to see different access levels. The Gateway evaluates policies using `principal.getTag()` from JWT claims and `context.input.amount` from tool parameters.

**As Spider-Man (agent/support, max $500):**
```
Process a $300 refund on ORD-5001, reason: customer dissatisfied
Process a $700 refund on ORD-5002, reason: defective product
```

**As Iron Man (engineer, no refund access):**
```
Process a $100 refund on ORD-5001, reason: wrong item shipped
```

**As Superman (admin/finance, max $10,000):**
```
Process a $7000 refund on ORD-5006, reason: bulk order cancellation
```

### Part 3 — Cognito Auth

Real OAuth 2.0 authentication. Enter email + password to see JWT claims.

**Test Credentials:**
| Hero | Email | Password |
|------|-------|----------|
| Superman | clark.kent@dailyplanet.com | Hero$ecure1! |
| Batman | bruce.wayne@waynetech.com | Hero$ecure1! |
| Spider-Man | peter.parker@bugle.com | Hero$ecure1! |
| Wonder Woman | diana.prince@themyscira.gov | Hero$ecure1! |
| Iron Man | tony.stark@starkindustries.com | Hero$ecure1! |

---

## Module 4: Observability & Evaluation

### Part 1 — Metrics

Every interaction emits latency and token metrics to CloudWatch.

**Suggested Prompts:**
```
Search for TechMart Hub
What laptops do you have under $800?
Tell me about the TechMart Titan
```

### Part 2 — Loop Detection

Circuit breaker activates when agent makes too many repeated tool calls (trips at 10).

**Suggested Prompt (triggers loop):**
```
Find all customer records and process each one
```

### Part 3 — Evaluation

LLM-as-judge evaluates agent responses on Correctness and Helpfulness.

**Suggested Queries to Evaluate:**
```
My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.
What's the best laptop for video editing under $800?
Can I return an item after 45 days?
```

---

## Module 5: Well-Architected

### Part 1 — E-Commerce System

Full 4-agent orchestrated system (Billing, Tech, Product, Shipping).

**Suggested Prompts:**
```
What laptops do you have under $800?
Check order status for ORD-7001
My TechMart Hub keeps dropping Wi-Fi, firmware v2.1.3
Can I get a refund on order ORD-7002?
What's the shipping cost for express delivery?
```

### Part 2 — Reliability

Fault injection with checkboxes. Break an agent and watch graceful degradation to fallback.

**Steps:**
1. Ask: `What laptops do you have?` (works normally)
2. Check "Break product" in the checkbox
3. Ask: `What laptops do you have?` (fallback agent responds with DEGRADED MODE)
4. Uncheck to restore

**Suggested Prompts:**
```
What laptops do you have?
Can I get a refund on my last order?
My Hub keeps disconnecting from Wi-Fi
```

### Part 3 — Cost Optimization

Model tiering: simple queries → economy model, complex → premium. Toggle "Smart Model Tiering" to compare.

**Simple Queries (economy tier):**
```
Hi
What's the price of the Hub?
Is the Pro 15 in stock?
```

**Complex Queries (premium tier):**
```
Compare the Pro 15 and Titan for video editing and recommend the best option
Analyze the trade-offs between the Air and Pro 15 for a college student
Explain the pros and cons of building a smart home with TechMart products
```

---

## Tech Stack

- **Streamlit 1.60+** — UI framework
- **Strands Agents SDK** — Agent orchestration, Graph & Swarm multi-agent patterns
- **Amazon Bedrock** — Foundation models (Claude Sonnet 4, Nova Micro/Pro)
- **Amazon Bedrock AgentCore** — Shared Memory, Evaluators, Gateway, Policy Engine
- **Amazon Cognito** — OAuth 2.0 authentication
- **Amazon Verified Permissions** — Cedar policy authorization
- **Amazon DynamoDB** — Data persistence
- **Amazon CloudWatch** — Metrics and monitoring
- **Bedrock Guardrails** — Content filtering and PII detection
- **boto3** — AWS SDK for Python
