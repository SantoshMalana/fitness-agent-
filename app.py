"""
app.py -- simple web UI for the Personal Budget Assistant.

No extra dependencies: uses Python's built-in http.server.

Run:
    $env:GROQ_API_KEY = "gsk_..."     (or paste the key into the UI)
    python app.py
Then open http://localhost:8000
"""

import json
import os
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

from agent import run_agent, MODEL
from memory import SessionMemory

PORT = 8000
UI_FILE = Path(__file__).parent / "ui.html"

memory = SessionMemory()
lock = Lock()  # one agent run at a time -- memory is shared
budget = {"amount": None}  # UI-only mirror of the budget the user states in chat

BUDGET_RE = re.compile(r"budget\D{0,20}?(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)


def state_payload():
    return {
        "expenses": memory.state["expenses"],
        "total_spent": memory.state["total_spent"],
        "budget": budget["amount"],
        "history": [m for m in memory.get_history() if m.get("content")],
        "has_key": bool(os.environ.get("GROQ_API_KEY")),
        "model": MODEL,
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path == "/":
            self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self._send(200, state_payload())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/chat":
            message = self._body().get("message", "").strip()
            if not message:
                return self._send(400, {"error": "Empty message."})
            if not os.environ.get("GROQ_API_KEY"):
                return self._send(400, {"error": "No GROQ_API_KEY set. Paste your key in the sidebar."})
            match = BUDGET_RE.search(message)
            if match:
                budget["amount"] = float(match.group(1).replace(",", ""))
            trace = []
            with lock:
                try:
                    reply = run_agent(message, memory, trace=trace)
                except Exception as e:  # surface API / tool errors in the UI instead of crashing
                    return self._send(500, {"error": f"{type(e).__name__}: {e}", "trace": trace})
            self._send(200, {"reply": reply, "trace": trace, **state_payload()})

        elif self.path == "/api/key":
            key = self._body().get("key", "").strip()
            if not key:
                return self._send(400, {"error": "Empty key."})
            os.environ["GROQ_API_KEY"] = key  # in-process only, not saved to disk
            self._send(200, state_payload())

        elif self.path == "/api/reset":
            with lock:
                memory.reset()
                budget["amount"] = None
            self._send(200, state_payload())
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass  # keep the console for the agent's own trace output


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Budget Assistant UI running at {url}  (Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
