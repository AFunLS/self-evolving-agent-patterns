---
layout: default
title: How to Build an AI Agent with Tools — Complete Guide (2025)
description: Step-by-step guide to building an AI agent with tool use. Real production code from a self-evolving system running 1000+ autonomous cycles.
---

# How to Build an AI Agent with Tools — Complete Guide

> This guide shows you how to build an AI agent that uses tools (file operations, shell commands, web browsing) with real production patterns. Not theory — every line comes from a system that has run **1,000+ autonomous cycles** autonomously.

## Why Most AI Agent Tutorials Are Wrong

Most tutorials show you:
```python
# ❌ The toy pattern everyone teaches
tools = [{"name": "search", "description": "Search the web"}]
response = client.messages.create(tools=tools, ...)
```

This works for demos. It falls apart in production because:

1. **No tool discovery** — tools are hardcoded, not discoverable
2. **No error recovery** — one bad tool call crashes everything  
3. **No learning** — the agent makes the same mistakes forever
4. **No context management** — the agent forgets everything between turns

Here's how to build it properly.

## The Architecture That Actually Works

```
┌─────────────────────────────────────────┐
│              Agent Loop                  │
│                                          │
│  1. Build Context (every turn!)          │
│  2. Call LLM with tools                  │
│  3. Execute tool calls                   │
│  4. Record outcomes                      │
│  5. Rebuild context → next turn          │
│                                          │
│  Key insight: Context is rebuilt EVERY    │
│  turn, not just at the start.            │
└─────────────────────────────────────────┘
```

## Step 1: The Tool Registry (Auto-Discovery)

Don't hardcode your tools. Build a registry that discovers them:

```python
import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable, Any

@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable[..., Any]

class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name] = tool
    
    def get_api_tools(self) -> list[dict]:
        """Convert to Claude/OpenAI tool format."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in self.tools.values()
        ]
    
    def execute(self, name: str, args: dict) -> str:
        """Execute a tool by name, return result as string."""
        tool = self.tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        try:
            result = tool.handler(**args)
            return str(result)
        except Exception as e:
            return f"Error executing {name}: {e}"
    
    def auto_discover(self, package_path: str):
        """Scan a directory for tool modules."""
        for importer, name, _ in pkgutil.iter_modules([package_path]):
            module = importlib.import_module(f"tools.{name}")
            if hasattr(module, "register_tools"):
                module.register_tools(self)
```

**Why this matters:** New tools are added by dropping a file in `tools/`. No imports to update, no hardcoded lists. The agent's capabilities grow without changing core code.

## Step 2: Core Tools (File + Shell + Web)

These three tools cover 90% of what an agent needs:

```python
import subprocess
import httpx

def register_core_tools(registry: ToolRegistry):
    # Read files
    registry.register(Tool(
        name="read_file",
        description="Read the contents of a file. Use for source code, configs, docs.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to file"}
            },
            "required": ["path"]
        },
        handler=lambda path: open(path).read()
    ))
    
    # Write files
    registry.register(Tool(
        name="write_file",
        description="Write content to a file. Creates parent dirs if needed.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to file"},
                "content": {"type": "string", "description": "Content to write"}
            },
            "required": ["path", "content"]
        },
        handler=lambda path, content: (
            __import__('pathlib').Path(path).parent.mkdir(parents=True, exist_ok=True),
            __import__('pathlib').Path(path).write_text(content)
        )[-1]
    ))
    
    # Shell commands
    registry.register(Tool(
        name="run_command",
        description="Execute a shell command. Use for git, pip, tests, system queries.",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"}
            },
            "required": ["command"]
        },
        handler=lambda command: subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        ).stdout[:10000] or subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        ).stderr[:5000]
    ))
```

## Step 3: The Agent Loop (The Key Pattern)

This is where most tutorials go wrong. They build the loop wrong. Here's the pattern that works in production:

```python
import anthropic

def run_agent(task: str, registry: ToolRegistry, max_turns: int = 10):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": task}]
    
    for turn in range(max_turns):
        # KEY PATTERN: Rebuild context every turn
        system_prompt = build_context()  # Dynamic, not static!
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=registry.get_api_tools(),
            messages=messages,
        )
        
        # Check if done (no tool use)
        if response.stop_reason == "end_turn":
            final_text = "".join(
                b.text for b in response.content if b.type == "text"
            )
            return final_text
        
        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = registry.execute(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
                
                # Record outcome for learning
                record_outcome(block.name, block.input, result)
        
        # Add assistant response + tool results to conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    
    return "Max turns reached"
```

## Step 4: Context That Improves Over Time

The secret sauce: your system prompt isn't static. It's rebuilt every turn with fresh information:

```python
def build_context() -> str:
    """Build dynamic context — the agent's 'perception' of the world."""
    sections = []
    
    # Identity (stable)
    sections.append(read_file("context/identity.md"))
    
    # Recent outcomes (dynamic — changes every turn)
    recent = load_recent_outcomes(limit=5)
    if recent:
        sections.append("## Recent Outcomes\n" + format_outcomes(recent))
    
    # Current task state (dynamic)
    if os.path.exists("state/current_task.md"):
        sections.append(read_file("state/current_task.md"))
    
    # Failure patterns (learned from history)
    failures = get_repeated_failures()
    if failures:
        sections.append(
            "## Known Failure Patterns — Avoid These\n" + 
            "\n".join(f"- {f}" for f in failures)
        )
    
    return "\n\n---\n\n".join(sections)
```

**This is the most important pattern in the entire guide.** An agent that rebuilds its context every turn can learn from mistakes within a single session. An agent with a static prompt repeats the same errors forever.

## Step 5: Outcome Recording (The Learning Loop)

```python
import json
from datetime import datetime

def record_outcome(tool_name: str, args: dict, result: str):
    """Record tool outcomes for learning."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "args": args,
        "result_preview": result[:200],
        "success": "error" not in result.lower(),
    }
    with open("state/outcomes.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

def get_repeated_failures(threshold: int = 2) -> list[str]:
    """Detect tools/patterns that keep failing."""
    if not os.path.exists("state/outcomes.jsonl"):
        return []
    
    failures = {}
    for line in open("state/outcomes.jsonl"):
        entry = json.loads(line)
        if not entry["success"]:
            key = f"{entry['tool']}({list(entry['args'].keys())})"
            failures[key] = failures.get(key, 0) + 1
    
    return [
        f"{k} has failed {v} times — try a different approach"
        for k, v in failures.items() if v >= threshold
    ]
```

## Complete Working Example

See [minimal_agent.py](../examples/minimal_agent.py) for a complete, runnable agent that puts all these patterns together in ~150 lines.

## Going Further

These patterns are extracted from a production system. The free examples cover the fundamentals. For production-grade implementations:

- **[Context Engineering Deep Dive](context-engineering.md)** — The most important skill for agent builders
- **[Two-Paradigm Architecture](two-paradigm.md)** — When to use code vs. LLM for different decisions
- **[Immune System Patterns](immune-system.md)** — Self-diagnosis and recovery
- **[Anti-Patterns Guide](anti-patterns.md)** — 15 mistakes that kill agents in production

For complete production frameworks with battle-tested code: visit [TutuoAI](https://tutuoai.com).

---

*Built by [TutuoAI](https://tutuoai.com) — Production AI Agent Engineering*
