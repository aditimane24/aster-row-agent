"""Adapter to expose the Anthropic client with the expected interface.

This simply constructs `anthropic.Anthropic(api_key=...)` and returns
the client so code can call `client.messages.create(...)` as before.
"""
from anthropic import Anthropic
from src import config


class AnthropicAdapter:
    def __init__(self):
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    @property
    def messages(self):
        return self.client.messages

    # Keep attribute access transparent
    def __getattr__(self, name):
        return getattr(self.client, name)
