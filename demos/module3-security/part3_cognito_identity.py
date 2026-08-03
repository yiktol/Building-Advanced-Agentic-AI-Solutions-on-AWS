"""
Module 3 - Part 3: Real Identity with Amazon Cognito

Demonstrates real OAuth 2.0 authentication with JWT tokens.
Users authenticate via Cognito, JWT claims are extracted, and
claims flow through to Cedar policy decisions.

Shows:
- Real Cognito authentication (USER_PASSWORD_AUTH flow)
- JWT token decoding and claim extraction
- Claims mapped to policy context
- Different users get different access based on their token
"""

import os
import json
import base64
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m3-demo-orders")
POLICY_STORE_ID = os.environ.get("POLICY_STORE_ID", "")
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID", "")
DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "Hero$ecure1!")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)
cognito_client = boto3.client("cognito-idp", region_name=REGION)
avp_client = boto3.client("verifiedpermissions", region_name=REGION)

# Session state
_authenticated_user = None
_id_token = None
_access_token = None


def decode_jwt_claims(token: str) -> dict:
    """Decode JWT payload without verification (for display purposes)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    # Add padding
    payload = parts[1]
    payload += "=" * (4 - len(payload) % 4)
    decoded = base64.b64decode(payload)
    return json.loads(decoded)


def authenticate(email: str, password: str) -> dict:
    """Authenticate user with Cognito and return decoded claims."""
    global _authenticated_user, _id_token, _access_token

    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password,
            },
        )

        result = response.get("AuthenticationResult", {})
        _id_token = result.get("IdToken", "")
        _access_token = result.get("AccessToken", "")

        # Decode the ID token to get claims
        claims = decode_jwt_claims(_id_token)

        _authenticated_user = {
            "email": claims.get("email", email),
            "sub": claims.get("sub", ""),
            "role": claims.get("custom:role", ""),
            "department": claims.get("custom:department", ""),
            "hero_name": claims.get("custom:hero_name", ""),
            "max_refund": int(claims.get("custom:max_refund", "0")),
        }

        return {"success": True, "user": _authenticated_user, "claims": claims}

    except cognito_client.exceptions.NotAuthorizedException:
        return {"success": False, "error": "Invalid credentials"}
    except cognito_client.exceptions.UserNotFoundException:
        return {"success": False, "error": "User not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_authorization(action: str, resource_attrs: dict) -> dict:
    """Check authorization via Verified Permissions with JWT-derived context."""
    if not POLICY_STORE_ID or not _authenticated_user:
        return {"decision": "DENY", "reasons": ["Not authenticated"]}

    request = {
        "policyStoreId": POLICY_STORE_ID,
        "principal": {
            "entityType": "TechMart::User",
            "entityId": _authenticated_user["email"],
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
                        "entityId": _authenticated_user["email"],
                    },
                    "attributes": {
                        "role": {"string": _authenticated_user["role"]},
                        "department": {"string": _authenticated_user["department"]},
                        "max_refund": {"long": _authenticated_user["max_refund"]},
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
        reasons = [p.get("policyId", "") for p in response.get("determiningPolicies", [])]
        return {"decision": decision, "reasons": reasons}
    except Exception as e:
        return {"decision": "DENY", "reasons": [str(e)]}


# =============================================================================
# PROTECTED TOOLS
# =============================================================================

@tool
def get_customer(customer_id: str) -> str:
    """Get customer details (requires authentication + ViewCustomer permission).

    Args:
        customer_id: Customer ID (e.g., CUST-1001)
    """
    if not _authenticated_user:
        return "🚫 NOT AUTHENTICATED: Please login first."

    auth = check_authorization("ViewCustomer", {"type": "Customer", "id": customer_id, "customer_id": customer_id})
    if auth["decision"] != "ALLOW":
        return f"🚫 ACCESS DENIED: ViewCustomer on {customer_id}."

    response = customers_table.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")
    if not item:
        return f"Customer {customer_id} not found."
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def get_order(order_id: str) -> str:
    """Get order details (requires authentication + ViewOrder permission).

    Args:
        order_id: Order ID (e.g., ORD-5001)
    """
    if not _authenticated_user:
        return "🚫 NOT AUTHENTICATED: Please login first."

    auth = check_authorization("ViewOrder", {"type": "Order", "id": order_id, "customer_id": "any", "amount": 0, "status": "any"})
    if auth["decision"] != "ALLOW":
        return f"🚫 ACCESS DENIED: ViewOrder on {order_id}."

    response = orders_table.get_item(Key={"order_id": order_id})
    item = response.get("Item")
    if not item:
        return f"Order {order_id} not found."
    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund (requires authentication + ProcessRefund permission).

    Args:
        order_id: Order to refund
        amount: Refund amount in dollars
        reason: Reason for refund
    """
    if not _authenticated_user:
        return "🚫 NOT AUTHENTICATED: Please login first."

    auth = check_authorization("ProcessRefund", {
        "type": "Order",
        "id": order_id,
        "amount": int(amount),
        "customer_id": "any",
        "status": "delivered",
    })

    if auth["decision"] != "ALLOW":
        hero = _authenticated_user.get("hero_name", "Unknown")
        return (
            f"🚫 REFUND DENIED: ${amount:.2f} on {order_id}\n"
            f"   Authenticated as: {hero} (role={_authenticated_user['role']}, max=${_authenticated_user['max_refund']})\n"
            f"   JWT sub: {_authenticated_user.get('sub', 'N/A')}"
        )

    orders_table.update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :s, refund_amount = :a, refund_reason = :r, refunded_by = :u, refund_token_sub = :sub",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "refunded",
            ":a": int(amount),
            ":r": reason,
            ":u": _authenticated_user["email"],
            ":sub": _authenticated_user.get("sub", ""),
        },
    )
    hero = _authenticated_user.get("hero_name", "Unknown")
    return f"✅ REFUND AUTHORIZED: ${amount:.2f} on {order_id}. By: {hero} (JWT verified)"


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a SECURE customer service agent for TechMart.
All actions require authentication (Cognito JWT) and authorization (Cedar policies).
Report any access denials clearly with the reason and user context.
"""

TEST_USERS = [
    ("clark.kent@dailyplanet.com", "Superman", "admin/finance"),
    ("bruce.wayne@waynetech.com", "Batman", "security_lead/security"),
    ("peter.parker@bugle.com", "Spider-Man", "agent/support"),
    ("diana.prince@themyscira.gov", "Wonder Woman", "manager/operations"),
    ("tony.stark@starkindustries.com", "Iron Man", "engineer/engineering"),
]


def run_demo():
    print("=" * 70)
    print("PART 3: Real Identity with Amazon Cognito + JWT Tokens")
    print("=" * 70)
    print()
    print("Real OAuth 2.0 authentication → JWT claims → Cedar policy decisions")
    print()
    print("🦸 Available users (all password: Hero$ecure1!):")
    for email, hero, role in TEST_USERS:
        print(f"    {hero:<14} {email:<35} {role}")
    print()

    # Authenticate
    while True:
        email = input("  Email to login: ").strip()
        if not email:
            continue

        print(f"  Authenticating {email}...")
        result = authenticate(email, DEFAULT_PASSWORD)

        if result["success"]:
            user = result["user"]
            print(f"\n  ✅ Authentication successful!")
            print(f"     Hero: {user['hero_name']}")
            print(f"     Role: {user['role']} | Department: {user['department']}")
            print(f"     Max Refund: ${user['max_refund']}")
            print(f"     Cognito Sub: {user['sub'][:20]}...")
            print(f"     ID Token: {_id_token[:50]}...")
            break
        else:
            print(f"  ❌ Authentication failed: {result['error']}")
            print("  Try again.")

    print()
    print("  Type 'token' to see JWT claims. Type 'switch' to re-authenticate.")
    print("  Type 'quit' to end.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_customer, get_order, process_refund],
    )

    while True:
        print()
        hero = _authenticated_user.get("hero_name", "?") if _authenticated_user else "?"
        try:
            user_input = input(f"  [{hero}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "token":
            claims = decode_jwt_claims(_id_token)
            print(f"\n  📋 JWT ID Token Claims:")
            for k, v in claims.items():
                if k in ("email", "sub", "custom:role", "custom:department", "custom:hero_name", "custom:max_refund", "iss", "aud", "exp"):
                    print(f"     {k}: {v}")
            continue

        if user_input.lower() == "switch":
            email = input("  New email: ").strip()
            result = authenticate(email, DEFAULT_PASSWORD)
            if result["success"]:
                user = result["user"]
                print(f"  ✅ Switched to: {user['hero_name']} ({user['role']}/{user['department']})")
            else:
                print(f"  ❌ Failed: {result['error']}")
            continue

        print()
        response = agent(user_input)
        print(f"\n  Agent: {response}")

    print(f"\n{'=' * 70}")
    print("  Full auth chain: Cognito AuthN → JWT Claims → Cedar AuthZ → Tool Execution")
    print("  In Part 4, we'll show private VPC connectivity.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_demo()
