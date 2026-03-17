#!/usr/bin/env python3
"""Auto-generate optimized CLAUDE.md for any Python project. No external deps.

Based on context engineering patterns from
https://github.com/AFunLS/self-evolving-agent-patterns

Usage: python claudemd-generator.py /path/to/project [-o output.md] [--stdout]
"""
import argparse, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

SKIP = {".git", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache", "node_modules",
        ".eggs", "dist", "build", ".venv", "venv", "env", ".env", ".nox", ".ruff_cache"}


def find_py_files(root: Path, limit: int = 500) -> list[Path]:
    """Walk project tree, return .py files, skipping irrelevant dirs."""
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.endswith(".egg-info")]
        for f in filenames:
            if f.endswith(".py"):
                results.append(Path(dirpath) / f)
                if len(results) >= limit:
                    return results
    return results


def build_tree(root: Path, max_depth: int = 3) -> str:
    """Build an ASCII directory tree."""
    lines = [f"{root.name}/"]
    def _walk(d: Path, prefix: str, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(d.iterdir(), key=lambda e: (not e.is_dir(), e.name))
        except PermissionError:
            return
        entries = [e for e in entries if e.name not in SKIP and not e.name.endswith(".egg-info")]
        for i, entry in enumerate(entries):
            last = i == len(entries) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{entry.name}")
            if entry.is_dir():
                _walk(entry, prefix + ("    " if last else "│   "), depth + 1)
    _walk(root, "", 1)
    return "\n".join(lines)


def detect_structure(root: Path) -> dict:
    """Detect src layout, packages, and test dirs."""
    info = {"layout": "flat", "packages": [], "test_dirs": []}
    src = root / "src"
    if src.is_dir():
        info["layout"] = "src-layout"
        info["packages"] = [d.name for d in src.iterdir() if d.is_dir() and (d / "__init__.py").exists()]
    else:
        info["packages"] = [d.name for d in root.iterdir()
                            if d.is_dir() and (d / "__init__.py").exists()
                            and d.name not in SKIP and d.name != "tests"]
    for name in ("tests", "test"):
        if (root / name).is_dir():
            info["test_dirs"].append(name)
    return info


def detect_deps(root: Path) -> dict:
    """Read dependencies from requirements.txt / pyproject.toml."""
    deps = {"source": None, "packages": []}
    req = root / "requirements.txt"
    if req.exists():
        deps["source"] = "requirements.txt"
        deps["packages"] = [ln.strip().split("==")[0].split(">=")[0].split("<")[0].strip()
                            for ln in req.read_text(errors="ignore").splitlines()
                            if ln.strip() and not ln.startswith(("#", "-"))][:30]
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        deps["source"] = deps["source"] or "pyproject.toml"
        m = re.search(r'dependencies\s*=\s*\[(.*?)\]', pyproj.read_text(errors="ignore"), re.DOTALL)
        if m:
            deps["packages"] += re.findall(r'"([^"<>=!~\[]+)', m.group(1))
    deps["packages"] = sorted(set(p.strip().lower() for p in deps["packages"] if p.strip()))
    return deps


def detect_tests(root: Path, py_files: list[Path]) -> dict:
    """Detect test framework (pytest/unittest) and command."""
    for marker in ("pytest.ini", "setup.cfg", "pyproject.toml", "tox.ini"):
        p = root / marker
        if p.exists() and ("[tool.pytest" in p.read_text(errors="ignore") or
                           "[pytest]" in p.read_text(errors="ignore")):
            return {"framework": "pytest", "command": "pytest"}
    for f in py_files:
        if "test" in f.name.lower() or "test" in str(f.parent).lower():
            try:
                head = f.read_text(errors="ignore")[:2000]
            except OSError:
                continue
            if "import pytest" in head:
                return {"framework": "pytest", "command": "pytest"}
            if "import unittest" in head or "from unittest" in head:
                return {"framework": "unittest", "command": "python -m unittest discover"}
    return {"framework": "unknown", "command": "pytest  # (no config found — guessed)"}


def detect_linters(root: Path) -> list[str]:
    """Detect linting/formatting tools from config files."""
    found = []
    checks = {"ruff": ["ruff.toml"], "flake8": [".flake8"], "mypy": ["mypy.ini", ".mypy.ini"],
              "pylint": [".pylintrc"], "isort": [".isort.cfg"]}
    toml_tools = ("ruff", "black", "isort", "mypy", "pylint", "flake8")
    for tool, files in checks.items():
        if any((root / f).exists() for f in files):
            found.append(tool)
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        text = pyproj.read_text(errors="ignore")
        for tool in toml_tools:
            if f"[tool.{tool}]" in text and tool not in found:
                found.append(tool)
    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        text = setup_cfg.read_text(errors="ignore")
        for tool in ("flake8", "isort", "mypy"):
            if f"[{tool}]" in text and tool not in found:
                found.append(tool)
    return sorted(set(found))


def detect_conventions(py_files: list[Path]) -> dict:
    """Sample Python files to detect coding style."""
    indents, hints, docs, total = Counter(), 0, 0, 0
    for f in py_files[:40]:
        try:
            content = f.read_text(errors="ignore")
        except OSError:
            continue
        total += 1
        for line in content.split("\n")[:200]:
            s = line.lstrip()
            if s and line != s:
                n = len(line) - len(s)
                if n in (2, 4, 8):
                    indents[n] += 1
        if re.search(r'def \w+\(.*:.*\)\s*->', content[:5000]):
            hints += 1
        if re.search(r'(def|class)\s+\w+.*:\s*\n\s+"""', content[:5000]):
            docs += 1
    if total == 0:
        return {"indent": "4 spaces", "type_hints": False, "docstrings": False}
    top = indents.most_common(1)
    return {
        "indent": f"{top[0][0]} spaces" if top else "4 spaces",
        "type_hints": hints > total * 0.3,
        "docstrings": docs > total * 0.3,
    }


def get_git_info(root: Path) -> dict:
    """Get branch and recent commits."""
    info = {"branch": "", "commits": [], "has_git": False}
    def _run(args):
        try:
            r = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=5)
            return r.stdout.strip() if r.returncode == 0 else ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch:
        info["has_git"] = True
        info["branch"] = branch
        log = _run(["git", "log", "--oneline", "-8", "--no-decorate"])
        info["commits"] = [ln for ln in log.splitlines() if ln.strip()]
    return info


