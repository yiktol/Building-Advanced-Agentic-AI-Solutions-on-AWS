"""
Building Advanced Agentic Systems on AWS — Lab Application
Main entry point with modern UI/UX.
"""

import streamlit as st
import boto3
from botocore.exceptions import ClientError

st.set_page_config(
    page_title="Building Advanced Agentic Systems on AWS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Auto-detect CloudFormation Stack Outputs ---
@st.cache_data(ttl=300)
def get_cfn_outputs():
    """Derive service configuration from infra-agentcore and module3 CloudFormation stack outputs."""
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
        cfn = boto3.client("cloudformation")
        for stack_name in stacks_to_check:
            try:
                resp = cfn.describe_stacks(StackName=stack_name)
                for output in resp["Stacks"][0].get("Outputs", []):
                    outputs[output["OutputKey"]] = output["OutputValue"]
            except ClientError:
                # Stack doesn't exist or isn't accessible
                continue
    except Exception:
        pass

    # Hardcoded fallback if CFN lookup returns empty
    if not outputs:
        outputs = {
            "SharedMemoryId": "mladas_shared_memory-FnBIrUFMzJ",
            "ToolSelectionEvaluatorId": "arn:aws:bedrock-agentcore:ap-southeast-1:875692608981:evaluator/mladas_tool_selection-jYBteNHyI9",
            "ComplianceEvaluatorId": "arn:aws:bedrock-agentcore:ap-southeast-1:875692608981:evaluator/mladas_compliance_check-UsUxd02sK8",
            "GatewayId": "mladas-tool-gateway-3tz53bxvi7",
            "GatewayArn": "arn:aws:bedrock-agentcore:ap-southeast-1:875692608981:gateway/mladas-tool-gateway-3tz53bxvi7",
            "PolicyEngineId": "mladas_policy_engine-rnk8ps49yd",
            "GuardrailId": "mz9uffp9swwy",
            "GuardrailVersion": "1",
            "UserPoolId": "ap-southeast-1_E0sMjmTN0",
            "UserPoolClientId": "330l8sbjpagntgjqtm2bcpau63",
            "PolicyStoreId": "UaLcNnxRby5abt23mN5LCm",
        }

    return outputs

# --- Custom CSS for modern styling ---
st.markdown("""
<style>
    /* Hide default UI elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Modern font and spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Module cards */
    .module-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        margin-bottom: 16px;
        transition: transform 0.2s;
    }
    .module-card:hover {
        transform: translateY(-2px);
    }
    .module-card h3 {
        margin: 0 0 8px 0;
        color: white;
    }
    .module-card p {
        margin: 0;
        opacity: 0.9;
        font-size: 14px;
    }

    /* Hero section */
    .hero {
        text-align: center;
        padding: 40px 20px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 20px;
        color: white;
        margin-bottom: 32px;
    }
    .hero h1 {
        font-size: 2.2rem;
        margin-bottom: 12px;
        color: white;
    }
    .hero p {
        font-size: 1.1rem;
        opacity: 0.85;
        max-width: 700px;
        margin: 0 auto;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Hero Section ---
st.markdown("""
<div class="hero">
    <h1>🤖 Building Advanced Agentic Systems on AWS</h1>
    <p>Interactive labs for multi-agent architecture, context engineering,
    security, observability, and Well-Architected practices.</p>
</div>
""", unsafe_allow_html=True)

# --- Service Configuration (top of page) ---
with st.expander("⚙️ Service Configuration — Connect real AWS services", expanded=True):
    st.caption("Enter resource IDs to connect real AWS services. Leave empty for local fallback.")

    # Auto-detect from CloudFormation
    cfn_outputs = get_cfn_outputs()
    if cfn_outputs:
        detected = ", ".join(cfn_outputs.keys())
        st.success(f"🔍 Auto-detected from CloudFormation stacks: {detected}")

    # --- Model Selection ---
    st.markdown("**:material/smart_toy: Model Configuration**")
    mcol1, mcol2 = st.columns(2)
    generation_models = {
        "Nova Micro": "amazon.nova-micro-v1:0",
        "Nova Lite": "amazon.nova-lite-v1:0",
        "Nova Pro": "amazon.nova-pro-v1:0",
        "Claude Sonnet 4 (APAC)": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "Claude Sonnet 4.5 (Global)": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "Claude Haiku 4.5 (Global)": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    }
    judge_models = {
        "Nova Pro": "amazon.nova-pro-v1:0",
        "Claude Sonnet 4 (APAC)": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "Claude Haiku 4.5 (Global)": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    }
    with mcol1:
        gen_choice = st.selectbox(
            "Generation model",
            list(generation_models.keys()),
            index=0,
            key="cfg_generation_model_name",
            help="Model used for all agent responses",
        )
        st.session_state["cfg_MODEL_ID"] = generation_models[gen_choice]
    with mcol2:
        judge_choice = st.selectbox(
            "Judge model (evaluation)",
            list(judge_models.keys()),
            index=0,
            key="cfg_judge_model_name",
            help="Model used for LLM-as-judge evaluation scoring",
        )
        st.session_state["cfg_JUDGE_MODEL_ID"] = judge_models[judge_choice]

    # Inference parameters
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        temp_val = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1, key="cfg_temp_slider", help="Controls randomness. Lower = more focused, higher = more creative.")
        st.session_state["cfg_temperature"] = temp_val
    with pcol2:
        max_tok_val = st.slider("Max tokens", min_value=256, max_value=4096, value=2048, step=256, key="cfg_max_tokens_slider", help="Maximum response length in tokens.")
        st.session_state["cfg_max_tokens"] = max_tok_val
    st.caption(f"Generation: `{generation_models[gen_choice]}` | Judge: `{judge_models[judge_choice]}` | Temp: {temp_val} | Max: {max_tok_val}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**:material/memory: AgentCore Memory**")
        st.caption("Enables shared memory across agents (Module 1 Part 4). Provides semantic search retrieval for cross-agent collaboration.")
        st.text_input("Memory ID", key="cfg_SharedMemoryId",
                      value=cfn_outputs.get("SharedMemoryId", ""),
                      placeholder="mladas_shared_memory-xxx")
        st.markdown("**:material/shield: Bedrock Guardrail**")
        st.caption("Protects all agent inputs/outputs with content filtering and PII detection. Applied globally to all modules.")
        st.text_input("Guardrail ID", key="cfg_GuardrailId",
                      value=cfn_outputs.get("GuardrailId", ""),
                      placeholder="7cv8wi8poz7f")
        st.text_input("Guardrail Version", key="cfg_GuardrailVersion",
                      value=cfn_outputs.get("GuardrailVersion", "DRAFT"))
    with c2:
        st.markdown("**:material/analytics: AgentCore Evaluator**")
        st.caption("Replaces local LLM-as-judge with real AgentCore Evaluations API (Module 4 Part 3). Use built-in IDs like `Builtin.Correctness`.")
        st.text_input("Evaluator ID", key="cfg_ToolSelectionEvaluatorId",
                      value=cfn_outputs.get("ToolSelectionEvaluatorId", ""),
                      placeholder="Builtin.Correctness")
        st.markdown("**:material/policy: AgentCore Policy**")
        st.caption("Enables Cedar policy authorization for agent tool calls (Module 3 Part 2). Controls refund limits per role via AgentCore Policy Engine.")
        st.text_input("Policy Engine ID", key="cfg_PolicyStoreId",
                      value=cfn_outputs.get("PolicyStoreId", cfn_outputs.get("PolicyEngineId", "")),
                      placeholder="mladas_policy_engine-xxx")
    with c3:
        st.markdown("**:material/person: Amazon Cognito**")
        st.caption("Enables real OAuth 2.0 authentication with JWT tokens (Module 3 Part 3). Users authenticate and claims drive authorization.")
        st.text_input("Cognito User Pool ID", key="cfg_CognitoUserPoolId",
                      value=cfn_outputs.get("UserPoolId", ""),
                      placeholder="ap-southeast-1_abc123")
        st.text_input("Cognito Client ID", key="cfg_CognitoClientId",
                      value=cfn_outputs.get("UserPoolClientId", ""),
                      placeholder="7eq16iqg...")
        st.markdown("**:material/hub: AgentCore Gateway**")
        st.caption("MCP-compatible tool gateway for centralized tool access (Module 1 Part 3).")
        st.text_input("Gateway ID", key="cfg_GatewayId",
                      value=cfn_outputs.get("GatewayId", ""),
                      placeholder="mladas-tool-gateway-xxx")
    # Status
    try:
        from agentcore_utils import get_agentcore_status
        status = get_agentcore_status()
        status_text = " | ".join([f"{'🟢' if v else '⚪'} {k.title()}" for k, v in status.items() if k != "region"])
        st.caption(f"Status: {status_text} | Region: {status['region']}")
    except Exception:
        st.caption("⚪ AgentCore not configured")

# --- Module Grid ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📚 Course Modules")
    modules = [
        ("1️⃣", "Multi-Agent Architecture", "Orchestration patterns, agent-as-tool, shared memory"),
        ("2️⃣", "Context Engineering", "Prompt caching, conversation managers, context isolation"),
        ("3️⃣", "Security & Compliance", "Cognito auth, AgentCore Policy (Cedar), VPC, audit trails"),
        ("4️⃣", "Observability", "Tracing, metrics, loop detection, LLM evaluation"),
        ("5️⃣", "Well-Architected", "Ops excellence, reliability, cost optimization"),
    ]
    for icon, title, desc in modules:
        st.markdown(f"""
        <div class="module-card">
            <h3>{icon} {title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("### 🚀 Quick Start")
    st.info("👈 Select a module from the sidebar to begin.")

    st.markdown("### 🛠️ Tech Stack")
    st.markdown("""
    - **Strands Agents SDK** — Agent orchestration
    - **Amazon Bedrock** — Foundation models (Claude Sonnet 4)
    - **Amazon Bedrock AgentCore** — Memory, Gateway, Policy Engine, Evaluators
    - **Amazon Cognito** — Authentication (OAuth 2.0)
    - **Amazon DynamoDB** — Data persistence
    - **Amazon CloudWatch** — Metrics, alarms, dashboards
    - **Amazon VPC** — Private connectivity
    """)

    st.markdown("### 🦸 Test Users (Module 3)")
    st.code("""
Superman (Clark Kent) — admin/finance
Batman (Bruce Wayne) — security_lead
Spider-Man (Peter Parker) — agent/support
Wonder Woman (Diana Prince) — manager/ops
Iron Man (Tony Stark) — engineer (no refund)

Password: Hero$ecure1!
    """, language="text")
