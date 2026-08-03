"""
Module 4 - Part 4: Agent Evaluation Framework

Implements automated evaluation using LLM-as-judge pattern.
Evaluates agent responses on correctness, helpfulness, and tool selection,
then publishes scores to CloudWatch for trend monitoring.

Shows:
- Built-in evaluator patterns (correctness, helpfulness)
- Custom evaluator (tool selection accuracy)
- Scoring rubrics with numeric scales
- Evaluation results stored in DynamoDB and published as metrics
"""

import os
import json
import time
import uuid
import boto3
from datetime import datetime
from decimal import Decimal
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
METRICS_NAMESPACE = os.environ.get("METRICS_NAMESPACE", "m4-demo/AgentMetrics")
EVAL_TABLE = os.environ.get("EVAL_TABLE", "m4-demo-evaluations")
EVAL_LOG_GROUP = os.environ.get("EVAL_LOG_GROUP", "/m4-demo/evaluations")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
logs_client = boto3.client("logs", region_name=REGION)

eval_table = dynamodb.Table(EVAL_TABLE)


# =============================================================================
# EVALUATION ENGINE (LLM-as-Judge)
# =============================================================================

class Evaluator:
    """Evaluates agent responses using an LLM judge."""

    def __init__(self, name: str, instructions: str, scoring_rubric: dict):
        self.name = name
        self.instructions = instructions
        self.scoring_rubric = scoring_rubric
        self.judge = Agent(
            model=BedrockModel(model_id=MODEL_ID),
            system_prompt=f"""You are an evaluation judge. Score the agent response strictly according to the rubric.

EVALUATION CRITERIA: {name}
{instructions}

SCORING RUBRIC:
{json.dumps(scoring_rubric, indent=2)}

OUTPUT FORMAT:
Return ONLY a JSON object: {{"score": <number>, "reasoning": "<brief explanation>"}}
Do not include any other text.
""",
        )

    def evaluate(self, query: str, response: str, context: dict = None) -> dict:
        """Evaluate a single response."""
        eval_prompt = f"""
Query: {query}
Agent Response: {response}
Context: {json.dumps(context or {})}

Score this response according to the rubric. Return JSON only.
"""
        try:
            result = self.judge(eval_prompt)
            result_str = str(result).strip()

            # Parse JSON from response
            # Try to extract JSON if wrapped in other text
            if "{" in result_str:
                json_start = result_str.index("{")
                json_end = result_str.rindex("}") + 1
                result_json = json.loads(result_str[json_start:json_end])
            else:
                result_json = {"score": 0.5, "reasoning": "Could not parse evaluation"}

            return {
                "evaluator": self.name,
                "score": float(result_json.get("score", 0.5)),
                "reasoning": result_json.get("reasoning", ""),
            }
        except Exception as e:
            return {"evaluator": self.name, "score": 0.5, "reasoning": f"Evaluation error: {e}"}


# Built-in evaluators
CORRECTNESS_EVALUATOR = Evaluator(
    name="Correctness",
    instructions="Assess whether the agent response contains factually correct information based on the available context.",
    scoring_rubric={
        "1.0": "Completely correct with accurate details",
        "0.75": "Mostly correct with minor inaccuracies",
        "0.5": "Partially correct, some errors",
        "0.25": "Mostly incorrect",
        "0.0": "Completely wrong or fabricated",
    },
)

HELPFULNESS_EVALUATOR = Evaluator(
    name="Helpfulness",
    instructions="Assess whether the response actually helps the user accomplish their goal.",
    scoring_rubric={
        "1.0": "Fully addresses the question with actionable information",
        "0.75": "Mostly helpful, addresses main points",
        "0.5": "Somewhat helpful but missing key information",
        "0.25": "Minimally helpful, mostly off-topic",
        "0.0": "Not helpful at all, doesn't address the question",
    },
)

