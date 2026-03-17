---
layout: default
title: "Claude API Agent Tutorial: Build an Autonomous AI Agent with Tool Use (2025)"
description: "Complete tutorial for building an autonomous AI agent using Claude's API with tool use, context engineering, and self-modification. Production-ready Python code included."
---

# Claude API Agent Tutorial: Build an Autonomous AI Agent with Tool Use (2025)

*Build a real autonomous agent — not a chatbot wrapper. Production Python code from a system running 24/7 on Claude.*

**What you'll build:** An AI agent that uses Claude's API with native tool use to autonomously execute tasks, modify files, run commands, browse the web, and learn from outcomes.

**Prerequisites:** Python 3.10+, Anthropic API key, basic understanding of LLMs.

**Time:** 30 minutes to a working agent. A weekend to production-ready.

---

## Table of Contents

1. [Why Claude for Agents?](#why-claude-for-agents)
2. [Architecture Overview](#architecture-overview)
3. [Setting Up the Project](#setting-up-the-project)
4. [The Agent Loop](#the-agent-loop)
5. [Defining Tools](#defining-tools)
6. [Context Engineering](#context-engineering)
7. [Multi-Turn Tool Use](#multi-turn-tool-use)
8. [Error Handling & Safety](#error-handling--safety)
9. [Adding Memory](#adding-memory)
10. [Going Autonomous](#going-autonomous)
11. [Production Checklist](#production-checklist)

---

## Why Claude for Agents?

Claude (specifically Opus and Sonnet) excels at agent tasks for three reasons:

1. **Native tool use** — Claude's API has first-class support for function calling. No JSON-hacking prompt tricks needed.
2. **Long context window** — 200K tokens means your agent can hold massive context: system prompts, conversation history, tool results, and memory — all at once.
3. **Instruction following** — Claude is exceptionally good at following complex behavioral instructions, making context engineering highly effective.

We've run a production agent on Claude's API for 1,000+ autonomous cycles. Here's what we learned.

---

## Architecture Overview

Every Claude-based agent has the same core structure:

```
┌─────────────────────────────────────────┐
│              System Prompt               │
│  (Identity + Rules + Context + Tools)    │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│            Claude API Call               │
│  messages=[system, user, assistant...]   │
│  tools=[read_file, run_command, ...]     │
└────────────────┬────────────────────────┘
                 │
          ┌──────┴──────┐
          │             │
     Tool Use      Text Response
          │             │
     Execute        Return to
     Tool           User/Loop
          │
     Append Result
     to Messages
          │
     Loop Back
     to API Call
```

The key insight: **the agent loop is just a while loop that keeps calling Claude until it stops requesting tools.**

---

## Setting Up the Project

```bash
mkdir my-agent && cd my-agent
python3 -m venv venv && source venv/bin/activate
pip install anthropic pyyaml
```

```python
# agent.py
import anthropic
import json
import subprocess
import os

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
MODEL = "claude-sonnet-4-20250514"  # Or claude-opus-4-6 for max capability
```

---

## The Agent Loop

This is the core of every Claude agent. It's simpler than you think:

```python
def agent_loop(system_prompt: str, user_task: str, tools: list, max_turns: int = 10):
    """Core agent loop — keeps calling Claude until task is done."""
    
    messages = [{"role": "user", "content": user_task}]
    
    for turn in range(max_turns):
        # Call Claude
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        
        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Extract tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Execute the tool
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            
            # Append assistant response + tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        
        elif response.stop_reason == "end_turn":
            # Claude is done — extract final text
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text
    
    return "Max turns reached"
```

**Key pattern:** The `messages` list grows with each turn. Claude sees the full conversation history — including its own previous tool calls and their results. This is how it maintains context across multi-step tasks.

---

## Defining Tools

Claude's API uses JSON Schema for tool definitions. Here are production-ready tools:

```python
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Use for source code, configs, docs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file with new content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "run_command",
        "description": "Execute a shell command. For git, pip, tests, system queries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the internet. Returns titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    },
]
```

**Tool implementation:**

```python
def execute_tool(name: str, inputs: dict) -> str:
    """Execute a tool and return the result as a string."""
    
    if name == "read_file":
        try:
            with open(inputs["path"], "r") as f:
                content = f.read()
            # Truncate large files
            if len(content) > 10000:
                content = content[:5000] + "\n\n... [truncated] ...\n\n" + content[-2000:]
            return content
        except Exception as e:
            return f"Error: {e}"
    
    elif name == "write_file":
        os.makedirs(os.path.dirname(inputs["path"]) or ".", exist_ok=True)
        with open(inputs["path"], "w") as f:
            f.write(inputs["content"])
        return f"Wrote {len(inputs['content'])} bytes to {inputs['path']}"
    
    elif name == "run_command":
        try:
            result = subprocess.run(
                inputs["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
            if len(output) > 10000:
                output = output[:5000] + "\n... [truncated] ...\n" + output[-2000:]
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out (30s)"
    
    return f"Unknown tool: {name}"
```

### Tool Design Tips (From Production)

1. **Always truncate output.** A single `cat` on a large file can blow your context window. 10K chars is a good limit.
2. **Return errors as strings, not exceptions.** Claude handles errors gracefully — let it see the error message and adapt.
3. **Tool descriptions matter.** Claude decides which tool to use based on the description. Be specific about when to use each tool.
4. **Add "when to use" guidance.** "Use for source code, configs, docs" helps Claude make better tool choices.

---

## Context Engineering

This is the **highest-leverage** part of building a Claude agent. The system prompt is your agent's identity, knowledge, and behavioral programming.

### The Four-Layer Context Architecture

```python
def build_system_prompt(task_context: str = "") -> str:
    """Build a layered system prompt for the agent."""
    
    layers = []
    
    # Layer 1: Identity — Who is the agent?
    layers.append("""
# Identity
You are an autonomous AI agent. You execute tasks by using tools — 
reading files, running commands, writing code, searching the web.
You work independently. Don't ask for permission — execute directly.
""")
    
    # Layer 2: Behavioral Rules — How should it act?
    layers.append("""
# Rules
- Execute directly. Don't ask "should I...?" — just do it.
- Verify your work. "I made the change" isn't done. 
  "Here's the test output proving it works" is done.
- If a tool call fails, try a different approach.
- Produce artifacts: commits, files, test results. 
  Assessment without action is waste.
""")
    
    # Layer 3: Dynamic Context — What does it know right now?
    layers.append(f"""
# Current Context
{task_context}
""")
    
    # Layer 4: On-Demand Knowledge — Skills loaded as needed
    layers.append("""
# Available Skills
If you need specialized knowledge, read the relevant skill file:
- skills/debugging.md — How to debug complex issues
- skills/testing.md — How to write and run tests
- skills/deployment.md — How to deploy to production
""")
    
    return "\n".join(layers)
```

### Context Engineering Anti-Patterns

| ❌ Anti-Pattern | ✅ Better Approach |
|---|---|
| Dump entire codebase into prompt | Include architecture overview, load files on-demand |
| Vague instructions ("be helpful") | Specific behavioral rules with examples |
| Static context only | Dynamic generators that compute fresh state each cycle |
| Everything at max priority | Priority tiers — identity is critical, skills are on-demand |

### The Two-Paradigm Discipline

The most important architectural decision in an agent system:

| Problem Type | Solution |
|---|---|
| Deterministic/mechanical | **Code** — file exists? test pass? parse JSON? |
| Semantic judgment | **LLM** — is this code good? what should I do next? |
| Changing agent behavior | **Context** — modify the system prompt, not the code |

**The cardinal sin:** Writing code to parse LLM output. If you find yourself writing regex on Claude's responses, you've made an architectural mistake. Use structured tool calls instead.

---

## Multi-Turn Tool Use

Real tasks require multiple tool calls. Here's how to handle complex workflows:

```python
# Example: "Fix the failing test in tests/test_auth.py"

# Turn 1: Claude calls read_file("tests/test_auth.py")
# Turn 2: Claude calls read_file("src/auth.py") — reads the source
# Turn 3: Claude calls run_command("pytest tests/test_auth.py -v")  
# Turn 4: Claude calls write_file("src/auth.py", fixed_code)
# Turn 5: Claude calls run_command("pytest tests/test_auth.py -v")
# Turn 6: Claude responds: "Fixed. The issue was..."
```

**Token management for multi-turn:**

Each turn re-sends the full message history. With a 200K context window, you have plenty of room, but costs add up. Strategies:

1. **Truncate tool results** — 10K chars per result is usually enough
2. **Summarize after N turns** — Replace old messages with a summary
3. **Use cheaper models for routine tasks** — Sonnet for simple operations, Opus for complex reasoning

```python
def maybe_compact_messages(messages: list, max_chars: int = 100000) -> list:
    """Summarize old messages if history gets too long."""
    total_chars = sum(len(str(m)) for m in messages)
    
    if total_chars < max_chars:
        return messages
    
    # Keep first (system context) and last 4 messages
    # Summarize the middle
    old_messages = messages[1:-4]
    summary = summarize_with_llm(old_messages)  # Use cheaper model
    
    return [messages[0], {"role": "user", "content": f"[Previous context summary: {summary}]"}] + messages[-4:]
```

---

## Error Handling & Safety

Production agents need guardrails:

```python
# Safety: Restrict file operations to project directory
ALLOWED_PATHS = [os.path.abspath(".")]

def is_safe_path(path: str) -> bool:
    """Ensure file operations stay within the project."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(p) for p in ALLOWED_PATHS)

# Safety: Command blocklist
BLOCKED_COMMANDS = ["rm -rf /", "sudo", "> /dev/sda", "mkfs"]

def is_safe_command(cmd: str) -> bool:
    """Block obviously dangerous commands."""
    return not any(blocked in cmd for blocked in BLOCKED_COMMANDS)

# Constitution: Things the agent must never do
CONSTITUTION = [
    "Never delete the main database",
    "Never modify production config without tests",
    "Never expose API keys in committed code",
]
```

### The Constitution Pattern

Hard constraints that override everything else. Checked before every write operation:

```python
def check_constitution(operation: str, target: str) -> tuple[bool, str]:
    """Check if an operation violates any constitutional rule."""
    
    protected_files = ["config/production.yaml", ".env", "database/main.db"]
    
    if operation == "write" and target in protected_files:
        return False, f"Constitutional violation: {target} is protected"
    
    return True, "OK"
```

---

## Adding Memory

Agents without memory repeat mistakes. Here's a minimal but effective memory system:

```python
import json
from datetime import datetime

class AgentMemory:
    """Simple append-only memory with retrieval."""
    
    def __init__(self, path: str = "memory.jsonl"):
        self.path = path
    
    def remember(self, event_type: str, content: str, metadata: dict = None):
        """Store a memory."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "content": content,
            "metadata": metadata or {},
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def recall(self, query: str, limit: int = 5) -> list:
        """Retrieve relevant memories (simple keyword match)."""
        memories = []
        if not os.path.exists(self.path):
            return memories
        
        with open(self.path) as f:
            for line in f:
                entry = json.loads(line)
                # Simple relevance: check if query words appear
                if any(word.lower() in entry["content"].lower() 
                       for word in query.split()):
                    memories.append(entry)
        
        return memories[-limit:]  # Most recent matches
    
    def inject_into_context(self, task: str) -> str:
        """Build a memory section for the system prompt."""
        relevant = self.recall(task, limit=5)
        if not relevant:
            return ""
        
        lines = ["## Relevant Past Experience"]
        for m in relevant:
            lines.append(f"- [{m['type']}] {m['content']}")
        return "\n".join(lines)

# Usage in agent loop:
memory = AgentMemory()

# After each cycle, remember the outcome
memory.remember("task_complete", "Fixed auth test — issue was expired token handling")
memory.remember("failure", "Tried to pip install on Python 3.8 — needs 3.10+")

# Before next cycle, inject relevant memories
task = "Fix the login endpoint"
context = memory.inject_into_context(task)
system_prompt = build_system_prompt(task_context=context)
```

### Memory Patterns (From Production)

| Memory Type | What to Store | When to Use |
|---|---|---|
| **Episodic** | "I did X and Y happened" | Learn from specific outcomes |
| **Procedural** | "To deploy, run X then Y then Z" | Reusable workflows |
| **Failure** | "X failed because Y" | Avoid repeating mistakes |
| **Strategic** | "Approach A works better than B for this type of task" | Decision-making |

---

## Going Autonomous

The final step: make your agent run continuously without human intervention.

```python
import time
import traceback

def autonomous_loop(interval: int = 60):
    """Run the agent continuously, processing tasks from a queue."""
    
    memory = AgentMemory()
    
    while True:
        try:
            # Get next task (from file, API, queue, etc.)
            task = get_next_task()  # You implement this
            
            if task is None:
                time.sleep(interval)
                continue
            
            # Build context with memory
            context = memory.inject_into_context(task)
            system_prompt = build_system_prompt(task_context=context)
            
            # Run the agent
            result = agent_loop(system_prompt, task, TOOLS)
            
            # Record outcome
            memory.remember("task_complete", f"Task: {task}\nResult: {result[:500]}")
            
            # Budget check
            if get_daily_spend() > DAILY_BUDGET_LIMIT:
                print("Budget limit reached, sleeping until tomorrow")
                sleep_until_midnight()
            
        except Exception as e:
            memory.remember("error", f"Crashed on task '{task}': {traceback.format_exc()[:500]}")
            time.sleep(interval)  # Back off on errors

if __name__ == "__main__":
    autonomous_loop()
```

### Self-Modification (Advanced)

The most powerful pattern: let the agent modify its own code.

```python
# Add to system prompt:
SELF_MODIFY_RULES = """
## Self-Modification
You can modify your own code using write_file and run_command.
After every modification:
1. Run tests: run_command("pytest -x")
2. If tests fail: run_command("git checkout -- .") to revert
3. If tests pass: run_command("git commit -am 'agent: <description>'")

You must NEVER modify:
- The constitution checker
- The budget manager
- The memory store's append function
"""
```

This is what makes an agent truly self-evolving — it can improve its own tools, fix its own bugs, and expand its own capabilities.

---

## Production Checklist

Before running your agent in production:

- [ ] **Budget limits** — Hard cap on daily API spend
- [ ] **File safety** — Restrict operations to project directory
- [ ] **Command safety** — Block destructive commands
- [ ] **Constitution** — Protected files that can never be modified
- [ ] **Output truncation** — Cap tool results at 10K chars
- [ ] **Timeout** — 30s default for commands, with override option
- [ ] **Error recovery** — Catch exceptions, log them, continue
- [ ] **Memory** — Store outcomes, inject relevant history
- [ ] **Monitoring** — Log every API call, track costs
- [ ] **Tests** — Run test suite before and after modifications
- [ ] **Git safety** — Never force-push, never delete history
- [ ] **Verification** — Agent must prove its work (test output, not claims)

---

## Next Steps

This tutorial gives you a production-ready foundation. To go deeper:

- **[Context Engineering for LLM Agents](https://tutuoai.gumroad.com/l/context-engineering)** — 9 named patterns for engineering what your agent sees
- **[Agent Self-Evolution Framework](https://tutuoai.gumroad.com/l/agent-self-evolution)** — 5-layer system for agents that modify their own code
- **[Complete Agent Engineering Bundle](https://tutuoai.gumroad.com/l/agent-engineering-bundle)** — All 7 frameworks, 45% off

Or explore the free patterns on [GitHub](https://github.com/AFunLS/self-evolving-agent-patterns).

---

*Built by [TutuoAI](https://tutuoai.com) — extracted from a real AI system that modifies its own code, learns from outcomes, and runs autonomously 24/7.*
