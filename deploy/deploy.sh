#!/bin/bash
################################################################################
# CloudFormation Deployment Script
# Description: Deploy MLADAS demo EC2 infrastructure (VPC, ALB, ASG, CloudFront)
#
# Usage:
#   ./deploy/deploy.sh           # Deploy everything
#   ./deploy/deploy.sh main      # Deploy main stack only
################################################################################

set -e
set -o pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGION='ap-southeast-1'
STACK_NAME='mladas-app-v2'
TEMPLATE_PREFIX='templates/mladas-app'
PARAMETER_PREFIX='/genai/cognito'
PROJECT_PREFIX='mladas-app'
LOG_FILE="deployment-$(date +%Y%m%d-%H%M%S).log"

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"; }

check_prerequisites() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not installed"
        exit 1
    fi
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        exit 1
    fi
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    log_success "Account: $account_id | Region: $REGION"
}

get_ssm_parameter() {
    aws ssm get-parameter --name "$1" --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null
}

wait_for_stack() {
    local stack_name=$1
    local start_time=$(date +%s)
    while true; do
        local status=$(aws cloudformation describe-stacks --stack-name "$stack_name" --region "$REGION" \
            --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "UNKNOWN")
        case $status in
            *COMPLETE) log_success "Stack $status ($(( $(date +%s) - start_time ))s)"; return 0 ;;
            *FAILED|*ROLLBACK*) log_error "Stack $status"; return 1 ;;
            UNKNOWN) log_error "Stack not found"; return 1 ;;
        esac
        echo -ne "\r  Status: $status ($(( $(date +%s) - start_time ))s)"
        sleep 10
    done
}

upload_templates() {
    local bucket=$1
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    log "Uploading templates to s3://$bucket/$TEMPLATE_PREFIX/"
    for yaml_file in "$script_dir"/cfn-*.yaml; do
        [ -f "$yaml_file" ] || continue
        aws s3 cp "$yaml_file" "s3://$bucket/$TEMPLATE_PREFIX/$(basename "$yaml_file")" --region "$REGION" > /dev/null
        log_success "  $(basename "$yaml_file")"
    done
}

deploy_main_stack() {
    log "=========================================="
    log "MLADAS Demo — EC2 Infrastructure"
    log "=========================================="

    local bucket=$(get_ssm_parameter "${PARAMETER_PREFIX}/BucketName")
    if [ -z "$bucket" ]; then
        log_error "S3 bucket not found in SSM: ${PARAMETER_PREFIX}/BucketName"
        exit 1
    fi
    log "S3 Bucket: $bucket"

    upload_templates "$bucket"

    local template_url="https://$bucket.s3.$REGION.amazonaws.com/$TEMPLATE_PREFIX/cfn-main.yaml"

    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &>/dev/null; then
        log "Updating stack: $STACK_NAME"
        local output=$(aws cloudformation update-stack \
            --region "$REGION" \
            --stack-name "$STACK_NAME" \
            --template-url "$template_url" \
            --parameters ParameterKey=Prefix,ParameterValue="$TEMPLATE_PREFIX" ParameterKey=BucketRegion,ParameterValue="$REGION" \
            --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM 2>&1) || true
        if echo "$output" | grep -q "No updates"; then
            log_success "No updates needed"
        else
            wait_for_stack "$STACK_NAME"
        fi
    else
        log "Creating stack: $STACK_NAME"
        aws cloudformation create-stack \
            --region "$REGION" \
            --stack-name "$STACK_NAME" \
            --template-url "$template_url" \
            --parameters ParameterKey=Prefix,ParameterValue="$TEMPLATE_PREFIX" ParameterKey=BucketRegion,ParameterValue="$REGION" \
            --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM
        wait_for_stack "$STACK_NAME"
    fi

    aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table 2>/dev/null || true

    log_success "Deployment complete"
}

main() {
    log "MLADAS Demo Deployment | Region: $REGION | Stack: $STACK_NAME"
    check_prerequisites
    deploy_main_stack
}

trap 'log_error "Deployment failed. See $LOG_FILE"' ERR
main "$@"
