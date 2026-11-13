"""Generate per-part architecture diagrams for Module 2 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, BLUE, GREEN, RED, PURPLE, BEDROCK,
    group, flow, aws, user, agent, tool,
)


def part1():
    with Diagram(filename="part1_context_exhaustion", **COMMON):
        customer = user("Customer")
        bot = agent("Agent")
        customer >> flow(RED, "growing context\n(token accumulation)") >> bot
    print("  ✓ part1_context_exhaustion.png")


def part2():
    with Diagram(filename="part2_prompt_caching", **COMMON):
        cache = aws("Bedrock\nPrompt Cache", BEDROCK)
        bot = agent("Agent")
        cache >> flow(GREEN, "cached prefix\n(fast)") >> bot
    print("  ✓ part2_prompt_caching.png")


def part3():
    with Diagram(filename="part3_conversation_managers", **COMMON):
        bot = agent("Agent")
        manager = aws("Summarizing\nManager", BEDROCK)
        bot >> flow(PURPLE, "compress history") >> manager
    print("  ✓ part3_conversation_managers.png")


def part4():
    with Diagram(filename="part4_context_isolation", **COMMON):
        researcher = agent("Researcher")
        analyst = agent("Analyst")
        writer = agent("Writer")
        researcher >> flow(BLUE, "findings only") >> analyst
        analyst >> flow(BLUE, "analysis only") >> writer
    print("  ✓ part4_context_isolation.png")


def part5():
    with Diagram(filename="part5_tool_design", **COMMON):
        bot = agent("Agent")
        with Cluster("Tool Responses", graph_attr=group("gray")):
            verbose = tool("Verbose Tool\n(5000 tokens)")
            optimized = tool("Optimized Tool\n(500 tokens)")
        bot >> flow(RED, "wasteful") >> verbose
        bot >> flow(GREEN, "efficient") >> optimized
    print("  ✓ part5_tool_design.png")


if __name__ == "__main__":
    os.chdir(HERE)
    print("Module 2: Context Engineering")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
