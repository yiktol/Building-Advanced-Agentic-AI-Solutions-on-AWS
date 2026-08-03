"""
Module 2 - Part 2: Prompt Caching with Amazon Bedrock

Demonstrates how caching static context (system prompt, tool definitions)
reduces latency and cost on subsequent calls.

Shows:
- First call (cold): full processing of system prompt
- Subsequent calls (cached): faster response from cached prefix
- Cache configuration with Strands SDK
"""

import time
from strands import Agent, tool
from strands.models import BedrockModel
from strands.types.content import ContentBlock

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# Large system prompt to make caching benefits visible
SYSTEM_PROMPT_CONTENT = """You are an advanced financial analyst AI assistant for GlobalTech Corp.

COMPANY CONTEXT:
GlobalTech Corp is a Fortune 500 technology conglomerate with operations in:
- Cloud Computing (35% revenue): AWS-based SaaS products, $4.2B ARR
- AI/ML Services (28% revenue): Enterprise ML platforms, $3.4B ARR
- IoT Solutions (22% revenue): Industrial IoT, smart city platforms, $2.7B ARR
- Cybersecurity (15% revenue): Zero-trust architecture products, $1.8B ARR

FINANCIAL DATA (FY2025):
- Total Revenue: $12.1B (+18% YoY)
- Gross Margin: 72.3%
- Operating Margin: 28.1%
- Net Income: $2.4B
- Free Cash Flow: $3.1B
- R&D Spend: $2.8B (23% of revenue)
- Employee Count: 45,000 across 28 countries
- Market Cap: $89B (P/E ratio: 37x)

QUARTERLY BREAKDOWN:
Q1: $2.8B (seasonally low, enterprise budget cycles)
Q2: $3.0B (mid-year acceleration)
Q3: $3.1B (strong cloud growth)
Q4: $3.2B (enterprise year-end spending)

COMPETITIVE LANDSCAPE:
- Direct competitors: TechNova ($8.2B rev), CloudFirst ($6.7B rev), SecureAI ($4.1B rev)
- Market position: #1 in integrated cloud+AI, #2 in IoT, #3 in cybersecurity
- Key differentiator: End-to-end platform integration across all four segments

STRATEGIC PRIORITIES (2025-2027):
1. AI-first transformation: Embed AI across all product lines
2. Platform consolidation: Single pane of glass for enterprise customers
3. Geographic expansion: APAC revenue target 30% (currently 18%)
4. M&A pipeline: 3-5 acquisitions targeted in AI/cybersecurity space
5. Sustainability: Carbon neutral operations by 2027

RISK FACTORS:
- Regulatory: EU AI Act compliance, US data privacy legislation
- Competition: Hyperscaler AI offerings (AWS, Azure, GCP)
- Talent: AI/ML engineer retention in competitive market
- Macro: Enterprise IT budget sensitivity to economic cycles
- Geopolitical: China market access restrictions

You provide detailed financial analysis, strategic recommendations, and
market insights. Always cite specific numbers from the context above.
"""


@tool
def get_stock_price(ticker: str) -> str:
    """Get the current stock price for a ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., "GTCH")
    """
    # Mock data
    prices = {
        "GTCH": "$198.42 (+1.3% today, 52wk range: $142-$215)",
        "TNVA": "$87.55 (-0.4% today)",
        "CLDF": "$124.30 (+2.1% today)",
        "SCAI": "$56.78 (+0.8% today)",
    }
    return prices.get(ticker.upper(), f"Ticker {ticker} not found.")


@tool
def get_quarterly_metrics(quarter: str) -> str:
    """Get detailed quarterly metrics for GlobalTech.

    Args:
        quarter: Quarter to look up (e.g., "Q1-2025", "Q4-2024")
    """
    metrics = {
        "Q1-2025": "Revenue: $2.8B, Cloud: $980M, AI: $784M, IoT: $616M, Sec: $420M. New customers: 342. Churn: 2.1%",
        "Q2-2025": "Revenue: $3.0B, Cloud: $1.05B, AI: $840M, IoT: $660M, Sec: $450M. New customers: 411. Churn: 1.8%",
        "Q3-2025": "Revenue: $3.1B, Cloud: $1.09B, AI: $868M, IoT: $682M, Sec: $465M. New customers: 389. Churn: 1.9%",
        "Q4-2025": "Revenue: $3.2B, Cloud: $1.12B, AI: $896M, IoT: $704M, Sec: $480M. New customers: 467. Churn: 1.7%",
    }
    return metrics.get(quarter, f"No data for {quarter}.")


