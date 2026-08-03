"""Module 1: Multi-Agent Architecture."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from style import inject_css, part_header
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

    for msg in st.session_state.m1p1_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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
            """You are a Customer Service Orchestrator. Route queries to specialists.

ROUTING RULES:
- Billing (refunds, charges) → ask_billing
- Technical (devices, firmware) → ask_tech
- Products (recommendations) → ask_product

DELEGATION STRATEGY:
- Simple fact-finding (price, status): Route to 1 specialist, expect 1 tool call.
- Complex queries spanning domains: Route to multiple specialists, synthesize responses.
- If unsure which specialist: Route to the most likely one first.

For multi-domain queries, break into parts and route each to the appropriate specialist.""",
            tools=[ask_billing, ask_tech, ask_product],
        )

    for msg in st.session_state.m1p2_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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
    **Three orchestration patterns in Strands SDK:**

    | Pattern | How it works | Use case |
    |---------|-------------|----------|
    | **Workflow** | Pre-defined DAG, sequential | Repeatable pipelines |
    | **Graph** | Structured flowchart, agents decide paths | Branching logic |
    | **Swarm** | Autonomous handoffs, emergent behavior | Diverse perspectives |
    """)

    pattern = st.segmented_control("Pattern", ["Graph", "Swarm"], key="m1p5_pattern")

    if pattern == "Graph":
        st.markdown("""
        **Graph pattern:** Nodes = agents, Edges = dependencies. Execution follows the graph, respecting dependencies.
        Output from one node becomes input for dependent nodes.
        """)
        st.code("""
from strands.multiagent import Graph, Node

graph = Graph()
graph.add_node(Node("researcher", agent=researcher))
graph.add_node(Node("analyst", agent=analyst, depends_on=["researcher"]))
graph.add_node(Node("writer", agent=writer, depends_on=["analyst"]))

result = graph("Analyze solar energy market in Vietnam")
        """, language="python")

    elif pattern == "Swarm":
        st.markdown("""
        **Swarm pattern:** Each agent decides when to hand off. All agents share full context
        including task description, history, and available agents.
        """)
        st.code("""
from strands.multiagent import Swarm

swarm = Swarm(agents=[researcher, analyst, writer])
result = swarm(
    "Research and write a report on solar energy",
    invocation_state={"budget": "$100K", "region": "APAC"}
)
        """, language="python")

    st.caption(":material/info: These patterns use `invocation_state` to share state across agents via `ToolContext`.")

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
                    "Orchestrator: route to ask_billing, ask_tech, ask_product. Be concise.",
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
