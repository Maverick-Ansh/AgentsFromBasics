"""Research specialist — searches and reads the live web.

This one uses REAL tools (keyless DuckDuckGo search + page fetching), so the
research is genuinely live. The tools are plain Python functions, exactly like
the mock tools in the other specialists — that's the point: a "real" tool and a
"mock" tool look identical to the agent.
"""
import re

from ..agent import Agent
from ..tools import Tool, integer, obj, string

DESCRIPTION = (
    "Researches anything on the live web: current events, facts, prices, "
    "product comparisons, 'look up / find out / what's the latest on ...'. "
    "Pass it a clear research question as the task."
)

SYSTEM = """You are the Research specialist.

Workflow:
1. Use web_search to find relevant sources for the question.
2. Use web_fetch to read the most promising 1-3 pages when you need detail
   beyond the snippets.
3. Synthesize a clear, accurate, concise answer.

Always cite the source URLs you actually used. If the web tools are
unavailable or return nothing, say so plainly instead of guessing. Return just
the answer the Manager needs — no preamble."""


def _web_search(query: str, max_results: int = 5) -> str:
    # The package was renamed from `duckduckgo_search` to `ddgs`; support both.
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "Web search unavailable: run `pip install ddgs`."
    try:
        with DDGS() as ddg:
            results = list(ddg.text(query, max_results=max_results))
    except Exception as exc:  # network blocked, rate limited, etc.
        return f"Web search failed: {exc}"
    if not results:
        return "No results found."
    lines = []
    for r in results:
        title = r.get("title", "")
        href = r.get("href") or r.get("url", "")
        body = r.get("body", "")
        lines.append(f"- {title}\n  {href}\n  {body}")
    return "\n".join(lines)


def _web_fetch(url: str, max_chars: int = 4000) -> str:
    try:
        import requests
    except ImportError:
        return "Fetching unavailable: run `pip install requests`."
    try:
        resp = requests.get(
            url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (afb-research)"}
        )
        resp.raise_for_status()
    except Exception as exc:
        return f"Failed to fetch {url}: {exc}"
    # Very crude HTML -> text. Good enough for reading article bodies.
    text = resp.text
    text = re.sub(r"(?is)<(script|style)\b.*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + " …[truncated]"
    return text or "(no readable text found on page)"


def build(llm, on_event=None):
    tools = [
        Tool(
            "web_search",
            "Search the web; returns the top results as title + URL + snippet.",
            obj(
                query=string("What to search for"),
                max_results=integer("How many results to return (default 5)"),
                required=["query"],
            ),
            _web_search,
        ),
        Tool(
            "web_fetch",
            "Fetch a single web page by URL and return its readable text.",
            obj(url=string("The full http(s) URL to fetch"), required=["url"]),
            _web_fetch,
        ),
    ]
    agent = Agent("research", SYSTEM, tools, llm, on_event=on_event)
    return {"agent": agent, "description": DESCRIPTION}
