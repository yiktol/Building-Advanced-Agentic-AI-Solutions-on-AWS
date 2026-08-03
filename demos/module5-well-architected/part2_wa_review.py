"""
Module 5 - Part 2: Automated Well-Architected Review

An LLM-based reviewer evaluates the deployed multi-agent system
against each Well-Architected Framework pillar and produces a
scored findings report.
"""

import os
import json
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from strands import Agent
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
WA_REVIEW_TABLE = os.environ.get("WA_REVIEW_TABLE", "m5-demo-wa-reviews")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
review_table = dynamodb.Table(WA_REVIEW_TABLE)

# System architecture description for the reviewer
SYSTEM_DESCRIPTION = """
SYSTEM: TechMart Multi-Agent E-Commerce Customer Service

ARCHITECTURE:
- Orchestrator agent routes to 4 specialist agents (billing, tech, product, shipping)
- Each specialist has isolated context and focused system prompts
- Backed by DynamoDB tables (products, orders, customers)
- Uses Amazon Bedrock Claude Sonnet 4 for all agents
- Running in ap-southeast-1 region

CURRENT IMPLEMENTATION:
- Multi-agent: Framework-layer pattern with Strands SDK @tool routing
- Data: DynamoDB PAY_PER_REQUEST tables with GSI for customer lookups
- Auth: Not yet implemented (planned: Cognito + Verified Permissions)
- Observability: Not yet integrated (planned: CloudWatch + OTel)
- Deployment: Manual python execution (planned: containerized on ECS/Lambda)
- Context management: No conversation managers configured yet
- Error handling: Basic try/except, no circuit breakers
- Cost controls: No token budgets or model tiering
- Caching: No prompt caching configured

KNOWN GAPS:
- No authentication or authorization on tool calls
- No VPC isolation (runs on public internet)
- No audit logging
- No automated evaluation or quality monitoring
- No deployment pipeline or versioning
- No rate limiting or token budgets
- Single region deployment
"""

PILLARS = [
    {
        "name": "Operational Excellence",
        "focus": "Deployment, monitoring, continuous improvement, runbooks",
        "questions": [
            "Is there an automated deployment pipeline with rollback?",
            "Are there health checks and canaries for continuous validation?",
            "Is observability implemented (traces, metrics, logs)?",
            "Are there runbooks for common operational scenarios?",
            "Is there a process for continuous improvement (evaluation feedback loop)?",
        ],
    },
    {
        "name": "Security",
        "focus": "Identity, authorization, data protection, compliance",
        "questions": [
            "Is user identity verified before agent actions (AuthN)?",
            "Are tool calls authorized via policies (AuthZ)?",
            "Is data encrypted at rest and in transit?",
            "Are there audit trails for all agent actions?",
            "Is the agent deployed in a private network (VPC)?",
        ],
    },
    {
        "name": "Reliability",
        "focus": "Fault isolation, recovery, resilience",
        "questions": [
            "Are agents isolated so one failure doesn't cascade?",
            "Is there graceful degradation when a specialist fails?",
            "Are there circuit breakers for tool failures?",
            "Can the system recover from partial failures automatically?",
            "Is there multi-AZ or multi-region capability?",
        ],
    },
    {
        "name": "Performance Efficiency",
        "focus": "Context optimization, latency, resource usage",
        "questions": [
            "Is prompt caching used for static system prompts?",
            "Are conversation managers configured to prevent context bloat?",
            "Is context isolated across specialist agents?",
            "Are tool responses optimized for token efficiency?",
            "Is there model tiering (cheap model for simple, premium for complex)?",
        ],
    },
    {
        "name": "Cost Optimization",
        "focus": "Token budgets, caching, right-sizing",
        "questions": [
            "Are there token budgets per session/request?",
            "Is prompt caching reducing redundant token processing?",
            "Is there a model tiering strategy based on query complexity?",
            "Are evaluation costs managed (sampling vs full coverage)?",
            "Is there monitoring of cost per session?",
        ],
    },
    {
        "name": "Sustainability",
        "focus": "Resource efficiency, carbon awareness",
        "questions": [
            "Is the region selected for carbon efficiency?",
            "Are resources shared/consolidated where possible?",
            "Is there lifecycle management for data (TTL, archival)?",
            "Are idle resources cleaned up automatically?",
            "Is utilization monitored to prevent waste?",
        ],
    },
]


