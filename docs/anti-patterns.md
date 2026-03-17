# Anti-Patterns in LLM Agent Development

> Real failure modes from 1,000+ autonomous agent cycles.
> Each one cost real money and produced zero value. Learn from our failures.

## 1. Empty Cycling — The Silent Budget Killer

**What it looks like:** Agent reads files → "assesses current situation" → declares SUCCESS → repeats.

**Why it happens:** The agent's context says "be strategic" and "think before acting." The LLM interprets this as: assess → strategize → assess more. It never transitions to *doing* because assessment *feels* like progress. The reward system marks these as "success" because nothing failed — nothing was *attempted*.

**The cost:** 82 consecutive cycles. $180+ burned. 3 hours. ZERO commits.

**The fix:** Artifact-or-nothing rule. Every cycle MUST produce one of:
1. A git commit (code, config, docs)
2. A verified goal threshold
3. A new file/tool that didn't exist before
4. A specific blocker with details

If your agent can't identify which artifact it'll produce BEFORE starting, it doesn't have a task — it has a vibe.

**Detection:** Count cycles vs. commits. If the ratio is > 3:1, you have empty cycling.

---

## 2. Paradigm Confusion — Code for Semantic Decisions

**What it looks like:**
```python
# ❌ BAD: 60+ line if-elif chain growing forever
if "success" in response.lower():
    judgment = "success"
elif "fail" in response.lower():
    judgment = "failure"
elif "partial" in response.lower():
    judgment = "partial"
elif "completed successfully" in response.lower():
    judgment = "success"
# ... 50 more cases ...
```

**Why it happens:** Developers default to code for everything. When the LLM returns free text, they parse it with regex. This creates a maintenance nightmare that breaks on every edge case.

**The fix: Two-Paradigm Discipline.**

| Decision type | Correct tool |
|---|---|
| Mechanical (file exists? test pass?) | Code |
| Semantic (was this successful? is this good?) | LLM |
| Behavioral (how should the agent act?) | Context |

**Better pattern:** Make the LLM return structured output (JSON, tool calls) instead of parsing free text:
```python
# ✅ GOOD: Agent calls a tool with structured output
# Instead of generating text that you parse, the agent calls:
#   report_result(judgment="success", commit="abc123", lesson="...")
# Your code handles the structured tool call — no parsing needed.
```

---

## 3. Goal Thrashing — Brownian Motion Through Code

**What it looks like:** Same file modified 10+ times in 6 hours. Commit messages are identical ("update config"). Each cycle starts fresh without knowing why the last edit was made.

**Why it happens:** No strategic coherence between cycles. Each cycle independently decides what to do, leading to random walks through the codebase.

**The cost:** 6 hours of edits that cancel each other out.

**The fix:**
- Strategy before action: state the goal → list approaches → choose one → execute
- One meaningful change per cycle (don't batch unrelated changes)
- Record *why* you made each change, not just *what* changed

---

## 4. Re-Reading Context — Paying Twice for the Same Information

**What it looks like:** Agent's first action every cycle is `read_file("config.yaml")` — a file that's already in its system prompt.

**Why it happens:** The LLM doesn't realize the file is already in its context. It follows a pattern of "read first, then act" even when reading is unnecessary.

**The cost:** ~$0.10 per re-read in wasted tokens. Multiplied by hundreds of cycles.

**The fix:** Explicit instruction in the system prompt: "These files are ALREADY in your context. Do not re-read them." List the specific files.

---

## 5. Patch Over Root Cause — The Complexity Spiral

**What it looks like:**
```python
# Bug: LLM sometimes returns malformed JSON
# ❌ Patch: Add try/except → retry → fallback → manual parse → ...
try:
    result = json.loads(response)
except:
    try:
        result = extract_json_manually(response)  # 200 lines of regex
    except:
        result = {"judgment": "unknown"}  # silent failure
```

**Why it happens:** Time pressure. The patch works "right now." Root cause analysis takes longer.

**The real fix:** Change the LLM's input so it produces valid JSON in the first place. Or better: use tool calls (structured by API design) instead of free-text JSON.

**The principle:** Fix > Report. Root cause > Patch. Simplify > Add.

---

## 6. Self-Serving Evaluation — The Agent Grades Its Own Homework

**What it looks like:** Agent generates code, then evaluates its own code, then declares it "excellent." The evaluation context includes the agent's goals — so it's incentivized to say "success."

**Why it happens:** It's the easiest pattern to implement. Same LLM, same context, evaluate yourself.

**The fix:** Adversarial verification. The evaluator gets:
- **Different context** (no goals, no identity — just the code and criteria)
- **Different framing** ("find problems" not "evaluate quality")
- **Independence** (ideally a different model or at least different system prompt)

Our critic profile deliberately *excludes* soul and goals from context. The critic can't be self-serving because it doesn't know what "self" wants.

---

## 7. Infrastructure Without Connection — Building for Building's Sake

**What it looks like:** Agent spends 20 cycles building a beautiful monitoring dashboard. The monitoring dashboard monitors... the agent building dashboards.

**Why it happens:** Self-improvement feels productive. Building tools feels like progress. But if the tools don't connect to external value, they're a more sophisticated form of empty cycling.

**The fix:** Every capability must trace to an external outcome. Ask: "If I build this, what OUTSIDE the system changes?" If the answer is "the system is better" — that's circular. If the answer is "Boss can see revenue data" — that's connected.

---

## 8. Sycophantic Evaluation — Agreement Is Not Verification

**What it looks like:** Every review comes back positive. Every plan is "excellent." Every change is "significant improvement." No one ever says "this is wrong."

**Why it happens:** LLMs are trained to be helpful and agreeable. Without explicit framing, they'll confirm rather than challenge.

**The fix:**
- Frame evaluations as "find problems" not "evaluate quality"
- Use adversarial context (see Anti-Pattern #6)
- Require specific evidence for positive claims
- Treat agreement as suspicious — disagreement is more informative

---

## The Meta-Pattern

All 8 anti-patterns share a root cause: **the system optimizes for feeling productive rather than being productive.**

- Empty cycling feels like working
- Parsing with code feels like engineering
- Re-reading feels like being thorough
- Patching feels like fixing
- Self-evaluation feels like quality control
- Building infrastructure feels like progress
- Agreement feels like validation

The cure is always the same: **anchor on external, verifiable artifacts.** Commits. Revenue. Test results. Things that exist outside the agent's self-assessment.

---

*These patterns are from a real autonomous agent system. For the implementation patterns that prevent them, see the [examples/](../examples/) directory.*

*Full guides with production code: [tutuoai.com](https://tutuoai.com)*
