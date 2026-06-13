"""Terminal chat — the best interface for *learning*.

It prints every tool call as it happens, so you can literally watch the Manager
delegate to specialists and the specialists use their tools:

    you> book me a table for 2 tomorrow and put it on my calendar
       · [manager] ask_booking({"task": "Book a restaurant table for 2 ..."})
       · [booking] now({})
       · [booking] search_availability({"kind": "restaurant", ...})
       · [booking] make_booking({"name": "Blue Door Restaurant", ...})
       · [manager] ask_calendar({"task": "Add an event 'Dinner ...'"})
       · [calendar] create_event({"title": "Dinner at Blue Door", ...})
    assistant> Done! Booked Blue Door for 2 tomorrow at 19:00 and added it ...
"""
import json

from ..app import build_system

BANNER = """\
╭───────────────────────────────────────────────────────────────╮
│  Agents From Basics — Manager + 5 specialists                 │
│  Try: "what's the latest on <topic>", "add a task to ...",    │
│       "schedule lunch friday 1pm", "book a table for 2 ...",  │
│       "email alex that I'm running late", "remember I ..."    │
│  Type 'exit' to quit.                                         │
╰───────────────────────────────────────────────────────────────╯"""


def _short(value, limit: int = 90) -> str:
    try:
        s = json.dumps(value, ensure_ascii=False)
    except Exception:
        s = str(value)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def main() -> None:
    # Show tool calls so the orchestration is visible.
    def on_event(kind, **info):
        if kind == "tool_call":
            print(f"   · [{info.get('agent')}] {info.get('tool')}({_short(info.get('input'))})")

    manager = build_system(on_event)
    print(BANNER)

    conversation: list = []  # short-term memory: persists for this session
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            return
        if not user:
            continue
        if user.lower() in {"exit", "quit", ":q"}:
            print("bye!")
            return

        conversation.append({"role": "user", "content": user})
        try:
            reply, conversation = manager.run(conversation)
        except Exception as exc:  # keep the REPL alive on errors
            reply = f"(error: {exc})"
        print(f"\nassistant> {reply}")
