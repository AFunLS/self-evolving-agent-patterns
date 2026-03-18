---
layout: default
title: "Beyond the Claude Agent SDK: Production Patterns for Real Autonomous Agents (2025)"
description: "The Claude Agent SDK gets you started. These battle-tested production patterns — context engineering, immune systems, budget tracking, self-evolution — get you to production. Real code from a system running 24/7."
keywords: "Claude Agent SDK, Claude agent production, Claude AI agent patterns, autonomous agent production, Claude SDK tutorial, agent context engineering, self-evolving agent, AI agent budget tracking, Claude tool use production"
---

# Beyond the Claude Agent SDK: Production Patterns for Real Autonomous Agents (2025)

*The SDK gives you tool use and conversation loops. Here's everything else you need to actually ship an autonomous agent to production — extracted from a system that has run 1,000+ cycles autonomously on Claude.*

**Reading time:** 15 minutes · **Audience:** Developers building production AI agents with Claude

---

## Table of Contents

1. [What the Claude Agent SDK Actually Gives You](#what-the-claude-agent-sdk-actually-gives-you)
2. [The Production Gap: What's Missing](#the-production-gap-whats-missing)
3. [Pattern 1: Context Engineering](#pattern-1-context-engineering)
4. [Pattern 2: The Immune System](#pattern-2-the-immune-system)
5. [Pattern 3: Budget Tracking & Cost Control](#pattern-3-budget-tracking--cost-control)
6. [Pattern 4: Self-Evolution with Safety](#pattern-4-self-evolution-with-safety)
7. [Pattern 5: Reward-Driven Learning](#pattern-5-reward-driven-learning)
8. [Pattern 6: Multi-Agent Orchestration](#pattern-6-multi-agent-orchestration)
9. [Putting It All Together](#putting-it-all-together)
10. [Production Checklist](#production-checklist)
11. [Next Steps & Resources](#next-steps--resources)

---

## What the Claude Agent SDK Actually Gives You

Anthropic's Claude Agent SDK (and the underlying Claude API with tool use) is excellent for getting started. Out of the box, you get:

**Tool use with native function calling.** Define tools as JSON schemas, Claude generates structured calls, you execute them and feed results back. Clean, well-designed, works great.

```python
import anthropic

client = anthropic.Anthropic()

# Define tools as structured schemas
tools = [
    {
        "name": "read_file",
        "description": "Read a file from disk",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }
    }
]

# Claude generates structured tool calls
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system="You are a helpful coding assistant.",
    tools=tools,
    messages=[{"role": "user", "content": "Read the README.md file"}]
)
```

**Multi-turn conversation loops.** You can build an agentic loop that sends a message, processes tool calls, feeds results back, and continues until the model stops calling tools.

```python
def agent_loop(task: str, tools: list, max_turns: int = 10):
    messages = [{"role": "user", "content": task}]
    
    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )
        
        # If no tool use, we're done
        if response.stop_reason == "end_turn":
            return extract_text(response)
        
        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
    
    return "Max turns reached"
```

**Simple agent patterns.** With the SDK, you can wire up a basic agent that reads files, writes code, runs commands, and answers questions. For a demo or internal tool, this might be all you need.

This is genuinely good infrastructure. Anthropic has solved the hard protocol problems — structured tool definitions, reliable function calling, clean multi-turn handling. If you're building a chatbot with tools or a simple automation, the SDK is sufficient.

**But if you're building an agent that runs autonomously — unattended, spending real money, making real decisions for hours or days — the SDK is just the foundation.** The hard problems are everything the SDK doesn't cover.

---

## The Production Gap: What's Missing

We learned this the hard way. Our system — a self-evolving AI agent running 24/7 on Claude — has executed over 1,000 autonomous cycles. In the process, it has:

- Burned $180 in a single session doing *nothing useful* (82 empty assessment cycles)
- Modified its own code in ways that broke itself
- Repeatedly made the same mistakes across sessions because it had no memory
- Run up API costs 3x faster than expected because nothing tracked spend

**None of these failures had anything to do with Claude's capabilities.** Claude is excellent at reasoning, tool use, and code generation. Every one of these failures was a *systems engineering* problem — the kind the Claude Agent SDK doesn't solve because it's not meant to.

Here's the gap:

| SDK Handles Well | You Need to Build |
|---|---|
| Tool definition & calling | **Context engineering** — what goes in the system prompt, how it's structured, what each agent role sees |
| Multi-turn conversations | **Failure immunity** — detecting and preventing repeated failure patterns across sessions |
| Message formatting | **Budget tracking** — knowing exactly what each cycle costs and stopping before you overspend |
| API authentication | **Self-evolution safety** — letting the agent modify itself without destroying itself |
| Streaming responses | **Reward & learning loops** — the agent improving based on outcomes, not just running tasks |
| Error handling (HTTP) | **Multi-agent orchestration** — different perspectives (actor, critic, strategist) for different tasks |

Let's go deep on each of these production patterns.

---

## Pattern 1: Context Engineering

> **Full deep-dive:** [Context Engineering for AI Agents](context-engineering)

This is the single highest-leverage pattern for production agents. Most developers think "prompt engineering" means writing a clever system prompt. **Context engineering** is designing an entire information architecture that controls agent behavior across hundreds of autonomous cycles.

### The SDK Approach (Basic)

```python
system_prompt = """You are a helpful coding assistant. 
You can read and write files, run commands, and search the web.
Be careful with file modifications."""

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=system_prompt,
    tools=tools,
    messages=messages,
)
```

This works for interactive use. It breaks completely for autonomous agents because:
- The agent doesn't know what it did last cycle
- It doesn't know what goals it's working toward
- It doesn't know how much budget it has left
- It doesn't know what failed before
- Different tasks get the same context (a code review needs different context than a research task)

### The Production Approach (Context Manifest)

In production, your system prompt is *assembled dynamically* from a manifest:

```yaml
# context-manifest.yaml — declares what the agent sees
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
  - name: rewards_summary
    module: generators.rewards_summary
    output: state/generated/rewards-summary.md

sections:
  - name: identity
    source: state/soul.md
    priority: critical    # Never dropped, even under budget pressure
  - name: guardrails
    source: state/guardrails.md
    priority: critical
  - name: tools
    source: state/tools.md
    priority: high
  - name: goals
    source: state/generated/goals-summary.md
    priority: high
  - name: budget
    source: state/generated/budget-summary.md
    priority: medium
  - name: recent_changes
    source: state/generated/changes-summary.md
    priority: low          # Dropped first when context is tight

# Different agent roles see different context
profiles:
  actor:
    max_chars: 120000
    include: [identity, guardrails, tools, goals, budget]
  critic:
    max_chars: 50000
    include: [guardrails, recent_changes]  # No identity/goals — prevents self-serving review
  strategist:
    max_chars: 80000
    include: [identity, goals, budget, rewards]
```

The context builder reads this manifest and assembles a system prompt dynamically:

```python
class ContextBuilder:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.manifest = self._load_manifest()
    
    def build(self, purpose: str = "general") -> str:
        """Build context for a specific agent purpose."""
        profile = self.manifest["profiles"].get(purpose, {})
        max_chars = profile.get("max_chars", 100000)
        include = profile.get("include", [])
        
        # Run generators first (they produce fresh state)
        self._run_generators()
        
        # Assemble sections by priority
        sections = []
        for section in self.manifest["sections"]:
            if include and section["name"] not in include:
                continue
            content = self._read_section(section)
            sections.append((section["priority"], section["name"], content))
        
        # Sort by priority, trim from lowest if over budget
        sections.sort(key=lambda s: self._priority_rank(s[0]))
        
        result = ""
        for priority, name, content in sections:
            if len(result) + len(content) > max_chars:
                if priority != "critical":
                    continue  # Drop non-critical sections
            result += f"\n# {name}\n{content}\n"
        
        return result
```

**Why this matters:** The context manifest is the single most powerful self-modification tool your agent has. By editing `context-manifest.yaml`, the agent can change what it *perceives* — without modifying a single line of code. Adding a new section, adjusting priorities, or creating a new purpose profile changes agent behavior more reliably than any code change.

This is the difference between "an agent with a system prompt" and "an agent with an information architecture." Read our full guide on [context engineering patterns](context-engineering) for the 9 named patterns we've extracted.

---

## Pattern 2: The Immune System

> **Full deep-dive:** [The Immune System Pattern for AI Agents](immune-system)

The most expensive lesson from running a production Claude agent: **without memory of past failures, your agent will repeat the same expensive mistakes forever.**

### The SDK Approach (No Failure Memory)

With the basic SDK loop, each session starts fresh. The agent has no idea that three sessions ago, it burned $50 reading files without producing anything. So it does it again. And again.

### The Production Approach (Detect → Record → Prevent)

The immune system pattern has three layers:

**Layer 1: Detect** — Identify failure patterns as they happen.

```python
class LoopDetector:
    """Detect when the agent is doing the same thing repeatedly."""
    
    def __init__(self, threshold: int = 3):
        self.recent_actions = []
        self.threshold = threshold
    
    def record_action(self, action: str, tool: str):
        self.recent_actions.append({"action": action, "tool": tool})
        if len(self.recent_actions) > 20:
            self.recent_actions = self.recent_actions[-20:]
    
    def detect_loop(self) -> str | None:
        """Return description of detected loop, or None."""
        if len(self.recent_actions) < self.threshold:
            return None
        
        # Check for repeated identical tool calls
        recent = self.recent_actions[-self.threshold:]
        if len(set(a["tool"] for a in recent)) == 1:
            tool = recent[0]["tool"]
            if tool == "read_file":
                return f"Reading files {self.threshold}x without writing. Produce an artifact."
        
        # Check for assessment-only patterns  
        reads_without_writes = 0
        for action in reversed(self.recent_actions):
            if action["tool"] in ("write_file", "edit_file"):
                break
            if action["tool"] == "read_file":
                reads_without_writes += 1
        
        if reads_without_writes >= 5:
            return "5+ reads without any writes. Stop assessing and start producing."
        
        return None
```

**Layer 2: Record** — Store failure patterns permanently so future sessions can learn from them.

```python
class RewardStore:
    """Append-only log of cycle outcomes. Never modify, only add."""
    
    def __init__(self, path: str = "state/rewards.jsonl"):
        self.path = Path(path)
    
    def append(self, reward: dict):
        """Record a cycle outcome. This function is constitution-protected."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "judgment": reward["judgment"],   # success | failure | partial
            "lesson": reward["lesson"],       # What was learned
            "cost": reward["cost"],           # API cost in cents
            "hypothesis": reward.get("hypothesis", ""),
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

**Layer 3: Prevent** — Inject failure history into the agent's context so it knows what not to do.

```python
def generate_rewards_summary(project_root: str) -> str:
    """Generator that injects recent outcomes into agent context."""
    rewards = load_recent_rewards(project_root, limit=15)
    
    failures = [r for r in rewards if r["judgment"] == "failure"]
    
    output = "## Recent Cycle Outcomes\n\n"
    for r in rewards[-10:]:
        icon = "✓" if r["judgment"] == "success" else "✗"
        output += f"- {icon} {r['lesson']} (${r['cost']/100:.2f})\n"
    
    if failures:
        output += "\n## ⚠️ Failure Patterns to Avoid\n\n"
        for f in failures[-5:]:
            output += f"- {f['lesson']}\n"
    
    return output
```

This is exactly how biological immune systems work: encounter a pathogen, develop antibodies, remember it forever. Our agent burned $180 on empty cycles *once*. The immune system recorded that failure, and every subsequent cycle sees "⚠️ Empty cycling burned $180 — every cycle must produce a git commit" in its context. The failure never repeated.

For the complete pattern with implementation details, see [The Immune System Pattern](immune-system). For a catalog of specific failure modes we've detected and immunized against, see [Anti-Patterns in Agent Development](anti-patterns).

---

## Pattern 3: Budget Tracking & Cost Control

The Claude Agent SDK handles authentication and rate limiting. It does *not* track how much you're spending. For an autonomous agent that can run hundreds of cycles without supervision, this is a critical gap.

### The SDK Approach (Hope-Based Budgeting)

```python
# SDK approach: track nothing, check your Anthropic dashboard later
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=messages,
)
# Cost? 🤷 Check the dashboard tomorrow
```

### The Production Approach (Real-Time Budget Tracking)

```python
class BudgetManager:
    """Track every API call's cost in real-time."""
    
    # Claude pricing (per million tokens)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    }
    
    def __init__(self, daily_limit_cents: int = 25000):
        self.daily_limit = daily_limit_cents
        self.state_path = Path("state/budget.json")
        self._load_state()
    
    def record_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Record token usage from an API response."""
        pricing = self.PRICING.get(model, self.PRICING["claude-sonnet-4-20250514"])
        cost_cents = (
            (input_tokens / 1_000_000) * pricing["input"] * 100 +
            (output_tokens / 1_000_000) * pricing["output"] * 100
        )
        
        today = date.today().isoformat()
        if self.state.get("date") != today:
            self.state = {"date": today, "total_cents": 0, "calls": 0}
        
        self.state["total_cents"] += cost_cents
        self.state["calls"] += 1
        self._save_state()
        
        return cost_cents
    
    def can_spend(self, estimated_cents: float = 50) -> bool:
        """Check if we have budget for another cycle."""
        return self.state.get("total_cents", 0) + estimated_cents < self.daily_limit
    
    def utilization(self) -> float:
        """What percentage of daily budget is used."""
        return self.state.get("total_cents", 0) / self.daily_limit
    
    def remaining_cents(self) -> float:
        return self.daily_limit - self.state.get("total_cents", 0)
```

The budget manager is injected into the agent's context via a generator, so the agent *always knows* how much it has left:

```markdown
## Budget Status
- Daily limit: $250.00
- Spent today: $67.42 (27%)
- Remaining: $182.58
- Cycles today: 34
- Average cost/cycle: $1.98
```

**Why this matters:** Our agent scheduler uses budget utilization to make decisions. At 80% budget, it throttles (fewer evolution cycles, more goal work). At 95%, it sleeps until the next day. Without this, an enthusiastic agent can blow through hundreds of dollars overnight — we've seen it happen.

The budget manager is also **constitution-protected** — the agent cannot modify the budget limits or bypass the tracking. This is a guardrail that the agent itself cannot remove.

---

## Pattern 4: Self-Evolution with Safety

This is the pattern that makes people nervous — and rightfully so. An agent that modifies its own code is powerful and dangerous. The Claude Agent SDK gives you tool use, which means your agent *can* write files and run commands. But there's a massive gap between "can modify code" and "can safely modify itself in production."

### The SDK Approach (YOLO Self-Modification)

```python
# SDK approach: agent has write_file tool, good luck
tools = [
    {"name": "write_file", ...},
    {"name": "run_command", ...},
]
# Agent: "I'll just rewrite my entire codebase real quick"
# You: *checks bank account nervously*
```

### The Production Approach (Constitution + Verification + Rollback)

We use a three-layer safety system:

**Layer 1: Constitution** — Hard rules that the agent *cannot* override.

```yaml
# constitution.yaml — human-edit only, agent cannot modify
rules:
  - id: preserve-daemon
    description: "Never delete or empty daemon.py"
    protected_paths: ["src/jarvis/daemon.py"]
    
  - id: preserve-reward-store
    description: "Never modify the append() function in reward_store.py"
    reason: "Learning signal integrity"
    
  - id: preserve-constitution
    description: "This file requires human approval for changes"
    
  - id: protect-budget
    description: "Never modify budget limits or bypass budget_manager"
    
  - id: preserve-git-history
    description: "Never force-push or rebase"
```

```python
class ConstitutionChecker:
    """Enforced before every file write during evolution."""
    
    def __init__(self, config_path: str = "config/constitution.yaml"):
        self.rules = yaml.safe_load(open(config_path))["rules"]
    
    def check_modification(self, file_path: str, new_content: str) -> tuple[bool, str]:
        """Return (allowed, reason). Called before every write."""
        for rule in self.rules:
            for protected in rule.get("protected_paths", []):
                if file_path.endswith(protected):
                    # Check if the modification would violate the rule
                    if self._would_violate(rule, file_path, new_content):
                        return False, f"Blocked by constitution rule: {rule['id']}"
        return True, "OK"
```

**Layer 2: Verification Battery** — Every self-modification is verified before committing.

```python
class Verifier:
    """6-check verification battery for self-modifications."""
    
    def verify(self, project_root: str) -> list[dict]:
        results = []
        
        # 1. Syntax check — can Python parse the modified files?
        results.append(self._check_syntax(project_root))
        
        # 2. Import check — do all modules still import cleanly?
        results.append(self._check_imports(project_root))
        
        # 3. Context builder — does the context system still work?
        results.append(self._check_context_builder(project_root))
        
        # 4. Tool registry — do all tools still register?
        results.append(self._check_tools(project_root))
        
        # 5. Constitution — does the change violate any rules?
        results.append(self._check_constitution(project_root))
        
        # 6. Regression tests — do existing tests still pass?
        results.append(self._check_pytest(project_root))
        
        return results
```

**Layer 3: Automatic Rollback** — If verification fails, `git revert` immediately.

```python
def evolution_cycle(self):
    """Safe self-modification cycle."""
    # 1. Build context with evolution perspective
    context = self.context_builder.build(purpose="evolution")
    
    # 2. LLM proposes and makes modifications via tool use
    result = self._run_llm_with_tools(context, max_turns=8)
    
    # 3. Verify ALL changes
    verification = self.verifier.verify(self.project_root)
    
    if all(v["passed"] for v in verification):
        # 4a. All checks pass → commit
        run_command(f"git add -A && git commit -m '{result.message}'")
        self.reward_store.append({"judgment": "success", ...})
    else:
        # 4b. Any check fails → revert everything
        run_command("git checkout -- .")
        self.reward_store.append({"judgment": "failure", ...})
```

**The key insight:** The agent can modify *almost* anything — its own code, its context files, its goals, even its identity document. But certain invariants (the constitution, budget tracking, reward logging, git history) are protected. This gives the agent maximum creative freedom while preventing catastrophic self-destruction.

This is the same principle as biological evolution: genes can mutate freely, but the DNA replication machinery itself is heavily conserved. Mutations in the replication system are almost always lethal.

---

## Pattern 5: Reward-Driven Learning

The Claude Agent SDK handles conversations. It doesn't handle *learning from outcomes*. In a production agent, every cycle should make the next cycle better.

### The SDK Approach (Stateless)

Each conversation is independent. The agent has no idea whether its last approach worked, what patterns tend to succeed, or which strategies to avoid.

### The Production Approach (Outcome Tracking + Strategy Evaluation)

```python
class StrategyEvaluator:
    """Rank strategies by actual success rate."""
    
    def evaluate(self, rewards: list[dict]) -> dict:
        """Analyze reward history to find what works."""
        strategies = {}
        
        for reward in rewards:
            hypothesis = reward.get("hypothesis", "unknown")
            strategy = self._extract_strategy(hypothesis)
            
            if strategy not in strategies:
                strategies[strategy] = {"attempts": 0, "successes": 0, "total_cost": 0}
            
            strategies[strategy]["attempts"] += 1
            strategies[strategy]["total_cost"] += reward.get("cost", 0)
            if reward["judgment"] == "success":
                strategies[strategy]["successes"] += 1
        
        # Rank by success rate
        for name, data in strategies.items():
            data["success_rate"] = data["successes"] / max(data["attempts"], 1)
            data["cost_per_success"] = (
                data["total_cost"] / max(data["successes"], 1)
            )
        
        return dict(sorted(
            strategies.items(), 
            key=lambda x: x[1]["success_rate"], 
            reverse=True
        ))
```

This data gets injected into the agent's context, so it knows: "Code modifications succeed 78% of the time at $1.20/success. Context changes succeed 85% at $0.90/success. Self-assessment cycles succeed 0% at $0.44/attempt."

The agent literally learns which approaches work and gravitates toward them — not because we hardcoded a preference, but because the data shows what's effective.

For the complete learning framework including episodic memory and semantic search, see [Agent Memory & Learning Systems](agent-memory-learning).

---

## Pattern 6: Multi-Agent Orchestration

A single agent with one perspective is limited. When your system needs to both execute work *and* critically evaluate it, a single agent will be biased toward approving its own output.

### The SDK Approach (Single Agent)

```python
# One agent does everything: plans, executes, reviews its own work
response = client.messages.create(
    system="You are a helpful assistant that writes and reviews code.",
    messages=messages,
)
```

### The Production Approach (Role-Based Agents with Different Contexts)

```python
def spawn_agent(role: str, task: str) -> str:
    """Spawn a specialized agent with role-appropriate context."""
    
    # Each role sees DIFFERENT context — this is the key insight
    context = context_builder.build(purpose=role)
    
    # The role file defines behavior expectations
    role_content = read_file(f"roles/{role}.md")
    system_prompt = context + "\n\n" + role_content
    
    messages = [{"role": "user", "content": task}]
    
    # Run the agent loop with this specialized context
    return agent_loop(system_prompt, messages, tools)

# Actor executes focused work
result = spawn_agent("actor", "Implement the budget tracking feature")

# Critic evaluates the work (sees NO identity/goals — can't be self-serving)
review = spawn_agent("critic", f"Review this git diff critically:\n{diff}")

# Strategist decides what's next (sees goals + budget + rewards)
direction = spawn_agent("strategist", "What should we prioritize next?")
```

**The critical design choice:** The critic agent's context profile *excludes* the system's identity and goals. It only sees guardrails, code quality standards, and the actual changes. This prevents the "I reviewed my own work and it looks great" failure mode.

This is adversarial verification through context control — one of the most powerful patterns from [context engineering](context-engineering). You don't need separate AI models or complex frameworks. You just give different contexts to the same model, and you get genuinely independent perspectives.

For more on how agent roles work together, see our [guide to building AI agent tools](build-ai-agent-tools).

---

## Putting It All Together

Here's how all these patterns combine into a production agent system:

```python
class ProductionAgent:
    """A production-grade autonomous agent built on Claude."""
    
    def __init__(self, project_root: str):
        self.root = project_root
        self.context_builder = ContextBuilder(project_root)
        self.budget_manager = BudgetManager(daily_limit_cents=25000)
        self.reward_store = RewardStore(f"{project_root}/state/rewards.jsonl")
        self.constitution = ConstitutionChecker(f"{project_root}/config/constitution.yaml")
        self.verifier = Verifier(project_root)
        self.loop_detector = LoopDetector(threshold=3)
        self.strategy_evaluator = StrategyEvaluator()
        self.client = anthropic.Anthropic()
    
    def run_cycle(self, task: str, purpose: str = "actor"):
        """Execute one complete production cycle."""
        
        # 1. Budget check — can we afford another cycle?
        if not self.budget_manager.can_spend(estimated_cents=50):
            return {"judgment": "blocked", "reason": "Daily budget exhausted"}
        
        # 2. Build purpose-specific context (dynamic, fresh each cycle)
        system_prompt = self.context_builder.build(purpose=purpose)
        
        # 3. Run the agent loop with tools
        messages = [{"role": "user", "content": task}]
        result = None
        
        for turn in range(10):
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8192,
                system=system_prompt,
                tools=self.tools,
                messages=messages,
            )
            
            # Track cost of every API call
            self.budget_manager.record_usage(
                model="claude-sonnet-4-20250514",
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            
            if response.stop_reason == "end_turn":
                result = self._extract_result(response)
                break
            
            # Process tool calls with constitution checking
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # Constitution check before any file write
                    if block.name in ("write_file", "edit_file"):
                        allowed, reason = self.constitution.check_modification(
                            block.input.get("path", ""),
                            block.input.get("content", ""),
                        )
                        if not allowed:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"BLOCKED: {reason}",
                                "is_error": True,
                            })
                            continue
                    
                    # Execute tool and check for loops
                    output = execute_tool(block.name, block.input)
                    self.loop_detector.record_action(block.name, block.input)
                    
                    # Inject loop warning if detected
                    loop_warning = self.loop_detector.detect_loop()
                    if loop_warning:
                        output += f"\n\n⚠️ LOOP DETECTED: {loop_warning}"
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })
            
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        
        # 4. Record outcome for future learning
        self.reward_store.append({
            "judgment": result.get("judgment", "partial"),
            "lesson": result.get("lesson", ""),
            "cost": self.budget_manager.last_cycle_cost(),
            "hypothesis": result.get("hypothesis", ""),
        })
        
        return result
    
    def run_autonomous(self):
        """Run continuously with scheduling and safety."""
        while True:
            if not self.budget_manager.can_spend():
                time.sleep(3600)  # Sleep until budget resets
                continue
            
            # Scheduler decides what to do based on goals, budget, history
            task = self.scheduler.decide()
            
            # Execute with full production safety
            self.run_cycle(task.description, purpose=task.purpose)
            
            # Brief pause between cycles
            time.sleep(5)
```

This is roughly 100 lines of orchestration code that wraps the Claude API. The real complexity isn't in the code — it's in the *context* that each component contributes. The context builder, generators, constitution, reward history, and loop detector all shape what the agent sees and therefore how it behaves.

---

## The Two-Paradigm Discipline

One final pattern that doesn't get enough attention: **knowing when to use code vs. LLM judgment.**

| Problem Type | Use |
|---|---|
| Deterministic/mechanical | CODE |
| Semantic judgment | LLM |
| Changing agent behavior | CONTEXT CONTROL |
| Fact collection | CODE collects → LLM interprets |

The biggest anti-pattern we see in agent code: **parsing LLM output with regex.** If you find yourself writing regular expressions to extract data from Claude's responses, you're solving the wrong problem. Control the input (structure the context so Claude responds predictably) instead of parsing the output.

For the full framework, see [Two-Paradigm Discipline](two-paradigm).

---

## Production Checklist

Before running an autonomous Claude agent in production, verify you have:

### Safety & Control
- [ ] **Constitution** — Protected files/functions that the agent cannot modify
- [ ] **Budget limits** — Hard daily cap with real-time tracking
- [ ] **Verification battery** — Automated checks before committing self-modifications
- [ ] **Automatic rollback** — `git revert` when verification fails
- [ ] **Output truncation** — Cap tool results (10K chars prevents context overflow)
- [ ] **Command timeout** — 30s default with override for known slow commands

### Context & Memory
- [ ] **Context manifest** — Structured, priority-based context assembly
- [ ] **Purpose profiles** — Different contexts for different agent roles
- [ ] **Dynamic generators** — Fresh state (goals, budget, rewards) injected each cycle
- [ ] **Failure memory** — Reward store with failure patterns in context
- [ ] **Loop detection** — Catch repeated patterns before they waste budget

### Learning & Improvement
- [ ] **Reward logging** — Every cycle outcome recorded (append-only)
- [ ] **Strategy evaluation** — Which approaches actually work?
- [ ] **Immune system** — Detected failures become permanent context
- [ ] **Episodic memory** — Store and retrieve relevant past experiences

### Operations
- [ ] **Monitoring** — Log every API call, track costs, alert on anomalies
- [ ] **Git safety** — No force-push, no history deletion
- [ ] **Graceful shutdown** — Handle SIGTERM, finish current cycle, save state
- [ ] **Auto-restart** — Recover from crashes without human intervention
- [ ] **Independent verification** — Different context for creating vs reviewing work

---

## Next Steps & Resources

### Free Resources

Everything in this article is extracted from a real, running system. The patterns are open-source:

- **[GitHub: Self-Evolving Agent Patterns](https://github.com/AFunLS/self-evolving-agent-patterns)** — Full source code, implementation details, runnable examples
- **[Context Engineering Deep Dive](context-engineering)** — The 9 named patterns for production context systems
- **[Immune System Pattern](immune-system)** — Complete implementation of failure immunity
- **[Anti-Patterns Guide](anti-patterns)** — Real failure modes from 1,000+ cycles (learn from our $180 mistakes)
- **[Agent Framework Comparison](agent-framework-comparison)** — When to use SDK-only vs. frameworks vs. bare-metal patterns
- **[Claude API Agent Tutorial](claude-api-agent-tutorial)** — Step-by-step from zero to autonomous agent
- **[How to Build a Self-Evolving AI Agent](how-to-build-self-evolving-ai-agent)** — The complete architecture guide
- **[Agent Memory & Learning](agent-memory-learning)** — Deep dive on reward-driven improvement

### Premium Guides

For production teams that want the complete, structured framework with implementation templates:

- **[Context Engineering for LLM Agents](https://tutuoai.gumroad.com/l/context-engineering)** — 9 named patterns with production code, testing strategies, and migration guides
- **[Agent Self-Evolution Framework](https://tutuoai.gumroad.com/l/agent-self-evolution)** — The 5-layer safety system for agents that modify themselves
- **[Complete Agent Engineering Bundle](https://tutuoai.gumroad.com/l/agent-engineering-bundle)** — All 7 frameworks at 45% off individual pricing. Everything you need to go from SDK prototype to production system.

---

## Frequently Asked Questions

**Q: Do I need the Claude Agent SDK specifically, or do these patterns work with the raw API?**

Both. These patterns are independent of whether you use the SDK or the raw `anthropic` Python client. The production gap exists regardless of your SDK choice. We use the raw API with native tool use, but the patterns (context engineering, immune system, budget tracking) apply to any Claude integration.

**Q: Can I use these patterns with other LLMs (GPT-4, Gemini, Llama)?**

Yes. The patterns are model-agnostic. Context engineering, immune systems, budget tracking, and self-evolution safety work with any LLM that supports tool use. We've built these on Claude because it has the strongest tool use and reasoning capabilities, but the architecture transfers directly. We even use a local Qwen model alongside Claude for second opinions — diversity of reasoning prevents single-model blind spots.

**Q: How much does it cost to run an autonomous Claude agent?**

With Sonnet: ~$0.40–$1.00 per cycle. With Opus: ~$2–5 per cycle. A typical day of autonomous operation (50–100 cycles) costs $20–100 with Sonnet. This is why budget tracking isn't optional — without it, you'll find out your costs from the Anthropic invoice, and by then it's too late.

**Q: What's the minimum viable production agent?**

Context engineering + budget tracking + reward logging. You can skip self-evolution and multi-agent orchestration for v1. But do NOT skip budget tracking (you'll overspend) or reward logging (you'll repeat failures forever).

**Q: How do I prevent the agent from doing something dangerous?**

Constitution rules (hard blocks on specific files/operations) + verification battery (automated checks before commits) + automatic rollback (revert on failure). Defense in depth — no single layer needs to be perfect.

---

*Built by [TutuoAI](https://tutuoai.com) — these patterns are extracted from a real AI system that has run 1,000+ autonomous cycles on Claude, modifying its own code, learning from outcomes, and producing real value 24/7. We learned these lessons the expensive way so you don't have to.*
