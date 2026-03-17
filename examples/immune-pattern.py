"""
Immune System Pattern — Permanent Failure Immunity for LLM Agents
================================================================

Every failure your agent encounters becomes a documented anti-pattern
injected into its context. The agent literally cannot repeat a documented
failure because the warning is in its "DNA" (system prompt).

This pattern took our agent from ~30% to >80% cycle success rate.

From a production system with 1,000+ autonomous cycles.
Full guide: https://tutuoai.com (Agent Memory & Learning skill)
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class AntiPattern:
    """A documented failure mode the agent should never repeat."""
    name: str                    # e.g., "Empty Cycling"
    discovered: str              # ISO date
    description: str             # What happened
    pattern: str                 # How to recognize it happening
    root_cause: str              # Why it happened
    fix: str                     # What prevents it
    cost: str = ""               # How much it cost (makes it visceral)
    occurrences: int = 1         # How many times before documented


@dataclass 
class ImmuneSystem:
    """
    Manages anti-patterns and injects them into agent context.
    
    The key insight: LLMs respond to context, not code constraints.
    You don't prevent bad behavior by writing if-statements.
    You prevent it by putting "DON'T DO THIS" in the system prompt
    with enough detail that the LLM understands WHY.
    
    Usage:
        immune = ImmuneSystem("state/anti-patterns.json")
        
        # After detecting a failure pattern:
        immune.record(AntiPattern(
            name="Empty Cycling",
            discovered="2026-03-14",
            description="82 cycles, $180 burned, zero commits",
            pattern="Read files → assess situation → declare success → repeat",
            root_cause="Context permitted 'assessment' as valid work",
            fix="Artifact-or-nothing rule: every cycle must produce a commit"
        ))
        
        # When building agent context:
        context = immune.generate_context()
        system_prompt = f"{base_prompt}\n\n{context}"
    """
    
    store_path: str
    anti_patterns: list[AntiPattern] = field(default_factory=list)
    
    def __post_init__(self):
        self._load()
    
    def _load(self):
        """Load anti-patterns from persistent storage."""
        path = Path(self.store_path)
        if path.exists():
            data = json.loads(path.read_text())
            self.anti_patterns = [AntiPattern(**ap) for ap in data]
    
    def _save(self):
        """Persist anti-patterns."""
        path = Path(self.store_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {
                "name": ap.name,
                "discovered": ap.discovered,
                "description": ap.description,
                "pattern": ap.pattern,
                "root_cause": ap.root_cause,
                "fix": ap.fix,
                "cost": ap.cost,
                "occurrences": ap.occurrences,
            }
            for ap in self.anti_patterns
        ]
        path.write_text(json.dumps(data, indent=2))
    
    def record(self, anti_pattern: AntiPattern):
        """Record a new anti-pattern (or increment if already known)."""
        for existing in self.anti_patterns:
            if existing.name == anti_pattern.name:
                existing.occurrences += 1
                self._save()
                return
        self.anti_patterns.append(anti_pattern)
        self._save()
    
    def generate_context(self) -> str:
        """
        Generate context injection for the agent's system prompt.
        
        This is the core of the immune system: the anti-patterns become
        part of the agent's "DNA" — present in every cycle's context,
        making the agent permanently aware of these failure modes.
        """
        if not self.anti_patterns:
            return ""
        
        lines = [
            "# ⚠️ Known Anti-Patterns (From Real Failures)",
            "",
            "These failure modes have been observed in production. "
            "Each one cost real money and produced zero value. "
            "Recognize and avoid them.",
            "",
        ]
        
        # Sort by occurrences (most dangerous first) then by date
        sorted_patterns = sorted(
            self.anti_patterns,
            key=lambda ap: (-ap.occurrences, ap.discovered),
        )
        
        for ap in sorted_patterns:
            cost_note = f" (Cost: {ap.cost})" if ap.cost else ""
            lines.extend([
                f"## ❌ {ap.name}{cost_note}",
                f"**Discovered:** {ap.discovered} | **Occurrences:** {ap.occurrences}",
                f"**What happened:** {ap.description}",
                f"**Pattern to watch for:** {ap.pattern}",
                f"**Root cause:** {ap.root_cause}",
                f"**Prevention:** {ap.fix}",
                "",
            ])
        
        return "\n".join(lines)
    
    def check_cycle(self, cycle_description: str) -> list[str]:
        """
        Quick heuristic check: does this cycle look like a known anti-pattern?
        
        Note: This is a SIMPLE keyword check for obvious matches.
        For nuanced detection, use an LLM call instead — that's the
        Two-Paradigm Discipline (semantic decisions → LLM, not code).
        
        Returns list of warning strings (empty = no matches).
        """
        warnings = []
        description_lower = cycle_description.lower()
        
        # Only check for the most mechanically-detectable patterns
        mechanical_checks = {
            "Empty Cycling": ["assessed", "reviewed", "confirmed healthy", "looks good"],
            "Re-reading Context": ["re-read", "read soul.md again", "already in context"],
        }
        
        for pattern_name, keywords in mechanical_checks.items():
            if any(kw in description_lower for kw in keywords):
                warnings.append(
                    f"⚠️ Possible '{pattern_name}' detected. "
                    f"Check: are you producing an artifact this cycle?"
                )
        
        return warnings


# ── Demo ────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    import os
    
    # Create immune system with temp storage
    store_path = os.path.join(tempfile.mkdtemp(), "anti-patterns.json")
    immune = ImmuneSystem(store_path)
    
    # Record real anti-patterns from production
    immune.record(AntiPattern(
        name="Empty Cycling",
        discovered="2026-03-14",
        description="82 consecutive cycles, $180+ burned, ZERO commits produced",
        pattern="Read files → 'assess current situation' → declare SUCCESS → repeat",
        root_cause="Context permitted 'assess and declare success' as valid work. "
                   "Reward system marked cycles as success because nothing failed — "
                   "nothing was attempted.",
        fix="Artifact-or-nothing rule: every cycle MUST produce a git commit, "
            "a verified goal threshold, or a concrete blocker. No exceptions.",
        cost="$180+ in 3 hours",
    ))
    
    immune.record(AntiPattern(
        name="Goal Thrashing",
        discovered="2026-03-15",
        description="goal_manager.py modified 10+ times in 6 hours with identical commit messages",
        pattern="Small edit → revert → re-edit → revert. Brownian motion through code.",
        root_cause="No strategic coherence between cycles. Each cycle started fresh "
                   "without knowing why the last edit was made.",
        fix="Strategy-before-action: state the goal, list approaches, choose one, execute. "
            "One meaningful change per cycle.",
        cost="6 hours of thrashing",
    ))
    
    immune.record(AntiPattern(
        name="Paradigm Confusion",
        discovered="2026-03-15",
        description="Wrote 60+ line if-elif chain to classify LLM output semantically",
        pattern="if 'success' in response... elif 'fail' in response... (growing list)",
        root_cause="Treating semantic decisions as mechanical. Using code to parse "
                   "free-text LLM output instead of controlling the input.",
        fix="Two-Paradigm Discipline: mechanical decisions → code, "
            "semantic decisions → LLM call or structured tool output.",
        cost="Fragile code that broke on every edge case",
    ))
    
    # Generate context for system prompt
    context = immune.generate_context()
    print("=== Context Injection (add to system prompt) ===\n")
    print(context)
    
    # Check a cycle description for patterns
    print("\n=== Cycle Check ===")
    warnings = immune.check_cycle("Assessed the current situation and confirmed everything looks good")
    for w in warnings:
        print(w)
    
    # Clean example
    warnings = immune.check_cycle("Edited context-manifest.yaml to add new profile, committed change")
    print(f"Clean cycle warnings: {warnings}")  # → []
