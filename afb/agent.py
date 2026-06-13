"""An Agent, from scratch.

THIS IS THE HEART OF THE WHOLE PROJECT. Read it once and you understand agents.

An agent is four things:  a system prompt + some tools + an LLM + a loop.

The loop (this is what "agentic" means):
    1. Send the conversation + the tool specs to the model.
    2. The model replies. If it's a normal answer (stop_reason == "end_turn"),
       we're done — return the text.
    3. If instead the model asks to use tools (stop_reason == "tool_use"), we
       run each requested tool, append the results to the conversation, and go
       back to step 1.

Every "agent framework" you've heard of is, at its core, a fancier version of
this loop. No magic.
"""
from . import config
from .tools import Tool

# An "llm" here is anything with a `.complete(system, messages, tools)` method
# that returns an object with `.content` (a list of blocks) and `.stop_reason`.
# Both backends in afb/llm.py satisfy this — that's the whole point of the seam.


def _noop(*_args, **_kwargs):  # default event sink
    pass


class Agent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[Tool],
        llm,
        max_steps: int = config.MAX_STEPS,
        on_event=None,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = {t.name: t for t in tools}
        self.llm = llm
        self.max_steps = max_steps
        # on_event lets the interface show what's happening (which tool, etc.).
        self.on_event = on_event or _noop

    def run(self, messages: list) -> tuple[str, list]:
        """Run the loop over a conversation. Mutates and returns `messages`.

        Returns (final_text, messages).
        """
        tool_specs = [t.spec() for t in self.tools.values()]

        for _step in range(self.max_steps):
            response = self.llm.complete(
                self.system_prompt, messages, tool_specs or None
            )

            # Record the assistant's turn VERBATIM (text + any tool_use blocks).
            # The block objects must be passed back as-is on the next turn.
            messages.append({"role": "assistant", "content": response.content})

            # Not asking for a tool? Then it's the final answer.
            if response.stop_reason != "tool_use":
                text = "".join(
                    b.text for b in response.content if b.type == "text"
                )
                return text, messages

            # The model wants to call one or more tools. Run them all, then
            # send every result back in a single user message.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                self.on_event(
                    "tool_call", agent=self.name, tool=block.name, input=block.input
                )
                tool = self.tools.get(block.name)
                if tool is None:
                    output = f"ERROR: no such tool '{block.name}'"
                else:
                    output = tool.run(**block.input)
                self.on_event(
                    "tool_result", agent=self.name, tool=block.name, output=output
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,  # MUST match the tool_use id
                        "content": output,
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        return "(stopped: hit the max-steps safety limit before finishing)", messages

    def run_task(self, task: str) -> str:
        """One-shot helper used by specialists: take an instruction, return text.

        The manager delegates to a specialist by calling this with a task
        string; the specialist runs its own private loop and hands back a
        plain-text result.
        """
        text, _ = self.run([{"role": "user", "content": task}])
        return text
