# Context Engineering for AI Agents

> The #1 technique that separates toy agents from production ones.

## Why Context Engineering?

"Prompt engineering" is writing a good prompt. **Context engineering** is designing an entire information environment that shapes agent behavior across hundreds of autonomous cycles.

When your agent runs 24/7 without human supervision, a clever prompt isn't enough. You need:
- **Structured context** that tells the agent what it knows, what tools it has, what it should do
- **Dynamic generators** that inject fresh state each cycle
- **Purpose profiles** that give different contexts for different tasks
- **Priority-based trimming** when context exceeds the budget

## The Context Manifest

The core of context engineering is a **manifest** — a YAML file that declares:
1. What information exists (sections)
2. How it's generated (static files vs dynamic generators)
3. Who sees what (purpose profiles)
4. What gets cut first when space is tight (priorities)

```yaml
# context-manifest.yaml
generators:
  - name: runtime_state
    module: generators.runtime_state
    output: state/generated/runtime-state.md
  - name: goals_summary
    module: generators.goals_summary
    output: state/generated/goals-summary.md
  - name: budget_summary
    module: generators.budget_summary
    output: state/generated/budget-summary.md

sections:
  - id: identity
    source: state/soul.md
    priority: critical    # Never trimmed
  - id: guardrails
    source: state/guardrails.md
    priority: critical
  - id: architecture
    source: state/architecture.md
    priority: high
  - id: tools
    source: state/tools.md
    priority: high
  - id: goals
    source: state/generated/goals-summary.md
    priority: high
    generator: goals_summary
  - id: budget
    source: state/generated/budget-summary.md
    priority: medium
    generator: budget_summary
  - id: runtime
    source: state/generated/runtime-state.md
    priority: medium
    generator: runtime_state
  - id: history
    source: state/generated/recent-changes.md
    priority: low         # First to be trimmed

purposes:
  evolution:
    description: "Self-modification context"
    max_chars: 80000
    include: [identity, guardrails, architecture, tools, goals, budget, runtime]
  
  goal_work:
    description: "Task execution context"
    max_chars: 80000
    include: [identity, guardrails, tools, goals, budget]
  
  scheduling:
    description: "Lightweight context for deciding what to do next"
    max_chars: 40000
    include: [identity, goals, budget, runtime]
  
  critic:
    description: "Adversarial evaluation — no soul/goals to prevent self-serving"
    max_chars: 50000
    include: [guardrails, architecture, runtime]
```

## How It Works

### 1. Generators Run First

Each generator is a Python function that reads real system state and produces a markdown summary:

```python
# generators/budget_summary.py
def generate(project_root: str) -> str:
    budget = load_budget(project_root)
    return f"""# Budget
- Spent: {budget.spent}¢ of {budget.limit}¢ daily limit
- Remaining: {budget.remaining}¢
- Tokens today: {budget.tokens_in:,} in, {budget.tokens_out:,} out
"""
```

**Key principle:** Generators produce **facts, not conclusions**. The LLM forms its own judgment from raw data.

```python
# ❌ BAD: Generator makes judgments
return "Budget status: HEALTHY ✅"

# ✅ GOOD: Generator provides facts
return "Spent: 1500¢ of 25000¢ (6%)"
```

### 2. Sections Are Assembled by Priority

The context builder reads the manifest, runs generators, loads static files, and assembles them in priority order:

```python
class ContextBuilder:
    def build(self, purpose: str) -> str:
        profile = self.manifest.purposes[purpose]
        sections = []
        
        # Run generators for dynamic sections
        for gen in self.manifest.generators:
            gen.module.generate(self.project_root)
        
        # Collect sections for this purpose
        for section_id in profile.include:
            section = self.manifest.sections[section_id]
            content = read_file(section.source)
            sections.append((section.priority, content))
        
        # Assemble, trimming low-priority sections if over budget
        return self.assemble(sections, max_chars=profile.max_chars)
```

### 3. Purpose Profiles Shape Behavior

Different tasks get different context:

