"""
Module 2 - Part 5: Tool Design for Context Efficiency

Demonstrates how tool response design directly impacts token consumption.
Compares verbose tool responses vs information-dense structured responses.

Shows:
- Verbose tools: return full unstructured text (high token cost)
- Optimized tools: return structured JSON with only relevant fields
- TOON (Token-Oriented Object Notation) concept
- Token savings from information-dense responses
"""

import time
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# VERBOSE TOOLS (high token cost)
# =============================================================================

@tool
def verbose_customer_lookup(customer_id: str) -> str:
    """Look up customer information by ID.

    Args:
        customer_id: The customer ID to look up
    """
    return f"""
CUSTOMER RECORD RETRIEVED FROM DATABASE
========================================

Customer Identification Information:
- Customer ID: {customer_id}
- Full Name: Sarah Chen
- Email Address: sarah.chen@email.com
- Phone Number: +1 (555) 234-5678
- Mailing Address: 1234 Oak Street, Apartment 5B, San Francisco, California, 94102, United States of America
- Date of Birth: March 15, 1988
- Account Created: January 12, 2023
- Last Login: July 28, 2025 at 3:42 PM Pacific Standard Time

Account Details and Status Information:
- Account Status: Active and in Good Standing
- Account Type: Premium Membership (Annual Plan)
- Membership Since: January 12, 2023
- Membership Renewal Date: January 12, 2026
- Payment Method on File: Visa credit card ending in 4532
- Billing Cycle: Annual (next billing January 12, 2026)
- Loyalty Points Balance: 12,450 points (equivalent to $124.50 in store credit)

Purchase History Summary:
- Total Orders Placed: 47 orders
- Total Lifetime Spend: $8,934.22
- Average Order Value: $190.09
- Most Recent Order: TM-78432 (placed July 10, 2025)
- Most Frequently Purchased Category: Smart Home Devices (23 orders)
- Second Most Purchased: Laptops and Accessories (12 orders)
- Third Most Purchased: Audio Equipment (8 orders)
- Returns/Refunds: 3 items returned (return rate: 6.4%)

Support History:
- Total Support Tickets: 8
- Open Tickets: 1 (Ticket #ST-2025-4421 - TechMart Hub connectivity issue)
- Average Resolution Time: 2.3 days
- Customer Satisfaction Score: 4.7/5.0
- Last Contact: July 25, 2025 (phone call regarding Hub Wi-Fi issue)
- Preferred Contact Method: Email
- Support Tier: Priority (Premium member benefit)
- Notes: Customer is technically savvy, prefers detailed explanations

Communication Preferences:
- Marketing Emails: Opted In (weekly newsletter)
- SMS Notifications: Opted In (order updates only)
- Push Notifications: Opted Out
- Language Preference: English (US)
- Time Zone: Pacific Time (UTC-8)

Internal Notes (Staff Only):
- High-value customer with strong lifetime engagement
- Previously expressed interest in beta testing new products
- Referred 3 new customers (referral code: SARAH2023)
- Flagged for VIP upgrade consideration in Q1 2026
- No outstanding account issues or payment concerns
"""


