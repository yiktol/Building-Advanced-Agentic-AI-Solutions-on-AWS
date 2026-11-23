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
    """Load CFN outputs and cache them at module level.

    An empty result (nothing deployed yet) is only cached for 30 seconds, so a
    stack deployed while the app is running gets picked up without a restart.
    """
    global _cfn_cache, _cfn_cache_time
    import time
    now = time.time()
    if _cfn_cache is not None and (_cfn_cache or now - _cfn_cache_time < 30):
        return _cfn_cache
    _cfn_cache = _load_cfn_outputs()
    _cfn_cache_time = now
    return _cfn_cache


_cfn_cache = None
_cfn_cache_time = 0.0


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
        "m4-demo-observability",
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

    # No hardcoded fallback: if detection fails, return empty so status badges
    # honestly show services as unconfigured rather than pointing at deleted
    # resources. Users can still set IDs via the Home page / env vars.
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
        from agent_utils import make_model
        from strands import Agent as _Agent
        judge_model = make_model("judge")
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


# =============================================================================
# AGENTCORE GATEWAY + POLICY ENGINE (Module 3)
# =============================================================================
# Authorization is NOT evaluated in this app. Tool calls go to the AgentCore
# Gateway with the caller's Cognito JWT; the Gateway validates the token,
# turns its claims into principal tags and asks the attached Policy Engine
# (Cedar) for the decision. The app only reports what the Gateway returns.

DEMO_USER_PASSWORD = os.environ.get("DEMO_USER_PASSWORD", "Hero$ecure1!")


def gateway_mcp_url() -> str:
    """MCP endpoint of the policy-enforcing gateway, or '' if not deployed."""
    base = _get_config("GatewayUrl")
    return base.rstrip("/") + "/mcp" if base else ""


def cognito_id_token(email: str, password: str = "") -> str:
    """Authenticate a demo user against Cognito and return the ID token (JWT)."""
    import boto3
    client_id = _get_config("UserPoolClientId") or _get_config("CognitoClientId")
    if not client_id:
        raise RuntimeError("Cognito client ID not configured (deploy Module 3 infrastructure)")
    resp = boto3.client("cognito-idp", region_name=REGION).initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": email, "PASSWORD": password or DEMO_USER_PASSWORD},
    )
    return resp["AuthenticationResult"]["IdToken"]


def call_gateway_tool(id_token: str, tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool through the AgentCore Gateway as the JWT's user.

    Returns {"decision": "ALLOW" | "DENY" | "ERROR", "message": str, "policy": str}.
    "policy" is the matching policy name when the engine reports one (forbid hits).
    """
    import re
    import urllib.request
    import urllib.error

    url = gateway_mcp_url()
    if not url:
        return {"decision": "ERROR", "message": "AgentCore Gateway URL not configured (deploy demos/infra-agentcore)", "policy": ""}
    body = json.dumps({
        "jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {id_token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        return {"decision": "ERROR", "message": f"Gateway rejected the request (HTTP {e.code}): {detail}", "policy": ""}
    except Exception as e:
        return {"decision": "ERROR", "message": f"Gateway call failed: {e}", "policy": ""}

    err = data.get("error")
    if err:
        msg = err.get("message", "")
        if "denied" in msg.lower():
            m = re.search(r"denied due to ([\w\-]+?)(?:-[a-z0-9_]{10})?\]", msg)
            return {"decision": "DENY", "message": msg, "policy": m.group(1) if m else ""}
        return {"decision": "ERROR", "message": msg, "policy": ""}
    result = data.get("result", {})
    text = " ".join(c.get("text", "") for c in result.get("content", []))
    if result.get("isError"):
        return {"decision": "DENY" if "denied" in text.lower() else "ERROR", "message": text, "policy": ""}
    return {"decision": "ALLOW", "message": text, "policy": ""}