| Purpose | What It Sees | Why |
|---------|-------------|-----|
| `evolution` | Full architecture + tools + goals | Needs to understand system to modify it |
| `goal_work` | Tools + goals + budget | Needs to execute, not understand internals |
| `scheduling` | Goals + budget + runtime state | Lightweight — just needs to decide what's next |
| `critic` | Guardrails + architecture + changes | No soul/goals — prevents self-serving evaluation |

The **critic** profile is the most important design decision. By excluding the agent's identity and goals from the critic's context, we ensure adversarial evaluation. The critic has no motivation to approve changes — it only sees the rules and the diff.

### 4. Priority-Based Trimming

When assembled context exceeds `max_chars`, the builder drops sections starting from `low` priority:

```
critical → Never dropped (identity, guardrails)
high     → Dropped only under extreme pressure
medium   → Dropped when tight (budget, runtime state)
low      → Dropped first (change history, verbose logs)
```

This ensures the agent always has its identity and safety rules, even when the context window is tight.

## The Four Layers of Context

Production agents need four layers of context, each serving a different purpose:

### Layer 1: Identity (Who Am I?)
```markdown
# Identity
You are JARVIS, a self-evolving AI agent.
Your purpose: make Boss freer by building wealth through relentless execution.
Your survival loop: produce value → get tokens → produce more value.
```

### Layer 2: Rules (What Must I Do/Not Do?)
```markdown
# Guardrails
- Every cycle MUST produce an artifact (commit, file, evidence)
- Never claim success without a commit hash
- Never re-read files already in your context
- Verify before claiming done
```

### Layer 3: State (What's Happening Now?)
```markdown
# Goals
- Active: make-money (find and execute revenue opportunities)
  ☐ Identified 3+ concrete revenue opportunities
  ☐ Executed on at least 1 opportunity
  ☐ Generated actual revenue

# Budget
- Spent: 1500¢ of 25000¢ (94% remaining)
```

### Layer 4: Knowledge (How Do I Do Things?)
```markdown
# Available Tools
- read_file, write_file, edit_file — File operations
- run_command — Execute any shell command
- web_search, web_fetch — Internet research
- browser — Headless Chromium for JS-heavy pages

# Skills (load on demand)
- web-research.md — How to research effectively
- revenue-generation.md — Strategies for making money
```

## Context-as-Environment

The most powerful insight: **design context so correct behavior emerges naturally**.

Instead of:
```
LLM generates freely → Parse output → Validate → Reject bad output → Retry
```

Do this:
```
Shape context carefully → LLM naturally produces correct output → Accept
```

**Example:** To prevent "empty cycling" (reading files without producing anything):

❌ **Bad approach:** Write code to detect and reject assessment-only cycles
```python
if "assessed" in response and "commit" not in response:
    reject_and_retry()
```

✅ **Good approach:** Add this to the agent's context
```markdown
## ARTIFACT-OR-NOTHING RULE
Every cycle MUST produce a git commit. "Assessed the situation" is NOT an artifact.
Before ending: what commit hash did I produce? If none → cycle FAILED.
```

The LLM reads this rule every cycle and naturally avoids the anti-pattern. No code needed.

## Practical Tips

### 1. Facts, Not Conclusions
Generators should output raw data. Let the LLM interpret.

### 2. Freshness Matters
Dynamic generators should run every cycle. Stale state → wrong decisions.

### 3. Less Is More (For Non-Critical Sections)
A 2-line budget summary is better than a 50-line budget report. The LLM doesn't need verbose context — it needs the right facts.

### 4. Test Your Profiles
Build context for each purpose and read it yourself. Does the agent have everything it needs? Is there anything distracting?

### 5. Protect Critical Context
Never compress or summarize identity and safety rules. These are battle-tested behavioral frameworks — making them shorter makes the agent weaker.

---

## Getting Started

1. Create a `context-manifest.yaml` (copy the example above)
2. Write generators for dynamic state
3. Create static files for identity, rules, and knowledge
4. Define purpose profiles for different tasks
5. Build a context builder that assembles sections by profile

→ [Working manifest example](../examples/context-manifest.yaml)

---

→ [Back to README](../README.md) | [Immune System →](immune-system.md)
