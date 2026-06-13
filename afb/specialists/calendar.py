"""Calendar specialist — MOCK calendar stored on disk.

The tools below write to a local JSON file (data/calendar.json). To use REAL
Google Calendar later, reimplement these handlers against the Google Calendar
API — the agent and its system prompt don't change at all. That's the payoff of
putting every capability behind a tool.
"""
from datetime import datetime

from ..agent import Agent
from ..store import Collection
from ..tools import Tool, integer, obj, string

DESCRIPTION = (
    "Manages the user's calendar: create / list / reschedule / delete events. "
    "Use for 'schedule', 'add to my calendar', 'what's on Friday', 'move my "
    "meeting'. (Mock calendar stored locally; real Google Calendar swaps in "
    "behind these same tools.)"
)

SYSTEM = """You are the Calendar specialist managing the user's schedule.

- Call `now` to resolve relative dates ("tomorrow", "next Friday") into a
  concrete date before creating or moving events.
- Store times as "YYYY-MM-DD HH:MM".
- After any change, confirm what you did and include the event id.
- This is a local mock calendar; that's fine — behave exactly as you would with
  a real one. Return just the result the Manager needs."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def build(llm, on_event=None):
    col = Collection("calendar")

    def create_event(title, start, end=None, location=None, notes=None):
        ev = col.add(
            {"title": title, "start": start, "end": end,
             "location": location, "notes": notes}
        )
        span = f"{start}" + (f"–{end}" if end else "")
        return f"Created event #{ev['id']}: '{title}' at {span}."

    def list_events(query=None):
        items = col.all()
        if query:
            q = query.lower()
            items = [
                e for e in items
                if q in f"{e.get('title','')} {e.get('start','')}".lower()
            ]
        if not items:
            return "No events found."
        return "\n".join(
            f"#{e['id']} {e.get('start','?')}"
            + (f"–{e['end']}" if e.get("end") else "")
            + f" — {e['title']}"
            + (f" @ {e['location']}" if e.get("location") else "")
            for e in items
        )

    def update_event(event_id, title=None, start=None, end=None,
                     location=None, notes=None):
        changes = {k: v for k, v in dict(
            title=title, start=start, end=end, location=location, notes=notes
        ).items() if v is not None}
        if not changes:
            return "Nothing to update — provide at least one field to change."
        ev = col.update(event_id, **changes)
        return f"Updated event #{event_id}." if ev else f"No event #{event_id}."

    def delete_event(event_id):
        ok = col.delete(event_id)
        return f"Deleted event #{event_id}." if ok else f"No event #{event_id}."

    tools = [
        Tool("now", "Get the current date and time (to resolve relative dates).",
             obj(), lambda: _now()),
        Tool("create_event", "Add an event to the calendar.",
             obj(title=string("Event title"),
                 start=string("Start, 'YYYY-MM-DD HH:MM'"),
                 end=string("End, 'YYYY-MM-DD HH:MM' (optional)"),
                 location=string("Location (optional)"),
                 notes=string("Notes (optional)"),
                 required=["title", "start"]),
             create_event),
        Tool("list_events", "List events, optionally filtered by a keyword/date.",
             obj(query=string("Optional filter (e.g. a date or title word)")),
             list_events),
        Tool("update_event", "Reschedule or edit an existing event by id.",
             obj(event_id=integer("The event id"),
                 title=string("New title (optional)"),
                 start=string("New start (optional)"),
                 end=string("New end (optional)"),
                 location=string("New location (optional)"),
                 notes=string("New notes (optional)"),
                 required=["event_id"]),
             update_event),
        Tool("delete_event", "Delete an event by id.",
             obj(event_id=integer("The event id"), required=["event_id"]),
             delete_event),
    ]
    agent = Agent("calendar", SYSTEM, tools, llm, on_event=on_event)
    return {"agent": agent, "description": DESCRIPTION}
