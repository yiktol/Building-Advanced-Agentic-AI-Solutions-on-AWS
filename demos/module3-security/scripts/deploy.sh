#!/bin/bash
# Deploy Module 3 Demo Infrastructure
# Usage: ./scripts/deploy.sh [deploy|destroy]

set -euo pipefail

# Always run relative to the module directory, regardless of where it is invoked from.
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-1}}"
export AWS_DEFAULT_REGION="$REGION"
STACK_PREFIX="m3-demo"
DEFAULT_PASSWORD="${DEMO_USER_PASSWORD:-Hero\$ecure1!}"

ACTION="${1:-deploy}"

echo "=============================================="
echo " Module 3: Security Demo Infrastructure"
echo " Region: $REGION"
echo " Action: $ACTION"
echo "=============================================="

if [ "$ACTION" == "destroy" ]; then
    echo ""
    echo "⚠️  Destroying all stacks..."
    echo ""
    
    # Destroy in reverse order
    for STACK in "${STACK_PREFIX}-audit" "${STACK_PREFIX}-vpc" "${STACK_PREFIX}-verified-permissions" "${STACK_PREFIX}-cognito" "${STACK_PREFIX}-dynamodb"; do
        echo "  Deleting $STACK..."
        aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
        aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
        echo "  ✓ $STACK deleted"
    done
    
    echo ""
    echo "✅ All stacks destroyed."
    exit 0
fi

# --- Preflight: fail early with a clear message instead of halfway through ---
echo ""
echo "🔎 Preflight checks..."
command -v aws >/dev/null     || { echo "  ✗ aws CLI not found"; exit 1; }
command -v python3 >/dev/null || { echo "  ✗ python3 not found"; exit 1; }
python3 -c "import boto3" 2>/dev/null || { echo "  ✗ boto3 missing: pip install boto3"; exit 1; }
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
    echo "  ✗ AWS credentials missing or expired (try: aws sso login)"; exit 1; }
echo "  ✓ aws, python3, boto3 present; account $ACCOUNT, region $REGION"

echo ""
echo "📦 Deploying stacks..."
echo ""

# 1. DynamoDB Tables
echo "  [1/4] DynamoDB tables..."
aws cloudformation deploy \
    --template-file infra/cfn-dynamodb.yaml \
    --stack-name "${STACK_PREFIX}-dynamodb" \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module3-demo
echo "  ✓ DynamoDB tables deployed"

# 2. Cognito User Pool
echo "  [2/4] Cognito User Pool..."
aws cloudformation deploy \
    --template-file infra/cfn-cognito.yaml \
    --stack-name "${STACK_PREFIX}-cognito" \
    --region "$REGION" \
    --parameter-overrides DefaultPassword="$DEFAULT_PASSWORD" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module3-demo
echo "  ✓ Cognito deployed"

# 3. Verified Permissions
echo "  [3/4] Verified Permissions policy store..."
aws cloudformation deploy \
    --template-file infra/cfn-verified-permissions.yaml \
    --stack-name "${STACK_PREFIX}-verified-permissions" \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module3-demo
echo "  ✓ Verified Permissions deployed"

# 4. Audit (CloudWatch + IAM)
echo "  [4/4] Audit logging (CloudWatch + IAM)..."
aws cloudformation deploy \
    --template-file infra/cfn-audit.yaml \
    --stack-name "${STACK_PREFIX}-audit" \
    --region "$REGION" \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module3-demo
echo "  ✓ Audit infrastructure deployed"

echo ""
echo "=============================================="
echo " Creating test users..."
echo "=============================================="

USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-cognito" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
    --output text)

