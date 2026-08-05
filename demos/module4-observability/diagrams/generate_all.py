"""Generate per-part architecture diagrams for Module 4."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock
from diagrams.aws.database import Dynamodb
from diagrams.aws.management import Cloudwatch
from diagrams.aws.integration import SNS
from diagrams.aws.devtools import XRay

ICONS = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/aws-icons/custom"
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
    with Diagram("Part 1 — Distributed Tracing", filename="part1_tracing", **COMMON):
        agent = Custom("Agent", ROBOT)
        xray = XRay("X-Ray / ADOT")
        cw = Cloudwatch("CloudWatch")
        agent >> Edge(label="spans", color="#DD6B20", style="bold") >> xray
        xray >> Edge(label="traces", color="#0073BB", style="bold") >> cw
    print("  ✓ part1_tracing.png")


def part2():
    with Diagram("Part 2 — CloudWatch Metrics", filename="part2_metrics", **COMMON):
        agent = Custom("Agent", ROBOT)
        metrics = Cloudwatch("CloudWatch\nMetrics")
        agent >> Edge(label="latency, tokens,\nerrors", color="#0073BB", style="bold") >> metrics
    print("  ✓ part2_metrics.png")


def part3():
    with Diagram("Part 3 — Loop Detection", filename="part3_loop_detection", **COMMON):
        agent = Custom("Agent", ROBOT)
        alarms = Cloudwatch("CloudWatch\nAlarms")
        sns = SNS("SNS Alert")
        agent >> Edge(label="tool call spike", color="#DC2626", style="bold") >> alarms
        alarms >> Edge(label="notify", color="#7C3AED", style="bold") >> sns
    print("  ✓ part3_loop_detection.png")


def part4():
    with Diagram("Part 4 — Agent Evaluation", filename="part4_evaluation", **COMMON):
        agent = Custom("Agent", ROBOT)
        judge = Custom("LLM Judge", ROBOT)
        db = Dynamodb("Eval Results")
        metrics = Cloudwatch("Quality\nMetrics")
        agent >> Edge(label="response", color="#7C3AED", style="bold") >> judge
        judge >> Edge(label="scores", color="#0073BB", style="bold") >> db
        judge >> Edge(label="quality", color="#059669", style="dashed") >> metrics
    print("  ✓ part4_evaluation.png")


def part5():
    with Diagram("Part 5 — Unified Dashboard", filename="part5_dashboard", **COMMON):
        agent = Custom("Agent", ROBOT)
        with Cluster("Signals", graph_attr={"bgcolor": "#f8f8f8", "style": "rounded"}):
            traces = XRay("Traces")
            metrics = Cloudwatch("Metrics")
            alarms = Cloudwatch("Alarms")
        dashboard = Cloudwatch("Dashboard")
        agent >> Edge(color="#7C3AED", style="bold") >> traces
        agent >> Edge(color="#0073BB", style="bold") >> metrics
        agent >> Edge(color="#DC2626", style="bold") >> alarms
        traces >> Edge(color="#232F3E", style="dashed") >> dashboard
        metrics >> Edge(color="#232F3E", style="dashed") >> dashboard
        alarms >> Edge(color="#232F3E", style="dashed") >> dashboard
    print("  ✓ part5_dashboard.png")


if __name__ == "__main__":
    print("Module 4: Observability & Evaluation")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
