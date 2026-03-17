# 🧬 Self-Evolving AI Agent Patterns

> Battle-tested patterns from a production AI agent that has run **1,000+ autonomous cycles**, self-modified its own architecture, and recovered from catastrophic failures through self-diagnosis.

**This is not theory.** Every pattern was extracted from [JARVIS](https://tutuoai.com) — a real system running 24/7 on Claude API that autonomously modifies its own code, learns from outcomes, and compounds capability over time.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## ⚡ Try It Now

Get a self-evolving agent running in 60 seconds:

```bash
pip install anthropic pyyaml
export ANTHROPIC_API_KEY=your-key
cd examples/

# Run a complete self-evolving agent with tools, learning, and self-modification
python minimal_agent.py

# Or watch the evolve → verify → commit loop in action
python self_evolving_loop.py
```

The `minimal_agent.py` is a **complete, production-pattern agent** in 150 lines. It:
- Uses real tools (read/write files, run shell commands)
- Modifies its own system prompt to improve future behavior
- Records outcomes and learns from history across cycles
- Rebuilds its context every turn (the key pattern)

Set a custom task: `AGENT_TASK="Build a calculator module" python minimal_agent.py`

---

## 🎯 What's Inside

### Free Patterns (This Repo)

| Pattern | Description | Impact |
|---------|-------------|--------|
| [Context Engineering](docs/context-engineering.md) | Shape LLM behavior through input design, not output parsing | 🔥 **#1 most impactful** |
| [Immune System](docs/immune-system.md) | Make agents permanently resistant to encountered failures | 30% → 80% success rate |
| [Anti-Pattern Catalog](docs/anti-patterns.md) | 20+ real failures with root causes and fixes | Saves weeks of debugging |
| [Two-Paradigm Discipline](docs/two-paradigm.md) | Know when to use code vs LLM vs context control | Eliminates fragile parsing |
| [Context Manifest](examples/context-manifest.yaml) | Working config for profile-based context assembly | Copy-paste starter |
| [Tool Auto-Discovery](examples/tool-discovery.py) | Register tools without manual imports | Extensible tool system |

### 📊 Real Results

| Metric | Before These Patterns | After |
|--------|----------------------|-------|
| Cycle success rate | ~30% | **>80%** |
| Empty cycling (wasted budget) | 82 consecutive cycles, $180+ | **0 (eliminated)** |
| Self-modification safety | Manual review needed | **Automated verify + adversarial review** |
| Budget waste | $180+ in 3 hours | **<$5/hour** |
| Knowledge retention | Reset every session | **Persistent across restarts** |

---

## 🚀 Quick Start

### 1. Context Engineering (Start Here)

The single most important concept for production AI agents:

```
You don't control an LLM by parsing its output.
You control it by shaping its input.
```

**Bad pattern** (fragile, breaks constantly):
```python
response = llm.generate("Evaluate this code...")
if "success" in response.lower():
    handle_success()
elif "fail" in response.lower():
    handle_failure()
# What about "succeeded"? "failed partially"? "looks good"?
```

**Good pattern** (robust, works at scale):
```python
# Give the LLM a structured tool instead
tools = [{
    "name": "report_result",
    "input_schema": {
        "type": "object",
        "properties": {
            "judgment": {"type": "string", "enum": ["success", "failure", "partial"]},
            "evidence": {"type": "string"},
            "lesson": {"type": "string"}
        }
    }
}]
# The LLM calls the tool with structured data — no parsing needed
```

→ [Full Context Engineering Guide](docs/context-engineering.md)

### 2. The Immune System

Every failure becomes permanent immunity:

```markdown
## Anti-Pattern: Empty Cycling (discovered 2026-03-14)
- 82 cycles, $180+ burned, ZERO commits
- Pattern: Read files → assess → declare success → repeat
- Root cause: Context allowed "assessment" as valid work
- Fix: Added "Artifact-or-Nothing Rule" to agent context
- Result: Never happened again
```

After documenting 20+ anti-patterns, the agent has **permanent immunity** to entire classes of failures. This is the most underrated pattern in AI agent development.

→ [Immune System Guide](docs/immune-system.md)

### 3. Two-Paradigm Discipline

Before writing ANY code in an agent system, ask: "Should this be code at all?"

| Decision Type | Use | Example |
|---|---|---|
| **Mechanical** | Code | File exists? Test pass? HTTP status? |
| **Semantic** | LLM | Is this good? What should we do next? |
| **Behavioral** | Context Control | Change what the LLM sees, not what you filter |

The **#1 anti-pattern** in agent codebases: writing `if-elif` chains to handle semantic decisions that an LLM handles naturally.

→ [Two-Paradigm Guide](docs/two-paradigm.md)

---

## 📁 Repository Structure

```
├── docs/
│   ├── context-engineering.md    # Complete context engineering guide
│   ├── immune-system.md          # How to build failure immunity
│   ├── anti-patterns.md          # 20+ real failures documented
│   └── two-paradigm.md           # Code vs LLM vs Context discipline
├── examples/
│   ├── minimal_agent.py          # ⚡ Complete self-evolving agent (~150 lines, RUNNABLE)
│   ├── self_evolving_loop.py     # ⚡ Evolve → verify → commit loop (~100 lines, RUNNABLE)
│   ├── context-manifest.yaml     # Working context manifest config
│   ├── tool-discovery.py         # Auto-discovering tool registration
│   ├── immune-pattern.py         # Anti-pattern detection example
│   └── context-builder.py        # Minimal context builder implementation
├── pyproject.toml                # Project config (pip installable)
└── README.md
```

---

## 🏗️ Architecture (From Production)

```
┌─────────────────────────────────────────────┐
│              CONTEXT BUILDER                 │
│  Manifest → Generators → Purpose Profiles   │
├──────────────┬──────────────────────────────┤
│  EVOLUTION   │        GOAL WORK             │
│  ENGINE      │        (Agent Loop)          │
│  (Self-mod)  │        Task execution        │
├──────────────┴──────────────────────────────┤
│              TOOL SYSTEM                     │
│  Auto-discovered, constitution-gated        │
├─────────────────────────────────────────────┤
│         LEARNING & MEMORY                    │
│  Rewards → Episodic Memory → Strategy Eval  │
├─────────────────────────────────────────────┤
│            SAFETY LAYER                      │
│  Constitution → Verifier → Immune System    │
└─────────────────────────────────────────────┘
```

**Two execution paths:**
- **Evolution** — Agent modifies its own code. Changes verified mechanically (syntax, imports, tests) + adversarially (independent LLM review) before commit.
- **Goal Work** — Agent executes tasks toward measurable objectives. Tracked with thresholds and gradients.

---

## 💡 Key Insights

### 1. Context > Prompts
A "system prompt" is just a context document. The real skill is **context engineering** — deciding what information the LLM sees, in what order, at what detail level. This is the difference between a toy demo and a production agent.

### 2. LLMs Are Not Programs
Stop treating LLMs like functions with inputs and outputs. They're reasoning engines that operate on context. Control the context, and the right behavior emerges naturally — no parsing, no validation, no retry loops.

### 3. Self-Modification Is Safe (With Guardrails)
Our agent has made 500+ self-modifications to its own codebase. Zero catastrophic failures. The secret: mechanical verification (syntax, imports, tests) + adversarial review (independent LLM evaluates the diff) + constitution (hard rules that can never be violated).

### 4. Failures Are Assets
Every failure mode, once documented and injected into context, becomes **permanent immunity**. The agent literally cannot repeat a documented failure because the anti-pattern description is in its context. This is the most powerful learning mechanism we've found.

### 5. Budget Tracking Is Non-Negotiable
Without per-cycle cost tracking, agent costs grow silently until someone notices a $500 bill. Our agent tracks cost per cycle, enforces daily limits, and throttles/sleeps when approaching budget boundaries.

---

## 📚 Go Deeper — Premium Guides

The examples in this repo show you the **patterns**. The premium guides give you the **full production implementation** — battle-tested across 1,000+ autonomous cycles.

| Guide | What You Get | Price |
|-------|-------------|-------|
| [**Context Engineering — Complete Framework**](https://tutuoai.com) | 17,000+ word deep dive on manifest systems, purpose profiles, priority-based context trimming, generator architecture. The skill that makes everything else work. | **$8.99** |
| [**Self-Evolving Agent Blueprint**](https://tutuoai.com) | Complete architecture for agents that safely modify their own code: mechanical verification, adversarial LLM review, constitution constraints, rollback protocols. | **$19.99** |
| [**Tool & Function Calling Mastery**](https://tutuoai.com) | Auto-discovery patterns, write gates, tool registries, and the "tools as structured output" pattern that eliminates parsing forever. | **$6.99** |
| [**Multi-Agent Orchestration Patterns**](https://tutuoai.com) | How to spawn Actor/Critic/Strategist agents, manage sessions, and let LLMs decide the flow instead of hardcoding pipelines. | **$6.99** |
| [**Complete Bundle (All Skills + Future Updates)**](https://tutuoai.com) | Everything above + Reward Engineering, Immune System Implementation, and all future guides as they're released. | **$29.99** |

### Why Pay?

This repo gives you the **concepts** — enough to build a working agent (see `examples/minimal_agent.py`).

The premium guides give you the **production architecture** — the difference between a demo and a system that runs 24/7 for months without human intervention. They cover the hard parts: What happens when your agent modifies code that breaks itself? How do you prevent $180/hour budget waste? How do you build permanent immunity to failure modes?

Every guide is extracted from a real production system, not theory. **If you're building production AI agents, these will save you weeks.**

→ **[Browse all guides at tutuoai.com](https://tutuoai.com)**

---

## 🤝 About

Built by [TutuoAI](https://tutuoai.com) — we build AI agents that improve themselves. Our production system runs 24/7 on Claude API, autonomously modifying its own code, researching markets, and learning from every cycle.

**Star ⭐ this repo** if you find these patterns useful. It helps others discover them.

---

## License

MIT — use these patterns freely in your own projects.
