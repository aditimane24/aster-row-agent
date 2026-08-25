"""Run visible evaluation cases through the mock LLM provider and save outputs.

This is a no-cost, deterministic demo that exercises the full agent loop
using the built-in `mock` provider. It does NOT require any API keys.
"""
import os
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force mock provider regardless of environment before importing modules
os.environ["LLM_PROVIDER"] = "mock"

from src.agent import Agent
from src import config


def main():
    # Force mock provider regardless of environment
    os.environ["LLM_PROVIDER"] = "mock"

    vis = ROOT / "evaluation" / "visible-cases.json"
    cases = json.load(open(vis, "r", encoding="utf-8"))["cases"]

    agent = Agent()

    out = {"cases": []}
    for case in cases:
        cid = case["id"]
        prompt = " ".join(m["content"] for m in case["messages"])
        print(f"Running case: {cid}")
        resp = agent.run_turn(prompt, debug=True)
        # Agent run_turn may return a text or a structured object; coerce to str
        out_case = {"id": cid, "prompt": prompt, "response": str(resp)}
        out["cases"].append(out_case)

    out_path = ROOT / "evaluation" / "mock_live_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print("Saved mock live results to:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
