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
| `sync-ec2.sh` | Sync code + .env to running EC2 via SSM (git pull + restart) |
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

## Naming Convention

All resources use `mladas-demo` prefix to avoid conflicts with other stacks:
- Stack: `mladas-demo-ec2`
- ALB: `lb-mladas-demo`
- ASG: `mladas-demo-asg`
- Service: `mladas-demo.service`
- Secret: `cloudfront/mladas-demo`
- S3 logs: `mladas-demo-logging-{region}-{account}`
