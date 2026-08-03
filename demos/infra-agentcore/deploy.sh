#!/bin/bash
# Deploy AgentCore infrastructure for demo improvements
# Usage: ./deploy.sh [deploy|destroy] [component]
# Components: memory, evaluator, gateway, policy, guardrail, all

set -e

REGION="${AWS_DEFAULT_REGION:-ap-southeast-1}"
PREFIX="mladas-agentcore"
ACTION="${1:-deploy}"
COMPONENT="${2:-all}"

echo "=============================================="
echo " AgentCore Infrastructure"
echo " Region: $REGION"
echo " Action: $ACTION"
echo " Component: $COMPONENT"
echo "=============================================="

STACKS=(
    "memory:cfn-agentcore-memory.yaml"
    "evaluator:cfn-agentcore-evaluator.yaml"
    "gateway:cfn-agentcore-gateway.yaml"
    "policy:cfn-agentcore-policy.yaml"
    "guardrail:cfn-bedrock-guardrail.yaml"
)

if [ "$ACTION" == "destroy" ]; then
    echo ""
    echo "⚠️  Destroying stacks..."
    for entry in "${STACKS[@]}"; do
        name="${entry%%:*}"
        stack_name="${PREFIX}-${name}"
        if [ "$COMPONENT" != "all" ] && [ "$COMPONENT" != "$name" ]; then
            continue
        fi
        echo -n "  🗑️  $stack_name..."
        aws cloudformation delete-stack --stack-name "$stack_name" --region "$REGION" 2>/dev/null || true
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$REGION" 2>/dev/null && echo " ✓" || echo " (not found)"
    done
    echo "✅ Done."
    exit 0
fi

echo ""
echo "📦 Deploying..."
echo ""

for entry in "${STACKS[@]}"; do
    name="${entry%%:*}"
    template="${entry##*:}"
    stack_name="${PREFIX}-${name}"

    if [ "$COMPONENT" != "all" ] && [ "$COMPONENT" != "$name" ]; then
        continue
    fi

    echo -n "  [$name] $stack_name..."
    if aws cloudformation deploy \
        --template-file "$template" \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --no-fail-on-empty-changeset \
        --tags Project=mladas-demo 2>/dev/null; then
        echo " ✓"
    else
        echo " ✗ (check events)"
    fi
done

# Gather outputs
echo ""
echo "=============================================="
echo " Outputs"
echo "=============================================="

cat > config.env << EOF
# AgentCore Infrastructure (auto-generated)
export AWS_REGION="$REGION"
EOF

for entry in "${STACKS[@]}"; do
    name="${entry%%:*}"
    stack_name="${PREFIX}-${name}"
    if [ "$COMPONENT" != "all" ] && [ "$COMPONENT" != "$name" ]; then
        continue
    fi

    outputs=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" \
        --output text 2>/dev/null || true)

    if [ -n "$outputs" ]; then
        echo "  [$name]"
        while IFS=$'\t' read -r key value; do
            echo "    $key = $value"
            echo "export ${key}=\"${value}\"" >> config.env
        done <<< "$outputs"
    fi
done

echo ""
echo "  Config: source config.env"
echo "  ✅ Done."
echo ""
