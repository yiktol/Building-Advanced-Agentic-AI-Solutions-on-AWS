"""
Concept test: Part 2 - Multi-Agent Orchestrator.

Concept: an orchestrator routes each query to a focused specialist.

  Stage 1 PREFLIGHT   imports, AWS credentials, call recorders on specialists
  Stage 2 BASELINE    the single overloaded agent answers (informational)
  Stage 3 ROUTING     single-domain queries reach ONLY the right specialist
  Stage 4 MULTI       a mixed query reaches 2+ specialists
  Stage 5 ISOLATION   a specialist refuses out-of-scope questions
  Stage 6 SUMMARY

Usage (from module1-multi-agent/):  python test_concept/test_orchestrator_concept.py
"""
import time

from helpers import Suite, silent, has_aws_credentials, run


class Recorder:
    """Wraps a specialist agent and records every query routed to it."""

    def __init__(self, agent):
        self.agent, self.calls = agent, []

    def __call__(self, query, *a, **kw):
        self.calls.append(query)
        return self.agent(query, *a, **kw)


def main():
    s = Suite("Part 2 - Multi-Agent Orchestrator")

    s.banner(1, "PREFLIGHT")
    try:
        import part1_single_agent as p1
        import part2_multi_agent_orchestrator as p2
        s.check("demo modules import", True)
    except Exception as e:
        s.check("demo modules import", False, str(e))
        return s.finish()
    if not s.check("AWS credentials found", has_aws_credentials()):
        return s.finish()

    # @tool functions look these globals up at call time, so recorders see every routed query.
    rec = {"billing": Recorder(p2.billing_agent), "tech": Recorder(p2.tech_support_agent),
           "product": Recorder(p2.product_agent)}
    p2.billing_agent, p2.tech_support_agent, p2.product_agent = rec["billing"], rec["tech"], rec["product"]
    orchestrator = p2.create_orchestrator()
    s.info("orchestrator + 3 specialists created, call recorders attached")

    def reset():
        for r in rec.values():
            r.calls.clear()

    def routed():
        return {k for k, r in rec.items() if r.calls}

    s.banner(2, "BASELINE: single overloaded agent (informational)")
    q = ("My Hub drops Wi-Fi on firmware v2.1.3, I want a refund for order TM-1001, "
         "and which laptop is best for video editing?")
    s.info(f"Query: {q}")
    try:
        from strands import Agent
        from strands.models import BedrockModel
        single = Agent(model=BedrockModel(model_id=p1.MODEL_ID), system_prompt=p1.SYSTEM_PROMPT)
        t = time.time()
        r = silent(single, q)
        s.check("single agent answers", bool(str(r).strip()), f"{time.time() - t:.1f}s")
        s.snippet(r)
        s.info("No routing assertion: one agent has no specialists to route to.")
    except Exception as e:
        s.check("single agent answers", False, str(e))

    s.banner(3, "ROUTING: single-domain queries hit only the right specialist")
    for expected, q in [
        ("billing", "I was charged $9.99 but I cancelled my subscription. Order TM-78432."),
        ("tech", "My TechMart Hub keeps disconnecting from Wi-Fi. Firmware says v2.1.3."),
        ("product", "I need a laptop for college, budget $600-800, writing and video editing."),
    ]:
        reset()
        s.info(f"[{expected}] {q}")
        try:
            r = silent(orchestrator, q)
            s.check(f"'{expected}' query routed to {expected} only", routed() == {expected},
                    f"actual: {sorted(routed()) or 'none'}")
            s.snippet(r, 2)
        except Exception as e:
            s.check(f"'{expected}' query routed", False, str(e))

    s.banner(4, "MULTI: mixed query is split across specialists")
    reset()
    q = "If I buy the TechMart Pro 15, will it work with my Hub? Also, how do I get a refund on order TM-5555?"
    s.info(q)
    try:
        r = silent(orchestrator, q)
        s.check("2+ specialists called", len(routed()) >= 2, f"actual: {sorted(routed())}")
        s.check("product + billing both called", {"product", "billing"} <= routed())
        s.snippet(r)
    except Exception as e:
        s.check("multi-domain routing", False, str(e))

    s.banner(5, "ISOLATION: specialist stays inside its domain")
    q = "My router keeps dropping Wi-Fi. How do I update the firmware?"
    s.info(f"Asking the BILLING specialist directly: {q}")
    try:
        r = str(silent(p2.create_billing_agent(), q)).lower()
        s.check("billing agent declines tech question", "outside" in r and "billing" in r)
        s.snippet(r, 2)
    except Exception as e:
        s.check("billing agent declines tech question", False, str(e))

    s.finish()


if __name__ == "__main__":
    run(main)
