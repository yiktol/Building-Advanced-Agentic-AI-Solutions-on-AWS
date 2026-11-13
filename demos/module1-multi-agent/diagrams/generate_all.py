"""Generate per-part architecture diagrams for Module 1 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, NAVY, BLUE, RED, ORANGE, PURPLE, AGENTCORE,
    group, flow, aws, user, agent, tool,
)


def part1():
    with Diagram(filename="part1_single_agent", **COMMON):
        customer = user("Customer")
        with Cluster("One shared context window", graph_attr=group("orange")):
            single = agent("Single Agent")
            billing = tool("Billing rules")
            tech = tool("Tech procedures")
            product = tool("Product catalog")
        customer >> flow(RED, "billing + tech +\nproduct queries") >> single
        for domain in (billing, tech, product):
            single >> flow(ORANGE, dashed=True) >> domain
    print("  ✓ part1_single_agent.png")


def part2():
    with Diagram(filename="part2_orchestrator", **COMMON):
        customer = user("Customer")
        orch = agent("Orchestrator")
        with Cluster("Specialist Agents", graph_attr=group("blue")):
            billing = agent("Billing")
            tech = agent("Tech Support")
            product = agent("Product")
        customer >> flow(NAVY, "query") >> orch
        orch >> flow(BLUE, "route") >> billing
        orch >> flow(BLUE) >> tech
        orch >> flow(BLUE) >> product
    print("  ✓ part2_orchestrator.png")


def part3():
    with Diagram(filename="part3_agent_as_tool", **COMMON):
        with Cluster("Consumer Agents", graph_attr=group("blue")):
            sales = agent("Sales Agent")
            support = agent("Support Agent")
        with Cluster("Shared Tools (MCP)", graph_attr=group("orange")):
            lookup = tool("product_lookup")
            compat = tool("compatibility_check")
            order = tool("order_status")
        sales >> flow(BLUE) >> lookup
        sales >> flow(BLUE) >> compat
        support >> flow(ORANGE) >> lookup
        support >> flow(ORANGE) >> compat
        support >> flow(ORANGE) >> order
    print("  ✓ part3_agent_as_tool.png")


def part4():
    with Diagram(filename="part4_shared_memory", **COMMON):
        with Cluster("Support Pipeline", graph_attr=group("blue")):
            diag = agent("Diagnostic")
            resolve = agent("Resolution")
            followup = agent("Follow-up")
        memory = aws("AgentCore\nMemory", AGENTCORE)
        diag >> flow(NAVY, "handoff") >> resolve
        resolve >> flow(NAVY, "handoff") >> followup
        diag >> flow(PURPLE, "read / write", dashed=True) >> memory
        resolve >> flow(PURPLE, dashed=True) >> memory
        followup >> flow(PURPLE, dashed=True) >> memory
    print("  ✓ part4_shared_memory.png")


if __name__ == "__main__":
    os.chdir(HERE)
    print("Module 1: Multi-Agent Architecture")
    part1()
    part2()
    part3()
    part4()
    print("Done!")
