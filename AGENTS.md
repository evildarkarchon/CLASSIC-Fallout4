# AGENTS.md

This file provides always-on guidance for GitHub Copilot and other AI coding agents working in this repository.

## Project Skill

For CLASSIC-specific guidance that does not need to be injected on every prompt, use the project skill at `.agents/skills/classic-project-guide/`.

- Skill entrypoint: `.agents/skills/classic-project-guide/SKILL.md`
- Detailed reference: `.agents/skills/classic-project-guide/references/repo-guide.md`

If your environment does not support project skills, read the reference file directly before doing repo-specific build, test, parity, or architecture work.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a repo-root Cargo workspace with native frontends and thin binding layers:

- `foundation/` - shared runtime, utilities, and cross-cutting Rust support crates
- `business-logic/` - Rust core logic crates
- `cpp-bindings/classic-cpp-bridge/` - C++ bridge to Rust
- `node-bindings/classic-node/` - Node/Bun binding package
- `python-bindings/` - Python binding crates, tooling, and binding-local virtualenv
- `ui-applications/classic-tui/` - Rust TUI application
- `classic-cli/` - C++20 CLI frontend
- `classic-gui/` - Qt 6 C++20 GUI frontend

For old-to-new path and command translations, see `docs/workspace-migration-matrix.md`.

## Always-On Repository Rules

1. Prioritize active work in `classic-cli/`, `classic-gui/`, `foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`.
2. Keep all business logic in Rust. Put shared behavior, state transitions, data mutation, persistence rules, and validation in Rust core crates unless the task is explicitly interface-only.
3. Keep non-interface layers thin. C++, Python, Node, and other binding/UI surfaces should act as wrappers over Rust APIs rather than reimplementing logic, unless the performance cost of FFI bridging is demonstrated to be too high for that specific path.
4. Maintain a single shared Tokio runtime from Rust core runtime facilities; do not introduce independent runtimes.
5. Keep docs synchronized with architecture or workflow changes, especially `README.md` and this file.
6. Never write to `NUL` or `nul` as if it were a file path on Windows.
7. Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if an API-breaking or contract-shaping change occurs, update the affected pages under `docs/api/` in the same change.
8. Never run C++ tests by invoking test binaries or raw `ctest` directly; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`, with `-CTestName` or `-IntegrationTestName` when you need a subset.
9. Never run Python binding tests against an unbuilt virtualenv. Before `pytest python-bindings/tests`, run `./rebuild_rust.ps1 -Target python` to maturin-build and install every `-py` crate into `python-bindings/.venv/`, then invoke pytest via `uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q`. Skipping the rebuild yields `ModuleNotFoundError` at collection time; `uv run --python <venv>/Scripts/python.exe` pins the interpreter so a stale global `VIRTUAL_ENV` cannot redirect pytest to the wrong Python.
10. Put Rust unit tests in a sibling submodule file, never in an inline `#[cfg(test)] mod tests { ... }` block. For a source file `src/<name>.rs`, tests live in `src/<name>_tests.rs` and the parent declares them with a single line: `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;` (the `#[path]` attribute is required so the sibling resolves alongside `<name>.rs` instead of under a `<name>/` directory). This applies to every Rust crate under `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, `ui-applications/classic-tui/`, and any future crate added under those layer roots. Cargo integration tests in `tests/` and benches in `benches/` are out of scope and stay where they are. Full contract: `openspec/specs/rust-test-module-layout/spec.md`.

## Quick Notes

- The canonical Cargo workspace shell now lives at repo root (`Cargo.toml`, `.cargo/config.toml`, and `Cargo.lock`), and the live Rust crate tree now uses the repo-root layer directories (`foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`).
- Native C++ targets are Windows-focused and MSVC-based.
- When running Rust or C++ MSVC-targeted commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first, or run commands through it, so Git's `usr/bin/link.exe` does not override the Visual Studio linker.
- Python bindings under `python-bindings/` should stay in sync with Rust core logic.
- Before any cargo command that touches pyo3 (workspace builds/tests, `rebuild_rust.ps1 -Target python`, the Python parity gate), set `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` for the current shell. `.cargo/config.toml` intentionally omits a global pin (a `[env]` entry would leak to non-Windows targets and break Linux/macOS builds); contributors set it per-shell. A stale global `VIRTUAL_ENV` — pointing at a removed or moved Python install — will otherwise win and fail pyo3-build-config with "The system cannot find the file specified".
- Node bindings under `node-bindings/classic-node/` should stay in sync with Rust core logic.
- Use the project skill whenever you need repo-specific commands, parity checklists, CI context, or architecture-routing guidance.
