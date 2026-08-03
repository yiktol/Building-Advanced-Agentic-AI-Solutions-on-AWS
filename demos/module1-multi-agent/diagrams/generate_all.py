"""Generate per-part architecture diagrams for Module 1 using diagrams library built-in AWS icons."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock

ICONS = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/aws-icons/custom"
USER = f"{ICONS}/user.png"
ROBOT = f"{ICONS}/robot.png"
TOOL = f"{ICONS}/tool.png"

COMMON = {
    "show": False,
    "direction": "LR",
    "outformat": "png",
    "graph_attr": {"pad": "0.8", "nodesep": "0.8", "ranksep": "1.5", "bgcolor": "white", "dpi": "150"},
    "node_attr": {"fontsize": "13", "fontname": "Helvetica Bold"},
    "edge_attr": {"fontsize": "11", "fontname": "Helvetica", "penwidth": "2.0"},
}


def part1():
    with Diagram("Part 1 — Single Agent (Overloaded)", filename="part1_single_agent", **COMMON):
        user = Custom("Customer", USER)
        agent = Custom("Single Agent", ROBOT)
        user >> Edge(label="billing + tech +\nproduct queries", color="#DC2626", style="bold") >> agent
    print("  ✓ part1_single_agent.png")


def part2():
    with Diagram("Part 2 — Orchestrator Pattern", filename="part2_orchestrator", **COMMON):
        user = Custom("Customer", USER)
        orch = Custom("Orchestrator", ROBOT)
        with Cluster("Specialist Agents", graph_attr={"bgcolor": "#f0f8ff", "style": "rounded"}):
            billing = Custom("Billing", ROBOT)
            tech = Custom("Tech Support", ROBOT)
            product = Custom("Product", ROBOT)
        user >> Edge(color="#232F3E", style="bold") >> orch
        orch >> Edge(label="route", color="#0073BB", style="bold") >> billing
        orch >> Edge(color="#0073BB", style="bold") >> tech
        orch >> Edge(color="#0073BB", style="bold") >> product
    print("  ✓ part2_orchestrator.png")


def part3():
    with Diagram("Part 3 — Agent-as-Tool (MCP)", filename="part3_agent_as_tool", **COMMON):
        with Cluster("Consumer Agents", graph_attr={"bgcolor": "#f0f8ff", "style": "rounded"}):
            sales = Custom("Sales Agent", ROBOT)
            support = Custom("Support Agent", ROBOT)
        with Cluster("Shared Tools (MCP)", graph_attr={"bgcolor": "#fff8f0", "style": "rounded"}):
            lookup = Custom("product_lookup", TOOL)
            compat = Custom("compatibility_check", TOOL)
            order = Custom("order_status", TOOL)
        sales >> Edge(color="#DD6B20", style="bold") >> lookup
        sales >> Edge(color="#DD6B20", style="bold") >> compat
        support >> Edge(color="#DD6B20", style="bold") >> lookup
        support >> Edge(color="#DD6B20", style="bold") >> compat
        support >> Edge(color="#DD6B20", style="bold") >> order
    print("  ✓ part3_agent_as_tool.png")


def part4():
    with Diagram("Part 4 — Shared Memory", filename="part4_shared_memory", **COMMON):
        diag = Custom("Diagnostic", ROBOT)
        resolve = Custom("Resolution", ROBOT)
        followup = Custom("Follow-up", ROBOT)
        memory = Bedrock("AgentCore\nMemory")
        diag >> Edge(label="handoff", color="#232F3E", style="bold") >> resolve
        resolve >> Edge(label="handoff", color="#232F3E", style="bold") >> followup
        diag >> Edge(color="#7C3AED", style="dashed") >> memory
        resolve >> Edge(color="#7C3AED", style="dashed") >> memory
        followup >> Edge(color="#7C3AED", style="dashed") >> memory
    print("  ✓ part4_shared_memory.png")


if __name__ == "__main__":
    print("Module 1: Multi-Agent Architecture")
    part1()
    part2()
    part3()
    part4()
    print("Done!")
