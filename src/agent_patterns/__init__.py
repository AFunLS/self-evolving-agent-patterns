"""
agent-patterns — Battle-tested patterns for building self-evolving AI agents.

Extracted from a production system with 1,000+ autonomous cycles.
https://github.com/AFunLS/self-evolving-agent-patterns

Quick start:
    from agent_patterns import Agent, tool

    @tool("greet", "Greet someone by name")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    agent = Agent(model="claude-sonnet-4-20250514")
    agent.add_tool(greet)
    agent.run("Greet the user warmly")

For premium guides on context engineering, self-evolution, multi-agent
orchestration, and more: https://tutuoai.com
"""

__version__ = "0.1.0"

from agent_patterns.core import Agent
from agent_patterns.tools import tool

__all__ = ["Agent", "tool", "__version__"]
