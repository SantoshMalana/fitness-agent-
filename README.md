# 💰 Personal Budget Assistant

An LLM agent that tracks a monthly budget and answers affordability questions:
"can I afford a ₹2,000 trip this month?". It answers by **calling tools against
a real expense ledger** instead of guessing totals from the conversation.

Built for **CSE476 CA1 Project 1**. It ships with a plain Python plan-act loop,
a Jupyter demo and a small web UI.

![stack](https://img.shields.io/badge/python-3.10%2B-blue) ![llm](https://img.shields.io/badge/LLM-Groq%20%C2%B7%20gpt--oss--120b-purple) ![deps](https://img.shields.io/badge/deps-openai%20only-green)

---

## Features

- **Plan-act agent loop** ([agent.py](agent.py)): the model decides which tool to call, sees the
  result, and repeats until it can give a final answer. A `MAX_STEPS = 6` guard stops endless loops.
- **Two tools** ([tools.py](tools.py)): `add_expense` and `get_summary`.
- **Two-layer memory** ([memory.py](memory.py)): conversation history and a structured ledger.
- **Web UI** ([app.py](app.py) + [ui.html](ui.html)): chat, a budget meter, category breakdown,
  an expense list and expandable tool-call traces. It uses only Python's standard library, so there's nothing extra to install.
- **Offline tests** ([tests/](tests/)): the real `run_agent()` loop runs against a fake client, so no API key is needed.

## Quick start

```bash
git clone https://github.com/SantoshMalana/fitness-agent-.git
cd fitness-agent-
pip install -r requirements.txt
```

Get a free API key at <https://console.groq.com/keys>, then set it:

```bash
# macOS / Linux
export GROQ_API_KEY="gsk_..."

# Windows PowerShell
$env:GROQ_API_KEY = "gsk_..."
```

### Run the web UI (recommended)

```bash
python app.py
```

This opens <http://localhost:8000>. If you didn't set the key, you can paste it into the sidebar instead.
The key stays in memory only and is never written to disk.

1. Set your monthly budget, either in the sidebar or by saying it in chat ("My monthly budget is 20000 rupees").
2. Log expenses in plain English: *"Log 450 for groceries, category food, and 200 for a movie, category fun."*
3. Ask questions: *"How much have I spent on food?"* or *"Can I afford a 2000 rupee trip?"*
4. Click a ➕ / 📊 chip under an answer to see the exact tool call and its result.
5. **Reset session** clears the ledger, the budget and the chat history.

### Run from the command line

```bash
python agent.py          # runs 3 example goals and prints the full tool-call trace
```

### Run the notebook

```bash
jupyter notebook demo.ipynb   # asks for your key if GROQ_API_KEY isn't set
```

### Run the tests (no API key needed)

```bash
python tests/test_smoke.py
python tests/test_integration_e2e.py
```

## How it works

```
user message ─► run_agent()
                  │
                  ├─► LLM (system prompt + history + message + tool schemas)
                  │      │
                  │      ├─ tool call? ─► execute_tool() ─► reads/writes memory.state ─┐
                  │      │                                                             │
                  │      └─ plain text? ─► final answer, saved to memory.history       │
                  │                                                                    │
                  └──────────────── tool result fed back to the LLM ◄──────────────────┘
                                    (max 6 steps)
```

### Tools

| Tool | What it does |
|------|--------------|
| `add_expense(item, amount, category)` | Logs one expense and updates the running total. |
| `get_summary(category=None)` | Returns the full breakdown by category, or a single category's total. |

The system prompt tells the model to **always call `get_summary` before answering any
affordability or remaining-budget question**. Its decisions are grounded in the ledger,
not in numbers remembered from the chat.

### Memory

Memory has two layers:

1. **`SessionMemory.history`**: the raw conversation turns. The agent can recall things
   said earlier, like a budget stated in turn one, without a dedicated tool.
2. **`SessionMemory.state`**: the structured ledger. This is what shows memory is *used*,
   not just stored. `add_expense` writes to it in one turn, and `get_summary` reads it back in a
   later turn to answer "can I afford a 2000 rupee trip": the agent checks the running total,
   subtracts and decides.

### Example (real run, `openai/gpt-oss-120b` on Groq)

> **You:** My monthly budget is 20000 rupees. Log 3000 for rent, category housing.
> &nbsp;&nbsp;➕ `add_expense({"item":"rent","amount":3000,"category":"housing"})`
>
> **You:** Log 450 for groceries, category food, and 200 for a movie, category fun.
> &nbsp;&nbsp;➕ `add_expense(...)` ×2
>
> **You:** Can I afford a 2000 rupee trip this month?
> &nbsp;&nbsp;📊 `get_summary({})` → `{"total_spent": 3650, ...}`
>
> **Agent:** Yes, you can afford a **₹2,000** trip this month. Budget ₹20,000 – spent ₹3,650 =
> **₹16,350** remaining, which is well above the cost of the trip.

## One honest failure

On the first live run against Groq, the agent **crashed after the tool calls had already
succeeded**, with `UnicodeEncodeError: 'charmap' codec can't encode character '₹'`.
The model formats amounts with the rupee sign (₹), and on Windows `sys.stdout` defaults to
the cp1252 encoding, which has no ₹. The trace `print()` in `run_agent` therefore threw, and the final answer
was lost even though the ledger had been updated correctly. The offline tests never caught this
because the fake client only returns plain ASCII. The fix was a single line in `agent.py`,
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. While fixing it, I also wrapped
tool-argument parsing in `execute_tool` so that malformed JSON from the model is returned to it as an
error result it can retry from, instead of crashing the loop.

## Project structure

```
├── agent.py            # plan-act loop, system prompt, Groq client
├── tools.py            # add_expense, get_summary + JSON tool schemas
├── memory.py           # SessionMemory: history + ledger state
├── app.py              # web UI server (stdlib http.server)
├── ui.html             # web UI front end
├── demo.ipynb          # notebook demo for submission
├── requirements.txt
└── tests/
    ├── fakes.py                  # fake OpenAI-shaped client
    ├── test_smoke.py             # tool-call, memory, max-steps tests
    ├── test_integration_e2e.py   # 3-turn offline conversation
    └── e2e_trace_output.txt      # saved test output
```

## Configuration

| Setting | Where | Default |
|---------|-------|---------|
| Model | `MODEL` in [agent.py](agent.py) | `openai/gpt-oss-120b` |
| Max agent steps | `MAX_STEPS` in [agent.py](agent.py) | `6` |
| UI port | `PORT` in [app.py](app.py) | `8000` |
| API key | `GROQ_API_KEY` env var, or the UI sidebar | none |

Groq exposes an OpenAI-compatible API, so the `openai` SDK works with only a `base_url` change.
You can switch providers (OpenAI, GitHub Models and others) by editing `get_client()` and `MODEL`.

## Limitations

- Memory lasts for the session only. Restarting the app clears the ledger.
- The UI handles one user at a time, since every visitor shares the same server-side session.
- The budget meter in the UI reads the budget from your messages ("budget is 20000"), while
  the agent itself remembers it through conversation history.
