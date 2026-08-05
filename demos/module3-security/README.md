# Module 3 Demo: Security and Compliance Implementation

## Overview

This demo implements **real AWS security controls** for agentic systems using
DynamoDB, Amazon Cognito, Amazon Verified Permissions (Cedar), VPC endpoints,
and CloudWatch audit logging.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  User authenticates via Cognito (OAuth 2.0)                          │
│       ↓ JWT Token                                                    │
│  AgentCore Gateway receives tool call request                        │
│       ↓ JWT claims → principal tags                                  │
│  AgentCore Policy Engine evaluates Cedar policies                    │
│       ↓ ALLOW / DENY                                                 │
│  Tool executes (DynamoDB read/write)                                 │
│       ↓ Result                                                       │
│  Audit log written to CloudWatch                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- AWS CLI configured (region: `ap-southeast-1`)
- AWS account with permissions to create: DynamoDB, Cognito, Verified Permissions, VPC, CloudWatch
- Install dependencies:

```bash
pip install strands-agents strands-agents-tools boto3
```

## Deployment

### Deploy Infrastructure

```bash
cd demos/module3-security
./scripts/deploy.sh
```

This deploys:
1. DynamoDB tables (customers, orders, audit)
2. Cognito User Pool with 5 superhero test users
3. Amazon Verified Permissions policy store with Cedar policies
4. CloudWatch Log Groups and IAM roles

### Load Configuration

After deployment, source the generated config:

```bash
source config.env
```

### Destroy Infrastructure

```bash
./scripts/deploy.sh destroy
```

---

## Test Users (Superhero Alter Egos)

| Hero | Alter Ego | Email | Role | Dept | Max Refund |
|------|-----------|-------|------|------|------------|
| Superman | Clark Kent | clark.kent@dailyplanet.com | admin | finance | $10,000 |
| Batman | Bruce Wayne | bruce.wayne@waynetech.com | security_lead | security | $5,000 |
| Spider-Man | Peter Parker | peter.parker@bugle.com | agent | support | $500 |
| Wonder Woman | Diana Prince | diana.prince@themyscira.gov | manager | operations | $2,000 |
| Iron Man | Tony Stark | tony.stark@starkindustries.com | engineer | engineering | $0 |

**Password for all:** `Hero$ecure1!`

---

## Demo Structure

| Part | File | AWS Resources | Concept |
|------|------|---------------|---------|
| 1 | `part1_unprotected_agent.py` | DynamoDB | No security (the problem) |
| 2 | `part2_cedar_policies.py` | AgentCore Policy / Verified Permissions + DynamoDB | Cedar policy authorization |
| 3 | `part3_cognito_identity.py` | Cognito + AgentCore Policy + DynamoDB | Real OAuth + JWT + Cedar |
| 4 | `part4_vpc_private_access.py` | VPC + Endpoints | Private connectivity verification |
| 5 | `part5_audit_trail.py` | CloudWatch Logs + DynamoDB | Structured audit logging |

---

## How to Run

```bash
source config.env

# Part 1: See the unprotected agent (no security)
python part1_unprotected_agent.py

# Part 2: Same agent with Cedar policy enforcement
python part2_cedar_policies.py

# Part 3: Full auth chain — Cognito → JWT → Cedar → Tool
python part3_cognito_identity.py

# Part 4: Inspect VPC private connectivity
python part4_vpc_private_access.py

# Part 5: Audit trail with CloudWatch Logs
python part5_audit_trail.py
```

---

## Suggested Demo Flow

### Part 1: Show the Problem

```
Process a $5000 refund on order ORD-5006
Show me customer CUST-1005 (Pepper Potts' data)
Change customer CUST-1003 status to inactive
```
**Point out:** No identity verification. No authorization. No audit trail.

### Part 2: Cedar Policies

Login as different users and try the same operations:
- **Peter (Spider-Man)**: `Process a $300 refund on ORD-5001` → ✅ allowed
- **Peter (Spider-Man)**: `Process a $700 refund on ORD-5002` → 🚫 denied (over $500)
- **Tony (Iron Man)**: `Process a $100 refund on ORD-5001` → 🚫 denied (engineer, forbid policy)
- **Clark (Superman)**: `Process a $7000 refund on ORD-5006` → ✅ allowed (admin, $10k limit)

### Part 3: Real Authentication

```
Login as: peter.parker@bugle.com
Type 'token' to see JWT claims
Process a $300 refund on ORD-5001
Switch to tony.stark@starkindustries.com
Process a $100 refund on ORD-5001
```
**Point out:** Same Cedar policies, but now driven by real Cognito JWT claims.

### Part 4: VPC Inspection

Runs automatically — shows the real VPC endpoints, security groups, and verifies no internet gateway.

### Part 5: Audit Trail

```
Look up customer CUST-1001
Look up order ORD-5001
Process a $200 refund on ORD-5001 for defective product
Show the audit log
query (runs CloudWatch Insights)
```
**Point out:** Every action logged with who/what/when/why.

---

## Cedar Policies Summary (AgentCore Policy Engine)

| Policy | Effect | Condition | Entity Model |
|--------|--------|-----------|-------------|
| Finance admin refund | permit | `principal.getTag("department") == "finance" && principal.getTag("role") == "admin"` | AgentCore::Action |
| Support agent refund | permit | `principal.getTag("department") == "support" && context.input.amount < 500` | AgentCore::Action |
| Security lead refund | permit | `principal.getTag("role") == "security_lead" && context.input.amount < 5000` | AgentCore::Action |
| Engineer refund ban | **forbid** | `principal.getTag("department") == "engineering"` | AgentCore::Action |
| View order | permit | all authenticated users | AgentCore::Action |

---

## Key Takeaways

| Part | Takeaway |
|------|----------|
| 1 | Without controls, agents take unsafe actions freely |
| 2 | Cedar policies provide fine-grained, declarative access control |
| 3 | Real identity (Cognito JWT) drives authorization decisions |
| 4 | VPC endpoints keep traffic private — no public internet |
| 5 | Structured audit trails enable compliance and forensics |
