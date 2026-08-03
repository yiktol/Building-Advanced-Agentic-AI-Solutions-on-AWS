# Module 4 Demo: Production Monitoring, Observability, and Evaluation

## Overview

This demo implements **real production observability** for agentic systems using
CloudWatch metrics, traces, alarms, dashboards, and an LLM-based evaluation framework.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Agent Interaction                                                    │
│       │                                                              │
│       ├──→ Spans (CloudWatch Logs: /m4-demo/agent-spans)            │
│       ├──→ Metrics (CloudWatch: m4-demo/AgentMetrics)               │
│       ├──→ Loop Detection (CloudWatch Logs + Alarms)                │
│       └──→ Evaluation Scores (DynamoDB + CloudWatch Metrics)        │
│                                                                      │
│  CloudWatch Dashboard: Unified view of all signals                   │
│  CloudWatch Alarms: Proactive alerting (latency, loops, quality)    │
│  SNS Notifications: Alert delivery                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- AWS CLI configured (region: `ap-southeast-1`)
- Install dependencies:

```bash
pip install strands-agents strands-agents-tools boto3
```

## Deployment

```bash
cd demos/module4-observability
./scripts/deploy.sh
source config.env
```

### What Gets Deployed

| Resource | Purpose |
|----------|---------|
| CloudWatch Log Groups (4) | Spans, metrics, loop detection, evaluations |
| DynamoDB Table | Evaluation results storage |
| CloudWatch Alarms (6) | Latency, errors, loops, sessions, tokens, quality |
| SNS Topic | Alert notifications |
| CloudWatch Dashboard | Unified observability view |

### Destroy

```bash
./scripts/deploy.sh destroy
```

---

## Demo Structure

| Part | File | Concept |
|------|------|---------|
| 1 | `part1_tracing.py` | OTel-style tracing (session/trace/span hierarchy) |
| 2 | `part2_metrics.py` | Custom CloudWatch metrics (latency, tokens, tools) |
| 3 | `part3_loop_detection.py` | Loop detection + circuit breaker + alarms |
| 4 | `part4_evaluation.py` | LLM-as-judge evaluation framework |
| 5 | `part5_dashboard.py` | End-to-end observability (all signals combined) |

---

## How to Run

```bash
source config.env

python part1_tracing.py
python part2_metrics.py
python part3_loop_detection.py
python part4_evaluation.py
python part5_dashboard.py
```

---

## Suggested Demo Flow

### Part 1: Tracing

```
My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.
What laptops do you have under $800?
traces  (shows recorded span hierarchy)
```
**Observe:** Session → Trace → Span hierarchy with timing for each operation.

### Part 2: Metrics

```
Search for TechMart Hub
Check inventory for TechMart Pro 15
Place an order for 2 TechMart Hubs
stats  (shows session metrics)
dashboard  (gets dashboard URL)
```
**Observe:** Real-time metrics appearing in CloudWatch namespace.

### Part 3: Loop Detection

Choose mode 2 (loopy) to trigger circuit breaker:
```
Find all customer records and process them
```
**Observe:** Tool calls escalate, circuit breaker trips, alarm fires.

### Part 4: Evaluation

Choose mode 1 (automated) to run test suite:
- 4 pre-defined queries get evaluated by LLM judges
- Scores published to CloudWatch for each evaluator
- Quality threshold check (pass/fail)

### Part 5: Dashboard

```
Look up the TechMart Pro 15
Is it compatible with the TechMart Hub?
Place an order for 1 TechMart Pro 15
alarms  (check alarm states)
metrics (session summary)
query   (CloudWatch Insights on spans)
```
**Observe:** All signals flowing together — open the CloudWatch Dashboard.

---

## CloudWatch Alarms

| Alarm | Threshold | Severity |
|-------|-----------|----------|
| High Latency | Response > 30s | P2 |
| High Error Rate | > 5 errors in 5min | P1 |
| Loop Detected | > 50 tool calls in 5min | P1 |
| Long Session | > 10 min duration | P2 |
| Token Spike | > 50k tokens in 5min | P3 |
| Quality Regression | Eval score < 0.7 avg | P2 |

---

## Evaluation Dimensions

| Evaluator | What It Measures | Scale |
|-----------|-----------------|-------|
| Correctness | Factual accuracy | 0.0 – 1.0 |
| Helpfulness | Addresses user goal | 0.0 – 1.0 |
| ToolSelection | Used right tools | 0.0 – 1.0 |

---

## Key Takeaways

| Part | Takeaway |
|------|----------|
| 1 | Traces give request-level visibility into agent behavior |
| 2 | Custom metrics enable real-time performance monitoring |
| 3 | Loop detection is critical safety for autonomous agents |
| 4 | LLM-as-judge enables continuous quality assessment |
| 5 | Unified dashboards connect all signals for operations |
