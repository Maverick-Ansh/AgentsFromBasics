"""The five specialist agents.

Each module exposes `build(llm, on_event) -> {"agent": Agent, "description": str}`.
The `description` is what the Manager sees — it's how the Manager knows WHEN to
delegate to that specialist. Each specialist is a full Agent with its own
system prompt and its own domain tools.
"""
