# Demo Improvements — Implementation Notes

## Implemented ✅

| # | Improvement | Status |
|---|-------------|--------|
| 6 | TOON format in Module 2 Part 5 | ✅ Added third radio option with pipe-delimited format |
| 9 | Architecture diagrams in Streamlit app | ✅ Expander with st.image() in each part |
| 12 | Clickable suggestion chips (st.pills) | ✅ All chat parts have suggestion pills when empty |

## Requires AgentCore Provisioning 🔧

These improvements require creating AgentCore resources (Memory IDs, Evaluator IDs, Gateway, etc.) via the AWS console or CDK. They're documented here for instructors who want to upgrade the demos.

### #1 — A2A Protocol Demo (Module 1)

**What:** Add Part 5 showing peer-to-peer agent communication via A2A protocol.

**How to implement:**
```python
# Agent Card (published at /.well-known/agent.json)
agent_card = {
    "name": "billing-agent",
    "url": "https://agent-endpoint/a2a",
    "capabilities": ["process_refund", "check_charge"],
    "authentication": {"type": "bearer"}
}

# A2A Client sending a task
from strands_agents.a2a import A2AClient
client = A2AClient(agent_card_url="https://remote-agent/.well-known/agent.json")
task = client.send_task({"prompt": "Process refund for order ORD-5001"})
```

**Prerequisites:** Two AgentCore Runtime instances with HTTP endpoints.

### #2 — Real AgentCore Memory (Module 1 Part 4)

**What:** Replace the simulated `SharedMemoryStore` with actual AgentCore Memory API.

**How to implement:**
```python
import boto3
client = boto3.client('bedrock-agentcore', region_name='ap-southeast-1')

# Create memory records
client.batch_create_memory_records(
    memoryId='YOUR_MEMORY_ID',
    memoryRecords=[{
        'content': {'text': 'Diagnosis: Hub v2.1.3 has Wi-Fi bug'},
        'actorId': 'diagnostic-agent',
        'sessionId': 'session-001',
    }]
)

# Retrieve with semantic search
results = client.retrieve_memory_records(
    memoryId='YOUR_MEMORY_ID',
    namespace='/agents/{actorId}/findings',
    searchCriteria={
        'searchQuery': 'What was the diagnosis for the Wi-Fi issue?',
        'topK': 5
    }
)
```

**Prerequisites:** Create a Memory resource via AWS Console or CDK:
```bash
aws bedrock-agentcore create-memory --memory-name "demo-shared-memory"
```

### #3 — Real AgentCore Evaluations (Module 4 Part 3)

**What:** Replace homegrown LLM-as-judge with AgentCore Evaluations API.

**How to implement:**
```python
import boto3
client = boto3.client('bedrock-agentcore', region_name='ap-southeast-1')

# On-demand evaluation using built-in evaluator
response = client.evaluate(
    evaluatorId='Builtin.Correctness',
    evaluationInput={'text': 'My Hub keeps dropping Wi-Fi. Firmware v2.1.3.'},
    evaluationTarget={'text': agent_response},
)
score = response['score']
reasoning = response['reasoning']
```

**Prerequisites:** AgentCore Evaluations is available in preview. No resource creation needed for built-in evaluators.

### #4 — AgentCore Policy (Module 3)

**What:** Use AgentCore Policy instead of direct Verified Permissions calls.

**Implementation Note:** AgentCore Policy wraps Verified Permissions with:
- Natural language → Cedar conversion
- JWT claims → Entity Store tags (automatic)
- Gateway-level enforcement

The current implementation using Verified Permissions directly is functionally equivalent and demonstrates the same Cedar concepts from the slides. AgentCore Policy adds the Gateway integration layer which is more relevant for Runtime-hosted agents.

**When to upgrade:** When deploying agents on AgentCore Runtime.

### #5 — MCP via AgentCore Gateway (Module 1/2)

**What:** Register tools via AgentCore Gateway for MCP-compatible discovery.

**How to implement:**
```python
# Register a tool target in Gateway
# Then agents discover tools via semantic search:
from bedrock_agentcore.gateway import GatewayClient
gateway = GatewayClient(gateway_id='YOUR_GATEWAY_ID')
tools = gateway.search_tools("product lookup and pricing")
```

**Prerequisites:** Create an AgentCore Gateway instance and register tool targets.

### #7 — Real ADOT Instrumentation (Module 4 Part 1)

**What:** Replace manual span writing with actual OpenTelemetry SDK + ADOT collector.

**How to implement:**
```python
# For non-Runtime agents:
import os
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'https://otlp.ap-southeast-1.amazonaws.com'
os.environ['OTEL_SERVICE_NAME'] = 'demo-agent'

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("agent_invocation"):
    response = agent(prompt)
```

**Prerequisites:** `pip install opentelemetry-sdk opentelemetry-exporter-otlp` + CloudWatch Transaction Search enabled.

### #8 — Strands invocation_state (Module 5 Part 2)

**What:** Use `invocation_state` for shared state in the Graph/Swarm patterns.

**How to implement:**
```python
from strands import Agent, tool, ToolContext

@tool(context=True)
def check_customer(customer_id: str, tool_context: ToolContext) -> str:
    """Check customer with shared context."""
    debug = tool_context.invocation_state.get("debug_mode", False)
    user_id = tool_context.invocation_state.get("user_id")
    # Use shared state...

shared_state = {"user_id": "user123", "debug_mode": True}

# Works with Graph and Swarm patterns
from strands.multiagent import Graph
result = graph("Process customer request", invocation_state=shared_state)
```

**Note:** This is already in the CLI demo (`part4_reliability.py`) conceptually. The Streamlit app could expose `invocation_state` values as sidebar inputs.

### #10 — Responsible AI Dimensions (Module 5 Part 2)

**What:** Extend the WA reviewer to include the 8 Responsible AI dimensions from the course slides.

**Dimensions:**
1. Controllability
2. Privacy & Security
3. Safety
4. Fairness
5. Veracity & Robustness
6. Explainability
7. Transparency
8. Governance

**Implementation:** Add these as additional assessment criteria in the `PILLARS` list in `part2_wa_review.py`.

### #11 — Bedrock Guardrails (Module 3)

**What:** Add guardrail protection on agent inputs/outputs.

**How to implement:**
```python
from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id=MODEL_ID,
    guardrail_id="YOUR_GUARDRAIL_ID",
    guardrail_version="DRAFT",
)
agent = Agent(model=model, system_prompt="...")
```

**Prerequisites:** Create a Bedrock Guardrail via console with policies for:
- Content filters (hate, violence, sexual content)
- PII redaction
- Topic denial (restrict agent to business topics only)
