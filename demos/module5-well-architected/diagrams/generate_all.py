"""Generate per-part architecture diagrams for Module 5 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, NAVY, BLUE, GREEN, RED, ORANGE, PURPLE,
    BEDROCK, DYNAMODB, CLOUDWATCH, LAMBDA,
    group, flow, aws, user, agent,
)


def part1():
    with Diagram(filename="part1_ecommerce", **COMMON):
        customer = user("Customer")
        orch = agent("Orchestrator")
        with Cluster("Specialists", graph_attr=group("blue")):
            billing = agent("Billing")
            tech = agent("Tech")
            product = agent("Product")
            shipping = agent("Shipping")
        db = aws("DynamoDB", DYNAMODB)
        customer >> flow(NAVY) >> orch
        for specialist in (billing, tech, product, shipping):
            orch >> flow(BLUE) >> specialist
        billing >> flow(ORANGE, dashed=True) >> db
        product >> flow(ORANGE, dashed=True) >> db
    print("  ✓ part1_ecommerce.png")


def part2():
    with Diagram(filename="part2_wa_review", **COMMON):
        system = agent("System")
        reviewer = agent("WA Reviewer")
        db = aws("Findings", DYNAMODB)
        system >> flow(NAVY, "assess") >> reviewer
        reviewer >> flow(GREEN, "report") >> db
    print("  ✓ part2_wa_review.png")


def part3():
    with Diagram(filename="part3_ops_excellence", **COMMON):
        v1 = agent("Agent v1")
        health = aws("Health Check", CLOUDWATCH)
        v2 = agent("Agent v2")
        v1 >> flow(BLUE, "deploy") >> health
        health >> flow(GREEN, "healthy →\nactivate") >> v2
    print("  ✓ part3_ops_excellence.png")


def part4():
    with Diagram(filename="part4_reliability", **COMMON):
        orch = agent("Orchestrator")
        with Cluster("Agents", graph_attr=group("gray")):
            ok = agent("Agent OK")
            failed = agent("Agent FAILED")
        fallback = aws("Fallback", LAMBDA)
        orch >> flow(GREEN, "success") >> ok
        orch >> flow(RED, "error") >> failed
        failed >> flow(ORANGE, "failover", dashed=True) >> fallback
    print("  ✓ part4_reliability.png")


def part5():
    with Diagram(filename="part5_cost_optimization", **COMMON):
        query = user("Query")
        with Cluster("Model Tier", graph_attr=group("gray")):
            economy = aws("Economy Model", BEDROCK)
            premium = aws("Premium Model", BEDROCK)
        cost = aws("Cost Metrics", CLOUDWATCH)
        query >> flow(GREEN, "simple") >> economy
        query >> flow(PURPLE, "complex") >> premium
        economy >> flow(BLUE, dashed=True) >> cost
        premium >> flow(BLUE, dashed=True) >> cost
    print("  ✓ part5_cost_optimization.png")


if __name__ == "__main__":
    os.chdir(HERE)
    print("Module 5: Well-Architected")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
