"""
Module 5 - Part 1: Multi-Agent E-Commerce System

The complete production system that students will evaluate against
Well-Architected pillars. Features 4 specialist agents coordinated
by an orchestrator, backed by real DynamoDB data.

This is the "system under review" for Parts 2-5.
"""

import os
import boto3
from decimal import Decimal
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "m5-demo-products")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m5-demo-orders")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m5-demo-customers")

dynamodb = boto3.resource("dynamodb", region_name=REGION)
products_table = dynamodb.Table(PRODUCTS_TABLE)
orders_table = dynamodb.Table(ORDERS_TABLE)
customers_table = dynamodb.Table(CUSTOMERS_TABLE)


# =============================================================================
# DATA ACCESS TOOLS
# =============================================================================

@tool
def search_products(query: str) -> str:
    """Search the product catalog.

    Args:
        query: Product search query (name or category)
    """
    response = products_table.scan()
    items = response.get("Items", [])
    matches = [i for i in items if query.lower() in i.get("name", "").lower() or query.lower() in i.get("category", "").lower()]
    if not matches:
        return f"No products matching '{query}'."
    return str([{k: str(v) if isinstance(v, Decimal) else v for k, v in m.items()} for m in matches[:5]])


@tool
def get_order(order_id: str) -> str:
    """Look up an order by ID.

    Args:
        order_id: Order ID (e.g., ORD-7001)
    """
    response = orders_table.get_item(Key={"order_id": order_id})
    item = response.get("Item")
    if not item:
        return f"Order {order_id} not found."
    return str({k: str(v) if isinstance(v, Decimal) else v for k, v in item.items()})


@tool
def get_customer(customer_id: str) -> str:
    """Look up customer by ID.

    Args:
        customer_id: Customer ID (e.g., CUST-2001)
    """
    response = customers_table.get_item(Key={"customer_id": customer_id})
    item = response.get("Item")
    if not item:
        return f"Customer {customer_id} not found."
    return str({k: str(v) if isinstance(v, Decimal) else v for k, v in item.items()})


@tool
def get_customer_orders(customer_id: str) -> str:
    """Get all orders for a customer.

    Args:
        customer_id: Customer ID
    """
    response = orders_table.query(
        IndexName="customer-index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("customer_id").eq(customer_id),
    )
    items = response.get("Items", [])
    if not items:
        return f"No orders found for {customer_id}."
    return str([{k: str(v) if isinstance(v, Decimal) else v for k, v in i.items()} for i in items])


@tool
def process_refund(order_id: str, amount: float, reason: str) -> str:
    """Process a refund on an order.

    Args:
        order_id: Order to refund
        amount: Amount to refund
        reason: Reason for refund
    """
    orders_table.update_item(
        Key={"order_id": order_id},
        UpdateExpression="SET #s = :s, refund_amount = :a, refund_reason = :r",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":s": "refunded", ":a": int(amount), ":r": reason},
    )
    return f"Refund of ${amount:.2f} processed on {order_id}. Reason: {reason}"


@tool
def check_compatibility(product_a: str, product_b: str) -> str:
    """Check if two products are compatible.

    Args:
        product_a: First product name
        product_b: Second product name
    """
    # Compatibility rules
    rules = {
        ("TechMart Hub", "Smart Camera"): "Compatible via Wi-Fi. Hub recommended for centralized management.",
        ("TechMart Hub", "Motion Sensor"): "Compatible via Zigbee 3.0. Hub required for motion sensors.",
        ("TechMart Pro 15", "TechMart Hub"): "Compatible. Pro 15 has Wi-Fi 6 + BT 5.0 for optimal Hub control.",
        ("TechMart Air", "TechMart Hub"): "Compatible. Air has Wi-Fi 5 — works but slightly slower than Wi-Fi 6 devices.",
        ("TechMart Titan", "TechMart Hub"): "Compatible. Titan has Wi-Fi 6E for best-in-class Hub performance.",
    }
    key = (product_a, product_b)
    rev_key = (product_b, product_a)
    result = rules.get(key) or rules.get(rev_key)
    if result:
        return f"{product_a} + {product_b}: {result}"
    return f"{product_a} + {product_b}: No specific compatibility data. Both are TechMart products and should work together."


