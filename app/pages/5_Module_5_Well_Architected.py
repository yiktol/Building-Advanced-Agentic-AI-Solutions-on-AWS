"""Module 5: Well-Architected."""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from style import inject_css, part_header
from agent_utils import create_agent, chat_response, chat_response_with_metrics, MODEL_ID
from strands import Agent, tool
from strands.models import BedrockModel

st.set_page_config(page_title="Module 5: Well-Architected", page_icon="5️⃣", layout="wide")
inject_css()


def _do_cost_query(query, tiering_enabled):
    """Handle a cost-optimization query with model tiering."""
    complex_words = ["compare", "analyze", "recommend", "explain", "strategy", "trade-off", "pros and cons"]
    is_complex = any(w in query.lower() for w in complex_words) or len(query.split()) > 15
    tier = "economy" if (tiering_enabled and not is_complex) else "premium"

    st.session_state.m5p3_msgs.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner(f"Processing ({tier} tier)..."):
            # Use different models based on tier
            if tier == "economy":
                model = BedrockModel(model_id="apac.amazon.nova-micro-v1:0", max_tokens=1024)
            else:
                model = BedrockModel(model_id=MODEL_ID, max_tokens=2048)
            agent = Agent(model=model, system_prompt="You are a TechMart assistant. Pro 15 $799, Air $599, Titan $1299, Hub $149. Be concise.")
            import time as _t
            _s = _t.time()
            result = agent(query)
            wall_time = int((_t.time() - _s) * 1000)
            resp = str(result)
            # Get real token metrics
            try:
                invocations = result.metrics.agent_invocations
                usage = invocations[-1].usage if invocations else result.metrics.accumulated_usage
                tokens = usage.get("totalTokens", len(resp) // 4)
            except Exception:
                tokens = len(resp) // 4
        st.markdown(resp)

    # Calculate cost
    rate = 0.000003 if tier == "economy" else 0.000015
    cost = tokens * rate
    st.session_state.m5p3_costs.append({"tier": tier, "cost": cost, "tokens": tokens, "latencyMs": wall_time})
    st.session_state.m5p3_msgs.append({"role": "assistant", "content": resp})
    st.rerun()


# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 5️⃣ Module 5")
    part = st.radio(
        "Select Part",
        ["Part 1 — E-Commerce", "Part 2 — Reliability", "Part 3 — Cost optimization"],
        key="m5_part",
    )
    from agentcore_utils import get_agentcore_status
    _s = get_agentcore_status()
    from style import show_status_badge
    show_status_badge("Guardrail", _s['guardrail'])
    show_status_badge("Memory", _s['memory'])
    show_status_badge("Evaluator", _s['evaluator'])
    if st.button("🔄 Reset Session", key="m5_reset_session", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m5"):
                del st.session_state[key]
        st.rerun()
    if st.button("🗑️ Clear Chat", key="m5_clear_chat", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m5") and key.endswith("_msgs"):
                st.session_state[key] = []
        st.rerun()


# =============================================================================
# PART 1: E-Commerce System (Operational Excellence)
# =============================================================================
if part == "Part 1 — E-Commerce":
    part_header("Multi-agent e-commerce", "Full orchestrated system with 4 specialist agents and operational metrics.")

    with st.expander("📐 Architecture & Code", expanded=False):
        tab_diagram, tab_code = st.tabs(["Architecture Diagram", "Code"])
        with tab_diagram:
            diagram_path = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/demos/module5-well-architected/diagrams/part1_ecommerce.png"
            if os.path.exists(diagram_path):
                st.image(diagram_path)
            else:
                st.caption("Diagram not found.")
        with tab_code:
            st.code("""
from strands import Agent, tool
from strands.models import BedrockModel

# 4 specialist agents
billing = Agent(model=model, system_prompt="Billing specialist...")
tech = Agent(model=model, system_prompt="Tech support...")
product = Agent(model=model, system_prompt="Product specialist...")
shipping = Agent(model=model, system_prompt="Shipping specialist...")

# Orchestrator routes to specialists
@tool
def ask_billing(q: str) -> str: return str(billing(q))
@tool
def ask_tech(q: str) -> str: return str(tech(q))
@tool
def ask_product(q: str) -> str: return str(product(q))
@tool
def ask_shipping(q: str) -> str: return str(shipping(q))

orchestrator = Agent(
    model=model,
    system_prompt="Route ALL queries to the appropriate specialist.",
    tools=[ask_billing, ask_tech, ask_product, ask_shipping],
)
            """, language="python")

    if "m5p1_agent" not in st.session_state:
        st.session_state.m5p1_agent = None
        st.session_state.m5p1_msgs = []
        st.session_state.m5p1_metrics = []
    if "m5p1_metrics" not in st.session_state:
        st.session_state.m5p1_metrics = []

    # Operational dashboard
    if st.session_state.m5p1_metrics:
        all_m = st.session_state.m5p1_metrics
        with st.container(border=True):
            st.markdown("##### 📊 Operational Dashboard")
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Interactions", len(all_m))
            mc2.metric("Avg Latency", f"{sum(m.get('latencyMs',0) for m in all_m)//max(len(all_m),1)}ms")
            mc3.metric("Total Tokens", f"{sum(m.get('totalTokens',0) for m in all_m):,}")
            mc4.metric("Routing", "📋🔧🛍️🚚")

    st.markdown("**Specialists:** 📋 Billing | 🔧 Tech | 🛍️ Product | 🚚 Shipping")

    if st.session_state.m5p1_agent is None:
        billing = create_agent("Billing specialist. Refunds (30-day), charges, subscriptions. Be concise.")
        tech = create_agent("Tech support. Hub v2.1.x has Wi-Fi bug→v3.0.1. Motion sensors need Zigbee pairing (hold 5s).")
        product = create_agent("Product specialist. Pro 15 $799 (i7,16GB), Air $599 (i5,8GB), Titan $1299 (RTX 4060), Hub $149.")
        shipping = create_agent("Shipping specialist. Standard 5-7d free, Express 2d $12.99, Same-day $24.99.")

        @tool
        def ask_billing(q: str) -> str:
            """Route billing queries. Args: q: billing question"""
            return str(billing(q))
        @tool
        def ask_tech(q: str) -> str:
            """Route tech queries. Args: q: tech question"""
            return str(tech(q))
        @tool
        def ask_product(q: str) -> str:
            """Route product queries. Args: q: product question"""
            return str(product(q))
        @tool
        def ask_shipping(q: str) -> str:
            """Route shipping queries. Args: q: shipping question"""
            return str(shipping(q))

        st.session_state.m5p1_agent = create_agent(
            "You are a Customer Service Orchestrator. You MUST route ALL queries to specialists using your tools. "
            "NEVER answer directly. Route billing→ask_billing, tech→ask_tech, products→ask_product, shipping→ask_shipping. "
            "For multi-domain queries, call multiple tools. Be concise.",
            tools=[ask_billing, ask_tech, ask_product, ask_shipping],
        )

    for idx, msg in enumerate(st.session_state.m5p1_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg["role"] == "assistant":
            mi = idx // 2
            if mi < len(st.session_state.m5p1_metrics):
                m = st.session_state.m5p1_metrics[mi]
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("⬇️ Input", m.get("inputTokens", 0))
                mc2.metric("⬆️ Output", m.get("outputTokens", 0))
                mc3.metric("⏱️ Latency", f"{m.get('latencyMs', 0)}ms")

    if not st.session_state.m5p1_msgs:
        suggestions = ["Laptops under $800?", "Hub dropping Wi-Fi v2.1.3", "Express shipping cost?"]
        selected = st.pills("Try:", suggestions, key="m5p1_pills")
        if selected:
            st.session_state.m5p1_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Routing to specialists..."):
                    resp, metrics = chat_response_with_metrics(st.session_state.m5p1_agent, selected)
                st.markdown(resp)
            st.session_state.m5p1_msgs.append({"role": "assistant", "content": resp})
            st.session_state.m5p1_metrics.append(metrics)
            st.rerun()

    if prompt := st.chat_input("Chat with e-commerce system...", submit_mode="disable"):
        st.session_state.m5p1_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Routing to specialists..."):
                resp, metrics = chat_response_with_metrics(st.session_state.m5p1_agent, prompt)
            st.markdown(resp)
        st.session_state.m5p1_msgs.append({"role": "assistant", "content": resp})
        st.session_state.m5p1_metrics.append(metrics)


# =============================================================================
# PART 2: Reliability (Fault Tolerance + Graceful Degradation)
# =============================================================================
elif part == "Part 2 — Reliability":
    part_header("Reliability — Fault tolerance", "Break agents, watch graceful degradation with fallback and retry.")

    with st.expander("📐 Architecture & Code", expanded=False):
        tab_diagram, tab_code = st.tabs(["Architecture Diagram", "Code"])
        with tab_diagram:
            diagram_path = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/demos/module5-well-architected/diagrams/part4_reliability.png"
            if os.path.exists(diagram_path):
                st.image(diagram_path)
            else:
                st.caption("Diagram not found.")
        with tab_code:
            st.code("""
# Reliability pattern: retry + fallback
def call_specialist_with_retry(specialist, query, max_retries=1):
    for attempt in range(max_retries + 1):
        try:
            return specialist(query)
        except Exception:
            if attempt == max_retries:
                return fallback_agent(query)  # Graceful degradation
    return fallback_agent(query)
            """, language="python")

    if "m5p2_faults" not in st.session_state:
        st.session_state.m5p2_faults = {"billing": False, "tech": False, "product": False}
        st.session_state.m5p2_msgs = []
        st.session_state.m5p2_metrics = []
    if "m5p2_metrics" not in st.session_state:
        st.session_state.m5p2_metrics = []

    # Health dashboard
    with st.container(border=True):
        st.markdown("##### 🏥 Agent Health Dashboard")
        hc1, hc2, hc3 = st.columns(3)
        for col, name in zip([hc1, hc2, hc3], ["billing", "tech", "product"]):
            broken = st.session_state.m5p2_faults[name]
            col.metric(f"{'📋' if name=='billing' else '🔧' if name=='tech' else '🛍️'} {name.title()}",
                       "🔴 DOWN" if broken else "🟢 Healthy")

    st.markdown("**Fault Injection:**")
    fcol1, fcol2, fcol3 = st.columns(3)
    st.session_state.m5p2_faults["billing"] = fcol1.checkbox("Break Billing", value=st.session_state.m5p2_faults["billing"], key="m5p2_f_billing")
    st.session_state.m5p2_faults["tech"] = fcol2.checkbox("Break Tech", value=st.session_state.m5p2_faults["tech"], key="m5p2_f_tech")
    st.session_state.m5p2_faults["product"] = fcol3.checkbox("Break Product", value=st.session_state.m5p2_faults["product"], key="m5p2_f_product")

    # Create agents with fault injection
    faults = st.session_state.m5p2_faults
    fallback = create_agent("You are a FALLBACK agent. A specialist is currently unavailable. Help as best you can but clearly state: ⚠️ DEGRADED MODE — specialist unavailable, providing general guidance only.")

    @tool
    def ask_billing(q: str) -> str:
        """Route billing queries. Args: q: billing question"""
        if faults["billing"]:
            return "⚠️ DEGRADED MODE: Billing specialist unavailable. " + str(fallback(f"[Fallback billing] {q}"))
        return "Refund policy: 30-day full refund. Subscriptions $9.99/mo. Express shipping refundable if defective."
    @tool
    def ask_tech(q: str) -> str:
        """Route tech queries. Args: q: tech question"""
        if faults["tech"]:
            return "⚠️ DEGRADED MODE: Tech specialist unavailable. " + str(fallback(f"[Fallback tech] {q}"))
        return "Hub v2.1.x: known Wi-Fi bug, update to v3.0.1. Sensors: hold button 5s for Zigbee pairing."
    @tool
    def ask_product(q: str) -> str:
        """Route product queries. Args: q: product question"""
        if faults["product"]:
            return "⚠️ DEGRADED MODE: Product specialist unavailable. " + str(fallback(f"[Fallback product] {q}"))
        return "Pro 15 $799 (i7, 16GB), Air $599 (i5, 8GB), Titan $1299 (RTX 4060), Hub $149 (Wi-Fi 6)."

    orch = create_agent(
        "You are an Orchestrator. Route ALL queries to specialists. NEVER answer directly. "
        "If a specialist returns DEGRADED MODE, relay that to the user clearly.",
        tools=[ask_billing, ask_tech, ask_product],
    )

    for idx, msg in enumerate(st.session_state.m5p2_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg["role"] == "assistant" and idx // 2 < len(st.session_state.m5p2_metrics):
            m = st.session_state.m5p2_metrics[idx // 2]
            degraded = "⚠️" in msg["content"]
            mc1, mc2 = st.columns(2)
            mc1.metric("⏱️ Latency", f"{m.get('latencyMs', 0)}ms")
            mc2.metric("Status", "⚠️ Degraded" if degraded else "✅ Normal")

    if not st.session_state.m5p2_msgs:
        suggestions = ["What laptops available?", "Refund on last order?", "Hub disconnecting from Wi-Fi"]
        selected = st.pills("Try:", suggestions, key="m5p2_pills")
        if selected:
            st.session_state.m5p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Routing (with fault tolerance)..."):
                    resp, metrics = chat_response_with_metrics(orch, selected)
                st.markdown(resp)
            st.session_state.m5p2_msgs.append({"role": "assistant", "content": resp})
            st.session_state.m5p2_metrics.append(metrics)
            st.rerun()

    if prompt := st.chat_input("Break agents then ask...", submit_mode="disable"):
        st.session_state.m5p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Routing (with fault tolerance)..."):
                resp, metrics = chat_response_with_metrics(orch, prompt)
            st.markdown(resp)
        st.session_state.m5p2_msgs.append({"role": "assistant", "content": resp})
        st.session_state.m5p2_metrics.append(metrics)


# =============================================================================
# PART 3: Cost Optimization (Model Tiering)
# =============================================================================
elif part == "Part 3 — Cost optimization":
    part_header("Cost optimization", "Smart model tiering: simple queries → economy model, complex → premium.")

    with st.expander("📐 Architecture & Code", expanded=False):
        tab_diagram, tab_code = st.tabs(["Architecture Diagram", "Code"])
        with tab_diagram:
            diagram_path = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/demos/module5-well-architected/diagrams/part5_cost_optimization.png"
            if os.path.exists(diagram_path):
                st.image(diagram_path)
            else:
                st.caption("Diagram not found.")
        with tab_code:
            st.code("""
# Cost optimization: route by complexity
def classify_complexity(query: str) -> str:
    complex_words = ["compare", "analyze", "recommend", "explain", "strategy", "trade-off"]
    if any(w in query.lower() for w in complex_words) or len(query.split()) > 15:
        return "premium"
    return "economy"

# Economy: Nova Micro ($0.000003/token)
# Premium: Claude Sonnet ($0.000015/token)
tier = classify_complexity(user_query)
model_id = "nova-micro" if tier == "economy" else "claude-sonnet-4"
agent = Agent(model=BedrockModel(model_id=model_id), ...)
            """, language="python")

    if "m5p3_msgs" not in st.session_state:
        st.session_state.m5p3_msgs = []
        st.session_state.m5p3_costs = []

    tiering = st.toggle("Smart Model Tiering", value=True, key="m5p3_tier")

    # Cost dashboard
    if st.session_state.m5p3_costs:
        total_cost = sum(c["cost"] for c in st.session_state.m5p3_costs)
        premium_only_cost = sum(c["tokens"] * 0.000015 for c in st.session_state.m5p3_costs)
        savings = premium_only_cost - total_cost

        with st.container(border=True):
            st.markdown("##### 💰 Cost Dashboard")
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Session Cost", f"${total_cost:.5f}")
            cc2.metric("Premium-Only Would Be", f"${premium_only_cost:.5f}")
            cc3.metric("Savings", f"${savings:.5f}", delta=f"-{savings/max(premium_only_cost,0.00001)*100:.0f}%" if savings > 0 else "0%")
            cc4.metric("Interactions", len(st.session_state.m5p3_costs))
            # Token budget
            budget = 0.01  # $0.01 budget for demo
            st.progress(min(total_cost / budget, 1.0), text=f"Token budget: ${total_cost:.6f} / ${budget:.2f}")

    for idx, msg in enumerate(st.session_state.m5p3_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg["role"] == "assistant" and idx // 2 < len(st.session_state.m5p3_costs):
            c = st.session_state.m5p3_costs[idx // 2]
            icon = "💚" if c["tier"] == "economy" else "💎"
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("Tier", f"{icon} {c['tier'].title()}")
            mc2.metric("Tokens", c["tokens"])
            mc3.metric("Cost", f"${c['cost']:.6f}")
            mc4.metric("Latency", f"{c.get('latencyMs', 0)}ms")

    if not st.session_state.m5p3_msgs:
        suggestions = ["Hi", "What's the Hub price?", "Compare Pro 15 and Titan for video editing"]
        selected = st.pills("Try:", suggestions, key="m5p3_pills")
        if selected:
            _do_cost_query(selected, tiering)

    if prompt := st.chat_input("Ask something (simple or complex)...", submit_mode="disable"):
        _do_cost_query(prompt, tiering)
