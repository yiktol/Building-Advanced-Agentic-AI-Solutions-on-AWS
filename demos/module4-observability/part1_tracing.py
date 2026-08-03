"""
Module 4 - Part 1: Instrumented Agent with OpenTelemetry Tracing

Demonstrates session/trace/span hierarchy by instrumenting an agent
and writing structured span data to CloudWatch Logs.

Shows:
- Session-level: Full conversation context
- Trace-level: Individual request-response cycles
- Span-level: Tool calls, LLM invocations, processing steps
"""

import os
import json
import time
import uuid
import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
SPANS_LOG_GROUP = os.environ.get("SPANS_LOG_GROUP", "/m4-demo/agent-spans")

logs_client = boto3.client("logs", region_name=REGION)

# Tracing context
_session_id = f"session-{uuid.uuid4().hex[:12]}"
_trace_count = 0
_spans = []


def generate_trace_id() -> str:
    return uuid.uuid4().hex[:32]


def generate_span_id() -> str:
    return uuid.uuid4().hex[:16]


def emit_span(span_data: dict):
    """Write a span to CloudWatch Logs."""
    _spans.append(span_data)

    try:
        stream_name = f"traces-{_session_id}"
        try:
            logs_client.create_log_stream(
                logGroupName=SPANS_LOG_GROUP,
                logStreamName=stream_name,
            )
        except logs_client.exceptions.ResourceAlreadyExistsException:
            pass

        logs_client.put_log_events(
            logGroupName=SPANS_LOG_GROUP,
            logStreamName=stream_name,
            logEvents=[{
                "timestamp": int(time.time() * 1000),
                "message": json.dumps(span_data),
            }],
        )
    except Exception as e:
        pass  # Don't break the demo if logging fails


class TracingContext:
    """Manages trace/span hierarchy for a single request."""

    def __init__(self):
        global _trace_count
        _trace_count += 1
        self.trace_id = generate_trace_id()
        self.trace_number = _trace_count
        self.root_span_id = generate_span_id()
        self.start_time = time.time()
        self.child_spans = []

    def start_span(self, operation: str, attributes: dict = None) -> dict:
        span = {
            "session_id": _session_id,
            "trace_id": self.trace_id,
            "span_id": generate_span_id(),
            "parent_span_id": self.root_span_id,
            "operation": operation,
            "start_time": datetime.utcnow().isoformat() + "Z",
            "attributes": attributes or {},
        }
        self.child_spans.append(span)
        return span

    def end_span(self, span: dict, status: str = "OK", result: dict = None):
        span["end_time"] = datetime.utcnow().isoformat() + "Z"
        span["status"] = status
        span["duration_ms"] = int((time.time() - self.start_time) * 1000)
        if result:
            span["result"] = result
        emit_span(span)

    def end_trace(self, status: str = "OK"):
        root_span = {
            "session_id": _session_id,
            "trace_id": self.trace_id,
            "span_id": self.root_span_id,
            "parent_span_id": None,
            "operation": "InvokeAgentRuntime",
            "start_time": datetime.utcfromtimestamp(self.start_time).isoformat() + "Z",
            "end_time": datetime.utcnow().isoformat() + "Z",
            "duration_ms": int((time.time() - self.start_time) * 1000),
            "status": status,
            "child_span_count": len(self.child_spans),
            "trace_number": self.trace_number,
        }
        emit_span(root_span)


# Current tracing context
_current_trace: TracingContext = None


# =============================================================================
# INSTRUMENTED TOOLS
# =============================================================================

