"""
tools.py -- the two tools the agent can call.

Both tools operate on `state`, a plain dict owned by SessionMemory
(see memory.py). Passing state in explicitly (rather than using a
global) keeps these functions easy to unit test on their own.
"""


def add_expense(state, item: str, amount: float, category: str = "general"):
    """Log a single expense. Returns the updated running total."""
    entry = {"item": item, "amount": float(amount), "category": category}
    state["expenses"].append(entry)
    state["total_spent"] = round(state["total_spent"] + entry["amount"], 2)
    return {
        "logged": entry,
        "total_spent": state["total_spent"],
        "expense_count": len(state["expenses"]),
    }


def get_summary(state, category: str = None):
    """Return spending totals, optionally filtered to one category."""
    if category:
        matched = [e for e in state["expenses"] if e["category"].lower() == category.lower()]
        total = round(sum(e["amount"] for e in matched), 2)
        return {"category": category, "total": total, "count": len(matched)}

    by_category = {}
    for e in state["expenses"]:
        by_category[e["category"]] = round(by_category.get(e["category"], 0) + e["amount"], 2)
    return {
        "total_spent": state["total_spent"],
        "by_category": by_category,
        "expense_count": len(state["expenses"]),
    }


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Log a single expense so it counts toward the running total and category summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "What the expense was for, e.g. 'groceries'."},
                    "amount": {"type": "number", "description": "Amount spent, in the user's stated currency."},
                    "category": {"type": "string", "description": "Spending category, e.g. 'food', 'travel', 'rent'. Default 'general'."},
                },
                "required": ["item", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": "Get the running total spent, optionally filtered to one category. Always call this before answering any question about affordability or remaining budget -- never guess the total from memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": ["string", "null"], "description": "Optional category filter, e.g. 'food'. Omit for the full breakdown."},
                },
                "required": [],
            },
        },
    },
]
