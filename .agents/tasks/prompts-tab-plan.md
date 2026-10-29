# Implementation Plan — Add "💡 Prompts" tab to every diagram expander

## Goal (second user request only)

Inside each diagram expander's `st.tabs(...)`, add a NEW tab labeled `💡 Prompts` that lists
that part's sample prompts as read-only reference text. The first request (📐 Diagram + ℹ️ About
tabs inside an `st.expander`) is already merged — these files already have that structure, verified
by reading the current source.

## Scope and ground rules (verified against the current code)

- Edit ONLY these 5 files:
  - `app/pages/1_Module_1_Multi_Agent.py`
  - `app/pages/2_Module_2_Context.py`
  - `app/pages/3_Module_3_Security.py`
  - `app/pages/4_Module_4_Observability.py`
  - `app/pages/5_Module_5_Well_Architected.py`
- Do NOT touch `app/agent_utils.py`, `app/agentcore_utils.py`, `app/Home.py`, `app/style.py`, or anything under `demos/`.
- There are exactly **18 diagram sections** (each is a `with st.expander("📐 ...")` containing a
  `... = st.tabs([...])`). After this change there must be exactly **18 `💡 Prompts` tabs**:
  - M1: 4 (Parts 1–4). Part 5 Graph/Swarm has NO `📐` expander (it uses per-pattern `📝 Code` expanders) → leave it alone.
  - M2: 5 (Parts 1–5). Part 6 Failure Modes has no diagram expander → leave it alone.
  - M3: 3 (Parts 1–3).
  - M4: 3 (Parts 1–3). Part 4 Golden Dataset has no diagram expander; the `📐 Built-in Evaluators`
    expander on ~line 325 is a plain markdown table with NO `st.tabs` → leave both alone.
  - M5: 3 (Parts 1–3).

### Standard tab pattern to apply in every section

1. Add `"💡 Prompts"` to the `st.tabs([...])` label list, positioned **after `ℹ️ About`** and
   **before** any `📝 Code` / `Tool Output Comparison` / `Cedar Policies` / `Authorization Flow` tab.
   Capture it into a new variable `tab_prompts`.
   - 2-tab sections become: `tab_diagram, tab_about, tab_prompts = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts"])`
   - 3-tab sections (e.g. `+ 📝 Code`): `tab_diagram, tab_about, tab_prompts, tab_code = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts", "📝 Code"])`
   - M3 Part 2 (4 tabs) becomes: `tab_diagram, tab_about, tab_prompts, tab_policies, tab_flow = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts", "Cedar Policies", "Authorization Flow"])`
2. Add a `with tab_prompts:` block (as the body immediately after `with tab_about:` closes) that renders
   each prompt as a readable, read-only line. Use this exact body shape:
   ```python
   with tab_prompts:
       st.caption("Sample prompts — click the matching pill in the chat below to run them.")
       for _p in suggestions:
           st.markdown("- " + _p)
   ```
   For non-chat/workflow parts (M1 P4, M2 P4, M4 P3), the intro caption text is adjusted (see per-part
   notes) and the list variable is the one defined for that part.
3. **Single source of truth (Rule 3):** where a part already defines `suggestions = [...]` inside the
   `if not st.session_state.<...>_msgs:` block, HOIST that exact list to a module-part-local variable
   defined **right before the diagram `st.expander`** so both the Prompts tab and the later inline
   `st.pills(..., suggestions, ...)` use ONE variable. Do NOT duplicate the literal list. The inline
   `st.pills` call and its click handler stay exactly as-is (Rule 5) — only the list *definition* moves earlier.
4. Keep `diagram_path` construction in the existing `os.path.join(...)` relative form. Do not introduce
   absolute `/Users/...` or `/home/ubuntu` paths (Rule 6).

### Design decision: how to handle each part's `suggestions` scope

Reasoning: Most parts define `suggestions` inside `if not ..._msgs:`, which runs only when chat history
is empty. The Prompts tab lives in the diagram expander that renders on every run, so it needs the list
unconditionally. Hoisting the single list to just before the expander satisfies both the tab and the
existing inline pills without duplication, and keeps behavior identical. For parts where the inline list
is conditional on a sub-selector (M1 P3 Sales/Support), define the hoisted variable using the same
selector value that is already computed before the expander, OR list the union — see M1 P3 note.

