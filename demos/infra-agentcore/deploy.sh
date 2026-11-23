#!/bin/bash
# Deploy AgentCore infrastructure for demo improvements
# Usage: ./deploy.sh [deploy|destroy] [component]
# Components: memory, evaluator, policy, gateway, policies, guardrail, all
# The gateway needs the m3-demo-cognito stack (demos/module3-security/scripts/deploy.sh) first.

set -eo pipefail

# Always run relative to this directory (templates are referenced by file name).
cd "$(dirname "$0")"

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-1}}"
export AWS_DEFAULT_REGION="$REGION"
aws sts get-caller-identity >/dev/null 2>&1 || { echo "✗ AWS credentials missing or expired (try: aws sso login)"; exit 1; }
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
    "policy:cfn-agentcore-policy.yaml"
    "gateway:cfn-agentcore-gateway.yaml"
    "policies:cfn-agentcore-policies.yaml"
    "guardrail:cfn-bedrock-guardrail.yaml"
)

if [ "$ACTION" == "destroy" ]; then
    echo ""
    echo "⚠️  Destroying stacks..."
    # Reverse order: policies depend on the gateway and engine, the gateway on the engine.
    for ((i=${#STACKS[@]}-1; i>=0; i--)); do
        entry="${STACKS[$i]}"
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
FAILED=0
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
    if [ "$name" == "gateway" ]; then
        # Gateway validates Cognito JWTs and enforces the policy engine.
        out() { aws cloudformation describe-stacks --stack-name "$1" --region "$REGION" \
            --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text 2>/dev/null; }
        POOL_ID=$(out m3-demo-cognito UserPoolId)
        CLIENT_ID=$(out m3-demo-cognito UserPoolClientId)
        ENGINE_ARN=$(out "${PREFIX}-policy" PolicyEngineArn)
        for v in "$POOL_ID" "$CLIENT_ID" "$ENGINE_ARN"; do
            if [ -z "$v" ] || [ "$v" == "None" ]; then
                echo " ✗ (needs m3-demo-cognito and ${PREFIX}-policy stacks: run demos/module3-security/scripts/deploy.sh and ./deploy.sh deploy policy first)"
                continue 2
            fi
        done
        EXTRA_PARAMS="--parameter-overrides CognitoUserPoolId=$POOL_ID CognitoClientId=$CLIENT_ID PolicyEngineArn=$ENGINE_ARN"
    fi
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
        --tags Project=mladas-demo $EXTRA_PARAMS >/tmp/agentcore-deploy-$name.log 2>&1; then
        echo " ✓"
    else
        echo " ✗ (see /tmp/agentcore-deploy-$name.log)"
        tail -5 "/tmp/agentcore-deploy-$name.log" | sed 's/^/      /'
        FAILED=1
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
if [ "$FAILED" == "1" ]; then echo "  ❌ One or more stacks failed."; exit 1; fi
echo "  ✅ Done."
echo ""
