"""
Module 1 - Part 1: Single Agent Limitations

Demonstrates the cognitive load problem when a single agent handles
billing, technical support, and product recommendations simultaneously.

Notice how the agent may:
- Confuse billing procedures with technical troubleshooting
- Lose context as the conversation grows
- Provide generic rather than domain-expert responses
"""

from strands import Agent
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# A single agent with an overloaded system prompt trying to cover everything
SYSTEM_PROMPT = """You are a customer service agent for TechMart, an electronics e-commerce company.

You handle ALL customer inquiries including:

BILLING:
- Process refunds (verify order, check eligibility: within 30 days, unused items only)
- Explain charges (subscription fees are $9.99/month, shipping is $5.99 standard)
- Update payment methods (require last 4 digits of current card for verification)

TECHNICAL SUPPORT:
- Wi-Fi router troubleshooting (check firmware version, suggest channel switching for interference)
- Smart device pairing (Bluetooth 5.0 required, max 5 devices per hub)
- Software installation (verify OS compatibility, minimum 4GB RAM, 10GB disk space)

PRODUCT RECOMMENDATIONS:
- Budget laptops: TechMart Pro 15 ($799), TechMart Air ($599)
- Gaming: TechMart Titan ($1,299), accessories bundle ($199)
- Smart home: TechMart Hub ($149), sensors ($29 each), cameras ($79 each)

POLICIES:
- Refund window: 30 days from delivery
- Warranty: 1 year standard, 3 years extended ($99)
- Shipping: Standard 5-7 days, Express 2 days ($12.99), Same-day ($24.99)
- Price match: Within 14 days, must be same SKU from authorized retailer

Always verify customer identity before processing any account changes.
Track conversation context carefully across all domains.
"""

def run_demo():
    print("=" * 70)
    print("PART 1: Single Agent - Demonstrating Cognitive Load Limitations")
    print("=" * 70)
    print()
    print("This single agent handles billing, tech support, AND recommendations.")
    print("Try asking questions that span multiple domains to see it struggle.")
    print()
    print("Type 'quit' or 'exit' to end the conversation.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

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
        print(f"\n  Agent: {response}")

    print("\n" + "=" * 70)
    print("END OF PART 1")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