@tool
def verbose_order_lookup(order_id: str) -> str:
    """Look up order details by order ID.

    Args:
        order_id: The order ID to look up
    """
    return f"""
ORDER DETAIL RECORD
========================================

Order Identification:
- Order ID: {order_id}
- Order Date: July 10, 2025 at 2:15 PM PST
- Order Status: Delivered Successfully
- Customer ID: CUST-44821
- Customer Name: Sarah Chen

Shipping Information:
- Shipping Method: Express Delivery (2-day)
- Shipping Cost: $12.99
- Shipping Address: 1234 Oak Street, Apt 5B, San Francisco, CA 94102
- Carrier: FedEx
- Tracking Number: FX-7789234521
- Shipped Date: July 11, 2025
- Estimated Delivery: July 13, 2025
- Actual Delivery: July 12, 2025 (delivered 1 day early)
- Delivery Confirmation: Signed by resident
- Package Weight: 3.2 lbs
- Package Dimensions: 14" x 10" x 6"

Items Ordered:
1. TechMart Hub (Smart Home Controller)
   - SKU: TMH-2025-001
   - Quantity: 1
   - Unit Price: $149.00
   - Color: Matte Black
   - Warranty: Standard 1-year included
   - Serial Number: TMH-SN-88432109

2. Motion Sensor (Pack of 2)
   - SKU: TMS-2025-002
   - Quantity: 1 (pack of 2 sensors)
   - Unit Price: $58.00
   - Color: White
   - Battery Type: CR2450 (included)
   - Serial Numbers: TMS-SN-11234, TMS-SN-11235

Order Financial Summary:
- Subtotal: $207.00
- Shipping: $12.99
- Tax (8.625%): $17.85
- Discount Applied: None
- Total Charged: $237.84
- Payment Method: Visa ending in 4532
- Payment Status: Completed
- Transaction ID: TXN-2025-887432

Order Timeline:
- July 10, 2:15 PM: Order placed
- July 10, 2:16 PM: Payment authorized
- July 10, 2:18 PM: Order confirmed (email sent)
- July 10, 5:30 PM: Order picked and packed
- July 11, 8:00 AM: Shipped (tracking email sent)
- July 11, 9:15 AM: In transit - Oakland hub
- July 12, 6:30 AM: Out for delivery
- July 12, 11:45 AM: Delivered (signature confirmed)

Return/Refund Information:
- Return Window: Open until August 11, 2025 (30-day policy)
- Items Eligible for Return: All items (unopened condition required)
- Refund Method: Original payment method
- Return Shipping: Free for Premium members
- Restocking Fee: None (Premium member benefit)

Related Orders:
- Previous order: TM-65210 (3x Smart Cameras, June 15, 2025)
- Suggested next: TM-BUNDLE-SH (Smart Home Starter Kit expansion)
"""


# =============================================================================
# OPTIMIZED TOOLS (low token cost, information-dense)
# =============================================================================

@tool
def optimized_customer_lookup(customer_id: str) -> str:
    """Look up customer information by ID (optimized response).

    Args:
        customer_id: The customer ID to look up
    """
    return f"""{{
"id":"{customer_id}","name":"Sarah Chen","status":"active_premium",
"since":"2023-01","points":12450,
"orders":{{"total":47,"ltv":"$8,934","avg":"$190","top_cat":"smart_home"}},
"support":{{"open_tickets":1,"ticket":"ST-2025-4421:Hub Wi-Fi","csat":4.7}},
"recent_order":"TM-78432","payment":"visa_4532"
}}"""