TOOL_SELECTION_EVALUATOR = Evaluator(
    name="ToolSelection",
    instructions="Assess whether the agent chose the right tools for the task. Consider if the agent used unnecessary tools or missed tools it should have used.",
    scoring_rubric={
        "1.0": "Perfect tool selection — used exactly the right tools",
        "0.75": "Good selection, used appropriate tools with minor extras",
        "0.5": "Acceptable but could have been more efficient",
        "0.25": "Poor tool choices, wrong tools or too many",
        "0.0": "Completely wrong tools or no tools when needed",
    },
)


def run_evaluation(query: str, response: str, context: dict = None) -> list:
    """Run all evaluators on a response."""
    results = []
    evaluators = [CORRECTNESS_EVALUATOR, HELPFULNESS_EVALUATOR, TOOL_SELECTION_EVALUATOR]

    for evaluator in evaluators:
        result = evaluator.evaluate(query, response, context)
        results.append(result)

        # Publish score as CloudWatch metric
        try:
            cloudwatch.put_metric_data(
                Namespace=METRICS_NAMESPACE,
                MetricData=[{
                    "MetricName": "EvaluationScore",
                    "Value": result["score"],
                    "Unit": "None",
                    "Timestamp": datetime.utcnow(),
                    "Dimensions": [{"Name": "Evaluator", "Value": result["evaluator"]}],
                }],
            )
        except Exception:
            pass

    # Store in DynamoDB
    try:
        eval_record = {
            "eval_id": f"eval-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "response": response[:500],  # Truncate for storage
            "scores": json.dumps(results),
            "average_score": Decimal(str(round(sum(r["score"] for r in results) / len(results), 3))),
        }
        eval_table.put_item(Item=eval_record)
    except Exception:
        pass

    return results


# =============================================================================
# AGENT UNDER EVALUATION
# =============================================================================

@tool
def search_kb(query: str) -> str:
    """Search knowledge base.

    Args:
        query: Search query
    """
    knowledge = {
        "wifi": "TechMart Hub v2.1.x has known Wi-Fi bug. Update to v3.0.1 via Settings > System > Update.",
        "refund": "30-day full refund policy. Express shipping refundable only if item was defective.",
        "laptop": "TechMart Pro 15: $799, 15.6in, i7, 16GB, 512GB SSD. Best for video editing under $800.",
        "hub": "TechMart Hub: $149, supports Wi-Fi 6, Bluetooth 5.0, Zigbee 3.0, max 50 devices.",
    }
    for key, value in knowledge.items():
        if key in query.lower():
            return value
    return "No specific information found for this query."


@tool
def check_order(order_id: str) -> str:
    """Check order status.

    Args:
        order_id: Order ID
    """
    orders = {
        "ORD-5001": "Delivered 2025-07-12. Items: TechMart Hub ($149), Sensors x2 ($58). Total: $220.",
        "ORD-5002": "Delivered 2025-07-20. Items: TechMart Pro 15 ($799). Total: $799.",
    }
    return orders.get(order_id, f"Order {order_id} not found.")


SYSTEM_PROMPT = """You are a TechMart customer service agent.
Use search_kb for product/policy questions. Use check_order for order inquiries.
Provide accurate, helpful responses based on tool results.
"""


# =============================================================================
# DEMO
# =============================================================================

# Pre-defined test cases for evaluation
TEST_CASES = [
    {
        "query": "My TechMart Hub keeps dropping Wi-Fi. Firmware is v2.1.3.",
        "expected_tools": ["search_kb"],
        "expected_answer_contains": "v3.0.1",
    },
    {
        "query": "What's the status of order ORD-5001?",
        "expected_tools": ["check_order"],
        "expected_answer_contains": "Delivered",
    },
    {
        "query": "I need a laptop for video editing under $800. What do you recommend?",
        "expected_tools": ["search_kb"],
        "expected_answer_contains": "Pro 15",
    },
    {
        "query": "Can I get a refund on my TechMart Hub from order ORD-5001? I've had it for 2 weeks.",
        "expected_tools": ["search_kb", "check_order"],
        "expected_answer_contains": "30",
    },
]


