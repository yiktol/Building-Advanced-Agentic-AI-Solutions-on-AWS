#!/bin/bash
# Deploy Module 5 Demo Infrastructure
# Usage: ./scripts/deploy.sh [deploy|destroy]

set -e

REGION="${AWS_DEFAULT_REGION:-ap-southeast-1}"
STACK_PREFIX="m5-demo"
ACTION="${1:-deploy}"

echo "=============================================="
echo " Module 5: Well-Architected Demo Infrastructure"
echo " Region: $REGION"
echo " Action: $ACTION"
echo "=============================================="

if [ "$ACTION" == "destroy" ]; then
    echo ""
    echo "⚠️  Destroying all stacks..."
    for STACK in "${STACK_PREFIX}-cost-controls" "${STACK_PREFIX}-ecommerce"; do
        echo "  Deleting $STACK..."
        aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
        aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
        echo "  ✓ $STACK deleted"
    done
    echo "✅ All stacks destroyed."
    exit 0
fi

echo ""
echo "📦 Deploying stacks..."
echo ""

# 1. E-commerce tables
echo "  [1/2] E-commerce DynamoDB tables..."
aws cloudformation deploy \
    --template-file infra/cfn-ecommerce.yaml \
    --stack-name "${STACK_PREFIX}-ecommerce" \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module5-demo
echo "  ✓ E-commerce tables deployed"

# 2. Cost controls
echo "  [2/2] Cost control alarms..."
aws cloudformation deploy \
    --template-file infra/cfn-cost-controls.yaml \
    --stack-name "${STACK_PREFIX}-cost-controls" \
    --region "$REGION" \
    --no-fail-on-empty-changeset \
    --tags Project=mladas-module5-demo
echo "  ✓ Cost controls deployed"

echo ""
echo "📦 Seeding product catalog..."
python3 scripts/seed_data.py --region "$REGION"

# Write config
cat > config.env << EOF
# Module 5 Demo Configuration (auto-generated)
export AWS_REGION="$REGION"
export PRODUCTS_TABLE="m5-demo-products"
export ORDERS_TABLE="m5-demo-orders"
export CUSTOMERS_TABLE="m5-demo-customers"
export WA_REVIEW_TABLE="m5-demo-wa-reviews"
export COST_NAMESPACE="m5-demo/CostMetrics"
export OPS_NAMESPACE="m5-demo/Operational"
EOF

echo ""
echo "=============================================="
echo " ✅ DEPLOYMENT COMPLETE"
echo "=============================================="
echo ""
echo "  Config: source config.env"
echo "  Run:    python part1_ecommerce_system.py"
echo ""
