"""Generate per-part architecture diagrams for Module 3 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, NAVY, BLUE, GREEN, RED, ORANGE, PURPLE,
    BEDROCK, COGNITO, AGENTCORE, LAMBDA, DYNAMODB, PRIVATELINK, CLOUDWATCH,
    group, flow, aws, user, agent,
)


def part1():
    with Diagram(filename="part1_unprotected", **COMMON):
        person = user("User")
        bot = agent("Agent")
        db = aws("DynamoDB", DYNAMODB)
        person >> flow(RED, "no auth!") >> bot
        bot >> flow(RED, "unrestricted") >> db
    print("  ✓ part1_unprotected.png")


def part2():
    # Users are signed in to Cognito behind the scenes; the Gateway validates the JWT
    # and the attached Policy Engine (Cedar) decides ALLOW / DENY before the tool runs.
    with Diagram(filename="part2_cedar_policies", **COMMON):
        person = user("User")
        bot = agent("Agent")
        with Cluster("AgentCore", graph_attr=group("purple")):
            gateway = aws("Gateway", AGENTCORE)
            engine = aws("Policy Engine\n(Cedar)", AGENTCORE)
        tool_fn = aws("Lambda\n(order-status)", LAMBDA)
        db = aws("DynamoDB", DYNAMODB)
        person >> flow(NAVY, "request") >> bot
        bot >> flow(ORANGE, "tools/call + JWT") >> gateway
        gateway >> flow(PURPLE, "authorize", dashed=True) >> engine
        gateway >> flow(GREEN, "ALLOW only") >> tool_fn
        tool_fn >> flow(BLUE) >> db
    print("  ✓ part2_cedar_policies.png")


def part3():
    # Real identity: Cognito issues the JWT; the Gateway verifies it against the Cognito user pool
    # and turns its custom:role / custom:department claims into Cedar principal tags.
    with Diagram(filename="part3_cognito", **COMMON):
        person = user("User")
        cognito = aws("Amazon\nCognito", COGNITO)
        bot = agent("Agent")
        with Cluster("AgentCore", graph_attr=group("purple")):
            gateway = aws("Gateway", AGENTCORE)
            engine = aws("Policy Engine\n(Cedar)", AGENTCORE)
        tool_fn = aws("Lambda\n(order-status)", LAMBDA)
        db = aws("DynamoDB", DYNAMODB)
        person >> flow(ORANGE, "login") >> cognito
        cognito >> flow(ORANGE, "ID token (JWT)") >> bot
        bot >> flow(NAVY, "tools/call\n+ Bearer JWT") >> gateway
        gateway >> flow(PURPLE, "verify JWT, claims\n-> tags, authorize", dashed=True) >> engine
        gateway >> flow(GREEN, "ALLOW only") >> tool_fn
        tool_fn >> flow(BLUE) >> db
    print("  ✓ part3_cognito.png")


def part4():
    with Diagram(filename="part4_vpc", **COMMON):
        with Cluster("Private VPC", graph_attr=group("blue")):
            bot = agent("Agent")
            endpoint = aws("PrivateLink", PRIVATELINK)
        bedrock = aws("Amazon\nBedrock", BEDROCK)
        bot >> flow(BLUE, "private") >> endpoint
        endpoint >> flow(GREEN, "no internet") >> bedrock
    print("  ✓ part4_vpc.png")


def part5():
    with Diagram(filename="part5_audit", **COMMON):
        bot = agent("Agent")
        db = aws("DynamoDB", DYNAMODB)
        logs = aws("CloudWatch\nLogs", CLOUDWATCH)
        bot >> flow(BLUE, "actions") >> db
        bot >> flow(PURPLE, "audit log", dashed=True) >> logs
    print("  ✓ part5_audit.png")


if __name__ == "__main__":
    os.chdir(HERE)
    print("Module 3: Security & Compliance")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
