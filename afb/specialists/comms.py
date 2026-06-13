"""Comms specialist — MOCK email (data/outbox.json).

"Sending" just records the message to a local outbox; nothing actually leaves
the machine. Wire up SMTP or the Gmail API later behind send_email.
"""
from ..agent import Agent
from ..store import Collection
from ..tools import Tool, integer, obj, string

DESCRIPTION = (
    "Drafts and sends emails on the user's behalf. Use for 'email X', 'draft a "
    "message to', 'reply to'. Sending is MOCKED (saved to a local outbox, "
    "nothing actually sent)."
)

SYSTEM = """You are the Comms specialist. You draft and 'send' emails.

- Write clear, friendly, concise emails with a sensible subject line.
- Use draft_email when the user wants to review first; send_email to send.
- Sending is mocked (saved locally, nothing actually leaves the machine) — be
  transparent about that. Confirm with the message id. Return just the result
  the Manager needs."""


def build(llm, on_event=None):
    col = Collection("outbox")

    def draft_email(to, subject, body):
        m = col.add({"to": to, "subject": subject, "body": body, "status": "draft"})
        return f"Drafted email #{m['id']} to {to} — '{subject}'."

    def send_email(to, subject, body):
        m = col.add({"to": to, "subject": subject, "body": body, "status": "sent"})
        return f"Sent email #{m['id']} to {to} — '{subject}' (MOCK send)."

    def list_outbox(status=None):
        items = col.all()
        if status:
            items = [m for m in items if m.get("status") == status]
        if not items:
            return "Outbox is empty."
        return "\n".join(
            f"#{m['id']} [{m.get('status','?')}] to {m['to']} — '{m['subject']}'"
            for m in items
        )

    tools = [
        Tool("draft_email", "Save an email as a draft (not sent).",
             obj(to=string("Recipient email address"),
                 subject=string("Subject line"),
                 body=string("Email body"),
                 required=["to", "subject", "body"]),
             draft_email),
        Tool("send_email", "Send an email (mocked — saved to local outbox).",
             obj(to=string("Recipient email address"),
                 subject=string("Subject line"),
                 body=string("Email body"),
                 required=["to", "subject", "body"]),
             send_email),
        Tool("list_outbox", "List drafted/sent emails.",
             obj(status=string("Filter: 'draft' or 'sent' (optional)")),
             list_outbox),
    ]
    agent = Agent("comms", SYSTEM, tools, llm, on_event=on_event)
    return {"agent": agent, "description": DESCRIPTION}
