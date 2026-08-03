"""
Module 2 - Part 4: Context Isolation (Multi-Agent Boundaries)

Demonstrates how splitting work across specialized agents keeps each
agent's context lean and focused, vs a single agent accumulating everything.

Shows:
- Single agent: accumulates research + analysis + writing context
- Multi-agent: each specialist operates with only relevant context
- Token usage comparison between approaches
"""

import time
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# SPECIALIZED AGENTS (isolated context)
# =============================================================================

def create_researcher() -> Agent:
    """Research agent — only has research-related context."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a market research specialist.

Your role: Gather and synthesize market data, trends, and statistics.

Focus areas:
- Market size and growth rates
- Key players and market share
- Technology trends and adoption curves
- Regional market dynamics
- Regulatory landscape

Output format: Structured research findings with data points, sources referenced
as [Industry Report 2025], [Market Analysis], etc. Keep findings factual and quantitative.
Do NOT provide analysis or recommendations — just research data.""",
    )


def create_analyst() -> Agent:
    """Analysis agent — receives research output, produces analysis."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a financial and strategic analyst.

Your role: Take research data and produce analytical insights.

Focus areas:
- Financial viability assessment (ROI, NPV, payback period)
- Risk-reward analysis
- Competitive positioning
- SWOT analysis
- Scenario modeling (best/base/worst case)

Input: You receive research findings from a research specialist.
Output: Structured analysis with quantitative conclusions and confidence levels.
Do NOT write prose summaries — provide analytical frameworks and numbers.""",
    )


def create_writer() -> Agent:
    """Writing agent — receives analysis, produces executive summary."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are an executive communications specialist.

Your role: Transform analysis into clear, compelling executive summaries.

Writing style:
- Lead with the conclusion/recommendation
- Support with 2-3 key data points
- Use plain business language (no jargon)
- Keep it concise: 3 paragraphs maximum
- End with a clear call to action

Input: You receive analysis from a financial analyst.
Output: A polished 3-paragraph executive summary suitable for C-suite presentation.""",
    )


def create_single_agent() -> Agent:
    """Single agent that does everything — context accumulates."""
    return Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt="""You are a versatile business consultant who handles research,
analysis, AND executive writing.

When asked to research: Provide market data, trends, statistics.
When asked to analyze: Provide financial viability, ROI, risk assessment.
When asked to write: Produce a 3-paragraph executive summary.

You handle ALL stages of a project from research through final deliverable.""",
    )


# =============================================================================
# ORCHESTRATOR
# =============================================================================

def run_isolated_pipeline(task: str) -> dict:
    """Run task through isolated specialist agents."""
    results = {"timings": {}, "responses": {}}

    # Step 1: Research
    print(f"    🔬 Researcher analyzing...")
    researcher = create_researcher()
    start = time.time()
    research_output = researcher(f"Research the following topic thoroughly: {task}")
    results["timings"]["research"] = time.time() - start
    results["responses"]["research"] = str(research_output)
    print(f"       Done ({results['timings']['research']:.1f}s)")

    # Step 2: Analysis (receives only research output, not original task context)
    print(f"    📊 Analyst processing research...")
    analyst = create_analyst()
    start = time.time()
    analysis_output = analyst(
        f"Analyze the following research findings and provide strategic/financial analysis:\n\n"
        f"{results['responses']['research']}"
    )
    results["timings"]["analysis"] = time.time() - start
    results["responses"]["analysis"] = str(analysis_output)
    print(f"       Done ({results['timings']['analysis']:.1f}s)")

    # Step 3: Writing (receives only analysis, not research or original task)
    print(f"    ✍️  Writer creating executive summary...")
    writer = create_writer()
    start = time.time()
    writing_output = writer(
        f"Write a 3-paragraph executive summary based on this analysis:\n\n"
        f"{results['responses']['analysis']}"
    )
    results["timings"]["writing"] = time.time() - start
    results["responses"]["writing"] = str(writing_output)
    print(f"       Done ({results['timings']['writing']:.1f}s)")

    return results


