"""The LLM seam — the only place we talk to the model.

Why isolate this? So that "use an open-source model instead" is a change to
THIS FILE ONLY. Every agent calls `LLM.complete(...)`; none of them import the
Anthropic SDK directly. To run on a local model later (Ollama, vLLM, LM Studio,
...), you'd reimplement `complete()` against that backend and convert its
tool-call format into the same block shape the agent loop expects.
"""
from . import config


class LLM:
    """A thin wrapper around Claude's Messages API."""

    def __init__(self, model: str | None = None, max_tokens: int | None = None):
        # Imported lazily so the rest of the codebase can be imported / syntax
        # checked without the SDK installed.
        import anthropic

        # Reads ANTHROPIC_API_KEY from the environment automatically.
        self.client = anthropic.Anthropic()
        self.model = model or config.MODEL
        self.max_tokens = max_tokens or config.MAX_TOKENS

    def complete(self, system: str, messages: list, tools: list | None = None):
        """One model turn.

        Args:
            system:   the system prompt (the agent's "identity" + instructions).
            messages: the running conversation (list of role/content dicts).
            tools:    list of tool specs the model is allowed to call this turn.

        Returns the raw Anthropic response. It contains a list of content
        blocks (text and/or tool_use) plus a `stop_reason` the agent loop reads
        to decide whether the model is done or wants to run a tool.

        Non-streaming on purpose: it keeps the agent loop easy to read. For
        long outputs you'd switch to client.messages.stream(...).
        """
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)