# =============================================================================
# SPECIALIST AGENTS
# =============================================================================

billing_agent = Agent(
    model=BedrockModel(model_id=MODEL_ID),
    system_prompt="""You are the Billing Specialist. Handle refunds, charges, payment questions.
Rules: 30-day full refund, 60-day store credit. Express shipping only refundable if item defective.
If not billing-related, say so.""",
    tools=[get_order, process_refund, get_customer],
)

tech_agent = Agent(
    model=BedrockModel(model_id=MODEL_ID),
    system_prompt="""You are the Technical Support Specialist. Handle device issues, firmware, connectivity.
TechMart Hub v2.1.x has known Wi-Fi bug (update to v3.0.1). Motion sensors need Zigbee pairing (hold 5s).
If not tech-related, say so.""",
    tools=[search_products, check_compatibility],
)

product_agent = Agent(
    model=BedrockModel(model_id=MODEL_ID),
    system_prompt="""You are the Product Specialist. Handle recommendations, comparisons, compatibility.
Always check the catalog and compatibility before recommending.
If not product-related, say so.""",
    tools=[search_products, check_compatibility],
)

shipping_agent = Agent(
    model=BedrockModel(model_id=MODEL_ID),
    system_prompt="""You are the Shipping Specialist. Handle order status, delivery tracking, shipping options.
Standard: 5-7 days. Express: 2 days ($12.99). Same-day: select areas ($24.99).
If not shipping-related, say so.""",
    tools=[get_order, get_customer_orders],
)


@tool
def ask_billing(query: str) -> str:
    """Route to billing specialist for refunds, charges, payments.

    Args:
        query: Billing-related query
    """
    return str(billing_agent(query))


@tool
def ask_tech_support(query: str) -> str:
    """Route to tech support for device issues, firmware, connectivity.

    Args:
        query: Technical support query
    """
    return str(tech_agent(query))


@tool
def ask_product_specialist(query: str) -> str:
    """Route to product specialist for recommendations and comparisons.

    Args:
        query: Product-related query
    """
    return str(product_agent(query))


@tool
def ask_shipping(query: str) -> str:
    """Route to shipping specialist for order status and delivery.

    Args:
        query: Shipping/delivery query
    """
    return str(shipping_agent(query))


# =============================================================================
# ORCHESTRATOR
# =============================================================================

def create_orchestrator() -> Agent:
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are the Customer Service Orchestrator for TechMart e-commerce.

Route queries to the appropriate specialist:
- Billing (refunds, charges, payments) → ask_billing
- Tech Support (devices, firmware, connectivity) → ask_tech_support
- Products (recommendations, comparisons, specs) → ask_product_specialist
- Shipping (order status, delivery, tracking) → ask_shipping

For multi-domain queries, route to multiple specialists and synthesize.
Be transparent about which specialist is handling each part.
""",
        tools=[ask_billing, ask_tech_support, ask_product_specialist, ask_shipping],
    )


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 1: Multi-Agent E-Commerce System")
    print("=" * 70)
    print()
    print("  Full production multi-agent system with:")
    print("    📋 Billing Agent — refunds, charges")
    print("    🔧 Tech Support Agent — devices, firmware")
    print("    🛍️  Product Agent — recommendations, compatibility")
    print("    🚚 Shipping Agent — order status, delivery")
    print("    🎯 Orchestrator — routes to specialists")
    print()
    print("  Backed by real DynamoDB: products, orders, customers")
    print()
    print("  This is the system evaluated in Parts 2-5.")
    print("  Type 'quit' to end.")
    print("=" * 70)

    orchestrator = create_orchestrator()

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        print()
        response = orchestrator(user_input)
        print(f"\n  Agent: {response}")

    print()


if __name__ == "__main__":
    run_demo()
