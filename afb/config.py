"""Central configuration.

Everything tunable lives here so you don't go hunting through the code.
Values can be overridden with environment variables.
"""
import os

# The model the agents run on. You asked to start on Claude Sonnet.
# Because every model call goes through afb/llm.py, switching to an
# open-source model later is a change to that ONE file, not this string.
MODEL = os.environ.get("AFB_MODEL", "claude-sonnet-4-6")

# Upper bound on tokens per model response. 4096 is plenty for chat + tool use.
MAX_TOKENS = int(os.environ.get("AFB_MAX_TOKENS", "4096"))

# Safety rail: max times an agent will loop (call tools) before giving up on
# one request. Stops a confused agent from looping forever (and burning money).
MAX_STEPS = int(os.environ.get("AFB_MAX_STEPS", "12"))

# Where durable data lives: long-term memory + the mock calendar/tasks/etc.
# Defaults to a `data/` folder in the project root (gitignored).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("AFB_DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
