"""
fakes.py -- a fake client that mimics the exact shape of an OpenAI
ChatCompletion response object (response.choices[0].message.tool_calls,
.function.name/.arguments, .model_dump()). This lets run_agent()'s real,
unmodified code path be exercised without a network call or API key.
"""

import json


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = json.dumps(arguments)


class FakeToolCall:
    def __init__(self, name, arguments, call_id):
        self.id = call_id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, **kwargs):
        return {
            "role": "assistant",
            "content": self.content,
            "tool_calls": self.tool_calls,
        }


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


class FakeCompletions:
    def __init__(self, script):
        self.script = script
        self.calls = 0

    def create(self, model, messages, tools):
        msg = self.script[self.calls]
        self.calls += 1
        return FakeResponse(msg)


class FakeChatAPI:
    def __init__(self, script):
        self.completions = FakeCompletions(script)


class FakeClient:
    def __init__(self, script):
        self.chat = FakeChatAPI(script)