def run_pillar_review(pillar: dict) -> dict:
    """Run WA review for a single pillar."""
    reviewer = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=f"""You are an AWS Well-Architected Framework reviewer specializing in the {pillar['name']} pillar.

Evaluate the described system against best practices. For each question:
- Score 0.0 (not implemented) to 1.0 (fully implemented)
- Provide a brief finding (1-2 sentences)
- Suggest a specific remediation if score < 0.8

Return your assessment as JSON:
{{
  "pillar": "{pillar['name']}",
  "overall_score": <average of question scores>,
  "findings": [
    {{"question": "...", "score": 0.X, "finding": "...", "remediation": "..."}}
  ],
  "top_recommendation": "single most impactful improvement"
}}

Return ONLY valid JSON.
""",
    )

    prompt = f"""
SYSTEM UNDER REVIEW:
{SYSTEM_DESCRIPTION}

ASSESSMENT QUESTIONS for {pillar['name']}:
{json.dumps(pillar['questions'], indent=2)}

Evaluate this system and return your JSON assessment.
"""

    response = reviewer(prompt)
    response_str = str(response).strip()

    # Parse JSON
    try:
        if "{" in response_str:
            json_start = response_str.index("{")
            json_end = response_str.rindex("}") + 1
            return json.loads(response_str[json_start:json_end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {"pillar": pillar["name"], "overall_score": 0.0, "findings": [], "top_recommendation": "Parse error"}


def run_demo():
    print("=" * 70)
    print("PART 2: Automated Well-Architected Review")
    print("=" * 70)
    print()
    print("  An AI reviewer evaluates the e-commerce system against all 6 pillars.")
    print()
    print("  Choose scope:")
    print("  [1] Full review (all 6 pillars — takes ~2 minutes)")
    print("  [2] Quick review (select specific pillars)")
    print()

    choice = input("  Select (1/2): ").strip()

    if choice == "2":
        print("\n  Available pillars:")
        for i, p in enumerate(PILLARS, 1):
            print(f"    [{i}] {p['name']}")
        selected = input("  Enter numbers (e.g., 1,3,5): ").strip()
        indices = [int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]
        pillars_to_review = [PILLARS[i] for i in indices if 0 <= i < len(PILLARS)]
    else:
        pillars_to_review = PILLARS

    if not pillars_to_review:
        pillars_to_review = PILLARS

    print(f"\n  Reviewing {len(pillars_to_review)} pillars...")
    print(f"{'━' * 70}\n")

    results = []
    review_id = f"review-{uuid.uuid4().hex[:8]}"

    for i, pillar in enumerate(pillars_to_review, 1):
        print(f"  [{i}/{len(pillars_to_review)}] Reviewing: {pillar['name']}...")
        result = run_pillar_review(pillar)
        results.append(result)

        score = result.get("overall_score", 0)
        icon = "🟢" if score >= 0.8 else "🟡" if score >= 0.5 else "🔴"
        print(f"       {icon} Score: {score:.2f}")
        print(f"       Top recommendation: {result.get('top_recommendation', 'N/A')[:80]}")
        print()

        # Store in DynamoDB
        try:
            review_table.put_item(Item={
                "review_id": review_id,
                "timestamp": datetime.utcnow().isoformat(),
                "pillar": pillar["name"],
                "score": Decimal(str(round(score, 3))),
                "findings": json.dumps(result.get("findings", [])),
                "recommendation": result.get("top_recommendation", ""),
            })
        except Exception:
            pass

    # Final report card
    print(f"{'═' * 70}")
    print(f"  WELL-ARCHITECTED REVIEW — REPORT CARD")
    print(f"  Review ID: {review_id}")
    print(f"{'═' * 70}\n")

    print(f"  {'Pillar':<25} {'Score':>7} {'Status':>8}")
    print(f"  {'─' * 42}")

    total_score = 0
    for result in results:
        name = result.get("pillar", "Unknown")
        score = result.get("overall_score", 0)
        total_score += score
        icon = "🟢" if score >= 0.8 else "🟡" if score >= 0.5 else "🔴"
        status = "PASS" if score >= 0.7 else "NEEDS WORK"
        print(f"  {icon} {name:<23} {score:>6.2f} {status:>10}")

    avg = total_score / len(results) if results else 0
    print(f"  {'─' * 42}")
    print(f"  {'OVERALL':<25} {avg:>6.2f}")
    print()

    # Top recommendations
    print(f"  TOP RECOMMENDATIONS:")
    for result in results:
        if result.get("overall_score", 1) < 0.8:
            print(f"    • [{result.get('pillar', '?')}] {result.get('top_recommendation', 'N/A')[:70]}")

    print()
    print(f"  Results stored in: {WA_REVIEW_TABLE}")
    print()


if __name__ == "__main__":
    run_demo()
