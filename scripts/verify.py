"""
Verify a deployment of this project end to end.

Checks are read-only except one AgentCore Runtime invocation (adds a trace) and Cognito logins.
Refunds are only attempted in cases the Cedar policies must DENY, so no order data changes.

Usage:  python3 scripts/verify.py            (AWS_REGION defaults to ap-southeast-1)
Exit code: 0 all checks passed, 1 a check failed, 130 Ctrl+C.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

import boto3

REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1"))
PASSWORD = os.environ.get("DEMO_USER_PASSWORD", "Hero$ecure1!")
GREEN, RED, BLUE, DIM, NC = "\033[1;32m", "\033[1;31m", "\033[1;97;44m", "\033[2m", "\033[0m"
results: list[tuple[str, bool, str]] = []

STACKS = [
    "m3-demo-dynamodb", "m3-demo-cognito", "m3-demo-verified-permissions", "m3-demo-audit",
    "mladas-agentcore-memory", "mladas-agentcore-evaluator", "mladas-agentcore-policy",
    "mladas-agentcore-gateway", "mladas-agentcore-policies", "mladas-agentcore-guardrail",
    "m4-demo-observability", "m4-demo-alarms", "m4-demo-dashboard",
    "m5-demo-ecommerce", "m5-demo-cost-controls",
    "AgentCore-techmartagent-default", "techmart-runtime-observability",
]
REFUND_POLICIES = {"refund_finance_admin", "refund_support_agent_under_500", "refund_security_lead_under_5000", "forbid_engineering_refund"}


def section(title: str):
    print(f"\n{BLUE}  {title:<70}{NC}")


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))
    icon = f"{GREEN}✓{NC}" if ok else f"{RED}✗{NC}"
    print(f"  {icon} {name} {DIM}{detail}{NC}")
    return ok


def outputs(cfn, stack: str) -> dict:
    out = cfn.describe_stacks(StackName=stack)["Stacks"][0].get("Outputs", [])
    return {o["OutputKey"]: o["OutputValue"] for o in out}


def gateway_call(url: str, token: str, tool: str, args: dict) -> str:
    body = json.dumps({"jsonrpc": "2.0", "id": "1", "method": "tools/call", "params": {"name": tool, "arguments": args}}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    if data.get("error"):
        return "DENY" if "denied" in data["error"].get("message", "").lower() else "ERROR " + data["error"].get("message", "")[:80]
    res = data.get("result", {})
    return "DENY" if res.get("isError") else "ALLOW"


def main():
    cfn = boto3.client("cloudformation", region_name=REGION)
    print(f"Account {boto3.client('sts').get_caller_identity()['Account']}, region {REGION}")

    section("CloudFormation stacks")
    for s in STACKS:
        try:
            status = cfn.describe_stacks(StackName=s)["Stacks"][0]["StackStatus"]
            check(s, status.endswith("_COMPLETE") and "ROLLBACK" not in status, status)
        except Exception:
            check(s, False, "not deployed")

    section("Module 3 data and identity")
    ddb = boto3.resource("dynamodb", region_name=REGION)
    item = ddb.Table("m3-demo-customers").get_item(Key={"customer_id": "CUST-1005"}).get("Item", {})
    check("CUST-1005 seeded with phone and address", item.get("phone") and item.get("address"))
    cog = outputs(cfn, "m3-demo-cognito")
    idp = boto3.client("cognito-idp", region_name=REGION)

    def token(email):
        return idp.initiate_auth(ClientId=cog["UserPoolClientId"], AuthFlow="USER_PASSWORD_AUTH",
                                 AuthParameters={"USERNAME": email, "PASSWORD": PASSWORD})["AuthenticationResult"]["IdToken"]

    try:
        peter, tony = token("peter.parker@bugle.com"), token("tony.stark@starkindustries.com")
        check("Cognito login for demo users", True)
    except Exception as e:
        check("Cognito login for demo users", False, str(e)[:100])
        peter = tony = ""

    section("AgentCore Gateway + Policy Engine (Cedar)")
    gw = outputs(cfn, "mladas-agentcore-gateway")
    url = gw.get("GatewayUrl", "").rstrip("/") + "/mcp"
    engine = outputs(cfn, "mladas-agentcore-policy")["PolicyEngineId"]
    ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
    names = {p["name"] for p in ctl.list_policies(policyEngineId=engine)["policies"] if p.get("status") == "ACTIVE"}
    check("refund Cedar policies active", REFUND_POLICIES <= names, ", ".join(sorted(REFUND_POLICIES - names)) or "4/4")
    g = ctl.get_gateway(gatewayIdentifier=gw["GatewayId"])
    check("gateway uses Cognito JWT and enforces the policy engine",
          g.get("authorizerType") == "CUSTOM_JWT" and (g.get("policyEngineConfiguration") or {}).get("mode") == "ENFORCE")
    if peter:
        check("orderStatus allowed for support agent", gateway_call(url, peter, "order-status___orderStatus", {"orderId": "ORD-5002"}) == "ALLOW")
        check("$700 refund denied for support agent (limit $500)", gateway_call(url, peter, "order-status___processRefund", {"orderId": "ORD-5002", "amount": 700, "reason": "verify"}) == "DENY")
        check("refund denied for engineering (forbid)", gateway_call(url, tony, "order-status___processRefund", {"orderId": "ORD-5002", "amount": 10, "reason": "verify"}) == "DENY")
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=b'{"jsonrpc":"2.0","id":"1","method":"tools/list"}',
                                                      headers={"Content-Type": "application/json"}), timeout=30)
        check("gateway rejects calls without a token", False, "request was accepted")
    except urllib.error.HTTPError as e:
        check("gateway rejects calls without a token", e.code == 401, f"HTTP {e.code}")

    section("AgentCore Runtime agent, online evaluation, log delivery")
    agent_out = outputs(cfn, "AgentCore-techmartagent-default")
    arn = next(v for k, v in agent_out.items() if k.startswith("ApplicationAgentTechmartSupportRuntimeArnOutput"))
    oe_id = next((v for k, v in agent_out.items() if k.startswith("ApplicationOnlineEvalTechmartOnlineEvalIdOutput")), "")
    rt = boto3.client("bedrock-agentcore", region_name=REGION)
    sid = "verify-" + uuid.uuid4().hex + uuid.uuid4().hex[:6]
    t = time.time()
    resp = rt.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=sid, qualifier="DEFAULT",
                                   payload=json.dumps({"prompt": "Is the TechMart Air in stock?"}).encode())
    body = resp["response"].read().decode()
    check("runtime answers and calls check_inventory", "check_inventory" in body, f"{int((time.time() - t) * 1000)} ms, session {sid}")
    if oe_id:
        cfg = ctl.get_online_evaluation_config(onlineEvaluationConfigId=oe_id)
        check("online evaluation config enabled", cfg.get("status") == "ACTIVE" and cfg.get("executionStatus") == "ENABLED",
              f"{len(cfg.get('evaluators', []))} evaluators")
    else:
        check("online evaluation config enabled", False, "not deployed")
    logs = boto3.client("logs", region_name=REGION)
    delivered = {d["deliverySourceName"] for page in logs.get_paginator("describe_deliveries").paginate()
                 for d in page["deliveries"]}
    for src in ("techmart-runtime-app-logs", "techmart-runtime-usage-logs", "techmart-runtime-traces",
                "mladas-gateway-application-logs", "mladas-gateway-traces"):
        check(f"log/trace delivery {src}", src in delivered)
    dest = boto3.client("xray", region_name=REGION).get_trace_segment_destination()
    check("X-Ray Transaction Search sends spans to CloudWatch Logs", dest.get("Destination") == "CloudWatchLogs" and dest.get("Status") == "ACTIVE")

    section("Module 4 telemetry targets")
    groups = {g["logGroupName"] for g in logs.describe_log_groups(logGroupNamePrefix="/m4-demo/")["logGroups"]}
    check("/m4-demo/agent-spans log group", "/m4-demo/agent-spans" in groups)

    failed = [r for r in results if not r[1]]
    print(f"\n  {len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print(f"  {RED}✗ verification failed{NC}")
        sys.exit(1)
    print(f"  {GREEN}✓ deployment verified{NC}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye!")
        sys.exit(130)