def run_single_pipeline(task: str) -> dict:
    """Run all stages through a single agent (context accumulates)."""
    results = {"timings": {}, "responses": {}}

    agent = create_single_agent()

    # Step 1: Research
    print(f"    🔬 Researching...")
    start = time.time()
    research_output = agent(f"Research the following topic thoroughly with market data and statistics: {task}")
    results["timings"]["research"] = time.time() - start
    results["responses"]["research"] = str(research_output)
    print(f"       Done ({results['timings']['research']:.1f}s)")

    # Step 2: Analysis (same agent, context includes research)
    print(f"    📊 Analyzing (same agent, growing context)...")
    start = time.time()
    analysis_output = agent("Now analyze the research you just provided. Give financial viability, ROI estimates, and risk assessment.")
    results["timings"]["analysis"] = time.time() - start
    results["responses"]["analysis"] = str(analysis_output)
    print(f"       Done ({results['timings']['analysis']:.1f}s)")

    # Step 3: Writing (same agent, context includes research + analysis)
    print(f"    ✍️  Writing summary (same agent, full context)...")
    start = time.time()
    writing_output = agent("Now write a 3-paragraph executive summary combining your research and analysis. Be concise and lead with the recommendation.")
    results["timings"]["writing"] = time.time() - start
    results["responses"]["writing"] = str(writing_output)
    print(f"       Done ({results['timings']['writing']:.1f}s)")

    return results


# =============================================================================
# DEMO
# =============================================================================

def run_demo():
    print("=" * 70)
    print("PART 4: Context Isolation (Multi-Agent Boundaries)")
    print("=" * 70)
    print()
    print("Compare two approaches to a complex task:")
    print("  [A] Single agent: accumulates ALL context across stages")
    print("  [B] Isolated agents: each specialist gets only relevant input")
    print()

    task = input("  Describe a research task (or press Enter for default): ").strip()
    if not task:
        task = "Evaluate the viability of building a 50MW solar farm in Vietnam, considering market trends, financial returns, and regulatory environment in Southeast Asia for 2025-2027."

    print(f"\n  Task: {task}")
    print()

    # --- Approach A: Single Agent ---
    print(f"{'━' * 70}")
    print("  APPROACH A: Single Agent (context accumulates)")
    print(f"{'━' * 70}\n")

    start_a = time.time()
    results_single = run_single_pipeline(task)
    total_a = time.time() - start_a

    print(f"\n  Total time: {total_a:.1f}s")
    print(f"  Context at writing stage: includes research + analysis + all prior exchanges")

    # --- Approach B: Isolated Agents ---
    print(f"\n{'━' * 70}")
    print("  APPROACH B: Isolated Agents (each has clean context)")
    print(f"{'━' * 70}\n")

    start_b = time.time()
    results_isolated = run_isolated_pipeline(task)
    total_b = time.time() - start_b

    print(f"\n  Total time: {total_b:.1f}s")
    print(f"  Context at writing stage: only receives analysis output (not research)")

    # --- Comparison ---
    print(f"\n{'═' * 70}")
    print("  COMPARISON")
    print(f"{'═' * 70}\n")

    print(f"  {'Stage':<12} {'Single Agent':>14} {'Isolated':>14}")
    print(f"  {'─' * 42}")
    for stage in ["research", "analysis", "writing"]:
        t_single = results_single["timings"][stage]
        t_iso = results_isolated["timings"][stage]
        print(f"  {stage:<12} {t_single:>12.1f}s {t_iso:>12.1f}s")
    print(f"  {'─' * 42}")
    print(f"  {'TOTAL':<12} {total_a:>12.1f}s {total_b:>12.1f}s")

    print(f"\n  Context at each stage:")
    print(f"  {'Stage':<12} {'Single Agent':<30} {'Isolated':<30}")
    print(f"  {'─' * 72}")
    print(f"  {'Research':<12} {'task prompt':<30} {'task prompt':<30}")
    print(f"  {'Analysis':<12} {'task + research output':<30} {'research output only':<30}")
    print(f"  {'Writing':<12} {'task + research + analysis':<30} {'analysis output only':<30}")

    # Show final outputs
    print(f"\n{'━' * 70}")
    print("  FINAL EXECUTIVE SUMMARY (from isolated pipeline)")
    print(f"{'━' * 70}\n")
    print(f"  {results_isolated['responses']['writing']}")

    print(f"\n{'─' * 70}")
    print("  Key Insight: Each isolated agent works with ONLY what it needs.")
    print("  The writer never sees raw research data — just structured analysis.")
    print("  This reduces token usage and keeps each agent focused.")
    print(f"{'─' * 70}\n")


if __name__ == "__main__":
    run_demo()
