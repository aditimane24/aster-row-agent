"""Provider selector for LLM clients.

Exposes `get_client(provider_name)` which returns an object with
`messages.create(...)` compatible with the code in `src.agent`.
"""
from typing import Any

from src import config


def get_client(provider: str | None = None) -> Any:
    provider = provider or config.LLM_PROVIDER
    if provider == "mock":
        from .mock_provider import MockClient

        return MockClient()
    elif provider == "anthropic":
        try:
            from .anthropic_adapter import AnthropicAdapter

            return AnthropicAdapter()
        except Exception:
            # Fall back to mock if adapter can't be imported
            from .mock_provider import MockClient

            return MockClient()
    elif provider == "google":
        try:
            from .google_adapter import GoogleAdapter

            return GoogleAdapter()
        except Exception:
            from .mock_provider import MockClient

            return MockClient()
    else:
        # unknown provider => mock
        from .mock_provider import MockClient

        return MockClient()
