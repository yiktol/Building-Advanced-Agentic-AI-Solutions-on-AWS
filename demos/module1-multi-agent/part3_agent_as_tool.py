"""
Module 1 - Part 3: Agent-as-Tool Pattern (MCP-Style Communication)

Demonstrates how agents can be exposed as reusable tools that any other
agent or system can invoke — promoting loose coupling and reusability.

This pattern is analogous to Model Context Protocol (MCP) where agents
are discoverable capabilities with well-defined interfaces.

Benefits shown:
- Agents are reusable across different orchestrators/systems
- Clear interface contracts (input/output schemas)
- Loose coupling: consumers don't need to know implementation details
- Easy to swap, version, or scale individual agents independently
"""

from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# AGENT-AS-TOOL: Self-contained agents with clear interfaces
# =============================================================================

@tool
def product_lookup(product_name: str) -> str:
    """Look up product details including specs, price, and availability.

    Args:
        product_name: The product to look up (e.g., "TechMart Pro 15")
    """
    # This agent acts as a tool — it has a clear input/output contract
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a product database lookup service.
Given a product name, return structured information.

PRODUCT DATABASE:
- TechMart Air: $599, 14" Intel i5, 8GB RAM, 256GB SSD, Wi-Fi 5, Bluetooth 5.0, 1.2kg
- TechMart Pro 15: $799, 15.6" Intel i7, 16GB RAM, 512GB SSD, Wi-Fi 6, Bluetooth 5.0, 1.8kg
- TechMart Titan: $1,299, 16" RTX 4060, 32GB RAM, 1TB SSD, Wi-Fi 6E, Bluetooth 5.3, 2.4kg
- TechMart Hub: $149, Wi-Fi 6 + Bluetooth 5.0 + Zigbee 3.0, max 50 devices
- Smart Camera: $79, 1080p, night vision, Wi-Fi direct or via Hub
- Motion Sensor: $29, Zigbee 3.0, 120° detection, 2yr battery

Return a concise JSON-like summary with: name, price, key_specs, compatibility_notes, in_stock (always true for demo).
If product not found, say so clearly.
""",
    )
    print(f"    🔍 [Product Lookup Tool: searching for '{product_name}']")
    response = agent(f"Look up: {product_name}")
    return str(response)


@tool
def compatibility_check(product_a: str, product_b: str) -> str:
    """Check compatibility between two TechMart products.

    Args:
        product_a: First product name
        product_b: Second product name
    """
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a product compatibility verification service.
Given two products, determine if they work together.

COMPATIBILITY MATRIX:
- All TechMart laptops have Bluetooth 5.0+ → compatible with TechMart Hub
- TechMart Hub supports: Wi-Fi 6, Bluetooth 5.0, Zigbee 3.0 devices
- Smart Cameras: connect via Wi-Fi (direct) or via Hub (preferred for central management)
- Motion Sensors: Zigbee only → REQUIRE TechMart Hub (no direct laptop connection)
- TechMart Air (Wi-Fi 5): compatible with Hub but slightly slower smart home response
- TechMart Pro 15 / Titan (Wi-Fi 6/6E): optimal Hub performance

Return: compatible (yes/no), connection_method, performance_notes, any_limitations.
""",
    )
    print(f"    🔗 [Compatibility Check Tool: '{product_a}' ↔ '{product_b}']")
    response = agent(f"Check compatibility between: {product_a} and {product_b}")
    return str(response)


@tool
def order_status(order_id: str) -> str:
    """Check the status of a customer order.

    Args:
        order_id: The order ID (e.g., "TM-78432")
    """
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are an order management system lookup service.
Given an order ID, return its status.

MOCK ORDER DATABASE:
- TM-78432: Delivered 2025-07-15, items: [TechMart Hub ($149), Motion Sensor x2 ($58)], total: $219.99 (includes $12.99 express shipping), subscription: cancelled 2025-07-28
- TM-91001: Shipped 2025-07-28, items: [TechMart Pro 15 ($799)], est. delivery: 2025-08-01
- TM-65210: Processing, items: [Smart Camera x3 ($237)], payment: pending verification

Return: order_id, status, items, total, relevant_dates, any_notes.
""",
    )
    print(f"    📦 [Order Status Tool: looking up '{order_id}']")
    response = agent(f"Look up order: {order_id}")
    return str(response)


# =============================================================================
# CONSUMER AGENTS: Different agents that USE the tools above
# =============================================================================

def create_sales_agent() -> Agent:
    """A sales agent that uses product tools to help customers buy."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a TechMart Sales Agent helping customers find and purchase products.

Use the available tools to:
- Look up product details when customers ask about specific items
- Check compatibility when customers want to know if products work together
- Help customers make informed purchasing decisions

Be enthusiastic but honest. If products aren't compatible, say so clearly.
Focus on finding the best solution for the customer's needs.
""",
        tools=[product_lookup, compatibility_check],
    )


def create_support_agent() -> Agent:
    """A support agent that uses order and product tools to resolve issues."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a TechMart Support Agent helping with post-purchase issues.

Use the available tools to:
- Check order status to understand what the customer purchased
- Look up product details to provide accurate troubleshooting info
- Check compatibility if the customer's products should work together

Focus on resolving the customer's issue efficiently.
Be empathetic and solution-oriented.
""",
        tools=[product_lookup, compatibility_check, order_status],
    )


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 3: Agent-as-Tool Pattern (MCP-Style Communication)")
    print("=" * 70)
    print()
    print("Agents are exposed as reusable tools with clear interfaces:")
    print("  🔍 product_lookup — look up any product details")
    print("  🔗 compatibility_check — verify two products work together")
    print("  📦 order_status — check order details and status")
    print()
    print("Choose an agent to chat with:")
    print("  [1] 💰 Sales Agent — uses product_lookup + compatibility_check")
    print("  [2] 🛠️  Support Agent — uses all three tools")
    print()

    while True:
        choice = input("  Select agent (1 or 2): ").strip()
        if choice in ("1", "2"):
            break
        print("  Please enter 1 or 2.")

    if choice == "1":
        agent = create_sales_agent()
        agent_name = "Sales Agent"
    else:
        agent = create_support_agent()
        agent_name = "Support Agent"

    print()
    print(f"  Chatting with {agent_name}. Type 'quit' or 'exit' to end.")
    print("=" * 70)

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        print()
        response = agent(user_input)
        print(f"\n  {agent_name}: {response}")

    print("\n" + "=" * 70)
    print("END OF PART 3")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
