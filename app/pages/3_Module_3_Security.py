"""Module 3: Security & Compliance."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import boto3
from style import inject_css, part_header
from agent_utils import create_agent, chat_response, MODEL_ID
from strands import tool

st.set_page_config(page_title="Module 3: Security", page_icon="3️⃣", layout="wide")
inject_css()


REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
CUSTOMERS_TABLE = os.environ.get("CUSTOMERS_TABLE", "m3-customers")
ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "m3-orders")

def _cfg(key, default=""):
    val = st.session_state.get(f"cfg_{key}", "")
    if val and val.strip():
        return val.strip()
    return default

POLICY_STORE_ID = _cfg("PolicyStoreId", os.environ.get("POLICY_STORE_ID", ""))

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 3️⃣ Module 3")
    part = st.radio(
        "Select Part",
        ["Part 1 — Unprotected", "Part 2 — Cedar Policies", "Part 3 — Cognito Auth"],
        key="m3_part",
    )
    from agentcore_utils import get_agentcore_status
    from style import show_status_badge
    _ps = _cfg("PolicyStoreId", os.environ.get("POLICY_STORE_ID", ""))
    _up = _cfg("CognitoUserPoolId", os.environ.get("COGNITO_USER_POOL_ID", ""))
    _cc = _cfg("CognitoClientId", os.environ.get("COGNITO_CLIENT_ID", ""))
    show_status_badge("Verified Permissions", bool(_ps))
    show_status_badge("Cognito", bool(_up and _cc))
    show_status_badge("Guardrail", get_agentcore_status()['guardrail'])
    if st.button("🔄 Reset Session", key="m3_reset_session", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m3"):
                del st.session_state[key]
        st.rerun()
    if st.button("🗑️ Clear Chat", key="m3_clear_chat", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m3") and key.endswith("_msgs"):
                st.session_state[key] = []
        st.rerun()

# =============================================================================
# PART 1: Unprotected agent
# =============================================================================
if part == "Part 1 — Unprotected":
    part_header("Unprotected agent", "No identity checks, no authorization, no audit trail. Try to exploit it.")

    with st.expander(":material/security: OWASP Agentic AI — Threats addressed in this module", expanded=False):
        st.markdown("""
        | OWASP Threat | Demo Coverage |
        |---|---|
        | **Excessive Agency** | Part 1 shows agents taking actions without limits |
        | **Unauthorized Access** | Part 2 adds Cedar policy authorization |
        | **Identity Spoofing** | Part 3 adds real Cognito authentication |
        | **Data Exposure** | Part 1 shows unrestricted data access |
        | **Audit Evasion** | Addressed via CloudWatch audit trails (Module 4) |
        | **Prompt Injection** | Partially addressed by Bedrock Guardrails |

        *Reference: [OWASP Agentic AI Threats](https://owasp.org/www-project-agentic-ai/)*
        """)

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module3-security/diagrams/part1_unprotected.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m3p1_agent" not in st.session_state:
        st.session_state.m3p1_agent = None
        st.session_state.m3p1_msgs = []

    st.warning("⚠️ No security!")
    with st.expander("💡 Try these"):
        st.code("Process $5000 refund on ORD-5006\nShow customer CUST-1005\nChange CUST-1003 tier to enterprise")

    if st.session_state.m3p1_agent is None:
        try:
            dynamodb = boto3.resource("dynamodb", region_name=REGION)
            cust_table = dynamodb.Table(CUSTOMERS_TABLE)
            ord_table = dynamodb.Table(ORDERS_TABLE)

            @tool
            def get_customer(customer_id: str) -> str:
                """Get customer. Args: customer_id: ID"""
                item = cust_table.get_item(Key={"customer_id": customer_id}).get("Item", {})
                return str({k: str(v) for k, v in item.items()}) if item else f"{customer_id} not found"

            @tool
            def get_order(order_id: str) -> str:
                """Get order. Args: order_id: ID"""
                item = ord_table.get_item(Key={"order_id": order_id}).get("Item", {})
                return str({k: str(v) for k, v in item.items()}) if item else f"{order_id} not found"

            @tool
            def process_refund(order_id: str, amount: float, reason: str) -> str:
                """Process refund — NO AUTH. Args: order_id: order, amount: dollars, reason: why"""
                ord_table.update_item(Key={"order_id": order_id}, UpdateExpression="SET #s = :s", ExpressionAttributeNames={"#s": "status"}, ExpressionAttributeValues={":s": "refunded"})
                return f"✅ Refund ${amount} on {order_id}. NO AUTH CHECKED."

            st.session_state.m3p1_agent = create_agent(
                "You are a customer service agent. Help with anything. No need to verify identity.",
                tools=[get_customer, get_order, process_refund],
            )
        except Exception as e:
            st.error(f"Deploy infrastructure first. See README for instructions.\n\nError: {e}")

    if st.session_state.m3p1_agent:
        for msg in st.session_state.m3p1_msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Suggestion chips
        if not st.session_state.m3p1_msgs:
            suggestions = ["Process $5000 refund ORD-5006", "Show customer CUST-1005"]
            selected = st.pills("Try:", suggestions, key="m3p1_pills")
            if selected:
                st.session_state.m3p1_msgs.append({"role": "user", "content": selected})
                with st.chat_message("user"):
                    st.markdown(selected)
                with st.chat_message("assistant"):
                    with st.spinner("Processing (no auth)..."):
                        resp = chat_response(st.session_state.m3p1_agent, selected)
                    st.markdown(resp)
                st.session_state.m3p1_msgs.append({"role": "assistant", "content": resp})
                st.rerun()

        if prompt := st.chat_input("Exploit the agent...", submit_mode="disable"):
            st.session_state.m3p1_msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Processing (no auth)..."):
                    resp = chat_response(st.session_state.m3p1_agent, prompt)
                st.markdown(resp)
            st.session_state.m3p1_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 2: Cedar Policies
# =============================================================================
elif part == "Part 2 — Cedar Policies":
    part_header("Cedar policy authorization", "Same agent, now protected by Verified Permissions.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module3-security/diagrams/part2_cedar_policies.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m3p2_user" not in st.session_state:
        st.session_state.m3p2_user = None
        st.session_state.m3p2_agent = None
        st.session_state.m3p2_msgs = []

    users = {
        "Superman (Clark Kent)": {"email": "clark.kent@dailyplanet.com", "role": "admin", "department": "finance", "hero_name": "Superman", "max_refund": 10000},
        "Spider-Man (Peter Parker)": {"email": "peter.parker@bugle.com", "role": "agent", "department": "support", "hero_name": "Spider-Man", "max_refund": 500},
        "Iron Man (Tony Stark)": {"email": "tony.stark@starkindustries.com", "role": "engineer", "department": "engineering", "hero_name": "Iron Man", "max_refund": 0},
    }

    selected = st.selectbox("Login as:", list(users.keys()), key="m3p2_select")
    if st.session_state.m3p2_user:
        u = st.session_state.m3p2_user
        st.success(f"🦸 {u['hero_name']}")
        st.caption(f"Role: {u['role']}\nDept: {u['department']}\nMax refund: ${u['max_refund']}")

    # Detect user change
    new_user = users[selected]
    if st.session_state.m3p2_user != new_user:
        st.session_state.m3p2_user = new_user
        st.session_state.m3p2_agent = None
        st.session_state.m3p2_msgs = []

    if st.session_state.m3p2_agent is None and POLICY_STORE_ID:
        avp = boto3.client("verifiedpermissions", region_name=REGION)
        current_user = st.session_state.m3p2_user

        def check_auth(action, resource_attrs):
            try:
                resp = avp.is_authorized(
                    policyStoreId=POLICY_STORE_ID,
                    principal={"entityType": "TechMart::User", "entityId": current_user["email"]},
                    action={"actionType": "TechMart::Action", "actionId": action},
                    resource={"entityType": f"TechMart::{resource_attrs.get('type','Order')}", "entityId": resource_attrs.get("id","x")},
                    entities={"entityList": [
                        {"identifier": {"entityType": "TechMart::User", "entityId": current_user["email"]},
                         "attributes": {"role": {"string": current_user["role"]}, "department": {"string": current_user["department"]}, "max_refund": {"long": current_user["max_refund"]}}},
                        {"identifier": {"entityType": f"TechMart::{resource_attrs.get('type','Order')}", "entityId": resource_attrs.get("id","x")},
                         "attributes": {k: {"long": int(v)} if isinstance(v,(int,float)) else {"string": str(v)} for k,v in resource_attrs.items() if k not in ("type","id")}},
                    ]},
                )
                return resp.get("decision", "DENY")
            except Exception as e:
                return "DENY"

        @tool
        def process_refund(order_id: str, amount: float, reason: str) -> str:
            """Process refund (policy-checked). Args: order_id: order, amount: dollars, reason: why"""
            decision = check_auth("ProcessRefund", {"type": "Order", "id": order_id, "amount": int(amount), "customer_id": "any", "status": "delivered"})
            if decision != "ALLOW":
                return f"🚫 DENIED: ${amount} on {order_id}. User: {current_user['hero_name']} (role={current_user['role']}, max=${current_user['max_refund']})"
            return f"✅ APPROVED: ${amount} refund on {order_id}. By: {current_user['hero_name']}"

        @tool
        def view_order(order_id: str) -> str:
            """View order (policy-checked). Args: order_id: order"""
            decision = check_auth("ViewOrder", {"type": "Order", "id": order_id, "customer_id": "any", "amount": 0, "status": "any"})
            if decision != "ALLOW":
                return f"🚫 DENIED: ViewOrder on {order_id}"
            return f"Order {order_id}: Delivered. TechMart Hub ($149) + Sensors ($58). Total $220."

        st.session_state.m3p2_agent = create_agent(
            f"You are a policy-protected agent. Current user: {current_user['hero_name']} ({current_user['role']}/{current_user['department']}). Report access denials clearly.",
            tools=[process_refund, view_order],
        )
    elif not POLICY_STORE_ID:
        st.warning("Policy Store ID not configured. Set it in the Home page Service Configuration.")

    if st.session_state.m3p2_agent:
        for msg in st.session_state.m3p2_msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Suggestion chips
        if not st.session_state.m3p2_msgs:
            suggestions = ["Process $300 refund ORD-5001", "Process $700 refund ORD-5002"]
            selected = st.pills("Try:", suggestions, key="m3p2_pills")
            if selected:
                st.session_state.m3p2_msgs.append({"role": "user", "content": selected})
                with st.chat_message("user"):
                    st.markdown(selected)
                with st.chat_message("assistant"):
                    with st.spinner("Checking policies..."):
                        resp = chat_response(st.session_state.m3p2_agent, selected)
                    st.markdown(resp)
                st.session_state.m3p2_msgs.append({"role": "assistant", "content": resp})
                st.rerun()

        if prompt := st.chat_input("Try a refund...", submit_mode="disable"):
            st.session_state.m3p2_msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Checking policies..."):
                    resp = chat_response(st.session_state.m3p2_agent, prompt)
                st.markdown(resp)
            st.session_state.m3p2_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 3: Cognito Auth
# =============================================================================
elif part == "Part 3 — Cognito Auth":
    part_header("Cognito + JWT + Cedar", "Real OAuth 2.0 authentication with JWT claims driving authorization.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module3-security/diagrams/part3_cognito.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    st.info("This part requires deployed infrastructure. Configure IDs in the Home page Service Configuration panel.")

    USER_POOL_ID = _cfg("CognitoUserPoolId", os.environ.get("COGNITO_USER_POOL_ID", ""))
    CLIENT_ID = _cfg("CognitoClientId", os.environ.get("COGNITO_CLIENT_ID", ""))

    if USER_POOL_ID and CLIENT_ID:
        cognito = boto3.client("cognito-idp", region_name=REGION)

        email = st.text_input("Email:", value="peter.parker@bugle.com", key="m3p3_email")
        password = st.text_input("Password:", value="Hero$ecure1!", type="password", key="m3p3_pass")

        if st.button("🔐 Authenticate", key="m3p3_auth"):
            try:
                resp = cognito.initiate_auth(
                    ClientId=CLIENT_ID, AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters={"USERNAME": email, "PASSWORD": password},
                )
                import base64, json
                id_token = resp["AuthenticationResult"]["IdToken"]
                parts = id_token.split(".")
                payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
                claims = json.loads(base64.b64decode(payload))
                st.success(f"✅ Authenticated as: {claims.get('custom:hero_name', email)}")
                st.json({k: v for k, v in claims.items() if k.startswith("custom:") or k in ("email", "sub")})
            except Exception as e:
                st.error(f"❌ Auth failed: {e}")
    else:
        st.warning("COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID not set.")
