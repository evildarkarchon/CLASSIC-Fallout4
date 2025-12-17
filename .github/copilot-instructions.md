# CLASSIC-Fallout4 Copilot Instructions

## Project Overview
Hybrid Python-Rust desktop app for analyzing Bethesda game crash logs.
- **Core**: Python (PySide6 GUI, CLI) + Rust (Performance critical ops).
- **Package Managers**: `uv` (Python), `cargo` (Rust).

## Architecture & Patterns
- **Hybrid Structure**: 
  - **Python**: `ClassicLib` (Logic), `CLASSIC_Interface.py` (GUI), `CLASSIC_ScanLogs.py` (CLI).
  - **Rust**: 3-Layer Architecture in `rust/`:
    1. **Foundation**: `classic-shared` (Runtime, Errors).
    2. **Business Logic**: `*-core` crates (Pure Rust, NO PyO3).
    3. **Bindings**: `*-py` crates (PyO3 adapters, depends on `-core`).
- **One Runtime Rule**: All Rust crates share a single global Tokio runtime via `classic_shared::get_runtime()`.
- **Async Strategy**: 
  - **Python**: Async-first. Use `AsyncBridge.run_async()` for sync contexts (GUI).
  - **Rust**: Native async.
- **Integration**: Transparent acceleration. Python falls back to pure Python impl if Rust module missing.

## Critical Workflows
- **Setup**: `uv sync --all-extras` (Python), `cargo build --workspace` (Rust).
- **Run**: `uv run python CLASSIC_Interface.py` (GUI), `uv run python CLASSIC_ScanLogs.py` (CLI).
- **Rebuild Bindings**: `.\rebuild_rust.ps1` (Windows) or `maturin build`. **Required after Rust changes.**
- **Testing**: `uv run python -m pytest -n auto` (Terminal only). **VS Code Test Explorer freezes.**
  - Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.rust`.

## Coding Conventions
- **Python**:
  - **No `print()`**: Use `ClassicLib.MessageHandler` (`msg_info`, `msg_error`).
  - **Paths**: Always use `pathlib.Path`.
  - **Docs**: Google-style docstrings required.
  - **Types**: Python 3.12+ type hints mandatory.
- **Rust**:
  - **Stubs**: `.pyi` files mandatory for all `-py` crates.
  - **Exceptions**: Map Rust errors to Python exceptions in `-py` crates.
  - **Docs**: `///` doc comments required for all public items.

## Key Files
- `CLASSIC_Interface.py`: Main GUI Entry.
- `ClassicLib/AsyncBridge.py`: Sync/Async bridge.
- `rust/Cargo.toml`: Workspace definition.
- `rebuild_rust.ps1`: Rust build script.

## Issue Tracking with bd

This project uses **bd (beads)** for issue tracking - a Git-backed tracker designed for AI-supervised coding workflows.

**Key Features:**
- Dependency-aware issue tracking
- Auto-sync with Git via JSONL
- AI-optimized CLI with JSON output
- Built-in daemon for background operations
- MCP server integration for Claude and other AI assistants

**CRITICAL**: Use bd for ALL task tracking. Do NOT create markdown TODO lists.

### Essential Commands

```bash
# Find work
bd ready --json                    # Unblocked issues
bd stale --days 30 --json          # Forgotten issues

# Create and manage
bd create "Title" -t bug|feature|task -p 0-4 --json
bd create "Subtask" --parent <epic-id> --json  # Hierarchical subtask
bd update <id> --status in_progress --json
bd close <id> --reason "Done" --json

# Search
bd list --status open --priority 1 --json
bd show <id> --json

# Sync (CRITICAL at end of session!)
bd sync  # Force immediate export/commit/push
```

### Workflow

1. **Check ready work**: `bd ready --json`
2. **Claim task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** `bd create "Found bug" -p 1 --deps discovered-from:<parent-id> --json`
5. **Complete**: `bd close <id> --reason "Done" --json`
6. **Sync**: `bd sync` (flushes changes to git immediately)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Git Workflow

- Always commit `.beads/issues.jsonl` with code changes
- Run `bd sync` at end of work sessions
- Install git hooks: `bd hooks install` (ensures DB <-> JSONL consistency)

### MCP Server (Recommended)

For MCP-compatible clients (Claude Desktop, etc.), install the beads MCP server:
- Install: `pip install beads-mcp`
- Functions: `mcp__beads__ready()`, `mcp__beads__create()`, etc.

## CLI Help

Run `bd <command> --help` to see all available flags for any command.
For example: `bd create --help` shows `--parent`, `--deps`, `--assignee`, etc.

## Important Rules

- Use bd for ALL task tracking
- Always use `--json` flag for programmatic use
- Run `bd sync` at end of sessions
- Run `bd <cmd> --help` to discover available flags
- Do NOT create markdown TODO lists
- Do NOT commit `.beads/beads.db` (JSONL only)
