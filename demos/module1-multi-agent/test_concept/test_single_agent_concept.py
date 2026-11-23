"""
Concept test: Part 1 - Single Agent Limitations.

Concept: one agent with an overloaded prompt CAN answer all three domains, but
every query carries billing + tech + product instructions in one context and
nothing keeps the domains apart. This test checks what works and measures the
overload that motivates the multi-agent parts.

  Stage 1 PREFLIGHT   imports and AWS credentials
  Stage 2 COVERAGE    the single agent answers billing, tech, product queries
  Stage 3 CONTEXT     it keeps the order number across turns
  Stage 4 OVERLOAD    one prompt mixes all 3 domains; no scope boundary
  Stage 5 CROSSOVER   a mixed query is answered in one undifferentiated reply
  Stage 6 SUMMARY

Usage (from module1-multi-agent/):  python test_concept/test_single_agent_concept.py
"""
from helpers import Suite, silent, has_aws_credentials, any_in, run


def main():
    s = Suite("Part 1 - Single Agent Limitations")

    s.banner(1, "PREFLIGHT")
    try:
        import part1_single_agent as p1
        from strands import Agent
        from strands.models import BedrockModel
        s.check("demo module imports", True)
    except Exception as e:
        s.check("demo module imports", False, str(e))
        return s.finish()
    if not s.check("AWS credentials found", has_aws_credentials()):
        return s.finish()

    def new_agent():
        return Agent(model=BedrockModel(model_id=p1.MODEL_ID), system_prompt=p1.SYSTEM_PROMPT)

    s.banner(2, "COVERAGE: one agent answers every domain")
    cases = [
        ("billing", "What is the refund window for a TechMart order?", ["30"]),
        ("tech", "My Hub's Wi-Fi keeps dropping. What should I check?", ["firmware", "channel"]),
        ("product", "Which TechMart laptop is cheapest and how much is it?", ["599", "air"]),
    ]
    for domain, q, words in cases:
        try:
            r = silent(new_agent(), q)
            s.info(f"[{domain}] {q}")
            s.check(f"{domain} query answered with domain facts", any_in(r, words), f"expects one of {words}")
            s.snippet(r, 2)
        except Exception as e:
            s.check(f"{domain} query answered", False, str(e))

    s.banner(3, "CONTEXT: memory inside one conversation")
    try:
        a = new_agent()
        silent(a, "Hi, my order number is TM-78432 and I was charged $9.99 after cancelling.")
        r = silent(a, "Which order number did I give you?")
        s.check("agent recalls order number TM-78432", "78432" in str(r))
        s.check("history grows in the single context", len(a.messages) >= 4, f"{len(a.messages)} messages")
    except Exception as e:
        s.check("multi-turn context", False, str(e))

    s.banner(4, "OVERLOAD: one prompt, three domains, no boundary")
    p = p1.SYSTEM_PROMPT
    for label, kw in [("billing", "BILLING:"), ("tech support", "TECHNICAL SUPPORT:"), ("product", "PRODUCT RECOMMENDATIONS:")]:
        s.check(f"prompt contains {label} instructions", kw in p)
    s.info(f"System prompt size: {len(p)} chars, paid on EVERY turn for ALL domains")
    s.check("agent has no tools or scope guard (nothing to route or isolate)",
            "outside my" not in p.lower())

    s.banner(5, "CROSSOVER: mixed query handled by the same generalist")
    q = "Refund order TM-1001, fix my Hub on firmware v2.1.3, and recommend a $700 laptop."
    s.info(q)
    try:
        r = silent(new_agent(), q)
        text = str(r)
        s.check("single reply covers all 3 domains at once",
                any_in(text, ["refund"]) and any_in(text, ["firmware"]) and any_in(text, ["pro 15", "laptop"]))
        s.snippet(text, 3)
        s.info("It works, but one context carries every domain: the problem Part 2 solves.")
    except Exception as e:
        s.check("mixed query answered", False, str(e))

    s.finish()


if __name__ == "__main__":
    run(main)
