"""
CLI entry point for agent-patterns.

Usage:
    agent-patterns run "Build a calculator module"
    agent-patterns demo              # Run with a built-in demo task
    agent-patterns version
    agent-patterns doctor            # Check setup (API key, Python version, etc.)

Installed via: pip install agent-patterns
"""

from __future__ import annotations

import argparse
import os
import sys

from agent_patterns import Agent, __version__


DEMO_TASKS = [
    "Create a Python module called 'hello.py' that prints a greeting, then run it to verify it works.",
    "Write a fibonacci function to fib.py, test it with a few values, and record what you learned.",
    "Create a simple key-value store in store.py with get/set/delete operations, then test it.",
]


def cmd_run(args: argparse.Namespace) -> None:
    """Run an agent with a custom task."""
    task = " ".join(args.task)
    if not task.strip():
        print("Error: please provide a task. Example:")
        print('  agent-patterns run "Create a hello world script"')
        sys.exit(1)

    model = args.model or os.environ.get("AGENT_MODEL", "claude-sonnet-4-20250514")
    agent = Agent(model=model, self_evolving=args.evolve, max_turns=args.max_turns)
    result = agent.run(task, verbose=not args.quiet)

    if not args.quiet:
        print(f"\n📊 Completed in {result['turns']} turns")


def cmd_demo(args: argparse.Namespace) -> None:
    """Run a built-in demo task to see the agent in action."""
    import random

    task = random.choice(DEMO_TASKS)
    print(f"🎯 Demo task: {task}\n")

    model = args.model or os.environ.get("AGENT_MODEL", "claude-sonnet-4-20250514")
    agent = Agent(model=model, self_evolving=True, max_turns=8)
    result = agent.run(task, verbose=True)
    print(f"\n📊 Demo completed in {result['turns']} turns")
    print("💡 Try with your own task: agent-patterns run \"your task here\"")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Check that the environment is properly set up."""
    print(f"agent-patterns v{__version__}\n")

    # Check Python version
    v = sys.version_info
    ok = v >= (3, 11)
    print(f"{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro} {'(3.11+ required)' if not ok else ''}")

    # Check anthropic SDK
    try:
        import anthropic
        print(f"✅ anthropic SDK v{anthropic.__version__}")
    except ImportError:
        print("❌ anthropic SDK not installed — run: pip install anthropic")

    # Check API key
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        print(f"✅ ANTHROPIC_API_KEY set ({key[:8]}...{key[-4:]})")
    else:
        print("❌ ANTHROPIC_API_KEY not set — export ANTHROPIC_API_KEY=your-key")

    # Check optional pyyaml
    try:
        import yaml
        print(f"✅ pyyaml available")
    except ImportError:
        print("ℹ️  pyyaml not installed (optional, for context manifests)")

    print("\n🏥 Doctor complete.")


def cmd_version(args: argparse.Namespace) -> None:
    """Print version."""
    print(f"agent-patterns {__version__}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="agent-patterns",
        description="🧬 Self-Evolving AI Agent Patterns — battle-tested from 1,000+ autonomous cycles",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run
    p_run = subparsers.add_parser("run", help="Run the agent with a custom task")
    p_run.add_argument("task", nargs="+", help="The task for the agent to complete")
    p_run.add_argument("--model", help="Model to use (default: claude-sonnet-4-20250514)")
    p_run.add_argument("--evolve", action="store_true", help="Enable self-evolution")
    p_run.add_argument("--max-turns", type=int, default=10, help="Max turns (default: 10)")
    p_run.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    p_run.set_defaults(func=cmd_run)

    # demo
    p_demo = subparsers.add_parser("demo", help="Run a built-in demo to see the agent in action")
    p_demo.add_argument("--model", help="Model to use (default: claude-sonnet-4-20250514)")
    p_demo.set_defaults(func=cmd_demo)

    # doctor
    p_doctor = subparsers.add_parser("doctor", help="Check your setup")
    p_doctor.set_defaults(func=cmd_doctor)

    # version (also available as --version)
    p_version = subparsers.add_parser("version", help="Print version")
    p_version.set_defaults(func=cmd_version)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n💡 Quick start:")
        print("  agent-patterns doctor                          # Check setup")
        print("  agent-patterns demo                            # Run demo")
        print('  agent-patterns run "Create a hello world app"  # Custom task')
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
