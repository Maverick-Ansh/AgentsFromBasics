"""The Manager (orchestrator) agent.

The Manager is *just an Agent* whose tools are the OTHER agents. When the model
running the Manager decides "this needs research", it calls the `ask_research`
tool — whose handler runs the Research agent's own loop and returns its answer
as the tool result. Agents calling agents, built from the same primitives.

  user ──▶ Manager.run (its loop)
              │  calls ask_calendar(task="…")
              ▼
           Calendar agent.run_task (ITS loop, ITS tools)
              │  returns text
              ▼
           …Manager continues, maybe calls another specialist, then replies.
"""
from .agent import Agent
from .tools import Tool, obj, string

MANAGER_SYSTEM = """You are the Manager — the orchestrator of a small team of \
specialist agents. You talk to the user and get things done by DELEGATING to \
the right specialist. You do not do the domain work yourself.

Your specialists (call them with the matching ask_ tool):
{roster}

How to work:
- For anything in a specialist's domain, delegate with its ask_ tool. You may
  call several specialists in sequence for a multi-part request (e.g. research
  a restaurant, then book it, then add it to the calendar).
- Specialists CANNOT see this conversation. Each task you send must be a clear,
  self-contained instruction with every detail they need (dates, names, the
  user's choice, etc.).
- Use `recall` at the start when the user's saved preferences might matter, and
  use `remember` when the user states a durable preference or fact worth
  keeping for next time.
- After delegating, write ONE short, friendly reply to the user summarizing
  what happened. It may be read on a phone, so keep it concise and skip tool
  mechanics and ids unless they're useful.
- If a message needs no specialist (a greeting, a clarifying question), just
  reply directly."""


def build_manager(llm, specialists: dict, long_term_memory, on_event=None) -> Agent:
    """Wire the specialists in as delegate tools and return the Manager agent."""

    delegate_tools = []
    for key, spec in specialists.items():
        # A factory so each lambda captures its OWN agent (avoids the classic
        # late-binding closure bug where they'd all point at the last agent).
        def make_handler(agent):
            return lambda task: agent.run_task(task)

        delegate_tools.append(
            Tool(
                name=f"ask_{key}",
                description=spec["description"],
                input_schema=obj(
                    task=string(
                        "A clear, self-contained instruction for the specialist, "
                        "including all details it needs."
                    ),
                    required=["task"],
                ),
                handler=make_handler(spec["agent"]),
            )
        )

    # The Manager also gets the long-term memory tools so it can personalize.
    memory_tools = [
        Tool(
            "remember",
            "Save a durable fact or preference about the user for future "
            "sessions (e.g. 'prefers morning meetings', 'allergic to nuts').",
            obj(
                text=string("The fact/preference to remember"),
                tags={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional keyword tags for easier recall",
                },
                required=["text"],
            ),
            lambda text, tags=None: long_term_memory.remember(text, tags),
        ),
        Tool(
            "recall",
            "Look up durable facts/preferences you've saved about the user.",
            obj(query=string("What to look up"), required=["query"]),
            lambda query: long_term_memory.recall(query),
        ),
    ]

    roster = "\n".join(
        f"- ask_{key}: {spec['description']}" for key, spec in specialists.items()
    )
    system = MANAGER_SYSTEM.format(roster=roster)

    return Agent(
        "manager",
        system,
        delegate_tools + memory_tools,
        llm,
        on_event=on_event,
    )
