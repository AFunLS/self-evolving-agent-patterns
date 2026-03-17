"""
Minimal Context Builder — Manifest-Driven System Prompt Assembly
================================================================

The context builder is the most important component in an LLM agent.
It reads a manifest (YAML config) and assembles the system prompt from
prioritized sections — giving different agent roles different views of
the same system.

Think of it as a camera with different lenses:
- Evolution lens: shows code, architecture, safety rules
- Goal work lens: shows goals, tools, recent outcomes
- Scheduling lens: shows just goals + budget (lightweight)
- Critic lens: hides goals/identity to prevent self-serving bias

This is ~100 lines of Python. The value isn't in code complexity —
it's in the DESIGN of what goes where and why.

From a production system with 1,000+ autonomous cycles.
Full guide: https://tutuoai.com (Context Engineering skill)
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ContextSection:
    """A section of the system prompt."""
    id: str
    content: str
    priority: int = 50       # Higher = more important = trimmed last
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.content)


@dataclass
class ContextResult:
    """Result of building context for a specific purpose."""
    purpose: str
    sections: list[ContextSection]
    total_chars: int = 0
    sections_trimmed: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.total_chars = sum(s.char_count for s in self.sections)

    @property
    def system_prompt(self) -> str:
        """Assemble sections into the final system prompt."""
        return "\n\n---\n\n".join(s.content for s in self.sections)


class ContextBuilder:
    """
    Manifest-driven context assembly.
    
    Usage:
        builder = ContextBuilder(".")  # project root
        result = builder.build("goal_work")
        
        # Use as system prompt
        response = client.messages.create(
            model="claude-opus-4-20250918",
            system=result.system_prompt,
            messages=[{"role": "user", "content": "Execute the next task."}],
            tools=tool_registry.get_api_tools(),
        )
    """

    def __init__(self, project_root: str, manifest_path: str = "state/context-manifest.yaml"):
        self.root = Path(project_root)
        self.manifest_path = self.root / manifest_path
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        """Load the context manifest YAML."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Context manifest not found: {self.manifest_path}")
        return yaml.safe_load(self.manifest_path.read_text())

    def _load_section(self, section_config: dict) -> ContextSection | None:
        """Load a single section from file."""
        file_path = self.root / section_config["file"]
        if not file_path.exists():
            return None
        
        content = file_path.read_text().strip()
        if not content:
            return None
            
        return ContextSection(
            id=section_config["id"],
            content=content,
            priority=section_config.get("priority", 50),
        )

    def _run_generators(self):
        """
        Run dynamic generators that produce fresh content each cycle.
        
        In production, these compute runtime state, goal progress,
        budget remaining, etc. For this example, we skip actual execution.
        """
        for gen in self.manifest.get("generators", []):
            output_path = self.root / gen["output"]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # In production: importlib.import_module(gen["module"]).generate(self.root)
            # For this example, we just ensure the file exists
            if not output_path.exists():
                output_path.write_text(f"# {gen['description']}\n\nNo data yet.\n")

    def build(self, purpose: str = "general") -> ContextResult:
        """
        Build context for a specific purpose (profile).
        
        This is where the magic happens:
        1. Look up the profile in the manifest
        2. Load only the sections that profile includes
        3. If total chars exceed budget, trim lowest-priority sections first
        4. Return assembled context
        """
        # Run generators first (fresh data each cycle)
        self._run_generators()
        
        # Get profile config
        profiles = self.manifest.get("profiles", {})
        profile = profiles.get(purpose, profiles.get("general", {}))
        budget_chars = profile.get("budget_chars", 200_000)
        include = profile.get("include", "all")
        
        # Determine which sections to include
        all_sections = self.manifest.get("sections", [])
        if include == "all":
            section_ids = {s["id"] for s in all_sections}
        else:
            section_ids = set(include)
        
        # Load included sections
        loaded: list[ContextSection] = []
        for section_config in all_sections:
            if section_config["id"] not in section_ids:
                continue
            section = self._load_section(section_config)
            if section:
                loaded.append(section)
        
        # Add role file if specified
        role_file = profile.get("role_file")
        if role_file:
            role_path = self.root / role_file
            if role_path.exists():
                loaded.append(ContextSection(
                    id="role",
                    content=role_path.read_text().strip(),
                    priority=99,  # Role context is high priority
                ))
        
        # Sort by priority (highest first — these survive trimming)
        loaded.sort(key=lambda s: s.priority, reverse=True)
        
        # Trim to budget (drop lowest-priority sections first)
        result_sections: list[ContextSection] = []
        trimmed: list[str] = []
        remaining_budget = budget_chars
        
        for section in loaded:
            if section.char_count <= remaining_budget:
                result_sections.append(section)
                remaining_budget -= section.char_count
            else:
                trimmed.append(section.id)
        
        return ContextResult(
            purpose=purpose,
            sections=result_sections,
            sections_trimmed=trimmed,
        )


# ── Demo ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Context Builder — Manifest-Driven Assembly")
    print("=" * 50)
    print()
    print("Key concepts:")
    print()
    print("1. MANIFEST defines what exists (sections, generators, profiles)")
    print("2. PROFILES define what each role sees (evolution vs goal_work vs critic)")
    print("3. PRIORITY determines what gets trimmed when context is too large")
    print("4. GENERATORS produce fresh data each cycle (not static)")
    print()
    print("The power is in the DESIGN, not the code:")
    print("- Evolution profile includes architecture + code_quality → safe self-modification")
    print("- Critic profile EXCLUDES soul + goals → prevents self-serving evaluation")
    print("- Scheduling profile is lightweight → fast, cheap decisions")
    print("- Orchestrator profile includes everything → full awareness")
    print()
    print("To use this in your project:")
    print("1. Copy examples/context-manifest.yaml to your project")
    print("2. Create the referenced files (state/soul.md, etc.)")
    print("3. Instantiate ContextBuilder and call build('purpose_name')")
    print("4. Pass result.system_prompt to your LLM API call")
    print()
    print("Full implementation guide: https://tutuoai.com")