---

## Module 1 — `app/pages/1_Module_1_Multi_Agent.py` (4 Prompts tabs)

- [ ] 1. **M1 Part 1 — Single Agent.** Hoist the inline list
      `suggestions = ["Charged $9.99, cancelled last week", "Hub disconnecting, firmware v2.1.3", "Laptop under $800 for editing"]`
      (currently inside `if not st.session_state.m1p1_msgs:`) to just before `with st.expander("📐 Architecture Diagram", ...)` (~line 52). Add `tab_prompts` to the tabs list and a `with tab_prompts:` block that lists `suggestions`. In the inline block, keep `st.pills("Try:", suggestions, key="m1p1_pills")` but remove the now-local re-assignment of `suggestions` there (reference the hoisted var). **Also remove the standalone `st.expander("💡 Suggested Prompts", ...)` block** (the three `st.caption` lines ~115–118) per Rule 5 — its content is represented by the Prompts tab. Note: those three captions ("I was charged $9.99 but cancelled. Order TM-78432." / "My TechMart Hub keeps disconnecting. Firmware v2.1.3." / "I need a laptop under $800 for video editing.") match the inline pills in meaning, so no information is lost; the hoisted `suggestions` list is the single source.
      Files: `app/pages/1_Module_1_Multi_Agent.py`
      Verify: `python3 -m py_compile app/pages/1_Module_1_Multi_Agent.py` succeeds; grep confirms the standalone `💡 Suggested Prompts` expander is gone and a `💡 Prompts` tab label exists.

- [ ] 2. **M1 Part 2 — Orchestrator.** Hoist `suggestions = ["Refund on order TM-78432", "Hub Wi-Fi keeps dropping", "Recommend a laptop"]` to just before the Part 2 `st.expander("📐 Architecture Diagram", ...)` (~line 187). Add `tab_prompts` and the `with tab_prompts:` list block. Inline `st.pills(..., "m1p2_pills")` references the hoisted var.
      Files: `app/pages/1_Module_1_Multi_Agent.py`
      Verify: part of Step 6 full-file compile + tab count.

- [ ] 3. **M1 Part 3 — Agent-as-Tool.** IMPORTANT ORDERING FACT (verified): in this part the diagram
      `st.expander("📐 Architecture Diagram", ...)` (~line 353) comes BEFORE the `st.selectbox("Consumer Agent:", ...)`
      and the `new_type` computation (~lines 374–378). So `new_type` is NOT available where the Prompts tab
      renders, and the inline pills list is genuinely selector-dependent. Do NOT move the selectbox above the
      expander (that would reorder the visible UI, putting the selector above the diagram). Instead:
      - Add `tab_prompts` to the tabs list as usual.
      - In `with tab_prompts:`, show BOTH consumer agents' prompt sets as two labeled read-only groups:
        ```python
        with tab_prompts:
            st.caption("Sample prompts by consumer agent — click the matching pill in the chat below to run them.")
            st.markdown("**Sales Agent**")
            for _p in ["Look up TechMart Hub", "Hub + Camera compatible?"]:
                st.markdown("- " + _p)
            st.markdown("**Support Agent**")
            for _p in ["Order TM-78432 status", "Hub + sensors compatible?"]:
                st.markdown("- " + _p)
        ```
      - Leave the inline conditional `suggestions`/`st.pills(..., "m1p3_pills")` block exactly as-is (it is
        legitimately conditional on `new_type`; this is the documented exception to the hoist rule because the
        selector sits after the expander). This keeps the pills single-source within their own branch and does
        not break UI ordering.
      Files: `app/pages/1_Module_1_Multi_Agent.py`
      Verify: part of Step 6.