@tool
def optimized_order_lookup(order_id: str) -> str:
    """Look up order details by order ID (optimized response).

    Args:
        order_id: The order ID to look up
    """
    return f"""{{
"id":"{order_id}","date":"2025-07-10","status":"delivered","delivered":"2025-07-12",
"items":[{{"name":"TechMart Hub","price":149,"sn":"TMH-SN-88432109"}},{{"name":"Motion Sensor x2","price":58}}],
"total":"$237.84","shipping":"express_$12.99","payment":"visa_4532",
"return_window":"2025-08-11","customer":"CUST-44821:Sarah Chen"
}}"""


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 5: Tool Design for Context Efficiency")
    print("=" * 70)
    print()
    print("Comparing verbose vs optimized tool responses.")
    print("Same agent, same queries — different tool output density.")
    print()

    test_queries = [
        "Look up customer CUST-44821 and tell me about their recent support issue.",
        "What was in their last order TM-78432? Is it still within return window?",
        "Based on their history, what should we proactively offer this customer?",
    ]

    # --- Verbose Tools ---
    print(f"{'━' * 70}")
    print("  🗒️  VERBOSE TOOLS (full unstructured text)")
    print(f"{'━' * 70}\n")

    agent_verbose = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are a customer service agent. Use tools to look up information and provide concise answers to the customer's questions.",
        tools=[verbose_customer_lookup, verbose_order_lookup],
    )

    verbose_timings = []
    for i, query in enumerate(test_queries, 1):
        print(f"  Query {i}: {query}")
        start = time.time()
        response = agent_verbose(query)
        elapsed = time.time() - start
        verbose_timings.append(elapsed)
        print(f"  ⏱  {elapsed:.1f}s")
        resp_str = str(response)
        print(f"  Response: {resp_str[:150]}...")
        print()

    # Count tokens in verbose agent
    verbose_chars = 0
    if hasattr(agent_verbose, "messages"):
        for msg in agent_verbose.messages:
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and "text" in block:
                        verbose_chars += len(block["text"])
            elif isinstance(msg.get("content"), str):
                verbose_chars += len(msg["content"])
    verbose_tokens = verbose_chars // 4

    print(f"  📊 Verbose context: ~{verbose_tokens:,} tokens after {len(test_queries)} queries")

    # --- Optimized Tools ---
    print(f"\n{'━' * 70}")
    print("  ⚡ OPTIMIZED TOOLS (structured, information-dense)")
    print(f"{'━' * 70}\n")

    agent_optimized = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="You are a customer service agent. Use tools to look up information and provide concise answers to the customer's questions.",
        tools=[optimized_customer_lookup, optimized_order_lookup],
    )

    optimized_timings = []
    for i, query in enumerate(test_queries, 1):
        print(f"  Query {i}: {query}")
        start = time.time()
        response = agent_optimized(query)
        elapsed = time.time() - start
        optimized_timings.append(elapsed)
        print(f"  ⏱  {elapsed:.1f}s")
        resp_str = str(response)
        print(f"  Response: {resp_str[:150]}...")
        print()

    # Count tokens in optimized agent
    optimized_chars = 0
    if hasattr(agent_optimized, "messages"):
        for msg in agent_optimized.messages:
            if isinstance(msg.get("content"), list):
                for block in msg["content"]:
                    if isinstance(block, dict) and "text" in block:
                        optimized_chars += len(block["text"])
            elif isinstance(msg.get("content"), str):
                optimized_chars += len(msg["content"])
    optimized_tokens = optimized_chars // 4

    print(f"  📊 Optimized context: ~{optimized_tokens:,} tokens after {len(test_queries)} queries")

    # --- Comparison ---
    print(f"\n{'═' * 70}")
    print("  COMPARISON")
    print(f"{'═' * 70}\n")

    savings_pct = ((verbose_tokens - optimized_tokens) / verbose_tokens * 100) if verbose_tokens > 0 else 0

    print(f"  {'Metric':<25} {'Verbose':>12} {'Optimized':>12} {'Savings':>10}")
    print(f"  {'─' * 60}")
    print(f"  {'Context tokens':<25} {verbose_tokens:>11,} {optimized_tokens:>11,} {savings_pct:>9.0f}%")

    for i in range(len(test_queries)):
        vt = verbose_timings[i]
        ot = optimized_timings[i]
        print(f"  {'Query ' + str(i+1) + ' time':<25} {vt:>11.1f}s {ot:>11.1f}s")

    total_v = sum(verbose_timings)
    total_o = sum(optimized_timings)
    print(f"  {'Total time':<25} {total_v:>11.1f}s {total_o:>11.1f}s")

    print(f"\n  Token Reduction: ~{savings_pct:.0f}%")
    print()

    # Tool output comparison
    print(f"{'━' * 70}")
    print("  TOOL OUTPUT COMPARISON (Customer Lookup)")
    print(f"{'━' * 70}\n")

    verbose_output = verbose_customer_lookup("CUST-44821")
    optimized_output = optimized_customer_lookup("CUST-44821")

    print(f"  Verbose output:   {len(verbose_output):>5} chars (~{len(verbose_output)//4} tokens)")
    print(f"  Optimized output: {len(optimized_output):>5} chars (~{len(optimized_output)//4} tokens)")
    print(f"  Reduction:        {(1 - len(optimized_output)/len(verbose_output))*100:.0f}%")

    print(f"\n  Optimized output sample:")
    print(f"  {optimized_output}")

    print(f"\n{'─' * 70}")
    print("  Key Principles:")
    print("  1. Return only fields the agent needs for the current task")
    print("  2. Use compact formats (JSON, TOON) over prose")
    print("  3. Avoid verbose error messages and stack traces")
    print("  4. Structure data hierarchically for efficient parsing")
    print("  5. In production, use AgentCore Gateway for semantic tool search")
    print(f"{'─' * 70}\n")

    # Interactive follow-up
    print("  Continue chatting with the optimized agent. Type 'quit' to end.")
    print()

    while True:
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        start = time.time()
        response = agent_optimized(user_input)
        elapsed = time.time() - start
        print(f"\n  Agent: {response}")
        print(f"  ⏱  {elapsed:.1f}s\n")

    print()


if __name__ == "__main__":
    run_demo()
