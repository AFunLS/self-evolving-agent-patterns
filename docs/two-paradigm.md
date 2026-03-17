# Two-Paradigm Discipline for AI Agents

> The single most impactful design rule for production AI agent systems.

## The Problem

Most agent codebases are full of code like this:

```python
# ❌ BAD: Using code for semantic judgment
def evaluate_goal_progress(goal_text, evidence):
    if "revenue" in goal_text.lower():
        return check_revenue_metrics(evidence)
    elif "code quality" in goal_text.lower():
        return check_code_quality(evidence)
    elif "test" in goal_text.lower():
        return check_test_results(evidence)
    else:
        return "unknown goal type"
```

This creates a **ceiling on your agent's capability**. The human who wrote this code had to anticipate every possible goal type. An LLM can handle cases the human never imagined — but only if you don't constrain it with hardcoded dispatch.

## The Two Paradigms

Before writing ANY code in an agent system, ask: **"Am I making a MECHANICAL decision or a SEMANTIC one?"**

| Decision Type | Use | Examples |
|---|---|---|
| **Mechanical** | Code | File exists? HTTP 200? Test pass? JSON valid? |
| **Semantic** | LLM | Is this progress? What should we do? Is this relevant? |
| **Behavioral** | Context Control | Change what the LLM sees, don't filter what it says |
| **Fact Collection** | Code collects → LLM interprets | Gather metrics with code, evaluate meaning with LLM |

### Mechanical Decisions (Use Code)

These have deterministic, unambiguous answers:

```python
# ✅ GOOD: Mechanical checks in code
import os, json, subprocess

def verify_change(filepath):
    # Does file exist? (mechanical)
    if not os.path.exists(filepath):
        return False
    
    # Does it parse? (mechanical)
    try:
        with open(filepath) as f:
            json.load(f)
    except json.JSONDecodeError:
        return False
    
    # Do tests pass? (mechanical)
    result = subprocess.run(["pytest", "-x", "-q"], capture_output=True)
    return result.returncode == 0
```

### Semantic Decisions (Use LLM)

These require understanding, judgment, or reasoning:

```python
# ✅ GOOD: Semantic evaluation by LLM
def evaluate_goal_progress(goal, evidence):
    response = llm.generate(
        system="You are evaluating whether evidence shows progress toward a goal.",
        messages=[{
            "role": "user",
            "content": f"Goal: {goal}\n\nEvidence:\n{evidence}\n\n"
                       f"Does this evidence show meaningful progress? "
                       f"Call the report_result tool with your judgment."
        }],
        tools=[report_result_tool]
    )
    return response.tool_calls[0].input  # Structured result
```

### Behavioral Decisions (Use Context Control)

When you want to change what the LLM *does*, change what it *sees*:

```python
# ❌ BAD: Parsing and filtering LLM output
response = llm.generate("Write a commit message")
# Strip reasoning artifacts...
lines = response.split('\n')
lines = [l for l in lines if not l.startswith('I think')]
lines = [l for l in lines if not l.startswith('Let me')]
commit_msg = '\n'.join(lines).strip()

# ✅ GOOD: Context control — shape input, not output
response = llm.generate(
    system="Output ONLY a git commit message. No explanation. No reasoning. "
           "Format: type: description (under 72 chars)",
    messages=[{"role": "user", "content": f"Diff:\n{diff}"}]
)
commit_msg = response.strip()
```

## The Anti-Patterns

### 1. If-Elif Dispatch on Semantic Categories

```python
# ❌ BANNED: Semantic dispatch with code
def categorize_lesson(lesson_text):
    if "architecture" in lesson_text:
        return "architecture"
    elif "cost" in lesson_text or "budget" in lesson_text:
        return "cost"
    elif "debug" in lesson_text:
        return "debugging"
    # ... 15 more branches
```

**Why it's wrong:** What about "the system structure needs work" (architecture without the word)? What about "we spent too much on API calls" (cost without "cost" or "budget")?

**Fix:** Either use an LLM for categorization, or better — don't categorize at all. Ask: does the downstream code actually need categories?

### 2. Regex on LLM Output

```python
# ❌ BANNED: Parsing free-text LLM output with regex
import re
match = re.search(r'THRESHOLD:\s*(.*?)\nMET:\s*(.*?)\nEVIDENCE:\s*(.*)', response)
threshold = match.group(1)
met = match.group(2)
evidence = match.group(3)
```

**Why it's wrong:** LLMs don't reliably follow exact formatting. They might add extra spaces, reorder fields, include explanatory text, or use slightly different labels.

**Fix:** Use tool calls (function calling). The LLM calls a structured tool instead of writing formatted text:

```python
# ✅ GOOD: Structured output via tool calls
tools = [{
    "name": "report_evaluation",
    "input_schema": {
        "type": "object",
        "properties": {
            "threshold": {"type": "string"},
            "met": {"type": "boolean"},
            "evidence": {"type": "string"}
        },
        "required": ["threshold", "met", "evidence"]
    }
}]
```

### 3. Keyword Lists for Quality Judgment

```python
# ❌ BANNED: Keyword-based quality assessment
GARBAGE_PATTERNS = [
    "I'll help you", "certainly", "as an AI", "let me",
    "I'd be happy to", "great question", ...
]

def is_garbage(text):
    return any(p in text.lower() for p in GARBAGE_PATTERNS)
```

**Why it's wrong:** You're playing whack-a-mole with an infinite set of possible phrasings. You'll never catch them all, and you'll get false positives.

**Fix:** If the output quality matters, fix the input context so the LLM doesn't produce garbage. If you truly need quality filtering, use an LLM to evaluate (cheaper model is fine).

## Decision Flowchart

```
Need to make a decision in agent code?
│
├─ Is the answer deterministic/unambiguous?
│  ├─ YES → Use code (file exists, JSON parses, test passes)
│  └─ NO ↓
│
├─ Does it require understanding meaning?
│  ├─ YES → Use LLM (evaluate, categorize, decide)
│  └─ NO ↓
│
├─ Are you trying to change agent behavior?
│  ├─ YES → Change context (modify system prompt, not output filter)
│  └─ NO ↓
│
└─ Are you collecting facts for later judgment?
   └─ YES → Code collects facts → LLM interprets them
```

## Real Example: Goal Evaluation

**Before (5 different code-based evaluators):**
```python
def evaluate_goal(goal):
    if goal.type == "test_improvement":
        return run_tests_and_compare()
    elif goal.type == "context_reduction":
        return measure_context_size()
    elif goal.type == "revenue":
        return check_revenue_metrics()
    # Adding a new goal type? Edit this code!
```

**After (one LLM evaluator handles everything):**
```python
def evaluate_goal(goal):
    # Code collects facts (mechanical)
    evidence = gather_evidence()  # test results, file sizes, git log, etc.
    
    # LLM evaluates meaning (semantic)
    result = llm.evaluate(
        goal=goal.description,
        thresholds=goal.thresholds,
        evidence=evidence,
        tools=[report_evaluation_tool]
    )
    return result
```

New goal type? Zero code changes. The LLM already knows how to evaluate it.

---

## Summary

1. **Mechanical decisions** → Code (deterministic, unambiguous)
2. **Semantic decisions** → LLM (understanding, judgment, reasoning)
3. **Behavioral changes** → Context control (change input, not output)
4. **Fact collection** → Code gathers, LLM interprets

**The test:** Before every if-elif, ask "Am I making a semantic decision?" If yes, use an LLM.

→ [Back to README](../README.md) | [Context Engineering →](context-engineering.md)
