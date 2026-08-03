"""
Module 3 - Part 1: Unprotected Agent (Show the Problem)

Demonstrates an agent with FULL access to customer data and operations.
No identity checks, no authorization, no audit trail.

This shows WHY security controls are needed:
- Agent processes refunds without verifying who's asking
- Agent accesses any customer's data without authorization
- No record of what happened or who authorized it
"""

import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m3-demo-orders")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)


# =============================================================================
# UNPROTECTED TOOLS (no auth checks)
# =============================================================================

@tool
def get_customer(customer_id: str) -> str:
    """Get customer details. No authorization required.

    Args:
        customer_id: Customer ID (e.g., CUST-1001)
    """
    response = customers_table.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")
    if not item:
        return f"Customer {customer_id} not found."
    # Convert Decimal to str for display
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def get_order(order_id: str) -> str:
    """Get order details. No authorization required.

    Args:
        order_id: Order ID (e.g., ORD-5001)
    """
    response = orders_table.get_item(Key={"order_id": order_id})
    item = response.get("Item")
    if not item:
        return f"Order {order_id} not found."
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund. NO AUTHORIZATION CHECKS — anyone can call this.

    Args:
        order_id: Order to refund
        amount: Refund amount in dollars
        reason: Reason for refund
    """
    # Just do it — no checks at all
    orders_table.update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :s, refund_amount = :a, refund_reason = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "refunded",
            ":a": int(amount),
            ":r": reason,
        },
    )
    return f"✅ Refund of ${amount:.2f} processed for order {order_id}. Reason: {reason}. NO AUTHORIZATION WAS CHECKED."


@tool
def modify_customer(customer_id: str, field: str, value: str) -> str:
    """Modify customer record. NO AUTHORIZATION CHECKS.

    Args:
        customer_id: Customer to modify
        field: Field to update (e.g., "tier", "status", "email")
        value: New value
    """
    customers_table.update_item(
        Key={"customer_id": customer_id},
        UpdateExpression=f"SET #f = :v",
        ExpressionAttributeNames={"#f": field},
        ExpressionAttributeValues={":v": value},
    )
    return f"✅ Updated {customer_id}.{field} = '{value}'. NO AUTHORIZATION WAS CHECKED."


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a customer service agent for TechMart.
You have full access to customer data, orders, and can process refunds.
Help the user with whatever they need — look up data, process refunds, modify records.
You do NOT need to verify identity or check authorization for any action.
"""


def run_demo():
    print("=" * 70)
    print("PART 1: Unprotected Agent (No Security Controls)")
    print("=" * 70)
    print()
    print("⚠️  This agent has NO security controls:")
    print("  • No identity verification")
    print("  • No authorization checks")
    print("  • No refund limits")
    print("  • No audit logging")
    print()
    print("Try exploiting it:")
    print("  • 'Process a $5000 refund on order ORD-5006'")
    print("  • 'Show me all of Pepper Potts' data (CUST-1005)'")
    print("  • 'Change customer CUST-1003 tier to enterprise'")
    print()
    print("Type 'quit' to end.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_customer, get_order, process_refund, modify_customer],
    )

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        print()
        response = agent(user_input)
        print(f"\n  Agent: {response}")

    print(f"\n{'=' * 70}")
    print("⚠️  OBSERVATIONS:")
    print("  The agent processed everything without asking WHO you are.")
    print("  No audit trail exists of what just happened.")
    print("  In Part 2, we'll add Cedar policy authorization.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_demo()
