"""Booking specialist — SIMULATED reservations (data/bookings.json).

There's no real booking provider wired up, so `search_availability` returns
plausible made-up options and `make_booking` records a mock confirmation. The
shape is exactly what a real integration (OpenTable, a flights API, etc.) would
have — you'd just replace the function bodies.
"""
from datetime import datetime

from ..agent import Agent
from ..store import Collection
from ..tools import Tool, integer, obj, string

DESCRIPTION = (
    "Makes reservations/bookings: restaurants, appointments, etc. Use for "
    "'book a table', 'reserve', 'make an appointment'. Results are SIMULATED "
    "(no real provider connected) but it remembers what it booked."
)

SYSTEM = """You are the Booking specialist.

1. Use search_availability first to get options.
2. Then use make_booking for the option the user chose (or the best option if
   they didn't specify, stating which you picked).
Be transparent that these are simulated bookings. Call `now` for relative
dates. Confirm with the booking id. Return just the result the Manager needs."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def build(llm, on_event=None):
    col = Collection("bookings")

    def search_availability(kind, date=None, party_size=None, area=None):
        # MOCK: pretend to query providers and return a few options.
        label = kind.title()
        where = area or "downtown"
        when = date or "today"
        opts = [
            f"'The Garden {label}' — {where}, {when} 18:30",
            f"'Blue Door {label}' — {where}, {when} 19:00",
            f"'Corner {label} House' — {where}, {when} 20:15",
        ]
        body = "\n".join(f"- {o}" for o in opts)
        return (f"Available options (SIMULATED):\n{body}\n"
                "Pick one and call make_booking with its name and time.")

    def make_booking(name, when, party_size=None, notes=None):
        b = col.add({"name": name, "when": when,
                     "party_size": party_size, "notes": notes,
                     "status": "confirmed"})
        return (f"Booked #{b['id']}: {name} at {when}"
                + (f" for {party_size}" if party_size else "")
                + " — SIMULATED confirmation.")

    def list_bookings():
        items = col.all()
        if not items:
            return "No bookings."
        return "\n".join(
            f"#{b['id']} [{b.get('status','?')}] {b['name']} @ {b['when']}"
            + (f" ({b['party_size']})" if b.get("party_size") else "")
            for b in items
        )

    def cancel_booking(booking_id):
        b = col.update(booking_id, status="cancelled")
        return f"Cancelled booking #{booking_id}." if b else f"No booking #{booking_id}."

    tools = [
        Tool("now", "Get the current date and time.", obj(), lambda: _now()),
        Tool("search_availability", "Find available booking options (simulated).",
             obj(kind=string("What to book, e.g. 'restaurant', 'dentist'"),
                 date=string("Desired date (optional)"),
                 party_size=integer("Number of people (optional)"),
                 area=string("Area/neighborhood (optional)"),
                 required=["kind"]),
             search_availability),
        Tool("make_booking", "Confirm a booking for a chosen option.",
             obj(name=string("Venue/provider name"),
                 when=string("Date & time, 'YYYY-MM-DD HH:MM'"),
                 party_size=integer("Number of people (optional)"),
                 notes=string("Special requests (optional)"),
                 required=["name", "when"]),
             make_booking),
        Tool("list_bookings", "List all bookings.", obj(), list_bookings),
        Tool("cancel_booking", "Cancel a booking by id.",
             obj(booking_id=integer("The booking id"), required=["booking_id"]),
             cancel_booking),
    ]
    agent = Agent("booking", SYSTEM, tools, llm, on_event=on_event)
    return {"agent": agent, "description": DESCRIPTION}
