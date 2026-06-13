# Agents From Basics

A small **multi-agent assistant built from scratch** — no agent framework — so you
can read every line and understand exactly how AI agents work. One **Manager**
agent orchestrates **5 specialists** (research, calendar, tasks, booking, email).
Talk to it in your terminal or **from your phone via Telegram**.

It runs on **Claude Sonnet** out of the box, but every model call goes through
one thin file (`afb/llm.py`), so you can run it on an **open-source model**
(Ollama / vLLM / LM Studio / …) by setting a single env var — no agent code
changes. See [Run on an open-source model](#run-on-an-open-source-model).

---

## The one idea you need: what *is* an agent?

An agent is just **four things plus a loop**:

```
agent = system prompt  +  tools  +  an LLM  +  a loop
```

The loop (this is the entire "magic" of agents — see `afb/agent.py`):

```
1. Send the conversation + the list of tools to the model.
2. The model replies.
     • If it's a normal answer  → done, return the text.
     • If it asks to use a tool → run the tool, append the result to the
       conversation, and GO BACK TO STEP 1.
```

That's it. Everything else is detail. LangChain, CrewAI, etc. are all elaborate
versions of this loop — here it's ~40 readable lines.

---

## Architecture

```
                       ┌──────────────────┐
   you ───────────────▶│   Manager agent  │  decides WHO should handle this,
   (CLI / Telegram)    │  (orchestrator)  │  delegates, then replies to you
                       └────────┬─────────┘
        ask_research  ask_calendar  ask_tasks  ask_booking  ask_comms
              │            │           │           │            │
              ▼            ▼           ▼           ▼            ▼
          Research     Calendar     Tasks      Booking       Comms
           agent        agent       agent       agent        agent
              │            │           │           │            │
         web_search    create_event add_task  search_avail  send_email
         web_fetch     list_events  list_...  make_booking  draft_email
                       update/delete complete  cancel        list_outbox
              └────────────┴───────────┴───────────┴────────────┘
                     shared: long-term MEMORY + on-disk stores
```

The Manager's "tools" **are the specialists**. When it calls `ask_calendar`, that
handler runs the Calendar agent's *own* loop and returns its answer. Agents
calling agents — built from the same primitive everything else uses.

---

## Concept → file map

| You want to understand… | Read this file |
|---|---|
| **The agent loop** (the heart) | `afb/agent.py` |
| **What a tool is** | `afb/tools.py` |
| **How memory works** | `afb/memory.py` |
| **The orchestrator / delegation** | `afb/manager.py` |
| **The one place we call the model** (swap seam) | `afb/llm.py` |
| **A specialist + its tools** | `afb/specialists/calendar.py` (et al.) |
| **How it's all wired together** | `afb/app.py` |
| **Persistence (the mock data store)** | `afb/store.py` |
| **Phone control** | `afb/interfaces/telegram.py` |

---

## How memory works (you asked!)

Two deliberately separate layers (`afb/memory.py`):

- **Short-term memory** — the running list of messages in the current
  conversation. This *is* the model's working context; we send it on every
  turn. It lives in the interface (CLI keeps one list; Telegram keeps one per
  chat) and disappears when the process stops.

- **Long-term memory** — durable facts saved to disk (`data/memory.json`) that
  survive restarts. The Manager writes with `remember` ("user prefers aisle
  seats") and reads with `recall`. This is what makes it feel like the
  assistant *knows you* across days.

  > Recall here is simple keyword matching — honest and easy to read. The
  > standard upgrade is **semantic search**: embed each memory as a vector and
  > return the nearest ones to the query. That's a drop-in replacement for
  > `LongTermMemory.recall()`; nothing else changes.

---

## Quickstart (terminal)

```bash
# 1. Install dependencies (a virtualenv is recommended)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
#   then edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Chat
python run.py
```

The terminal interface **prints every tool call** so you can watch the
orchestration happen:

```
you> book a table for 2 tomorrow evening and put it on my calendar

   · [manager] ask_booking({"task": "Book a restaurant table for 2 for ..."})
   · [booking] now({})
   · [booking] search_availability({"kind": "restaurant", "party_size": 2})
   · [booking] make_booking({"name": "Blue Door", "when": "2026-06-14 19:00"})
   · [manager] ask_calendar({"task": "Add 'Dinner at Blue Door' on 2026-06-14 ..."})
   · [calendar] create_event({"title": "Dinner at Blue Door", "start": "..."})

assistant> Done — booked Blue Door for 2 tomorrow at 7pm (simulated) and added
it to your calendar. Want me to set a reminder too?
```

Try:
- `what's the latest on <topic>` (real web research)
- `add a task to renew my passport by July 1, high priority`
- `schedule a dentist appointment next Tuesday at 9am`
- `email alex@example.com that I'm running 10 minutes late`
- `remember that I prefer morning meetings` → then later `what do you know about me?`

---

## Run on an open-source model

The whole point of the `afb/llm.py` seam: switch from Claude to a local
open-source model **without touching any agent code**. Any OpenAI-compatible
server works — Ollama, vLLM, LM Studio, llama.cpp, LocalAI. The seam translates
the codebase's Anthropic-shaped messages/tools into the OpenAI format and back,
so `afb/agent.py` and every specialist stay identical.

Easiest path — **Ollama**:

```bash
# 1. Install Ollama (https://ollama.com), then pull a tool-capable model:
ollama pull llama3.1          # qwen2.5 and mistral-nemo also work well

# 2. In .env, point afb at it:
#      AFB_PROVIDER=openai
#      AFB_OPENAI_MODEL=llama3.1
#      AFB_OPENAI_BASE_URL=http://localhost:11434/v1   (the default)

# 3. Run exactly as before — no ANTHROPIC_API_KEY needed:
python run.py
```

It prints which backend is active on startup, e.g.
`🔌 Model backend: openai · llama3.1 @ http://localhost:11434/v1`.

Point `AFB_OPENAI_BASE_URL` at any compatible server (a vLLM endpoint, or LM
Studio's `http://localhost:1234/v1`) and set `AFB_OPENAI_MODEL` to match.

> **Tool-calling quality varies by model.** Multi-agent delegation leans hard on
> tool use, so pick a model trained for it (llama3.1, qwen2.5, mistral-nemo).
> Small models may call the wrong tool or skip tools — a model limitation, not a
> code one. Switch back to Claude anytime with `AFB_PROVIDER=anthropic`.

---

## Control it from your phone (Telegram)

1. On Telegram, message **@BotFather** → `/newbot` → follow the prompts.
2. It gives you a token. Put it in `.env` as `TELEGRAM_BOT_TOKEN=...`.
3. Run the bot:
   ```bash
   python run.py telegram
   ```
4. Open the `t.me/<your_bot>` link on your phone and start chatting.

Each chat has its own short-term memory; long-term memory and the
calendar/tasks/etc. are shared — it's the same assistant, reachable from
anywhere.

> For always-on phone access, run `python run.py telegram` on a machine that
> stays up (a cheap VPS, a Raspberry Pi, or a container). It uses long-polling,
> so no public URL or webhook is required.

---

## The "mock now, real later" seams

Everything a real integration would need is already shaped correctly — only the
function bodies are mocked. To go live, you reimplement handlers; **agents and
prompts don't change.**

- **Google Calendar / Tasks** → `afb/specialists/calendar.py`,
  `afb/specialists/tasks.py`. Today they read/write local JSON. Swap the handler
  bodies for the Google Calendar / Tasks API (OAuth via `google-auth-oauthlib`,
  client via `google-api-python-client`). The tool *names and schemas* stay the
  same, so the model behaves identically.
- **Booking** → `afb/specialists/booking.py` returns simulated options. Replace
  with a real provider (OpenTable, a flights/hotels API, etc.).
- **Email** → `afb/specialists/comms.py` saves to a local outbox. Replace
  `send_email` with SMTP or the Gmail API.
- **Open-source model** → `afb/llm.py` — **already implemented.** Set
  `AFB_PROVIDER=openai` to run on Ollama / vLLM / LM Studio / any
  OpenAI-compatible server (see [Run on an open-source model](#run-on-an-open-source-model)).
  Nothing else in the codebase changes.

---

## Project layout

```
AgentsFromBasics/
├── run.py                      # entry point: python run.py [cli|telegram]
├── requirements.txt
├── .env.example                # copy to .env, add your keys
├── afb/
│   ├── config.py               # model id, limits, data dir
│   ├── llm.py                  # ← the model seam (swap OSS models here)
│   ├── tools.py                # ← what a tool is
│   ├── memory.py               # ← short-term + long-term memory
│   ├── store.py                # tiny JSON persistence
│   ├── agent.py                # ← the agent loop (the heart)
│   ├── manager.py              # ← the orchestrator
│   ├── app.py                  # wires everything together
│   ├── specialists/
│   │   ├── research.py         # real web search + fetch
│   │   ├── calendar.py         # mock calendar
│   │   ├── tasks.py            # mock to-do list
│   │   ├── booking.py          # simulated bookings
│   │   └── comms.py            # mock email
│   └── interfaces/
│       ├── cli.py              # terminal chat (shows orchestration)
│       └── telegram.py         # phone control
└── data/                       # created at runtime (gitignored)
```

---

## Ideas to extend it

- Wire **real Google Calendar/Tasks** behind the existing tools.
- Swap `recall()` for **vector/semantic memory**.
- Add **streaming** in `llm.py` so replies appear token-by-token.
- Add a new specialist (Weather? Finance? Notes?) — copy a specialist file,
  give it tools, add one line in `afb/app.py`.
- Try different **open-source models** (`AFB_OPENAI_MODEL`) or a hosted vLLM
  endpoint (`AFB_OPENAI_BASE_URL`).
- Add **human-in-the-loop approval** before "send email" / "make booking" fires.

Built to be read. Start with `afb/agent.py`.
