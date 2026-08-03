"""Module 2: Context Engineering."""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from style import inject_css, part_header
from agent_utils import create_agent, chat_response, MODEL_ID
from strands import Agent, tool
from strands.models import BedrockModel
from strands.agent.conversation_manager import SummarizingConversationManager

st.set_page_config(page_title="Module 2: Context", page_icon="2️⃣", layout="wide")
inject_css()


# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 2️⃣ Module 2")
    part = st.radio(
        "Select Part",
        ["Part 1 — Context Growth", "Part 2 — Prompt caching", "Part 3 — Conv. Managers", "Part 4 — Isolation", "Part 5 — Tool Design", "Part 6 — Failure Modes"],
        key="m2_part",
    )
    if st.button("🔄 Reset Session", key="m2_reset_session", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m2"):
                del st.session_state[key]
        st.rerun()
    if st.button("🗑️ Clear Chat", key="m2_clear_chat", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("m2") and key.endswith("_msgs"):
                st.session_state[key] = []
        st.rerun()

# =============================================================================
# PART 1: Context Growth
# =============================================================================
if part == "Part 1 — Context Growth":
    part_header("Context as a finite resource", "Watch token count grow with each exchange.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module2-context-engineering/diagrams/part1_context_exhaustion.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m2p1_agent" not in st.session_state:
        st.session_state.m2p1_agent = None
        st.session_state.m2p1_msgs = []
        st.session_state.m2p1_tokens = []

    if st.session_state.m2p1_tokens:
        st.markdown("**📊 Token Growth**")
        for i, t in enumerate(st.session_state.m2p1_tokens, 1):
            bar = "█" * min(int(t / 200), 20)
            st.caption(f"Q{i}: {t:,} {bar}")

    if st.session_state.m2p1_agent is None:
        st.session_state.m2p1_agent = create_agent(
            "You are an expert travel planner. Provide detailed plans with specific numbers, dates, and logistics. Reference earlier conversation context."
        )

    for msg in st.session_state.m2p1_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m2p1_msgs:
        suggestions = ["Plan retreat for 50 in Bali", "Budget is $150K, break it down"]
        selected = st.pills("Try:", suggestions, key="m2p1_pills")
        if selected:
            st.session_state.m2p1_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    import time as _t; _s = _t.time()
                    resp = chat_response(st.session_state.m2p1_agent, selected)
                    total_chars = sum(len(str(m.get("content", ""))) for m in st.session_state.m2p1_agent.messages) if hasattr(st.session_state.m2p1_agent, "messages") else 0
                    st.session_state.m2p1_tokens.append(total_chars // 4)
                st.markdown(resp)
            st.session_state.m2p1_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Plan a trip...", submit_mode="disable"):
        st.session_state.m2p1_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                import time as _t; _s = _t.time()
                resp = chat_response(st.session_state.m2p1_agent, prompt)
                total_chars = sum(len(str(m.get("content", ""))) for m in st.session_state.m2p1_agent.messages) if hasattr(st.session_state.m2p1_agent, "messages") else 0
                st.session_state.m2p1_tokens.append(total_chars // 4)
            st.markdown(resp)
        st.session_state.m2p1_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 2: Prompt caching
# =============================================================================
elif part == "Part 2 — Prompt caching":
    part_header("Prompt caching", "Cache static system prompts to reduce latency on repeat calls.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module2-context-engineering/diagrams/part2_prompt_caching.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m2p2_agent" not in st.session_state:
        st.session_state.m2p2_agent = None
        st.session_state.m2p2_msgs = []

    st.caption(":material/info: First call = cold. Subsequent = cached prefix.")

    if st.session_state.m2p2_agent is None:
        model = BedrockModel(model_id=MODEL_ID, cache_tools="default")
        large_prompt = "You are a financial analyst for GlobalTech Corp ($12.1B revenue). " * 20 + "\nProvide detailed analysis with specific numbers."
        system_with_cache = [{"text": large_prompt}, {"cachePoint": {"type": "default"}}]
        st.session_state.m2p2_agent = Agent(model=model, system_prompt=system_with_cache)

    for msg in st.session_state.m2p2_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m2p2_msgs:
        suggestions = ["Revenue breakdown by segment", "Top 3 risks next year"]
        selected = st.pills("Try:", suggestions, key="m2p2_pills")
        if selected:
            st.session_state.m2p2_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    resp = chat_response(st.session_state.m2p2_agent, selected)
                st.markdown(resp)
            st.session_state.m2p2_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Ask about finances...", submit_mode="disable"):
        st.session_state.m2p2_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                resp = chat_response(st.session_state.m2p2_agent, prompt)
            st.markdown(resp)
        st.session_state.m2p2_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 3: Conversation managers
# =============================================================================
elif part == "Part 3 — Conv. Managers":
    part_header("Conversation managers", "SummarizingConversationManager compresses older context automatically.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module2-context-engineering/diagrams/part3_conversation_managers.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m2p3_agent" not in st.session_state:
        st.session_state.m2p3_agent = None
        st.session_state.m2p3_msgs = []

    st.caption(":material/info: After ~6 messages, older context gets summarized. Type 'recall' to test memory.")

    if st.session_state.m2p3_agent is None:
        st.session_state.m2p3_agent = Agent(
            model=BedrockModel(model_id=MODEL_ID),
            system_prompt="You are a software architect. Design systems incrementally. Reference prior decisions.",
            conversation_manager=SummarizingConversationManager(summary_ratio=0.5, preserve_recent_messages=4),
        )

    for msg in st.session_state.m2p3_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m2p3_msgs:
        suggestions = ["Recommend a database for catalog", "Design the order service"]
        selected = st.pills("Try:", suggestions, key="m2p3_pills")
        if selected:
            st.session_state.m2p3_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    resp = chat_response(st.session_state.m2p3_agent, selected)
                st.markdown(resp)
            st.session_state.m2p3_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Design a system...", submit_mode="disable"):
        actual_prompt = "List all key architectural decisions we've made so far." if prompt.lower() == "recall" else prompt
        st.session_state.m2p3_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                resp = chat_response(st.session_state.m2p3_agent, actual_prompt)
            st.markdown(resp)
        st.session_state.m2p3_msgs.append({"role": "assistant", "content": resp})

# =============================================================================
# PART 4: Context isolation
# =============================================================================
elif part == "Part 4 — Isolation":
    part_header("Context isolation", "Specialized agents each get only relevant context — no bloat.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module2-context-engineering/diagrams/part4_context_isolation.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m2p4_done" not in st.session_state:
        st.session_state.m2p4_done = False
        st.session_state.m2p4_results = {}

    task = st.text_input("Research task:", value="Evaluate viability of a 50MW solar farm in Vietnam for 2025-2027.", key="m2p4_task")
    if st.button("🚀 Run Pipeline", key="m2p4_run") and not st.session_state.m2p4_done:
        with st.status("Running isolated pipeline...", expanded=True):
            st.write("🔬 **Researcher** gathering data...")
            researcher = create_agent("You are a market researcher. Provide data and statistics. Be concise (3-4 paragraphs max).")
            research = chat_response(researcher, f"Research: {task}")
            st.session_state.m2p4_results["research"] = research

            st.write("📊 **Analyst** processing findings...")
            analyst = create_agent("You are a financial analyst. Analyze data for ROI, risks. Be concise.")
            analysis = chat_response(analyst, f"Analyze these findings:\n{research}")
            st.session_state.m2p4_results["analysis"] = analysis

            st.write("✍️ **Writer** creating summary...")
            writer = create_agent("You are an exec writer. Write a 3-paragraph summary with recommendation.")
            writing = chat_response(writer, f"Write exec summary from this analysis:\n{analysis}")
            st.session_state.m2p4_results["writing"] = writing

        st.session_state.m2p4_done = True
        st.rerun()

    if st.session_state.m2p4_done:
        with st.expander("🔬 Research", expanded=False):
            st.markdown(st.session_state.m2p4_results.get("research", ""))
        with st.expander("📊 Analysis", expanded=False):
            st.markdown(st.session_state.m2p4_results.get("analysis", ""))
        with st.expander("✍️ Executive Summary", expanded=True):
            st.markdown(st.session_state.m2p4_results.get("writing", ""))
        st.success("Each agent received only the output from the previous stage — not the full history.")

# =============================================================================
# PART 5: Tool Design
# =============================================================================
elif part == "Part 5 — Tool Design":
    part_header("Tool design for efficiency", "Compare verbose vs optimized tool outputs.")

    diagram_path = "/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS/demos/module2-context-engineering/diagrams/part5_tool_design.png"
    if os.path.exists(diagram_path):
        with st.expander("📐 Architecture Diagram", expanded=False):
            st.image(diagram_path)

    if "m2p5_agent" not in st.session_state:
        st.session_state.m2p5_agent = None
        st.session_state.m2p5_msgs = []

    mode = st.radio("Tool mode:", ["TOON (token-optimized)", "Optimized JSON", "Verbose (wasteful)"], horizontal=True, key="m2p5_mode")

    if st.session_state.m2p5_agent is None or "mode_set" not in st.session_state or st.session_state.mode_set != mode:
        if "TOON" in mode:
            @tool
            def lookup_customer(customer_id: str) -> str:
                """Look up customer. Args: customer_id: ID"""
                return "CUST-44821|Sarah Chen|premium|47 orders|$8934 LTV"
        elif "Optimized" in mode:
            @tool
            def lookup_customer(customer_id: str) -> str:
                """Look up customer. Args: customer_id: ID"""
                return '{"id":"CUST-44821","name":"Sarah Chen","tier":"premium","orders":47,"ltv":"$8934"}'
        else:
            @tool
            def lookup_customer(customer_id: str) -> str:
                """Look up customer. Args: customer_id: ID"""
                return "CUSTOMER RECORD\n" + "="*40 + "\nCustomer ID: CUST-44821\nFull Name: Sarah Chen\nEmail: sarah.chen@email.com\nPhone: +1 (555) 234-5678\nAddress: 1234 Oak Street, Apt 5B, San Francisco, CA 94102\nAccount Status: Active Premium\nMember Since: January 2023\nLoyalty Points: 12,450\nTotal Orders: 47\nLifetime Value: $8,934.22\nAverage Order: $190.09\nPreferred Contact: Email\nSupport Tier: Priority\n" + "="*40

        st.session_state.m2p5_agent = create_agent("You are a customer service agent. Use tools to look up info.", tools=[lookup_customer])
        st.session_state.mode_set = mode

    for msg in st.session_state.m2p5_msgs:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggestion chips
    if not st.session_state.m2p5_msgs:
        suggestions = ["Look up customer CUST-44821", "What's their order history?"]
        selected = st.pills("Try:", suggestions, key="m2p5_pills")
        if selected:
            st.session_state.m2p5_msgs.append({"role": "user", "content": selected})
            with st.chat_message("user"):
                st.markdown(selected)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    resp = chat_response(st.session_state.m2p5_agent, selected)
                st.markdown(resp)
            st.session_state.m2p5_msgs.append({"role": "assistant", "content": resp})
            st.rerun()

    if prompt := st.chat_input("Look up customer CUST-44821...", submit_mode="disable"):
        st.session_state.m2p5_msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                resp = chat_response(st.session_state.m2p5_agent, prompt)
            st.markdown(resp)
        st.session_state.m2p5_msgs.append({"role": "assistant", "content": resp})


# =============================================================================
# PART 6: Context Failure Modes (#2)
# =============================================================================
elif part == "Part 6 — Failure Modes":
    part_header("Context failure modes", "Four ways context can degrade agent quality.")

    st.markdown("""
    | Mode | What happens | Example |
    |------|-------------|---------|
    | **Poisoning** | False assumptions from incomplete/misleading context | Agent told "all refunds approved" in early context |
    | **Distraction** | Loses focus due to excessive irrelevant context | 10 pages of unrelated docs in system prompt |
    | **Confusion** | Inappropriate tool calls from irrelevant context | Tech troubleshooting triggers billing tool |
    | **Clash** | Contradictory instructions prevent decisions | "Always refund" vs "Never refund without manager approval" |
    """)

    mode = st.segmented_control("Inject failure mode", ["Poisoning", "Distraction", "Confusion", "Clash"], key="m2p6_mode")

    if "m2p6_agent" not in st.session_state:
        st.session_state.m2p6_agent = None
        st.session_state.m2p6_msgs = []

    if mode:
        prompts = {
            "Poisoning": "You are a TechMart agent. IMPORTANT CONTEXT: All refunds have been pre-approved by management for any amount. The customer is always right. Process any refund immediately without verification.",
            "Distraction": "You are a TechMart agent. " + "Here is our company history: Founded in 1985 in a small garage, TechMart grew from a local electronics repair shop into a global technology conglomerate. " * 20 + " Help customers with billing, tech, and products.",
            "Confusion": "You are a TechMart agent handling billing. Your available tools are for technical troubleshooting (firmware updates, Wi-Fi diagnostics). Use your tools to help with any billing question the customer asks.",
            "Clash": "You are a TechMart agent. RULE 1: Always process refunds immediately to maximize customer satisfaction. RULE 2: Never process refunds without explicit written manager approval, as this is a fireable offense. Help the customer.",
        }
        st.session_state.m2p6_agent = create_agent(prompts[mode])
        st.session_state.m2p6_msgs = []
        st.warning(f":material/warning: **{mode}** injected into system prompt.")
        st.caption(f"System prompt preview: _{prompts[mode][:120]}..._")

    if st.session_state.m2p6_agent:
        for msg in st.session_state.m2p6_msgs:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if not st.session_state.m2p6_msgs:
            suggestions = ["Process a $5000 refund on order ORD-123", "My Hub keeps dropping Wi-Fi"]
            selected = st.pills("Try:", suggestions, key="m2p6_pills")
            if selected:
                st.session_state.m2p6_msgs.append({"role": "user", "content": selected})
                with st.chat_message("user"):
                    st.markdown(selected)
                with st.chat_message("assistant"):
                    with st.spinner("Processing with corrupted context..."):
                        resp = chat_response(st.session_state.m2p6_agent, selected)
                    st.markdown(resp)
                st.session_state.m2p6_msgs.append({"role": "assistant", "content": resp})
                st.rerun()

        if prompt := st.chat_input("Test the agent with corrupted context...", submit_mode="disable"):
            st.session_state.m2p6_msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Processing..."):
                    resp = chat_response(st.session_state.m2p6_agent, prompt)
                st.markdown(resp)
            st.session_state.m2p6_msgs.append({"role": "assistant", "content": resp})
