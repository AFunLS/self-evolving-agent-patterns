# CLAUDE.md — self-evolving-agent-patterns

> This file IS the pattern. It's a working example of Context Engineering — the #1 most impactful pattern in this repo. Claude Code reads this file automatically to understand your project.

## What This Project Is

Battle-tested patterns for building production AI agents that modify their own code, learn from outcomes, and compound capability over time. Every pattern was extracted from JARVIS — a real system running 24/7 on Claude API.

## Project Structure

```
self-evolving-agent-patterns/
├── examples/               # Runnable code — start here
│   ├── minimal_agent.py    # Complete self-evolving agent in 150 lines
│   ├── self_evolving_loop.py  # Evolve → verify → commit loop
│   ├── claudemd-generator.py  # Auto-generate CLAUDE.md for any Python project
│   ├── context-manifest.yaml  # Working config for context assembly
│   └── tool-discovery.py   # Tool auto-registration pattern
├── docs/                   # Deep-dive pattern documentation
│   ├── context-engineering.md   # 🔥 #1 pattern — shape behavior through input
│   ├── immune-system.md         # Self-healing failure resistance
│   ├── anti-patterns.md         # 20+ real failures with root causes
│   ├── two-paradigm.md          # When to use code vs LLM vs context
│   ├── agent-memory-learning.md # Reward-driven learning systems
│   └── build-ai-agent-tools.md  # Tool system design
├── src/agent_patterns/     # Pip-installable library
│   ├── agent.py            # Core Agent class with tool loop
│   └── tools.py            # File + shell tool implementations
├── dist/                   # Built packages
└── pyproject.toml          # Package config (pip install .)
```

## Key Commands

```bash
# Run the minimal agent example
cd examples && python minimal_agent.py

# Run with a custom task
AGENT_TASK="Build a calculator" python examples/minimal_agent.py

# Generate CLAUDE.md for any project
python examples/claudemd-generator.py /path/to/project

# Install as a library
pip install .

# Run tests (if contributing)
pytest
```

## Architecture Principles

1. **Context Engineering > Prompt Engineering** — Control what the LLM sees (input), not what it says (output). Never parse LLM output with regex.
2. **Two-Paradigm Discipline** — Use code for mechanical decisions, LLM for semantic judgment. Never mix them.
3. **Immune System Pattern** — Every failure becomes a permanent behavioral guardrail. The system gets stronger from what breaks it.
4. **Skills as Knowledge** — Reusable patterns stored as readable files, loaded on-demand. Knowledge compounds.

## Code Style

- Python 3.11+, type hints on public APIs
- 4-space indentation, Google-style docstrings
- Functions under 50 lines, files under 300 lines
- No external ML dependencies — pure Python + anthropic SDK

## Contributing

See CONTRIBUTING.md. Key rule: every pattern must come from real operational experience, not theory.
