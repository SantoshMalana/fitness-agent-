"""
Offline smoke test for the plan-act loop.

Uses a fake client that mimics the shape of an OpenAI ChatCompletion
response, so the control flow (tool routing, memory writes, message
construction) can be verified without a real API key or network call.
Run: python tests/test_smoke.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import run_agent
from memory import SessionMemory
from fakes import FakeMessage, FakeToolCall, FakeClient


def test_tool_call_then_final_answer():
    """Step 1: model calls add_expense. Step 2: model answers in plain text.
    Checks the loop executes the tool, writes to memory.state, and returns
    the final answer without needing a 3rd step."""
    script = [
        FakeMessage(tool_calls=[
            FakeToolCall("add_expense", {"item": "rent", "amount": 3000, "category": "housing"}, "call_1")
        ]),
        FakeMessage(content="Logged your 3000 rent expense."),
    ]
    client = FakeClient(script)
    memory = SessionMemory()

    result = run_agent("Log 3000 for rent", memory, client=client, verbose=False)

    assert result == "Logged your 3000 rent expense."
    assert memory.state["total_spent"] == 3000
    assert memory.state["expenses"][0]["item"] == "rent"
    assert memory.history[-1]["content"] == "Logged your 3000 rent expense."
    print("PASS: test_tool_call_then_final_answer")


def test_memory_used_across_turns():
    """Turn 1 logs an expense. Turn 2 (fresh run_agent call, same SessionMemory)
    asks for a summary -- proves state persists and is read back later."""
    memory = SessionMemory()

    script_turn1 = [
        FakeMessage(tool_calls=[
            FakeToolCall("add_expense", {"item": "groceries", "amount": 450, "category": "food"}, "call_1")
        ]),
        FakeMessage(content="Logged groceries."),
    ]
    run_agent("Log 450 for groceries", memory, client=FakeClient(script_turn1), verbose=False)

    script_turn2 = [
        FakeMessage(tool_calls=[
            FakeToolCall("get_summary", {"category": "food"}, "call_2")
        ]),
        FakeMessage(content="You've spent 450 on food so far."),
    ]
    result = run_agent("How much have I spent on food?", memory, client=FakeClient(script_turn2), verbose=False)

    assert result == "You've spent 450 on food so far."
    assert len(memory.history) == 4  # 2 turns x (user, assistant)
    print("PASS: test_memory_used_across_turns")


def test_max_steps_guard():
    """If the model never stops calling tools, the loop must still terminate
    instead of looping forever -- this is a real failure mode worth
    reproducing against the live API for the README."""
    script = [
        FakeMessage(tool_calls=[FakeToolCall("get_summary", {}, f"call_{i}")])
        for i in range(10)
    ]
    memory = SessionMemory()
    result = run_agent("loop forever", memory, client=FakeClient(script), verbose=False)
    assert result == "Reached max steps without a final answer."
    print("PASS: test_max_steps_guard")


if __name__ == "__main__":
    test_tool_call_then_final_answer()
    test_memory_used_across_turns()
    test_max_steps_guard()
    print("\nAll smoke tests passed.")
