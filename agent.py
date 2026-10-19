"""
agent.py -- plan-act loop for the Personal Budget Assistant.

Setup:
    pip install openai
    export GROQ_API_KEY=<your Groq API key>     (PowerShell: $env:GROQ_API_KEY = "...")

Run:
    python agent.py
"""

import os
import sys
import json
from openai import OpenAI

# The model often answers with symbols like the rupee sign; the default Windows
# console encoding (cp1252) can't print them and print() raises UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tools import add_expense, get_summary, TOOL_SCHEMAS
from memory import SessionMemory

MODEL = "openai/gpt-oss-120b"   # using Groq model
MAX_STEPS = 6

SYSTEM_PROMPT = (
    "You are a personal budget assistant. You have two tools: add_expense and "
    "get_summary. Always call get_summary before answering any question about "
    "affordability, remaining budget, or category totals -- never guess a total "
    "from memory. If the user states a monthly budget in conversation, remember "
    "it and use it together with get_summary's total to decide whether something "
    "is affordable, and explain the numbers behind your answer."
)

TOOL_FUNCTIONS = {"add_expense": add_expense, "get_summary": get_summary}


def get_client():
    """Created lazily so importing this module doesn't require GROQ_API_KEY
    to already be set (e.g. when unit testing with a fake client)."""
    return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )


def execute_tool(name: str, arguments_json: str, state: dict):
    # Return errors to the model as the tool result so it can retry,
    # instead of crashing the whole loop on malformed arguments.
    try:
        args = json.loads(arguments_json or "{}")
        return TOOL_FUNCTIONS[name](state, **args)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        return {"error": f"{type(e).__name__}: {e}"}


def run_agent(goal: str, memory: SessionMemory, client=None, verbose: bool = True, trace: list = None):
    """The plan-act loop. Each iteration: ask the model what to do next,
    given everything tool calls have returned so far. Stop when the model
    responds with plain text instead of a tool call."""
    client = client or get_client()

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + memory.get_history()
        + [{"role": "user", "content": goal}]
    )

    for step in range(1, MAX_STEPS + 1):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            memory.append({"role": "user", "content": goal})
            memory.append({"role": "assistant", "content": msg.content})
            if verbose:
                print(f"[step {step}] final answer:\n{msg.content}\n")
            return msg.content

        messages.append(msg.model_dump(exclude_unset=True))
        for call in msg.tool_calls:
            result = execute_tool(call.function.name, call.function.arguments, memory.state)
            if trace is not None:
                trace.append({"step": step, "tool": call.function.name,
                              "args": call.function.arguments, "result": result})
            if verbose:
                print(f"[step {step}] called {call.function.name}({call.function.arguments}) -> {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return "Reached max steps without a final answer."


if __name__ == "__main__":
    memory = SessionMemory()
    run_agent(
        "My monthly budget is 20000 rupees. Log a 3000 expense for rent, category housing.",
        memory,
    )
    run_agent(
        "Also log 450 for groceries, category food, and 200 for a movie, category fun.",
        memory,
    )
    run_agent("Can I afford a 2000 rupee trip this month?", memory)
