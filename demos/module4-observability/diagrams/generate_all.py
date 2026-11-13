"""Generate per-part architecture diagrams for Module 4 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, NAVY, BLUE, GREEN, RED, ORANGE, PURPLE,
    DYNAMODB, CLOUDWATCH, SNS, XRAY,
    group, flow, aws, agent,
)


def part1():
    with Diagram(filename="part1_tracing", **COMMON):
        bot = agent("Agent")
        xray = aws("X-Ray / ADOT", XRAY)
        cw = aws("CloudWatch", CLOUDWATCH)
        bot >> flow(ORANGE, "spans") >> xray
        xray >> flow(BLUE, "traces") >> cw
    print("  ✓ part1_tracing.png")


def part2():
    with Diagram(filename="part2_metrics", **COMMON):
        bot = agent("Agent")
        metrics = aws("CloudWatch\nMetrics", CLOUDWATCH)
        bot >> flow(BLUE, "latency, tokens,\nerrors") >> metrics
    print("  ✓ part2_metrics.png")


def part3():
    with Diagram(filename="part3_loop_detection", **COMMON):
        bot = agent("Agent")
        alarms = aws("CloudWatch\nAlarms", CLOUDWATCH)
        sns = aws("SNS Alert", SNS)
        bot >> flow(RED, "tool call spike") >> alarms
        alarms >> flow(PURPLE, "notify") >> sns
    print("  ✓ part3_loop_detection.png")


def part4():
    with Diagram(filename="part4_evaluation", **COMMON):
        bot = agent("Agent")
        judge = agent("LLM Judge")
        db = aws("Eval Results", DYNAMODB)
        metrics = aws("Quality\nMetrics", CLOUDWATCH)
        bot >> flow(PURPLE, "response") >> judge
        judge >> flow(BLUE, "scores") >> db
        judge >> flow(GREEN, "quality", dashed=True) >> metrics
    print("  ✓ part4_evaluation.png")


def part5():
    with Diagram(filename="part5_dashboard", **COMMON):
        bot = agent("Agent")
        with Cluster("Signals", graph_attr=group("gray")):
            traces = aws("Traces", XRAY)
            metrics = aws("Metrics", CLOUDWATCH)
            alarms = aws("Alarms", CLOUDWATCH)
        dashboard = aws("Dashboard", CLOUDWATCH)
        bot >> flow(PURPLE) >> traces
        bot >> flow(BLUE) >> metrics
        bot >> flow(RED) >> alarms
        traces >> flow(NAVY, dashed=True) >> dashboard
        metrics >> flow(NAVY, dashed=True) >> dashboard
        alarms >> flow(NAVY, dashed=True) >> dashboard
    print("  ✓ part5_dashboard.png")


if __name__ == "__main__":
    os.chdir(HERE)
    print("Module 4: Observability & Evaluation")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
