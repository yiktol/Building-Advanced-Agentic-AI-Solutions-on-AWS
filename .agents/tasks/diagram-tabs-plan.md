# Implementation Plan — Tabbed navigation inside architecture-diagram sections

## Goal

For every architecture-diagram section on all 5 Streamlit module pages, replace the
bare `st.image(diagram_path)` inside the diagram area with `st.tabs(...)` so that:

- First tab `📐 Diagram` holds the existing image (guarded by `if os.path.exists(diagram_path)`;
  show `st.info("Diagram not available.")` in the `else` branch).
- Second tab `ℹ️ About` holds specific, accurate markdown about that exact part.
- Where a Code / comparison / policies tab already exists (Pattern B), the About tab is
  added so the result is `📐 Diagram`, `ℹ️ About`, then the existing extra tab(s) (preserved verbatim).

This is purely additive UI wrapping. No chat / judge / metrics / session_state logic changes.

## Design decisions (made here, grounded in the code read)

1. **Keep each diagram inside its existing `st.expander` (Pattern A) or existing expander
   wrapper (Pattern B).** The task requires it, and every Pattern A section is already
   wrapped in `with st.expander("📐 Architecture Diagram", expanded=False):`. For Pattern A
   the new `st.tabs(...)` goes directly inside that expander. Rationale: minimal structural
   change, preserves the collapse behavior users already have.

2. **Guard clause stays outer for Pattern A.** Pattern A currently reads:
   ```python
   if os.path.exists(diagram_path):
       with st.expander("📐 Architecture Diagram", expanded=False):
           st.image(diagram_path)
   ```
   If the whole block is only entered when the file exists, a missing diagram hides the
   expander entirely and the About tab would never show. The task explicitly wants an
   `st.info("Diagram not available.")` fallback *inside* the Diagram tab, and the About tab
   should always be reachable. **Decision:** restructure Pattern A so the expander is
   unconditional and the existence check moves *inside* the Diagram tab. The `diagram_path =`
   assignment stays exactly as-is (relative `os.path.join` form) and moves just above/into the
   expander. This is the one behavioral nuance; it makes the About tab always visible, matching
   the task intent. Pattern B already has the check inside the tab, so it is left in place.

3. **Tab labels exactly `📐 Diagram`, `ℹ️ About`, `📝 Code`.** Pattern B sections currently
   label the first tab `Architecture Diagram`; those labels are updated to `📐 Diagram` for
   consistency across all pages, and the existing second tab is renamed only by *prepending*
   its icon where helpful but its content is preserved. (Module 2 Part 5 `Tool Output Comparison`
   and Module 3 Part 2 `Cedar Policies` / `Authorization Flow` keep their descriptive labels;
   only the diagram tab is relabeled and the About tab inserted as the 2nd tab.)

4. **About text is derived per-part from the module README + part_header.** Draft text for all
   18 sections is in the "About text" appendix below. Each is specific to the part (concept +
   why it matters + what to try), 2–5 sentences or a short bullet list.

## Before-count of architecture-diagram sections (coverage baseline)

Target = `st.expander("📐 Architecture Diagram" ...)` (Pattern A) **plus** the Pattern B
expanders whose first tab is the Architecture Diagram. Verified by grep:

| Page | Pattern A (expander→image) | Pattern B (expander→tabs) | Total sections |
|------|----------------------------|---------------------------|----------------|
| 1_Module_1_Multi_Agent.py | Parts 1,2,3,4 = 4 | 0 | 4 |
| 2_Module_2_Context.py | Part 1 = 1 | Parts 2,3,4,5 = 4 | 5 |
| 3_Module_3_Security.py | Parts 1,3 = 2 | Part 2 = 1 | 3 |
| 4_Module_4_Observability.py | Parts 1,2,3 = 3 | 0 | 3 |
| 5_Module_5_Well_Architected.py | 0 | Parts 1,2,3 = 3 | 3 |
| **TOTAL** | **10** | **8** | **18** |

NOT in scope (confirmed during exploration, do not touch):
- Module 1 Part 5 "Graph & Swarm" and "Auto-run Walkthrough" — no `diagram_path`, no Architecture Diagram section.
- Module 3 Part 1 OWASP expander (`st.expander(":material/security: OWASP ...")`) — not a diagram.
- Module 4 Part 3 "📐 Built-in Evaluators (deployed)" expander (line ~295) — not a diagram section.
- Module 4 Part 4 "Golden Dataset" — no diagram section.

After the change, every one of the 18 sections must contain an `st.tabs([` call with an
`ℹ️ About` tab. Coverage target: **18 `ℹ️ About` tabs added total**.

---

## Ordered implementation items

