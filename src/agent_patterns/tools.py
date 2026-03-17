"""
Tool registration utilities for agent-patterns.

The `@tool` decorator turns any Python function into an LLM-callable tool
with automatic schema generation.

Usage:
    from agent_patterns import tool

    @tool("read_file", "Read a file's contents")
    def read_file(path: str) -> str:
        return open(path).read()

    @tool("calculator", "Evaluate a math expression")
    def calculator(expression: str) -> str:
        return str(eval(expression))  # In production, use a sandbox!
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


# Python type → JSON Schema type mapping
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


@dataclass
class ToolDef:
    """A tool definition that can be sent to Claude's tool_use API."""

    name: str
    description: str
    handler: Callable[..., str]
    parameters: dict = field(default_factory=dict)

    def to_api_schema(self) -> dict:
        """Convert to Anthropic API tool schema format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": list(self.parameters.keys()),
            },
        }

    def call(self, **kwargs) -> str:
        """Execute the tool handler and return string result."""
        try:
            result = self.handler(**kwargs)
            return str(result) if result is not None else "(no output)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"


def _infer_schema(func: Callable) -> dict:
    """Infer JSON Schema properties from function type hints."""
    sig = inspect.signature(func)
    hints = func.__annotations__
    properties = {}

    for name, param in sig.parameters.items():
        if name == "return":
            continue
        hint = hints.get(name, str)
        json_type = _TYPE_MAP.get(hint, "string")
        prop: dict[str, Any] = {"type": json_type}

        # Use parameter default as description hint if it's a string
        if param.default is not inspect.Parameter.empty and isinstance(param.default, str):
            prop["description"] = param.default

        properties[name] = prop

    return properties


def tool(name: str, description: str) -> Callable[[Callable], ToolDef]:
    """
    Decorator that converts a function into a ToolDef.

    Usage:
        @tool("my_tool", "What this tool does")
        def my_tool(arg1: str, arg2: int) -> str:
            return f"Result: {arg1} {arg2}"

    The decorated object is a ToolDef instance with .call(), .to_api_schema(), etc.
    """

    def decorator(func: Callable) -> ToolDef:
        params = _infer_schema(func)
        return ToolDef(
            name=name,
            description=description,
            handler=func,
            parameters=params,
        )

    return decorator


# --- Built-in tools (common patterns) ----------------------------------------

@tool("read_file", "Read a file's contents. Use to inspect code, configs, or data.")
def read_file(path: str) -> str:
    """Read a file and return its contents."""
    from pathlib import Path as P
    try:
        return P(path).read_text()
    except Exception as e:
        return f"Error reading {path}: {e}"


@tool("write_file", "Create or overwrite a file. Use to produce artifacts.")
def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    from pathlib import Path as P
    P(path).parent.mkdir(parents=True, exist_ok=True)
    P(path).write_text(content)
    return f"Wrote {len(content)} chars to {path}"


@tool("run_command", "Execute a shell command and return stdout+stderr (30s timeout).")
def run_command(command: str) -> str:
    """Execute a shell command with a 30-second timeout."""
    import subprocess
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = (r.stdout + r.stderr)[:10000]
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out (30s)"


BUILTIN_TOOLS = [read_file, write_file, run_command]
