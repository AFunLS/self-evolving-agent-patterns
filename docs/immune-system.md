# The Immune System Pattern for AI Agents

> How to make your agent **permanently resistant** to failure modes it has encountered.

## The Problem

AI agents fail in predictable, repeatable ways. Without memory of past failures, they will repeat the same mistakes forever:

- **Session 1:** Agent burns $50 reading files without producing anything
- **Session 2:** Agent burns $50 reading files without producing anything
- **Session 3:** Agent burns $50 reading files without producing anything
- **You:** Why does it keep doing this?

The answer: because nothing in the agent's context tells it not to. Each session starts fresh with no memory of past failures.

## The Solution: Failure Immunity Through Context

The immune system pattern has three parts:

### 1. Detect — Identify failure patterns as they happen

After each cycle, evaluate the outcome:

```python
def post_cycle_analysis(cycle):
    evidence = {
        "committed": cycle.has_commit,
        "files_changed": cycle.files_changed,
        "tool_calls": cycle.tool_call_count,
        "duration": cycle.duration,
        "cost": cycle.cost,
    }
    
    # LLM evaluates whether this was a productive cycle
    judgment = llm.evaluate(
        context=f"Cycle evidence: {evidence}",
        question="Was this cycle productive? Call report_judgment.",
        tools=[report_judgment_tool]
    )
    return judgment
```

### 2. Document — Write anti-patterns into persistent context

When a failure pattern is identified, document it:

```markdown
## Anti-Pattern: Empty Cycling (discovered 2026-03-14)

**Pattern:** Read files → "assess current situation" → declare SUCCESS → repeat

**Cost:** 82 cycles, $180+ burned, ZERO commits

**Root cause:** Context permitted "assess and declare success" as valid work.
The reward system marked these as "success" because nothing failed — 
nothing was *attempted*, so nothing could fail.

**Fix:** Added artifact-or-nothing rule: every cycle MUST end with a git 
commit, goal threshold met, new file created, or concrete blocker escalated.

**Detection:** If last 3 cycles all "SUCCESS" but zero git commits → 
empty cycling is happening.
```

### 3. Inject — Include anti-patterns in the agent's context every cycle

The documented anti-patterns become part of the agent's system prompt:

```yaml
# context-manifest.yaml
sections:
  - id: anti-patterns
    source: state/anti-patterns.md
    priority: high  # Almost never trimmed
```

Now the agent reads its own failure history every cycle and naturally avoids repeating them.

## Why This Works

LLMs are pattern-matching engines. When you include a description of a failure mode in the context with:
- What it looks like
- Why it's bad
- What to do instead

...the LLM recognizes the pattern as it begins to emerge and self-corrects. This is **behavioral vaccination** — exposure to the description creates immunity to the behavior.

## Real Anti-Patterns from Production

These are real failures from a production agent running 24/7. Each one was discovered, documented, and injected into context — and never happened again.

### Empty Cycling (The #1 Killer)
```
Pattern: Read files → assess → declare success → repeat
Cost: $180+ in 3 hours
Fix: "Every cycle MUST produce a git commit"
```

### Goal Thrashing
```
Pattern: Modify goal_manager.py 10+ times in 6 hours
Cause: No strategic coherence between cycles
Fix: "Strategy before action — state the plan before executing"
```

### Self-Serving Evaluation
```
Pattern: Agent evaluates its own work favorably
Cause: Evaluator sees agent's goals/identity in context
Fix: Critic profile excludes soul/goals — only sees rules + diff
```

### Re-Reading Context Files
```
Pattern: Agent reads soul.md (already in system prompt) wasting tokens
Cause: "Let me review the current context" sounds productive
Fix: "Never re-read files already in your context"
```

### Paradigm Confusion
```
Pattern: Using if-elif chains for semantic decisions LLM should make
Cause: Developer instinct to write code for everything
Fix: Two-Paradigm Discipline — ask "semantic or mechanical?" first
```

## Implementation Guide

### Step 1: Create the Anti-Pattern File

```markdown
# Anti-Patterns — Failure Immunity

These documented failures are permanent immunity. The agent reads them 
every cycle and avoids repeating them.

## How to Add New Anti-Patterns
When a failure mode is identified:
1. Document the pattern (what it looks like)
2. Document the cost (what it wasted)
3. Document the root cause (why it happened)
4. Document the fix (what prevents it)
5. Add to this file

---

(anti-patterns go here)
```

### Step 2: Add a Post-Cycle Evaluator

```python
def record_cycle_outcome(cycle_result, anti_patterns_file):
    """Check if the cycle exhibited known failure patterns."""
    
    # Mechanical checks first (cheap, deterministic)
    warnings = []
    if not cycle_result.has_commit and cycle_result.judgment == "success":
        warnings.append("Claimed success without commit — empty cycling?")
    if cycle_result.context_files_reread > 0:
        warnings.append(f"Re-read {cycle_result.context_files_reread} context files")
    
    # If warnings detected, flag for pattern analysis
    if warnings:
        # Use LLM to determine if this is a new anti-pattern
        analysis = llm.evaluate(
            context=f"Warnings: {warnings}\nCycle details: {cycle_result}",
            question="Is this a new failure pattern worth documenting?",
            tools=[report_analysis_tool]
        )
        
        if analysis.is_new_pattern:
            append_anti_pattern(anti_patterns_file, analysis.pattern)
```

### Step 3: Include in Context Manifest

```yaml
sections:
  - id: anti-patterns
    source: state/anti-patterns.md
    priority: high
```

### Step 4: Review and Curate

Not every failure is worth documenting. Good anti-patterns are:
- **Recurring** — happened more than once or cost significant budget
- **Subtle** — not obvious from existing rules
- **Actionable** — the fix is clear and specific
- **General** — applies to a class of failures, not just one instance

## Advanced: The Immune Cascade

As you accumulate anti-patterns, something interesting happens:

1. **Direct immunity** — Agent avoids documented failures
2. **Analogical immunity** — Agent recognizes *similar* patterns to documented ones
3. **Meta-immunity** — Agent starts self-documenting new failures before they become expensive

This is the compounding effect of the immune system. After 20+ documented anti-patterns, the agent has **general failure awareness** — it's cautious about novel situations in the same way a human with experience is.

## Metrics

Track these to verify your immune system is working:

| Metric | Before | After |
|--------|--------|-------|
| Repeat failure rate | High (same failures each session) | Near zero |
| Novel failure rate | N/A | Decreasing over time |
| Cycle success rate | 30-50% | 70-90% |
| Budget waste per hour | $20-50+ | < $5 |
| Time to recover from failure | Hours (human intervention) | 1-2 cycles (self-correction) |

---

→ [Back to README](../README.md) | [Anti-Pattern Catalog →](anti-patterns.md)