Each page is independent; order is by page number. Each item leaves the file importable
(`py_compile` clean). Do all sections within a page in one item (same mechanical change),
then verify that page before moving on.

- [ ] 1. **Module 1 — convert all 4 Pattern A diagram sections to tabs.**
      For each of Parts 1, 2, 3, 4, replace the pattern
      `if os.path.exists(diagram_path): / with st.expander("📐 Architecture Diagram", expanded=False): / st.image(diagram_path)`
      with: keep the `diagram_path = os.path.join(...)` line unchanged, then an unconditional
      `with st.expander("📐 Architecture Diagram", expanded=False):` containing
      `tab_diagram, tab_about = st.tabs(["📐 Diagram", "ℹ️ About"])`; inside `tab_diagram` put
      `if os.path.exists(diagram_path): st.image(diagram_path)` / `else: st.info("Diagram not available.")`;
      inside `tab_about` put the per-part About markdown (appendix M1-P1..M1-P4).
      Files: app/pages/1_Module_1_Multi_Agent.py
      Verify: `python3 -m py_compile app/pages/1_Module_1_Multi_Agent.py` exits 0, and
      `grep -c 'ℹ️ About' app/pages/1_Module_1_Multi_Agent.py` returns `4`.

- [ ] 2. **Module 2 — Part 1 (Pattern A) + Parts 2,3,4,5 (Pattern B).**
      Part 1: same Pattern A conversion as item 1 (appendix M2-P1).
      Parts 2,3,4: these already have `with st.expander("📐 Architecture & Code", ...):` and
      `tab_diagram, tab_code = st.tabs(["Architecture Diagram", "Code"])`. Change that line to
      `tab_diagram, tab_about, tab_code = st.tabs(["📐 Diagram", "ℹ️ About", "📝 Code"])`, add a
      `with tab_about:` block (About markdown M2-P2/M2-P3/M2-P4) between the existing
      `with tab_diagram:` and `with tab_code:` blocks, leaving diagram and code bodies unchanged.
      Part 5: expander `"📐 Architecture & Tool Comparison"`, currently
      `tab_diagram, tab_comparison = st.tabs(["Architecture Diagram", "Tool Output Comparison"])`.
      Change to `tab_diagram, tab_about, tab_comparison = st.tabs(["📐 Diagram", "ℹ️ About", "Tool Output Comparison"])`
      and insert `with tab_about:` (M2-P5) before `with tab_comparison:`; keep both existing bodies.
      Files: app/pages/2_Module_2_Context.py
      Verify: `python3 -m py_compile app/pages/2_Module_2_Context.py` exits 0, and
      `grep -c 'ℹ️ About' app/pages/2_Module_2_Context.py` returns `5`.

- [ ] 3. **Module 3 — Parts 1,3 (Pattern A) + Part 2 (Pattern B, 3→4 tabs).**
      Parts 1 and 3: Pattern A conversion as item 1 (appendix M3-P1, M3-P3).
      Part 2: expander `"📐 Architecture & Cedar Policies"`, currently
      `tab_diagram, tab_policies, tab_flow = st.tabs(["Architecture Diagram", "Cedar Policies", "Authorization Flow"])`.
      Change to `tab_diagram, tab_about, tab_policies, tab_flow = st.tabs(["📐 Diagram", "ℹ️ About", "Cedar Policies", "Authorization Flow"])`
      and insert `with tab_about:` (M3-P2) after the `with tab_diagram:` block; keep policies and
      flow bodies unchanged.
      Files: app/pages/3_Module_3_Security.py
      Verify: `python3 -m py_compile app/pages/3_Module_3_Security.py` exits 0, and
      `grep -c 'ℹ️ About' app/pages/3_Module_3_Security.py` returns `3`.

- [ ] 4. **Module 4 — convert all 3 Pattern A diagram sections to tabs.**
      Parts 1, 2, 3: Pattern A conversion as item 1 (appendix M4-P1, M4-P2, M4-P3). Do NOT modify
      the separate `st.expander("📐 Built-in Evaluators (deployed)")` block in Part 3 (line ~295).
      Files: app/pages/4_Module_4_Observability.py
      Verify: `python3 -m py_compile app/pages/4_Module_4_Observability.py` exits 0, and
      `grep -c 'ℹ️ About' app/pages/4_Module_4_Observability.py` returns `3`.

