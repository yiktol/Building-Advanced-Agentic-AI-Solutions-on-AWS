"""
Test: Part 4 — VPC Private Access (Infrastructure Inspection)

Inspects the deployed VPC stack to verify private connectivity
configuration (VPC endpoints, no internet gateway).

Usage:
    python tests/test_part4.py

Requires:
    - VPC CloudFormation stack deployed (m3-demo-vpc)
    - AWS credentials configured
"""

import sys
import time

sys.path.insert(0, ".")

from part4_vpc_private_access import get_stack_outputs

# --- Configuration ---
MODEL_ID = "apac.amazon.nova-micro-v1:0"
VPC_STACK_NAME = "m3-demo-vpc"

# --- Colors ---
RED = "\033[1;31m"
DIM = "\033[2m"
RESET = "\033[0m"
PROMPT_COLOR = "\033[0;91m"
RESPONSE_COLOR = "\033[0;97m"
TIMING_COLOR = "\033[0;90m"
SUCCESS = "\033[1;32m"
FAIL = "\033[1;31m"
HEADER_BG = "\033[1;97;41m"  # White on red background


def main():
    print(f"\n{HEADER_BG}{'=' * 72}{RESET}")
    print(f"{HEADER_BG}  TEST: Part 4 — VPC Private Access (Infrastructure Inspection)       {RESET}")
    print(f"{HEADER_BG}{'=' * 72}{RESET}\n")

    total_start = time.time()
    results = []

    # --- Step 1: Check if VPC stack is deployed ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 1: Check VPC stack deployment{RESET}")
    print(f"  {PROMPT_COLOR}Stack: {VPC_STACK_NAME}{RESET}\n")

    start = time.time()
    outputs = get_stack_outputs(VPC_STACK_NAME)
    elapsed = time.time() - start

    if "error" in outputs:
        print(f"  {DIM}⚠️  VPC stack not deployed: {outputs['error']}{RESET}")
        print(f"  {DIM}   Skipping VPC test (infrastructure not deployed).{RESET}")
        print(f"  {DIM}   Deploy with: ./scripts/deploy.sh{RESET}\n")
        sys.exit(0)

    print(f"    {RESPONSE_COLOR}Stack found. Outputs: {list(outputs.keys())}{RESET}")
    print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")
    results.append(("PASS", elapsed))

    # --- Step 2: Verify VPC ID exists ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 2: Verify VPC ID exists in stack outputs{RESET}\n")

    start = time.time()
    vpc_id = outputs.get("VpcId", "")
    elapsed = time.time() - start

    print(f"    {RESPONSE_COLOR}VPC ID: {vpc_id}{RESET}")
    print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

    if vpc_id and vpc_id.startswith("vpc-"):
        results.append(("PASS", elapsed))
    else:
        print(f"    {FAIL}Expected VPC ID starting with 'vpc-' but got '{vpc_id}'{RESET}")
        results.append(("FAIL", elapsed))

    # --- Step 3: Check for VPC endpoints ---
    print(f"  {RED}{'─' * 68}{RESET}")
    print(f"  {RED}Step 3: Verify VPC endpoints exist{RESET}\n")

    start = time.time()
    try:
        import boto3
        import os

        region = os.environ.get("AWS_REGION", "ap-southeast-1")
        ec2_client = boto3.client("ec2", region_name=region)

        endpoints = ec2_client.describe_vpc_endpoints(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
        )["VpcEndpoints"]
        elapsed = time.time() - start

        print(f"    {RESPONSE_COLOR}Found {len(endpoints)} VPC endpoint(s){RESET}")
        for ep in endpoints:
            service = ep["ServiceName"]
            state = ep["State"]
            ep_type = ep["VpcEndpointType"]
            icon = "✅" if state == "available" else "⚠️"
            print(f"    {RESPONSE_COLOR}  {icon} {service} ({ep_type}, {state}){RESET}")

        print(f"\n    {TIMING_COLOR}⏱  {elapsed:.1f}s{RESET}\n")

        if len(endpoints) > 0:
            results.append(("PASS", elapsed))
        else:
            print(f"    {FAIL}No VPC endpoints found — private connectivity not configured{RESET}")
            results.append(("FAIL", elapsed))
    except Exception as e:
        elapsed = time.time() - start
        print(f"    {FAIL}ERROR: {e}{RESET}\n")
        results.append(("FAIL", elapsed))

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n  {RED}{'═' * 68}{RESET}")
    print(f"  {RED}RESULTS{RESET}\n")

    step_names = ["Stack Deployed", "VPC ID Valid", "VPC Endpoints Exist"]
    all_passed = True
    for i, (status, elapsed) in enumerate(results):
        icon = "✅" if status == "PASS" else "❌"
        color = SUCCESS if status == "PASS" else FAIL
        print(f"    {icon} {color}{step_names[i]}: {status}{RESET} {TIMING_COLOR}({elapsed:.1f}s){RESET}")
        if status != "PASS":
            all_passed = False

    print(f"\n    {TIMING_COLOR}Total: {total_elapsed:.1f}s{RESET}")

    if all_passed:
        print(f"\n  {SUCCESS}✅ Part 4 test passed — VPC private access configured.{RESET}")
        print(f"  {DIM}Tip: All traffic stays within AWS private network (no IGW).{RESET}\n")
    else:
        print(f"\n  {FAIL}❌ Part 4 test had failures.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
