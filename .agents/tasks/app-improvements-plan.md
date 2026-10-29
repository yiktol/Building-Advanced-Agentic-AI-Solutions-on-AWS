# Implementation Plan — App Improvements (HEAVY, multi-subsystem)

Target repo: `/Users/erictole/demo/Building-Advanced-Agentic-Systems-on-AWS`
App code under `app/`. Work on the main working tree (no worktree). Do NOT commit, push, or deploy — the orchestrator reviews the full diff and handles commit/push/EC2 sync.

## Verified ground truth (from exploration)

- App files: `app/Home.py`, `app/agent_utils.py`, `app/agentcore_utils.py`, `app/style.py`, `app/pages/{1..5}_Module_*.py`.
- `app/agent_utils.py` already has: `MODEL_ID`, `_get_model_id()`, `_VALID_MODEL_IDS` (5 ids), `_DEFAULT_JUDGE_MODEL_ID`, `_get_judge_model_id()`, `get_model()`, `create_agent()`, `_default_metrics()`, `chat_response()`, `chat_response_with_metrics()`, `chat_stream()`. `get_model()` never passes `temperature`; reads `cfg_MODEL_ID` and `cfg_max_tokens` from session_state; hardcodes `region_name="ap-southeast-1"`.
- `chat_stream()` already exists and yields `event["data"]` chunks (fallback to full response).
- Live `BedrockModel(...)` construction sites to replace with the factory (display `st.code` strings are NOT touched):
  - `app/pages/1_Module_1_Multi_Agent.py`: line ~103 (`judge_response`), line ~235 (`judge_orchestrator_response`) — both judge.
  - `app/pages/2_Module_2_Context.py`: line ~203 (Part 2 prompt-caching agent, `cache_tools="default"`), line ~352 (Part 3 SummarizingConversationManager agent), line ~679 (judge in Part 6/context-failure). NOTE: lines ~170, ~317, ~320, ~418, ~420 are inside `st.code("""...""")` display blocks — DO NOT TOUCH.
  - `app/pages/3_Module_3_Security.py`: line ~133 (`judge_security`), line ~398 (`judge_cedar`) — both judge.
  - `app/pages/4_Module_4_Observability.py`: line ~367-368 (Part 3 judge `_BM`, `max_tokens=1024`).
  - `app/pages/5_Module_5_Well_Architected.py`: line ~31 (economy tier `apac.amazon.nova-micro-v1:0`, `max_tokens=1024` — KEEP this model id, pass explicitly), line ~33 (premium tier, `MODEL_ID`, `max_tokens=2048`). Lines ~105, ~381 are display `st.code` — DO NOT TOUCH.
  - `app/agentcore_utils.py`: line ~206-209 (`AgentCoreEvaluator.evaluate` local judge fallback, `_BM`) — judge.
- Metric dict access audit:
  - `app/pages/2_Module_2_Context.py` has BARE access to fix: Part 1 `m['inputTokens']`, `m['outputTokens']`, `m['totalTokens']`, `prev['inputTokens']`, `prev['totalTokens']` (~lines 88-99); `latest['inputTokens']` (~104-105); `metrics['inputTokens']`, `metrics['totalTokens']`, `prev[...]` in the delta expressions (~134-137); `entry["totalTokens"]`, `entry["inputTokens"]` (~605-606). Lines ~191-192 are inside `st.code` — DO NOT TOUCH.
  - `app/pages/4_Module_4_Observability.py`: Part 1 already uses `.get(...)` for display; `metrics["latencyMs"]`/`metrics["toolCalls"]` writes (~160-161, 184-185) are assignments, not reads — leave. No bare reads to fix.
  - `app/pages/5_Module_5_Well_Architected.py`: already uses `m.get(...)`. No bare reads.
  - `app/pages/1_Module_1_Multi_Agent.py`, `3_Module_3_Security.py`: no bare metric-dict reads found.
