#!/bin/bash
# Cleanup Module 3 CloudFormation stacks
# Usage: ./scripts/cleanup.sh [--confirm]

set -e

REGION="${AWS_DEFAULT_REGION:-ap-southeast-1}"

STACKS=(
    "m3-demo-audit"
    "m3-demo-vpc"
    "m3-demo-verified-permissions"
    "m3-demo-cognito"
    "m3-demo-dynamodb"
)

echo ""
echo "═══════════════════════════════════════════════"
echo "  Module 3: Security — Cleanup"
echo "  Region: $REGION"
echo "  Stacks: ${#STACKS[@]}"
echo "═══════════════════════════════════════════════"
echo ""

if [ "$1" != "--confirm" ]; then
    read -p "  ⚠️  Delete all Module 3 stacks? (yes/no): " ANSWER
    if [ "$ANSWER" != "yes" ]; then
        echo "  Cancelled."
        exit 0
    fi
fi

echo ""
DELETED=0; SKIPPED=0; FAILED=0

for STACK in "${STACKS[@]}"; do
    STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")
    if [ "$STATUS" == "NOT_FOUND" ]; then
        echo "  ⏭️  $STACK — skipped (not found)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi
    echo -n "  🗑️  $STACK — deleting..."
    aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION"
    if aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION" 2>/dev/null; then
        echo " ✓"
        DELETED=$((DELETED + 1))
    else
        echo " ✗ FAILED"
        FAILED=$((FAILED + 1))
    fi
done

rm -f config.env 2>/dev/null

echo ""
echo "  Done. Deleted: $DELETED | Skipped: $SKIPPED | Failed: $FAILED"
[ $FAILED -eq 0 ] && echo "  ✅ Module 3 cleanup complete." || echo "  ⚠️  Some deletions failed."
echo ""
