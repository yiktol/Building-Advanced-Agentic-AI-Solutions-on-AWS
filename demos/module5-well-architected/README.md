# Module 5 Demo: Well-Architected Agentic AI Systems

## Overview

This is the **capstone demo** — a full multi-agent e-commerce system evaluated
against all Well-Architected Framework pillars with concrete implementation
patterns for operational excellence, reliability, and cost optimization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Customer Query                                                      │
│       ↓                                                              │
│  Orchestrator (routes by intent)                                     │
│       ├─→ Billing Agent (refunds, payments)                         │
│       ├─→ Tech Support Agent (devices, firmware)                    │
│       ├─→ Product Agent (recommendations, compatibility)            │
│       └─→ Shipping Agent (orders, delivery)                         │
│                                                                      │
│  Cross-cutting concerns:                                             │
│  • Circuit breakers per specialist (Reliability)                    │
│  • Health checks + versioning (Operational Excellence)              │
│  • Token budgets + model tiering (Cost Optimization)                │
│  • Automated WA review (Governance)                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
pip install strands-agents strands-agents-tools boto3
```

## Deployment

```bash
cd demos/module5-well-architected
./scripts/deploy.sh
source config.env
```

### Destroy

```bash
./scripts/deploy.sh destroy
```

---

## Demo Structure

| Part | File | WA Pillar | Concept |
|------|------|-----------|---------|
| 1 | `part1_ecommerce_system.py` | All | Full multi-agent system (the architecture) |
| 2 | `part2_wa_review.py` | Governance | Automated WA assessment by LLM reviewer |
| 3 | `part3_operational_excellence.py` | Ops Excellence | Versioning, health checks, rollback |
| 4 | `part4_reliability.py` | Reliability | Fault injection, circuit breakers, fallback |
| 5 | `part5_cost_optimization.py` | Cost | Token budgets, model tiering, cost tracking |

---

## How to Run

```bash
source config.env

python part1_ecommerce_system.py     # The production system
python part2_wa_review.py            # Automated assessment
python part3_operational_excellence.py  # Deployment patterns
python part4_reliability.py          # Fault tolerance
python part5_cost_optimization.py    # Cost management
```

---

## Suggested Demo Flow

### Part 1: The System

Interactive multi-agent system — demonstrate it works end-to-end:
```
What laptops do you have under $800?
Check order ORD-7001
My TechMart Hub keeps dropping Wi-Fi, firmware v2.1.3
Can I get a refund on order ORD-7002?
```

### Part 2: WA Review

Choose quick review (select pillars 1,3,5 for focused demo):
- Produces a scored report card per pillar
- Identifies gaps and top recommendations
- Results stored in DynamoDB

### Part 3: Operational Excellence

Watch the deployment lifecycle:
1. Deploy v1 → health check → active
2. Deploy v2 → health check → blue/green switch
3. Deploy broken version → health check FAILS → deployment rejected
4. Active remains on v2 (safe!)

### Part 4: Reliability

```
status                    (see all circuit breakers green)
What laptops do you have? (works normally via product agent)
break product             (inject fault)
What laptops do you have? (fallback agent responds)
status                    (product breaker shows failures)
fix product               (recover)
What laptops do you have? (normal again)
```

### Part 5: Cost Optimization

Choose mode 2 (smart tiering), then:
```
Hi                        (simple → economy model)
What's the price of the Hub?  (simple → economy)
Compare the Pro 15 and Titan for video editing  (complex → premium)
cost                      (see tier breakdown and savings)
budget                    (check remaining token budget)
```

---

## Well-Architected Alignment

| Pillar | Demo Coverage |
|--------|--------------|
| **Operational Excellence** | Part 3: Versioning, health checks, deployment rollback |
| **Security** | Covered in Module 3 (Cognito, Cedar, VPC, audit) |
| **Reliability** | Part 4: Circuit breakers, fault isolation, fallback agents |
| **Performance Efficiency** | Covered in Module 2 (caching, context managers, isolation) |
| **Cost Optimization** | Part 5: Token budgets, model tiering, cost tracking |
| **Sustainability** | Part 2: Reviewed via automated assessment |

---

## Key Takeaways

| Part | Takeaway |
|------|----------|
| 1 | A production multi-agent system needs cross-cutting concerns |
| 2 | Automated reviews catch gaps before they become incidents |
| 3 | Deployment safety: health checks prevent bad deploys from going live |
| 4 | Fault isolation + fallback = system stays available despite failures |
| 5 | Smart tiering and budgets prevent cost surprises in production |