- Status indicator: `app/pages/1_Module_1_Multi_Agent.py` Part 4 already shows a memory status line; module pages do NOT currently show a near-title live-vs-local caption. Home keeps its full status line. No per-service sidebar badges exist on module pages (good — do not add).
- DynamoDB defaults already correct in `app/pages/3_Module_3_Security.py`: `CUSTOMERS_TABLE` default `m3-demo-customers`, `ORDERS_TABLE` default `m3-demo-orders`.
- `app/requirements.txt`: `streamlit>=1.60.0`, `strands-agents>=1.50.0`, `strands-agents-tools>=0.2.19`, `boto3>=1.35.0`. No `app/tests/`, no dev deps file.
- Deploy: `deploy/deploy.sh` (CFN, `set -e -o pipefail`), `deploy/sync-ec2.sh` (uses `git pull origin main`; `REPO_DIR=/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS`; service `mladas-app`; ASG `mladas-app-asg`; copies repo-root `.env`), `deploy/cleanup.sh`, `deploy/README.md`.
- `demos/infra-agentcore/cfn-agentcore-evaluator.yaml` (already git-modified): defines `ToolSelectionEvaluator` + `ComplianceEvaluator` (good) PLUS `EvaluationLogGroup`, `EvaluationExecutionRole`, `OnlineEvalConfig` (`AWS::BedrockAgentCore::OnlineEvaluationConfig` referencing `Builtin.*` evaluator ids) and outputs `OnlineEvalConfigId`/`OnlineEvalConfigArn` — this is the resource that fails CFN early validation.
- `demos/module3-security/scripts/deploy.sh`: `DEFAULT_PASSWORD="Hero\$ecure1!"` hardcoded (~line 9); user-creation loop uses `declare -A USERS` (~line 95) which fails on macOS Bash 3.2 (confirmed: local shell is `GNU bash 3.2.57`). 5 hero users with role/dept/hero_name/max_refund attributes and permanent passwords.
- Local env: Python 3.13, Bash 3.2.57. `bash -n` and `python3 -m py_compile` are available for offline verification.

## Dependency ordering (critical)

