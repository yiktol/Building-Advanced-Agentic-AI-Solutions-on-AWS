#!/bin/bash
# Sync the latest origin/main and .env to every in-service app instance via SSM.
#
# Usage: bash deploy/sync-ec2.sh [INSTANCE_IDS] [REGION]
#   INSTANCE_IDS  comma-separated instance IDs (default: every InService instance in the ASG)
#   REGION        default ap-southeast-1
#   ASG_NAME      env var, default mladas-app-asg
#
# Steps run on all instances at once and stop if any instance fails:
#   1. git fetch + reset --hard origin/main   2. copy .env   3. pip install -r app/requirements.txt
# then the Streamlit service is restarted one instance at a time (rolling), waiting for its
# health check, so the load balancer always has healthy targets.

set -euo pipefail

REGION="${2:-ap-southeast-1}"
ASG_NAME="${ASG_NAME:-mladas-app-asg}"
REPO_DIR="/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS"
ENV_FILE="$(dirname "$0")/../.env"
PROJECT="mladas-app"

if [ -n "${1:-}" ]; then
  INSTANCES=(${1//,/ })
else
  INSTANCES=($(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-name "$ASG_NAME" \
    --region "$REGION" \
    --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId' \
    --output text || true))
fi
[ "${#INSTANCES[@]}" -gt 0 ] || { echo "❌ No InService instances found in $ASG_NAME"; exit 1; }

EXPECTED=$(git -C "$(dirname "$0")/.." ls-remote origin refs/heads/main 2>/dev/null | cut -c1-7)

echo "=== Sync to EC2 ==="
echo "  Instances: ${INSTANCES[*]} (${#INSTANCES[@]})"
echo "  Region:    $REGION"
echo "  Commit:    origin/main ${EXPECTED:-unknown}"
echo ""

# run_on <timeout_s> <json-commands> <instance ...>: run on the given instances, wait, print each result.
# Returns 1 if any instance did not succeed.
run_on() {
  local timeout="$1" commands="$2"; shift 2
  local cmd_id status out failed=0
  cmd_id=$(aws ssm send-command --instance-ids "$@" --region "$REGION" \
    --document-name "AWS-RunShellScript" \
    --parameters "{\"commands\":$commands,\"executionTimeout\":[\"$timeout\"]}" \
    --query "Command.CommandId" --output text) || cmd_id=""
  [ -n "$cmd_id" ] || { echo "  ❌ send-command failed for: $*"; return 1; }
  for id in "$@"; do
    status="Pending"
    for _ in $(seq 1 $((timeout / 5 + 6))); do
      sleep 5
      status=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$id" \
        --region "$REGION" --query "Status" --output text 2>/dev/null || echo "Pending")
      case "$status" in Pending|InProgress|Delayed) ;; *) break ;; esac
    done
    out=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$id" --region "$REGION" \
      --query "StandardOutputContent" --output text 2>/dev/null | grep -v '^[[:space:]]*$' | tail -1 || true)
    if [ "$status" == "Success" ]; then
      echo "  ✅ $id ${out}"
    else
      failed=1
      echo "  ❌ $id ($status)"
      aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$id" --region "$REGION" \
        --query "[StandardOutputContent,StandardErrorContent]" --output text 2>/dev/null | tail -5 | sed 's/^/      /'
    fi
  done
  return $failed
}

# --- Step 1: Git fetch + hard reset (deterministic update) ---
echo "1/4 git fetch + reset --hard origin/main"
run_on 120 "[\"cd $REPO_DIR && sudo -u ubuntu git fetch -q origin main && sudo -u ubuntu git reset -q --hard origin/main && sudo -u ubuntu git log -1 --format=commit=%h\"]" "${INSTANCES[@]}" \
  || { echo "❌ git update failed"; exit 1; }

# --- Step 2: Copy .env ---
echo ""
echo "2/4 Copy .env"
if [ ! -f "$ENV_FILE" ]; then
  echo "  ⚠️  .env not found at $ENV_FILE (skipping; the app reads its settings from CloudFormation)"
else
  B64=$(base64 < "$ENV_FILE" | tr -d "\n")
  run_on 60 "[\"echo '$B64' | base64 -d > $REPO_DIR/.env\",\"chown ubuntu:ubuntu $REPO_DIR/.env\",\"echo .env updated\"]" "${INSTANCES[@]}" \
    || { echo "❌ .env copy failed"; exit 1; }
fi

# --- Step 3: Install requirements (picks up new or upgraded dependencies) ---
echo ""
echo "3/4 pip install -r app/requirements.txt"
run_on 600 "[\"cd $REPO_DIR && sudo -u ubuntu venv/bin/pip install -q -r app/requirements.txt 2>&1 | tail -3; echo requirements ok\"]" "${INSTANCES[@]}" \
  || { echo "❌ pip install failed"; exit 1; }

# --- Step 4: Rolling restart, one instance at a time ---
echo ""
echo "4/4 Rolling restart of $PROJECT"
HEALTH_CHECK="for i in \$(seq 1 30); do [ \\\"\$(curl -s -o /dev/null -w '%{http_code}' localhost:8501/_stcore/health)\\\" = 200 ] && break; sleep 2; done; echo service=\$(systemctl is-active $PROJECT) health=\$(curl -s -o /dev/null -w '%{http_code}' localhost:8501/_stcore/health); [ \\\"\$(curl -s -o /dev/null -w '%{http_code}' localhost:8501/_stcore/health)\\\" = 200 ]"
for id in "${INSTANCES[@]}"; do
  run_on 120 "[\"systemctl restart $PROJECT\",\"$HEALTH_CHECK\"]" "$id" \
    || { echo "❌ restart failed on $id; remaining instances were not restarted"; exit 1; }
done

echo ""
echo "=== Done! ${#INSTANCES[@]} instance(s) running origin/main ${EXPECTED:-} ==="
