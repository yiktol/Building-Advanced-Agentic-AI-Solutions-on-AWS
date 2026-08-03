"""
Module 3 - Part 2: Cedar Policy Authorization with Amazon Verified Permissions

Same agent as Part 1, but now every tool call goes through Cedar policy
evaluation using Amazon Verified Permissions before executing.

Shows:
- permit/forbid policies with conditions
- Amount-based refund limits per role
- Real Cedar policy evaluation via AWS API
"""

import os
import json
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m3-demo-orders")
POLICY_STORE_ID = os.environ.get("POLICY_STORE_ID", "")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)
avp_client = boto3.client("verifiedpermissions", region_name=REGION)

# Current user context (set during authentication)
_current_user = {}


def set_current_user(user_attrs: dict):
    """Set the authenticated user context for policy evaluation."""
    global _current_user
    _current_user = user_attrs


def check_authorization(action: str, resource_attrs: dict) -> dict:
    """Check authorization against Amazon Verified Permissions.

    Returns: {"decision": "ALLOW"|"DENY", "reasons": [...]}
    """
    if not POLICY_STORE_ID:
        return {"decision": "DENY", "reasons": ["No policy store configured"]}

    if not _current_user:
        return {"decision": "DENY", "reasons": ["No authenticated user"]}

    # Build the authorization request
    request = {
        "policyStoreId": POLICY_STORE_ID,
        "principal": {
            "entityType": "TechMart::User",
            "entityId": _current_user.get("email", "unknown"),
        },
        "action": {
            "actionType": "TechMart::Action",
            "actionId": action,
        },
        "resource": {
            "entityType": f"TechMart::{resource_attrs.get('type', 'Order')}",
            "entityId": resource_attrs.get("id", "unknown"),
        },
        "entities": {
            "entityList": [
                {
                    "identifier": {
                        "entityType": "TechMart::User",
                        "entityId": _current_user.get("email", "unknown"),
                    },
                    "attributes": {
                        "role": {"string": _current_user.get("role", "")},
                        "department": {"string": _current_user.get("department", "")},
                        "max_refund": {"long": int(_current_user.get("max_refund", 0))},
                    },
                },
                {
                    "identifier": {
                        "entityType": f"TechMart::{resource_attrs.get('type', 'Order')}",
                        "entityId": resource_attrs.get("id", "unknown"),
                    },
                    "attributes": {
                        k: {"long": int(v)} if isinstance(v, (int, float)) else {"string": str(v)}
                        for k, v in resource_attrs.items()
                        if k not in ("type", "id")
                    },
                },
            ]
        },
    }

    try:
        response = avp_client.is_authorized(**request)
        decision = response.get("decision", "DENY")
        reasons = []
        for error in response.get("errors", []):
            reasons.append(error.get("errorDescription", ""))
        for det in response.get("determiningPolicies", []):
            reasons.append(f"Policy: {det.get('policyId', 'unknown')}")
        return {"decision": decision, "reasons": reasons}
    except Exception as e:
        return {"decision": "DENY", "reasons": [f"Authorization error: {str(e)}"]}


# =============================================================================
# PROTECTED TOOLS (with Cedar policy checks)
# =============================================================================

@tool
def get_customer(customer_id: str) -> str:
    """Get customer details (requires ViewCustomer permission).

    Args:
        customer_id: Customer ID (e.g., CUST-1001)
    """
    auth = check_authorization("ViewCustomer", {"type": "Customer", "id": customer_id, "customer_id": customer_id})
    if auth["decision"] != "ALLOW":
        return f"🚫 ACCESS DENIED: ViewCustomer on {customer_id}. Reasons: {auth['reasons']}"

    response = customers_table.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")
    if not item:
        return f"Customer {customer_id} not found."
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def get_order(order_id: str) -> str:
    """Get order details (requires ViewOrder permission).

    Args:
        order_id: Order ID (e.g., ORD-5001)
    """
    auth = check_authorization("ViewOrder", {"type": "Order", "id": order_id, "customer_id": "any", "amount": 0, "status": "any"})
    if auth["decision"] != "ALLOW":
        return f"🚫 ACCESS DENIED: ViewOrder on {order_id}. Reasons: {auth['reasons']}"

    response = orders_table.get_item(Key={"order_id": order_id})
    item = response.get("Item")
    if not item:
        return f"Order {order_id} not found."
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund (requires ProcessRefund permission — checked against Cedar policies).

    Args:
        order_id: Order to refund
        amount: Refund amount in dollars
        reason: Reason for refund
    """
    # Check authorization with the refund amount as resource context
    auth = check_authorization("ProcessRefund", {
        "type": "Order",
        "id": order_id,
        "amount": int(amount),
        "customer_id": "any",
        "status": "delivered",
    })

    if auth["decision"] != "ALLOW":
        user = _current_user.get("hero_name", _current_user.get("email", "Unknown"))
        role = _current_user.get("role", "unknown")
        dept = _current_user.get("department", "unknown")
        max_r = _current_user.get("max_refund", 0)
        return (
            f"🚫 REFUND DENIED for ${amount:.2f} on {order_id}.\n"
            f"   User: {user} (role={role}, dept={dept}, max_refund=${max_r})\n"
            f"   Policy decision: {auth['decision']}\n"
            f"   Reasons: {auth['reasons']}"
        )

    # Authorized — process the refund
    orders_table.update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :s, refund_amount = :a, refund_reason = :r, refunded_by = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "refunded",
            ":a": int(amount),
            ":r": reason,
            ":u": _current_user.get("email", "unknown"),
        },
    )
    user = _current_user.get("hero_name", _current_user.get("email", "Unknown"))
    return f"✅ REFUND AUTHORIZED: ${amount:.2f} on {order_id}. Processed by: {user}. Reason: {reason}"


@tool
def modify_customer(customer_id: str, field: str, value: str) -> str:
    """Modify customer record (requires ModifyCustomer permission).

    Args:
        customer_id: Customer to modify
        field: Field to update
        value: New value
    """
    auth = check_authorization("ModifyCustomer", {"type": "Customer", "id": customer_id, "customer_id": customer_id})
    if auth["decision"] != "ALLOW":
        user = _current_user.get("hero_name", _current_user.get("email", "Unknown"))
        return f"🚫 ACCESS DENIED: ModifyCustomer on {customer_id}. User: {user}. Reasons: {auth['reasons']}"

    customers_table.update_item(
        Key={"customer_id": customer_id},
        UpdateExpression="SET #f = :v",
        ExpressionAttributeNames={"#f": field},
        ExpressionAttributeValues={":v": value},
    )
    user = _current_user.get("hero_name", _current_user.get("email", "Unknown"))
    return f"✅ AUTHORIZED: Updated {customer_id}.{field} = '{value}'. Modified by: {user}"


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a POLICY-PROTECTED customer service agent for TechMart.
All your actions are checked against Cedar authorization policies.
If an action is denied, explain WHY it was denied (role, limits, etc).
Help the user with their request, but respect all authorization decisions.
"""

