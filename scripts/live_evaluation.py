"""Run visible evaluation cases through a live LLM provider.

This script requires either `GOOGLE_API_KEY` (for Gemini) or
`ANTHROPIC_API_KEY` (for Anthropic) to be set. It runs each visible
case by sending the combined messages to the agent and printing the
LLM response. This is a developer aid for manual verification and
demoing; it is NOT used by the deterministic runner.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config
from src.agent import Agent


def main():
    provider = os.getenv("LLM_PROVIDER", config.LLM_PROVIDER)
    if provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY is not set. Set it and run again.")
        return 2
    if provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Set it and run again.")
        return 2

    import json
    vis = ROOT / "evaluation" / "visible-cases.json"
    cases = json.load(open(vis, "r", encoding="utf-8"))["cases"]

    agent = Agent()

    for case in cases:
        print("\n===", case["id"], "===")
        # combine multi-turn messages for a single-turn demo
        prompt = " ".join(m["content"] for m in case["messages"]) 
        resp = agent.run_turn(prompt, debug=True)
        print("Agent reply:\n", resp)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
