#!/bin/bash
# Sync local repo and .env to the EC2 instance via SSM.
# Usage: bash deploy/sync-ec2.sh [INSTANCE_ID] [REGION]
#
# Defaults:
#   INSTANCE_ID = (set your instance ID)
#   REGION      = ap-southeast-1

set -e

INSTANCE_ID="${1:-i-00c7cc125113deaa6}"
REGION="${2:-ap-southeast-1}"
REPO_DIR="/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS"
ENV_FILE="$(dirname "$0")/../.env"
PROJECT="mladas-app"

echo "=== Sync to EC2 ==="
echo "  Instance: $INSTANCE_ID"
echo "  Region:   $REGION"
echo "  Project:  $PROJECT"
echo ""

# --- Step 1: Git pull on remote ---
echo "1/3 Running git pull on EC2..."
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --document-name "AWS-RunShellScript" \
  --parameters "{\"commands\":[\"cd $REPO_DIR && sudo -u ubuntu git pull origin main 2>&1\"]}" \
  --query "Command.CommandId" \
  --output text)

echo "     Command: $CMD_ID"
sleep 8

PULL_STATUS=$(aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --query "Status" \
  --output text)

if [ "$PULL_STATUS" != "Success" ]; then
  echo "  ❌ git pull failed (status: $PULL_STATUS)"
  aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$REGION" \
    --query "[StandardOutputContent,StandardErrorContent]" \
    --output text
  exit 1
fi
echo "  ✅ git pull succeeded"

# --- Step 2: Copy .env ---
echo ""
echo "2/3 Copying .env to EC2..."

if [ ! -f "$ENV_FILE" ]; then
  echo "  ⚠️  .env file not found at: $ENV_FILE (skipping)"
else
  B64=$(base64 -w0 "$ENV_FILE")
  CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --document-name "AWS-RunShellScript" \
    --parameters "{\"commands\":[\"echo '$B64' | base64 -d > $REPO_DIR/.env\",\"chown ubuntu:ubuntu $REPO_DIR/.env\"]}" \
    --query "Command.CommandId" \
    --output text)

  sleep 5

  ENV_STATUS=$(aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$REGION" \
    --query "Status" \
    --output text)

  if [ "$ENV_STATUS" != "Success" ]; then
    echo "  ❌ .env copy failed (status: $ENV_STATUS)"
    exit 1
  fi
  echo "  ✅ .env updated"
fi

# --- Step 3: Restart service ---
echo ""
echo "3/3 Restarting Streamlit service..."
CMD_ID=$(aws ssm send-command \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --document-name "AWS-RunShellScript" \
  --parameters "{\"commands\":[\"systemctl restart ${PROJECT}-demo && sleep 2 && systemctl is-active ${PROJECT}-demo\"]}" \
  --query "Command.CommandId" \
  --output text)

sleep 8

RESTART_STATUS=$(aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --query "Status" \
  --output text)

RESTART_OUTPUT=$(aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --query "StandardOutputContent" \
  --output text)

if [ "$RESTART_STATUS" != "Success" ]; then
  echo "  ❌ Restart failed (status: $RESTART_STATUS)"
  exit 1
fi
echo "  ✅ Service status: $RESTART_OUTPUT"

echo ""
echo "=== Done! EC2 is running latest code ==="
