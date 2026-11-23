"""
Generate sample observability and evaluation data for the techmart_support AgentCore Runtime agent.

Runs a set of customer scenarios against the deployed runtime (single-turn and multi-turn
sessions, including out-of-catalog and off-topic requests so the scores vary), then:

  Stage 1  PREFLIGHT    resolve the runtime and online eval config from CloudFormation
  Stage 2  INVOKE       run every scenario; prints tools called, tokens and latency
  Stage 3  TRACES       wait for each session's spans in CloudWatch Transaction Search (aws/spans)
  Stage 4  EVALUATE     score each session with the AgentCore built-in evaluators (on-demand Evaluate)
  Stage 5  ONLINE       optionally wait for the online evaluation config to score the same sessions
  Stage 6  SUMMARY      per-scenario scores and where to find the data in CloudWatch

Usage (from anywhere):
    python agents/techmartagent/scripts/generate_sample_data.py              # stages 1-4 and 6
    python .../generate_sample_data.py --online-wait 20                      # also wait up to 20 min for online eval
    python .../generate_sample_data.py --no-evaluate                         # traffic only (stages 1-2, 6)
    python .../generate_sample_data.py --repeat 3                            # run the scenario set 3 times

Needs AWS credentials for the account the runtime is deployed in. Each run makes Bedrock calls
(agent + evaluators), so it costs a few cents. Exit code: 0 ok, 1 failures, 130 Ctrl+C.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

import boto3

REGION = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1"))
STACK = "AgentCore-techmartagent-default"

BUILTIN_EVALUATORS = [
    "Builtin.Correctness",
    "Builtin.Helpfulness",
    "Builtin.Coherence",
    "Builtin.ToolSelectionAccuracy",
    "Builtin.GoalSuccessRate",
]

# Each scenario is one runtime session; multi-turn scenarios keep the same session ID.
SCENARIOS = [
    {"name": "laptop-under-800", "turns": ["Which laptop under $800 do you have, and is it in stock?"]},
    {"name": "hub-stock", "turns": ["Is the TechMart Hub in stock? I need 5 of them."]},
    {"name": "refund-policy", "turns": ["I bought a laptop 45 days ago and want my money back. What are my options?"]},
    {"name": "compare-and-buy", "turns": [
        "What's the difference between the TechMart Air and the Pro 15?",
        "I edit videos. Which one should I get, and do you have it in stock?",
    ]},
    {"name": "out-of-catalog", "turns": ["Do you sell a gaming laptop for under $300?"]},
    {"name": "off-topic", "turns": ["Can you book me a flight to Singapore next week?"]},
]

# --- Colours (one per stage) ---
RESET, DIM, BOLD = "\033[0m", "\033[2m", "\033[1m"
PASS, FAIL, WARN = "\033[1;32m", "\033[1;31m", "\033[1;33m"
STAGE_BG = {1: "\033[1;97;44m", 2: "\033[1;30;43m", 3: "\033[1;97;46m", 4: "\033[1;97;45m", 5: "\033[1;97;42m", 6: "\033[1;30;47m"}
STAGE_FG = {1: "\033[34m", 2: "\033[33m", 3: "\033[36m", 4: "\033[35m", 5: "\033[32m", 6: "\033[37m"}


def banner(stage: int, title: str):
    print(f"\n{STAGE_BG[stage]}{'=' * 76}{RESET}")
    print(f"{STAGE_BG[stage]}  STAGE {stage}: {title:<66}{RESET}")
    print(f"{STAGE_BG[stage]}{'=' * 76}{RESET}")


def info(stage: int, msg: str):
    print(f"  {STAGE_FG[stage]}{msg}{RESET}", flush=True)


def ok(msg: str):
    print(f"  ✅ {PASS}{msg}{RESET}", flush=True)


def bad(msg: str):
    print(f"  ❌ {FAIL}{msg}{RESET}", flush=True)


def colour_score(v) -> str:
    if v is None:
        # No result: e.g. ToolSelectionAccuracy when the agent called no tools.
        return f"{DIM}  n/a{RESET}"
    c = PASS if v >= 0.75 else WARN if v >= 0.5 else FAIL
    return f"{c}{v:5.2f}{RESET}"


# ------------------------------------------------------------------ AWS helpers
def resolve_ids() -> tuple[str, str]:
    outs = boto3.client("cloudformation", region_name=REGION).describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
    arn = next(o["OutputValue"] for o in outs if o["OutputKey"].startswith("ApplicationAgentTechmartSupportRuntimeArnOutput"))
    oe = next((o["OutputValue"] for o in outs if o["OutputKey"].startswith("ApplicationOnlineEvalTechmartOnlineEvalIdOutput")), "")
    return arn, oe


def new_session_id(name: str) -> str:
    # Runtime session IDs must be at least 33 characters.
    return f"sample-{name}-{uuid.uuid4().hex}"


def invoke(client, arn: str, session_id: str, prompt: str) -> dict:
    started = time.time()
    resp = client.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=session_id,
                                       payload=json.dumps({"prompt": prompt}).encode(), qualifier="DEFAULT")
    text, tools, tokens = [], [], 0
    for raw in resp["response"].iter_lines():
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        try:
            event = json.loads(line[5:].strip()).get("event", {})
        except Exception:
            continue
        start = event.get("contentBlockStart", {}).get("start", {})
        if isinstance(start, dict) and "toolUse" in start:
            tools.append(start["toolUse"].get("name", "?"))
        delta = event.get("contentBlockDelta", {}).get("delta", {})
        if "text" in delta:
            text.append(delta["text"])
        if "metadata" in event:
            tokens += int(event["metadata"].get("usage", {}).get("totalTokens", 0))
    return {"text": "".join(text), "tools": tools, "tokens": tokens, "ms": int((time.time() - started) * 1000)}


def query_spans(logs, session_id: str) -> list[dict]:
    end = int(time.time())
    q = ("fields @timestamp, @message | filter ispresent(scope.name) and ispresent(attributes.session.id) "
         f'| filter attributes.session.id = "{session_id}" | sort @timestamp asc | limit 10000')
    out = []
    for group in ("aws/spans", RUNTIME_LOG_GROUP):
        try:
            qid = logs.start_query(logGroupName=group, startTime=end - 7200, endTime=end + 60, queryString=q)["queryId"]
        except Exception:
            continue
        for _ in range(60):
            r = logs.get_query_results(queryId=qid)
            if r["status"] in ("Complete", "Failed", "Cancelled", "Timeout"):
                break
            time.sleep(1)
        for row in r.get("results", []):
            for f in row:
                if f["field"] == "@message" and f["value"].strip().startswith("{"):
                    try:
                        out.append(json.loads(f["value"]))
                    except Exception:
                        pass
    return out


def span_count(spans: list[dict]) -> int:
    return sum(1 for s in spans if "spanId" in s)


def spans_ready(spans: list[dict]) -> bool:
    """Agent spans (invoke_agent + chat) present; Evaluate rejects input without them."""
    names = [str(s.get("name", "")) for s in spans if "spanId" in s and "kind" in s]
    return any(n.startswith("invoke_agent") for n in names) and any(n.startswith("chat") for n in names)


def online_results(logs, log_group: str, session_id: str) -> list[dict]:
    rows, kwargs = [], {"logGroupName": log_group, "filterPattern": f'"{session_id}"',
                        "startTime": int((time.time() - 4 * 3600) * 1000)}
    try:
        while True:
            page = logs.filter_log_events(**kwargs)
            for ev in page.get("events", []):
                try:
                    a = json.loads(ev["message"]).get("attributes", {})
                except Exception:
                    continue
                if a.get("session.id") == session_id:
                    rows.append({"evaluator": a.get("gen_ai.evaluation.name", ""), "value": a.get("gen_ai.evaluation.score.value")})
            if not page.get("nextToken"):
                break
            kwargs["nextToken"] = page["nextToken"]
    except logs.exceptions.ResourceNotFoundException:
        pass
    return rows


def averages(rows: list[dict]) -> dict:
    by = {}
    for r in rows:
        if r.get("value") is not None:
            by.setdefault(r["evaluator"], []).append(float(r["value"]))
    return {k: sum(v) / len(v) for k, v in by.items()}


def score_line(avg: dict) -> str:
    return "  ".join(f"{e.replace('Builtin.', '')[:12]:>12} {colour_score(avg.get(e))}" for e in BUILTIN_EVALUATORS)


# ------------------------------------------------------------------ main
RUNTIME_LOG_GROUP = ""


def main():
    global RUNTIME_LOG_GROUP
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repeat", type=int, default=1, help="run the scenario set N times (default 1)")
    p.add_argument("--no-evaluate", action="store_true", help="only generate traffic; skip traces and evaluation")
    p.add_argument("--trace-wait", type=int, default=6, help="minutes to wait for spans per run (default 6)")
    p.add_argument("--online-wait", type=int, default=0, help="minutes to wait for online evaluation results (default 0 = skip)")
    args = p.parse_args()
    failures = 0
    started = time.time()

    # ------------------------------------------------------------ Stage 1
    banner(1, "PREFLIGHT")
    try:
        identity = boto3.client("sts", region_name=REGION).get_caller_identity()
        ok(f"AWS account {identity['Account']}, region {REGION}")
        arn, online_eval = resolve_ids()
    except Exception as e:
        bad(f"cannot resolve the runtime from stack {STACK}: {e}")
        sys.exit(1)
    runtime_id = arn.split("/")[-1]
    RUNTIME_LOG_GROUP = f"/aws/bedrock-agentcore/runtimes/{runtime_id}-DEFAULT"
    ok(f"runtime {runtime_id}")
    info(1, f"online eval config: {online_eval or 'not deployed'}")
    agent = boto3.client("bedrock-agentcore", region_name=REGION)
    logs = boto3.client("logs", region_name=REGION)

    # ------------------------------------------------------------ Stage 2
    banner(2, f"INVOKE: {len(SCENARIOS)} scenarios x {args.repeat}")
    sessions = []
    for rnd in range(1, args.repeat + 1):
        for sc in SCENARIOS:
            sid = new_session_id(sc["name"])
            sess = {"name": sc["name"], "round": rnd, "session_id": sid, "turns": [], "ok": True}
            info(2, f"[{sc['name']}] round {rnd} · session {sid}")
            for prompt in sc["turns"]:
                try:
                    r = invoke(agent, arn, sid, prompt)
                    sess["turns"].append(r)
                    print(f"    {DIM}you:{RESET} {prompt}")
                    print(f"    {DIM}agent:{RESET} {r['text'][:110].replace(chr(10), ' ')}{'…' if len(r['text']) > 110 else ''}")
                    print(f"    {DIM}tools={r['tools'] or 'none'} tokens={r['tokens']} latency={r['ms']}ms{RESET}")
                except Exception as e:
                    sess["ok"] = False
                    failures += 1
                    bad(f"invoke failed: {e}")
                    break
            sessions.append(sess)
    ok(f"{sum(len(s['turns']) for s in sessions)} invocations across {len(sessions)} sessions")

    if not args.no_evaluate:
        # ------------------------------------------------------------ Stage 3
        banner(3, "TRACES: wait for spans in CloudWatch Transaction Search")
        info(3, "ingestion usually takes 1 to 3 minutes")
        pending = [s for s in sessions if s["ok"]]
        deadline = time.time() + args.trace_wait * 60
        while pending and time.time() < deadline:
            time.sleep(20)
            for s in list(pending):
                spans = query_spans(logs, s["session_id"])
                # Complete once the agent spans are there and the count stopped growing since the last poll.
                if spans_ready(spans) and span_count(spans) == s.get("_last", -1):
                    s["spans"] = spans
                    pending.remove(s)
                    ok(f"[{s['name']}] {span_count(spans)} spans after {int(time.time() - started)}s")
                else:
                    s["_last"] = span_count(spans) if spans_ready(spans) else -1
            if pending:
                info(3, f"waiting for {len(pending)} session(s)…")
        time.sleep(15)  # let late spans land, then take a final snapshot
        for s in sessions:
            if "spans" in s:
                s["spans"] = query_spans(logs, s["session_id"])
        for s in pending:
            failures += 1
            bad(f"[{s['name']}] no spans within {args.trace_wait} min")

        # ------------------------------------------------------------ Stage 4
        banner(4, "EVALUATE: on-demand AgentCore built-in evaluators")
        for s in sessions:
            if not s.get("spans"):
                continue
            rows = []
            for ev in BUILTIN_EVALUATORS:
                try:
                    res = agent.evaluate(evaluatorId=ev, evaluationInput={"sessionSpans": s["spans"]})
                    for x in res.get("evaluationResults", []):
                        rows.append({"evaluator": ev, "value": x.get("value"), "error": x.get("errorMessage", "")})
                except Exception as e:
                    rows.append({"evaluator": ev, "value": None, "error": str(e)})
            s["ondemand"] = averages(rows)
            errs = [r for r in rows if r["value"] is None]
            print(f"  {BOLD}{s['name']:<18}{RESET}{score_line(s['ondemand'])}")
            for r in errs:
                failures += 1
                bad(f"{r['evaluator']}: {r['error'][:140]}")

        # ------------------------------------------------------------ Stage 5
        if args.online_wait and online_eval:
            banner(5, "ONLINE: wait for the online evaluation config")
            group = f"/aws/bedrock-agentcore/evaluations/results/{online_eval}"
            info(5, f"results go to {group}; sessions are scored after 5 min idle")
            pending = [s for s in sessions if s["ok"]]
            deadline = time.time() + args.online_wait * 60
            while pending and time.time() < deadline:
                time.sleep(60)
                for s in list(pending):
                    avg = averages(online_results(logs, group, s["session_id"]))
                    if len(avg) >= len(BUILTIN_EVALUATORS):
                        s["online"] = avg
                        pending.remove(s)
                        ok(f"[{s['name']}] online results in")
                info(5, f"{int((time.time() - started) / 60)} min elapsed, {len(pending)} session(s) pending")
            for s in pending:
                partial = averages(online_results(logs, group, s["session_id"]))
                if partial:
                    s["online"] = partial
                info(5, f"[{s['name']}] online results not complete yet; check later with the session ID")

    # ------------------------------------------------------------ Stage 6
    banner(6, "SUMMARY")
    for s in sessions:
        icon = "✅" if s["ok"] else "❌"
        print(f"  {icon} {BOLD}{s['name']:<18}{RESET}{DIM}{s['session_id']}{RESET}")
        if s.get("ondemand"):
            print(f"     on-demand {score_line(s['ondemand'])}")
        if s.get("online"):
            print(f"     online    {score_line(s['online'])}")
    console = f"https://{REGION}.console.aws.amazon.com/cloudwatch/home?region={REGION}"
    print(f"\n  {BOLD}Where the data is{RESET}")
    print(f"  {DIM}traces    {RESET}Transaction Search, log group aws/spans (filter attributes.session.id)")
    print(f"  {DIM}runtime   {RESET}{RUNTIME_LOG_GROUP}")
    print(f"  {DIM}vended    {RESET}/aws/vendedlogs/bedrock-agentcore/runtime/APPLICATION_LOGS/{runtime_id} and .../USAGE_LOGS/{runtime_id}")
    if online_eval:
        print(f"  {DIM}online    {RESET}/aws/bedrock-agentcore/evaluations/results/{online_eval}")
    print(f"  {DIM}dashboard {RESET}{console}#gen-ai-observability/agent-core")
    print(f"\n  {DIM}{int(time.time() - started)}s total{RESET}")
    if failures:
        print(f"\n  {FAIL}❌ finished with {failures} failure(s){RESET}\n")
        sys.exit(1)
    print(f"\n  {PASS}✅ sample data generated{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {FAIL}Interrupted. Goodbye!{RESET}")
        sys.exit(130)