def get_readme_summary(root: Path) -> str:
    """Extract first meaningful paragraph from README."""
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = root / name
        if not p.exists():
            continue
        lines, out = p.read_text(errors="ignore")[:3000].splitlines(), []
        for line in lines:
            s = line.strip()
            if s.startswith(("#", "[!", "![", "===", "---")):
                continue
            if s:
                out.append(s)
            elif out:
                break
        return " ".join(out)[:500] if out else ""
    return ""


def detect_scripts(root: Path) -> list[str]:
    """Find Makefile targets, scripts/ dir, CLI entry points."""
    scripts = []
    mk = root / "Makefile"
    if mk.exists():
        targets = re.findall(r'^([a-zA-Z_][\w-]*):', mk.read_text(errors="ignore")[:5000], re.MULTILINE)
        if targets:
            scripts.append(f"Makefile targets: {', '.join(targets[:10])}")
    sd = root / "scripts"
    if sd.is_dir():
        files = [f.name for f in sd.iterdir() if f.is_file()][:10]
        if files:
            scripts.append(f"scripts/: {', '.join(files)}")
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        m = re.search(r'\[project\.scripts\](.*?)(\[|$)', pyproj.read_text(errors="ignore"), re.DOTALL)
        if m:
            entries = re.findall(r'(\w[\w-]*)\s*=', m.group(1))
            if entries:
                scripts.append(f"CLI entry points: {', '.join(entries[:10])}")
    return scripts


def generate_claude_md(root: Path) -> str:
    """Assemble the complete CLAUDE.md content."""
    root = root.resolve()
    py_files = find_py_files(root)
    pkg = detect_structure(root)
    deps = detect_deps(root)
    tests = detect_tests(root, py_files)
    linters = detect_linters(root)
    conv = detect_conventions(py_files)
    git = get_git_info(root)
    readme = get_readme_summary(root)
    scripts = detect_scripts(root)

    out = [f"# CLAUDE.md — {root.name}\n", "> Auto-generated project context for Claude Code.\n"]
    if readme:
        out.append(f"## Overview\n\n{readme}\n")

    out.append(f"## Project Structure\n\n```\n{build_tree(root)}\n```\n")
    if pkg["layout"] == "src-layout":
        out.append("**Layout:** src-layout (packages under `src/`)\n")
    if pkg["packages"]:
        out.append(f"**Packages:** {', '.join(pkg['packages'])}\n")
    out.append(f"**Python files:** {len(py_files)}\n")

    if deps["packages"]:
        out.append(f"## Dependencies\n\nSource: `{deps['source']}`\n\n"
                   f"Key packages: {', '.join(deps['packages'][:15])}\n")

    out.append("## Coding Conventions\n\n"
               f"- **Indentation:** {conv['indent']}\n"
               f"- **Type hints:** {'Yes — use them in new code' if conv['type_hints'] else 'Sparse — match existing style'}\n"
               f"- **Docstrings:** {'Yes — add to public functions' if conv['docstrings'] else 'Minimal — match existing style'}\n")

    out.append(f"## Testing\n\n**Framework:** {tests['framework']}\n\n"
               f"```bash\n{tests['command']}\n```\n")
    if pkg["test_dirs"]:
        out.append(f"Test directories: {', '.join(pkg['test_dirs'])}\n")

    if linters:
        out.append(f"## Linting & Formatting\n\nTools: {', '.join(linters)}\n\n"
                   "Run before committing to match project style.\n")
    if scripts:
        out.append("## Available Scripts\n\n" + "\n".join(f"- {s}" for s in scripts) + "\n")

    if git["has_git"]:
        out.append(f"## Git\n\n**Default branch:** {git['branch']}\n")
        if git["commits"]:
            out.append("**Recent commits:**\n```\n" + "\n".join(git["commits"][:7]) + "\n```\n")

    key_files = [n for n in ("setup.py", "setup.cfg", "pyproject.toml", "Makefile",
                             "Dockerfile", "docker-compose.yml", ".env.example",
                             "alembic.ini", "manage.py", "app.py", "main.py", "cli.py")
                 if (root / n).exists()]
    if key_files:
        out.append("## Key Files\n\n" + "\n".join(f"- `{f}`" for f in key_files) + "\n")

    out.append("## Working in This Codebase\n\n"
               "- Read existing code before modifying — match the style you see.\n"
               "- Run tests after changes to verify nothing broke.\n"
               "- Keep functions focused and under 50 lines when possible.\n"
               "- Commit messages: imperative mood (\"add feature\" not \"added feature\").\n")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Generate an optimized CLAUDE.md for a Python project.")
    parser.add_argument("project_dir", help="Path to the Python project root")
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: CLAUDE.md in project root)")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing a file")
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    if not project.is_dir():
        print(f"Error: {project} is not a directory", file=sys.stderr)
        sys.exit(1)
    content = generate_claude_md(project)
    if args.stdout:
        print(content)
    else:
        out_path = Path(args.output) if args.output else project / "CLAUDE.md"
        out_path.write_text(content)
        print(f"✓ Generated {out_path} ({len(content)} chars)")


if __name__ == "__main__":
    main()
