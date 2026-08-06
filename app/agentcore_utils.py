"""
AgentCore API utilities with fallback to local simulation.

Reads config from:
1. st.session_state (sidebar input in Streamlit app)
2. Environment variables (from deployed CFN config.env)
3. Falls back to local in-memory implementations if neither is set.
"""

import os
import json
import uuid
from datetime import datetime


def _get_config(key: str, default: str = "") -> str:
    """Get config value from session_state first, then env var, then CFN outputs."""
    try:
        import streamlit as st
        val = st.session_state.get(f"cfg_{key}", "")
        if val and val.strip():
            return val.strip()
    except Exception:
        pass
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val
    # Fallback: check CFN stack outputs
    cfn_vals = _get_cfn_config_cached()
    return cfn_vals.get(key, default)


def _get_cfn_config_cached() -> dict:
    """Load CFN outputs once and cache in module-level variable."""
    global _cfn_cache
    if _cfn_cache is not None:
        return _cfn_cache
    _cfn_cache = _load_cfn_outputs()
    return _cfn_cache


_cfn_cache = None


def _load_cfn_outputs() -> dict:
    """Query CloudFormation stacks for service configuration outputs."""
    stacks_to_check = [
        "mladas-agentcore-memory",
        "mladas-agentcore-evaluator",
        "mladas-agentcore-gateway",
        "mladas-agentcore-policy",
        "mladas-agentcore-guardrail",
        "m3-demo-cognito",
        "m3-demo-verified-permissions",
    ]
    outputs = {}
    try:
        import boto3
        from botocore.exceptions import ClientError
        cfn = boto3.client("cloudformation", region_name=REGION)
        for stack_name in stacks_to_check:
            try:
                resp = cfn.describe_stacks(StackName=stack_name)
                for output in resp["Stacks"][0].get("Outputs", []):
                    outputs[output["OutputKey"]] = output["OutputValue"]
            except (ClientError, Exception):
                continue
    except Exception:
        pass

    # Hardcoded fallback
    if not outputs:
        outputs = {
            "SharedMemoryId": "mladas_shared_memory-FnBIrUFMzJ",
            "ToolSelectionEvaluatorId": "arn:aws:bedrock-agentcore:ap-southeast-1:875692608981:evaluator/mladas_tool_selection-jYBteNHyI9",
            "GatewayId": "mladas-tool-gateway-3tz53bxvi7",
            "PolicyEngineId": "mladas_policy_engine-rnk8ps49yd",
            "GuardrailId": "",
            "GuardrailVersion": "",
            "UserPoolId": "ap-southeast-1_E0sMjmTN0",
            "UserPoolClientId": "330l8sbjpagntgjqtm2bcpau63",
            "PolicyStoreId": "UaLcNnxRby5abt23mN5LCm",
        }

    return outputs


REGION = os.environ.get("AWS_REGION", "ap-southeast-1")


# =============================================================================
# MEMORY
# =============================================================================

