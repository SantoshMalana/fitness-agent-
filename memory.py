"""
memory.py -- session memory for the agent.

Two layers, and the assignment checks both:
  1. `history` -- raw conversation turns. Lets the agent recall things the
     user said earlier (e.g. a stated monthly budget) without a tool call.
  2. `state`   -- structured data (the expense ledger). Lets tools read and
     write data that persists and gets used again in a *later* turn --
     this is what get_summary reads back after add_expense wrote to it.
"""


class SessionMemory:
    def __init__(self):
        self.history = []  # list of {"role": ..., "content": ...} dicts
        self.state = {"expenses": [], "total_spent": 0.0}

    def get_history(self):
        return list(self.history)

    def append(self, message: dict):
        self.history.append(message)

    def reset(self):
        self.__init__()
