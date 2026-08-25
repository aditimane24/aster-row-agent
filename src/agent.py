"""
The agent loop: takes a user message, gives Claude access to two
tools (knowledge_search, order_lookup), executes whichever tools
Claude decides to call, feeds results back, and returns the final
text response. Conversation history is kept per-session so follow-up
questions ("What about Canada?") work naturally — Claude just sees
the prior turns like any multi-turn chat.
"""
import uuid

from src import config, logging_utils
from src.llm.provider import get_client
from src.system_prompt import SYSTEM_PROMPT
from src.retriever import search as knowledge_search
from src.order_tool import lookup_order, ORDER_LOOKUP_TOOL_SCHEMA

KNOWLEDGE_SEARCH_TOOL_SCHEMA = {
    "name": "knowledge_search",
    "description": (
        "Search the Aster & Row knowledge base for policy and product information. "
        "Returns the most relevant passages with their source file, heading, status "
        "(active/superseded/draft), and authority level."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A natural-language search query, e.g. 'return window for TrailPlus members'."
            }
        },
        "required": ["query"],
    },
}

TOOLS = [KNOWLEDGE_SEARCH_TOOL_SCHEMA, ORDER_LOOKUP_TOOL_SCHEMA]

# Phrases that, if present in the final response, suggest the agent is
# recommending a human handoff. Used only for logging/observability —
# not for controlling behavior.
_HANDOFF_HINTS = [
    "human", "support specialist", "contact support", "escalat",
    "recommend reaching out", "review before",
]


class Agent:
    def __init__(self):
        self.client = get_client(config.LLM_PROVIDER)
        self.session_id = str(uuid.uuid4())[:8]
        self.messages = []  # full conversation history, Claude-format

    def _execute_tool(self, name: str, tool_input: dict) -> tuple[dict, dict]:
        """Runs the requested tool. Returns (raw_result_for_model, log_entry)."""
        if name == "knowledge_search":
            results = knowledge_search(tool_input["query"])
            # what Claude sees: text + metadata needed for citation/precedence
            model_view = [
                {
                    "source_file": r["source_file"],
                    "heading": r["heading"],
                    "text": r["text"],
                    "status": r["status"],
                    "policy_authority": r["policy_authority"],
                    "audience": r["audience"],
                }
                for r in results
            ]
            log_entry = {
                "tool": "knowledge_search",
                "arguments": tool_input,
                "result_summary": f"{len(results)} chunks: " +
                                   ", ".join(f"{r['source_file']}::{r['heading']}" for r in results),
            }
            return {"results": model_view}, log_entry, results

        elif name == "order_lookup":
            result = lookup_order(tool_input.get("order_id", ""))
            log_entry = {
                "tool": "order_lookup",
                "arguments": tool_input,
                "result_summary": (
                    f"found=True status={result.get('status')}" if result.get("found")
                    else f"found=False requested_id={result.get('requested_id')}"
                ),
            }
            return result, log_entry, []

        else:
            return {"error": f"unknown tool {name}"}, {"tool": name, "arguments": tool_input,
                                                          "result_summary": "unknown tool"}, []

    def run_turn(self, user_message: str, debug: bool = False) -> str:
        self.messages.append({"role": "user", "content": user_message})

        all_tool_calls = []
        all_retrieved = []

        while True:
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
            )

            # Collect assistant content (text + any tool_use blocks) into history
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                handoff = any(hint in final_text.lower() for hint in _HANDOFF_HINTS)
                record = logging_utils.log_turn(
                    self.session_id, user_message, len(self.messages),
                    all_retrieved, all_tool_calls, final_text, handoff,
                )
                if debug:
                    logging_utils.print_debug(record)
                return final_text

            # Execute every tool_use block in this response, then loop again
            tool_results_content = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                raw_result, log_entry, retrieved = self._execute_tool(block.name, block.input)
                all_tool_calls.append(log_entry)
                all_retrieved.extend(retrieved)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(raw_result),
                })

            self.messages.append({"role": "user", "content": tool_results_content})
