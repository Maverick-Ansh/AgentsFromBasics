#!/usr/bin/env python3
"""Entry point.

    python run.py            # terminal chat (default)
    python run.py cli        # terminal chat
    python run.py telegram   # phone control via Telegram

Loads environment variables from a .env file if present.
"""
import os
import sys


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv is optional; env vars can be set however you like

    mode = sys.argv[1] if len(sys.argv) > 1 else "cli"
    if mode not in {"cli", "telegram"}:
        print("usage: python run.py [cli|telegram]")
        sys.exit(1)

    from afb import config

    if config.PROVIDER in ("anthropic", "claude"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print(
                "⚠️  ANTHROPIC_API_KEY is not set.\n"
                "    Copy .env.example to .env and add your key "
                "(from https://console.anthropic.com/),\n"
                "    or set AFB_PROVIDER=openai to run on a local/open-source model."
            )
            sys.exit(1)
        print(f"🔌 Model backend: Anthropic · {config.MODEL}")
    else:
        print(
            f"🔌 Model backend: {config.PROVIDER} · {config.OPENAI_MODEL} "
            f"@ {config.OPENAI_BASE_URL}"
        )

    if mode == "cli":
        from afb.interfaces.cli import main as run_cli
        run_cli()
    else:
        from afb.interfaces.telegram import main as run_telegram
        run_telegram()


if __name__ == "__main__":
    main()
