"""
Core Agent class — a minimal but production-pattern AI agent.

This is the main entry point for agent-patterns. It implements the
context-engineering pattern: control LLM behavior through INPUT, not output parsing.

Usage:
    from agent_patterns import Agent

    agent = Agent(model="claude-sonnet-4-20250514")
    result = agent.run("Create a hello world script and verify it works")

For self-evolution (the agent modifies its own behavior):
    agent = Agent(model="claude-sonnet-4-20250514", self_evolving=True)

Full production guide: https://tutuoai.com
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

from agent_patterns.tools import BUILTIN_TOOLS, ToolDef


class Agent:
    """
    A minimal, production-pattern AI agent with tool use and optional self-evolution.

    Key patterns implemented:
    - Context engineering: system prompt rebuilt every turn
    - Tool use: real tools with automatic dispatch
    - Self-evolution: agent can modify its own prompt (opt-in)
    - Learning: outcomes logged for future context injection
    """

    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-20250514",
        system_prompt: str | None = None,
        max_turns: int = 10,
        self_evolving: bool = False,
        prompt_file: str | Path = "agent_prompt.md",
        reward_log: str | Path = "rewards.jsonl",
        max_output: int = 10000,
    ):
        self.model = model
        self._base_prompt = system_prompt or self._default_prompt()
        self.max_turns = max_turns
        self.self_evolving = self_evolving
        self.prompt_file = Path(prompt_file)
        self.reward_log = Path(reward_log)
        self.max_output = max_output
        self._tools: dict[str, ToolDef] = {}
        self._client = anthropic.Anthropic()

        # Register built-in tools
        for t in BUILTIN_TOOLS:
            self._tools[t.name] = t

        # Add self-evolution tools if enabled
        if self_evolving:
            self._add_evolution_tools()

    def add_tool(self, tool_def: ToolDef) -> "Agent":
        """Register a tool. Chainable: agent.add_tool(t1).add_tool(t2)"""
        self._tools[tool_def.name] = tool_def
        return self

    def run(self, task: str, *, verbose: bool = True) -> dict[str, Any]:
        """
        Run one agent cycle: given a task, use tools to complete it.

        Returns a dict with keys: turns, messages, final_text
        """
        messages: list[dict] = [{"role": "user", "content": task}]
        final_text = ""

        if verbose:
            print(f"\n{'='*60}")
            print(f"🧬 Agent Cycle — Task: {task[:80]}")
            print(f"{'='*60}\n")

        for turn in range(self.max_turns):
            response = self._client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._build_system_prompt(),
                tools=[t.to_api_schema() for t in self._tools.values()],
                messages=messages,
            )

            tool_used = False
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    final_text = block.text
                    if verbose:
                        print(f"💭 {block.text[:300]}")

                elif block.type == "tool_use":
                    tool_used = True
                    tool_def = self._tools.get(block.name)
                    if verbose:
                        print(f"🔧 {block.name}({json.dumps(block.input)[:100]})")

                    if tool_def:
                        result = tool_def.call(**block.input)
                    else:
                        result = f"Error: unknown tool '{block.name}'"

                    result = result[:self.max_output]
                    if verbose:
                        print(f"   → {result[:200]}")

                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": block.id, "content": result}
                        ],
                    })

            if response.stop_reason == "end_turn" and not tool_used:
                if verbose:
                    print(f"\n✅ Cycle complete (turn {turn + 1}/{self.max_turns})")
                break

        return {"turns": turn + 1, "messages": messages, "final_text": final_text}

    def _build_system_prompt(self) -> str:
        """
        Rebuild the system prompt every turn.

        This is THE key pattern: context engineering. The agent sees
        its base identity + accumulated knowledge + recent history.
        """
        prompt = self._base_prompt

        # Layer on self-modified knowledge
        if self.self_evolving and self.prompt_file.exists():
            knowledge = self.prompt_file.read_text().strip()
            if knowledge:
                prompt += f"\n\n## Your Accumulated Knowledge\n{knowledge}\n"

        # Layer on recent reward history
        if self.reward_log.exists():
            try:
                lines = self.reward_log.read_text().strip().split("\n")
                recent = lines[-5:]
                prompt += "\n## Recent History (learn from this)\n"
                for line in recent:
                    entry = json.loads(line)
                    prompt += f"- [{entry.get('judgment', '?')}] {entry.get('lesson', '?')}\n"
            except Exception:
                pass  # Non-critical — don't crash on corrupt history

        return prompt

    def _add_evolution_tools(self) -> None:
        """Add self-evolution tools: modify_prompt and record_result."""

        def modify_prompt(addition: str) -> str:
            current = self.prompt_file.read_text() if self.prompt_file.exists() else ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.prompt_file.write_text(
                current + f"\n\n## Learned ({timestamp})\n{addition}\n"
            )
            return "✅ System prompt updated — this will affect all future cycles."

        def record_result(judgment: str, lesson: str) -> str:
            entry = {"judgment": judgment, "lesson": lesson, "timestamp": datetime.now().isoformat()}
            with open(self.reward_log, "a") as f:
                f.write(json.dumps(entry) + "\n")
            return f"Recorded: {judgment} — {lesson}"

        self._tools["modify_prompt"] = ToolDef(
            name="modify_prompt",
            description=(
                "Append a new rule or insight to the agent's own system prompt. "
                "This permanently changes future behavior — the core of self-evolution."
            ),
            handler=modify_prompt,
            parameters={"addition": {"type": "string", "description": "Text to append"}},
        )

        self._tools["record_result"] = ToolDef(
            name="record_result",
            description="Record the outcome of this cycle for future learning.",
            handler=record_result,
            parameters={
                "judgment": {
                    "type": "string",
                    "enum": ["success", "failure", "partial"],
                    "description": "How did this cycle go?",
                },
                "lesson": {"type": "string", "description": "What to remember"},
            },
        )

    @staticmethod
    def _default_prompt() -> str:
        return (
            "You are a self-evolving AI agent. You execute tasks using tools, learn from "
            "outcomes, and improve your own behavior by modifying your system prompt.\n\n"
            "## Rules\n"
            "- Use tools to act, don't just talk about acting\n"
            "- After completing a task, call record_result with your judgment and lesson\n"
            "- If you discover a reusable insight, call modify_prompt to remember it\n"
            "- Be concrete: produce files, run commands, verify results\n"
        )
