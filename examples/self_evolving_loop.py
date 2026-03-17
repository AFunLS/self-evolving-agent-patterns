#!/usr/bin/env python3
"""
Self-Evolving Loop — The core evolve → verify → commit pattern in ~100 lines.

This is the "aha moment" example. It shows how an LLM can:
  1. Propose a code change to itself (evolve)
  2. Verify the change didn't break anything (verify)
  3. Keep the change if safe, revert if not (commit/rollback)

This is how production self-evolving agents work. The LLM doesn't just
generate code — it modifies its OWN code, tests it, and learns.

    pip install anthropic
    export ANTHROPIC_API_KEY=your-key
    python self_evolving_loop.py

For the full production implementation: https://tutuoai.com
"""

import json
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path

import anthropic

MODEL = "claude-sonnet-4-20250514"

# --- The Target: a file the agent will evolve --------------------------------

TARGET = Path("evolvable_greeter.py")
HISTORY = Path("evolution_log.jsonl")

def ensure_target():
    """Create the initial version of the code the agent will evolve."""
    if not TARGET.exists():
        TARGET.write_text(textwrap.dedent('''\
            """A simple greeter — the agent will evolve this."""

            def greet(name: str) -> str:
                return f"Hello, {name}!"

            if __name__ == "__main__":
                print(greet("World"))
        '''))
        print(f"📄 Created {TARGET} (initial version)")


# --- Verification: mechanical checks on the evolved code --------------------

def verify(path: Path) -> tuple[bool, str]:
    """Run mechanical verification: syntax check + execute the file."""
    # Check 1: Does it parse?
    r = subprocess.run(
        ["python3", "-c", f"import py_compile; py_compile.compile('{path}', doraise=True)"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False, f"Syntax error: {r.stderr}"

    # Check 2: Does it run without crashing?
    r = subprocess.run(["python3", str(path)], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        return False, f"Runtime error: {r.stderr}"

    return True, f"Output: {r.stdout.strip()}"


# --- The Evolution Cycle -----------------------------------------------------

def evolve_once(improvement_goal: str) -> dict:
    """One evolution cycle: propose change → verify → keep or revert."""
    client = anthropic.Anthropic()
    current_code = TARGET.read_text()
    backup = current_code  # Save for rollback

    # Ask the LLM to propose an improvement
    print(f"\n🧬 Evolution goal: {improvement_goal}")
    print(f"📝 Current code:\n{textwrap.indent(current_code, '   ')}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            "You are a code evolution engine. Given existing code and an improvement goal, "
            "produce the COMPLETE improved file. Reply with ONLY the Python code, no markdown "
            "fences, no explanation. The code must be valid Python that runs standalone."
        ),
        messages=[{"role": "user", "content": (
            f"Current code in {TARGET}:\n```\n{current_code}```\n\n"
            f"Improvement goal: {improvement_goal}\n\n"
            f"Produce the complete improved file:"
        )}],
    )

    new_code = response.content[0].text.strip()
    # Strip markdown fences if the model included them
    if new_code.startswith("```"):
        new_code = "\n".join(new_code.split("\n")[1:])
    if new_code.endswith("```"):
        new_code = "\n".join(new_code.split("\n")[:-1])

    # Write the evolved version
    TARGET.write_text(new_code)
    print(f"\n🔬 Proposed change written. Verifying...")

    # Verify: did the change break anything?
    passed, detail = verify(TARGET)
    result = {
        "timestamp": datetime.now().isoformat(),
        "goal": improvement_goal,
        "passed": passed,
        "detail": detail,
    }

    if passed:
        print(f"✅ Verification passed! {detail}")
        print(f"📝 New code:\n{textwrap.indent(new_code, '   ')}")
    else:
        # ROLLBACK: revert to the backup
        TARGET.write_text(backup)
        print(f"❌ Verification failed — rolled back. {detail}")

    # Log the outcome (learning signal)
    with open(HISTORY, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result


# --- Entry Point -------------------------------------------------------------

if __name__ == "__main__":
    ensure_target()

    # Run a sequence of evolution cycles — each builds on the last
    goals = [
        "Add type hints and a docstring to the greet function",
        "Add a 'farewell' function and call both in __main__",
        "Add error handling for empty names and add a simple test block",
    ]

    results = []
    for goal in goals:
        result = evolve_once(goal)
        results.append(result)
        print(f"   {'🟢' if result['passed'] else '🔴'} {goal}\n")

    # Summary
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{'='*60}")
    print(f"🧬 Evolution complete: {passed}/{len(results)} cycles succeeded")
    print(f"   See {HISTORY} for full log")
    print(f"   See {TARGET} for the evolved code")
    print(f"\n   This is the core pattern behind production self-evolving agents.")
    print(f"   For safety layers, multi-agent review, and immune system:")
    print(f"   → https://tutuoai.com")
