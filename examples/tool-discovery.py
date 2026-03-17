"""
Auto-Discovering Tool Registration for LLM Agents
==================================================

Drop a .py file in the tools/ directory → it's automatically available to the agent.
No manual imports, no registration lists, no code changes needed.

This pattern eliminates "tool rot" — where someone adds a tool file but forgets
to register it, or removes a tool but forgets to unregister it.

From a production system with 13 auto-discovered tools and 1,000+ autonomous cycles.
Full guide: https://tutuoai.com (Tool & Function Calling Mastery skill)
"""

import importlib
import pkgutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class ToolDef:
    """Definition of a tool the LLM can call."""
    name: str
    description: str
    handler: Callable
    input_schema: dict = field(default_factory=dict)

    def to_api_format(self) -> dict:
        """Convert to Anthropic/OpenAI tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.input_schema.get("properties", {}),
                "required": self.input_schema.get("required", []),
            },
        }


class ToolRegistry:
    """
    Registry that auto-discovers tools from a package directory.
    
    Usage:
        registry = ToolRegistry()
        registry.auto_discover("my_agent.tools")  # scans the package
        
        # Get tools for API call
        tools = registry.get_api_tools()
        
        # Execute a tool call from the LLM
        result = registry.execute("read_file", {"path": "README.md"})
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef):
        """Register a single tool."""
        self._tools[tool.name] = tool

    def auto_discover(self, package_name: str):
        """
        Scan a Python package for modules that export tools.
        
        Each module must have a `register_tools(registry)` function.
        This convention means:
        - Adding a tool = drop a .py file with register_tools()
        - Removing a tool = delete the .py file
        - No central registry to maintain
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            print(f"Warning: Could not import {package_name}: {e}")
            return

        package_path = Path(package.__file__).parent

        for module_info in pkgutil.iter_modules([str(package_path)]):
            module_name = f"{package_name}.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
                # Convention: each tool module has register_tools(registry)
                if hasattr(module, "register_tools"):
                    module.register_tools(self)
            except Exception as e:
                # Never crash on a single bad tool — log and continue
                print(f"Warning: Failed to load tool {module_name}: {e}")

    def get_api_tools(self) -> list[dict]:
        """Get all tools in API format for LLM calls."""
        return [tool.to_api_format() for tool in self._tools.values()]

    def execute(self, tool_name: str, args: dict) -> Any:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return self._tools[tool_name].handler(**args)
        except Exception as e:
            return {"error": f"Tool {tool_name} failed: {str(e)}"}

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# ── Example Tool Module ─────────────────────────────────────
# Save this as tools/file_ops.py and it will be auto-discovered

def _read_file(path: str) -> dict:
    """Read a file and return its contents."""
    try:
        content = Path(path).read_text()
        return {"success": True, "content": content, "size": len(content)}
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _write_file(path: str, content: str) -> dict:
    """Write content to a file, creating parent directories."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return {"success": True, "path": str(p), "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_tools(registry: ToolRegistry):
    """Called by auto_discover — register this module's tools."""
    registry.register(ToolDef(
        name="read_file",
        description="Read the contents of a file. Use for source code, config, docs.",
        handler=_read_file,
        input_schema={
            "properties": {
                "path": {"type": "string", "description": "Path to the file"}
            },
            "required": ["path"],
        },
    ))
    registry.register(ToolDef(
        name="write_file",
        description="Create or overwrite a file. Creates parent directories.",
        handler=_write_file,
        input_schema={
            "properties": {
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    ))


# ── Demo ────────────────────────────────────────────────────

if __name__ == "__main__":
    # Create registry and discover tools
    registry = ToolRegistry()
    
    # Option 1: Auto-discover from a package
    # registry.auto_discover("my_agent.tools")
    
    # Option 2: Manual registration (for this demo)
    register_tools(registry)
    
    print(f"Registered tools: {registry.tool_names}")
    # → ['read_file', 'write_file']
    
    # Get tools in API format (pass to Anthropic/OpenAI)
    api_tools = registry.get_api_tools()
    print(f"\nAPI format for LLM:\n{api_tools[0]}")
    
    # Execute a tool call (as if the LLM requested it)
    result = registry.execute("read_file", {"path": "README.md"})
    print(f"\nTool result: {result}")
