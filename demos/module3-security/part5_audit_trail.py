"""
Module 3 - Part 5: CloudWatch Audit Trail and Compliance

Demonstrates real structured logging to CloudWatch with full audit metadata.
Every agent action is logged with identity, reasoning, timestamps, and outcome.

Shows:
- Structured JSON audit logs written to CloudWatch
- Action logging (what the agent did)
- Identity context (who authorized it)
- Reasoning chains (why it made the decision)
- CloudWatch Insights queries for compliance reports
"""

import os
import json
import time
import uuid
from datetime import datetime
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m3-demo-customers")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m3-demo-orders")
AUDIT_LOG_GROUP = os.environ.get("AUDIT_LOG_GROUP", "/m3-demo/agent-audit")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)
logs_client = boto3.client("logs", region_name=REGION)

# Session context
_session_id = str(uuid.uuid4())[:8]
_current_user = {
    "email": "clark.kent@dailyplanet.com",
    "role": "admin",
    "department": "finance",
    "hero_name": "Superman",
}
_audit_records = []  # Local cache for display


def write_audit_log(event: dict):
    """Write structured audit event to CloudWatch Logs."""
    log_event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": _session_id,
        "user": _current_user,
        **event,
    }

    _audit_records.append(log_event)

    # Write to CloudWatch
    try:
        stream_name = f"session-{_session_id}"

        # Ensure log stream exists
        try:
            logs_client.create_log_stream(
                logGroupName=AUDIT_LOG_GROUP,
                logStreamName=stream_name,
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass

        logs_client.put_log_events(
            logGroupName=AUDIT_LOG_GROUP,
            logStreamName=stream_name,
            logEvents=[
                {
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps(log_event),
                }
            ],
        )
    except Exception as e:
        print(f"    ⚠️  Audit log write failed: {e}")


# =============================================================================
# AUDITED TOOLS
# =============================================================================

@tool
def get_customer(customer_id: str) -> str:
    """Get customer details with full audit logging.

    Args:
        customer_id: Customer ID (e.g., CUST-1001)
    """
    write_audit_log({
        "action": "ViewCustomer",
        "resource": customer_id,
        "resource_type": "customer",
        "outcome": "initiated",
        "reasoning": f"Agent accessed customer record {customer_id} to fulfill user request",
    })

    response = customers_table.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")

    if not item:
        write_audit_log({
            "action": "ViewCustomer",
            "resource": customer_id,
            "resource_type": "customer",
            "outcome": "not_found",
            "reasoning": "Customer record does not exist in database",
        })
        return f"Customer {customer_id} not found."

    write_audit_log({
        "action": "ViewCustomer",
        "resource": customer_id,
        "resource_type": "customer",
        "outcome": "success",
        "data_accessed": list(item.keys()),
        "reasoning": "Successfully retrieved customer record",
    })

    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def get_order(order_id: str) -> str:
    """Get order details with full audit logging.

    Args:
        order_id: Order ID (e.g., ORD-5001)
    """
    write_audit_log({
        "action": "ViewOrder",
        "resource": order_id,
        "resource_type": "order",
        "outcome": "initiated",
        "reasoning": f"Agent accessed order record {order_id}",
    })

    response = orders_table.get_item(Key={"order_id": order_id})
    item = response.get("Item")

    if not item:
        write_audit_log({
            "action": "ViewOrder",
            "resource": order_id,
            "resource_type": "order",
            "outcome": "not_found",
        })
        return f"Order {order_id} not found."

    write_audit_log({
        "action": "ViewOrder",
        "resource": order_id,
        "resource_type": "order",
        "outcome": "success",
        "data_accessed": list(item.keys()),
        "order_customer": item.get("customer_id", "unknown"),
    })

    return str({k: str(v) if hasattr(v, "as_tuple") else v for k, v in item.items()})


@tool
def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund with comprehensive audit logging.

    Args:
        order_id: Order to refund
        amount: Refund amount in dollars
        reason: Reason for refund
    """
    write_audit_log({
        "action": "ProcessRefund",
        "resource": order_id,
        "resource_type": "order",
        "outcome": "initiated",
        "amount": amount,
        "reason": reason,
        "reasoning": f"Refund request: ${amount} on {order_id} because: {reason}",
        "risk_level": "high" if amount > 1000 else "medium" if amount > 200 else "low",
    })

    # Process it
    orders_table.update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :s, refund_amount = :a, refund_reason = :r, refunded_by = :u",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": "refunded",
            ":a": int(amount),
            ":r": reason,
            ":u": _current_user["email"],
        },
    )

    write_audit_log({
        "action": "ProcessRefund",
        "resource": order_id,
        "resource_type": "order",
        "outcome": "success",
        "amount": amount,
        "reason": reason,
        "processed_by": _current_user["email"],
        "reasoning": f"Refund authorized and processed. Amount ${amount} returned to customer.",
    })

    return f"✅ Refund ${amount:.2f} processed on {order_id}. Fully audited."


@tool
def view_audit_log() -> str:
    """View the audit trail for this session.
    """
    if not _audit_records:
        return "No audit records in this session."

    lines = [f"📋 AUDIT TRAIL — Session {_session_id} ({len(_audit_records)} events)\n"]
    for i, record in enumerate(_audit_records, 1):
        ts = record.get("timestamp", "")
        action = record.get("action", "unknown")
        resource = record.get("resource", "")
        outcome = record.get("outcome", "")
        reasoning = record.get("reasoning", "")
        user_email = record.get("user", {}).get("email", "unknown")

        outcome_icon = {"success": "✅", "initiated": "▶️", "denied": "🚫", "not_found": "⚠️"}.get(outcome, "❓")

        lines.append(f"  {i}. [{ts}] {outcome_icon} {action} on {resource}")
        lines.append(f"     Outcome: {outcome} | User: {user_email}")
        if reasoning:
            lines.append(f"     Reasoning: {reasoning}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a FULLY AUDITED customer service agent for TechMart.
Every action you take is logged to CloudWatch with:
- What you did (action + resource)
- Why you did it (reasoning chain)
- Who authorized it (identity context)
- When it happened (timestamp)
- What data you accessed (field-level tracking)

Help users with their requests. They can ask you to 'show audit log' at any time
to see the complete trail of what happened in this session.
"""


def run_demo():
    global _current_user

    print("=" * 70)
    print("PART 5: CloudWatch Audit Trail and Compliance")
    print("=" * 70)
    print()
    print("Every agent action is logged to CloudWatch with full metadata.")
    print(f"Session ID: {_session_id}")
    print(f"Log Group: {AUDIT_LOG_GROUP}")
    print()
    print("🦸 Select user context:")
    print("  [1] Superman (Clark Kent) — admin/finance")
    print("  [2] Spider-Man (Peter Parker) — agent/support")
    print()

    choice = input("  Select (1/2): ").strip()
    if choice == "2":
        _current_user = {
            "email": "peter.parker@bugle.com",
            "role": "agent",
            "department": "support",
            "hero_name": "Spider-Man",
        }

    print(f"\n  Logged in as: {_current_user['hero_name']} ({_current_user['role']}/{_current_user['department']})")
    print()
    print("  Try:")
    print("    • 'Look up customer CUST-1001'")
    print("    • 'Process a $200 refund on ORD-5001 for defective item'")
    print("    • 'Show the audit log' (see what was recorded)")
    print("    • 'query' (run CloudWatch Insights query)")
    print()
    print("  Type 'quit' to end.")
    print("=" * 70)

    # Log session start
    write_audit_log({
        "action": "SessionStart",
        "resource": "session",
        "resource_type": "session",
        "outcome": "success",
        "reasoning": "User initiated agent session",
    })

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[get_customer, get_order, process_refund, view_audit_log],
    )

    while True:
        print()
        hero = _current_user.get("hero_name", "?")
        try:
            user_input = input(f"  [{hero}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "query":
            run_compliance_query()
            continue

        print()
        response = agent(user_input)
        print(f"\n  Agent: {response}")

    # Log session end
    write_audit_log({
        "action": "SessionEnd",
        "resource": "session",
        "resource_type": "session",
        "outcome": "success",
        "total_events": len(_audit_records),
        "reasoning": "User ended agent session",
    })

    # Final audit summary
    print(f"\n{'═' * 70}")
    print(f"  AUDIT SUMMARY — Session {_session_id}")
    print(f"{'═' * 70}\n")
    print(f"  Total audit events: {len(_audit_records)}")
    print(f"  CloudWatch Log Group: {AUDIT_LOG_GROUP}")
    print(f"  Log Stream: session-{_session_id}")
    print()

    # Action breakdown
    actions = {}
    for r in _audit_records:
        a = r.get("action", "unknown")
        actions[a] = actions.get(a, 0) + 1
    print("  Action breakdown:")
    for action, count in sorted(actions.items()):
        print(f"    {action}: {count}")

    print()
    print("  To query in AWS Console:")
    print(f"  CloudWatch > Logs > Insights > Log group: {AUDIT_LOG_GROUP}")
    print(f"  Query: fields @timestamp, action, resource, outcome, user.hero_name")
    print(f"         | filter session_id = '{_session_id}'")
    print(f"         | sort @timestamp asc")
    print()


def run_compliance_query():
    """Run a CloudWatch Insights query against the audit log."""
    print(f"\n  📊 Running CloudWatch Insights query...")
    print(f"     Log Group: {AUDIT_LOG_GROUP}")

    query = """
fields @timestamp, action, resource, outcome, user.hero_name as hero, user.role as role
| filter action != 'SessionStart' and action != 'SessionEnd'
| sort @timestamp desc
| limit 20
"""
    print(f"     Query: {query.strip()}")

    try:
        response = logs_client.start_query(
            logGroupName=AUDIT_LOG_GROUP,
            startTime=int((time.time() - 3600) * 1000),  # Last hour
            endTime=int(time.time() * 1000),
            queryString=query,
        )
        query_id = response["queryId"]

        # Wait for results
        print("     Waiting for results...")
        for _ in range(10):
            time.sleep(1)
            result = logs_client.get_query_results(queryId=query_id)
            if result["status"] == "Complete":
                break

        results = result.get("results", [])
        if results:
            print(f"\n  📋 Query Results ({len(results)} events):")
            print(f"  {'─' * 60}")
            for row in results[:10]:
                fields = {f["field"]: f["value"] for f in row}
                ts = fields.get("@timestamp", "?")
                action = fields.get("action", "?")
                resource = fields.get("resource", "?")
                outcome = fields.get("outcome", "?")
                hero = fields.get("hero", "?")
                print(f"  {ts} | {hero:<12} | {action:<16} | {resource:<12} | {outcome}")
        else:
            print("  No results (logs may not have been ingested yet)")

    except Exception as e:
        print(f"  ⚠️  Query failed: {e}")
        print("  (CloudWatch Logs may need a moment to ingest events)")


if __name__ == "__main__":
    run_demo()