- [ ] 4. **M1 Part 4 — Shared memory (NO existing suggestions, workflow part).** This part uses a `st.text_area` + "Start Workflow" button, not pills. Per Rules 2/4, ADD a read-only example-inputs list as a NEW variable defined before `with st.expander("📐 Architecture Diagram", ...)` (~line 442):
      ```python
      suggestions = [
          "My TechMart Hub firmware v2.1.3 keeps dropping Wi-Fi every few minutes. I also added 2 motion sensors yesterday and they aren't appearing in the app.",
          "My smart cameras keep going offline at night. I have 3 cameras connected through my TechMart Hub.",
      ]
      ```
      (Derived from the README "Suggested Issues" for Part 4 and the text_area placeholder "My TechMart Hub firmware v2.1.3 keeps dropping Wi-Fi...".) The `with tab_prompts:` caption should read "Example issue descriptions — paste one into the box below." then list `suggestions`. Do NOT wire these into the text_area or add pills (Rule 4: never break the existing workflow; the text_area has no safe pre-fill hook here). Read-only list only.
      Files: `app/pages/1_Module_1_Multi_Agent.py`
      Verify: part of Step 6.

- [ ] 5. (reserved — no Part 5 / walkthrough change; Part 5 Graph/Swarm and Auto-run have no `📐` diagram expander and are intentionally untouched.)

- [ ] 6. **Verify Module 1.** Run `python3 -m py_compile app/pages/1_Module_1_Multi_Agent.py` (expect no output / exit 0) and confirm exactly 4 occurrences of the `💡 Prompts` tab label and that no `💡 Suggested Prompts` standalone expander remains.
      Files: none (verification only)
      Verify: `python3 -m py_compile app/pages/1_Module_1_Multi_Agent.py` exits 0; `grep -c '"💡 Prompts"' app/pages/1_Module_1_Multi_Agent.py` returns 4; `grep -c '💡 Suggested Prompts' app/pages/1_Module_1_Multi_Agent.py` returns 0.

---

## Module 2 — `app/pages/2_Module_2_Context.py` (5 Prompts tabs)

- [ ] 7. **M2 Part 1 — Context Growth.** Hoist `suggestions = ["Plan retreat for 50 in Bali", "Budget is $150K, break it down", "12 vegetarians, 3 mobility issues"]` to before `st.expander("📐 Architecture Diagram", ...)` (~line 51). Add `tab_prompts` (2→3 tabs) + list block; inline `st.pills(..., "m2p1_pills")` references the hoisted var.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: part of Step 12.

- [ ] 8. **M2 Part 2 — Prompt caching.** This section's expander is `st.expander("📐 Architecture & Code", ...)` with `tab_diagram, tab_about, tab_code`. Insert `tab_prompts` BEFORE `tab_code`: `tab_diagram, tab_about, tab_prompts, tab_code = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts", "📝 Code"])`. Hoist `suggestions = ["Revenue breakdown by segment", "Top 3 risks next year", "Growth vs competitors"]` to before this expander (~line 150); add the `with tab_prompts:` block between `with tab_about:` and `with tab_code:`. Inline `st.pills(..., "m2p2_pills")` references the hoisted var.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: part of Step 12.

- [ ] 9. **M2 Part 3 — Conv. Managers.** Same `📐 Architecture & Code` 3-tab shape. Insert `tab_prompts` before `tab_code`. Hoist `suggestions = ["Recommend a database for catalog", "Design the order service"]` to before the expander (~line 293). Add list block; inline `st.pills(..., "m2p3_pills")` references hoisted var.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: part of Step 12.

- [ ] 10. **M2 Part 4 — Isolation (NO existing suggestions, pipeline part).** Uses a `st.text_input` (default value "Evaluate viability of a 50MW solar farm in Vietnam for 2025-2027.") + "Run Pipeline" button. Same `📐 Architecture & Code` 3-tab shape; insert `tab_prompts` before `tab_code`. ADD a new list before the expander (~line 386), derived from the README "Suggested Task" and the input default:
      ```python
      suggestions = [
          "Evaluate viability of a 50MW solar farm in Vietnam for 2025-2027.",
          "Assess the market for electric delivery vans in Southeast Asia.",
          "Evaluate launching a cloud data-analytics product for SMBs.",
      ]
      ```
      `with tab_prompts:` caption: "Example research tasks — type one into the Research task box." then list `suggestions`. Do NOT alter the text_input or add pills.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: part of Step 12.