- [ ] 5. **Module 5 — Parts 1,2,3 (Pattern B, 2→3 tabs).**
      Each part has expander `"📐 Architecture & Code"` and
      `tab_diagram, tab_code = st.tabs(["Architecture Diagram", "Code"])`. Change each to
      `tab_diagram, tab_about, tab_code = st.tabs(["📐 Diagram", "ℹ️ About", "📝 Code"])` and insert
      a `with tab_about:` block (appendix M5-P1, M5-P2, M5-P3) between the diagram and code blocks;
      keep diagram and code bodies unchanged.
      Files: app/pages/5_Module_5_Well_Architected.py
      Verify: `python3 -m py_compile app/pages/5_Module_5_Well_Architected.py` exits 0, and
      `grep -c 'ℹ️ About' app/pages/5_Module_5_Well_Architected.py` returns `3`.

- [ ] 6. **Whole-app coverage + syntax verification.**
      Confirm every page still compiles and the total About-tab count equals the before-count (18).
      Files: (none — verification only)
      Verify:
      `python3 -m py_compile app/pages/*.py` exits 0; and
      `grep -rc 'ℹ️ About' app/pages/*.py` sums to 18 (4+5+3+3+3); and
      `grep -c 'st.image(diagram_path)' app/pages/*.py` per file is unchanged from before
      (each diagram still rendered once per section — M1:4, M2:5, M3:3, M4:3, M5:3). Also confirm
      no absolute paths were introduced: `grep -n '/home/ubuntu\|/Users/' app/pages/*.py` returns
      nothing in the edited diagram blocks.

---

## About text (draft, per section) — use verbatim or lightly adjusted

Content below is derived from each part's `part_header` and the module README. Keep each short
and specific.

### Module 1 — Multi-Agent (README: TechMart scenario)
- **M1-P1 (Single agent — cognitive load):** One agent handles billing, tech support, and
  product questions at once. As the conversation spans domains it mixes up procedures and
  can't go deep on any topic — context fills with cross-domain history and quality drops. Try
  the 5-query sequence (billing → Wi-Fi → laptop → refund → compatibility) and watch it degrade.
- **M1-P2 (Orchestrator pattern):** A central orchestrator routes each query to the right
  specialist (📋 billing, 🔧 tech, 🛍️ product). Specialists give deeper, more accurate answers
  and don't get polluted by unrelated context; a compound query gets decomposed across
  specialists. Run the same prompts as Part 1 to compare.
- **M1-P3 (Agent-as-tool / MCP):** A Sales agent and a Support agent reuse the *same* underlying
  tools (`product_lookup`, `compatibility_check`, `order_status`) through clear input/output
  contracts. The implementation can change without touching the consumer agents — this is how
  AgentCore Gateway exposes shared tools. Try the Sales vs Support prompt sets.
- **M1-P4 (Shared memory):** Three agents (Diagnose → Resolve → Follow-up) collaborate by
  reading and writing a shared memory instead of passing full transcripts. Watch 💾 (write) and
  📖 (read): the Resolution agent never saw the original message, and the final state shows an
  audit trail with distinct `actor_id`s — mirroring AgentCore Memory.

### Module 2 — Context Engineering
- **M2-P1 (Context growth):** Context is a finite resource. As a long conversation accumulates,
  token counts rise, latency grows, and later answers lose details from early turns. Build up
  the multi-turn retreat-planning prompts and watch the token counter climb.
- **M2-P2 (Prompt caching):** A cache point marker lets Bedrock store a large static system-prompt
  prefix once (cache WRITE) and reuse it on later calls (cache READ) at a discounted rate,
  cutting latency and cost. Check `cacheReadInputTokens` / `cacheWriteInputTokens` in the usage
  metrics to confirm a cache hit.
- **M2-P3 (Conversation managers):** `SummarizingConversationManager` compresses older turns into
  a summary so the agent keeps earlier decisions without carrying the full transcript. Run the
  long architecture-design thread, then ask it to recall an early decision to confirm the summary
  retained it.
- **M2-P4 (Context isolation):** Specialized sub-agents (research, analysis, writing) each receive
  only the context relevant to their step, not the whole history — keeping every agent's context
  lean. Run the renewable-energy research → analysis → summary flow and note how little each
  sub-agent sees.
- **M2-P5 (Tool design for efficiency):** Tool output format directly drives token cost. Compare
  verbose JSON vs an optimized/TOON response for the same data and watch the estimated token
  count change. Switch the active tool mode and re-run a lookup to see the difference.

### Module 3 — Security
- **M3-P1 (Unprotected agent):** A baseline agent with no identity checks, authorization, or audit
  trail — it will process refunds, read other customers' data, and change records on request. Try
  the exploit prompts to see why controls are needed; later parts add them.
- **M3-P2 (Cedar policy authorization):** The same agent is now fronted by the AgentCore Policy
  Engine (Amazon Verified Permissions). Cedar policies permit/deny each tool call from principal
  tags (department, role) and request context (e.g. refund amount). Log in as different users and
  try refunds above and below their limit to watch ALLOW vs DENY.
