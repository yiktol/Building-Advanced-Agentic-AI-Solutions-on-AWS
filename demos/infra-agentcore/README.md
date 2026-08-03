# AgentCore Infrastructure (Advanced Improvements)

CloudFormation templates for deploying Amazon Bedrock AgentCore resources that enable the advanced demo improvements.

## Templates

| Template | Resources | For Improvement |
|----------|-----------|-----------------|
| `cfn-agentcore-memory.yaml` | AgentCore Memory (shared + context) | #2 — Real AgentCore Memory |
| `cfn-agentcore-evaluator.yaml` | Custom evaluators (tool selection, compliance) | #3 — Real AgentCore Evaluations |
| `cfn-agentcore-gateway.yaml` | Gateway + MCP tool targets | #5 — MCP via AgentCore Gateway |
| `cfn-agentcore-policy.yaml` | Policy Engine + Cedar policies | #4 — AgentCore Policy |
| `cfn-bedrock-guardrail.yaml` | Bedrock Guardrail (content + PII) | #11 — Bedrock Guardrails |

## Deploy

```bash
cd demos/infra-agentcore

# Deploy all
./deploy.sh deploy all

# Deploy specific component
./deploy.sh deploy memory
./deploy.sh deploy evaluator
./deploy.sh deploy guardrail

# Load outputs
source config.env
```

## Destroy

```bash
./deploy.sh destroy all
./deploy.sh destroy memory
```

## What Gets Created

### AgentCore Memory
- **mladas-shared-agent-memory** — Multi-agent collaboration (Module 1 Part 4)
  - Namespace: `/agents/{actorId}/findings`
  - Namespace: `/agents/{actorId}/resolutions`
  - Namespace: `/sessions/{sessionId}/context`
- **mladas-context-memory** — Long-term context storage (Module 2)
  - Namespace: `/users/{actorId}/preferences`
  - Namespace: `/users/{actorId}/history`

### AgentCore Evaluators
- **mladas-tool-selection** — Evaluates correct tool usage (0.0-1.0 scale)
- **mladas-compliance-check** — Checks policy compliance (Compliant/Non-compliant)

### AgentCore Gateway
- **mladas-tool-gateway** — MCP-compatible tool gateway with targets:
  - `product-lookup` — Product details search
  - `compatibility-check` — Product compatibility
  - `order-status` — Order tracking

### AgentCore Policy Engine
- **mladas-policy-engine** — Cedar policy enforcement with:
  - Finance admin can refund (any amount)
  - Support agent can refund (< $500)
  - Engineers cannot refund (forbid)
  - Everyone can view orders

### Bedrock Guardrail
- **mladas-agent-guardrail** — Content + PII protection:
  - Content filters: hate, insults, sexual, violence, misconduct
  - PII: anonymize credit cards, SSNs, bank accounts; block passwords
  - Topic denial: unauthorized system access, malicious intent

## Usage in Code

### Memory
```python
import boto3
client = boto3.client('bedrock-agentcore', region_name='ap-southeast-1')

# Write
client.batch_create_memory_records(
    memoryId=os.environ['SharedMemoryId'],
    memoryRecords=[{'content': {'text': 'findings...'}, 'actorId': 'diag-agent', 'sessionId': 'sess-1'}]
)

# Read (semantic search)
results = client.retrieve_memory_records(
    memoryId=os.environ['SharedMemoryId'],
    namespace='/agents/{actorId}/findings',
    searchCriteria={'searchQuery': 'Wi-Fi diagnosis', 'topK': 5}
)
```

### Evaluator
```python
response = client.evaluate(
    evaluatorId=os.environ['ToolSelectionEvaluatorId'],
    evaluationInput={'text': user_query},
    evaluationTarget={'text': agent_response},
)
print(f"Score: {response['score']}, Reasoning: {response['reasoning']}")
```

### Guardrail
```python
from strands.models import BedrockModel
model = BedrockModel(
    model_id=MODEL_ID,
    guardrail_id=os.environ['GuardrailId'],
    guardrail_version=os.environ['GuardrailVersion'],
)
```
