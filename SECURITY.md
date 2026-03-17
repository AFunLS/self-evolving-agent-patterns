# Security Policy

## ⚠️ Important: AI Agent Security

This package creates AI agents that can **execute shell commands** and **modify files**. This is by design — agents need real tools to be useful. However:

- **Never run agents with elevated privileges** (no sudo, no root)
- **Use in sandboxed environments** when possible (containers, VMs)
- **Review the default tools** in `src/agent_patterns/tools.py` before use
- **The self-evolution feature** (`self_evolving=True`) allows the agent to modify its own prompt file — review changes periodically

## Reporting Vulnerabilities

If you discover a security issue, please email **hello@tutuoai.com** instead of opening a public issue.

We'll respond within 48 hours and work with you to address the issue.

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Current          |
