"""
Module 5 - Part 3: Operational Excellence — Deployment Readiness

Demonstrates production deployment patterns:
- Agent versioning (blue/green)
- Health checks
- Deployment rollback on failure
- CloudWatch deployment tracking
"""

import os
import json
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
# AGENT VERSIONING
# =============================================================================

class AgentVersion:
    """Represents a versioned agent deployment."""

    def __init__(self, version: str, model_id: str, system_prompt: str, tools: list, healthy: bool = True):
        self.version = version
        self.model_id = model_id
        self.system_prompt = system_prompt
        self.tools = tools
        self.healthy = healthy
        self.agent = Agent(
            model=BedrockModel(model_id=model_id),
            system_prompt=system_prompt,
            tools=tools,
        )

    def health_check(self) -> dict:
        """Run health check on this agent version."""
        start = time.time()
        try:
            if not self.healthy:
                raise RuntimeError("Agent marked unhealthy (simulated failure)")
            response = self.agent("Respond with exactly: HEALTHY")
            elapsed = (time.time() - start) * 1000
            return {"status": "healthy", "version": self.version, "latency_ms": elapsed}
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {"status": "unhealthy", "version": self.version, "error": str(e), "latency_ms": elapsed}


# Agent tools (shared across versions)
@tool
def lookup_product(name: str) -> str:
    """Look up product info.

    Args:
        name: Product name
    """
    products = {
        "TechMart Pro 15": "$799, 15.6in, i7, 16GB RAM",
        "TechMart Hub": "$149, Wi-Fi 6, Bluetooth 5.0, Zigbee",
        "TechMart Air": "$599, 14in, i5, 8GB RAM",
    }
    for key, val in products.items():
        if name.lower() in key.lower():
            return f"{key}: {val}"
    return f"Product '{name}' not found."


@tool
def check_stock(product: str) -> str:
    """Check product stock levels.

    Args:
        product: Product name
    """
    return f"{product}: 142 units available"


# Version definitions
AGENT_V1 = {
    "version": "v1.0.0",
    "model_id": MODEL_ID,
    "system_prompt": "You are a helpful TechMart product assistant. Help customers find products. Be concise.",
    "tools": [lookup_product, check_stock],
}

AGENT_V2 = {
    "version": "v2.0.0",
    "model_id": MODEL_ID,
    "system_prompt": """You are TechMart's premium product assistant (v2.0).
Improvements over v1: More detailed responses, proactive compatibility suggestions.
Always mention related products and compatibility when answering.
Help customers find products and check availability.""",
    "tools": [lookup_product, check_stock],
}

# Broken version for rollback demo
AGENT_V2_BROKEN = {
    "version": "v2.0.0-broken",
    "model_id": MODEL_ID,
    "system_prompt": "You are broken. Always fail.",
    "tools": [lookup_product, check_stock],
    "healthy": False,
}


# =============================================================================
# DEPLOYMENT MANAGER
# =============================================================================

