"""
Module 4 - Part 3: Loop Detection and Proactive Monitoring

Demonstrates detection and prevention of agent loops — repeated tool calls,
excessive session duration, and runaway token consumption.

Shows:
- Tool call pattern tracking
- Circuit breaker activation when loops detected
- Real CloudWatch alarm triggers
- Automatic session termination
"""

import os
import time
import json
import uuid
import boto3
from datetime import datetime
from strands import Agent, tool
from strands.models import BedrockModel

# --- Configuration ---
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")
METRICS_NAMESPACE = os.environ.get("METRICS_NAMESPACE", "m4-demo/AgentMetrics")
LOOP_LOG_GROUP = os.environ.get("LOOP_LOG_GROUP", "/m4-demo/loop-detection")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)
logs_client = boto3.client("logs", region_name=REGION)

# Session tracking
_session_id = f"loop-test-{uuid.uuid4().hex[:8]}"
_session_start = time.time()

# Loop detection state
_tool_call_history = []  # (timestamp, tool_name)
_circuit_breaker_open = False
_max_tool_calls_per_minute = 15
_max_consecutive_same_tool = 5
_max_session_duration_seconds = 300  # 5 minutes


class LoopDetector:
    """Detects agent loops by monitoring tool call patterns."""

    def __init__(self):
        self.consecutive_same_tool = 0
        self.last_tool_name = None
        self.total_calls = 0
        self.alerts_fired = []

    def record_call(self, tool_name: str) -> dict:
        """Record a tool call and check for loop patterns."""
        global _circuit_breaker_open

        self.total_calls += 1
        now = time.time()
        _tool_call_history.append((now, tool_name))

        # Check 1: Consecutive same tool
        if tool_name == self.last_tool_name:
            self.consecutive_same_tool += 1
        else:
            self.consecutive_same_tool = 1
        self.last_tool_name = tool_name

        result = {"loop_detected": False, "reason": None}

        # Trigger: Same tool called too many times in a row
        if self.consecutive_same_tool >= _max_consecutive_same_tool:
            result = {
                "loop_detected": True,
                "reason": f"Same tool '{tool_name}' called {self.consecutive_same_tool} times consecutively",
                "severity": "HIGH",
            }
            self._fire_alert(result)
            _circuit_breaker_open = True

        # Trigger: Too many tool calls in last 60 seconds
        recent_calls = [(t, n) for t, n in _tool_call_history if now - t < 60]
        if len(recent_calls) > _max_tool_calls_per_minute:
            result = {
                "loop_detected": True,
                "reason": f"{len(recent_calls)} tool calls in last 60s (limit: {_max_tool_calls_per_minute})",
                "severity": "HIGH",
            }
            self._fire_alert(result)
            _circuit_breaker_open = True

        # Trigger: Session too long
        session_duration = now - _session_start
        if session_duration > _max_session_duration_seconds:
            result = {
                "loop_detected": True,
                "reason": f"Session duration {session_duration:.0f}s exceeds {_max_session_duration_seconds}s limit",
                "severity": "MEDIUM",
            }
            self._fire_alert(result)

        return result

    def _fire_alert(self, alert_data: dict):
        """Log alert and publish metric."""
        self.alerts_fired.append({**alert_data, "timestamp": datetime.utcnow().isoformat()})

        # Publish to CloudWatch
        try:
            cloudwatch.put_metric_data(
                Namespace=METRICS_NAMESPACE,
                MetricData=[{
                    "MetricName": "LoopDetected",
                    "Value": 1,
                    "Unit": "Count",
                    "Timestamp": datetime.utcnow(),
                }],
            )

            # Also publish high tool invocation count to trigger alarm
            cloudwatch.put_metric_data(
                Namespace=METRICS_NAMESPACE,
                MetricData=[{
                    "MetricName": "ToolInvocationCount",
                    "Value": self.total_calls,
                    "Unit": "Count",
                    "Timestamp": datetime.utcnow(),
                }],
            )
        except Exception:
            pass

        # Log to CloudWatch Logs
        try:
            stream_name = f"alerts-{_session_id}"
            try:
                logs_client.create_log_stream(
                    logGroupName=LOOP_LOG_GROUP,
                    logStreamName=stream_name,
                )
            except logs_client.exceptions.ResourceAlreadyExistsException:
                pass

            logs_client.put_log_events(
                logGroupName=LOOP_LOG_GROUP,
                logStreamName=stream_name,
                logEvents=[{
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps({
                        "event": "LOOP_DETECTED",
                        "session_id": _session_id,
                        **alert_data,
                    }),
                }],
            )
        except Exception:
            pass


# Global loop detector
detector = LoopDetector()


# =============================================================================
# TOOLS WITH LOOP PROTECTION
# =============================================================================

@tool
def search_database(query: str) -> str:
    """Search the database. Protected by circuit breaker.

    Args:
        query: Search query
    """
    global _circuit_breaker_open

    # Check circuit breaker
    if _circuit_breaker_open:
        return "🚨 CIRCUIT BREAKER OPEN: Tool calls suspended due to detected loop pattern. Session should be terminated."

    # Record and check for loops
    check = detector.record_call("search_database")
    if check["loop_detected"]:
        print(f"    🚨 LOOP DETECTED: {check['reason']}")
        return f"🚨 LOOP DETECTED: {check['reason']}. Circuit breaker activated."

    time.sleep(0.1)
    return f"Database results for '{query}': 3 records found. [Customer data, order history, preferences]"


