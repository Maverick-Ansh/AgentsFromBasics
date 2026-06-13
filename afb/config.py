"""Central configuration.

Everything tunable lives here so you don't go hunting through the code.
Values can be overridden with environment variables.
"""
import os

# Which model backend the agents run on:
#   "anthropic" — Claude via the Anthropic API (needs ANTHROPIC_API_KEY)
#   "openai"    — ANY OpenAI-compatible server: Ollama, vLLM, LM Studio,
#                 llama.cpp, LocalAI, ... — i.e. how you run an open-source model.
# Because every model call goes through afb/llm.py, this switch is the ONLY
# change needed; no agent code is touched.
PROVIDER = os.environ.get("AFB_PROVIDER", "anthropic").lower()

# --- Anthropic backend ---
MODEL = os.environ.get("AFB_MODEL", "claude-sonnet-4-6")

# --- OpenAI-compatible backend (open-source / local models) ---
# Defaults target a local Ollama server. Point these at any compatible endpoint
# (e.g. LM Studio's http://localhost:1234/v1, or a vLLM server).
OPENAI_BASE_URL = os.environ.get("AFB_OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_MODEL = os.environ.get("AFB_OPENAI_MODEL", "llama3.1")
OPENAI_API_KEY = os.environ.get("AFB_OPENAI_API_KEY", "ollama")  # local servers ignore it

# Upper bound on tokens per model response. 4096 is plenty for chat + tool use.
MAX_TOKENS = int(os.environ.get("AFB_MAX_TOKENS", "4096"))

# Safety rail: max times an agent will loop (call tools) before giving up on
# one request. Stops a confused agent from looping forever (and burning money).
MAX_STEPS = int(os.environ.get("AFB_MAX_STEPS", "12"))

# Where durable data lives: long-term memory + the mock calendar/tasks/etc.
# Defaults to a `data/` folder in the project root (gitignored).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("AFB_DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
