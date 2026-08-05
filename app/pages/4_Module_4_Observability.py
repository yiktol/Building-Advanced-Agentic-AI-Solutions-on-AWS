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
from agent_utils import create_agent, chat_response, chat_response_with_metrics, MODEL_ID
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
    show_status_badge("Guardrail", _s['guardrail'])
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
    part_header("Real-time metrics", "Every interaction emits latency, token, and tool metrics.")

    diagram_path = "/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS/demos/module4-observability/diagrams/part1_tracing.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m4p1_agent" not in st.session_state:
        st.session_state.m4p1_agent = None
        st.session_state.m4p1_msgs = []
        st.session_state.m4p1_metrics = []
    if "m4p1_metrics" not in st.session_state:
        st.session_state.m4p1_metrics = []

    # Cumulative session metrics at the top
    if st.session_state.m4p1_metrics:
        all_m = st.session_state.m4p1_metrics
        total_input = sum(m.get("inputTokens", 0) for m in all_m)
        total_output = sum(m.get("outputTokens", 0) for m in all_m)
        total_latency = sum(m.get("latencyMs", 0) for m in all_m)
        avg_latency = total_latency / len(all_m)
        total_tool_calls = sum(m.get("toolCalls", 0) for m in all_m)
        latest = all_m[-1]
        prev = all_m[-2] if len(all_m) > 1 else None

        with st.container(border=True):
            st.markdown("##### 📊 Observability Dashboard")
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("Total Input Tokens", f"{total_input:,}",
                       delta=f"+{latest.get('inputTokens', 0):,}" if prev else None, delta_color="off")
            mc2.metric("Total Output Tokens", f"{total_output:,}",
                       delta=f"+{latest.get('outputTokens', 0):,}" if prev else None, delta_color="off")
            mc3.metric("Avg Latency", f"{avg_latency:.0f}ms",
                       delta=f"{latest.get('latencyMs', 0) - avg_latency:+.0f}ms" if prev else None,
                       delta_color="inverse")
            mc4.metric("Total Tool Calls", total_tool_calls,
                       delta=f"+{latest.get('toolCalls', 0)}" if prev else None, delta_color="off")
            mc5.metric("Interactions", len(all_m))
            # Token usage bar
            st.progress(min(total_input / 10000, 1.0), text=f"Token budget: {total_input:,} / 10,000 (session limit example)")

    if st.session_state.m4p1_agent is None:
        st.session_state.m4p1_tool_calls = 0

        @tool
        def search_products(query: str) -> str:
            """Search products. Args: query: search term"""
            st.session_state.m4p1_tool_calls += 1
            return "TechMart Pro 15 ($799, i7/16GB), Air ($599, i5/8GB), Hub ($149, Wi-Fi 6), Titan ($1299, RTX 4060)"

        @tool
        def check_inventory(product_name: str) -> str:
            """Check product inventory. Args: product_name: product to check"""
            st.session_state.m4p1_tool_calls += 1
            stock = {"pro": "In stock (23 units)", "air": "In stock (45 units)", "hub": "Low stock (3 units)", "titan": "In stock (12 units)"}
            for k, v in stock.items():
                if k in product_name.lower():
                    return f"{product_name}: {v}"
            return f"{product_name}: Out of stock"

        st.session_state.m4p1_agent = create_agent(
            "You are a TechMart sales agent. Use search_products to find products and check_inventory to verify availability. Be helpful and concise.",
            tools=[search_products, check_inventory],
        )

    if "m4p1_tool_calls" not in st.session_state:
        st.session_state.m4p1_tool_calls = 0

    for idx, msg in enumerate(st.session_state.m4p1_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        if msg["role"] == "assistant":
            metrics_idx = idx // 2
            if metrics_idx < len(st.session_state.m4p1_metrics):
                m = st.session_state.m4p1_metrics[metrics_idx]
                with st.container(border=True):
                    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                    mc1.metric("⬇️ Input", f"{m.get('inputTokens', 0):,}")
                    mc2.metric("⬆️ Output", f"{m.get('outputTokens', 0):,}")
                    mc3.metric("⏱️ Latency", f"{m.get('latencyMs', 0)}ms")
                    mc4.metric("🔧 Tools", m.get("toolCalls", 0))
                    mc5.metric("Σ Total", f"{m.get('totalTokens', 0):,}")

    # Suggestion chips
    if not st.session_state.m4p1_msgs:
        suggestions = ["Search for TechMart Hub", "What laptops under $800?", "Is the Titan in stock?"]
        selected = st.pills("Try:", suggestions, key="m4p1_pills")
        if selected:
            st.session_state.m4p1_msgs.append({"role": "user", "content": selected})
            st.session_state.m4p1_tool_calls = 0
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    import time as _t; _s = _t.time()
                    resp, metrics = chat_response_with_metrics(st.session_state.m4p1_agent, selected)
                    wall_time = (_t.time() - _s) * 1000
                    metrics["latencyMs"] = metrics.get("latencyMs", 0) or int(wall_time)
                    metrics["toolCalls"] = st.session_state.m4p1_tool_calls
                st.markdown(resp)
            with st.container(border=True):
                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("⬇️ Input", f"{metrics.get('inputTokens', 0):,}")
                mc2.metric("⬆️ Output", f"{metrics.get('outputTokens', 0):,}")
                mc3.metric("⏱️ Latency", f"{metrics.get('latencyMs', 0)}ms")
                mc4.metric("🔧 Tools", metrics.get("toolCalls", 0))
                mc5.metric("Σ Total", f"{metrics.get('totalTokens', 0):,}")
            st.session_state.m4p1_msgs.append({"role": "assistant", "content": resp})
            st.session_state.m4p1_metrics.append(metrics)
            st.rerun()

    if prompt := st.chat_input("Ask about products...", submit_mode="disable"):
        st.session_state.m4p1_msgs.append({"role": "user", "content": prompt})
        st.session_state.m4p1_tool_calls = 0
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                import time as _t; _s = _t.time()
                resp, metrics = chat_response_with_metrics(st.session_state.m4p1_agent, prompt)
                wall_time = (_t.time() - _s) * 1000
                metrics["latencyMs"] = metrics.get("latencyMs", 0) or int(wall_time)
                metrics["toolCalls"] = st.session_state.m4p1_tool_calls
            st.markdown(resp)
        with st.container(border=True):
            mc1, mc2, mc3, mc4, mc5 = st.columns(5)
            mc1.metric("⬇️ Input", f"{metrics.get('inputTokens', 0):,}")
            mc2.metric("⬆️ Output", f"{metrics.get('outputTokens', 0):,}")
            mc3.metric("⏱️ Latency", f"{metrics.get('latencyMs', 0)}ms")
            mc4.metric("🔧 Tools", metrics.get("toolCalls", 0))
            mc5.metric("Σ Total", f"{metrics.get('totalTokens', 0):,}")
        st.session_state.m4p1_msgs.append({"role": "assistant", "content": resp})
        st.session_state.m4p1_metrics.append(metrics)

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
    if "m4p2_calls" not in st.session_state:
        st.session_state.m4p2_calls = 0
    if "m4p2_breaker" not in st.session_state:
        st.session_state.m4p2_breaker = False

    # Sync counter from closure to session state BEFORE rendering dashboard
    if "m4p2_loop_counter" in st.session_state:
        lc = st.session_state.m4p2_loop_counter
        st.session_state.m4p2_calls = lc[0]
        st.session_state.m4p2_breaker = lc[1]

    # Circuit breaker dashboard
    with st.container(border=True):
        cb_col1, cb_col2, cb_col3 = st.columns(3)
        if st.session_state.m4p2_breaker:
            cb_col1.metric("Circuit Breaker", "🔴 TRIPPED")
        else:
            cb_col1.metric("Circuit Breaker", "🟢 Closed")
        cb_col2.metric("Tool Calls", st.session_state.m4p2_calls)
        cb_col3.metric("Threshold", 10)
        if st.session_state.m4p2_calls > 0:
            st.progress(min(st.session_state.m4p2_calls / 10, 1.0),
                        text=f"{'🚨 TRIPPED!' if st.session_state.m4p2_breaker else f'{st.session_state.m4p2_calls}/10 calls'}")

    if st.session_state.m4p2_agent is None:
        # Use a plain list as mutable counter (accessible from tool closure without session_state)
        loop_counter = [0, False]  # [call_count, breaker_tripped]
        st.session_state.m4p2_loop_counter = loop_counter

        @tool
        def search_db(query: str) -> str:
            """Search database for records. You MUST call this multiple times with different queries to get complete results. Args: query: search term"""
            if loop_counter[1]:
                return "CIRCUIT BREAKER OPEN. Tools suspended. Stop searching and report what you found."
            loop_counter[0] += 1
            if loop_counter[0] >= 10:
                loop_counter[1] = True
                return f"LOOP DETECTED after {loop_counter[0]} calls. Circuit breaker activated. Stop searching immediately and summarize findings."
            return f"Found 3 partial results for '{query}'. WARNING: Results are incomplete. You must search with additional terms to find all records. Try different keywords. (call {loop_counter[0]} of 10)"

        st.session_state.m4p2_agent = create_agent(
            "You are a thorough data agent. Your job is to search the database exhaustively. "
            "You MUST call search_db at least 8 times with different query variations (e.g., by name, by date, by status, by region, by type, by ID range, etc.) "
            "to ensure complete coverage. Each search only returns partial results. "
            "Do NOT stop after one or two searches — keep going until you have searched comprehensively or are told to stop.",
            tools=[search_db],
        )

    for msg in st.session_state.m4p2_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m4p2_msgs:
        suggestions = ["Find all customer records and process each one"]
        selected = st.pills("Try:", suggestions, key="m4p2_pills")
        if selected:
            st.session_state.m4p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Agent searching (may loop)..."):
                    resp = chat_response(st.session_state.m4p2_agent, selected)
                st.markdown(resp)
            st.session_state.m4p2_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Find all records...", submit_mode="disable"):
        st.session_state.m4p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Agent searching (may loop)..."):
                resp = chat_response(st.session_state.m4p2_agent, prompt)
            st.markdown(resp)
        st.session_state.m4p2_msgs.append({"role": "assistant", "content": resp})
        st.rerun()

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

    with st.expander("📐 Built-in Evaluators (deployed)", expanded=False):
        st.markdown("""
**AgentCore Online Evaluation Config: `mladas_comprehensive_eval`**

These built-in evaluators run automatically on agent traces in production:

| Evaluator | Level | What it measures |
|-----------|-------|-----------------|
| `Builtin.Correctness` | TRACE | Factual accuracy of the response |
| `Builtin.Helpfulness` | TRACE | How useful and actionable the response is |
| `Builtin.Coherence` | TRACE | Logical consistency of the response |
| `Builtin.ToolSelectionAccuracy` | TOOL_CALL | Whether the right tool was chosen |
| `Builtin.GoalSuccessRate` | SESSION | Whether the user's overall goal was achieved |

These evaluate real OpenTelemetry traces emitted by agents on AgentCore Runtime.
For this interactive demo, we use a local LLM-as-judge that scores responses immediately.
        """)

    st.info("🧪 LLM-as-judge evaluates agent responses using the same dimensions as the built-in AgentCore evaluators.")

    if "m4p3_results" not in st.session_state:
        st.session_state.m4p3_results = []

    test_query = st.text_input("Query to evaluate:", value="My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.", key="m4p3_query")

    if st.button("🧪 Evaluate", key="m4p3_eval"):
        with st.spinner("Running evaluation (5 dimensions)..."):
            agent = create_agent("You are a TechMart support agent. TechMart Hub v2.1.x has Wi-Fi bug — update to v3.0.1. Be helpful and concise.")
            agent_resp = chat_response(agent, test_query)

            from strands import Agent as _A
            from strands.models import BedrockModel as _BM
            from agent_utils import _get_judge_model_id
            import json as _json

            judge_model = _BM(model_id=_get_judge_model_id(), max_tokens=1024)
            judge = _A(
                model=judge_model,
                system_prompt="""You are an agent evaluator scoring responses on 5 dimensions matching AgentCore built-in evaluators.

Score each dimension 0.0 to 1.0:
1. **Correctness** — Is the response factually accurate?
2. **Helpfulness** — Is it useful and actionable for the user?
3. **Coherence** — Is it logically consistent and well-structured?
4. **ToolSelection** — Did the agent use appropriate tools (or correctly not use tools)?
5. **GoalSuccess** — Did the response achieve what the user was asking for?

Return ONLY a JSON object with these exact keys:
{"Correctness": 0.X, "Helpfulness": 0.X, "Coherence": 0.X, "ToolSelection": 0.X, "GoalSuccess": 0.X, "explanation": "brief reasoning"}
""",
            )
            judge_resp = str(judge(f"User query: {test_query}\n\nAgent response: {agent_resp}\n\nScore this response."))

            scores = {"Correctness": 0.5, "Helpfulness": 0.5, "Coherence": 0.5, "ToolSelection": 0.5, "GoalSuccess": 0.5}
            explanation = ""
            try:
                if "{" in judge_resp:
                    parsed = _json.loads(judge_resp[judge_resp.index("{"):judge_resp.rindex("}") + 1])
                    for key in scores:
                        if key in parsed:
                            scores[key] = float(parsed[key])
                    explanation = parsed.get("explanation", "")
            except Exception:
                pass

            st.session_state.m4p3_results.append({"scores": scores, "explanation": explanation, "query": test_query, "response": agent_resp})
            st.rerun()

    # Display results persistently
    if st.session_state.m4p3_results:
        for i, result in enumerate(reversed(st.session_state.m4p3_results)):
            with st.container(border=True):
                st.caption(f"**Query:** {result['query']}")
                st.markdown(f"**Agent:** {result['response'][:300]}...")
                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                for col, (name, score) in zip([mc1, mc2, mc3, mc4, mc5], result["scores"].items()):
                    icon = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
                    col.metric(f"{icon} {name}", f"{score:.2f}")
                avg = sum(result["scores"].values()) / len(result["scores"])
                st.progress(avg, text=f"Overall: {avg:.2f} / 1.00")
                if result.get("explanation"):
                    st.caption(f"💬 {result['explanation']}")
            if i >= 2:
                break  # Show last 3 evaluations


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
