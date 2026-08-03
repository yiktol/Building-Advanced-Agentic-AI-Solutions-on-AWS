"""Module 4: Observability."""

import sys
import os
import time
import uuid
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import boto3
from style import inject_css, part_header
from agent_utils import create_agent, chat_response, MODEL_ID
from strands import tool

st.set_page_config(page_title="Module 4: Observability", page_icon="4️⃣", layout="wide")
inject_css()


# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 4️⃣ Module 4")
    part = st.radio(
        "Select Part",
        ["Part 1 — Metrics", "Part 2 — Loop detection", "Part 3 — Evaluation"],
        key="m4_part",
    )
    from agentcore_utils import get_agentcore_status
    _s = get_agentcore_status()
    from style import show_status_badge
    show_status_badge("Evaluator", _s['evaluator'])
    show_status_badge("CloudWatch", True)
    if st.button("🔄 Reset Session", key="m4_reset_session", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m4"):
                del st.session_state[key]
        st.rerun()
    if st.button("🗑️ Clear Chat", key="m4_clear_chat", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m4") and key.endswith("_msgs"):
                st.session_state[key] = []
        st.rerun()

REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
METRICS_NAMESPACE = os.environ.get("METRICS_NAMESPACE", "AgentMetrics")

# =============================================================================
# PART 1: Metrics
# =============================================================================
if part == "Part 1 — Metrics":
    part_header("Real-time metrics", "Every interaction emits latency, token, and tool metrics to CloudWatch.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module4-observability/diagrams/part1_tracing.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m4p1_agent" not in st.session_state:
        st.session_state.m4p1_agent = None
        st.session_state.m4p1_msgs = []
        st.session_state.m4p1_metrics = []

    if st.session_state.m4p1_metrics:
        st.markdown("**📊 Metrics**")
        for m in st.session_state.m4p1_metrics[-5:]:
            st.caption(f"⏱ {m['latency']:.0f}ms | ~{m['tokens']} tok")

    if st.session_state.m4p1_agent is None:
        @tool
        def search_products(query: str) -> str:
            """Search products. Args: query: search term"""
            time.sleep(0.2)
            return "TechMart Pro 15 ($799), Air ($599), Hub ($149)"

        st.session_state.m4p1_agent = create_agent(
            "You are a TechMart sales agent. Use tools to search products.",
            tools=[search_products],
        )

    for msg in st.session_state.m4p1_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m4p1_msgs:
        suggestions = ["Search for TechMart Hub", "What laptops under $800?"]
        selected = st.pills("Try:", suggestions, key="m4p1_pills")
        if selected:
            st.session_state.m4p1_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    import time as _t; _s = _t.time()
                    resp = chat_response(st.session_state.m4p1_agent, selected)
                    elapsed = (_t.time() - _s) * 1000
                    tokens = len(resp) // 4
                    st.session_state.m4p1_metrics.append({"latency": elapsed, "tokens": tokens})
                st.markdown(resp)
                st.caption(f"📊 {elapsed:.0f}ms | ~{tokens} tokens")
            st.session_state.m4p1_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Ask about products...", submit_mode="disable"):
        st.session_state.m4p1_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                import time as _t; _s = _t.time()
                resp = chat_response(st.session_state.m4p1_agent, prompt)
                elapsed = (_t.time() - _s) * 1000
                tokens = len(resp) // 4
                st.session_state.m4p1_metrics.append({"latency": elapsed, "tokens": tokens})
            st.markdown(resp)
            st.caption(f"📊 {elapsed:.0f}ms | ~{tokens} tokens")
        st.session_state.m4p1_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 2: Loop detection
# =============================================================================
elif part == "Part 2 — Loop detection":
    part_header("Loop detection", "Circuit breaker activates when agent makes too many repeated tool calls.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module4-observability/diagrams/part3_loop_detection.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m4p2_agent" not in st.session_state:
        st.session_state.m4p2_agent = None
        st.session_state.m4p2_msgs = []
        st.session_state.m4p2_calls = 0
        st.session_state.m4p2_breaker = False

    breaker_status = "🔴 OPEN" if st.session_state.m4p2_breaker else "🟢 Closed"
    st.metric("Circuit Breaker", breaker_status)
    st.metric("Tool Calls", st.session_state.m4p2_calls)
    st.caption("Trips at 10 calls")

    if st.session_state.m4p2_agent is None:
        @tool
        def search_db(query: str) -> str:
            """Search database. Args: query: search"""
            if st.session_state.m4p2_breaker:
                return "🚨 CIRCUIT BREAKER OPEN — tools suspended"
            st.session_state.m4p2_calls += 1
            if st.session_state.m4p2_calls >= 10:
                st.session_state.m4p2_breaker = True
                return "🚨 LOOP DETECTED — circuit breaker activated!"
            return f"Results for '{query}': 3 records found."

        st.session_state.m4p2_agent = create_agent(
            "You are a data agent. Search the database repeatedly with different query variations to find all matches. Try at least 5 different queries.",
            tools=[search_db],
        )

    for msg in st.session_state.m4p2_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m4p2_msgs:
        suggestions = ["Find all customer records"]
        selected = st.pills("Try:", suggestions, key="m4p2_pills")
        if selected:
            st.session_state.m4p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    resp = chat_response(st.session_state.m4p2_agent, selected)
                st.markdown(resp)
            st.session_state.m4p2_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Find all records...", submit_mode="disable"):
        st.session_state.m4p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                resp = chat_response(st.session_state.m4p2_agent, prompt)
            st.markdown(resp)
        st.session_state.m4p2_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 3: Evaluation
# =============================================================================
elif part == "Part 3 — Evaluation":
    part_header("LLM-as-judge evaluation", "Automated quality scoring of agent responses.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module4-observability/diagrams/part4_evaluation.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    from agentcore_utils import AgentCoreEvaluator, get_agentcore_status
    status = get_agentcore_status()
    if status["evaluator"]:
        st.success("🟢 Using **real AgentCore Evaluations** (deployed)")
    else:
        st.info("🟡 Using local LLM-as-judge. Deploy `infra-agentcore/cfn-agentcore-evaluator.yaml` for real AgentCore Evaluations.")

    if "m4p3_results" not in st.session_state:
        st.session_state.m4p3_results = []

    if st.session_state.m4p3_results:
        avg = sum(r["score"] for r in st.session_state.m4p3_results) / len(st.session_state.m4p3_results)
        st.metric("Avg Score", f"{avg:.2f}")
        for r in st.session_state.m4p3_results[-3:]:
            icon = "🟢" if r["score"] >= 0.75 else "🟡" if r["score"] >= 0.5 else "🔴"
            st.caption(f"{icon} {r['evaluator']}: {r['score']:.2f} ({r.get('source', 'unknown')})")

    test_query = st.text_input("Query to evaluate:", value="My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.", key="m4p3_query")

    if st.button("🧪 Evaluate", key="m4p3_eval"):
        with st.status("Running evaluation...", expanded=True):
            st.write("Getting agent response...")
            agent = create_agent("You are a TechMart support agent. TechMart Hub v2.1.x has Wi-Fi bug — update to v3.0.1.")
            agent_resp = chat_response(agent, test_query)
            st.write(f"**Agent:** {agent_resp[:200]}...")

            st.write("Evaluating...")
            evaluators = [
                ("Correctness", AgentCoreEvaluator(os.environ.get("ToolSelectionEvaluatorId", ""))),
                ("Helpfulness", AgentCoreEvaluator(os.environ.get("ComplianceEvaluatorId", ""))),
            ]

            for name, evaluator in evaluators:
                result = evaluator.evaluate(test_query, agent_resp)
                score = result["score"]
                source = result.get("source", "unknown")
                st.session_state.m4p3_results.append({"evaluator": name, "score": score, "source": source})
                icon = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
                st.write(f"{icon} **{name}**: {score:.2f} (via {source})")

        st.rerun()


# =============================================================================
# PART 4: Golden Dataset Baseline (#4)
# =============================================================================
elif part == "Part 4 — Golden Dataset":
    part_header("Golden dataset baseline", "Run a test suite to establish quality baselines and detect regressions.")

    st.markdown("""
    **Evaluation lifecycle:** Baseline → Monitor → Insight → Optimize

    This runs a pre-defined set of test queries with expected outcomes to establish a quality baseline.
    """)

    GOLDEN_DATASET = [
        {"query": "My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.", "expected_contains": "v3.0.1", "category": "Tech Support"},
        {"query": "I need a laptop for video editing under $800.", "expected_contains": "Pro 15", "category": "Product"},
        {"query": "Can I get a refund? I bought it 2 weeks ago.", "expected_contains": "30", "category": "Billing"},
        {"query": "Will the TechMart Hub work with the Smart Camera?", "expected_contains": "compatible", "category": "Product"},
        {"query": "What's the shipping cost for express delivery?", "expected_contains": "12.99", "category": "Shipping"},
    ]

    if "m4p4_results" not in st.session_state:
        st.session_state.m4p4_results = []

    if st.session_state.m4p4_results:
        # Show results summary
        total = len(st.session_state.m4p4_results)
        passed = sum(1 for r in st.session_state.m4p4_results if r["pass"])
        score = passed / total if total else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("Test cases", total)
        col2.metric("Passed", f"{passed}/{total}")
        col3.metric("Score", f"{score:.0%}")

        if score >= 0.8:
            st.success(f":material/check_circle: Quality baseline: **{score:.0%}** — PASS")
        elif score >= 0.6:
            st.warning(f":material/warning: Quality baseline: **{score:.0%}** — NEEDS ATTENTION")
        else:
            st.error(f":material/error: Quality baseline: **{score:.0%}** — FAILING")

        for r in st.session_state.m4p4_results:
            icon = ":material/check_circle:" if r["pass"] else ":material/cancel:"
            with st.expander(f"{icon} [{r['category']}] {r['query'][:50]}...", expanded=not r["pass"]):
                st.markdown(f"**Expected to contain:** `{r['expected']}`")
                st.markdown(f"**Found:** {'Yes' if r['pass'] else 'No'}")
                st.markdown(f"**Response:** {r['response'][:300]}...")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(":material/play_arrow: Run golden dataset", key="m4p4_run", use_container_width=True):
            st.session_state.m4p4_results = []
            agent = create_agent("You are a TechMart support agent. Hub v2.1.x → update to v3.0.1. Pro 15 $799. Refund within 30 days. Hub + Camera compatible. Express shipping $12.99.")

            progress = st.progress(0, text="Running test suite...")
            for i, tc in enumerate(GOLDEN_DATASET):
                progress.progress((i + 1) / len(GOLDEN_DATASET), text=f"Testing {i+1}/{len(GOLDEN_DATASET)}: {tc['category']}")
                resp = chat_response(agent, tc["query"])
                passed = tc["expected_contains"].lower() in resp.lower()
                st.session_state.m4p4_results.append({
                    "query": tc["query"],
                    "expected": tc["expected_contains"],
                    "response": resp,
                    "pass": passed,
                    "category": tc["category"],
                })
            st.rerun()

    with col_b:
        if st.button(":material/refresh: Clear results", key="m4p4_clear", use_container_width=True):
            st.session_state.m4p4_results = []
            st.rerun()
