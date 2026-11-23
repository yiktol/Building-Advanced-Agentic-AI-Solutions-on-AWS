#!/bin/bash
# Deploy log + trace delivery for the techmart_support runtime.
# Run after `agentcore deploy` (the runtime must exist).
# Usage: ./observability/deploy.sh [deploy|destroy]
set -euo pipefail
cd "$(dirname "$0")"

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-1}}"
STACK="techmart-runtime-observability"
ACTION="${1:-deploy}"

if [ "$ACTION" == "destroy" ]; then
    aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION"
    aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION"
    echo "✓ $STACK deleted"
    exit 0
fi

RUNTIME_ARN=$(aws cloudformation describe-stacks --stack-name AgentCore-techmartagent-default --region "$REGION" \
    --query "Stacks[0].Outputs[?starts_with(OutputKey,'ApplicationAgentTechmartSupportRuntimeArnOutput')].OutputValue | [0]" \
    --output text)
if [ -z "$RUNTIME_ARN" ] || [ "$RUNTIME_ARN" == "None" ]; then
    echo "✗ Runtime not found. Run 'agentcore deploy' in agents/techmartagent first."; exit 1
fi
RUNTIME_ID="${RUNTIME_ARN##*/}"
echo "Runtime: $RUNTIME_ID"

aws cloudformation deploy \
    --template-file cfn-runtime-observability.yaml \
    --stack-name "$STACK" \
    --region "$REGION" \
    --parameter-overrides RuntimeArn="$RUNTIME_ARN" RuntimeId="$RUNTIME_ID" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-demo
echo "✓ Log and trace delivery deployed ($STACK)"
