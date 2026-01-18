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

1. **TDD Required** - Write failing tests first, then implement (see `.claude/skills/tdd/SKILL.md`)
2. **No print()** - Use MessageHandler
3. **Use pathlib.Path** - Never string paths
4. **Async-first** - Use AsyncBridge for sync contexts
5. **Google-style docstrings** - All modules, classes, functions
6. **ONE RUNTIME RULE** - Single global Tokio runtime
7. **Business logic separation** - `-core` crates separate from `-py` crates

## Test-Driven Development

**All new features and bug fixes MUST follow TDD.** AI agents should use the TDD skill.

```bash
# TDD Workflow: Red -> Green -> Refactor
# 1. Write failing test
# 2. Implement minimal code to pass
# 3. Refactor with tests as safety net
```

See `.claude/skills/tdd/SKILL.md` for complete TDD patterns including async testing, Rust integration tests, and fixture organization.

## Test Fixtures

- **All fixtures in `tests/fixtures/`** - centralized, never in individual test files
- **Exception**: Local `conftest.py` allowed ONLY for `autouse=True` fixtures needing directory scoping
- Autouse wrappers call centralized implementations to avoid overhead on unrelated tests
