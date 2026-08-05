"""Module 1: Multi-Agent Architecture."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from style import inject_css, part_header
import agent_utils
from agent_utils import create_agent, chat_response, MODEL_ID
from strands import Agent, tool
from strands.models import BedrockModel

st.set_page_config(page_title="Module 1: Multi-Agent", page_icon="1️⃣", layout="wide")
inject_css()

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 1️⃣ Module 1")
    part = st.radio(
        "Select Part",
        ["Part 1 — Single Agent", "Part 2 — Orchestrator", "Part 3 — Agent-as-Tool", "Part 4 — Shared memory", "Part 5 — Graph & Swarm", "Auto-run Walkthrough"],
        key="m1_part",
    )
    from agentcore_utils import get_agentcore_status
    _s = get_agentcore_status()
    from style import show_status_badge
    show_status_badge("Memory", _s['memory'])
    show_status_badge("Guardrail", _s['guardrail'])
    show_status_badge("Evaluator", _s['evaluator'])
    show_status_badge("Gateway", _s['gateway'])
    show_status_badge("Cognito", _s['cognito'])
    show_status_badge("Policy", _s['policy_store'])
    if st.button("🔄 Reset Session", key="m1_reset_session", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m1"):
                del st.session_state[key]
        st.rerun()
    if st.button("🗑️ Clear Chat", key="m1_clear_chat", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m1") and key.endswith("_msgs"):
                st.session_state[key] = []
        st.rerun()

# =============================================================================
# PART 1: Single Agent
# =============================================================================
if part == "Part 1 — Single Agent":
    part_header("Single agent (cognitive load)", "One agent handles billing, tech support, and product queries.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module1-multi-agent/diagrams/part1_single_agent.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m1p1_agent" not in st.session_state:
        st.session_state.m1p1_agent = None
        st.session_state.m1p1_msgs = []
        st.session_state.m1p1_judgments = []

    # --- Judge Model Configuration ---
    JUDGE_SYSTEM_PROMPT = """You are a Judge Model evaluating an AI customer service agent's response for signs of COGNITIVE LOAD issues.

The agent being evaluated handles billing, tech support, AND product queries simultaneously.

Evaluate the agent's response on these criteria (score each 1-5, where 1 = major issue, 5 = no issue):

1. **Domain Accuracy**: Did the agent apply the correct domain knowledge? (e.g., not mixing billing procedures with tech troubleshooting)
2. **Context Retention**: Did the agent maintain relevant context from the user's query without hallucinating or losing key details?
3. **Specificity**: Did the agent provide domain-expert level detail, or was it overly generic / surface-level?
4. **Domain Confusion**: Did the agent bleed information from one domain into another where it doesn't belong?
5. **Actionability**: Did the agent provide clear, actionable next steps appropriate to the domain?

Output format:
**Cognitive Load Assessment**

| Criterion | Score | Observation |
|-----------|-------|-------------|
| Domain Accuracy | X/5 | ... |
| Context Retention | X/5 | ... |
| Specificity | X/5 | ... |
| Domain Confusion | X/5 | ... |
| Actionability | X/5 | ... |

**Overall Score: X/25**

**Verdict:** [PASS ✅ | MARGINAL ⚠️ | FAIL ❌]
- PASS (20-25): Agent handled query well despite broad scope
- MARGINAL (13-19): Some signs of cognitive overload
- FAIL (≤12): Clear evidence of cognitive overload impacting quality