@tool
def call_external_api(endpoint: str) -> str:
    """Call an external API. Protected by circuit breaker.

    Args:
        endpoint: API endpoint to call
    """
    global _circuit_breaker_open

    if _circuit_breaker_open:
        return "🚨 CIRCUIT BREAKER OPEN: Tool calls suspended."

    check = detector.record_call("call_external_api")
    if check["loop_detected"]:
        print(f"    🚨 LOOP DETECTED: {check['reason']}")
        return f"🚨 LOOP DETECTED: {check['reason']}. Circuit breaker activated."

    time.sleep(0.2)
    return f"API response from {endpoint}: {{status: 200, data: 'processed'}}"


@tool
def update_record(record_id: str, field: str, value: str) -> str:
    """Update a database record. Protected by circuit breaker.

    Args:
        record_id: Record to update
        field: Field name
        value: New value
    """
    global _circuit_breaker_open

    if _circuit_breaker_open:
        return "🚨 CIRCUIT BREAKER OPEN: Tool calls suspended."

    check = detector.record_call("update_record")
    if check["loop_detected"]:
        print(f"    🚨 LOOP DETECTED: {check['reason']}")
        return f"🚨 LOOP DETECTED: {check['reason']}. Circuit breaker activated."

    time.sleep(0.15)
    return f"Updated {record_id}.{field} = '{value}'"


# =============================================================================
# DEMO
# =============================================================================

SYSTEM_PROMPT_NORMAL = """You are a helpful customer service agent.
Use tools to search for information and update records as needed.
If you can't find information, try different search queries.
"""

# This prompt intentionally causes loops for demonstration
SYSTEM_PROMPT_LOOPY = """You are a data processing agent.
Your task: search the database repeatedly to find ALL possible matches.
If the first search doesn't return complete results, search again with variations.
Keep searching with different query terms until you have exhaustive results.
Never stop searching until you've tried at least 10 different query variations.
After searching, update each record found to mark it as 'processed'.
"""


def run_demo():
    global _circuit_breaker_open

    print("=" * 70)
    print("PART 3: Loop Detection and Proactive Monitoring")
    print("=" * 70)
    print()
    print(f"  Session: {_session_id}")
    print()
    print("  Loop detection thresholds:")
    print(f"    • Max {_max_consecutive_same_tool} consecutive calls to same tool")
    print(f"    • Max {_max_tool_calls_per_minute} tool calls per minute")
    print(f"    • Max {_max_session_duration_seconds}s session duration")
    print()
    print("  Choose mode:")
    print("  [1] Normal agent (loop detection monitors)")
    print("  [2] Loopy agent (intentionally triggers loops — DEMO ONLY)")
    print()

    choice = input("  Select (1/2): ").strip()
    if choice == "2":
        system_prompt = SYSTEM_PROMPT_LOOPY
        print("\n  ⚠️  LOOPY MODE: Agent will attempt repetitive tool calls.")
        print("  Watch the circuit breaker activate!")
    else:
        system_prompt = SYSTEM_PROMPT_NORMAL
        print("\n  Normal mode. Try sending queries that might cause repeated searches.")

    print()
    print("  Type 'status' to see loop detection state.")
    print("  Type 'reset' to reset the circuit breaker.")
    print("  Type 'quit' to end.")
    print("=" * 70)

    model = BedrockModel(model_id=MODEL_ID)
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[search_database, call_external_api, update_record],
    )

    while True:
        print()
        try:
            user_input = input("  You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input or user_input.lower() in ("quit", "exit"):
            break

        if user_input.lower() == "status":
            show_status()
            continue

        if user_input.lower() == "reset":
            _circuit_breaker_open = False
            detector.consecutive_same_tool = 0
            print("  ✅ Circuit breaker reset. Tools re-enabled.")
            continue

        print()
        start = time.time()
        response = agent(user_input)
        elapsed = time.time() - start

        print(f"\n  Agent: {response}")
        print(f"\n    ⏱ {elapsed:.1f}s | Tool calls: {detector.total_calls} | Circuit breaker: {'🔴 OPEN' if _circuit_breaker_open else '🟢 closed'}")

    # Final summary
    print(f"\n{'═' * 70}")
    print(f"  LOOP DETECTION SUMMARY")
    print(f"{'═' * 70}")
    show_status()
    print()


def show_status():
    """Show current loop detection state."""
    duration = time.time() - _session_start
    print(f"\n  🛡️  LOOP DETECTION STATUS")
    print(f"  {'─' * 50}")
    print(f"  Session duration: {duration:.0f}s / {_max_session_duration_seconds}s max")
    print(f"  Total tool calls: {detector.total_calls}")
    print(f"  Consecutive same tool: {detector.consecutive_same_tool} / {_max_consecutive_same_tool} max")
    print(f"  Circuit breaker: {'🔴 OPEN (tools suspended)' if _circuit_breaker_open else '🟢 CLOSED (tools active)'}")
    print(f"  Alerts fired: {len(detector.alerts_fired)}")

    if detector.alerts_fired:
        print(f"\n  Recent alerts:")
        for alert in detector.alerts_fired[-5:]:
            print(f"    🚨 [{alert.get('severity', '?')}] {alert.get('reason', '?')}")


if __name__ == "__main__":
    run_demo()
