"""
Structured logging for observability. Every turn writes one JSON line
to logs/trace.jsonl containing: user message, retrieved chunks, tool
calls + sanitized results, and the final response. Plain text with
--debug prints the same info to the terminal as it happens.

Never log secrets: we log tool call ARGUMENTS and RESULTS, but the
order tool already strips internal fields before we ever see them, so
there's nothing sensitive to accidentally log here.
"""
import json
from datetime import datetime, timezone

from src import config

config.LOGS_DIR.mkdir(exist_ok=True)
TRACE_FILE = config.LOGS_DIR / "trace.jsonl"


def log_turn(session_id: str, user_message: str, history_len: int,
             retrieved: list, tool_calls: list, final_response: str,
             handoff: bool):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_message": user_message,
        "conversation_turns_so_far": history_len,
        "retrieved_chunks": [
            {"source_file": r["source_file"], "heading": r["heading"],
             "score": round(r["score"], 3), "status": r["status"]}
            for r in retrieved
        ],
        "tool_calls": tool_calls,
        "final_response": final_response,
        "handoff_recommended": handoff,
    }
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return record


def print_debug(record: dict):
    print("\n--- DEBUG TRACE ---")
    print(f"User message: {record['user_message']}")
    if record["retrieved_chunks"]:
        print("Retrieved chunks:")
        for c in record["retrieved_chunks"]:
            print(f"  [{c['score']}] {c['source_file']} :: {c['heading']} (status={c['status']})")
    if record["tool_calls"]:
        print("Tool calls:")
        for t in record["tool_calls"]:
            print(f"  {t['tool']}({t['arguments']}) -> {t['result_summary']}")
    print(f"Handoff recommended: {record['handoff_recommended']}")
    print("--- END TRACE ---\n")
