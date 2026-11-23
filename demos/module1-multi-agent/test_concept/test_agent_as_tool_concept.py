"""
Concept test: Part 3 - Agent-as-Tool (MCP-style).

Concept: agents wrapped as @tool have a clear interface, are reusable by many
consumer agents, and consumers only get the tools they are given.

  Stage 1 PREFLIGHT   imports and AWS credentials
  Stage 2 CONTRACTS   tool names, descriptions and input schemas (no LLM)
  Stage 3 DIRECT      call each tool directly, no consumer agent
  Stage 4 REUSE       sales and support agents share the same tool objects
  Stage 5 CONSUMERS   each consumer calls the tools it needs, and only its own
  Stage 6 SUMMARY

Usage (from module1-multi-agent/):  python test_concept/test_agent_as_tool_concept.py
"""
from helpers import Suite, silent, has_aws_credentials, tools_called, any_in, run


def main():
    s = Suite("Part 3 - Agent-as-Tool")

    s.banner(1, "PREFLIGHT")
    try:
        import part3_agent_as_tool as p3
        s.check("demo module imports", True)
    except Exception as e:
        s.check("demo module imports", False, str(e))
        return s.finish()
    if not s.check("AWS credentials found", has_aws_credentials()):
        return s.finish()

    s.banner(2, "CONTRACTS: each tool exposes a clear interface")
    expected = {
        "product_lookup": {"product_name"},
        "compatibility_check": {"product_a", "product_b"},
        "order_status": {"order_id"},
    }
    for name, params in expected.items():
        t = getattr(p3, name)
        spec = t.tool_spec
        props = set(spec["inputSchema"]["json"]["properties"].keys())
        s.check(f"{name}: name, description, params {sorted(params)}",
                spec["name"] == name and bool(spec.get("description")) and props == params, f"found {sorted(props)}")

    s.banner(3, "DIRECT: tools work without any consumer agent")
    try:
        r = silent(p3.product_lookup, "TechMart Pro 15")
        s.check("product_lookup returns Pro 15 price", "799" in str(r)); s.snippet(r, 2)
        r = silent(p3.order_status, "TM-91001")
        s.check("order_status returns shipped order", any_in(r, ["shipped"])); s.snippet(r, 2)
        r = silent(p3.compatibility_check, "Motion Sensor", "TechMart Hub")
        s.check("compatibility_check: sensor works with Hub", any_in(r, ["compatible", "yes", "hub"])); s.snippet(r, 2)
    except Exception as e:
        s.check("direct tool calls", False, str(e))

    s.banner(4, "REUSE: same tool objects serve multiple agents")
    sales, support = p3.create_sales_agent(), p3.create_support_agent()
    sales_tools = set(sales.tool_names)
    support_tools = set(support.tool_names)
    s.check("sales agent tools == {product_lookup, compatibility_check}",
            sales_tools == {"product_lookup", "compatibility_check"}, str(sorted(sales_tools)))
    s.check("support agent tools include all three", support_tools == set(expected), str(sorted(support_tools)))
    s.check("shared tools reused by both agents", {"product_lookup", "compatibility_check"} <= sales_tools & support_tools)
    s.check("order_status is NOT exposed to sales agent", "order_status" not in sales_tools)

    s.banner(5, "CONSUMERS: agents invoke tools for the right job")
    try:
        q = "Will the TechMart Pro 15 work with the TechMart Hub?"
        s.info(f"Sales: {q}")
        r = silent(sales, q)
        called = tools_called(r)
        s.check("sales used compatibility_check or product_lookup",
                bool(called & {"compatibility_check", "product_lookup"}), str(sorted(called)))
        s.check("sales answer says compatible", any_in(r, ["compatible", "works", "yes"])); s.snippet(r, 2)

        q = "What is the status of order TM-91001 and what is in it?"
        s.info(f"Support: {q}")
        r = silent(support, q)
        called = tools_called(r)
        s.check("support used order_status", "order_status" in called, str(sorted(called)))
        s.check("support answer mentions Pro 15", any_in(r, ["pro 15"])); s.snippet(r, 2)
    except Exception as e:
        s.check("consumer agents call tools", False, str(e))

    s.finish()


if __name__ == "__main__":
    run(main)