# Create users with custom attributes.
# Bash-3.2 safe: newline-delimited "email,role,dept,hero_name,max_refund" rows
# iterated with a while-read loop (no associative arrays, Bash-3.2 compatible).
while IFS=',' read -r EMAIL ROLE DEPT HERO MAX_REFUND; do
    [ -z "$EMAIL" ] && continue

    # Create user; tolerate only "already exists" so re-runs are idempotent
    if ! OUT=$(aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$EMAIL" \
        --user-attributes \
            Name=email,Value="$EMAIL" \
            Name=email_verified,Value=true \
            Name=custom:role,Value="$ROLE" \
            Name=custom:department,Value="$DEPT" \
            Name=custom:hero_name,Value="$HERO" \
            Name=custom:max_refund,Value="$MAX_REFUND" \
        --message-action SUPPRESS \
        --region "$REGION" 2>&1 >/dev/null); then
        echo "$OUT" | grep -q UsernameExistsException || { echo "  ✗ create $EMAIL failed: $OUT"; exit 1; }
    fi
    # Keep attributes in sync on re-runs, then set a permanent password
    aws cognito-idp admin-update-user-attributes \
        --user-pool-id "$USER_POOL_ID" --username "$EMAIL" --region "$REGION" \
        --user-attributes \
            Name=custom:role,Value="$ROLE" \
            Name=custom:department,Value="$DEPT" \
            Name=custom:hero_name,Value="$HERO" \
            Name=custom:max_refund,Value="$MAX_REFUND" >/dev/null
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$EMAIL" \
        --password "$DEFAULT_PASSWORD" \
        --permanent \
        --region "$REGION" >/dev/null
    echo "  ✓ $HERO ($EMAIL) — $ROLE/$DEPT"
done <<'EOF'
clark.kent@dailyplanet.com,admin,finance,Superman,10000
bruce.wayne@waynetech.com,security_lead,security,Batman,5000
peter.parker@bugle.com,agent,support,Spider-Man,500
diana.prince@themyscira.gov,manager,operations,Wonder Woman,2000
tony.stark@starkindustries.com,engineer,engineering,Iron Man,0
EOF

echo ""
echo "=============================================="
echo " Seeding DynamoDB..."
echo "=============================================="

python3 scripts/seed_data.py --region "$REGION" --verify

echo ""
echo "=============================================="
echo " Gathering outputs..."
echo "=============================================="

# Gather all outputs
CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-cognito" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
    --output text)

POLICY_STORE_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-verified-permissions" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='PolicyStoreId'].OutputValue" \
    --output text)

# Write config file for demo scripts
cat > config.env << EOF
# Module 3 Demo Configuration (auto-generated by deploy.sh)
export AWS_REGION="$REGION"
export COGNITO_USER_POOL_ID="$USER_POOL_ID"
export COGNITO_CLIENT_ID="$CLIENT_ID"
export POLICY_STORE_ID="$POLICY_STORE_ID"
export CUSTOMERS_TABLE="m3-demo-customers"
export ORDERS_TABLE="m3-demo-orders"
export AUDIT_TABLE="m3-demo-audit-log"
export AUDIT_LOG_GROUP="/m3-demo/agent-audit"
export SECURITY_LOG_GROUP="/m3-demo/security-events"
export DEFAULT_PASSWORD="$DEFAULT_PASSWORD"
EOF

echo ""
echo "  Config written to: config.env"
echo ""
echo "=============================================="
echo " ✅ DEPLOYMENT COMPLETE"
echo "=============================================="
echo ""
echo "  User Pool ID:     $USER_POOL_ID"
echo "  Client ID:        $CLIENT_ID"
echo "  Policy Store ID:  $POLICY_STORE_ID"
echo ""
echo "  Test Users:"
echo "    Superman (Clark Kent):    clark.kent@dailyplanet.com    admin/finance"
echo "    Batman (Bruce Wayne):     bruce.wayne@waynetech.com     security_lead/security"
echo "    Spider-Man (Peter Parker): peter.parker@bugle.com       agent/support"
echo "    Wonder Woman (Diana):     diana.prince@themyscira.gov   manager/operations"
echo "    Iron Man (Tony Stark):    tony.stark@starkindustries.com engineer/engineering"
echo ""
echo "  Password for all: $DEFAULT_PASSWORD"
echo ""
echo "  To use: source config.env && python part1_unprotected_agent.py"
echo ""
