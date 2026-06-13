"""Assemble the whole system.

This is the one place that builds every piece and wires them together, so both
interfaces (CLI and Telegram) share the exact same brain.
"""
from .llm import make_llm
from .manager import build_manager
from .memory import LongTermMemory
from .specialists import booking, calendar, comms, research, tasks
from .store import Collection


def build_system(on_event=None):
    """Build and return the Manager agent (with all 5 specialists wired in).

    `on_event(kind, **info)` is an optional callback the interface can pass to
    watch what's happening (which agent calls which tool). See cli.py.
    """
    llm = make_llm()  # backend chosen by AFB_PROVIDER (anthropic | openai)

    # Long-term memory: one durable store shared across the whole system.
    long_term_memory = LongTermMemory(Collection("memory"))

    # Build each specialist. The dict key becomes the delegate tool name
    # (ask_research, ask_calendar, ...).
    specialists = {
        "research": research.build(llm, on_event),
        "calendar": calendar.build(llm, on_event),
        "tasks": tasks.build(llm, on_event),
        "booking": booking.build(llm, on_event),
        "comms": comms.build(llm, on_event),
    }

    return build_manager(llm, specialists, long_term_memory, on_event=on_event)
