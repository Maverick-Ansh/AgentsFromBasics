"""Memory: how the system remembers. Two deliberately separate layers.

1) ShortTermMemory — the running conversation for ONE session. This IS the
   model's working context: the list of messages we send every turn. When the
   process restarts, it's gone. (In this project the conversation list is held
   by the interface — CLI/Telegram — and handed to the manager each turn; this
   class is the simple shape of it.)

2) LongTermMemory — durable facts that survive restarts, saved to disk via a
   Collection. "User prefers aisle seats." "Dentist booked 2026-06-20." Agents
   write with `remember` and read with `recall`. This is what makes the
   assistant feel like it *knows* you across days.

   `recall` here is plain keyword matching — honest and simple. The standard
   upgrade is semantic search: embed each memory as a vector and find the
   nearest ones to the query. That's a drop-in replacement for `recall()`
   (see the README), and everything else stays the same.
"""
from .store import Collection


class ShortTermMemory:
    """A session's message list. The model's working context."""

    def __init__(self):
        self.messages: list[dict] = []

    def add(self, role: str, content) -> None:
        self.messages.append({"role": role, "content": content})

    def get(self) -> list[dict]:
        return self.messages

    def reset(self) -> None:
        self.messages = []


class LongTermMemory:
    """Durable, cross-session facts backed by a JSON Collection."""

    def __init__(self, collection: Collection):
        self._c = collection

    def remember(self, text: str, tags: list[str] | None = None) -> str:
        item = self._c.add({"text": text, "tags": tags or []})
        return f"Remembered (#{item['id']}): {text}"

    def recall(self, query: str, limit: int = 5) -> str:
        q = (query or "").lower().strip()
        hits = [
            m for m in self._c.all()
            if q and (q in m["text"].lower()
                      or any(q in t.lower() for t in m.get("tags", [])))
        ]
        if not hits:
            # No keyword match: fall back to the most recent memories so the
            # agent still has *some* context to personalize with.
            hits = self._c.all()[-limit:]
        hits = hits[:limit]
        if not hits:
            return "No memories stored yet."
        return "\n".join(f"- {m['text']}" for m in hits)

    def all(self) -> list[dict]:
        return self._c.all()