- [ ] 11. **M2 Part 5 — Tool Design.** Expander is `st.expander("📐 Architecture & Tool Comparison", ...)` with `tab_diagram, tab_about, tab_comparison`. Insert `tab_prompts` BEFORE `tab_comparison`: `tab_diagram, tab_about, tab_prompts, tab_comparison = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts", "Tool Output Comparison"])`. Hoist `suggestions = ["Look up customer CUST-44821", "Summarize their account status", "What should we proactively offer them?"]` to before the expander (~line 485; note the `TOOL_RESPONSES` dict is already defined above the expander — place the hoist after it, right before `with st.expander(...)`). Add the list block; inline `st.pills(..., "m2p5_pills")` references the hoisted var.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: part of Step 12.

- [ ] 12. **Verify Module 2.** Part 6 Failure Modes is intentionally untouched (no diagram expander).
      Files: none (verification only)
      Verify: `python3 -m py_compile app/pages/2_Module_2_Context.py` exits 0; `grep -c '"💡 Prompts"' app/pages/2_Module_2_Context.py` returns 5.

---

## Module 3 — `app/pages/3_Module_3_Security.py` (3 Prompts tabs)

- [ ] 13. **M3 Part 1 — Unprotected.** Diagram expander is `st.expander("📐 Architecture Diagram", ...)` (`tab_diagram, tab_about`), ~line 82. Note there is ALSO a separate `st.expander("💡 Try these", ...)` with an `st.code(...)` of exploit prompts (~line, just above the agent setup) — leave that as-is (it is not a diagram tabs section; the task only requires adding the Prompts tab, not removing M3's Try-these helper). Hoist `suggestions = ["Process $5000 refund ORD-5006", "Show customer CUST-1005"]` to before the diagram expander. Add `tab_prompts` + list block; inline `st.pills(..., "m3p1_pills")` references hoisted var. Optionally extend the Prompts tab list to the three README exploit prompts by keeping the 2 pill prompts as the `suggestions` var (single source for pills) and NOT duplicating — the pills list is the authoritative `suggestions`; the Prompts tab shows those two.
      Files: `app/pages/3_Module_3_Security.py`
      Verify: part of Step 16.

- [ ] 14. **M3 Part 2 — Cedar Policies.** Expander `st.expander("📐 Architecture & Cedar Policies", ...)` with `tab_diagram, tab_about, tab_policies, tab_flow` (~line 233). Insert `tab_prompts` AFTER `tab_about`, BEFORE `tab_policies`: `tab_diagram, tab_about, tab_prompts, tab_policies, tab_flow = st.tabs(["📐 Diagram", "ℹ️ About", "💡 Prompts", "Cedar Policies", "Authorization Flow"])`. The inline pills list `suggestions = ["Process $300 refund on ORD-5001, reason: customer dissatisfied", "Process $700 refund on ORD-5002, reason: defective product"]` is inside `if not ..._msgs:` which is AFTER the `users`/selectbox logic. Hoist this list to before the expander (the expander is near the top of the Part 2 block, before the `users` dict). This is safe because the list is static (not user-dependent). Add the `with tab_prompts:` block between `with tab_about:` and `with tab_policies:`; inline `st.pills(..., "m3p2_pills")` references the hoisted var.
      Files: `app/pages/3_Module_3_Security.py`
      Verify: part of Step 16.

- [ ] 15. **M3 Part 3 — Cognito Auth.** Diagram expander `st.expander("📐 Architecture Diagram", ...)` (`tab_diagram, tab_about`), ~line 542. The inline pills here use f-strings: `suggestions = [f"Process $300 refund on ORD-5001, reason: defective", f"Process $700 refund on ORD-5002, reason: wrong item"]` and are defined deep inside the `else:` (authenticated) branch — NOT before the diagram expander. The diagram expander renders regardless of auth state, so define a hoisted plain (non-f-string, no interpolation needed) list before the expander:
      ```python
      suggestions = ["Process $300 refund on ORD-5001, reason: defective", "Process $700 refund on ORD-5002, reason: wrong item"]
      ```
      Add `tab_prompts` + list block. In the authenticated branch, change the inline `st.pills("Try:", suggestions, key="m3p3_pills")` to reference the hoisted `suggestions` (drop the local f-string redefinition — they contain no interpolation, so behavior is identical). Keep the pill click handler unchanged.
      Files: `app/pages/3_Module_3_Security.py`
      Verify: part of Step 16.

- [ ] 16. **Verify Module 3.**
      Files: none (verification only)
      Verify: `python3 -m py_compile app/pages/3_Module_3_Security.py` exits 0; `grep -c '"💡 Prompts"' app/pages/3_Module_3_Security.py` returns 3.

---

## Module 4 — `app/pages/4_Module_4_Observability.py` (3 Prompts tabs)

- [ ] 17. **M4 Part 1 — Metrics.** Diagram expander `st.expander("📐 Architecture Diagram", ...)` (`tab_diagram, tab_about`), ~line 55. Hoist `suggestions = ["Search for TechMart Hub", "What laptops under $800?", "Is the Titan in stock?"]` to before the expander. Add `tab_prompts` + list block; inline `st.pills(..., "m4p1_pills")` references hoisted var.
      Files: `app/pages/4_Module_4_Observability.py`
      Verify: part of Step 20.

- [ ] 18. **M4 Part 2 — Loop detection.** Diagram expander `st.expander("📐 Architecture Diagram", ...)` (`tab_diagram, tab_about`), ~line 206. Hoist `suggestions = ["Find all customer records and process each one"]` to before the expander. Add `tab_prompts` + list block; inline `st.pills(..., "m4p2_pills")` references hoisted var.
      Files: `app/pages/4_Module_4_Observability.py`
      Verify: part of Step 20.

- [ ] 19. **M4 Part 3 — Evaluation (NO inline pills; uses text_input + Evaluate button).** Diagram expander `st.expander("📐 Architecture Diagram", ...)` (`tab_diagram, tab_about`), ~line 308. This part has a `st.text_input("Query to evaluate:", value="My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.", ...)` and a "🧪 Evaluate" button — no pills. Per Rules 2/4, ADD a new read-only list before the diagram expander, derived from the README "Suggested Queries to Evaluate" for Module 4 Part 3:
      ```python
      suggestions = [
          "My TechMart Hub keeps dropping Wi-Fi. Firmware v2.1.3.",
          "What's the best laptop for video editing under $800?",
          "Can I return an item after 45 days?",
      ]
      ```
      `with tab_prompts:` caption: "Example queries to evaluate — type one into the box above." then list `suggestions`. Do NOT alter the text_input or add pills. Note the `📐 Built-in Evaluators` expander (~line 325) and Part 4 Golden Dataset are intentionally untouched (no `st.tabs`).
      Files: `app/pages/4_Module_4_Observability.py`
      Verify: part of Step 20.

- [ ] 20. **Verify Module 4.**
      Files: none (verification only)
      Verify: `python3 -m py_compile app/pages/4_Module_4_Observability.py` exits 0; `grep -c '"💡 Prompts"' app/pages/4_Module_4_Observability.py` returns 3.

---

## Module 5 — `app/pages/5_Module_5_Well_Architected.py` (3 Prompts tabs)

- [ ] 21. **M5 Part 1 — E-Commerce.** Expander `st.expander("📐 Architecture & Code", ...)` with `tab_diagram, tab_about, tab_code` (~line 89). Insert `tab_prompts` before `tab_code`. Hoist `suggestions = ["Laptops under $800?", "Hub dropping Wi-Fi v2.1.3", "Express shipping cost?"]` to before the expander. Add the `with tab_prompts:` block between `with tab_about:` and `with tab_code:`; inline `st.pills(..., "m5p1_pills")` references hoisted var.
      Files: `app/pages/5_Module_5_Well_Architected.py`
      Verify: part of Step 24.

- [ ] 22. **M5 Part 2 — Reliability.** Same `📐 Architecture & Code` 3-tab shape (~line 226). Insert `tab_prompts` before `tab_code`. Hoist `suggestions = ["What laptops available?", "Refund on last order?", "Hub disconnecting from Wi-Fi"]` to before the expander. Add list block; inline `st.pills(..., "m5p2_pills")` references hoisted var.
      Files: `app/pages/5_Module_5_Well_Architected.py`
      Verify: part of Step 24.

- [ ] 23. **M5 Part 3 — Cost optimization.** Same `📐 Architecture & Code` 3-tab shape (~line 347). Insert `tab_prompts` before `tab_code`. Hoist `suggestions = ["Hi", "What's the Hub price?", "Compare Pro 15 and Titan for video editing"]` to before the expander. Add list block; inline `st.pills(..., "m5p3_pills")` references hoisted var. NOTE: the pill click path calls `_do_cost_query(selected, tiering)` — leave that handler untouched; only the list definition moves.
      Files: `app/pages/5_Module_5_Well_Architected.py`
      Verify: part of Step 24.

- [ ] 24. **Verify Module 5.**
      Files: none (verification only)
      Verify: `python3 -m py_compile app/pages/5_Module_5_Well_Architected.py` exits 0; `grep -c '"💡 Prompts"' app/pages/5_Module_5_Well_Architected.py` returns 3.

---

## Final integration verification

- [ ] 25. **Compile all 5 files and confirm the global tab count.**
      Files: none (verification only)
      Verify:
      - `python3 -m py_compile app/pages/1_Module_1_Multi_Agent.py app/pages/2_Module_2_Context.py app/pages/3_Module_3_Security.py app/pages/4_Module_4_Observability.py app/pages/5_Module_5_Well_Architected.py` exits 0 (no syntax errors).
      - `grep -rc '"💡 Prompts"' app/pages/*.py` totals **18** (M1=4, M2=5, M3=3, M4=3, M5=3).
      - `grep -rn '/Users/erictole\|/home/ubuntu' app/pages/*.py` returns NOTHING (no absolute paths reintroduced).
      - `grep -c '💡 Suggested Prompts' app/pages/1_Module_1_Multi_Agent.py` returns 0 (standalone expander removed).
      - Smoke-check that Streamlit can import a page if the environment allows:
        `cd app && python3 -c "import streamlit" 2>/dev/null && echo "streamlit present"` — if Streamlit is
        not installed, `py_compile` is the authoritative build check for this plan (the pages require a
        running Streamlit + AWS context to execute fully, which is out of scope for static verification).

## Notes, assumptions, and gaps

- `py_compile` is used as the build/verification command because the repo has no test suite for the app
  pages and these Streamlit pages cannot execute without a running Streamlit server and AWS credentials.
  A successful `py_compile` plus the grep-based structural counts is the strongest static guarantee
  available here. (The grep counts verify structure, not behavior; the compile verifies the edits are
  valid Python — together they confirm the change is buildable and shaped correctly.)
- Prompt sources: every proposed prompt is drawn from the current inline `suggestions`/`st.pills` lists,
  the part input placeholder/default strings, and the app `README.md` "Suggested Prompts" sections, which
  mirror `demos/module{1..5}-*/README.md`. No invented product facts.
- Rule 5 compliance: the only removal is Module 1 Part 1's standalone `💡 Suggested Prompts` expander.
  All existing inline `st.pills("Try:", ...)` call sites and their click handlers are preserved; only the
  `suggestions` list *definition* is relocated earlier so the Prompts tab and the pills share one variable.
- Non-chat/workflow parts that previously had NO prompts (M1 P4, M2 P4, M4 P3) get a NEW read-only
  `suggestions` list shown only in the Prompts tab; per Rule 4 they are NOT wired into text inputs/pills,
  to avoid breaking those input mechanisms.
- M1 Part 3's hoisted `suggestions` depends on the Sales/Support selectbox value, which the current code
  already computes (`new_type`) above the diagram expander — the implementer must confirm ordering holds
  after editing and keep the selectbox above the expander.
