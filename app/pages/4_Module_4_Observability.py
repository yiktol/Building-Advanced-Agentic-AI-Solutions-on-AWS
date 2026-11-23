"""Module 4: Observability."""

import sys
import os
import time
import uuid
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import boto3
from style import inject_css, part_header, live_services_caption, show_diagram, render_sample_prompts, take_sample_prompt
from agent_utils import create_agent, chat_response, chat_response_with_metrics, make_model, estimate_cost, MODEL_ID, stream_chat
from strands import tool
import telemetry
import runtime_client

st.set_page_config(page_title="Module 4: Observability", page_icon="4️⃣", layout="wide")
inject_css()
live_services_caption()


# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 4️⃣ Module 4")
    part = st.radio(
        "Select Part",
        ["Part 1 — Metrics", "Part 2 — Loop detection", "Part 3 — Evaluation"],
        key="m4_part",
    )
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
METRICS_NAMESPACE = telemetry.metrics_namespace()

# =============================================================================
# PART 1: Metrics
# =============================================================================
if part == "Part 1 — Metrics":
    part_header("Real-time metrics", "Every interaction emits latency, token, and tool metrics.")

    diagram_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "demos", "module4-observability", "diagrams", "part1_tracing.png")
    with st.expander("📐 Architecture Diagram", expanded=False):
        tab_diagram, tab_about, tab_prompts = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts"])
        with tab_diagram:
            if os.path.exists(diagram_path):
                show_diagram(diagram_path)
            else:
                st.info("Diagram not available.")
        with tab_about:
            st.markdown("""
Every interaction emits latency, token, and tool metrics and records a Session → Trace → Span hierarchy to CloudWatch, giving per-operation visibility into what the agent did.

**Try it:** Run a few queries and open the span view to see per-operation timing feeding the dashboard.
""")
        with tab_prompts:
            render_sample_prompts('m4p1')
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

        import agent_utils as _au
        _model_id = _au._get_model_id()
        _total_tokens = sum(m.get("totalTokens", 0) for m in all_m)
        _est_cost = estimate_cost(_model_id, total_input, total_output)
        with st.container(border=True):
            st.markdown("##### 💰 Estimated session cost")
            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Total Tokens", f"{_total_tokens:,}")
            cc2.metric("Total Latency", f"{total_latency:,.0f}ms")
            cc3.metric("Avg Latency", f"{avg_latency:.0f}ms")
            cc4.metric("Est. Cost (USD)", f"${_est_cost:.4f}")
            st.caption(f"Estimated (not billing-accurate) for `{_model_id}`.")

    # Thread-safe tool-call counter. Strands runs tools on a background thread
    # that has no Streamlit ScriptRunContext, so the tools must NOT touch
    # st.session_state (that raises "no attribute ..."). A plain list is shared
    # by reference and safe to mutate from the worker thread.
    if "m4p1_tool_counter" not in st.session_state:
        st.session_state.m4p1_tool_counter = [0]
    tool_counter = st.session_state.m4p1_tool_counter
    # Tool spans for the current request (same thread-safety reason as the counter).
    if "m4p1_tool_spans" not in st.session_state:
        st.session_state.m4p1_tool_spans = telemetry.ToolSpanRecorder()
    tool_spans = st.session_state.m4p1_tool_spans
    if "m4p1_session_id" not in st.session_state:
        st.session_state.m4p1_session_id = telemetry.new_session_id()
        st.session_state.m4p1_traces = []

    if st.session_state.m4p1_agent is None:
        @tool
        def search_products(query: str) -> str:
            """Search products. Args: query: search term"""
            tool_counter[0] += 1
            _t0 = time.time()
            result = "TechMart Pro 15 ($799, i7/16GB), Air ($599, i5/8GB), Hub ($149, Wi-Fi 6), Titan ($1299, RTX 4060)"
            tool_spans.record("search_products", _t0, {"query": query}, result={"chars": len(result)})
            return result

        @tool
        def check_inventory(product_name: str) -> str:
            """Check product inventory. Args: product_name: product to check"""
            tool_counter[0] += 1
            _t0 = time.time()
            stock = {"pro": "In stock (23 units)", "air": "In stock (45 units)", "hub": "Low stock (3 units)", "titan": "In stock (12 units)"}
            result = f"{product_name}: Out of stock"
            for k, v in stock.items():
                if k in product_name.lower():
                    result = f"{product_name}: {v}"
                    break
            tool_spans.record("check_inventory", _t0, {"product_name": product_name}, result={"answer": result})
            return result

        st.session_state.m4p1_agent = create_agent(
            "You are a TechMart sales agent. Use search_products to find products and check_inventory to verify availability. Be helpful and concise.",
            tools=[search_products, check_inventory],
        )

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

    _use_runtime = runtime_client.is_configured()
    if _use_runtime:
        if "m4p1_rt_session" not in st.session_state:
            st.session_state.m4p1_rt_session = runtime_client.new_session_id()
        st.info(
            f"🛰 Requests go to the deployed agent on **AgentCore Runtime** (`{runtime_client.runtime_id()}`). "
            "The runtime emits OpenTelemetry traces (ADOT) to CloudWatch Transaction Search, application and usage logs "
            "through vended log delivery, and the online evaluation config scores each session."
        )
    else:
        st.caption("AgentCore Runtime agent not deployed; using the in-process agent.")
    if prompt := (st.chat_input("Ask about products...", submit_mode="disable") or take_sample_prompt('m4p1')):
        st.session_state.m4p1_msgs.append({"role": "user", "content": prompt})
        tool_counter[0] = 0
        tool_spans.reset()
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            import time as _t; _s = _t.time()
            if _use_runtime:
                _box = st.empty()
                _buf = []

                def _on_text(chunk):
                    _buf.append(chunk)
                    _box.markdown("".join(_buf) + "▌")

                try:
                    with st.spinner("Invoking AgentCore Runtime..."):
                        rt = runtime_client.invoke_runtime(prompt, st.session_state.m4p1_rt_session, on_text=_on_text)
                    resp = rt["text"]
                    _box.markdown(resp)
                    metrics = {**rt["usage"], "latencyMs": rt["latencyMs"], "toolCalls": len(rt["tool_calls"])}
                    for _name in rt["tool_calls"]:
                        tool_spans.record(_name, _s, {"source": "agentcore-runtime"})
                    st.caption(f"🔧 Tools called by the runtime: {', '.join(rt['tool_calls']) or 'none'} · session `{rt['session_id']}`")
                except Exception as e:
                    resp = f"⚠ AgentCore Runtime call failed: {e}"
                    _box.markdown(resp)
                    metrics = {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "latencyMs": 0, "toolCalls": 0}
            else:
                resp, metrics = stream_chat(st.session_state.m4p1_agent, prompt, "Processing...")
                metrics["toolCalls"] = tool_counter[0]
            wall_time = (_t.time() - _s) * 1000
            metrics["latencyMs"] = metrics.get("latencyMs", 0) or int(wall_time)
            _ended = time.time()
        # Send the trace (spans) to CloudWatch Logs and the metrics to CloudWatch.
        pub = telemetry.publish_interaction(
            st.session_state.m4p1_session_id, len(st.session_state.m4p1_traces) + 1, prompt,
            _ended - wall_time / 1000, _ended, metrics, list(tool_spans.spans),
        )
        st.session_state.m4p1_traces.append(pub)
        if pub["ok"]:
            st.caption(f"📡 Trace `{pub['trace_id'][:12]}…` ({len(pub['spans'])} spans) written to CloudWatch Logs `{pub['log_group']}`.")
            if pub.get("metrics_error"):
                st.warning(f"Metrics were NOT sent to `{METRICS_NAMESPACE}`: {pub['metrics_error']}")
            else:
                st.caption(f"Metrics sent to CloudWatch namespace `{METRICS_NAMESPACE}`.")
            with st.expander("🔍 Spans sent to CloudWatch", expanded=False):
                st.json(pub["spans"])
        else:
            st.warning(f"Telemetry was NOT sent to CloudWatch: {pub['error']}")
        if _use_runtime:
            _rid = runtime_client.runtime_id()
            _console = f"https://{runtime_client.REGION}.console.aws.amazon.com/cloudwatch/home?region={runtime_client.REGION}"
            st.caption(
                f"🛰 Runtime telemetry (arrives in 1 to 3 minutes): traces in Transaction Search (`aws/spans`, session.id = "
                f"`{st.session_state.m4p1_rt_session}`), runtime logs in `{runtime_client.runtime_log_group()}`, "
                f"vended logs in `/aws/vendedlogs/bedrock-agentcore/runtime/APPLICATION_LOGS/{_rid}` and `.../USAGE_LOGS/{_rid}`. "
                f"[GenAI Observability dashboard]({_console}#gen-ai-observability/agent-core)"
            )
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

    diagram_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "demos", "module4-observability", "diagrams", "part3_loop_detection.png")
    with st.expander("📐 Architecture Diagram", expanded=False):
        tab_diagram, tab_about, tab_prompts = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts"])
        with tab_diagram:
            if os.path.exists(diagram_path):
                show_diagram(diagram_path)
            else:
                st.info("Diagram not available.")
        with tab_about:
            st.markdown("""
A circuit breaker trips when the agent makes too many repeated tool calls, stopping runaway loops and firing a CloudWatch alarm — critical safety for autonomous agents.

**Try it:** Trigger the "loopy" mode to watch tool calls escalate and the breaker activate.
""")
        with tab_prompts:
            render_sample_prompts('m4p2')
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

    if prompt := (st.chat_input("Find all records...", submit_mode="disable") or take_sample_prompt('m4p2')):
        st.session_state.m4p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            resp, _ = stream_chat(st.session_state.m4p2_agent, prompt, "Agent searching (may loop)...")
        st.session_state.m4p2_msgs.append({"role": "assistant", "content": resp})
        st.rerun()

