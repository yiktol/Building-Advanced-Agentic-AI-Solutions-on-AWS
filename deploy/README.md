# Deploy — EC2 Hosting Infrastructure

Production deployment for the MLADAS Streamlit demo app on EC2 behind ALB + CloudFront.

## Architecture

```
User → CloudFront → ALB (HTTPS, origin verify) → EC2 (Streamlit :8501)
                                                    ↓
                                              Private Subnet (SSM access)
```

## Prerequisites

- Existing VPC with CloudFormation exports: `VpcId`, `PublicSubnetOne`, `PublicSubnetTwo`, `PrivateSubnetOne`
- SSM parameters under `/genai/cognito/`: `BucketName`, `DomainName`, `CertificateId`, `WebApplicationFirewallACLArn`
- ACM certificates in `ap-southeast-1` (ALB) and `us-east-1` (CloudFront)
- S3 bucket with `lambda/random_generator.zip` for the random string Lambda

## Files

| File | Purpose |
|------|---------|
| `deploy.sh` | Deploy full stack (uploads templates, creates/updates CFN) |
| `cleanup.sh` | Tear down infrastructure (empties S3, deletes stack + secrets) |
| `sync-ec2.sh` | Sync code + .env to running EC2 via SSM (git fetch + reset --hard + restart) |
| `generate-env.sh` | Generate repo-root `.env` from deployed CloudFormation stack outputs |
| `cfn-main.yaml` | Root nested stack (reads SSM params, wires sub-stacks) |
| `cfn-alb-asg.yaml` | ALB + ASG + EC2 Launch Template with UserData |
| `cfn-cloudfront.yaml` | CloudFront + origin verification secret + logging |

## Usage

```bash
# Deploy infrastructure
./deploy/deploy.sh

# Sync code changes to EC2 (no redeploy needed)
./deploy/sync-ec2.sh

# Tear down
./deploy/cleanup.sh
```

### Generate `.env` from deployed stacks

`generate-env.sh` reads the deployed CloudFormation stacks (the same ones the app
queries: `mladas-agentcore-memory`, `mladas-agentcore-evaluator`,
`mladas-agentcore-gateway`, `mladas-agentcore-policy`, `mladas-agentcore-guardrail`,
`m3-demo-cognito`, `m3-demo-verified-permissions`) and writes the repo-root `.env`
that `sync-ec2.sh` copies to the instance. It emits a key only when its value
resolves, never hardcodes resource ids, and is safe to re-run (it regenerates the
file cleanly each time).

```bash
# Uses AWS_REGION (default ap-southeast-1)
bash deploy/generate-env.sh

# then push it to the running instance
./deploy/sync-ec2.sh
```

### Module 3 demo users — password override

`demos/module3-security/scripts/deploy.sh` seeds the five demo users with a shared
permanent password. The default is unchanged, but you can override it without
editing the script by exporting `DEMO_USER_PASSWORD` before deploying:

```bash
DEMO_USER_PASSWORD='YourOwnStrongPass1!' ./demos/module3-security/scripts/deploy.sh
```

### Zero-downtime updates (opt-in)

`sync-ec2.sh` updates code in place and restarts the service, which causes a brief
blip while Streamlit restarts. For a zero-downtime rollout, temporarily raise the
ASG capacity so a replacement instance can come up before the old one is replaced:

```bash
# Raise max capacity to 2, then run an instance refresh
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name mladas-app-asg \
  --max-size 2 --region ap-southeast-1

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name mladas-app-asg --region ap-southeast-1
```

This is opt-in and does not change default live behavior (the ASG stays at its
current `MaxSize` otherwise).

## Naming Convention

All resources use `mladas-demo` prefix to avoid conflicts with other stacks:
- Stack: `mladas-demo-ec2`
- ALB: `lb-mladas-demo`
- ASG: `mladas-demo-asg`
- Service: `mladas-demo.service`
- Secret: `cloudfront/mladas-demo`
- S3 logs: `mladas-demo-logging-{region}-{account}`