**Key Observations:** 1-2 sentences on how cognitive load affected (or didn't affect) the response.
"""

    def judge_response(user_query: str, agent_response: str) -> str:
        """Use a Judge Model to evaluate the agent's response for cognitive load issues."""
        judge_model = BedrockModel(model_id=agent_utils._get_judge_model_id())
        judge_agent = Agent(model=judge_model, system_prompt=JUDGE_SYSTEM_PROMPT)
        evaluation_prompt = f"""Evaluate this single-agent interaction:

**User Query:** {user_query}

**Agent Response:** {agent_response}

Assess whether the agent showed signs of cognitive overload from handling multiple domains."""
        result = judge_agent(evaluation_prompt)
        return str(result)

    with st.expander("💡 Suggested Prompts", expanded=False):
        st.caption("• I was charged $9.99 but cancelled. Order TM-78432.")
        st.caption("• My TechMart Hub keeps disconnecting. Firmware v2.1.3.")
        st.caption("• I need a laptop under $800 for video editing.")

    if st.session_state.m1p1_agent is None:
        st.session_state.m1p1_agent = create_agent(
            """You are a customer service agent for TechMart handling ALL inquiries:
BILLING: Refunds (30-day window), subscriptions ($9.99/mo), payments.
TECH: Wi-Fi troubleshooting, firmware updates, device pairing.
PRODUCTS: TechMart Pro 15 ($799), Air ($599), Titan ($1299), Hub ($149).
Always verify identity before account changes."""
        )

    for idx, msg in enumerate(st.session_state.m1p1_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        # Show judgment after assistant messages
        if msg["role"] == "assistant":
            judgment_idx = idx // 2  # Each pair (user, assistant) has one judgment
            if judgment_idx < len(st.session_state.m1p1_judgments):
                with st.expander(f"🧑‍⚖️ Judge Evaluation", expanded=False):
                    st.markdown(st.session_state.m1p1_judgments[judgment_idx])

    # Suggestion chips
    if not st.session_state.m1p1_msgs:
        suggestions = ["Charged $9.99, cancelled last week", "Hub disconnecting, firmware v2.1.3", "Laptop under $800 for editing"]
        selected = st.pills("Try:", suggestions, key="m1p1_pills")
        if selected:
            st.session_state.m1p1_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    resp = chat_response(st.session_state.m1p1_agent, selected)
                st.markdown(resp)
            st.session_state.m1p1_msgs.append({"role": "assistant", "content": resp})
            # Judge evaluation
            with st.expander("🧑‍⚖️ Judge Evaluation", expanded=True):
                with st.spinner("Judge Model evaluating..."):
                    judgment = judge_response(selected, resp)
                st.markdown(judgment)
            st.session_state.m1p1_judgments.append(judgment)
            st.rerun()

    if prompt := st.chat_input("Chat with single agent...", submit_mode="disable"):
        st.session_state.m1p1_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = chat_response(st.session_state.m1p1_agent, prompt)
            st.markdown(resp)
        st.session_state.m1p1_msgs.append({"role": "assistant", "content": resp})
        # Judge evaluation
        with st.expander("🧑‍⚖️ Judge Evaluation", expanded=True):
            with st.spinner("Judge Model evaluating..."):
                judgment = judge_response(prompt, resp)
            st.markdown(judgment)
        st.session_state.m1p1_judgments.append(judgment)

# =============================================================================
# PART 2: Orchestrator
# =============================================================================
elif part == "Part 2 — Orchestrator":
    part_header("Orchestrator pattern", "Centralized routing to specialist agents.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module1-multi-agent/diagrams/part2_orchestrator.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m1p2_orch" not in st.session_state:
        st.session_state.m1p2_orch = None
        st.session_state.m1p2_msgs = []
        st.session_state.m1p2_judgments = []

    # --- Judge Model for Orchestrator ---
    JUDGE_ORCH_SYSTEM_PROMPT = """You are a Judge Model evaluating an ORCHESTRATOR agent that routes customer queries to specialist agents (Billing, Tech Support, Product).

Evaluate the orchestrator's response on these criteria (score each 1-5, where 1 = major issue, 5 = excellent):

1. **Routing Accuracy**: Did the orchestrator route the query to the correct specialist(s)? (Billing for refunds/charges, Tech for devices/firmware, Product for recommendations)
2. **Delegation Completeness**: For multi-domain queries, did it correctly identify ALL relevant domains and route to each?
3. **Synthesis Quality**: Did the orchestrator combine specialist responses into a coherent, unified answer?
4. **Information Preservation**: Was important specialist detail preserved (not lost or oversimplified) in the final response?
5. **Efficiency**: Did it avoid unnecessary routing (e.g., sending a pure billing question to tech support)?

Output format:
**Orchestrator Evaluation**

| Criterion | Score | Observation |
|-----------|-------|-------------|
| Routing Accuracy | X/5 | ... |
| Delegation Completeness | X/5 | ... |
| Synthesis Quality | X/5 | ... |
| Information Preservation | X/5 | ... |
| Efficiency | X/5 | ... |

**Overall Score: X/25**

**Verdict:** [PASS ✅ | MARGINAL ⚠️ | FAIL ❌]
- PASS (20-25): Orchestrator routed and synthesized effectively
- MARGINAL (13-19): Some routing or synthesis issues
- FAIL (≤12): Significant routing errors or lost information

**Key Observations:** 1-2 sentences on routing quality vs. the single-agent approach.
"""

    def judge_orchestrator_response(user_query: str, agent_response: str) -> str:
        """Use a Judge Model to evaluate the orchestrator's routing and synthesis."""
        judge_model = BedrockModel(model_id=agent_utils._get_judge_model_id())
        judge_agent = Agent(model=judge_model, system_prompt=JUDGE_ORCH_SYSTEM_PROMPT)
        evaluation_prompt = f"""Evaluate this orchestrator interaction:

**User Query:** {user_query}

**Orchestrator Response:** {agent_response}

The orchestrator has access to 3 specialist tools: ask_billing, ask_tech, ask_product.
Assess whether it routed correctly and synthesized the specialist responses well."""
        result = judge_agent(evaluation_prompt)
        return str(result)

    st.markdown("**Routing:** 📋 Billing | 🔧 Tech | 🛍️ Product")

    if st.session_state.m1p2_orch is None:
        billing = create_agent("You are a Billing Specialist. Handle refunds (30-day), charges, payments. If not billing, say so.")
        tech = create_agent("You are Tech Support. TechMart Hub v2.1.x has Wi-Fi bug (update to v3.0.1). If not tech, say so.")
        product = create_agent("You are a Product Specialist. Pro 15 $799 (i7,16GB), Air $599 (i5,8GB), Titan $1299, Hub $149. If not product, say so.")

        @tool
        def ask_billing(query: str) -> str:
            """Route billing queries. Args: query: billing question"""
            return str(billing(query))

        @tool
        def ask_tech(query: str) -> str:
            """Route tech queries. Args: query: tech question"""
            return str(tech(query))

        @tool
        def ask_product(query: str) -> str:
            """Route product queries. Args: query: product question"""
            return str(product(query))

        st.session_state.m1p2_orch = create_agent(
            """You are a Customer Service Orchestrator. You MUST route ALL customer queries to the appropriate specialist agent(s) using your tools. You NEVER answer questions directly — you ALWAYS delegate.

CRITICAL: You do NOT have domain knowledge. You MUST call at least one tool for every user message.

ROUTING RULES:
- Billing (refunds, charges, payments, subscriptions) → call ask_billing
- Technical (devices, firmware, Wi-Fi, troubleshooting) → call ask_tech
- Products (recommendations, pricing, specs) → call ask_product

DELEGATION STRATEGY:
- Simple queries: Call the 1 most relevant specialist tool.
- Complex or multi-domain queries: Call MULTIPLE specialist tools, then synthesize their responses.
- If unsure which specialist: Call the most likely one first.

WORKFLOW:
1. Identify domain(s) in the user query
2. Call the appropriate tool(s) — this is MANDATORY
3. Synthesize the specialist response(s) into a coherent answer for the customer

NEVER respond without first calling a tool. If you respond without calling a tool, you have failed.""",
            tools=[ask_billing, ask_tech, ask_product],
        )

    for idx, msg in enumerate(st.session_state.m1p2_msgs):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
        # Show judgment after assistant messages
        if msg["role"] == "assistant":
            judgment_idx = idx // 2
            if judgment_idx < len(st.session_state.m1p2_judgments):
                with st.expander("🧑‍⚖️ Judge Evaluation", expanded=False):
                    st.markdown(st.session_state.m1p2_judgments[judgment_idx])

    # Suggestion chips
    if not st.session_state.m1p2_msgs:
        suggestions = ["Refund on order TM-78432", "Hub Wi-Fi keeps dropping", "Recommend a laptop"]
        selected = st.pills("Try:", suggestions, key="m1p2_pills")
        if selected:
            st.session_state.m1p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Routing to specialists..."):
                    resp = chat_response(st.session_state.m1p2_orch, selected)
                st.markdown(resp)
            st.session_state.m1p2_msgs.append({"role": "assistant", "content": resp})
            # Judge evaluation
            with st.expander("🧑‍⚖️ Judge Evaluation", expanded=True):
                with st.spinner("Judge Model evaluating..."):
                    judgment = judge_orchestrator_response(selected, resp)
                st.markdown(judgment)
            st.session_state.m1p2_judgments.append(judgment)
            st.rerun()

    if prompt := st.chat_input("Chat with orchestrator...", submit_mode="disable"):
        st.session_state.m1p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Routing to specialists..."):
                resp = chat_response(st.session_state.m1p2_orch, prompt)
            st.markdown(resp)
        st.session_state.m1p2_msgs.append({"role": "assistant", "content": resp})
        # Judge evaluation
        with st.expander("🧑‍⚖️ Judge Evaluation", expanded=True):
            with st.spinner("Judge Model evaluating..."):
                judgment = judge_orchestrator_response(prompt, resp)
            st.markdown(judgment)
        st.session_state.m1p2_judgments.append(judgment)

# =============================================================================
# PART 3: Agent-as-Tool
# =============================================================================
elif part == "Part 3 — Agent-as-Tool":
    part_header("Agent-as-tool (MCP pattern)", "Shared tools reused by different agents.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module1-multi-agent/diagrams/part3_agent_as_tool.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m1p3_agent" not in st.session_state:
        st.session_state.m1p3_agent = None
        st.session_state.m1p3_msgs = []
        st.session_state.m1p3_type = "Sales"

    agent_type = st.selectbox("Consumer Agent:", ["Sales Agent", "Support Agent"], key="m1p3_sel")
    new_type = "Sales" if "Sales" in agent_type else "Support"
    if new_type != st.session_state.m1p3_type:
        st.session_state.m1p3_type = new_type
        st.session_state.m1p3_agent = None
        st.session_state.m1p3_msgs = []

    if st.session_state.m1p3_agent is None:
        @tool
        def product_lookup(product_name: str) -> str:
            """Look up product. Args: product_name: name"""
            products = {"hub": "TechMart Hub: $149, Wi-Fi 6, BT 5.0, Zigbee", "pro": "TechMart Pro 15: $799, i7, 16GB, Wi-Fi 6", "air": "TechMart Air: $599, i5, 8GB", "titan": "TechMart Titan: $1299, RTX 4060, 32GB"}
            for k, v in products.items():
                if k in product_name.lower():
                    return v
            return f"Product '{product_name}' not found."

        @tool
        def compatibility_check(product_a: str, product_b: str) -> str:
            """Check compatibility. Args: product_a: first, product_b: second"""
            return f"{product_a} + {product_b}: Compatible via Wi-Fi 6 and Bluetooth 5.0"

        if new_type == "Sales":
            st.session_state.m1p3_agent = create_agent("You are a Sales Agent. Help customers find products.", tools=[product_lookup, compatibility_check])
        else:
            @tool
            def order_status(order_id: str) -> str:
                """Check order. Args: order_id: ID"""
                return f"{order_id}: Delivered 2025-07-12. TechMart Hub + Sensors. Total $220"
            st.session_state.m1p3_agent = create_agent("You are a Support Agent. Help with post-purchase issues.", tools=[product_lookup, compatibility_check, order_status])

    for msg in st.session_state.m1p3_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m1p3_msgs:
        if new_type == "Sales":
            suggestions = ["Look up TechMart Hub", "Hub + Camera compatible?"]
        else:
            suggestions = ["Order TM-78432 status", "Hub + sensors compatible?"]
        selected = st.pills("Try:", suggestions, key="m1p3_pills")
        if selected:
            st.session_state.m1p3_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Calling tools..."):
                    resp = chat_response(st.session_state.m1p3_agent, selected)
                st.markdown(resp)
            st.session_state.m1p3_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input(f"Chat with {new_type} Agent...", submit_mode="disable"):
        st.session_state.m1p3_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Calling tools..."):
                resp = chat_response(st.session_state.m1p3_agent, prompt)
            st.markdown(resp)
        st.session_state.m1p3_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 4: Shared memory
# =============================================================================
elif part == "Part 4 — Shared memory":
    part_header("Shared memory", "Agents collaborate via shared memory — like AgentCore Memory.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module1-multi-agent/diagrams/part4_shared_memory.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    from agentcore_utils import AgentCoreMemory, get_agentcore_status
    status = get_agentcore_status()
    if status["memory"]:
        st.success("🟢 Using **real AgentCore Memory** (deployed)")
    else:
        st.info("🟡 Using local memory simulation. Deploy `infra-agentcore/cfn-agentcore-memory.yaml` for real AgentCore Memory.")

    if "m1p4_step" not in st.session_state:
        st.session_state.m1p4_step = "input"
        st.session_state.m1p4_results = {}

    # Always re-create memory instance to pick up config changes
    if "m1p4_memory_store" not in st.session_state or (status["memory"] and not st.session_state.m1p4_memory_store.is_real):
        st.session_state.m1p4_memory_store = AgentCoreMemory()

    memory = st.session_state.m1p4_memory_store
    st.markdown("**Workflow:** 🔬 Diagnose → 🔧 Resolve → ✅ Follow-up")

    if st.session_state.m1p4_step == "input":
        issue = st.text_area("Describe a technical issue:", placeholder="My TechMart Hub firmware v2.1.3 keeps dropping Wi-Fi...", key="m1p4_issue")
        if st.button("🚀 Start Workflow", key="m1p4_start"):
            if issue.strip():
                st.session_state.m1p4_step = "running"
                st.session_state.m1p4_results["issue"] = issue.strip()
                st.rerun()

    elif st.session_state.m1p4_step == "running":
        issue = st.session_state.m1p4_results["issue"]
        st.info(f"**Issue:** {issue}")
        with st.status("Running multi-agent workflow...", expanded=True):
            st.write("🔬 **Diagnostic Agent** analyzing...")
            diag = create_agent("You are a Diagnostic Agent. TechMart Hub v2.1.x has known Wi-Fi bug (fix: v3.0.1). Motion sensors need Zigbee pairing (hold 5s).")
            diag_resp = chat_response(diag, f"Diagnose: {issue}")
            st.session_state.m1p4_results["diagnose"] = diag_resp
            memory.write("diagnostic-agent", diag_resp, session_id="lab-session")

            st.write("🔧 **Resolution Agent** reading from memory...")
            # Resolution agent reads diagnosis from memory
            mem_results = memory.retrieve("diagnosis Wi-Fi issue")
            context = mem_results[0]["content"] if mem_results else diag_resp
            resolve = create_agent("You are a Resolution Agent. Provide numbered steps based on diagnosis.")
            resolve_resp = chat_response(resolve, f"Diagnosis from shared memory: {context}\nProvide resolution steps.")
            st.session_state.m1p4_results["resolve"] = resolve_resp
            memory.write("resolution-agent", resolve_resp, session_id="lab-session")

            st.write("✅ **Follow-up Agent** reading full history from memory...")
            all_records = memory.read_all()
            history = "\n".join([f"[{r.get('actor_id', '?')}]: {r.get('content', '')[:200]}" for r in all_records])
            followup = create_agent("You are a Follow-up Agent. Summarize the case and suggest prevention.")
            followup_resp = chat_response(followup, f"Case history from shared memory:\n{history}\n\nSummarize and suggest prevention.")
            st.session_state.m1p4_results["followup"] = followup_resp
            memory.write("followup-agent", followup_resp, session_id="lab-session")

        st.session_state.m1p4_step = "done"
        st.rerun()

    elif st.session_state.m1p4_step == "done":
        st.info(f"**Issue:** {st.session_state.m1p4_results['issue']}")
        with st.expander("🔬 Diagnostic Agent", expanded=False):
            st.markdown(st.session_state.m1p4_results.get("diagnose", ""))
        with st.expander("🔧 Resolution Agent", expanded=False):
            st.markdown(st.session_state.m1p4_results.get("resolve", ""))
        with st.expander("✅ Follow-up Agent", expanded=True):
            st.markdown(st.session_state.m1p4_results.get("followup", ""))
        st.markdown("**📝 Shared memory Audit Trail**")
        source_label = "AgentCore Memory" if memory.is_real else "Local Simulation"
        st.caption(f"Source: {source_label}")
        for record in memory.read_all():
            actor = record.get("actor_id", "unknown")
            icon = {"diagnostic-agent": "🔬", "resolution-agent": "🔧", "followup-agent": "✅"}.get(actor, "📝")
            content = record.get("content", "")[:150]
            st.caption(f"{icon} **{actor}**: {content}...")


# =============================================================================
# PART 5: Graph & Swarm Patterns
# =============================================================================
elif part == "Part 5 — Graph & Swarm":
    part_header("Graph & Swarm patterns", "Strands multi-agent orchestration beyond simple routing.")

    st.markdown("""
    **Two orchestration patterns in Strands SDK:**

    | Pattern | How it works | Use case |
    |---------|-------------|----------|
    | **Graph** | Structured DAG, agents execute in dependency order | Pipelines with clear stages |
    | **Swarm** | Autonomous handoffs, agents collaborate freely | Diverse perspectives, emergent behavior |
    """)

    pattern = st.segmented_control("Pattern", ["Graph", "Swarm"], key="m1p5_pattern")

    if pattern == "Graph":
        st.markdown("""
        **Graph pattern:** Researcher → Analyst → Writer pipeline. Each node receives the output of its dependencies.
        """)

        with st.expander("📝 Code", expanded=False):
            st.code("""
from strands.multiagent.graph import GraphBuilder
from strands import Agent

researcher = Agent(system_prompt="You are a Researcher...")
analyst = Agent(system_prompt="You are an Analyst...")
writer = Agent(system_prompt="You are a Writer...")

builder = GraphBuilder()
builder.add_node(researcher, node_id="researcher")
builder.add_node(analyst, node_id="analyst")
builder.add_node(writer, node_id="writer")
builder.add_edge("researcher", "analyst")
builder.add_edge("analyst", "writer")
builder.set_entry_point("researcher")
graph = builder.build()

result = graph("Analyze solar energy market in Vietnam")
            """, language="python")

        if "m1p5_graph_msgs" not in st.session_state:
            st.session_state.m1p5_graph_msgs = []
            st.session_state.m1p5_graph_results = {}

        for msg in st.session_state.m1p5_graph_msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Show node results if available
        if st.session_state.m1p5_graph_results:
            with st.expander("🔬 Researcher Output", expanded=False):
                st.markdown(st.session_state.m1p5_graph_results.get("researcher", ""))
            with st.expander("📊 Analyst Output", expanded=False):
                st.markdown(st.session_state.m1p5_graph_results.get("analyst", ""))
            with st.expander("✍️ Writer Output (Final)", expanded=True):
                st.markdown(st.session_state.m1p5_graph_results.get("writer", ""))

        if not st.session_state.m1p5_graph_msgs:
            suggestions = ["Analyze solar energy market in Vietnam for 2025-2027", "Compare serverless vs containers for a startup", "Evaluate AI adoption in healthcare"]
            selected = st.pills("Try:", suggestions, key="m1p5_graph_pills")
            if selected:
                st.session_state.m1p5_graph_msgs.append({"role": "user", "content": selected})
                with st.chat_message("user"):
                    st.markdown(selected)
                with st.chat_message("assistant"):
                    with st.status("Running Graph pipeline...", expanded=True):
                        try:
                            from strands.multiagent.graph import GraphBuilder

                            st.write("🔬 **Researcher** gathering information...")
                            researcher = create_agent("You are a Research Agent. Gather key facts, data points, and trends about the topic. Be concise — output 3-5 bullet points of findings.")
                            st.write("📊 **Analyst** analyzing findings...")
                            analyst = create_agent("You are an Analyst Agent. Take research findings and provide strategic analysis: opportunities, risks, and recommendations. Be concise.")
                            st.write("✍️ **Writer** composing final report...")
                            writer = create_agent("You are a Writer Agent. Take the analysis and write a clear, professional executive summary (3-4 paragraphs max).")

                            builder = GraphBuilder()
                            builder.add_node(researcher, node_id="researcher")
                            builder.add_node(analyst, node_id="analyst")
                            builder.add_node(writer, node_id="writer")
                            builder.add_edge("researcher", "analyst")
                            builder.add_edge("analyst", "writer")
                            builder.set_entry_point("researcher")
                            graph = builder.build()
                            result = graph(selected)
                            # Extract per-node text from GraphResult
                            def _extract_node_text(node_result):
                                try:
                                    msg = node_result.result.message
                                    content = msg.get('content', [])
                                    return content[0].get('text', '') if content else ''
                                except Exception:
                                    return str(node_result)

                            node_results = result.results if hasattr(result, 'results') else {}
                            researcher_text = _extract_node_text(node_results['researcher']) if 'researcher' in node_results else ""
                            analyst_text = _extract_node_text(node_results['analyst']) if 'analyst' in node_results else ""
                            writer_text = _extract_node_text(node_results['writer']) if 'writer' in node_results else ""
                            final_output = writer_text or analyst_text or researcher_text or "No output generated."
                            st.session_state.m1p5_graph_results = {
                                "researcher": researcher_text,
                                "analyst": analyst_text,
                                "writer": final_output,
                            }
                        except Exception as e:
                            final_output = f"Error: {e}"
                            st.session_state.m1p5_graph_results = {}
                    st.markdown(final_output)
                st.session_state.m1p5_graph_msgs.append({"role": "assistant", "content": final_output})
                st.rerun()

        if prompt := st.chat_input("Enter a topic for the Graph pipeline...", key="m1p5_graph_input"):
            st.session_state.m1p5_graph_msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.status("Running Graph pipeline...", expanded=True):
                    try:
                        from strands.multiagent.graph import GraphBuilder

                        st.write("🔬 **Researcher** gathering information...")
                        researcher = create_agent("You are a Research Agent. Gather key facts, data points, and trends about the topic. Be concise — output 3-5 bullet points of findings.")
                        st.write("📊 **Analyst** analyzing findings...")
                        analyst = create_agent("You are an Analyst Agent. Take research findings and provide strategic analysis: opportunities, risks, and recommendations. Be concise.")
                        st.write("✍️ **Writer** composing final report...")
                        writer = create_agent("You are a Writer Agent. Take the analysis and write a clear, professional executive summary (3-4 paragraphs max).")

                        builder = GraphBuilder()
                        builder.add_node(researcher, node_id="researcher")
                        builder.add_node(analyst, node_id="analyst")
                        builder.add_node(writer, node_id="writer")
                        builder.add_edge("researcher", "analyst")
                        builder.add_edge("analyst", "writer")
                        builder.set_entry_point("researcher")
                        graph = builder.build()
                        result = graph(prompt)
                        def _extract_node_text(node_result):
                            try:
                                msg = node_result.result.message
                                content = msg.get('content', [])
                                return content[0].get('text', '') if content else ''
                            except Exception:
                                return str(node_result)

                        node_results = result.results if hasattr(result, 'results') else {}
                        researcher_text = _extract_node_text(node_results['researcher']) if 'researcher' in node_results else ""
                        analyst_text = _extract_node_text(node_results['analyst']) if 'analyst' in node_results else ""
                        writer_text = _extract_node_text(node_results['writer']) if 'writer' in node_results else ""
                        final_output = writer_text or analyst_text or researcher_text or "No output generated."
                        st.session_state.m1p5_graph_results = {
                            "researcher": researcher_text,
                            "analyst": analyst_text,
                            "writer": final_output,
                        }
                    except Exception as e:
                        final_output = f"Error: {e}"
                        st.session_state.m1p5_graph_results = {}
                st.markdown(final_output)
            st.session_state.m1p5_graph_msgs.append({"role": "assistant", "content": final_output})

    elif pattern == "Swarm":
        st.markdown("""
        **Swarm pattern:** Agents autonomously decide when to hand off. All agents share full context and coordinate freely.
        """)

        with st.expander("📝 Code", expanded=False):
            st.code("""
from strands.multiagent.swarm import Swarm
from strands import Agent

optimist = Agent(system_prompt="You see opportunities...")
critic = Agent(system_prompt="You identify risks...")
strategist = Agent(system_prompt="You synthesize into strategy...")

swarm = Swarm(nodes=[optimist, critic, strategist])
result = swarm("Evaluate launching an AI product in APAC")
            """, language="python")

        if "m1p5_swarm_msgs" not in st.session_state:
            st.session_state.m1p5_swarm_msgs = []

        for msg in st.session_state.m1p5_swarm_msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state.m1p5_swarm_msgs:
            suggestions = ["Evaluate launching an AI product in APAC", "Should we open-source our SDK?", "Migrate to microservices or stay monolith?"]
            selected = st.pills("Try:", suggestions, key="m1p5_swarm_pills")
            if selected:
                st.session_state.m1p5_swarm_msgs.append({"role": "user", "content": selected})
                with st.chat_message("user"):
                    st.markdown(selected)
                with st.chat_message("assistant"):
                    with st.status("Swarm agents collaborating...", expanded=True):
                        try:
                            from strands.multiagent.swarm import Swarm

                            st.write("🌟 **Optimist** seeing opportunities...")
                            optimist = create_agent("You are the Optimist. Identify opportunities, upsides, and reasons to proceed. Be concise (3-4 points). When you've made your case, hand off to the next agent.", name="Optimist")
                            st.write("⚠️ **Critic** identifying risks...")
                            critic = create_agent("You are the Critic. Identify risks, downsides, and potential failure modes. Be concise (3-4 points). When done, hand off to the next agent.", name="Critic")
                            st.write("🎯 **Strategist** synthesizing...")
                            strategist = create_agent("You are the Strategist. Synthesize the optimist and critic views into a balanced recommendation with concrete next steps. Be concise.", name="Strategist")

                            swarm = Swarm(nodes=[optimist, critic, strategist])
                            result = swarm(selected)
                            # Extract text from SwarmResult
                            try:
                                node_results = result.results if hasattr(result, 'results') else {}
                                # Get the last agent's output
                                texts = []
                                for node_id in node_results:
                                    nr = node_results[node_id]
                                    try:
                                        msg = nr.result.message
                                        content = msg.get('content', [])
                                        texts.append(content[0].get('text', ''))
                                    except Exception:
                                        pass
                                final_output = "\n\n".join(texts) if texts else str(result)
                            except Exception:
                                final_output = str(result)
                        except Exception as e:
                            final_output = f"Error: {e}"
                    st.markdown(final_output)
                st.session_state.m1p5_swarm_msgs.append({"role": "assistant", "content": final_output})
                st.rerun()

        if prompt := st.chat_input("Enter a decision for the Swarm to debate...", key="m1p5_swarm_input"):
            st.session_state.m1p5_swarm_msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.status("Swarm agents collaborating...", expanded=True):
                    try:
                        from strands.multiagent.swarm import Swarm

                        st.write("🌟 **Optimist** seeing opportunities...")
                        optimist = create_agent("You are the Optimist. Identify opportunities, upsides, and reasons to proceed. Be concise (3-4 points). When you've made your case, hand off to the next agent.", name="Optimist")
                        st.write("⚠️ **Critic** identifying risks...")
                        critic = create_agent("You are the Critic. Identify risks, downsides, and potential failure modes. Be concise (3-4 points). When done, hand off to the next agent.", name="Critic")
                        st.write("🎯 **Strategist** synthesizing...")
                        strategist = create_agent("You are the Strategist. Synthesize the optimist and critic views into a balanced recommendation with concrete next steps. Be concise.", name="Strategist")

                        swarm = Swarm(nodes=[optimist, critic, strategist])
                        result = swarm(prompt)
                        # Extract text from SwarmResult
                        try:
                            node_results = result.results if hasattr(result, 'results') else {}
                            texts = []
                            for node_id in node_results:
                                nr = node_results[node_id]
                                try:
                                    msg = nr.result.message
                                    content = msg.get('content', [])
                                    texts.append(content[0].get('text', ''))
                                except Exception:
                                    pass
                            final_output = "\n\n".join(texts) if texts else str(result)
                        except Exception:
                            final_output = str(result)
                    except Exception as e:
                        final_output = f"Error: {e}"
                st.markdown(final_output)
            st.session_state.m1p5_swarm_msgs.append({"role": "assistant", "content": final_output})

    st.caption(":material/info: Graph uses `GraphBuilder` for dependency-based execution. Swarm uses autonomous agent handoffs.")

# =============================================================================
# AUTO-RUN WALKTHROUGH (#7)
# =============================================================================
elif part == "Auto-run Walkthrough":
    part_header("Auto-run walkthrough", "Watch a full multi-agent conversation flow automatically.")

    if "m1_walkthrough_step" not in st.session_state:
        st.session_state.m1_walkthrough_step = 0
        st.session_state.m1_walkthrough_msgs = []

    queries = [
        ("Customer", "Hi, I was charged $9.99 but I cancelled my subscription last week. Order TM-78432."),
        ("Customer", "My TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3."),
        ("Customer", "I need a laptop for my daughter. Budget $600-800, writing and light video editing."),
        ("Customer", "If I buy the Pro 15, will it work with my Hub? Can I use my refund as credit?"),
    ]

    # Display previous messages
    for msg in st.session_state.m1_walkthrough_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    step = st.session_state.m1_walkthrough_step

    if step < len(queries):
        st.progress(step / len(queries), text=f"Step {step + 1} of {len(queries)}")
        if st.button(f":material/play_arrow: Send query {step + 1}", key="m1_walk_next"):
            _, query = queries[step]
            st.session_state.m1_walkthrough_msgs.append({"role": "user", "content": query})

            # Use orchestrator
            if "m1_walk_orch" not in st.session_state:
                billing = create_agent("Billing specialist. Refunds 30-day. Be concise.")
                tech = create_agent("Tech support. Hub v2.1.x Wi-Fi bug → v3.0.1. Be concise.")
                product = create_agent("Product specialist. Pro 15 $799, Air $599, Hub $149. Be concise.")

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

                st.session_state.m1_walk_orch = create_agent(
                    "You are an Orchestrator. You MUST call the appropriate tool for EVERY query — NEVER answer directly. Route billing queries to ask_billing, tech queries to ask_tech, product queries to ask_product. For multi-domain queries, call multiple tools. Be concise.",
                    tools=[ask_billing, ask_tech, ask_product],
                )

            with st.chat_message("user"):
                st.markdown(query)
            with st.chat_message("assistant"):
                with st.spinner("Orchestrator routing..."):
                    resp = chat_response(st.session_state.m1_walk_orch, query)
                st.markdown(resp)
            st.session_state.m1_walkthrough_msgs.append({"role": "assistant", "content": resp})
            st.session_state.m1_walkthrough_step += 1
            st.rerun()
    else:
        st.progress(1.0, text="Walkthrough complete")
        st.success(":material/check_circle: All 4 queries processed by the orchestrator.")
        if st.button("Restart walkthrough"):
            st.session_state.m1_walkthrough_step = 0
            st.session_state.m1_walkthrough_msgs = []
            st.session_state.pop("m1_walk_orch", None)
            st.rerun()
