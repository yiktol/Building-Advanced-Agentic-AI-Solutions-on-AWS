"""Generate per-part architecture diagrams for Module 3."""

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom
from diagrams.aws.ml import Bedrock
from diagrams.aws.database import Dynamodb
from diagrams.aws.security import Cognito, IAMPermissions
from diagrams.aws.network import VPC, Privatelink
from diagrams.aws.management import Cloudwatch

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
    with Diagram("Part 1 — Unprotected Agent", filename="part1_unprotected", **COMMON):
        user = Custom("User", USER)
        agent = Custom("Agent", ROBOT)
        db = Dynamodb("DynamoDB")
        user >> Edge(label="no auth!", color="#DC2626", style="bold") >> agent
        agent >> Edge(label="unrestricted", color="#DC2626", style="bold") >> db
    print("  ✓ part1_unprotected.png")


def part2():
    with Diagram("Part 2 — Cedar Policy Authorization", filename="part2_cedar_policies", **COMMON):
        user = Custom("User", USER)
        avp = IAMPermissions("Verified\nPermissions")
        agent = Custom("Agent", ROBOT)
        db = Dynamodb("DynamoDB")
        user >> Edge(label="request", color="#232F3E", style="bold") >> avp
        avp >> Edge(label="ALLOW / DENY", color="#059669", style="bold") >> agent
        agent >> Edge(color="#0073BB", style="bold") >> db
    print("  ✓ part2_cedar_policies.png")


def part3():
    with Diagram("Part 3 — Cognito + JWT + Cedar", filename="part3_cognito", **COMMON):
        user = Custom("User", USER)
        cognito = Cognito("Amazon\nCognito")
        avp = IAMPermissions("Verified\nPermissions")
        agent = Custom("Agent", ROBOT)
        db = Dynamodb("DynamoDB")
        user >> Edge(label="login", color="#DD6B20", style="bold") >> cognito
        cognito >> Edge(label="JWT claims", color="#059669", style="bold") >> avp
        avp >> Edge(label="authorized", color="#059669", style="bold") >> agent
        agent >> Edge(color="#0073BB", style="bold") >> db
    print("  ✓ part3_cognito.png")


def part4():
    with Diagram("Part 4 — VPC Private Access", filename="part4_vpc", **COMMON):
        with Cluster("Private VPC", graph_attr={"bgcolor": "#f0f8ff", "style": "rounded"}):
            agent = Custom("Agent", ROBOT)
            endpoint = Privatelink("PrivateLink")
        bedrock = Bedrock("Amazon\nBedrock")
        agent >> Edge(label="private", color="#0073BB", style="bold") >> endpoint
        endpoint >> Edge(label="no internet", color="#059669", style="bold") >> bedrock
    print("  ✓ part4_vpc.png")


def part5():
    with Diagram("Part 5 — Audit Trail", filename="part5_audit", **COMMON):
        agent = Custom("Agent", ROBOT)
        db = Dynamodb("DynamoDB")
        logs = Cloudwatch("CloudWatch\nLogs")
        agent >> Edge(label="actions", color="#0073BB", style="bold") >> db
        agent >> Edge(label="audit log", color="#7C3AED", style="dashed") >> logs
    print("  ✓ part5_audit.png")


if __name__ == "__main__":
    print("Module 3: Security & Compliance")
    part1()
    part2()
    part3()
    part4()
    part5()
    print("Done!")