1. **#1 model factory lands FIRST** — all page/agentcore call-site edits depend on `make_model` existing and exported from `app/agent_utils.py`.
2. **#3 defensive metrics** is independent but touches the same pages as #5/#6/#7; group the Module-2/Module-4 edits to avoid churn.
3. **#2 .env generation** and **#3/#5** interact only via env var names (`CUSTOMERS_TABLE`, `ORDERS_TABLE`, `AWS_REGION`, service ids) — keep the generated key names identical to what `agentcore_utils._get_config`/`Home.py` read.
4. **#10 test suite** lands LAST among app work — it imports `make_model`, `_get_judge_model_id`, `chat_response_with_metrics`, and the DynamoDB defaults, so #1 and #3 must be in place.
5. Deploy/infra items (#2, #4, #8, cognito password) are independent of app items and can land in any order relative to them.

---

## Items

- [ ] 1. Add central model factory `make_model` to `app/agent_utils.py` and refactor `get_model()`/`create_agent()`/judge construction to route through it.
      `make_model(purpose: str = "generation", model_id: str | None = None, **overrides) -> BedrockModel`. Rules: always set `region_name` from `AWS_REGION` env else `"ap-southeast-1"`; resolve model id precedence: explicit `model_id` arg > session_state (`cfg_MODEL_ID` for generation, `cfg_JUDGE_MODEL_ID` for judge) > default `global.anthropic.claude-haiku-5-5`; validate the resolved id against `_VALID_MODEL_IDS` and fall back to the default if invalid/stale; NEVER pass `temperature` (claude-haiku-5.x rejects it); honor `max_tokens` from `cfg_max_tokens` session_state (default 2048) unless overridden; accept per-call `**overrides` (e.g. `max_tokens`, `cache_tools`) and forward them to `BedrockModel`. Refactor `get_model()` to `return make_model("generation")`; keep `create_agent()` calling `get_model()` (or `make_model`). Keep `_get_judge_model_id()` but have judge callers use `make_model("judge")`. Export `make_model` (module-level def, importable).
      Files: `app/agent_utils.py`
      Verify: `cd app && python3 -m py_compile agent_utils.py` succeeds; `cd app && python3 -c "import agent_utils as a; m=a.make_model('generation', model_id='bogus-id'); print(type(m).__name__)"` prints `BedrockModel` and does not raise (confirms allow-list fallback and no network call at construction).

- [ ] 2. Replace every live `BedrockModel(...)` construction across the pages and `agentcore_utils.py` with `make_model`, preserving each call's overrides; leave all `st.code(...)` display strings untouched.
      Generation vs judge per call: M5 Part 1 economy tier → `make_model("generation", model_id="apac.amazon.nova-micro-v1:0", max_tokens=1024)`; M5 premium tier → `make_model("generation", max_tokens=2048)`; M2 Part 2 → `make_model("generation", cache_tools="default")`; M2 Part 3 → `make_model("generation")`; all judge sites (M1 x2, M2 context-failure, M3 x2, M4 Part 3 `max_tokens=1024`, `agentcore_utils.AgentCoreEvaluator.evaluate` fallback) → `make_model("judge", ...)` preserving `max_tokens` overrides. Remove now-unused `from strands.models import BedrockModel` imports only where no display/other use remains (M2 keeps it if still referenced elsewhere — verify before removing). Depends on item 1.
      Files: `app/pages/1_Module_1_Multi_Agent.py`, `app/pages/2_Module_2_Context.py`, `app/pages/3_Module_3_Security.py`, `app/pages/4_Module_4_Observability.py`, `app/pages/5_Module_5_Well_Architected.py`, `app/agentcore_utils.py`
      Verify: `cd app && python3 -m py_compile pages/*.py agentcore_utils.py` succeeds; `grep -rn "BedrockModel(" app/pages app/agentcore_utils.py` returns only matches inside `st.code(` display blocks (M2 only).

- [ ] 3. Convert bare metric-dict reads to `.get(key, 0)` in `app/pages/2_Module_2_Context.py`.
      Fix Part 1 metric block (`m['inputTokens']`→`m.get('inputTokens',0)` etc. incl. the `prev[...]` delta expressions and the `latest['inputTokens']` context-window progress), the Part-1-style metric columns (~lines 134-137 `metrics['...']`/`prev['...']` deltas), and the Part 5 token-log sums (`entry["totalTokens"]`/`entry["inputTokens"]`). Do NOT touch the `st.code("""...""")` display block that prints `usage["cacheReadInputTokens"]`.
      Files: `app/pages/2_Module_2_Context.py`
      Verify: `cd app && python3 -m py_compile pages/2_Module_2_Context.py` succeeds; `grep -nE "(m|prev|latest|metrics|entry)\[['\"](inputTokens|outputTokens|totalTokens|latencyMs|toolCalls|cacheReadInputTokens|cacheWriteInputTokens)['\"]\]" app/pages/2_Module_2_Context.py` returns only matches inside the `st.code` display block.

- [ ] 4. Add an honest "running on real AWS vs local simulation" caption under the title of each module page (NOT Home).
      Add a small helper in `app/style.py`, e.g. `live_services_caption()` that calls `agentcore_utils.get_agentcore_status()` and renders one subtle `st.caption` line (e.g. "🟢 Live AWS: Memory, Evaluator, Cognito · Region ap-southeast-1" vs "⚪ Local simulation — no AWS services resolved · Region …"). Call it once near the top of each of pages 1–5 (after `inject_css()`, before/after the part radio — pick a single consistent spot, e.g. immediately after the sidebar block at module scope so it shows for every part). Do NOT re-add per-service sidebar badges; keep Home's existing status line as-is. Keep it to one line.
      Files: `app/style.py`, `app/pages/1_Module_1_Multi_Agent.py`, `app/pages/2_Module_2_Context.py`, `app/pages/3_Module_3_Security.py`, `app/pages/4_Module_4_Observability.py`, `app/pages/5_Module_5_Well_Architected.py`
      Verify: `cd app && python3 -m py_compile style.py pages/*.py` succeeds; `grep -rn "live_services_caption\|get_agentcore_status" app/pages` shows it invoked in all 5 module pages and `grep -c "live_services_caption" app/Home.py` returns 0.

- [ ] 5. Stream single-agent chat responses with `st.write_stream(chat_stream(...))` where plain `chat_response` is used today and no metrics/judge depend on the return object.
      Apply to: M1 Part 1 (`m1p1_agent`, both pills + chat_input paths — stream the text, then run judge on the streamed string), M1 Part 3 (`m1p3_agent`), M4 Part 1 uses `chat_response_with_metrics` — leave blocking to preserve metrics/tool-count (do NOT stream), M5 parts that use plain chat. For each converted site, capture the streamed text (`resp = st.write_stream(chat_stream(agent, msg))`) and keep appending `resp` to the `_msgs` session_state and feeding judge where present. Where a part shows metrics via `chat_response_with_metrics` or relies on the response metrics object (M4 P1, M5 P1), leave it blocking. Preserve `submit_mode="disable"`, spinners can be dropped on streamed paths.
      Files: `app/pages/1_Module_1_Multi_Agent.py`, `app/pages/5_Module_5_Well_Architected.py`
      Verify: `cd app && python3 -m py_compile pages/1_Module_1_Multi_Agent.py pages/5_Module_5_Well_Architected.py` succeeds; `grep -n "write_stream\|chat_stream" app/pages/1_Module_1_Multi_Agent.py` shows streaming wired into Part 1 and Part 3; manual note: judge calls still receive the full streamed string.

- [ ] 6. Add a cost-estimate helper and a compact per-session cost/latency panel on Module 4.
      Add `estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float` (or token-total based) to `app/agent_utils.py` with a clearly-labeled illustrative price table keyed by model id (`global.anthropic.claude-haiku-5-5`, `global.anthropic.claude-haiku-4-5-20251001-v1:0`, `apac.amazon.nova-micro-v1:0`, `apac.amazon.nova-lite-v1:0`, `apac.amazon.nova-pro-v1:0`) — approximate per-1K-token USD, documented as "estimated, not billing-accurate". On `app/pages/4_Module_4_Observability.py` Part 1, add one small `st.container(border=True)` panel summing session tokens + estimated cost + total/avg latency from `st.session_state.m4p1_metrics`, labeled "Estimated session cost". Use `.get(...)` for all metric reads.
      Files: `app/agent_utils.py`, `app/pages/4_Module_4_Observability.py`
      Verify: `cd app && python3 -m py_compile agent_utils.py pages/4_Module_4_Observability.py` succeeds; `cd app && python3 -c "import agent_utils as a; print(round(a.estimate_cost('global.anthropic.claude-haiku-5-5', 1000, 500), 6))"` prints a non-negative float.

- [ ] 7. Add a deploy helper that writes `.env` from live CloudFormation outputs (idempotent).
      Create `deploy/generate-env.sh` that queries the same stacks `Home.py`/`agentcore_utils` list (`mladas-agentcore-memory`, `-evaluator`, `-gateway`, `-policy`, `-guardrail`, `m3-demo-cognito`, `m3-demo-verified-permissions`) in `${AWS_REGION:-ap-southeast-1}` and writes repo-root `.env` (the file `sync-ec2.sh` copies) with: `AWS_REGION`, `SharedMemoryId`, `ToolSelectionEvaluatorId`, `GatewayId`, `PolicyStoreId`, `PolicyEngineId`, `GuardrailId`, `GuardrailVersion`, `UserPoolId`/`CognitoUserPoolId`, `UserPoolClientId`/`CognitoClientId`, `CUSTOMERS_TABLE=m3-demo-customers`, `ORDERS_TABLE=m3-demo-orders`. Only emit keys whose values resolved (no blank/stale overwrites); re-runnable (regenerate cleanly). Do NOT hardcode resource ids — derive from CFN at runtime. Document usage in `deploy/README.md`. Do NOT run it.
      Files: `deploy/generate-env.sh`, `deploy/README.md`
      Verify: `bash -n deploy/generate-env.sh` passes; `grep -n "CUSTOMERS_TABLE=m3-demo-customers\|ORDERS_TABLE=m3-demo-orders" deploy/generate-env.sh` matches; `grep -n "generate-env" deploy/README.md` shows it documented. (No AWS calls executed in verification.)

- [ ] 8. Make the evaluator CFN stack deploy reliably by removing the failing `OnlineEvaluationConfig` resource and its outputs.
      In `demos/infra-agentcore/cfn-agentcore-evaluator.yaml` remove `OnlineEvalConfig` (`AWS::BedrockAgentCore::OnlineEvaluationConfig`) plus the now-unused `EvaluationLogGroup` and `EvaluationExecutionRole` if only referenced by it, and remove the `OnlineEvalConfigId`/`OnlineEvalConfigArn` outputs. Keep `ToolSelectionEvaluator` + `ComplianceEvaluator` and their `...EvaluatorId`/`...EvaluatorArn` outputs (the app only needs `ToolSelectionEvaluatorId`/`ComplianceEvaluatorId`).
      Files: `demos/infra-agentcore/cfn-agentcore-evaluator.yaml`
      Verify: `python3 -c "import yaml,sys; yaml.safe_load(open('demos/infra-agentcore/cfn-agentcore-evaluator.yaml'))" 2>/dev/null || echo 'note: CFN intrinsics (!Ref/!GetAtt) are not plain YAML — use a tag-tolerant check'`; practical check: `grep -c "OnlineEvaluationConfig\|OnlineEvalConfig" demos/infra-agentcore/cfn-agentcore-evaluator.yaml` returns 0 and `grep -c "ToolSelectionEvaluatorId" demos/infra-agentcore/cfn-agentcore-evaluator.yaml` returns ≥1.

- [ ] 9. Make the Module 3 user-creation loop Bash-3.2 compatible and the demo password env-configurable.
      In `demos/module3-security/scripts/deploy.sh`: replace `declare -A USERS` + `for EMAIL in "${!USERS[@]}"` with a POSIX/Bash-3.2 approach — a newline-delimited here-doc/variable of `email,role,dept,hero,max_refund` rows iterated with `while IFS=',' read -r ...` (preserve all 5 hero users: Superman/admin/finance/10000, Batman/security_lead/security/5000, Spider-Man/agent/support/500, Wonder Woman/manager/operations/2000, Iron Man/engineer/engineering/0; preserve custom attrs and permanent-password step). Change `DEFAULT_PASSWORD="Hero\$ecure1!"` to `DEFAULT_PASSWORD="${DEMO_USER_PASSWORD:-Hero\$ecure1!}"` so it stays the current password by default but can be overridden by env var. Document the override in `deploy/README.md`. Never commit a new secret.
      Files: `demos/module3-security/scripts/deploy.sh`, `deploy/README.md`
      Verify: `bash -n demos/module3-security/scripts/deploy.sh` passes under local Bash 3.2; `grep -c "declare -A" demos/module3-security/scripts/deploy.sh` returns 0; `grep -n "DEMO_USER_PASSWORD" demos/module3-security/scripts/deploy.sh deploy/README.md` shows both the default and the doc note; confirm all 5 hero rows still present via `grep -c "Superman\|Batman\|Spider-Man\|Wonder Woman\|Iron Man" demos/module3-security/scripts/deploy.sh`.

- [ ] 10. Harden `deploy/sync-ec2.sh` git update to be deterministic and document the zero-downtime ASG option.
      Replace the remote `git pull origin main` command with `git fetch origin main && git reset --hard origin/main` (run as the `ubuntu` user, same `cd $REPO_DIR`). Preserve the `.env` copy step and the service restart. In `deploy/README.md` document the opt-in zero-downtime approach (raise ASG `mladas-app-asg` MaxSize to 2 before an instance refresh); optionally add a commented/opt-in flag in the script but do NOT change live AWS behavior by default. Do NOT run the script.
      Files: `deploy/sync-ec2.sh`, `deploy/README.md`
      Verify: `bash -n deploy/sync-ec2.sh` passes; `grep -n "reset --hard origin/main" deploy/sync-ec2.sh` matches and `grep -c "git pull origin main" deploy/sync-ec2.sh` returns 0; `grep -n "MaxSize" deploy/README.md` shows the zero-downtime note.

- [ ] 11. Create the offline-by-default smoke test suite and a dev-deps file.
      Create `app/requirements-dev.txt` with `pytest` (and `pyyaml` if used by CFN checks) — do NOT add to runtime `app/requirements.txt`. Create `app/tests/` with `conftest.py` (adds `app/` to `sys.path`, defines a `live` marker) and tests that would have caught this session's bugs: (a) `make_model` never passes `temperature` for claude-haiku-5.x (inspect constructed model kwargs / assert factory omits temperature); (b) `_get_judge_model_id()` returns a value in `_VALID_MODEL_IDS`; (c) `make_model('generation', model_id='bogus')` falls back to a valid id without raising; (d) `chat_response_with_metrics` return shape — assert `_default_metrics()`/metrics dict always contains `inputTokens,outputTokens,totalTokens,cacheReadInputTokens,cacheWriteInputTokens,latencyMs`; (e) DynamoDB table-name defaults resolve to `m3-demo-customers`/`m3-demo-orders` (import module-level defaults or assert the `os.environ.get(..., default)` default); (f) `estimate_cost` returns a non-negative float. Mark any test needing live Bedrock/AWS with `@pytest.mark.live` and skip by default (register the marker and skip unless `--run-live`/env flag). Add a one-line run command to `app/tests/README.md`. Depends on items 1, 3, 6.
      Files: `app/requirements-dev.txt`, `app/tests/conftest.py`, `app/tests/test_model_factory.py`, `app/tests/test_metrics.py`, `app/tests/test_defaults.py`, `app/tests/README.md`
      Verify: `cd app && python3 -m pip install -r requirements-dev.txt` (if not already installed) then `cd app && python3 -m pytest tests -q` runs offline (live tests skipped) and all non-live tests pass; `grep -n "pytest" app/requirements.txt` returns nothing (dev deps stayed out of runtime).

- [ ] 12. Final consistency pass: compile everything and re-verify AWS resource references.
      Confirm all pages reference deployed resources correctly: region default `ap-southeast-1`, DynamoDB `m3-demo-customers`/`m3-demo-orders`, config keys resolved via `agentcore_utils._get_config` / `Home.get_cfn_outputs` (Memory/Evaluator/Gateway/Policy/Guardrail/Cognito), no absolute diagram paths (`/Users/erictole` or `/home/ubuntu`) — all diagram paths stay relative via `os.path.join(os.path.dirname(...))`. Confirm `part_header` styling, the Diagram/About/Prompts tabs, judge eval, M4 thread-safe tool counter, and session_state keys are all intact.
      Files: (review only) `app/Home.py`, `app/pages/*.py`, `app/agentcore_utils.py`, `app/agent_utils.py`
      Verify: `cd app && python3 -m py_compile Home.py agent_utils.py agentcore_utils.py style.py pages/*.py` succeeds; `grep -rn "/Users/erictole\|/home/ubuntu" app/pages app/*.py` returns nothing; `cd app && python3 -m pytest tests -q` still passes offline.

## Gaps / assumptions

- `deploy/sync-ec2.sh` `REPO_DIR` is `/home/ubuntu/Building-Advanced-Agentic-AI-Solutions-on-AWS` (note: differs from this checkout's folder name). This is pre-existing and out of scope; item 10 only changes the git update command, not the path. Flag to orchestrator if the EC2 clone path has changed.
- The task spec lists improvements #1–#8, #10 and two "decisions already made"; there is no #9 (skipped) and no standalone #11 — the Cognito-password change is folded into item 9 here per the decisions block.
- CFN template uses `!Ref`/`!GetAtt` short tags, so plain `yaml.safe_load` will error; item 8 verification relies on grep + the orchestrator's real `aws cloudformation validate-template` at deploy time (not run in this workflow).
- Price table values in item 6 are illustrative; exact per-model rates are a reasonable estimate, clearly labeled "estimated, not billing-accurate".