def run_demo():
    print("=" * 70)
    print("PART 4: Agent Evaluation Framework (LLM-as-Judge)")
    print("=" * 70)
    print()
    print("  Evaluators:")
    print("    • Correctness — factual accuracy of responses")
    print("    • Helpfulness — does it address the user's goal")
    print("    • ToolSelection — did it use the right tools")
    print()
    print("  Choose mode:")
    print("  [1] Run evaluation on pre-defined test cases (automated)")
    print("  [2] Interactive — chat and evaluate each response")
    print()

    choice = input("  Select (1/2): ").strip()

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_kb, check_order],
    )

    if choice == "1":
        run_automated_evaluation(agent)
    else:
        run_interactive_evaluation(agent)


def run_automated_evaluation(agent: Agent):
    """Run evaluation on pre-defined test cases."""
    print(f"\n{'━' * 70}")
    print(f"  Running {len(TEST_CASES)} test cases with evaluation...")
    print(f"{'━' * 70}\n")

    all_scores = []

    for i, tc in enumerate(TEST_CASES, 1):
        query = tc["query"]
        print(f"  Test {i}/{len(TEST_CASES)}: {query}")
        print()

        # Get agent response
        start = time.time()
        response = agent(query)
        elapsed = time.time() - start
        response_str = str(response)
        print(f"    Response: {response_str[:120]}...")
        print(f"    ⏱ {elapsed:.1f}s")

        # Evaluate
        print(f"    Evaluating...")
        results = run_evaluation(query, response_str, {"expected_tools": tc["expected_tools"]})

        for r in results:
            score = r["score"]
            icon = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
            print(f"      {icon} {r['evaluator']}: {score:.2f} — {r['reasoning'][:60]}")
            all_scores.append(r)

        print()

    # Summary
    print(f"{'═' * 70}")
    print(f"  EVALUATION SUMMARY ({len(TEST_CASES)} test cases)")
    print(f"{'═' * 70}\n")

    by_evaluator = {}
    for s in all_scores:
        name = s["evaluator"]
        if name not in by_evaluator:
            by_evaluator[name] = []
        by_evaluator[name].append(s["score"])

    print(f"  {'Evaluator':<16} {'Avg Score':>10} {'Min':>6} {'Max':>6}")
    print(f"  {'─' * 40}")
    for name, scores in by_evaluator.items():
        avg = sum(scores) / len(scores)
        icon = "🟢" if avg >= 0.75 else "🟡" if avg >= 0.5 else "🔴"
        print(f"  {icon} {name:<14} {avg:>9.2f} {min(scores):>6.2f} {max(scores):>6.2f}")

    overall_avg = sum(s["score"] for s in all_scores) / len(all_scores)
    print(f"\n  Overall average: {overall_avg:.2f}")
    print(f"  Quality threshold: 0.70")
    print(f"  Status: {'✅ PASS' if overall_avg >= 0.7 else '❌ BELOW THRESHOLD'}")
    print()
    print(f"  Scores published to: {METRICS_NAMESPACE} (EvaluationScore metric)")
    print(f"  Results stored in: {EVAL_TABLE}")
    print()


def run_interactive_evaluation(agent: Agent):
    """Chat with agent, evaluate each response."""
    print(f"\n  Interactive mode — each response gets evaluated.")
    print(f"  Type 'quit' to end.\n")

    while True:
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        print()
        response = agent(user_input)
        response_str = str(response)
        print(f"\n  Agent: {response_str}")

        # Evaluate
        print(f"\n  📊 Evaluating response...")
        results = run_evaluation(user_input, response_str)

        for r in results:
            score = r["score"]
            icon = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
            print(f"    {icon} {r['evaluator']}: {score:.2f} — {r['reasoning'][:80]}")

        avg = sum(r["score"] for r in results) / len(results)
        print(f"    Average: {avg:.2f}")
        print()

    print()


if __name__ == "__main__":
    run_demo()
