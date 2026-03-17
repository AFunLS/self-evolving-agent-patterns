---
layout: default
title: AI Agent Memory & Learning System — Production Patterns (2025)
description: How to build memory and learning into AI agents. Episodic memory, outcome tracking, failure detection, and self-improvement patterns from production.
---

# AI Agent Memory & Learning System — Production Patterns

> How to build an AI agent that learns from its mistakes, remembers past actions, and improves over time. Real patterns from a production system with 1,000+ autonomous cycles.

## The Problem: Stateless Agents Are Useless

Most AI agents are goldfish. Every conversation starts fresh. They:
- Repeat the same mistakes endlessly
- Can't build on previous work
- Have no concept of "this approach failed before"
- Lose all progress between sessions

Here's how to fix that with three memory systems that work together.

## Architecture: Three Memory Layers

```
┌─────────────────────────────────────────┐
│           Memory Architecture            │
│                                          │
│  Layer 1: Outcome History (JSONL)        │
│  → What happened? Tool calls + results   │
│  → Cheap, append-only, always grows      │
│                                          │
│  Layer 2: Episodic Memory               │
│  → What did I learn? Key-value insights  │
│  → Searchable by relevance              │
│                                          │
│  Layer 3: Strategy Rankings              │
│  → What works? Success rates by approach │
│  → Automatically ranks strategies        │
│                                          │
│  All three feed into context building    │
│  → Agent sees its own history each turn  │
└─────────────────────────────────────────┘
```

## Layer 1: Outcome History

The simplest and most important memory. Log every action and its result:

```python
import json
from datetime import datetime
from pathlib import Path

class OutcomeHistory:
    def __init__(self, path: str = "state/outcomes.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def record(self, action: str, args: dict, result: str, success: bool):
        entry = {
            "ts": datetime.now().isoformat(),
            "action": action,
            "args_summary": str(args)[:200],
            "result_preview": result[:500],
            "success": success,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def get_recent(self, n: int = 10) -> list[dict]:
        """Get last N outcomes."""
        if not self.path.exists():
            return []
        lines = self.path.read_text().strip().split("\n")
        return [json.loads(line) for line in lines[-n:]]
    
    def get_failure_patterns(self, threshold: int = 2) -> list[str]:
        """Find actions that repeatedly fail."""
        if not self.path.exists():
            return []
        
        failures: dict[str, int] = {}
        for line in open(self.path):
            entry = json.loads(line)
            if not entry["success"]:
                key = entry["action"]
                failures[key] = failures.get(key, 0) + 1
        
        return [
            f"⚠️ {action} has failed {count} times — try different approach"
            for action, count in failures.items()
            if count >= threshold
        ]
```

**Why JSONL?** Append-only is crash-safe. No database needed. Easy to inspect with `tail -f`. Grows linearly. Perfect for agents.

## Layer 2: Episodic Memory

Outcome history is raw data. Episodic memory is **distilled knowledge** — lessons learned, patterns discovered, insights gained:

```python
class EpisodicMemory:
    def __init__(self, path: str = "state/memories.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def store(self, content: str, tags: list[str] = None):
        """Store a lesson or insight."""
        entry = {
            "ts": datetime.now().isoformat(),
            "content": content,
            "tags": tags or [],
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Simple keyword search across memories."""
        if not self.path.exists():
            return []
        
        query_words = set(query.lower().split())
        scored = []
        
        for line in open(self.path):
            entry = json.loads(line)
            content_words = set(entry["content"].lower().split())
            tag_words = set(w for t in entry.get("tags", []) for w in t.lower().split())
            
            # Score by word overlap
            score = len(query_words & (content_words | tag_words))
            if score > 0:
                scored.append((score, entry))
        
        scored.sort(key=lambda x: -x[0])
        return [entry for _, entry in scored[:limit]]
    
    def consolidate(self, llm_client, max_entries: int = 100):
        """When memory gets large, ask LLM to consolidate old entries."""
        if not self.path.exists():
            return
        
        entries = [json.loads(line) for line in open(self.path)]
        if len(entries) <= max_entries:
            return
        
        # Take oldest half, ask LLM to summarize
        old = entries[:len(entries) // 2]
        new = entries[len(entries) // 2:]
        
        summary = llm_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"Consolidate these {len(old)} memories into 5-10 key insights. "
                           f"Preserve actionable lessons, discard noise.\n\n"
                           + "\n".join(e["content"] for e in old)
            }]
        ).content[0].text
        
        # Replace file with consolidated + new
        consolidated = {
            "ts": datetime.now().isoformat(),
            "content": f"[CONSOLIDATED from {len(old)} memories] {summary}",
            "tags": ["consolidated"],
        }
        
        with open(self.path, "w") as f:
            f.write(json.dumps(consolidated) + "\n")
            for entry in new:
                f.write(json.dumps(entry) + "\n")
```