class AgentCoreMemory:
    """Wrapper for AgentCore Memory with local fallback."""

    def __init__(self, memory_id: str = None):
        self.memory_id = memory_id or _get_config("SharedMemoryId")
        self.use_real = bool(self.memory_id)
        self._local_store: list[dict] = []
        self._client = None

        if self.use_real:
            try:
                import boto3
                self._client = boto3.client("bedrock-agentcore", region_name=REGION)
            except Exception:
                self.use_real = False

    def write(self, actor_id: str, content: str, session_id: str = "default") -> dict:
        """Write a memory record."""
        import uuid
        record = {
            "actor_id": actor_id,
            "content": content,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if self.use_real:
            try:
                from datetime import timezone
                self._client.batch_create_memory_records(
                    memoryId=self.memory_id,
                    records=[{
                        "requestIdentifier": str(uuid.uuid4()),
                        "namespaces": [f"/agents/{actor_id}/findings"],
                        "content": {"text": content},
                        "timestamp": datetime.now(timezone.utc),
                    }],
                    clientToken=str(uuid.uuid4()),
                )
                record["source"] = "agentcore"
            except Exception as e:
                record["source"] = f"local (API error: {e})"
                self._local_store.append(record)
        else:
            record["source"] = "local"
            self._local_store.append(record)

        return record

    def retrieve(self, query: str, top_k: int = 5, namespace: str = None) -> list[dict]:
        """Retrieve memory records via semantic search."""
        if self.use_real:
            try:
                ns = namespace or "/agents/diagnostic-agent/findings"
                resp = self._client.retrieve_memory_records(
                    memoryId=self.memory_id,
                    namespace=ns,
                    searchCriteria={"searchQuery": query, "topK": top_k},
                )
                return [
                    {"content": r.get("content", {}).get("text", ""), "score": r.get("score", 0)}
                    for r in resp.get("memoryRecordSummaries", [])
                ]
            except Exception:
                pass

        # Local fallback: simple keyword matching
        results = []
        query_lower = query.lower()
        for record in self._local_store:
            content = record.get("content", "")
            if any(word in content.lower() for word in query_lower.split()):
                results.append({"content": content, "score": 0.8})
        return results[:top_k]

    def read_all(self) -> list[dict]:
        """Read all records (local store for audit trail display)."""
        return self._local_store

    @property
    def is_real(self) -> bool:
        return self.use_real


# =============================================================================
# EVALUATOR
# =============================================================================

class AgentCoreEvaluator:
    """Wrapper for AgentCore Evaluations with LLM-as-judge fallback."""

    def __init__(self, evaluator_id: str = None):
        self.evaluator_id = evaluator_id or _get_config("ToolSelectionEvaluatorId")
        self.use_real = bool(self.evaluator_id)
        self._client = None

        if self.use_real:
            try:
                import boto3
                self._client = boto3.client("bedrock-agentcore", region_name=REGION)
            except Exception:
                self.use_real = False

    def evaluate(self, query: str, response: str) -> dict:
        """Evaluate an agent response. Returns {score, reasoning, source}."""
        if self.use_real:
            try:
                resp = self._client.evaluate(
                    evaluatorId=self.evaluator_id,
                    evaluationInput={"text": query},
                    evaluationTarget={"text": response},
                )
                return {
                    "score": float(resp.get("score", 0.5)),
                    "reasoning": resp.get("reasoning", ""),
                    "source": "agentcore",
                }
            except Exception as e:
                return {"score": 0.5, "reasoning": f"AgentCore API error: {e}", "source": "error"}

        # Local fallback: use LLM-as-judge
        from agent_utils import _get_judge_model_id
        from strands.models import BedrockModel as _BM
        from strands import Agent as _Agent
        judge_model = _BM(model_id=_get_judge_model_id())
        judge = _Agent(
            model=judge_model,
            system_prompt="You are a quality judge. Score responses 0.0-1.0. Return ONLY JSON: {\"score\": X, \"reasoning\": \"...\"}",
        )
        result = str(judge(f"Query: {query}\nResponse: {response}\nScore this."))
        try:
            if "{" in result:
                parsed = json.loads(result[result.index("{"):result.rindex("}") + 1])
                return {"score": float(parsed.get("score", 0.5)), "reasoning": parsed.get("reasoning", ""), "source": "local-llm-judge"}
        except Exception:
            pass
        return {"score": 0.5, "reasoning": "Parse error", "source": "local-fallback"}


















    @property
    def is_real(self) -> bool:
        return self.use_real


# =============================================================================
# GUARDRAIL
# =============================================================================

def get_guardrail_config() -> dict:
    """Get guardrail config for BedrockModel if deployed, otherwise empty."""
    guardrail_id = _get_config("GuardrailId")
    guardrail_version = _get_config("GuardrailVersion")
    if guardrail_id and guardrail_version:
        return {
            "guardrail_id": guardrail_id,
            "guardrail_version": guardrail_version,
        }
    return {}


# =============================================================================
# STATUS HELPER
# =============================================================================

def get_agentcore_status() -> dict:
    """Check which AgentCore features are available."""
    return {
        "memory": bool(_get_config("SharedMemoryId")),
        "evaluator": bool(_get_config("ToolSelectionEvaluatorId")),
        "guardrail": bool(_get_config("GuardrailId")),
        "cognito": bool(_get_config("UserPoolId") or _get_config("CognitoUserPoolId")),
        "policy_store": bool(_get_config("PolicyStoreId") or _get_config("PolicyEngineId")),
        "gateway": bool(_get_config("GatewayId")),
        "region": REGION,
    }
