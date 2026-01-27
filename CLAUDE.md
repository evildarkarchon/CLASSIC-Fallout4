# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About CLASSIC

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a hybrid Python-Rust desktop application analyzing crash logs from Bethesda games (Fallout 4, Skyrim). Python 3.12+, uv package manager, PyO3 0.27 bindings.

## Quick Reference

```bash
# Development
uv sync --all-extras
uv run python CLASSIC_Interface.py  # GUI
uv run python CLASSIC_ScanLogs.py   # CLI

# Testing
uv run pytest -m "unit and not slow"

# Rust
./rebuild_rust.ps1              # Build all
./rebuild_rust.ps1 yaml         # Build specific
```

## Essential Rules

1. **TDD Required** - Use `/tdd` skill
2. **No print()** - Use MessageHandler
3. **Use pathlib.Path** - Never string paths
4. **Async-first** - AsyncBridge for GUI sync contexts only
5. **Google-style docstrings** - Use `/python-docstrings` skill
6. **ONE RUNTIME** - Single global Tokio runtime
7. **Separate crates** - Business logic in `-core`, PyO3 in `-py`
8. **Lazy YAML imports** - Import `yaml_settings`, `classic_settings` inside functions to avoid circular imports

## Skills

| Skill | Purpose |
|-------|---------|
| `/tdd` | Test-driven development workflow |
| `/python-docstrings` | Google-style docstring format |
| `/rust-crate` | Create new Rust crates |
| `/ci-check` | Run local CI checks |

## Rules

Detailed standards in `.claude/rules/`:
- `01-project-overview.md` - Setup and commands
- `02-architecture.md` - Hybrid architecture
- `03-testing.md` - Test organization and fixtures
- `04-development.md` - Code quality standards
- `05-memories.md` - Historical decisions
