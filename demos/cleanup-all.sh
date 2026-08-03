#!/bin/bash
# =============================================================================
# CLEANUP ALL CLOUDFORMATION STACKS
# Destroys all demo infrastructure across Modules 3, 4, and 5.
# Usage: ./cleanup-all.sh [--confirm]
# =============================================================================

set -e

REGION="${AWS_DEFAULT_REGION:-ap-southeast-1}"

# All stacks in deletion order (dependents first)
STACKS=(
    # AgentCore Infrastructure (improvements)
    "mladas-agentcore-guardrail"
    "mladas-agentcore-policy"
    "mladas-agentcore-gateway"
    "mladas-agentcore-evaluator"
    "mladas-agentcore-memory"

    # Module 5: Well-Architected
    "m5-demo-cost-controls"
    "m5-demo-ecommerce"

    # Module 4: Observability
    "m4-demo-dashboard"
    "m4-demo-alarms"
    "m4-demo-observability"

    # Module 3: Security
    "m3-demo-audit"
    "m3-demo-vpc"
    "m3-demo-verified-permissions"
    "m3-demo-cognito"
    "m3-demo-dynamodb"
)

echo ""
echo "============================================================"
echo "  CLEANUP ALL DEMO CLOUDFORMATION STACKS"
echo "  Region: $REGION"
echo "  Stacks to delete: ${#STACKS[@]}"
echo "============================================================"
echo ""
echo "  Stacks:"
for STACK in "${STACKS[@]}"; do
    echo "    • $STACK"
done
echo ""

# Confirm unless --confirm flag passed
if [ "$1" != "--confirm" ]; then
    read -p "  ⚠️  Delete all stacks? (yes/no): " ANSWER
    if [ "$ANSWER" != "yes" ]; then
        echo "  Cancelled."
        exit 0
    fi
fi

echo ""
echo "  Deleting stacks..."
echo ""

DELETED=0
SKIPPED=0
FAILED=0

for STACK in "${STACKS[@]}"; do
    # Check if stack exists
    STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK" \
        --region "$REGION" \
        --query "Stacks[0].StackStatus" \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [ "$STATUS" == "NOT_FOUND" ]; then
        echo "  ⏭️  $STACK — does not exist (skipped)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    echo -n "  🗑️  $STACK — deleting..."

    # Delete the stack
    aws cloudformation delete-stack \
        --stack-name "$STACK" \
        --region "$REGION" 2>/dev/null

    # Wait for deletion
    if aws cloudformation wait stack-delete-complete \
        --stack-name "$STACK" \
        --region "$REGION" 2>/dev/null; then
        echo " ✓ deleted"
        DELETED=$((DELETED + 1))
    else
        echo " ✗ FAILED"
        FAILED=$((FAILED + 1))
    fi
done

# Clean up config.env files
echo ""
echo "  Cleaning config files..."
for DIR in module3-security module4-observability module5-well-architected; do
    CONFIG="$DIR/config.env"
    if [ -f "$CONFIG" ]; then
        rm -f "$CONFIG"
        echo "    ✓ Removed $CONFIG"
    fi
done

# Summary
echo ""
echo "============================================================"
echo "  CLEANUP COMPLETE"
echo "============================================================"
echo ""
echo "  Deleted: $DELETED"
echo "  Skipped: $SKIPPED (did not exist)"
echo "  Failed:  $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "  ⚠️  Some stacks failed to delete. Check the AWS Console:"
    echo "  https://$REGION.console.aws.amazon.com/cloudformation/home?region=$REGION"
    exit 1
else
    echo "  ✅ All demo resources cleaned up."
fi
echo ""
