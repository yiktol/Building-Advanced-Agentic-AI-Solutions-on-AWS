"""Generate per-part architecture diagrams for Module 2."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock

import os as _os
ICONS = _os.environ.get(
    "MLADAS_ICONS",
    _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))), "aws-icons", "custom"),
)
USER = f"{ICONS}/user.png"
ROBOT = f"{ICONS}/robot.png"
TOOL = f"{ICONS}/tool.png"

COMMON = {
    "show": False,
    "direction": "LR",
    "outformat": "png",
    # forcelabels + xlabel on edges keeps labels off the line (no overlap); dpi 300 = crisp.
    "graph_attr": {"pad": "0.8", "nodesep": "1.0", "ranksep": "3.0", "bgcolor": "white", "dpi": "300", "forcelabels": "true"},
    "node_attr": {"fontsize": "13", "fontname": "Helvetica Bold"},
    "edge_attr": {"fontsize": "11", "fontname": "Helvetica", "penwidth": "2.0", "minlen": "2"},
}


def part1():
    with Diagram("Part 1 — Context Exhaustion", filename="part1_context_exhaustion", **COMMON):
        user = Custom("Customer", USER)
        agent = Custom("Agent", ROBOT)
        user >> Edge(xlabel="growing context\n(token accumulation)", color="#DC2626", style="bold") >> agent
    print("  ✓ part1_context_exhaustion.png")


def part2():
    with Diagram("Part 2 — Prompt Caching", filename="part2_prompt_caching", **COMMON):
        cache = Bedrock("Bedrock\nPrompt Cache")
        agent = Custom("Agent", ROBOT)
        cache >> Edge(xlabel="cached prefix\n(fast)", color="#059669", style="bold") >> agent
    print("  ✓ part2_prompt_caching.png")


def part3():
    with Diagram("Part 3 — Conversation Managers", filename="part3_conversation_managers", **COMMON):
        agent = Custom("Agent", ROBOT)
        manager = Bedrock("Summarizing\nManager")
        agent >> Edge(xlabel="compress history", color="#7C3AED", style="bold") >> manager
    print("  ✓ part3_conversation_managers.png")


def part4():
    with Diagram("Part 4 — Context Isolation", filename="part4_context_isolation", **COMMON):
        researcher = Custom("Researcher", ROBOT)
        analyst = Custom("Analyst", ROBOT)
        writer = Custom("Writer", ROBOT)
        researcher >> Edge(xlabel="findings only", color="#0073BB", style="bold") >> analyst
        analyst >> Edge(xlabel="analysis only", color="#0073BB", style="bold") >> writer
    print("  ✓ part4_context_isolation.png")


def part5():
    with Diagram("Part 5 — Tool Design", filename="part5_tool_design", **COMMON):
        agent = Custom("Agent", ROBOT)
        with Cluster("Tool Responses", graph_attr={"bgcolor": "#f8f8f8", "style": "rounded"}):
            verbose = Custom("Verbose Tool\n(5000 tokens)", TOOL)
            optimized = Custom("Optimized Tool\n(500 tokens)", TOOL)
        agent >> Edge(xlabel="wasteful", color="#DC2626", style="bold") >> verbose
        agent >> Edge(xlabel="efficient", color="#059669", style="bold") >> optimized
    print("  ✓ part5_tool_design.png")


if __name__ == "__main__":
    print("Module 2: Context Engineering")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
