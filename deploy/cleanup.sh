#!/bin/bash
################################################################################
# Cleanup Script — Delete MLADAS demo EC2 infrastructure
# Usage: ./deploy/cleanup.sh [--force]
################################################################################

set -e
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION='ap-southeast-1'
STACK_NAME='mladas-app-infra'
PROJECT_PREFIX='mladas-app'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✓${NC} $1"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')] ✗${NC} $1"; }

FORCE=false
for arg in "$@"; do [ "$arg" = "--force" ] && FORCE=true; done

if [ "$FORCE" != true ]; then
    echo -e "${RED}WARNING: This will permanently delete:${NC}"
    echo "  - $STACK_NAME (VPC, ALB, ASG, CloudFront, EC2)"
    echo ""
    read -p "Are you sure? (yes/no): " confirm
    [ "$confirm" != "yes" ] && echo "Cancelled." && exit 0
fi

log "Deleting stack: $STACK_NAME"

# Empty S3 logging bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="${PROJECT_PREFIX}-logging-${REGION}-${ACCOUNT_ID}"
if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
    log "Emptying bucket: $BUCKET"
    aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" 2>/dev/null || true
    log_success "Bucket emptied"
fi

# Delete stack
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
log "Waiting for deletion..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
log_success "Stack deleted"

# Clean up secrets
for secret in "cloudfront/${PROJECT_PREFIX}" ; do
    for r in "$REGION" "us-east-1"; do
        aws secretsmanager delete-secret --secret-id "$secret" --force-delete-without-recovery --region "$r" 2>/dev/null || true
    done
done
log_success "Secrets cleaned up"

log_success "Cleanup complete"
