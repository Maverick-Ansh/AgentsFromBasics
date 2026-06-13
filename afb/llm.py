"""The LLM seam — the only place we talk to a model.

Why isolate this? So "use an open-source model instead of Claude" is a change
to THIS FILE ONLY. The agent loop (agent.py) speaks ONE shape — Anthropic-style
content blocks plus a `stop_reason` — and every backend here returns that shape,
translating its own native format internally.

Backends:
  AnthropicLLM     Claude via the Anthropic API. Returns native objects.
  OpenAICompatLLM  ANY OpenAI-compatible server — Ollama, vLLM, LM Studio,
                   llama.cpp, LocalAI — i.e. how you run an open-source model.
                   Translates to/from the OpenAI chat format so agent.py never
                   has to know which backend it's talking to.

Pick one with AFB_PROVIDER (see config.py); the agents can't tell the difference.
"""
import json

from . import config


# Lightweight stand-ins so non-Anthropic backends can return the SAME shape the
# agent loop reads: block.type / .text / .id / .name / .input, and resp.stop_reason.
class Block:
    __slots__ = ("type", "text", "id", "name", "input")

    def __init__(self, type, text=None, id=None, name=None, input=None):
        self.type = type
        self.text = text
        self.id = id
        self.name = name
        self.input = input


class Response:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class AnthropicLLM:
    """Claude via the Anthropic API. Returns native Anthropic response objects."""

    def __init__(self, model=None, max_tokens=None):
        import anthropic  # lazy: only needed when this backend is used

        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = model or config.MODEL
        self.max_tokens = max_tokens or config.MAX_TOKENS
        self.label = f"Anthropic · {self.model}"

    def complete(self, system, messages, tools=None):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)


class OpenAICompatLLM:
    """Any OpenAI-compatible server (Ollama / vLLM / LM Studio / llama.cpp / ...).

    The codebase speaks Anthropic's shape everywhere. This backend translates:
      - on the way IN:  our messages + tools  ->  OpenAI chat-completions format
      - on the way OUT: the OpenAI response   ->  Anthropic-shaped Blocks
    so agent.py, manager.py, and every specialist stay byte-for-byte identical.
    """

    def __init__(self, base_url=None, model=None, api_key=None, max_tokens=None):
        import openai  # lazy: only needed when this backend is used

        base_url = base_url or config.OPENAI_BASE_URL
        self.client = openai.OpenAI(
            base_url=base_url,
            api_key=api_key or config.OPENAI_API_KEY,
        )
        self.model = model or config.OPENAI_MODEL
        self.max_tokens = max_tokens or config.MAX_TOKENS
        self.label = f"OpenAI-compatible · {self.model} @ {base_url}"

    def complete(self, system, messages, tools=None):
        kwargs = {
            "model": self.model,
            "messages": self._to_openai_messages(system, messages),
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
        resp = self.client.chat.completions.create(**kwargs)
        return self._from_openai_response(resp)

    # --- translation helpers (pure; unit-testable without a running server) ---

    @staticmethod
    def _to_openai_tools(tools):
        # Anthropic {name, description, input_schema} -> OpenAI function tool.
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    @staticmethod
    def _attr(block, key, default=None):
        """Read a field whether the block is a dict or an object (Block/SDK)."""
        if isinstance(block, dict):
            return block.get(key, default)
        return getattr(block, key, default)

    @classmethod
    def _to_openai_messages(cls, system, messages):
        out = [{"role": "system", "content": system}]
        for m in messages:
            role, content = m["role"], m["content"]

            # Plain user text.
            if role == "user" and isinstance(content, str):
                out.append({"role": "user", "content": content})

            # User turn carrying tool_result block(s) (and possibly text).
            elif role == "user":
                texts = []
                for blk in content:
                    if cls._attr(blk, "type") == "tool_result":
                        result = cls._attr(blk, "content", "")
                        out.append({
                            "role": "tool",
                            "tool_call_id": cls._attr(blk, "tool_use_id"),
                            "content": result if isinstance(result, str) else str(result),
                        })
                    elif cls._attr(blk, "type") == "text":
                        texts.append(cls._attr(blk, "text", ""))
                if texts:
                    out.append({"role": "user", "content": "\n".join(texts)})

            # Assistant turn: text and/or tool_use blocks.
            elif role == "assistant":
                if isinstance(content, str):
                    out.append({"role": "assistant", "content": content})
                    continue
                texts, tool_calls = [], []
                for blk in content:
                    btype = cls._attr(blk, "type")
                    if btype == "text":
                        texts.append(cls._attr(blk, "text", ""))
                    elif btype == "tool_use":
                        tool_calls.append({
                            "id": cls._attr(blk, "id"),
                            "type": "function",
                            "function": {
                                "name": cls._attr(blk, "name"),
                                "arguments": json.dumps(cls._attr(blk, "input") or {}),
                            },
                        })
                msg = {"role": "assistant", "content": "\n".join(t for t in texts if t) or None}
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                out.append(msg)

        return out

    @staticmethod
    def _from_openai_response(resp):
        message = resp.choices[0].message
        blocks = []
        if getattr(message, "content", None):
            blocks.append(Block("text", text=message.content))
        tool_calls = getattr(message, "tool_calls", None) or []
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (ValueError, TypeError):
                args = {}
            blocks.append(Block("tool_use", id=tc.id, name=tc.function.name, input=args))
        if not blocks:  # never hand the loop an empty turn
            blocks.append(Block("text", text=""))
        return Response(blocks, "tool_use" if tool_calls else "end_turn")


def make_llm(provider: str | None = None, **kwargs):
    """Factory: build the backend chosen by AFB_PROVIDER (or the argument)."""
    provider = (provider or config.PROVIDER).lower()
    if provider in ("anthropic", "claude"):
        return AnthropicLLM(**kwargs)
    if provider in ("openai", "openai-compat", "ollama", "vllm", "local", "lmstudio"):
        return OpenAICompatLLM(**kwargs)
    raise ValueError(f"Unknown AFB_PROVIDER '{provider}'. Use 'anthropic' or 'openai'.")
