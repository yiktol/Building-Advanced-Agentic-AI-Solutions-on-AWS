"""Module 5: Well-Architected."""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from style import inject_css, part_header
from agent_utils import create_agent, chat_response, MODEL_ID
from strands import tool

st.set_page_config(page_title="Module 5: Well-Architected", page_icon="5️⃣", layout="wide")
inject_css()


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
# PART 1: E-Commerce System
# =============================================================================
if part == "Part 1 — E-Commerce":
    part_header("Multi-agent e-commerce", "Full orchestrated system with 4 specialist agents.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module5-well-architected/diagrams/part1_ecommerce.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m5p1_agent" not in st.session_state:
        st.session_state.m5p1_agent = None
        st.session_state.m5p1_msgs = []

    st.markdown("**Specialists:** 📋 Billing | 🔧 Tech | 🛍️ Product | 🚚 Shipping")

    if st.session_state.m5p1_agent is None:
        billing = create_agent("Billing specialist. Refunds (30-day), charges. Be concise.")
        tech = create_agent("Tech support. Hub v2.1.x has Wi-Fi bug→v3.0.1. Motion sensors need Zigbee pairing.")
        product = create_agent("Product specialist. Pro 15 $799, Air $599, Titan $1299, Hub $149.")
        shipping = create_agent("Shipping specialist. Standard 5-7d, Express 2d ($12.99), Same-day $24.99.")

        @tool
        def ask_billing(q: str) -> str:
            """Billing. Args: q: query"""
            return str(billing(q))
        @tool
        def ask_tech(q: str) -> str:
            """Tech. Args: q: query"""
            return str(tech(q))
        @tool
        def ask_product(q: str) -> str:
            """Product. Args: q: query"""
            return str(product(q))
        @tool
        def ask_shipping(q: str) -> str:
            """Shipping. Args: q: query"""
            return str(shipping(q))

        st.session_state.m5p1_agent = create_agent(
            "Orchestrator: route to ask_billing, ask_tech, ask_product, ask_shipping.",
            tools=[ask_billing, ask_tech, ask_product, ask_shipping],
        )

    for msg in st.session_state.m5p1_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m5p1_msgs:
        suggestions = ["Laptops under $800?", "Order status ORD-7001", "Hub dropping Wi-Fi"]
        selected = st.pills("Try:", suggestions, key="m5p1_pills")
        if selected:
            st.session_state.m5p1_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Routing..."):
                    resp = chat_response(st.session_state.m5p1_agent, selected)
                st.markdown(resp)
            st.session_state.m5p1_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Chat with e-commerce...", submit_mode="disable"):
        st.session_state.m5p1_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Routing..."):
                resp = chat_response(st.session_state.m5p1_agent, prompt)
            st.markdown(resp)
        st.session_state.m5p1_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 2: Reliability
# =============================================================================
elif part == "Part 2 — Reliability":
    part_header("Reliability — Fault tolerance", "Break an agent, watch graceful degradation to fallback.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module5-well-architected/diagrams/part4_reliability.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m5p2_faults" not in st.session_state:
        st.session_state.m5p2_faults = {"billing": False, "tech": False, "product": False}
        st.session_state.m5p2_agent = None
        st.session_state.m5p2_msgs = []

    st.markdown("**Fault Injection:**")
    for name in ["billing", "tech", "product"]:
        st.session_state.m5p2_faults[name] = st.checkbox(
            f"Break {name}", value=st.session_state.m5p2_faults[name], key=f"m5p2_fault_{name}"
        )
    st.markdown("**Status:**")
    for name, broken in st.session_state.m5p2_faults.items():
        icon = "🔴" if broken else "🟢"
        st.caption(f"{icon} {name}")

    # Recreate agent each time since faults change
    faults = st.session_state.m5p2_faults
    fallback = create_agent("You are a FALLBACK agent. A specialist is down. Help as best you can. Prefix: ⚠️ DEGRADED MODE")

    @tool
    def ask_billing(q: str) -> str:
        """Billing. Args: q: query"""
        if faults["billing"]:
            return str(fallback(f"[Fallback for billing] {q}"))
        return "Refund policy: 30-day full refund. Express shipping refundable if defective."
    @tool
    def ask_tech(q: str) -> str:
        """Tech. Args: q: query"""
        if faults["tech"]:
            return str(fallback(f"[Fallback for tech] {q}"))
        return "Hub v2.1.x: known Wi-Fi bug. Update to v3.0.1. Sensors: hold button 5s for pairing."
    @tool
    def ask_product(q: str) -> str:
        """Product. Args: q: query"""
        if faults["product"]:
            return str(fallback(f"[Fallback for product] {q}"))
        return "Pro 15 $799 (i7, 16GB), Air $599 (i5, 8GB), Titan $1299 (RTX 4060), Hub $149."

    orch = create_agent(
        "Orchestrator: route queries. If specialist returns DEGRADED MODE, let user know.",
        tools=[ask_billing, ask_tech, ask_product],
    )

    for msg in st.session_state.m5p2_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m5p2_msgs:
        suggestions = ["What laptops available?", "Refund on last order?"]
        selected = st.pills("Try:", suggestions, key="m5p2_pills")
        if selected:
            st.session_state.m5p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Routing..."):
                    resp = chat_response(orch, selected)
                st.markdown(resp)
            st.session_state.m5p2_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Break agents then ask...", submit_mode="disable"):
        st.session_state.m5p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Routing..."):
                resp = chat_response(orch, prompt)
            st.markdown(resp)
        st.session_state.m5p2_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 3: Cost optimization
# =============================================================================
elif part == "Part 3 — Cost optimization":
    part_header("Cost optimization", "Model tiering: simple queries → economy, complex → premium.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module5-well-architected/diagrams/part5_cost_optimization.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m5p3_msgs" not in st.session_state:
        st.session_state.m5p3_msgs = []
        st.session_state.m5p3_costs = []

    if st.session_state.m5p3_costs:
        total = sum(c["cost"] for c in st.session_state.m5p3_costs)
        st.metric("Session Cost", f"${total:.5f}")
        for c in st.session_state.m5p3_costs[-5:]:
            icon = "💚" if c["tier"] == "economy" else "💎"
            st.caption(f"{icon} {c['tier']}: ${c['cost']:.5f}")

    tiering = st.toggle("Smart Model Tiering", value=True, key="m5p3_tier")

    for msg in st.session_state.m5p3_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m5p3_msgs:
        suggestions = ["Hi", "Compare Pro 15 and Titan for editing"]
        selected = st.pills("Try:", suggestions, key="m5p3_pills")
        if selected:
            complex_words = ["compare", "analyze", "recommend", "explain", "strategy"]
            is_complex = any(w in selected.lower() for w in complex_words) or len(selected.split()) > 15
            tiering_val = st.session_state.get("m5p3_tier", True)
            tier = "economy" if (tiering_val and not is_complex) else "premium"
            st.session_state.m5p3_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner(f"Processing ({tier})..."):
                    import time as _t; _s = _t.time()
                    agent = create_agent("You are a TechMart assistant. Be concise.")
                    resp = chat_response(agent, selected)
                    elapsed = _t.time() - _s
                tokens = len(resp) // 4 + len(selected) // 4
                cost = tokens * 0.000015 if tier == "premium" else tokens * 0.000003
                st.session_state.m5p3_costs.append({"tier": tier, "cost": cost, "tokens": tokens})
                st.markdown(resp)
                icon = "💚" if tier == "economy" else "💎"
                st.caption(f"{icon} {tier} | ~{tokens} tokens | ${cost:.6f}")
            st.session_state.m5p3_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Chat (watch cost)...", submit_mode="disable"):
        complex_words = ["compare", "analyze", "recommend", "explain", "strategy"]
        is_complex = any(w in prompt.lower() for w in complex_words) or len(prompt.split()) > 15
        tiering_val = st.session_state.get("m5p3_tier", True)
        tier = "economy" if (tiering_val and not is_complex) else "premium"
        st.session_state.m5p3_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner(f"Processing ({tier})..."):
                import time as _t; _s = _t.time()
                agent = create_agent("You are a TechMart assistant. Be concise.")
                resp = chat_response(agent, prompt)
                elapsed = _t.time() - _s
            tokens = len(resp) // 4 + len(prompt) // 4
            cost = tokens * 0.000015 if tier == "premium" else tokens * 0.000003
            st.session_state.m5p3_costs.append({"tier": tier, "cost": cost, "tokens": tokens})
            st.markdown(resp)
            icon = "💚" if tier == "economy" else "💎"
            st.caption(f"{icon} {tier} | ~{tokens} tokens | ${cost:.6f}")
        st.session_state.m5p3_msgs.append({"role": "assistant", "content": resp})
