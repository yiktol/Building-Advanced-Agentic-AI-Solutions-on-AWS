"""Generate per-part architecture diagrams for Module 2."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock

ICONS = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/aws-icons/custom"
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
    with Diagram("Part 1 — Context Exhaustion", filename="part1_context_exhaustion", **COMMON):
        user = Custom("Customer", USER)
        agent = Custom("Agent", ROBOT)
        user >> Edge(label="growing context\n(token accumulation)", color="#DC2626", style="bold") >> agent
    print("  ✓ part1_context_exhaustion.png")


def part2():
    with Diagram("Part 2 — Prompt Caching", filename="part2_prompt_caching", **COMMON):
        cache = Bedrock("Bedrock\nPrompt Cache")
        agent = Custom("Agent", ROBOT)
        cache >> Edge(label="cached prefix\n(fast)", color="#059669", style="bold") >> agent
    print("  ✓ part2_prompt_caching.png")


def part3():
    with Diagram("Part 3 — Conversation Managers", filename="part3_conversation_managers", **COMMON):
        agent = Custom("Agent", ROBOT)
        manager = Bedrock("Summarizing\nManager")
        agent >> Edge(label="compress history", color="#7C3AED", style="bold") >> manager
    print("  ✓ part3_conversation_managers.png")


def part4():
    with Diagram("Part 4 — Context Isolation", filename="part4_context_isolation", **COMMON):
        researcher = Custom("Researcher", ROBOT)
        analyst = Custom("Analyst", ROBOT)
        writer = Custom("Writer", ROBOT)
        researcher >> Edge(label="findings only", color="#0073BB", style="bold") >> analyst
        analyst >> Edge(label="analysis only", color="#0073BB", style="bold") >> writer
    print("  ✓ part4_context_isolation.png")


def part5():
    with Diagram("Part 5 — Tool Design", filename="part5_tool_design", **COMMON):
        agent = Custom("Agent", ROBOT)
        with Cluster("Tool Responses", graph_attr={"bgcolor": "#f8f8f8", "style": "rounded"}):
            verbose = Custom("Verbose Tool\n(5000 tokens)", TOOL)
            optimized = Custom("Optimized Tool\n(500 tokens)", TOOL)
        agent >> Edge(label="wasteful", color="#DC2626", style="bold") >> verbose
        agent >> Edge(label="efficient", color="#059669", style="bold") >> optimized
    print("  ✓ part5_tool_design.png")


if __name__ == "__main__":
    print("Module 2: Context Engineering")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
