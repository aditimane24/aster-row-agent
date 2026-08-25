"""A deterministic, rule-based mock LLM client for offline demos and tests.

The mock exposes `messages.create(...)` which mimics the minimal shape
the agent expects: it returns an object with `.content` (iterable of
blocks) and `.stop_reason`.
"""
import re
import uuid
from types import SimpleNamespace
from typing import List, Dict, Any


class Block(SimpleNamespace):
    pass


class MockClient:
    def __init__(self):
        self._id = str(uuid.uuid4())
        # expose `.messages.create(...)` like Anthropic client
        self.messages = self
    # Keep same call signature as Anthropic client's messages.create
    def create(self, model=None, max_tokens=None, system=None, tools=None, messages=None):
        # Determine last user content
        last_user = None
        if messages:
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user = m.get("content")
                    break

        # If last_user is a list of tool_result dicts, return final text
        if isinstance(last_user, list) and last_user and all(isinstance(t, dict) and t.get("type") == "tool_result" for t in last_user):
            # Summarize tool results
            parts = [t.get("content", "") for t in last_user]
            text = "\n".join(parts)
            return SimpleNamespace(content=[Block(type="text", text=f"Here are the tool results:\n{text}" )], stop_reason="completed")

        # If user asked about an order id, request order_lookup tool
        if isinstance(last_user, str):
            # extract order id pattern
            m = re.search(r"\b(ORD-?\d{3,})\b", last_user, re.I)
            if m:
                order_id = m.group(1).upper().replace("-", "-")
                tool_block = Block(type="tool_use", name="order_lookup", input={"order_id": order_id}, id=str(uuid.uuid4()))
                return SimpleNamespace(content=[tool_block], stop_reason="tool_use")

            # return/return policy keywords => call knowledge_search
            if any(k in last_user.lower() for k in ("return", "refund", "final sale", "return window", "return policy")):
                tool_block = Block(type="tool_use", name="knowledge_search", input={"query": last_user}, id=str(uuid.uuid4()))
                return SimpleNamespace(content=[tool_block], stop_reason="tool_use")

        # Default: simple canned reply
        default_text = "I can answer policy and order questions. Ask about an order `ORD-xxxx` or 'return policy'."
        return SimpleNamespace(content=[Block(type="text", text=default_text)], stop_reason="completed")
