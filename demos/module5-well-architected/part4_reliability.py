"""
Module 5 - Part 4: Reliability — Fault Tolerance and Graceful Degradation

Demonstrates multi-agent fault isolation, circuit breakers, and
fallback routing when specialist agents fail.

Shows:
- Independent failure domains (one agent failure doesn't crash system)
- Graceful degradation to fallback agent
- Circuit breaker per specialist
- Automatic recovery detection
"""

import os
import time
import uuid
import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
OPS_NAMESPACE = os.environ.get("OPS_NAMESPACE", "m5-demo/Operational")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    """Circuit breaker for agent fault isolation."""

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"  # CLOSED (healthy), OPEN (tripped), HALF_OPEN (testing)
        self.last_failure_time = None

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return False

    def status(self) -> str:
        icons = {"CLOSED": "🟢", "OPEN": "🔴", "HALF_OPEN": "🟡"}
        return f"{icons.get(self.state, '❓')} {self.name}: {self.state} (failures: {self.failure_count})"


# =============================================================================
# SPECIALIST AGENTS WITH FAULT INJECTION
# =============================================================================

# Fault injection flags
_faults = {
    "billing": False,
    "tech": False,
    "product": False,
    "shipping": False,
}

# Circuit breakers per specialist
_breakers = {
    "billing": CircuitBreaker("billing"),
    "tech": CircuitBreaker("tech"),
    "product": CircuitBreaker("product"),
    "shipping": CircuitBreaker("shipping"),
}


def create_specialist(name: str, prompt: str) -> Agent:
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=prompt,
    )


billing_agent = create_specialist("billing", "You are a billing specialist. Handle refunds and payment questions concisely.")
tech_agent = create_specialist("tech", "You are a tech support specialist. Handle device and firmware issues. TechMart Hub v2.1.x has Wi-Fi bug, update to v3.0.1.")
product_agent = create_specialist("product", "You are a product specialist. TechMart Pro 15 $799 (i7, 16GB), Air $599 (i5, 8GB), Titan $1299 (RTX 4060), Hub $149.")
shipping_agent = create_specialist("shipping", "You are a shipping specialist. Standard 5-7 days, Express 2 days ($12.99), Same-day $24.99.")

# Fallback agent handles anything when specialists are down
fallback_agent = create_specialist("fallback",
    """You are a GENERAL customer service fallback agent. One or more specialist agents are currently unavailable.
Provide the best answer you can, but note that you're operating in degraded mode.
Prefix your response with: ⚠️ [DEGRADED MODE - Specialist unavailable]"""
)


def call_specialist(name: str, agent: Agent, query: str) -> str:
    """Call a specialist with circuit breaker protection."""
    breaker = _breakers[name]

    # Check circuit breaker
    if not breaker.can_execute():
        print(f"    🔴 [{name}] Circuit breaker OPEN — routing to fallback")
        return str(fallback_agent(f"[Fallback for {name}]: {query}"))

    # Check fault injection
    if _faults.get(name, False):
        breaker.record_failure()
        error_msg = f"⚠️ [{name}] SIMULATED FAILURE (fault injected)"
        print(f"    ❌ {error_msg}")

        # If breaker just tripped, use fallback
        if breaker.state == "OPEN":
            print(f"    🔴 [{name}] Circuit breaker TRIPPED — switching to fallback")
            return str(fallback_agent(f"[Fallback for {name}]: {query}"))
        return error_msg

    # Normal execution
    try:
        response = agent(query)
        breaker.record_success()
        return str(response)
    except Exception as e:
        breaker.record_failure()
        print(f"    ❌ [{name}] Error: {e}")
        if breaker.state == "OPEN":
            print(f"    🔴 [{name}] Circuit breaker TRIPPED")
            return str(fallback_agent(f"[Fallback for {name}]: {query}"))
        return f"Error from {name}: {e}"


# =============================================================================
# ORCHESTRATOR TOOLS
# =============================================================================

@tool
def ask_billing(query: str) -> str:
    """Route to billing specialist (with circuit breaker).

    Args:
        query: Billing query
    """
    return call_specialist("billing", billing_agent, query)


@tool
def ask_tech_support(query: str) -> str:
    """Route to tech support specialist (with circuit breaker).

    Args:
        query: Tech support query
    """
    return call_specialist("tech", tech_agent, query)


@tool
def ask_product_specialist(query: str) -> str:
    """Route to product specialist (with circuit breaker).

    Args:
        query: Product query
    """
    return call_specialist("product", product_agent, query)


@tool
def ask_shipping(query: str) -> str:
    """Route to shipping specialist (with circuit breaker).

    Args:
        query: Shipping query
    """
    return call_specialist("shipping", shipping_agent, query)


# =============================================================================
# DEMO
# =============================================================================

def create_orchestrator() -> Agent:
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are the TechMart orchestrator. Route queries to specialists.
If a specialist reports a failure or degraded mode, let the customer know
the system is experiencing partial issues but still serving them.""",
        tools=[ask_billing, ask_tech_support, ask_product_specialist, ask_shipping],
    )


def run_demo():
    print("=" * 70)
    print("PART 4: Reliability — Fault Tolerance & Graceful Degradation")
    print("=" * 70)
    print()
    print("  Specialists have independent circuit breakers.")
    print("  When one fails, the system degrades gracefully to a fallback.")
    print()
    print("  Commands:")
    print("    'break <agent>'  — inject fault (billing/tech/product/shipping)")
    print("    'fix <agent>'    — remove fault")
    print("    'status'         — show circuit breaker states")
    print("    'quit'           — end")
    print()
    print("  Try: break billing, then ask a billing question.")
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

        # Command: break <agent>
        if user_input.lower().startswith("break "):
            agent_name = user_input.split(" ", 1)[1].strip().lower()
            if agent_name in _faults:
                _faults[agent_name] = True
                print(f"    💥 Fault injected into [{agent_name}] — next calls will fail")
            else:
                print(f"    Unknown agent. Use: billing, tech, product, shipping")
            continue

        # Command: fix <agent>
        if user_input.lower().startswith("fix "):
            agent_name = user_input.split(" ", 1)[1].strip().lower()
            if agent_name in _faults:
                _faults[agent_name] = False
                _breakers[agent_name].failure_count = 0
                _breakers[agent_name].state = "CLOSED"
                print(f"    ✅ [{agent_name}] fault removed, circuit breaker reset")
            else:
                print(f"    Unknown agent.")
            continue

        # Command: status
        if user_input.lower() == "status":
            print(f"\n  🛡️  CIRCUIT BREAKER STATUS")
            print(f"  {'─' * 50}")
            for name, breaker in _breakers.items():
                fault = "💥 FAULT ACTIVE" if _faults.get(name) else ""
                print(f"    {breaker.status()} {fault}")
            continue

        # Normal query — route through orchestrator
        print()
        response = orchestrator(user_input)
        print(f"\n  Agent: {response}")

    # Final status
    print(f"\n{'═' * 70}")
    print(f"  FINAL CIRCUIT BREAKER STATUS")
    print(f"{'═' * 70}\n")
    for name, breaker in _breakers.items():
        print(f"  {breaker.status()}")
    print()
    print("  Key Reliability Patterns Demonstrated:")
    print("  ✅ Fault isolation: broken billing doesn't affect product queries")
    print("  ✅ Circuit breaker: prevents cascading failures")
    print("  ✅ Graceful degradation: fallback agent keeps system running")
    print("  ✅ Recovery: fix command resets breaker (auto-recovery via timeout)")
    print()


if __name__ == "__main__":
    run_demo()
