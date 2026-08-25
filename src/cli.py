"""
Minimal CLI interface. Run: python -m src.cli
Add --debug to see retrieval scores, tool calls, and handoff flags
after every response (satisfies the observability requirement).
"""
import sys

from src.agent import Agent


def main():
    debug = "--debug" in sys.argv
    # parse optional provider flag
    provider = None
    for arg in sys.argv[1:]:
        if arg.startswith("--llm-provider="):
            provider = arg.split("=", 1)[1]
        if arg == "--mock-llm":
            provider = "mock"

    # If provider is not mock, require ANTHROPIC_API_KEY to be set (for Anthropic adapter)
    cfg = __import__("src.config", fromlist=["LLM_PROVIDER", "ANTHROPIC_API_KEY"]) 
    selected = provider or cfg.LLM_PROVIDER
    if selected != "mock" and not cfg.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key, or run with --mock-llm for a free demo.")
        sys.exit(1)

    # pass provider through config for Agent to pick up
    if provider:
        import os

        os.environ["LLM_PROVIDER"] = provider

    agent = Agent()
    print("Aster & Row Support Agent — type 'exit' to quit, '--debug' was "
          f"{'ON' if debug else 'OFF'}")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not user_input:
            continue

        response = agent.run_turn(user_input, debug=debug)
        print(f"\nAgent: {response}")


if __name__ == "__main__":
    main()
