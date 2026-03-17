# Changelog

All notable changes to `agent-patterns` will be documented in this file.

## [0.1.0] — 2025-03-16

### 🎉 Initial Release

**Core Framework**
- `Agent` class with tool use, context engineering, and optional self-evolution
- `@tool` decorator for easy tool registration
- Built-in tools: `read_file`, `write_file`, `run_command`
- Self-evolution tools: `modify_prompt`, `record_result`

**CLI**
- `agent-patterns run "task"` — Run agent with custom task
- `agent-patterns demo` — Built-in demo with random task
- `agent-patterns doctor` — Check environment setup
- `agent-patterns version` — Print version

**Documentation**
- Context Engineering guide — shape LLM behavior through input design
- Immune System pattern — permanent failure resistance
- Anti-Pattern Catalog — 20+ real failures with fixes
- Two-Paradigm Discipline — code vs LLM vs context control
- Agent Memory & Learning patterns

**Examples**
- `minimal_agent.py` — Complete self-evolving agent in 150 lines
- `self_evolving_loop.py` — Evolve → verify → commit loop
- `context-manifest.yaml` — Profile-based context assembly
- `tool-discovery.py` — Auto-registering tool system

### Patterns Extracted From
Every pattern in this release was extracted from **JARVIS** — a production AI agent that has run 1,000+ autonomous cycles, self-modified its own architecture, and recovered from catastrophic failures through self-diagnosis. Running 24/7 on Claude API.

[0.1.0]: https://github.com/AFunLS/self-evolving-agent-patterns/releases/tag/v0.1.0
