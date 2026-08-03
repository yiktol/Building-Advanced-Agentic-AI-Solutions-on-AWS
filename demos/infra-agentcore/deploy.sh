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
    "policies:cfn-agentcore-policies.yaml"
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
    EXTRA_PARAMS=""
    if [ "$name" == "policies" ]; then
        # Get PolicyEngineId from the policy engine stack
        POLICY_ENGINE_ID=$(aws cloudformation describe-stacks \
            --stack-name "${PREFIX}-policy" \
            --region "$REGION" \
            --query "Stacks[0].Outputs[?OutputKey=='PolicyEngineId'].OutputValue" \
            --output text 2>/dev/null)
        GATEWAY_ARN=$(aws cloudformation describe-stacks \
            --stack-name "${PREFIX}-gateway" \
            --region "$REGION" \
            --query "Stacks[0].Outputs[?OutputKey=='GatewayArn'].OutputValue" \
            --output text 2>/dev/null)
        if [ -z "$POLICY_ENGINE_ID" ] || [ "$POLICY_ENGINE_ID" == "None" ]; then
            echo " ✗ (policy engine stack not ready)"
            continue
        fi
        if [ -z "$GATEWAY_ARN" ] || [ "$GATEWAY_ARN" == "None" ]; then
            echo " ✗ (gateway stack not ready)"
            continue
        fi
        EXTRA_PARAMS="--parameter-overrides PolicyEngineId=$POLICY_ENGINE_ID GatewayArn=$GATEWAY_ARN"
    fi
    if aws cloudformation deploy \
        --template-file "$template" \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --capabilities CAPABILITY_NAMED_IAM \
        --no-fail-on-empty-changeset \
        --tags Project=mladas-demo $EXTRA_PARAMS 2>/dev/null; then
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