- **M3-P3 (Cognito + JWT + Cedar):** Real OAuth 2.0: a Cognito JWT's claims become the principal
  tags that drive the same Cedar policies — authorization is now tied to real identity. Log in,
  inspect the JWT claims, and switch users to see decisions change with identity.

### Module 4 — Observability
- **M4-P1 (Real-time metrics / tracing):** Every interaction emits latency, token, and tool metrics
  and records a Session → Trace → Span hierarchy to CloudWatch. Run a few queries and open the
  span view to see per-operation timing feeding the dashboard.
- **M4-P2 (Loop detection):** A circuit breaker trips when the agent makes too many repeated tool
  calls, stopping runaway loops and firing a CloudWatch alarm — critical safety for autonomous
  agents. Trigger the "loopy" mode to watch tool calls escalate and the breaker activate.
- **M4-P3 (LLM-as-judge evaluation):** An automated judge scores responses on correctness,
  helpfulness, and tool selection (0.0–1.0), publishing scores to CloudWatch for continuous
  quality tracking and regression alerts. Run the automated test suite to see per-evaluator scores
  and the pass/fail quality threshold.

### Module 5 — Well-Architected
- **M5-P1 (Multi-agent e-commerce):** The capstone system — an orchestrator routing to four
  specialists (billing, tech, product, shipping) with cross-cutting concerns (circuit breakers,
  health checks, token budgets) wired in. Run the sample queries to see the full system end to end.
- **M5-P2 (Reliability — fault tolerance):** Per-specialist circuit breakers isolate failures and
  fallback agents keep the system answering when one specialist breaks. Use `break product`, ask a
  product question to see the fallback respond, then `fix product` to recover — `status` shows each
  breaker's state.
- **M5-P3 (Cost optimization):** Smart model tiering routes simple queries to an economy model and
  complex ones to a premium model, under a token budget, to prevent cost surprises. Send a simple
  then a complex query and check `cost` / `budget` to see the tier split and savings.

---

## Notes / assumptions

- Emoji in labels are the same ones already used in the codebase (`📐`, `📝`); `ℹ️` is new but
  standard Streamlit-safe.
- No automated UI test suite exists (checked `app/requirements.txt`); `py_compile` + structural
  grep is the realistic verification. Streamlit 1.60.0 is installed locally, so a manual
  `streamlit run` smoke test is possible but not required by this plan.
- The single behavioral change (Pattern A expander becoming unconditional so the About tab is
  always visible) is intentional and matches the task's requirement for a "Diagram not available."
  fallback inside the Diagram tab. If a reviewer prefers to keep the expander hidden when the
  diagram is missing, that is the only point open to revision — flagged here rather than silently
  chosen the other way.

---

## Verification results (iteration 1 — implemented)

Commands run from `app/` after editing all 5 pages:

1. **Byte-compile** — `python3 -m py_compile pages/*.py` → exit 0 (`COMPILE_OK`). All 5 pages compile.

2. **Structural grep** (per-page counts):

   | Page | `ℹ️ About` | `st.tabs(` | `📐 Diagram` label | `st.image(diagram_path)` |
   |------|-----------|-----------|--------------------|--------------------------|
   | 1_Module_1_Multi_Agent.py | 4 | 4 | 4 | 4 |
   | 2_Module_2_Context.py | 5 | 5 | 5 | 5 |
   | 3_Module_3_Security.py | 3 | 3 | 3 | 3 |
   | 4_Module_4_Observability.py | 3 | 3 | 3 | 3 |
   | 5_Module_5_Well_Architected.py | 3 | 3 | 3 | 3 |
   | **TOTAL** | **18** | **18** | **18** | **18** |

   - `grep -rn '"Architecture Diagram"' pages/*.py` → no matches (all old tab labels renamed to `📐 Diagram`).
   - `grep -rn '/Users/erictole\|/home/ubuntu' pages/*.py` → no matches (no absolute paths introduced).

3. **Coverage** — 18 About tabs added = the 18-section before-count (M1:4, M2:5, M3:3, M4:3, M5:3).
   Every former `st.expander("📐 Architecture Diagram"...)` (Pattern A) and every Pattern B
   Architecture-Diagram expander now contains an `st.tabs(` call with an `ℹ️ About` tab, and each
   diagram is still rendered exactly once per section (`st.image(diagram_path)` counts unchanged).
   All 18 sections have a diagram_path; no part in scope lacked a diagram. Out-of-scope expanders
   (Module 3 Part 1 OWASP, Module 4 Part 3 "Built-in Evaluators") were left untouched.

Scope: only the 5 files under `app/pages/` were modified by this task. (Pre-existing uncommitted
changes under `demos/` were present in the working tree before this task and were not touched.)
Not committed per instructions.
