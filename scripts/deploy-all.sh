#!/bin/bash
# Deploy everything the demos and the Streamlit app need, in dependency order.
#
#   1. Module 3   DynamoDB, Cognito (+ test users), Verified Permissions, audit, seed data
#   2. AgentCore  memory, evaluators, policy engine, gateway (Cognito JWT + Cedar), policies, guardrail
#   3. Module 4   observability log groups, alarms, dashboard
#   4. Module 5   e-commerce tables, cost controls, seed data
#   5. Agent      techmart_support on AgentCore Runtime + online evaluation (agentcore CLI),
#                 then vended log/trace delivery for the runtime
#   6. App        (only with --with-app) EC2 hosting stack, then code sync to the instance
#
# Usage:
#   ./scripts/deploy-all.sh                  # steps 1-5
#   ./scripts/deploy-all.sh --with-app       # steps 1-6
#   ./scripts/deploy-all.sh --from agent     # resume at a step: m3 | agentcore | m4 | m5 | agent | app
#
# Env: AWS_REGION (default ap-southeast-1), ALERT_EMAIL (Module 4 alarms), DEMO_USER_PASSWORD (Cognito users).
# Every step is idempotent, so re-running is safe.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-1}}"
export AWS_DEFAULT_REGION="$AWS_REGION"
WITH_APP=0
FROM="m3"
while [ $# -gt 0 ]; do
    case "$1" in
        --with-app) WITH_APP=1 ;;
        --from) FROM="$2"; shift ;;
        -h|--help) sed -n 2,18p "$0"; exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
    shift
done
STEPS=(m3 agentcore m4 m5 agent app)
START=-1
for i in "${!STEPS[@]}"; do [ "${STEPS[$i]}" == "$FROM" ] && START=$i; done
[ "$START" -lt 0 ] && { echo "Unknown step '$FROM' (use: ${STEPS[*]})"; exit 1; }
run_step() { # run_step <name>: true if the step is at or after --from
    for i in "${!STEPS[@]}"; do [ "${STEPS[$i]}" == "$1" ] && [ "$i" -ge "$START" ] && return 0; done
    return 1
}

BLUE='\033[1;97;44m'; GREEN='\033[1;32m'; RED='\033[1;31m'; NC='\033[0m'
step() { echo -e "\n${BLUE}  $1  ${NC}"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
die() { echo -e "  ${RED}✗ $1${NC}"; exit 1; }

# ---------------------------------------------------------------- preflight
step "Preflight"
for cmd in aws python3 node npm agentcore uv; do
    command -v "$cmd" >/dev/null || die "$cmd not found (see README.md > Prerequisites)"
done
python3 -c "import boto3" 2>/dev/null || die "boto3 missing: pip install boto3"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || die "AWS credentials missing or expired (try: aws sso login)"
ok "account $ACCOUNT, region $AWS_REGION, agentcore CLI $(agentcore --version)"

# ---------------------------------------------------------------- 1. Module 3
if run_step m3; then
    step "1/6 Module 3: security infrastructure"
    "$ROOT/demos/module3-security/scripts/deploy.sh"
fi

# ---------------------------------------------------------------- 2. AgentCore shared resources
if run_step agentcore; then
    step "2/6 AgentCore: memory, evaluators, policy engine, gateway, policies, guardrail"
    (cd "$ROOT/demos/infra-agentcore" && ./deploy.sh deploy all)
fi

# ---------------------------------------------------------------- 3. Module 4
if run_step m4; then
    step "3/6 Module 4: observability"
    "$ROOT/demos/module4-observability/scripts/deploy.sh"
fi

# ---------------------------------------------------------------- 4. Module 5
if run_step m5; then
    step "4/6 Module 5: well-architected"
    "$ROOT/demos/module5-well-architected/scripts/deploy.sh"
fi

# ---------------------------------------------------------------- 5. AgentCore Runtime agent
if run_step agent; then
    step "5/6 Agent: techmart_support on AgentCore Runtime"
    AGENT_DIR="$ROOT/agents/techmartagent"
    TARGETS="$AGENT_DIR/agentcore/aws-targets.json"
    STATE="$AGENT_DIR/agentcore/.cli/deployed-state.json"
    # The committed deploy target and state belong to the account they were deployed from.
    # Point the target at the current account/region; drop state that belongs to another one.
    python3 - "$TARGETS" "$STATE" "$ACCOUNT" "$AWS_REGION" <<'PY'
import json, os, sys
targets, state, account, region = sys.argv[1:]
json.dump([{"name": "default", "account": account, "region": region}], open(targets, "w"), indent=2)
if os.path.exists(state) and f":{account}:" not in open(state).read():
    os.remove(state)
    print("  removed deployed-state.json from a different account")
PY
    (cd "$AGENT_DIR/agentcore/cdk" && npm ci --no-audit --no-fund --silent)
    (cd "$AGENT_DIR" && agentcore deploy -y)
    "$AGENT_DIR/observability/deploy.sh"
fi

# ---------------------------------------------------------------- 6. EC2 app hosting
if [ "$WITH_APP" == "1" ] && run_step app; then
    step "6/6 App: EC2 hosting + code sync"
    "$ROOT/deploy/deploy.sh"
    bash "$ROOT/deploy/sync-ec2.sh"
fi

step "Done"
echo "  Verify with: python3 scripts/verify.py"
