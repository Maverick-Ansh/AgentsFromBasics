"""Phone control via a Telegram bot.

Setup (once):
  1. On Telegram, message @BotFather, send /newbot, follow the prompts.
  2. It gives you a token — put it in .env as TELEGRAM_BOT_TOKEN.
  3. Run:  python run.py telegram
  4. Open the t.me/<your_bot> link on your phone and start chatting.

Each chat gets its own short-term memory (conversation). Long-term memory and
the calendar/tasks/etc. stores are shared — it's still one assistant.
"""
import asyncio
import os

from ..app import build_system

WELCOME = (
    "👋 Hi! I'm your assistant, backed by a Manager agent and 5 specialists "
    "(research, calendar, tasks, booking, email).\n\n"
    "Try things like:\n"
    "• what's the latest on the Mars sample return mission\n"
    "• schedule a dentist appointment next Tuesday 9am\n"
    "• add a task to renew my passport\n"
    "• book a table for 2 tomorrow evening\n"
    "• remember that I prefer aisle seats"
)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN not set. Create a bot via @BotFather and put the "
            "token in your .env file."
        )

    # Imported here so `python run.py cli` doesn't require python-telegram-bot.
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    manager = build_system()  # one brain, shared across all chats
    conversations: dict[int, list] = {}  # chat_id -> short-term memory

    async def on_start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(WELCOME)

    async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        convo = conversations.setdefault(chat_id, [])
        convo.append({"role": "user", "content": update.message.text})

        # Show "typing…" while the agents work (LLM + tool calls take a moment).
        await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

        # manager.run is blocking (network calls), so run it off the event loop.
        loop = asyncio.get_running_loop()
        try:
            reply, _ = await loop.run_in_executor(None, manager.run, convo)
        except Exception as exc:  # noqa: BLE001
            reply = f"Something went wrong: {exc}"
        await update.message.reply_text(reply or "(no reply)")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("✅ Telegram bot running — message it from your phone. Ctrl-C to stop.")
    app.run_polling()
