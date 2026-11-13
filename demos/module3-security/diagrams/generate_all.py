"""Generate per-part architecture diagrams for Module 3 (shared style: demos/diagram_style.py)."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from diagrams import Diagram, Cluster  # noqa: E402
from diagram_style import (  # noqa: E402
    COMMON, NAVY, BLUE, GREEN, RED, ORANGE, PURPLE,
    BEDROCK, COGNITO, VERIFIED_PERMISSIONS, DYNAMODB, PRIVATELINK, CLOUDWATCH,
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
    with Diagram(filename="part2_cedar_policies", **COMMON):
        person = user("User")
        avp = aws("Verified\nPermissions", VERIFIED_PERMISSIONS)
        bot = agent("Agent")
        db = aws("DynamoDB", DYNAMODB)
        person >> flow(NAVY, "request") >> avp
        avp >> flow(GREEN, "ALLOW / DENY") >> bot
        bot >> flow(BLUE) >> db
    print("  ✓ part2_cedar_policies.png")


def part3():
    with Diagram(filename="part3_cognito", **COMMON):
        person = user("User")
        cognito = aws("Amazon\nCognito", COGNITO)
        avp = aws("Verified\nPermissions", VERIFIED_PERMISSIONS)
        bot = agent("Agent")
        db = aws("DynamoDB", DYNAMODB)
        person >> flow(ORANGE, "login") >> cognito
        cognito >> flow(GREEN, "JWT claims") >> avp
        avp >> flow(GREEN, "authorized") >> bot
        bot >> flow(BLUE) >> db
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