# =============================================================================
# PART 3: Evaluation
# =============================================================================
elif part == "Part 3 — Evaluation":
    part_header("AgentCore Evaluations", "Built-in evaluators score real AgentCore Runtime traces.")

    diagram_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "demos", "module4-observability", "diagrams", "part4_evaluation.png")
    with st.expander("📐 Architecture Diagram", expanded=False):
        tab_diagram, tab_about, tab_prompts = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts"])
        with tab_diagram:
            if os.path.exists(diagram_path):
                show_diagram(diagram_path)
            else:
                st.info("Diagram not available.")
        with tab_about:
            st.markdown("""
The query is sent to the deployed agent on AgentCore Runtime. Its OpenTelemetry spans are read back from CloudWatch Transaction Search and scored by the AgentCore **built-in evaluators** through the `Evaluate` API (on-demand evaluation). The same evaluators also run continuously through the online evaluation config, which writes results to CloudWatch Logs.

**Try it:** Evaluate a query, wait for the spans to arrive (1 to 3 minutes), then check the online evaluation results a few minutes later.
""")
        with tab_prompts:
            render_sample_prompts('m4p3', target_key="m4p3_query", action_label="Use", note="Click **Use** to load a query into the box below, then press 🧪 Evaluate.")
    _oe = runtime_client.online_eval_id()
    with st.expander("📐 Built-in evaluators (online evaluation config)", expanded=False):
        st.markdown(
            (f"**Online evaluation config:** `{_oe}` (sampling 100%, results in `{runtime_client.online_eval_log_group()}`)\n\n" if _oe else
             "**Online evaluation config:** not deployed\n\n")
            + "| Evaluator | Level | What it measures |\n|---|---|---|\n"
            + "\n".join(f"| `{n}` | {lvl} | {d} |" for n, lvl, d in runtime_client.BUILTIN_EVALUATORS)
        )
    if "m4p3_results" not in st.session_state:
        st.session_state.m4p3_results = []
    if "m4p3_query" not in st.session_state:
        from sample_prompts import PROMPTS
        st.session_state.m4p3_query = PROMPTS["m4p3"][0]["prompt"]
    test_query = st.text_input("Query to evaluate:", key="m4p3_query")
    if not runtime_client.is_configured():
        st.warning("The AgentCore Runtime agent is not deployed (agents/techmartagent), so there are no traces to evaluate.")
    elif st.button("🧪 Evaluate", key="m4p3_eval"):
        sid = runtime_client.new_session_id()
        with st.status("Running AgentCore evaluation...", expanded=True) as status_box:
            st.write(f"1. Invoking AgentCore Runtime (session `{sid}`)")
            try:
                rt = runtime_client.invoke_runtime(test_query, sid)
            except Exception as e:
                status_box.update(label=f"Runtime call failed: {e}", state="error")
                st.stop()
            st.write(f"   Tools called: {', '.join(rt['tool_calls']) or 'none'}")
            st.write("2. Waiting for the session's spans in CloudWatch Transaction Search (usually 1 to 3 minutes)")
            _tick = st.empty()
            spans = runtime_client.wait_for_spans(sid, timeout_s=300, interval_s=15,
                                                  on_tick=lambda n: _tick.caption(f"   spans found: {n}"))
            if not spans:
                status_box.update(label="Spans did not arrive within 5 minutes; try 'Check online results' later.", state="error")
                st.session_state.m4p3_results.append({"query": test_query, "response": rt["text"], "session_id": sid,
                                                      "rows": [], "spans": 0, "online": []})
                st.stop()
            st.write(f"3. Scoring {len(spans)} spans with {len(runtime_client.BUILTIN_EVALUATORS)} built-in evaluators")
            rows = runtime_client.evaluate(spans, [e[0] for e in runtime_client.BUILTIN_EVALUATORS])
            status_box.update(label="Evaluation complete", state="complete")
        st.session_state.m4p3_results.append({"query": test_query, "response": rt["text"], "session_id": sid,
                                              "rows": rows, "spans": len(spans), "online": []})
        st.rerun()
    # Display results persistently
    if st.session_state.m4p3_results:
        for i, result in enumerate(reversed(st.session_state.m4p3_results)):
            with st.container(border=True):
                st.caption(f"**Query:** {result['query']} · session `{result['session_id']}` · {result['spans']} spans")
                st.markdown(f"**Agent (AgentCore Runtime):** {result['response'][:400]}")
                rows = [r for r in result["rows"] if r.get("value") is not None]
                if rows:
                    by_eval = {}
                    for r in rows:
                        by_eval.setdefault(r["evaluator"], []).append(r)
                    cols = st.columns(len(by_eval))
                    for col, (name, rs) in zip(cols, by_eval.items()):
                        v = sum(r["value"] for r in rs) / len(rs)
                        icon = "🟢" if v >= 0.75 else "🟡" if v >= 0.5 else "🔴"
                        col.metric(f"{icon} {name.replace('Builtin.', '')}", f"{v:.2f}", help=rs[0]["label"])
                    avg = sum(r["value"] for r in rows) / len(rows)
                    st.progress(min(max(avg, 0.0), 1.0), text=f"Overall: {avg:.2f} / 1.00 (AgentCore on-demand evaluation)")
                    with st.expander("💬 Evaluator explanations", expanded=False):
                        for r in result["rows"]:
                            label = f"{r['value']:.2f} {r['label']}" if r.get("value") is not None else "error"
                            st.markdown(f"**{r['evaluator']}** · {label}  \n{r['explanation'] or r['error']}")
                errors = [r for r in result["rows"] if r.get("value") is None and r.get("error")]
                for r in errors:
                    st.warning(f"{r['evaluator']}: {r['error']}")
                if runtime_client.online_eval_id():
                    if st.button("🔄 Check online evaluation results", key=f"m4p3_online_{result['session_id']}"):
                        with st.spinner("Querying online evaluation results..."):
                            result["online"] = runtime_client.fetch_online_results(result["session_id"])
                    if result["online"]:
                        st.markdown(f"**Online evaluation results** (written by `{runtime_client.online_eval_id()}`)")
                        _by = {}
                        for r in result["online"]:
                            if r.get("value") is not None:
                                _by.setdefault(r["evaluator"], []).append(float(r["value"]))
                        if _by:
                            _cols = st.columns(len(_by))
                            for _c, (_n, _v) in zip(_cols, _by.items()):
                                _c.metric(_n.replace("Builtin.", ""), f"{sum(_v) / len(_v):.2f}")
                        with st.expander("💬 Online evaluator explanations", expanded=False):
                            for r in result["online"]:
                                st.markdown(f"**{r['evaluator']}** · {r['value']} {r['label']}  \n{r['explanation']}")
                    else:
                        st.caption("Online evaluation runs after 5 minutes of session inactivity; results can take a few more minutes.")
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
