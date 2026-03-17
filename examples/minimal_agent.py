#!/usr/bin/env python3
"""
Minimal Self-Evolving Agent — A complete, runnable agent in ~150 lines.

This agent can:
  1. Execute tasks using real tools (read/write files, run shell commands)
  2. Modify its own system prompt to improve future behavior
  3. Record what worked and learn from outcomes across cycles

Run it:
    pip install anthropic pyyaml
    export ANTHROPIC_API_KEY=your-key
    python minimal_agent.py

For the full production implementation with multi-agent orchestration,
constitution safety, and immune system: https://tutuoai.com
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import anthropic

# --- Configuration -----------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"
PROMPT_FILE = Path("agent_prompt.md")          # The agent's self-modifiable context
REWARD_LOG = Path("rewards.jsonl")             # Append-only learning history
MAX_TURNS = 10                                  # Safety limit per cycle

# --- Tools: what the agent can DO --------------------------------------------
# Each tool is a plain function. The agent sees the schema and calls them by name.

TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's contents. Use to inspect code, configs, or data.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path to read"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Create or overwrite a file. Use to produce artifacts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_command",
        "description": "Execute a shell command and return stdout+stderr.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Shell command"}},
            "required": ["command"],
        },
    },
    {
        "name": "modify_prompt",
        "description": "Append a new rule or insight to the agent's own system prompt. "
        "This permanently changes future behavior — the core of self-evolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "addition": {
                    "type": "string",
                    "description": "Text to append to the system prompt (a new rule or lesson)",
                },
            },
            "required": ["addition"],
        },
    },
    {
        "name": "record_result",
        "description": "Record the outcome of this cycle for future learning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "judgment": {"type": "string", "enum": ["success", "failure", "partial"]},
                "lesson": {"type": "string", "description": "What to remember"},
            },
            "required": ["judgment", "lesson"],
        },
    },
]


def handle_tool(name: str, input: dict) -> str:
    """Dispatch a tool call to the right handler. Returns a string result."""
    if name == "read_file":
        try:
            return Path(input["path"]).read_text()
        except Exception as e:
            return f"Error: {e}"

    elif name == "write_file":
        Path(input["path"]).parent.mkdir(parents=True, exist_ok=True)
        Path(input["path"]).write_text(input["content"])
        return f"Wrote {len(input['content'])} chars to {input['path']}"

    elif name == "run_command":
        try:
            r = subprocess.run(
                input["command"], shell=True, capture_output=True, text=True, timeout=30
            )
            return (r.stdout + r.stderr)[:5000] or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: command timed out (30s)"

    elif name == "modify_prompt":
        # Self-evolution: the agent rewrites its own context
        current = PROMPT_FILE.read_text() if PROMPT_FILE.exists() else ""
        PROMPT_FILE.write_text(current + f"\n\n## Learned ({datetime.now():%Y-%m-%d %H:%M})\n{input['addition']}\n")
        return f"✅ System prompt updated — this will affect all future cycles."

    elif name == "record_result":
        entry = {**input, "timestamp": datetime.now().isoformat()}
        with open(REWARD_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return f"Recorded: {input['judgment']} — {input['lesson']}"

    return f"Unknown tool: {name}"


# --- Context Builder ---------------------------------------------------------
# The #1 pattern: control LLM behavior through INPUT, not output parsing.

def build_system_prompt() -> str:
    """Assemble the agent's identity + learned knowledge + recent history."""
    base = (
        "You are a self-evolving AI agent. You execute tasks using tools, learn from "
        "outcomes, and improve your own behavior by modifying your system prompt.\n\n"
        "## Rules\n"
        "- Use tools to act, don't just talk about acting\n"
        "- After completing a task, call record_result with your judgment and lesson\n"
        "- If you discover a reusable insight, call modify_prompt to remember it\n"
        "- Be concrete: produce files, run commands, verify results\n"
    )
    # Layer on self-modified knowledge (the evolution accumulator)
    if PROMPT_FILE.exists():
        base += f"\n## Your Accumulated Knowledge\n{PROMPT_FILE.read_text()}\n"

    # Layer on recent reward history (what worked and what didn't)
    if REWARD_LOG.exists():
        lines = REWARD_LOG.read_text().strip().split("\n")
        recent = lines[-5:]  # Last 5 outcomes
        base += "\n## Recent History (learn from this)\n"
        for line in recent:
            entry = json.loads(line)
            base += f"- [{entry['judgment']}] {entry['lesson']}\n"

    return base


# --- Agent Loop --------------------------------------------------------------
# The core cycle: send message → get tool calls → execute → feed back → repeat

def run_agent(task: str) -> None:
    """Run one agent cycle: given a task, use tools to complete it."""
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var
    messages = [{"role": "user", "content": task}]

    print(f"\n{'='*60}")
    print(f"🧬 Agent Cycle — Task: {task}")
    print(f"{'='*60}\n")

    for turn in range(MAX_TURNS):
        # Call the LLM with our engineered context + tools
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=build_system_prompt(),  # Rebuilt every turn (captures self-mods!)
            tools=TOOLS,
            messages=messages,
        )

        # Process the response: text blocks and tool calls
        tool_used = False
        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"💭 {block.text[:200]}")
            elif block.type == "tool_use":
                tool_used = True
                print(f"🔧 {block.name}({json.dumps(block.input)[:100]})")
                result = handle_tool(block.name, block.input)
                print(f"   → {result[:150]}")
                # Feed the tool result back to the LLM
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}],
                })

        # If the LLM stopped without calling tools, it's done
        if response.stop_reason == "end_turn" and not tool_used:
            print(f"\n✅ Cycle complete (turn {turn + 1}/{MAX_TURNS})")
            return

    print(f"\n⚠️  Hit turn limit ({MAX_TURNS})")


# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":
    # Example: give the agent a real task
    task = os.environ.get("AGENT_TASK", (
        "Create a Python file called 'hello_evolved.py' that prints a greeting. "
        "Then run it to verify it works. Finally, record what you learned."
    ))
    run_agent(task)
    print("\n🧬 Self-evolving agent cycle complete.")
    print("   Run again — it remembers what it learned!")
    print("   Check agent_prompt.md for accumulated knowledge.")
    print("   Check rewards.jsonl for outcome history.\n")
    # For the full production implementation: https://tutuoai.com
