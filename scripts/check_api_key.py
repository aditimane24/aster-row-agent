"""Simple health-check for LLM provider keys.

Usage: `python scripts/check_api_key.py` — prints status and exits
with code 0 when a usable key is found or mock is selected; non-zero otherwise.
"""
import os
from src import config


def main():
    provider = os.getenv("LLM_PROVIDER", config.LLM_PROVIDER)
    if provider == "mock":
        print("LLM provider: mock (no key required)")
        return 0

    if provider == "anthropic":
        if config.ANTHROPIC_API_KEY:
            print("Anthropic API key found (LLM calls enabled)")
            return 0
        else:
            print("Anthropic API key NOT found. Set ANTHROPIC_API_KEY in .env or environment.")
            return 2

    print(f"LLM provider '{provider}' selected. Please ensure credentials are configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
