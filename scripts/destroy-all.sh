#!/bin/bash
# Delete everything deploy-all.sh created, in reverse dependency order.
# DESTRUCTIVE: deletes the demo DynamoDB tables, Cognito users, gateway, runtime agent and log groups.
#
# Usage:
#   ./scripts/destroy-all.sh               # asks you to type the account ID to confirm
#   ./scripts/destroy-all.sh --with-app    # also tears down the EC2 hosting stack (deploy/cleanup.sh)
#   ./scripts/destroy-all.sh --yes         # no prompt (CI)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-1}}"
export AWS_DEFAULT_REGION="$AWS_REGION"
WITH_APP=0; YES=0
for a in "$@"; do
    case "$a" in --with-app) WITH_APP=1 ;; --yes) YES=1 ;; *) echo "Unknown option: $a"; exit 1 ;; esac
done

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "This deletes all demo stacks in account $ACCOUNT, region $AWS_REGION."
if [ "$YES" != "1" ]; then
    read -r -p "Type the account ID to confirm: " CONFIRM
    [ "$CONFIRM" == "$ACCOUNT" ] || { echo "Cancelled."; exit 1; }
fi

delete_stack() {
    echo "  deleting $1..."
    aws cloudformation delete-stack --stack-name "$1" --region "$AWS_REGION" 2>/dev/null || true
    aws cloudformation wait stack-delete-complete --stack-name "$1" --region "$AWS_REGION" 2>/dev/null \
        && echo "  ✓ $1" || echo "  ! $1 (check the CloudFormation console)"
}

[ "$WITH_APP" == "1" ] && bash "$ROOT/deploy/cleanup.sh"

delete_stack techmart-runtime-observability
delete_stack AgentCore-techmartagent-default
"$ROOT/demos/module5-well-architected/scripts/deploy.sh" destroy
"$ROOT/demos/module4-observability/scripts/deploy.sh" destroy
(cd "$ROOT/demos/infra-agentcore" && ./deploy.sh destroy all)
"$ROOT/demos/module3-security/scripts/deploy.sh" destroy
echo "✅ Done. CloudWatch Transaction Search and the CDK bootstrap stack are left in place."