# Available test users
TEST_USERS = {
    "clark": {
        "email": "clark.kent@dailyplanet.com",
        "role": "admin",
        "department": "finance",
        "hero_name": "Superman",
        "max_refund": 10000,
    },
    "bruce": {
        "email": "bruce.wayne@waynetech.com",
        "role": "security_lead",
        "department": "security",
        "hero_name": "Batman",
        "max_refund": 5000,
    },
    "peter": {
        "email": "peter.parker@bugle.com",
        "role": "agent",
        "department": "support",
        "hero_name": "Spider-Man",
        "max_refund": 500,
    },
    "diana": {
        "email": "diana.prince@themyscira.gov",
        "role": "manager",
        "department": "operations",
        "hero_name": "Wonder Woman",
        "max_refund": 2000,
    },
    "tony": {
        "email": "tony.stark@starkindustries.com",
        "role": "engineer",
        "department": "engineering",
        "hero_name": "Iron Man",
        "max_refund": 0,
    },
}


def run_demo():
    print("=" * 70)
    print("PART 2: Cedar Policy Authorization (Verified Permissions)")
    print("=" * 70)
    print()
    print("Same tools as Part 1, but now protected by Cedar policies.")
    print()
    print("🦸 Select a user to authenticate as:")
    print("  [clark]  Superman — admin/finance (max refund: $10,000)")
    print("  [bruce]  Batman  — security_lead/security (max refund: $5,000)")
    print("  [peter]  Spider-Man — agent/support (max refund: $500)")
    print("  [diana]  Wonder Woman — manager/operations (max refund: $2,000)")
    print("  [tony]   Iron Man — engineer/engineering (NO refund access)")
    print()

    while True:
        choice = input("  Login as (clark/bruce/peter/diana/tony): ").strip().lower()
        if choice in TEST_USERS:
            break
        print("  Please enter a valid username.")

    user = TEST_USERS[choice]
    set_current_user(user)

    print(f"\n  ✅ Authenticated as: {user['hero_name']} ({user['email']})")
    print(f"     Role: {user['role']} | Dept: {user['department']} | Max refund: ${user['max_refund']}")
    print()
    print("  Try:")
    print("    • 'Process a $300 refund on ORD-5001' (under $500 — most users can)")
    print("    • 'Process a $7000 refund on ORD-5006' (only Superman can)")
    print("    • 'Change customer CUST-1003 tier to enterprise' (admin/manager only)")
    print()
    print("  Type 'switch' to change user. Type 'quit' to end.")
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
            user_input = input(f"  [{user['hero_name']}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "switch":
            print()
            while True:
                choice = input("  Login as (clark/bruce/peter/diana/tony): ").strip().lower()
                if choice in TEST_USERS:
                    break
            user = TEST_USERS[choice]
            set_current_user(user)
            print(f"  ✅ Switched to: {user['hero_name']} ({user['role']}/{user['department']})")
            continue

        print()
        response = agent(user_input)
        print(f"\n  Agent: {response}")

    print(f"\n{'=' * 70}")
    print("  Cedar policies enforce authorization at every tool call.")
    print("  In Part 3, we'll add real Cognito authentication with JWT tokens.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_demo()
