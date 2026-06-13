"""afb — Agents From Basics.

A small multi-agent system built from scratch (no agent framework) so you can
see exactly how the pieces fit together:

    llm.py      the one place we talk to the model (swap-in seam for OSS models)
    tools.py    what a "tool" is
    memory.py   short-term (conversation) + long-term (durable) memory
    agent.py    the agent loop — the heart of everything
    manager.py  the orchestrator that delegates to specialists
    specialists/  the 5 domain agents (research, calendar, tasks, booking, comms)
"""
