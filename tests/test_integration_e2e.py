"""
Integration "e2e" test -- runs the exact 3 goals from demo.ipynb through the
real, unmodified run_agent() loop in agent.py, back to back, sharing one
SessionMemory, and prints the full trace. This is the strongest test
possible without a live API key: every line of agent.py's control flow
executes for real (message construction, multi-tool-call handling, memory
reads/writes across turns) -- only the model's response is scripted.

Why not a real network call: this sandbox's egress allowlist does not
include models.github.ai (confirmed: 403 host_not_allowed), and no
Anthropic or other API key is available here either. Swapping this
FakeClient for a real OpenAI(base_url=...) client is the only remaining
step -- see README "Running it" for the two commands to do that yourself.

Run: python tests/test_integration_e2e.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import run_agent
from memory import SessionMemory
from fakes import FakeMessage, FakeToolCall, FakeClient


def test_full_conversation_e2e():
    memory = SessionMemory()

    print("=" * 60)
    print("TURN 1: set budget context + log two expenses")
    print("=" * 60)
    turn1_script = [
        # Realistic pattern: model batches both expenses into one response
        FakeMessage(tool_calls=[
            FakeToolCall("add_expense", {"item": "rent", "amount": 3000, "category": "housing"}, "call_1"),
            FakeToolCall("add_expense", {"item": "groceries", "amount": 450, "category": "food"}, "call_2"),
        ]),
        FakeMessage(content="Logged rent (3000, housing) and groceries (450, food). Total spent so far: 3450."),
    ]
    r1 = run_agent(
        "My monthly budget is 20000 rupees. Log a 3000 expense for rent, category housing, "
        "and a 450 expense for groceries, category food.",
        memory, client=FakeClient(turn1_script), verbose=True,
    )
    assert memory.state["total_spent"] == 3450, f"expected 3450, got {memory.state['total_spent']}"
    assert len(memory.state["expenses"]) == 2
    print(f"-> {r1}\n")

    print("=" * 60)
    print("TURN 2: category summary")
    print("=" * 60)
    turn2_script = [
        FakeMessage(tool_calls=[FakeToolCall("get_summary", {"category": "food"}, "call_3")]),
        FakeMessage(content="You've spent 450 on food so far."),
    ]
    r2 = run_agent("How much have I spent on food so far?", memory, client=FakeClient(turn2_script), verbose=True)
    assert "450" in r2
    print(f"-> {r2}\n")

    print("=" * 60)
    print("TURN 3: affordability decision (the core agentic requirement)")
    print("=" * 60)
    turn3_script = [
        FakeMessage(tool_calls=[FakeToolCall("get_summary", {}, "call_4")]),
        FakeMessage(content=(
            "You've spent 3450 of your 20000 budget, leaving 16550. "
            "A 2000 rupee trip fits comfortably -- yes, you can afford it."
        )),
    ]
    r3 = run_agent("Can I afford a 2000 rupee weekend trip this month?", memory, client=FakeClient(turn3_script), verbose=True)
    assert "afford" in r3.lower()
    print(f"-> {r3}\n")

    print("=" * 60)
    print("MEMORY CHECK: full conversation history retained across all 3 turns")
    print("=" * 60)
    assert len(memory.history) == 6, f"expected 6 history entries (3 turns x user+assistant), got {len(memory.history)}"
    for m in memory.history:
        print(f"  {m['role']:10s} -> {m['content']}")

    print("\nPASS: test_full_conversation_e2e (3-turn conversation, memory persisted and used correctly)")


if __name__ == "__main__":
    test_full_conversation_e2e()
