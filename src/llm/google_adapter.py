"""Adapter for Google Gemini (Generative AI) chat API.

This adapter is optional — it will attempt to import `google.generativeai`.
Set `GOOGLE_API_KEY` in your environment (or use application default
credentials) and set `LLM_PROVIDER=google` or run CLI with
`--llm-provider=google`.

The adapter exposes `.messages.create(...)` returning an object with
`.content` (iterable of blocks with `.type` and `.text`) and
`.stop_reason` to match the minimal interface used by `src.agent`.
"""
import os
from types import SimpleNamespace
from dataclasses import dataclass

try:
    import google.generativeai as genai
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False


@dataclass
class Block(SimpleNamespace):
    pass


class GoogleAdapter:
    def __init__(self):
        if not HAS_GENAI:
            raise RuntimeError("google.generativeai package not installed")

        key = os.getenv("GOOGLE_API_KEY")
        if key:
            genai.configure(api_key=key)

        self.messages = self

    def create(self, model=None, max_tokens=None, system=None, tools=None, messages=None):
        # Convert messages to GenAI format
        gen_messages = []
        # include system prompt first if provided
        if system:
            # include tools info in the system prompt for structured tool-calling guidance
            system_text = system
            if tools:
                try:
                    import json
                    tools_desc = json.dumps(tools)
                except Exception:
                    tools_desc = str(tools)
                system_text = f"{system_text}\n\nTOOLS:{tools_desc}"
            gen_messages.append({"author": "system", "content": system_text})

        if messages:
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content")
                # genai expects dicts with 'author' and 'content'
                gen_messages.append({"author": role, "content": content})

        # Use provided model or environment
        model_name = model or os.getenv("GOOGLE_MODEL", "gemini-pro")

        # The SDK has changed over time. Prefer `genai.chat.create` when
        # available (newer SDK surface). Fall back to the Responses API
        # (`genai.responses.create`) by concatenating messages into a single
        # input string when `chat` isn't available (older or deprecated SDK).
        # Try multiple SDK surfaces: newer SDKs offer `chat.create`, older
        # ones may expose `responses.create`, and some variants expose a
        # `responder` helper. Attempt each in turn and fall back safely.
        response = None
        try:
            response = genai.chat.create(model=model_name, messages=gen_messages)
        except Exception:
            # build a plain-text input from role/message tuples
            parts = []
            for m in gen_messages:
                author = m.get("author", "user")
                content = m.get("content", "")
                parts.append(f"{author}: {content}")
            input_text = "\n".join(parts)

            # Try `responses.create`
            try:
                response = genai.responses.create(model=model_name, input=input_text)
            except Exception:
                # Try `responder` surfaces with a few common call signatures
                try:
                    responder = getattr(genai, "responder")
                    # common variants: responder.create(...), responder.respond(...),
                    # or a callable that accepts positional or keyword input.
                    if hasattr(responder, "create"):
                        response = responder.create(model=model_name, input=input_text)
                    elif hasattr(responder, "respond"):
                        response = responder.respond(model=model_name, input=input_text)
                    elif callable(responder):
                        # Try multiple calling conventions in order.
                        call_attempts = [
                            lambda r: r(input=input_text, model=model_name),
                            lambda r: r(input_text, model=model_name),
                            lambda r: r(input_text),
                            lambda r: r(input=input_text),
                            lambda r: r(model_name, input_text),
                        ]
                        last_err = None
                        for attempt in call_attempts:
                            try:
                                response = attempt(responder)
                                break
                            except Exception as e:
                                last_err = e
                        if response is None:
                            raise RuntimeError("No usable responder API found on genai module") from last_err
                    else:
                        raise RuntimeError("No usable responder API found on genai module")
                except Exception as ex:
                    raise RuntimeError("No compatible Google GenAI client API found: " + str(ex)) from ex

        # Try to extract textual content. GenAI responses vary by SDK version.
        text = ""
        try:
            if hasattr(response, "candidates") and response.candidates:
                # newer SDKs provide candidates
                text = response.candidates[0].content
            elif hasattr(response, "content"):
                text = response.content
            else:
                text = str(response)
        except Exception:
            text = str(response)

        # If the model returned JSON describing a tool call, parse it and
        # yield a `tool_use` block so the agent can execute the tool.
        # Expected JSON shape (flexible): {"tool_use": {"name": "knowledge_search", "input": {...}}}
        import json
        try:
            payload = json.loads(text)
            tu = payload.get("tool_use") or payload.get("tool")
            if isinstance(tu, dict) and tu.get("name"):
                block = Block(type="tool_use", name=tu["name"], input=tu.get("input", {}), id="genai-1")
                return SimpleNamespace(content=[block], stop_reason="tool_use")
        except Exception:
            # not JSON or missing tool_use key — continue
            pass

        # Otherwise return a text block
        block = Block(type="text", text=text)
        return SimpleNamespace(content=[block], stop_reason="completed")
