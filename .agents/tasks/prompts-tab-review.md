# "💡 Prompts" tab added to every diagram expander across all 5 module pages

Each module page renders its parts inside a `📐 Architecture Diagram` (or `📐 Architecture & Code` / `& Cedar Policies` / `& Tool Comparison`) expander whose body is an `st.tabs(...)`. This change inserts a new `💡 Prompts` tab — positioned after `ℹ️ About` and before any `📝 Code` / comparison / policy / flow tab — into all 18 diagram sections (M1:4, M2:5, M3:3, M4:3, M5:3). The tab lists that part's sample prompts as read-only markdown. Parts that already had a `suggestions = [...]` list feeding inline `st.pills("Try:", ...)` now define that list once, hoisted to just before the expander, so the tab and the pills share one variable. Parts with no prior prompts (M1 P4, M2 P4, M4 P3) get a new read-only `suggestions` list shown only in the tab. The standalone `st.expander("💡 Suggested Prompts", ...)` in M1 Part 1 is removed and folded into the tab.

Watch for: a deliberate single-source exception in M1 Part 3 where the tab hardcodes the Sales/Support prompt literals instead of sharing a variable (confirmed — justified by UI ordering); and unrelated `demos/` working-tree changes present in the tree but outside this task's edits (confirmed — not introduced by this change).

**Verdict**: APPROVED

## High-level view

The change is purely additive and structural. Eighteen `st.tabs(...)` calls each gain one label and one `with tab_prompts:` body; nothing in the chat loop, judge, metrics, session-state keys, or `chat_input` is altered. Verification evidence (py_compile clean on all five files, grep counts of exactly 18 Prompts tabs split 4/5/3/3/3, zero absolute paths, zero remaining standalone expander) is present in the plan file and reproduced here by spot-check.

The single-source-of-truth rule is honored everywhere a part feeds inline pills, with one documented exception. Where pills existed, the `suggestions` literal moved up to just before the expander so both the tab and the later `st.pills(..., key="...")` reference the same name; the pill click handlers and keys are untouched. M1 Part 3 is the exception: its pill list is conditional on a Sales/Support selectbox that renders *after* the diagram expander, so the tab lists both prompt sets as hardcoded literals rather than sharing a variable. This reintroduces a small literal duplication but avoids reordering the visible UI, and the hardcoded values match the inline branches exactly.

New prompts for the three prompt-less parts (M1 P4 shared memory, M2 P4 isolation, M4 P3 evaluation) are read-only and were not wired into their text inputs or buttons, preserving those workflow mechanisms. M3 Part 3's former f-string list (which contained no interpolation) became a plain hoisted list with identical values.

The `demos/` directory has many modified files in the working tree (model-ID swaps, regenerated infra `config.env`, test tweaks). These are a separate, pre-existing workstream — the behavioral change here lives entirely in `app/pages/*.py`, matching the task's scope constraint.

<details>
<summary>Issues (2)</summary>

1. **M1 P3 literal duplication** — the Prompts tab hardcodes the Sales/Support prompt lists instead of sharing the inline `suggestions` variable, a documented exception because the selectbox renders after the expander. Non-blocking; if the two lists drift later they must be kept in sync by hand.
2. **Unrelated demos/ changes in tree** — many `demos/*` files are modified in the working tree but are outside this task's edits and this change did not touch them. Non-blocking for this review; keep them out of any commit scoped to the Prompts tab work.

</details>

<details>
<summary>Details</summary>

### Tab insertion and positioning

Every diagram section's `st.tabs([...])` label list gains `"💡 Prompts"` immediately after `"ℹ️ About"` and before any trailing tab, with the handle captured into a new `tab_prompts`. Two-tab sections become three (`tab_diagram, tab_about, tab_prompts`); the `📝 Code` sections in M2 P2/P3/P4 and M5 P1/P2/P3 become four with `tab_prompts` slotted before `tab_code`; M2 P5 slots it before `Tool Output Comparison`; M3 P2 becomes five with it before `Cedar Policies`. The `with tab_prompts:` body is placed right after `with tab_about:` closes, so render order follows tab order. Grep confirms 18 total Prompts tabs split 4/5/3/3/3, and `python3 -m py_compile` is clean on all five files.

### Single source of truth for pills, and the M1 P3 exception

Where a part already fed inline pills, the `suggestions = [...]` literal that previously lived inside `if not st.session_state.<...>_msgs:` is hoisted to just before the `st.expander(...)`, and the inline block now reads that name rather than redefining it. The `st.pills("Try:", suggestions, key="...")` calls and their click-to-submit handlers are unchanged — grep shows all pill keys intact (m1p1/m1p2, m2p1/m2p2/m2p3/m2p5, m3p1/m3p2/m3p3, m4p1/m4p2, m5p1/m5p2/m5p3) and every `st.pills` call still present.

M1 Part 3 is the one place that does not share a variable. Its inline pill list depends on the `new_type` Sales/Support selectbox, which the code computes *after* the diagram expander renders:

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