@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant information.

    Args:
        query: Search query
    """
    global _current_trace
    span = _current_trace.start_span("KnowledgeBaseSearch", {"query": query})

    # Simulate KB search
    time.sleep(0.3)
    results = {
        "wifi": "TechMart Hub firmware v2.1.x has known Wi-Fi dropout bug. Update to v3.0.1.",
        "refund": "Refund policy: 30 days for full refund, 60 days for store credit.",
        "laptop": "TechMart Pro 15: $799, i7, 16GB RAM. TechMart Air: $599, i5, 8GB RAM.",
    }

    # Find best match
    result = "No relevant results found."
    for key, value in results.items():
        if key in query.lower():
            result = value
            break

    _current_trace.end_span(span, "OK", {"results_count": 1, "chars": len(result)})
    print(f"    📍 [Span] KnowledgeBaseSearch: {len(result)} chars")
    return result


@tool
def get_customer_info(customer_id: str) -> str:
    """Look up customer information.

    Args:
        customer_id: Customer ID
    """
    global _current_trace
    span = _current_trace.start_span("CustomerLookup", {"customer_id": customer_id})

    # Simulate DB lookup
    time.sleep(0.2)
    data = f'{{"id":"{customer_id}","name":"Sarah Chen","tier":"premium","orders":47}}'

    _current_trace.end_span(span, "OK", {"found": True})
    print(f"    📍 [Span] CustomerLookup: {customer_id}")
    return data


@tool
def process_action(action_type: str, details: str) -> str:
    """Process a customer service action.

    Args:
        action_type: Type of action (refund, update, escalate)
        details: Action details
    """
    global _current_trace
    span = _current_trace.start_span("ProcessAction", {"action_type": action_type})

    time.sleep(0.4)
    result = f"Action '{action_type}' processed: {details}"

    _current_trace.end_span(span, "OK", {"action_type": action_type})
    print(f"    📍 [Span] ProcessAction: {action_type}")
    return result


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT = """You are a customer service agent for TechMart.
Use tools to look up information and process actions.
Always search the knowledge base before answering technical questions.
"""


def run_demo():
    global _current_trace

    print("=" * 70)
    print("PART 1: Instrumented Agent with OpenTelemetry Tracing")
    print("=" * 70)
    print()
    print(f"  Session ID: {_session_id}")
    print(f"  Log Group:  {SPANS_LOG_GROUP}")
    print()
    print("  Each request creates a TRACE with child SPANS:")
    print("  └─ Trace (InvokeAgentRuntime)")
    print("     ├─ Span (KnowledgeBaseSearch)")
    print("     ├─ Span (CustomerLookup)")
    print("     └─ Span (ProcessAction)")
    print()
    print("  Type 'traces' to see all recorded spans.")
    print("  Type 'quit' to end.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[search_knowledge_base, get_customer_info, process_action],
    )

    session_start = time.time()

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "traces":
            show_traces()
            continue

        # Start a new trace for this request
        _current_trace = TracingContext()
        trace_id = _current_trace.trace_id

        print(f"\n    🔵 Trace #{_current_trace.trace_number} started: {trace_id[:16]}...")
        print()

        start = time.time()
        response = agent(user_input)
        elapsed = time.time() - start

        # End the trace
        _current_trace.end_trace("OK")

        print(f"\n  Agent: {response}")
        print(f"\n    🔵 Trace #{_current_trace.trace_number} completed: {elapsed:.1f}s, {len(_current_trace.child_spans)} spans")

    # Session summary
    session_duration = time.time() - session_start
    print(f"\n{'═' * 70}")
    print(f"  SESSION SUMMARY")
    print(f"{'═' * 70}")
    print(f"  Session ID: {_session_id}")
    print(f"  Duration: {session_duration:.1f}s")
    print(f"  Traces: {_trace_count}")
    print(f"  Total spans: {len(_spans)}")
    print(f"  Log Group: {SPANS_LOG_GROUP}")
    print()
    print("  Observability hierarchy:")
    print(f"  └─ Session ({_session_id})")
    for span in _spans:
        if span.get("parent_span_id") is None:
            tn = span.get("trace_number", "?")
            dur = span.get("duration_ms", 0)
            children = span.get("child_span_count", 0)
            print(f"     ├─ Trace #{tn} ({dur}ms, {children} spans)")
    print()


def show_traces():
    """Display recorded traces and spans."""
    print(f"\n  📋 RECORDED SPANS ({len(_spans)} total)")
    print(f"  {'─' * 60}")

    # Group by trace
    traces = {}
    for span in _spans:
        tid = span.get("trace_id", "unknown")
        if tid not in traces:
            traces[tid] = []
        traces[tid].append(span)

    for tid, spans in traces.items():
        root = next((s for s in spans if s.get("parent_span_id") is None), None)
        if root:
            dur = root.get("duration_ms", 0)
            tn = root.get("trace_number", "?")
            print(f"\n  Trace #{tn}: {tid[:16]}... ({dur}ms)")
            for s in spans:
                if s.get("parent_span_id") is not None:
                    op = s.get("operation", "?")
                    status = s.get("status", "?")
                    attrs = s.get("attributes", {})
                    print(f"    └─ {op}: {status} {attrs}")
    print()


if __name__ == "__main__":
    run_demo()