## Layer 3: Strategy Rankings

The most powerful layer. Track which *approaches* succeed and fail:

```python
class StrategyTracker:
    def __init__(self, path: str = "state/strategies.json"):
        self.path = Path(path)
        self.strategies: dict[str, dict] = {}
        if self.path.exists():
            self.strategies = json.loads(self.path.read_text())
    
    def record(self, strategy: str, success: bool, cost: float = 0):
        """Record a strategy attempt."""
        if strategy not in self.strategies:
            self.strategies[strategy] = {
                "attempts": 0, "successes": 0, "total_cost": 0
            }
        
        s = self.strategies[strategy]
        s["attempts"] += 1
        if success:
            s["successes"] += 1
        s["total_cost"] += cost
        
        self.path.write_text(json.dumps(self.strategies, indent=2))
    
    def get_rankings(self) -> str:
        """Return strategies ranked by success rate."""
        ranked = []
        for name, stats in self.strategies.items():
            rate = stats["successes"] / max(stats["attempts"], 1)
            ranked.append((rate, name, stats))
        
        ranked.sort(reverse=True)
        
        lines = ["## Strategy Rankings (by success rate)"]
        for rate, name, stats in ranked:
            emoji = "🟢" if rate >= 0.7 else "🟡" if rate >= 0.4 else "🔴"
            lines.append(
                f"{emoji} **{name}**: {rate:.0%} success "
                f"({stats['attempts']} attempts, ${stats['total_cost']:.2f} spent)"
            )
        
        return "\n".join(lines)
```

## Putting It Together: Memory-Augmented Context

The magic happens when you feed all three layers into the agent's context:

```python
def build_context_with_memory(
    task: str,
    outcomes: OutcomeHistory,
    memory: EpisodicMemory,
    strategies: StrategyTracker,
) -> str:
    """Build context that includes agent's memory."""
    sections = ["# Your Identity\nYou are a capable AI agent that learns from experience.\n"]
    
    # Inject relevant memories for this task
    relevant = memory.search(task, limit=3)
    if relevant:
        sections.append(
            "## Relevant Past Learnings\n" +
            "\n".join(f"- {m['content']}" for m in relevant)
        )
    
    # Inject failure warnings
    failures = outcomes.get_failure_patterns()
    if failures:
        sections.append("## ⚠️ Known Failure Patterns\n" + "\n".join(failures))
    
    # Inject strategy rankings
    rankings = strategies.get_rankings()
    if rankings:
        sections.append(rankings)
    
    # Inject recent outcomes
    recent = outcomes.get_recent(5)
    if recent:
        sections.append(
            "## Recent Actions\n" +
            "\n".join(
                f"{'✅' if r['success'] else '❌'} {r['action']}: {r['result_preview'][:100]}"
                for r in recent
            )
        )
    
    return "\n\n---\n\n".join(sections)
```

## The Learning Loop

After each agent cycle, extract and store lessons:

```python
def post_cycle_learning(
    task: str,
    outcome: str,
    success: bool,
    memory: EpisodicMemory,
    strategies: StrategyTracker,
    llm_client,
):
    """Extract lessons after a cycle completes."""
    # Ask LLM to extract a lesson
    lesson = llm_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": f"Task: {task}\nOutcome: {outcome}\nSuccess: {success}\n\n"
                       f"Extract ONE actionable lesson (1 sentence). "
                       f"If the task failed, what should be done differently?"
        }]
    ).content[0].text
    
    memory.store(lesson, tags=[task[:50]])
    strategies.record(task[:100], success)
```

## Results: Before vs After Memory

| Metric | Without Memory | With Memory |
|--------|---------------|-------------|
| Repeated failures | ~40% of cycles | <5% of cycles |
| Time to complete task | 8-12 turns | 3-5 turns |
| Budget waste | High (same errors) | Low (learns from mistakes) |
| Cross-session learning | None | Full knowledge transfer |

## Going Further

- **[Build an AI Agent with Tools](build-ai-agent-tools.md)** — The foundation
- **[Context Engineering Deep Dive](context-engineering.md)** — Advanced context patterns
- **[Immune System Patterns](immune-system.md)** — Self-diagnosis and auto-recovery

For complete production implementations with battle-tested code: visit [TutuoAI](https://tutuoai.com).

---

*Built by [TutuoAI](https://tutuoai.com) — Production AI Agent Engineering*
