from typing import Any
from collections import OrderedDict
from strands import Agent, tool
import asyncio
from strands.agent.conversation_manager.null_conversation_manager import NullConversationManager
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

# Define a Streamable HTTP MCP Client
mcp_clients = []  # no external MCP servers: the tools below are self-contained

DEFAULT_SYSTEM_PROMPT = """
You are a customer service agent for TechMart, an electronics e-commerce company.
Use search_products to find products and prices, check_inventory to verify stock,
and get_refund_policy before answering any refund question. Never invent prices,
stock levels or policy terms: only state what the tools return. Be concise and helpful.
"""

# Define a collection of tools used by the model
tools = []
_INLINE_FUNCTION_NAMES = set()

CATALOG = {
    "TechMart Air": {"category": "laptop", "price": 599, "specs": "14in, i5, 8GB RAM, 256GB SSD, Wi-Fi 5", "stock": 45},
    "TechMart Pro 15": {"category": "laptop", "price": 799, "specs": "15.6in, i7, 16GB RAM, 512GB SSD, Wi-Fi 6", "stock": 23},
    "TechMart Titan": {"category": "laptop", "price": 1299, "specs": "16in, RTX 4060, 32GB RAM, 1TB SSD, Wi-Fi 6E", "stock": 12},
    "TechMart Hub": {"category": "smart home hub", "price": 149, "specs": "Wi-Fi 6, Bluetooth 5.0, Zigbee 3.0, max 50 devices", "stock": 3},
}


@tool
def search_products(query: str) -> str:
    """Search the TechMart catalog.

    Args:
        query: search term, for example "laptop", "hub" or a product name
    """
    words = [w for w in query.lower().replace("?", " ").split() if len(w) > 2]
    hits = [
        f"{name}: ${p['price']} ({p['category']}; {p['specs']})"
        for name, p in CATALOG.items()
        if any(w in f"{name} {p['category']} {p['specs']}".lower() for w in words)
    ]
    return "\n".join(hits) if hits else "No matching products."


@tool
def check_inventory(product_name: str) -> str:
    """Check how many units of a product are in stock.

    Args:
        product_name: exact or partial product name
    """
    for name, p in CATALOG.items():
        if product_name.lower() in name.lower():
            status = "Low stock" if p["stock"] < 5 else "In stock"
            return f"{name}: {status} ({p['stock']} units)"
    return f"{product_name}: not found in catalog"


@tool
def get_refund_policy() -> str:
    """Return the TechMart refund policy."""
    return (
        "Full refund within 30 days of delivery for unused items. 30-60 days: store credit only. "
        "Shipping fees are refundable only if the item was defective or the wrong item was sent."
    )


tools.extend([search_products, check_inventory, get_refund_policy])

# Add MCP client to tools if available
for mcp_client in mcp_clients:
    if mcp_client:
        tools.append(mcp_client)

def _make_conversation_manager():
    return NullConversationManager()

# Reuses one Agent per session_id so each session keeps its own in-process
# conversation history (best-effort; resets on cold start). The cache is bounded
# to 128 sessions with LRU eviction (least-recently-used is dropped and its
# history reset) so a single process serving many sessions cannot leak history
# between them or grow without limit. For durable history, attach a session manager.
def agent_factory():
    cache = OrderedDict()
    def get_or_create_agent(session_id):
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools,
            conversation_manager=_make_conversation_manager(),
            hooks=[
            ],
        )
        return cache[session_id]
    return get_or_create_agent
get_or_create_agent = agent_factory()


def _extract_prompt(payload: dict):
    """Accept harness-style messages[], tool_results[], or plain prompt string payloads."""
    if "messages" in payload:
        return payload["messages"]
    if "tool_results" in payload:
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in payload["tool_results"]]}]
    return payload.get("prompt", "")


def _has_inline_function_call(messages) -> bool:
    """Return True if messages contains an assistant toolUse for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES or not isinstance(messages, list):
        return False
    for msg in messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("toolUse", {}).get("name") in _INLINE_FUNCTION_NAMES:
                    return True
    return False


def _is_inline_function_call(event: dict) -> bool:
    """Check if a contentBlockStart event is for an inline function tool."""
    if not _INLINE_FUNCTION_NAMES:
        return False
    cbs = event.get("contentBlockStart", {})
    start = cbs.get("start", {})
    tool_use = start.get("toolUse") if isinstance(start, dict) else None
    return tool_use is not None and tool_use.get("name") in _INLINE_FUNCTION_NAMES



@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")


    session_id = getattr(context, 'session_id', 'default-session')
    agent = get_or_create_agent(session_id)

    prompt = _extract_prompt(payload)


    async for event in agent.stream_async(
        prompt,
    ):
        if not isinstance(event, dict) or "event" not in event:
            continue
        cbs = event["event"].get("contentBlockStart")
        if cbs is not None and not cbs.get("start"):
            continue
        yield event


if __name__ == "__main__":
    app.run()
