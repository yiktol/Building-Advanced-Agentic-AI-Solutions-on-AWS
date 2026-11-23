# Building Advanced Agentic Systems on AWS

Demos for a five-module course on agentic systems with Amazon Bedrock, Strands Agents and Amazon Bedrock AgentCore, plus a Streamlit app (`app/`) that runs every module in the browser.

| Path | Contents |
|---|---|
| `demos/module1-multi-agent` … `demos/module5-well-architected` | Command-line demos, per-module infrastructure (`infra/`, `scripts/deploy.sh`), tests |
| `demos/infra-agentcore` | Shared AgentCore resources: memory, evaluators, policy engine, gateway, Cedar policies, guardrail |
| `agents/techmartagent` | The TechMart support agent deployed to AgentCore Runtime with the AgentCore CLI, plus its online evaluation config and log/trace delivery |
| `app/` | Streamlit app for all modules |
| `deploy/` | EC2 + ALB + CloudFront hosting for the app, and `sync-ec2.sh` to push code to the instance |
| `scripts/` | `deploy-all.sh`, `verify.py`, `destroy-all.sh` |

## Prerequisites

- An AWS account with access to Amazon Bedrock (Claude Haiku 5.5 via the `global.anthropic.claude-haiku-5-5` inference profile) in `ap-southeast-1`.
- AWS CLI v2 with credentials for that account (`aws sso login` if you use SSO). The deploy creates IAM roles, so it needs admin-level permissions.
- Python 3.10+ with `boto3` (`pip install -r app/requirements.txt` installs everything the app and scripts need).
- Node.js 20+ and npm, the AgentCore CLI (`npm install -g @aws/agentcore@0.24.0`) and `uv`. These deploy the runtime agent.
- The account must be CDK-bootstrapped in the region (`npx cdk bootstrap aws://<account>/ap-southeast-1`); the AgentCore CLI deploys through CDK.
- Optional, for diagrams: `pip install diagrams` and Graphviz (`brew install graphviz librsvg`).

## Deploy

```bash
./scripts/deploy-all.sh            # all demo infrastructure + the runtime agent
python3 scripts/verify.py          # 34 end-to-end checks
```

`deploy-all.sh` runs these steps in order. Each is idempotent; resume with `--from <step>`.

| Step | Runs | Creates |
|---|---|---|
| `m3` | `demos/module3-security/scripts/deploy.sh` | DynamoDB tables (seeded and verified), Cognito user pool with 5 demo users, Verified Permissions, audit logging |
| `agentcore` | `demos/infra-agentcore/deploy.sh deploy all` | AgentCore memory, evaluators, policy engine, gateway (Cognito JWT authorizer, policy engine in ENFORCE mode, Lambda order tool, log/trace delivery), Cedar policies, guardrail |
| `m4` | `demos/module4-observability/scripts/deploy.sh` | Log groups, alarms + SNS, CloudWatch dashboard |
| `m5` | `demos/module5-well-architected/scripts/deploy.sh` | E-commerce tables (seeded), cost alarms |
| `agent` | `agentcore deploy` in `agents/techmartagent`, then `observability/deploy.sh` | Runtime agent with OpenTelemetry, online evaluation (5 built-in evaluators), Transaction Search, application/usage log and trace delivery |
| `app` | `deploy/deploy.sh`, `deploy/sync-ec2.sh` (only with `--with-app`) | EC2 hosting for the Streamlit app |

The order matters: the gateway validates tokens from the Module 3 Cognito pool and its Lambda reads the Module 3 orders table.

Settings:

| Variable | Default | Used for |
|---|---|---|
| `AWS_REGION` | `ap-southeast-1` | Everything |
| `ALERT_EMAIL` | `demo-alerts@example.com` | Module 4 alarm notifications (confirm the SNS subscription email) |
| `DEMO_USER_PASSWORD` | `Hero$ecure1!` | Password of the Cognito demo users |

The hosting step (`--with-app`) also needs the SSM parameters, VPC exports and certificates listed in `deploy/README.md`.

## Run

```bash
pip install -r app/requirements.txt
cd app && streamlit run Home.py        # http://localhost:8501
```

The app finds every deployed resource from CloudFormation outputs, so no configuration file is needed. Code changes reach the hosted app with `bash deploy/sync-ec2.sh` after you push to `main`.

Generate sample traces, logs and evaluation scores for the runtime agent (shows up in CloudWatch GenAI Observability and Module 4):

```bash
python3 agents/techmartagent/scripts/generate_sample_data.py --online-wait 20
```

## Tear down

```bash
./scripts/destroy-all.sh               # asks you to type the account ID
./scripts/destroy-all.sh --with-app    # also removes the EC2 hosting stack
```

This deletes the demo data. CloudWatch Transaction Search and the CDK bootstrap stack stay in place.

## Notes

- Deploy scripts write `config.env` files next to themselves for the command-line demos (`source config.env`). They hold account-specific IDs and are not committed.
- `agents/techmartagent/agentcore/aws-targets.json` and `.cli/deployed-state.json` are rewritten by `deploy-all.sh` for the account you deploy to.
- The AgentCore CLI's generated CDK app pins `aws-cdk-lib` to `2.268.0`; newer releases emit a cloud assembly schema the bundled CDK toolkit cannot read.
