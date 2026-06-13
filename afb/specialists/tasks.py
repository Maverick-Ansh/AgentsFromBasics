"""Tasks specialist — MOCK to-do list stored on disk (data/tasks.json).

Swap these handlers for the Google Tasks API later without touching the agent.
"""
from datetime import datetime

from ..agent import Agent
from ..store import Collection
from ..tools import Tool, integer, obj, string

DESCRIPTION = (
    "Manages the user's to-do list: add / list / complete / delete tasks. "
    "Use for 'remind me to', 'add a task', 'what's on my list', 'mark X done'. "
    "(Mock task store locally; real Google Tasks swaps in behind these tools.)"
)

SYSTEM = """You are the Tasks specialist managing the user's to-do list.

- Call `now` if you need today's date to interpret a due date.
- Keep titles short and actionable.
- After any change, confirm it and include the task id. Return just the result
  the Manager needs."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M (%A)")


def build(llm, on_event=None):
    col = Collection("tasks")

    def add_task(title, due=None, priority=None):
        t = col.add({"title": title, "due": due,
                     "priority": priority or "normal", "status": "open"})
        return (f"Added task #{t['id']}: '{title}'"
                + (f" (due {due})" if due else "")
                + (f" [{priority}]" if priority and priority != "normal" else ""))

    def list_tasks(status=None):
        items = col.all()
        if status:
            items = [t for t in items if t.get("status") == status]
        if not items:
            return "No tasks."
        return "\n".join(
            f"#{t['id']} [{t.get('status','open')}] {t['title']}"
            + (f" (due {t['due']})" if t.get("due") else "")
            + (f" !{t['priority']}" if t.get("priority") not in (None, "normal") else "")
            for t in items
        )

    def complete_task(task_id):
        t = col.update(task_id, status="done")
        return f"Completed task #{task_id}." if t else f"No task #{task_id}."

    def delete_task(task_id):
        ok = col.delete(task_id)
        return f"Deleted task #{task_id}." if ok else f"No task #{task_id}."

    tools = [
        Tool("now", "Get the current date and time.", obj(), lambda: _now()),
        Tool("add_task", "Add a new task to the to-do list.",
             obj(title=string("What needs doing"),
                 due=string("Due date 'YYYY-MM-DD' (optional)"),
                 priority=string("'low', 'normal', or 'high' (optional)"),
                 required=["title"]),
             add_task),
        Tool("list_tasks", "List tasks, optionally filtered by status.",
             obj(status=string("Filter: 'open' or 'done' (optional)")),
             list_tasks),
        Tool("complete_task", "Mark a task as done by id.",
             obj(task_id=integer("The task id"), required=["task_id"]),
             complete_task),
        Tool("delete_task", "Delete a task by id.",
             obj(task_id=integer("The task id"), required=["task_id"]),
             delete_task),
    ]
    agent = Agent("tasks", SYSTEM, tools, llm, on_event=on_event)
    return {"agent": agent, "description": DESCRIPTION}
