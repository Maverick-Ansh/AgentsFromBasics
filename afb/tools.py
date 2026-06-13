"""What a *tool* is.

A tool is just four things:
  - name          a short identifier the model uses to call it
  - description   tells the model WHEN to use it (this is prompt-engineering!)
  - input_schema  JSON Schema describing the arguments the model must provide
  - handler       the Python function that actually does the work

The model only ever sees name + description + input_schema. It decides to call
a tool; our agent loop (agent.py) runs `handler` and feeds the result back.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., str]

    def spec(self) -> dict:
        """The exact shape Claude's API wants in its `tools` list."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def run(self, **kwargs) -> str:
        """Execute the tool. Always returns a string (what the model reads back).

        We catch exceptions and return them as text instead of crashing — the
        model can often recover (retry with different args, or tell the user).
        """
        try:
            result = self.handler(**kwargs)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the model
            return f"ERROR running tool '{self.name}': {exc}"
        return result if isinstance(result, str) else str(result)


# A couple of tiny helpers so specialist files read cleanly when declaring
# argument schemas.
def obj(**properties) -> dict:
    """Build an object JSON-schema. Mark required fields with required=[...]."""
    required = properties.pop("required", [])
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def string(description: str) -> dict:
    return {"type": "string", "description": description}


def integer(description: str) -> dict:
    return {"type": "integer", "description": description}
