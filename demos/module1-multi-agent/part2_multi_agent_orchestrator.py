"""
Module 1 - Part 2: Multi-Agent Orchestrator Pattern (Framework-Layer Communication)

Demonstrates the framework-layer communication pattern where a centralized
orchestrator routes queries to specialized agents.

Benefits shown:
- Each agent is a domain expert with focused context
- Orchestrator provides deterministic routing
- Fault isolation: one agent failing doesn't crash the system
- Each agent's context stays lean and relevant
"""

from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# SPECIALIZED AGENTS
# =============================================================================

def create_billing_agent() -> Agent:
    """Creates a billing specialist agent with deep domain knowledge."""
    system_prompt = """You are the Billing Specialist for TechMart.

You ONLY handle billing inquiries. You are an expert in:
- Refund processing (30-day window, unused items only, original payment method)
- Charge explanations (subscriptions $9.99/month, shipping tiers, taxes)
- Payment method updates (require last 4 digits verification)
- Price match claims (14-day window, same SKU, authorized retailers only)
- Subscription management (cancel, upgrade, downgrade)

REFUND RULES:
- Within 30 days of delivery: full refund
- 30-60 days: store credit only
- Shipping fees: refundable if item was defective or wrong item sent
- Subscription charges: refundable if cancelled before billing date

Always verify the order number before processing any changes.
If a query is NOT about billing, say "This is outside my billing expertise."
"""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
    )


def create_tech_support_agent() -> Agent:
    """Creates a technical support specialist agent."""
    system_prompt = """You are the Technical Support Specialist for TechMart.

You ONLY handle technical issues. You are an expert in:
- Wi-Fi/networking (routers, mesh systems, interference, firmware updates)
- Smart home devices (TechMart Hub, sensors, cameras, pairing protocols)
- Software troubleshooting (drivers, compatibility, installation)
- Device connectivity (Bluetooth 5.0, Zigbee, Z-Wave protocols)

TECHMART HUB SPECS:
- Firmware latest: v3.0.1 (anything below v2.5 needs update)
- Supports: Bluetooth 5.0, Wi-Fi 6, Zigbee 3.0
- Max devices: 50 (5 per direct Bluetooth, rest via Zigbee/Wi-Fi)
- Common issues: v2.1.x firmware has known Wi-Fi dropout bug (fixed in v2.5+)

TROUBLESHOOTING APPROACH:
1. Identify the device and current firmware/software version
2. Check for known issues with that version
3. Provide step-by-step resolution
4. Suggest preventive measures

If a query is NOT about technical support, say "This is outside my technical expertise."
"""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
    )


def create_product_agent() -> Agent:
    """Creates a product recommendation specialist agent."""
    system_prompt = """You are the Product Recommendation Specialist for TechMart.

You ONLY handle product recommendations. You are an expert in:
- Matching customer needs to products
- Comparing specifications and value propositions
- Bundle suggestions for maximum value
- Compatibility verification between products

PRODUCT CATALOG:
Laptops:
- TechMart Air ($599): 14", Intel i5, 8GB RAM, 256GB SSD - great for writing, browsing
- TechMart Pro 15 ($799): 15.6", Intel i7, 16GB RAM, 512GB SSD - video editing capable
- TechMart Titan ($1,299): 16", RTX 4060, 32GB RAM, 1TB SSD - gaming/creative pro

Smart Home:
- TechMart Hub ($149): Central controller, Wi-Fi 6 + Bluetooth 5.0 + Zigbee
- Motion Sensors ($29): Zigbee, 120° detection, 2-year battery
- Smart Cameras ($79): 1080p, night vision, Wi-Fi direct or via Hub

Accessories:
- USB-C Dock ($89): 3 USB-A, 2 USB-C, HDMI, Ethernet
- Wireless Mouse+Keyboard ($49): Bluetooth, multi-device switching

COMPATIBILITY NOTES:
- TechMart Pro 15 and Titan have Wi-Fi 6 (compatible with TechMart Hub)
- TechMart Air has Wi-Fi 5 (still compatible, slightly slower smart home control)
- All laptops have Bluetooth 5.0 (direct Hub pairing supported)

If a query is NOT about products, say "This is outside my product expertise."
"""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
    )


# =============================================================================
# ORCHESTRATOR WITH AGENTS AS TOOLS
# =============================================================================

# Create specialized agents (module-level so tools can reference them)
billing_agent = create_billing_agent()
tech_support_agent = create_tech_support_agent()
product_agent = create_product_agent()


@tool
def ask_billing_agent(query: str) -> str:
    """Route billing-related queries to the billing specialist.
    Use for: refunds, charges, payments, subscriptions, price matching.
    """
    print(f"    📋 [Routing to Billing Agent]")
    response = billing_agent(query)
    return str(response)


@tool
def ask_tech_support_agent(query: str) -> str:
    """Route technical issues to the tech support specialist.
    Use for: device troubleshooting, connectivity, firmware, software issues.
    """
    print(f"    🔧 [Routing to Tech Support Agent]")
    response = tech_support_agent(query)
    return str(response)


@tool
def ask_product_agent(query: str) -> str:
    """Route product questions to the product recommendation specialist.
    Use for: product suggestions, comparisons, compatibility, bundles.
    """
    print(f"    🛍️  [Routing to Product Agent]")
    response = product_agent(query)
    return str(response)


def create_orchestrator() -> Agent:
    """Creates the orchestrator agent that routes to specialists."""
    system_prompt = """You are the Customer Service Orchestrator for TechMart.

Your role is to:
1. Understand the customer's intent
2. Route to the appropriate specialist agent
3. Synthesize responses from multiple specialists if needed
4. Maintain conversational continuity

ROUTING RULES:
- Billing questions (refunds, charges, payments) → ask_billing_agent
- Technical issues (troubleshooting, connectivity) → ask_tech_support_agent
- Product questions (recommendations, comparisons) → ask_product_agent

MULTI-DOMAIN QUERIES:
If a customer query spans multiple domains, break it into parts and route
each part to the appropriate specialist. Then combine their responses into
a coherent answer.

Keep your orchestration transparent — briefly mention which specialist
is handling each part of a complex query.
"""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=system_prompt,
        tools=[ask_billing_agent, ask_tech_support_agent, ask_product_agent],
    )


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 2: Multi-Agent Orchestrator (Framework-Layer Pattern)")
    print("=" * 70)
    print()
    print("An orchestrator routes queries to specialized agents:")
    print("  📋 Billing Agent — refunds, charges, subscriptions")
    print("  🔧 Tech Support Agent — devices, connectivity, firmware")
    print("  🛍️  Product Agent — recommendations, compatibility")
    print()
    print("Watch the routing decisions and domain-expert responses.")
    print("Type 'quit' or 'exit' to end the conversation.")
    print("=" * 70)

    orchestrator = create_orchestrator()

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
        response = orchestrator(user_input)
        print(f"\n  Orchestrator: {response}")

    print("\n" + "=" * 70)
    print("END OF PART 2")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
