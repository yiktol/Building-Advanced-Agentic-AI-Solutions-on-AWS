"""Generate per-part architecture diagrams for Module 5."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock
from diagrams.aws.database import Dynamodb
from diagrams.aws.management import Cloudwatch
from diagrams.aws.compute import Lambda

ICONS = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/aws-icons/custom"
USER = f"{ICONS}/user.png"
ROBOT = f"{ICONS}/robot.png"

COMMON = {
    "show": False,
    "direction": "LR",
    "outformat": "png",
    "graph_attr": {"pad": "0.8", "nodesep": "0.8", "ranksep": "1.5", "bgcolor": "white", "dpi": "150"},
    "node_attr": {"fontsize": "13", "fontname": "Helvetica Bold"},
    "edge_attr": {"fontsize": "11", "fontname": "Helvetica", "penwidth": "2.0"},
}


def part1():
    with Diagram("Part 1 — E-Commerce Multi-Agent", filename="part1_ecommerce", **COMMON):
        user = Custom("Customer", USER)
        orch = Custom("Orchestrator", ROBOT)
        with Cluster("Specialists", graph_attr={"bgcolor": "#f0f8ff", "style": "rounded"}):
            billing = Custom("Billing", ROBOT)
            tech = Custom("Tech", ROBOT)
            product = Custom("Product", ROBOT)
            shipping = Custom("Shipping", ROBOT)
        db = Dynamodb("DynamoDB")
        user >> Edge(color="#232F3E", style="bold") >> orch
        orch >> Edge(color="#0073BB", style="bold") >> billing
        orch >> Edge(color="#0073BB", style="bold") >> tech
        orch >> Edge(color="#0073BB", style="bold") >> product
        orch >> Edge(color="#0073BB", style="bold") >> shipping
        billing >> Edge(color="#DD6B20", style="dashed") >> db
        product >> Edge(color="#DD6B20", style="dashed") >> db
    print("  ✓ part1_ecommerce.png")


def part2():
    with Diagram("Part 2 — Well-Architected Review", filename="part2_wa_review", **COMMON):
        system = Custom("System", ROBOT)
        reviewer = Custom("WA Reviewer", ROBOT)
        db = Dynamodb("Findings")
        system >> Edge(label="assess", color="#232F3E", style="bold") >> reviewer
        reviewer >> Edge(label="report", color="#059669", style="bold") >> db
    print("  ✓ part2_wa_review.png")


def part3():
    with Diagram("Part 3 — Ops Excellence", filename="part3_ops_excellence", **COMMON):
        v1 = Custom("Agent v1", ROBOT)
        health = Cloudwatch("Health Check")
        v2 = Custom("Agent v2", ROBOT)
        v1 >> Edge(label="deploy", color="#0073BB", style="bold") >> health
        health >> Edge(label="healthy →\nactivate", color="#059669", style="bold") >> v2
    print("  ✓ part3_ops_excellence.png")


def part4():
    with Diagram("Part 4 — Reliability", filename="part4_reliability", **COMMON):
        orch = Custom("Orchestrator", ROBOT)
        with Cluster("Agents", graph_attr={"bgcolor": "#f8f8f8", "style": "rounded"}):
            ok = Custom("Agent OK", ROBOT)
            failed = Custom("Agent FAILED", ROBOT)
        fallback = Lambda("Fallback")
        orch >> Edge(label="success", color="#059669", style="bold") >> ok
        orch >> Edge(label="error", color="#DC2626", style="bold") >> failed
        failed >> Edge(label="failover", color="#DD6B20", style="dashed") >> fallback
    print("  ✓ part4_reliability.png")


def part5():
    with Diagram("Part 5 — Cost Optimization", filename="part5_cost_optimization", **COMMON):
        query = Custom("Query", USER)
        with Cluster("Model Tier", graph_attr={"bgcolor": "#f8f8f8", "style": "rounded"}):
            economy = Bedrock("Economy Model")
            premium = Bedrock("Premium Model")
        cost = Cloudwatch("Cost Metrics")
        query >> Edge(label="simple", color="#059669", style="bold") >> economy
        query >> Edge(label="complex", color="#7C3AED", style="bold") >> premium
        economy >> Edge(color="#0073BB", style="dashed") >> cost
        premium >> Edge(color="#0073BB", style="dashed") >> cost
    print("  ✓ part5_cost_optimization.png")


if __name__ == "__main__":
    print("Module 5: Well-Architected")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
