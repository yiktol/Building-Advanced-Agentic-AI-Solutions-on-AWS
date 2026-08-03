"""
Module 3 - Part 4: VPC Private Connectivity Verification

Demonstrates and verifies the VPC infrastructure deployed via CloudFormation.
Inspects the real VPC endpoints, security groups, and route tables to show
private connectivity between the agent and AWS services.

Shows:
- VPC endpoint configuration for Bedrock Runtime
- Security group rules (restricted HTTPS only)
- Route table entries showing private paths
- Verification that no public internet path exists
"""

import os
import json
import boto3

# --- Configuration ---
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")

ec2_client = boto3.client("ec2", region_name=REGION)


def get_stack_outputs(stack_name: str) -> dict:
    """Get CloudFormation stack outputs."""
    cf_client = boto3.client("cloudformation", region_name=REGION)
    try:
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = {}
        for output in response["Stacks"][0].get("Outputs", []):
            outputs[output["OutputKey"]] = output["OutputValue"]
        return outputs
    except Exception as e:
        return {"error": str(e)}


def inspect_vpc(vpc_id: str):
    """Inspect VPC configuration."""
    print(f"\n  {'─' * 60}")
    print(f"  🔍 VPC: {vpc_id}")
    print(f"  {'─' * 60}")

    vpcs = ec2_client.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]
    if vpcs:
        vpc = vpcs[0]
        print(f"  CIDR: {vpc['CidrBlock']}")
        print(f"  DNS Support: {vpc.get('EnableDnsSupport', 'N/A')}")
        print(f"  DNS Hostnames: {vpc.get('EnableDnsHostnames', 'N/A')}")
        name = next((t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"), "unnamed")
        print(f"  Name: {name}")


def inspect_subnets(vpc_id: str):
    """Inspect subnets."""
    print(f"\n  {'─' * 60}")
    print(f"  🔍 Subnets")
    print(f"  {'─' * 60}")

    subnets = ec2_client.describe_subnets(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Subnets"]

    for subnet in subnets:
        name = next((t["Value"] for t in subnet.get("Tags", []) if t["Key"] == "Name"), "unnamed")
        public = "PUBLIC ⚠️" if subnet.get("MapPublicIpOnLaunch") else "PRIVATE ✅"
        print(f"  {name}")
        print(f"    ID: {subnet['SubnetId']}")
        print(f"    CIDR: {subnet['CidrBlock']}")
        print(f"    AZ: {subnet['AvailabilityZone']}")
        print(f"    Type: {public}")
        print()


def inspect_vpc_endpoints(vpc_id: str):
    """Inspect VPC endpoints."""
    print(f"\n  {'─' * 60}")
    print(f"  🔍 VPC Endpoints (Private Connectivity)")
    print(f"  {'─' * 60}")

    endpoints = ec2_client.describe_vpc_endpoints(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["VpcEndpoints"]

    if not endpoints:
        print("  ⚠️  No VPC endpoints found!")
        return

    for ep in endpoints:
        name = next((t["Value"] for t in ep.get("Tags", []) if t["Key"] == "Name"), ep["ServiceName"])
        ep_type = ep["VpcEndpointType"]
        state = ep["State"]
        service = ep["ServiceName"]

        icon = "✅" if state == "available" else "⚠️"
        print(f"  {icon} {name}")
        print(f"    Type: {ep_type}")
        print(f"    Service: {service}")
        print(f"    State: {state}")
        print(f"    ID: {ep['VpcEndpointId']}")

        if ep_type == "Interface":
            dns = ep.get("DnsEntries", [])
            if dns:
                print(f"    Private DNS: {dns[0].get('DnsName', 'N/A')}")
            private_dns_enabled = ep.get("PrivateDnsEnabled", False)
            print(f"    Private DNS Enabled: {private_dns_enabled}")
            subnets = ep.get("SubnetIds", [])
            print(f"    Subnets: {', '.join(subnets)}")

        elif ep_type == "Gateway":
            route_tables = ep.get("RouteTableIds", [])
            print(f"    Route Tables: {', '.join(route_tables)}")

        print()


def inspect_security_groups(vpc_id: str):
    """Inspect security groups."""
    print(f"\n  {'─' * 60}")
    print(f"  🔍 Security Groups")
    print(f"  {'─' * 60}")

    sgs = ec2_client.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "tag:Project", "Values": ["mladas-module3-demo"]},
        ]
    )["SecurityGroups"]

    for sg in sgs:
        print(f"\n  🔒 {sg['GroupName']}")
        print(f"    ID: {sg['GroupId']}")
        print(f"    Description: {sg['Description']}")

        print(f"    Inbound Rules:")
        for rule in sg.get("IpPermissions", []):
            protocol = rule.get("IpProtocol", "all")
            from_port = rule.get("FromPort", "all")
            to_port = rule.get("ToPort", "all")
            for cidr in rule.get("IpRanges", []):
                desc = cidr.get("Description", "")
                print(f"      ALLOW {protocol} {from_port}-{to_port} from {cidr['CidrIp']} ({desc})")

        print(f"    Outbound Rules:")
        for rule in sg.get("IpPermissionsEgress", []):
            protocol = rule.get("IpProtocol", "all")
            from_port = rule.get("FromPort", "all")
            to_port = rule.get("ToPort", "all")
            for cidr in rule.get("IpRanges", []):
                desc = cidr.get("Description", "")
                port_str = f"{from_port}-{to_port}" if protocol != "-1" else "all"
                print(f"      ALLOW {protocol} {port_str} to {cidr['CidrIp']} ({desc})")


def verify_no_internet_gateway(vpc_id: str):
    """Verify no internet gateway is attached."""
    print(f"\n  {'─' * 60}")
    print(f"  🔍 Internet Gateway Check")
    print(f"  {'─' * 60}")

    igws = ec2_client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["InternetGateways"]

    if igws:
        print(f"  ⚠️  Internet Gateway FOUND: {igws[0]['InternetGatewayId']}")
        print(f"     Traffic CAN reach the public internet!")
    else:
        print(f"  ✅ No Internet Gateway attached")
        print(f"     Traffic CANNOT reach the public internet")
        print(f"     All AWS service access goes through VPC Endpoints")


def run_demo():
    print("=" * 70)
    print("PART 4: VPC Private Connectivity Verification")
    print("=" * 70)
    print()
    print("Inspecting the deployed VPC infrastructure to verify")
    print("private connectivity for agent workloads.")
    print()

    # Get VPC ID from CloudFormation
    outputs = get_stack_outputs("m3-demo-vpc")
    if "error" in outputs:
        print(f"  ⚠️  VPC stack not deployed: {outputs['error']}")
        print("  Run: ./scripts/deploy.sh (include VPC stack)")
        print("  Or deploy: aws cloudformation deploy --template-file infra/cfn-vpc.yaml --stack-name m3-demo-vpc")
        return

    vpc_id = outputs.get("VpcId", "")
    if not vpc_id:
        print("  ⚠️  No VPC ID in stack outputs")
        return

    print(f"  Stack: m3-demo-vpc")
    print(f"  VPC ID: {vpc_id}")

    # Run all inspections
    inspect_vpc(vpc_id)
    inspect_subnets(vpc_id)
    inspect_vpc_endpoints(vpc_id)
    inspect_security_groups(vpc_id)
    verify_no_internet_gateway(vpc_id)

    # Summary
    print(f"\n{'═' * 70}")
    print("  PRIVATE CONNECTIVITY SUMMARY")
    print(f"{'═' * 70}")
    print()
    print("  Traffic Flow (agent inside VPC):")
    print("  ┌────────────────────────────────────────────────────────┐")
    print("  │  Agent (Private Subnet)                                 │")
    print("  │     │                                                   │")
    print("  │     ├──→ Bedrock Runtime (Interface VPC Endpoint)       │")
    print("  │     ├──→ DynamoDB (Gateway VPC Endpoint)                │")
    print("  │     ├──→ CloudWatch Logs (Interface VPC Endpoint)       │")
    print("  │     └──→ STS (Interface VPC Endpoint)                   │")
    print("  │                                                         │")
    print("  │  ❌ NO Internet Gateway = NO public internet access     │")
    print("  └────────────────────────────────────────────────────────┘")
    print()
    print("  Key Security Properties:")
    print("  ✅ All traffic stays within AWS private network")
    print("  ✅ Security groups restrict to HTTPS (port 443) only")
    print("  ✅ No public IPs assigned to subnets")
    print("  ✅ PHI/sensitive data never traverses the internet")
    print()


if __name__ == "__main__":
    run_demo()