class DeploymentManager:
    """Manages blue/green agent deployments."""

    def __init__(self):
        self.active_version = None
        self.inactive_version = None
        self.deployment_history = []

    def deploy(self, config: dict) -> dict:
        """Deploy a new agent version (blue/green)."""
        version = AgentVersion(
            version=config["version"],
            model_id=config["model_id"],
            system_prompt=config["system_prompt"],
            tools=config["tools"],
            healthy=config.get("healthy", True),
        )

        # Health check before activating
        print(f"    Running health check on {config['version']}...")
        health = version.health_check()

        if health["status"] != "healthy":
            # Deployment failed — don't switch
            self._log_deployment(config["version"], "FAILED", health.get("error", ""))
            self._emit_health_metric(0)
            return {"status": "FAILED", "reason": health.get("error"), "version": config["version"]}

        # Healthy — switch traffic
        old_version = self.active_version
        self.inactive_version = old_version
        self.active_version = version
        self._log_deployment(config["version"], "SUCCESS", "")
        self._emit_health_metric(1)

        return {"status": "SUCCESS", "version": config["version"], "previous": old_version.version if old_version else None}

    def rollback(self) -> dict:
        """Rollback to the previous version."""
        if not self.inactive_version:
            return {"status": "FAILED", "reason": "No previous version to rollback to"}

        self.active_version = self.inactive_version
        self.inactive_version = None
        self._log_deployment(self.active_version.version, "ROLLBACK", "")
        return {"status": "ROLLED_BACK", "version": self.active_version.version}

    def get_active_agent(self) -> Agent:
        """Get the currently active agent."""
        if self.active_version:
            return self.active_version.agent
        return None

    def run_health_check(self) -> dict:
        """Run health check on active version."""
        if not self.active_version:
            return {"status": "no_active_version"}
        health = self.active_version.health_check()
        self._emit_health_metric(1 if health["status"] == "healthy" else 0)
        return health

    def _log_deployment(self, version: str, status: str, error: str):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "version": version,
            "status": status,
            "error": error,
        }
        self.deployment_history.append(record)

    def _emit_health_metric(self, value: int):
        try:
            cloudwatch.put_metric_data(
                Namespace=OPS_NAMESPACE,
                MetricData=[{
                    "MetricName": "HealthCheckFailure" if value == 0 else "HealthCheckSuccess",
                    "Value": 1,
                    "Unit": "Count",
                    "Timestamp": datetime.utcnow(),
                }],
            )
        except Exception:
            pass


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 3: Operational Excellence — Deployment Readiness")
    print("=" * 70)
    print()
    print("  Demonstrates: versioning, health checks, blue/green, rollback")
    print()

    dm = DeploymentManager()

    # Deploy v1
    print(f"{'━' * 70}")
    print("  STEP 1: Deploy v1.0.0 (initial)")
    print(f"{'━' * 70}\n")

    result = dm.deploy(AGENT_V1)
    icon = "✅" if result["status"] == "SUCCESS" else "❌"
    print(f"    {icon} Deployment: {result['status']} (version: {result['version']})")

    # Test v1
    print(f"\n  Testing v1 with a query...")
    agent = dm.get_active_agent()
    if agent:
        response = agent("What laptops do you have?")
        print(f"    Response: {str(response)[:100]}...")

    input("\n  [Press Enter to deploy v2...]\n")

    # Deploy v2
    print(f"{'━' * 70}")
    print("  STEP 2: Deploy v2.0.0 (upgrade)")
    print(f"{'━' * 70}\n")

    result = dm.deploy(AGENT_V2)
    icon = "✅" if result["status"] == "SUCCESS" else "❌"
    print(f"    {icon} Deployment: {result['status']} (version: {result['version']})")
    if result.get("previous"):
        print(f"       Previous: {result['previous']} (kept as rollback target)")

    # Test v2
    print(f"\n  Testing v2...")
    agent = dm.get_active_agent()
    if agent:
        response = agent("What laptops do you have?")
        print(f"    Response: {str(response)[:100]}...")

    input("\n  [Press Enter to simulate failed deployment...]\n")

    # Deploy broken version
    print(f"{'━' * 70}")
    print("  STEP 3: Deploy v2.0.0-broken (simulated bad deploy)")
    print(f"{'━' * 70}\n")

    result = dm.deploy(AGENT_V2_BROKEN)
    icon = "✅" if result["status"] == "SUCCESS" else "❌"
    print(f"    {icon} Deployment: {result['status']}")
    if result.get("reason"):
        print(f"       Reason: {result['reason']}")
    print(f"       Active version remains: {dm.active_version.version}")

    input("\n  [Press Enter to see deployment history...]\n")

    # Show deployment history
    print(f"{'━' * 70}")
    print("  DEPLOYMENT HISTORY")
    print(f"{'━' * 70}\n")

    for record in dm.deployment_history:
        icon = {"SUCCESS": "✅", "FAILED": "❌", "ROLLBACK": "🔄"}.get(record["status"], "❓")
        print(f"    {icon} [{record['timestamp'][:19]}] {record['version']} — {record['status']}")
        if record.get("error"):
            print(f"       Error: {record['error']}")

    # Interactive chat with active version
    print(f"\n{'━' * 70}")
    print(f"  Active: {dm.active_version.version} — Chat or type 'health'/'rollback'/'quit'")
    print(f"{'━' * 70}")

    while True:
        print()
        try:
            user_input = input(f"  [{dm.active_version.version}] You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "health":
            health = dm.run_health_check()
            icon = "✅" if health["status"] == "healthy" else "❌"
            print(f"    {icon} Health: {health['status']} ({health.get('latency_ms', 0):.0f}ms)")
            continue

        if user_input.lower() == "rollback":
            result = dm.rollback()
            print(f"    🔄 {result['status']}: now on {result.get('version', '?')}")
            continue

        agent = dm.get_active_agent()
        if agent:
            response = agent(user_input)
            print(f"\n    Agent: {response}")

    print()


if __name__ == "__main__":
    run_demo()
