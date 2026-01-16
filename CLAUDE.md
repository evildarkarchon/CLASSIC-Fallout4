# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About CLASSIC

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a high-performance hybrid Python-Rust desktop application that analyzes crash logs from Bethesda games (Fallout 4 and Skyrim).

**Key characteristics**:
- Hybrid Python-Rust architecture (10-150x Rust acceleration)
- GUI (PySide6/Qt), CLI (Python), and TUI (Ratatui/Rust) interfaces
- PyO3 0.27 bindings with native async solution
- Python 3.12+ required, uv package manager

## Documentation Structure

Detailed rules and standards are in `.claude/rules/`:
- `01-project-overview.md` - Quick start, development setup
- `02-architecture.md` - Hybrid architecture, Rust directory structure
- `03-testing-standards.md` - Test organization, critical rules
- `04-ci-cd.md` - CI pipeline, local checks
- `05-code-quality.md` - Development rules, anti-patterns
- `06-python-documentation.md` - Google-style docstring standards
- `07-rust-development.md` - Rust docs, PyO3, guides
- `08-memories.md` - Historical decisions, bug fixes

## Quick Reference

```bash
# Development
uv sync --all-extras
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing
uv run pytest -n auto -m "unit and not slow"

# Rust
./rebuild_rust.ps1              # Build all
./rebuild_rust.ps1 yaml         # Build specific
```

## Essential Rules

1. **No print()** - Use MessageHandler
2. **Use pathlib.Path** - Never string paths
3. **Async-first** - Use AsyncBridge for sync contexts
4. **Google-style docstrings** - All modules, classes, functions
5. **ONE RUNTIME RULE** - Single global Tokio runtime
6. **Business logic separation** - `-core` crates separate from `-py` crates