The inline branch still carries the authoritative lists:

```python
if new_type == "Sales":
    suggestions = ["Look up TechMart Hub", "Hub + Camera compatible?"]
else:
    suggestions = ["Order TM-78432 status", "Hub + sensors compatible?"]
selected = st.pills("Try:", suggestions, key="m1p3_pills")
```

The tab's four hardcoded strings are byte-for-byte identical to the two inline branches, so today they agree. The cost is a maintenance coupling: a future edit to one set will not propagate to the other. Hoisting the selectbox above the expander would have fixed this but would move the selector above the diagram in the visible UI, so the duplication is the lesser evil. Confirmed by reading lines 419–423 and 453-adjacent; non-blocking.

### New prompts for prompt-less parts

M1 P4 (shared memory), M2 P4 (isolation), and M4 P3 (evaluation) had no prior `suggestions`. Each gets a new read-only list with a part-specific caption that points at the right input ("paste one into the box below", "type one into the Research task box", "type one into the box above"). None of these are wired into the part's `st.text_area` / `st.text_input` / button — consistent with not disturbing the existing workflow entry points. The added prompts are on-topic for each part (TechMart Hub firmware/sensor issues for shared memory; solar-farm / market-assessment research tasks for isolation; Wi-Fi / laptop / returns queries for evaluation).

### M3 P3 f-string to plain list

Part 3's inline list was `suggestions = [f"Process $300 refund on ORD-5001, reason: defective", f"Process $700 refund on ORD-5002, reason: wrong item"]` — `f"..."` prefixes with no `{}` interpolation, so the strings were already plain. The hoisted definition drops the `f` prefix with identical resulting values, and the authenticated-branch `st.pills(..., key="m3p3_pills")` now references it. Grep for `suggestions = [f"` in the file returns nothing, confirming no interpolating f-string list remains. The hoisted list sits at module-part top level, so it is in scope inside the later authenticated `else:` branch where the pills render.

### Scope, paths, and untouched sections

`grep -rn '/Users/erictole\|/home/ubuntu' app/pages/*.py` returns nothing — every `diagram_path` stays in its relative `os.path.join(os.path.dirname(...), "demos", ...)` form. The M1 P1 standalone `st.expander("💡 Suggested Prompts", ...)` is gone (`grep -c` returns 0); its three caption strings matched the hoisted `suggestions` in meaning, so folding them into the tab loses no information. Intentionally untouched: M1 Part 5 (Graph/Swarm, per-pattern code expanders, no `📐` tabs section), M2 Part 6 (Failure Modes, no diagram expander), M4 Part 4 and the `📐 Built-in Evaluators` markdown expander (no `st.tabs`), and the M3 Part 1 `💡 Try these` exploit-prompt helper (not a diagram tabs section). The pre-existing inline `suggestions` lists at M1 lines 610/738 and M2 line 733 belong to these untouched parts and are correctly left as-is.

### Unrelated demos/ changes

`git status` shows ~40 modified files under `demos/` plus untracked `config.env` files. Sampling the diff (`demos/module1-multi-agent/part1_single_agent.py`, `README.md`, `infra-agentcore/config.env`, `cleanup-all.sh`) shows model-ID migrations (`apac.anthropic.claude-sonnet-4` → `global.anthropic.claude-haiku-5-5`), regenerated AgentCore infra identifiers, and a new stack name in the cleanup list. None relate to the Prompts tab and none are in `app/pages/`. This change did not touch `demos/`, so the task's "only app/pages/*.py" constraint holds for the work under review; the demos edits are separate uncommitted tree state and should simply be kept out of any commit scoped to this task.

### Not tested

These Streamlit pages cannot execute without a running Streamlit server and AWS credentials, so `py_compile` plus structural grep counts are the authoritative static checks — behavior at runtime (tab renders, pill click-to-submit still fires, judge/metrics unchanged) was not exercised. The diff confirms no edits to chat loops, `chat_input`, judge calls, metric rendering, or session-state keys, which bounds the runtime risk to the new read-only tab bodies.

</details>

<details>
<summary>Files changed</summary>

- `app/pages/1_Module_1_Multi_Agent.py` — 4 Prompts tabs (P1–P4); P1 standalone `💡 Suggested Prompts` expander removed; P3 tab uses hardcoded dual lists (documented exception).
- `app/pages/2_Module_2_Context.py` — 5 Prompts tabs (P1–P5); P4 gets new read-only research-task list.
- `app/pages/3_Module_3_Security.py` — 3 Prompts tabs (P1–P3); P3 f-string list flattened to plain hoisted list.
- `app/pages/4_Module_4_Observability.py` — 3 Prompts tabs (P1–P3); P3 gets new read-only eval-query list.
- `app/pages/5_Module_5_Well_Architected.py` — 3 Prompts tabs (P1–P3), all before `📝 Code`.

Full diff: `git diff -- app/pages/` against `main`.

</details>