@tool
def get_competitor_analysis(competitor: str) -> str:
    """Get competitive analysis for a specific competitor.

    Args:
        competitor: Competitor name (e.g., "TechNova", "CloudFirst")
    """
    analysis = {
        "TechNova": "Revenue $8.2B, growth 12%, strong in pure-play AI. Weakness: no IoT. Threat: expanding into enterprise cloud.",
        "CloudFirst": "Revenue $6.7B, growth 22%, cloud-native focus. Weakness: limited AI capabilities. Threat: aggressive pricing.",
        "SecureAI": "Revenue $4.1B, growth 31%, cybersecurity leader. Weakness: narrow product line. Threat: bundling security with AI.",
    }
    return analysis.get(competitor, f"No data for {competitor}.")


def run_demo():
    print("=" * 70)
    print("PART 2: Prompt Caching with Amazon Bedrock")
    print("=" * 70)
    print()
    print("Comparing latency with and without prompt caching.")
    print("The system prompt is ~800 tokens of financial context.")
    print()

    test_queries = [
        "What is GlobalTech's revenue breakdown by segment?",
        "Compare our growth rate with TechNova.",
        "What's our Q3-2025 performance?",
        "What are the top 3 risks for next year?",
        "Recommend an acquisition target based on our strategic priorities.",
    ]

    # --- Run WITHOUT caching ---
    print(f"{'─' * 70}")
    print("  🚫 WITHOUT CACHING (baseline)")
    print(f"{'─' * 70}\n")

    model_no_cache = BedrockModel(model_id=MODEL_ID)
    agent_no_cache = Agent(
        model=model_no_cache,
        system_prompt=SYSTEM_PROMPT_CONTENT,
        tools=[get_stock_price, get_quarterly_metrics, get_competitor_analysis],
    )

    no_cache_times = []
    for i, query in enumerate(test_queries, 1):
        print(f"  Query {i}: {query}")
        start = time.time()
        response = agent_no_cache(query)
        elapsed = time.time() - start
        no_cache_times.append(elapsed)
        print(f"  ⏱  {elapsed:.2f}s")
        print(f"  Response: {str(response)[:100]}...")
        print()

    # --- Run WITH caching ---
    print(f"{'─' * 70}")
    print("  ✅ WITH CACHING (cache_tools + system prompt cache point)")
    print(f"{'─' * 70}\n")

    # Configure caching on the model
    model_cached = BedrockModel(
        model_id=MODEL_ID,
        cache_tools="default",  # Cache tool definitions
    )

    # System prompt with cache point
    system_with_cache = [
        {"text": SYSTEM_PROMPT_CONTENT},
        {"cachePoint": {"type": "default"}},  # Cache checkpoint
    ]

    agent_cached = Agent(
        model=model_cached,
        system_prompt=system_with_cache,
        tools=[get_stock_price, get_quarterly_metrics, get_competitor_analysis],
    )

    cache_times = []
    for i, query in enumerate(test_queries, 1):
        print(f"  Query {i}: {query}")
        start = time.time()
        response = agent_cached(query)
        elapsed = time.time() - start
        cache_times.append(elapsed)
        cache_label = "(cold)" if i == 1 else "(cached)"
        print(f"  ⏱  {elapsed:.2f}s {cache_label}")
        print(f"  Response: {str(response)[:100]}...")
        print()

    # --- Comparison ---
    print(f"{'═' * 70}")
    print("  COMPARISON: Caching Impact")
    print(f"{'═' * 70}\n")

    print(f"  {'Query':<8} {'No Cache':>10} {'Cached':>10} {'Savings':>10}")
    print(f"  {'─' * 40}")
    for i in range(len(test_queries)):
        nc = no_cache_times[i]
        c = cache_times[i]
        savings = ((nc - c) / nc * 100) if nc > c else 0
        print(f"  {i+1:<8} {nc:>9.2f}s {c:>9.2f}s {savings:>9.1f}%")

    avg_nc = sum(no_cache_times) / len(no_cache_times)
    avg_c = sum(cache_times) / len(cache_times)
    # Skip first cached call (cold start) for cached average
    avg_c_warm = sum(cache_times[1:]) / len(cache_times[1:]) if len(cache_times) > 1 else avg_c

    print(f"\n  Average (all):     {avg_nc:.2f}s → {avg_c:.2f}s")
    print(f"  Average (warm):    {avg_nc:.2f}s → {avg_c_warm:.2f}s")
    print()
    print("  Note: Caching benefits are most visible on:")
    print("  - Large system prompts (500+ tokens)")
    print("  - Many tool definitions")
    print("  - Reference documents attached to messages")
    print("  - Repeated calls within the cache TTL window")
    print()

    # Interactive follow-up
    print(f"{'─' * 70}")
    print("  Continue chatting with the cached agent. Type 'quit' to end.")
    print(f"{'─' * 70}")

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        start = time.time()
        response = agent_cached(user_input)
        elapsed = time.time() - start
        print(f"\n  Agent: {response}")
        print(f"  ⏱  {elapsed:.2f}s (cached)")

    print()


if __name__ == "__main__":
    run_demo()
