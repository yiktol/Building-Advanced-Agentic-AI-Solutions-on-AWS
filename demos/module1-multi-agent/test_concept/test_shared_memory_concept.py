"""
Concept test: Part 4 - Shared Memory Across Agents.

Concept: agents hand work off through a shared store (memory_id) with their
own actor_id, without copying each other's context into their prompts.

  Stage 1 PREFLIGHT   imports and AWS credentials
  Stage 2 STORE       SharedMemoryStore semantics (no LLM)
  Stage 3 HANDOFF     diagnostic -> resolution -> follow-up via memory
  Stage 4 IDENTITY    each agent wrote under its own actor_id
  Stage 5 ISOLATION   later agents got the diagnosis from memory, not the prompt
  Stage 6 SUMMARY

Usage (from module1-multi-agent/):  python test_concept/test_shared_memory_concept.py
"""
from helpers import Suite, silent, has_aws_credentials, tools_called, any_in, run


def main():
    s = Suite("Part 4 - Shared Memory Across Agents")

    s.banner(1, "PREFLIGHT")
    try:
        import part4_shared_memory as p4
        s.check("demo module imports", True)
    except Exception as e:
        s.check("demo module imports", False, str(e))
        return s.finish()
    if not s.check("AWS credentials found", has_aws_credentials()):
        return s.finish()

    s.banner(2, "STORE: memory semantics (deterministic)")
    st = p4.SharedMemoryStore("m-1", "s-1")
    s.check("empty store summary", st.summary() == "No shared memories yet.")
    st.write("a", {"observation": "x"}, "diagnosis")
    st.write("b", {"observation": "y"}, "action_taken")
    st.write("a", {"observation": "z"}, "observation")
    s.check("read_all returns 3 records", len(st.read_all()) == 3)
    s.check("read_by_actor('a') returns 2", len(st.read_by_actor("a")) == 2)
    s.check("read_by_type('diagnosis') returns 1", len(st.read_by_type("diagnosis")) == 1)
    s.check("all records share memory_id and session_id",
            {r["memory_id"] for r in st.read_all()} == {"m-1"} and {r["session_id"] for r in st.read_all()} == {"s-1"})

    s.banner(3, "HANDOFF: three agents collaborate through memory")
    p4.shared_memory.records.clear()
    issue = "My TechMart Hub keeps dropping Wi-Fi. The firmware says v2.1.3."
    s.info(f"Customer issue: {issue}")
    try:
        diag, res, fup = p4.create_diagnostic_agent(), p4.create_resolution_agent(), p4.create_followup_agent()
        r1 = silent(diag, f"Customer reports: {issue}\n\nDiagnose the root cause(s). Save your findings to shared memory.")
        n1 = len(p4.shared_memory.records)
        s.check("diagnostic agent wrote to memory", n1 >= 1, f"{n1} record(s)")
        s.check("diagnosis names the firmware bug", any_in(r1, ["2.1", "firmware"])); s.snippet(r1, 2)

        r2 = silent(res, "A customer needs help. Check shared memory for the diagnosis and provide "
                         "step-by-step resolution. Save your resolution plan to shared memory.")
        s.check("resolution agent read shared memory", "read_shared_memory" in tools_called(r2), str(sorted(tools_called(r2))))
        s.check("resolution wrote to memory", len(p4.shared_memory.records) > n1)
        s.check("resolution is the firmware update", any_in(r2, ["firmware", "update", "3.0.1"])); s.snippet(r2, 2)

        n2 = len(p4.shared_memory.records)
        r3 = silent(fup, "Review shared memory for the complete case history. Provide a summary for the "
                         "customer and suggest preventive measures. Save your summary to shared memory.")
        s.check("follow-up agent read shared memory", "read_shared_memory" in tools_called(r3))
        s.check("follow-up wrote to memory", len(p4.shared_memory.records) > n2)
        s.check("follow-up summary reflects the case", any_in(r3, ["firmware", "wi-fi"])); s.snippet(r3, 2)
    except Exception as e:
        s.check("handoff workflow", False, str(e))
        return s.finish()

    s.banner(4, "IDENTITY: one memory_id, distinct actor_id per agent")
    actors = {r["actor_id"] for r in p4.shared_memory.records}
    s.info(f"actors seen: {sorted(actors)}")
    s.check("at least 3 distinct actors wrote", len(actors) >= 3)
    s.check("every record uses the same memory_id",
            {r["memory_id"] for r in p4.shared_memory.records} == {p4.shared_memory.memory_id})
    for a in ("diagnostic-agent", "resolution-agent", "followup-agent"):
        s.check(f"records exist for actor '{a}'", len(p4.shared_memory.read_by_actor(a)) >= 1)

    s.banner(5, "ISOLATION: context passed through memory, not the prompt")
    first_user_msg = str(res.messages[0]["content"])
    s.check("resolution agent's prompt never contained the customer issue", "v2.1.3" not in first_user_msg)
    s.check("yet its answer used the diagnosis (came from memory)", any_in(r2, ["firmware", "update"]))

    s.finish()


if __name__ == "__main__":
    run(main)
