# AGENTS.md

This file provides always-on guidance for GitHub Copilot and other AI coding agents working in this repository.

## Project Skills

For CLASSIC-specific guidance that does not need to be injected on every prompt, use the project skill at `.agents/skills/classic-project-guide/`.

- Skill entrypoint: `.agents/skills/classic-project-guide/SKILL.md`
- Detailed reference: `references/repo-guide.md` relative to that `SKILL.md`

OpenSpec workflow skills (for example `openspec-apply-change`, `openspec-archive-change`) also live under `.agents/skills/`. Cursor may mirror them under `.cursor/skills/`.

If your environment does not support project skills, read the reference file next to the skill entrypoint before doing repo-specific build, test, parity, or architecture work.

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
8. Never run C++ tests by invoking test binaries or raw `ctest` directly; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test` and pass `-CTestName <name[,name...]>` when you need a subset. The CLI wrapper additionally accepts `-IntegrationTestName <name[,name...]>` for its integration test subset; the GUI wrapper has no `-IntegrationTestName` parameter (passing it will fail with "parameter cannot be found").
9. Never run Python binding tests against an unbuilt virtualenv. The `python-bindings/` tree is a uv-managed project (`python-bindings/pyproject.toml`, `python-bindings/uv.lock`); create/refresh `python-bindings/.venv/` with `uv sync --project python-bindings --inexact`, then run `./rebuild_rust.ps1 -Target python` to maturin-build and install every `-py` crate into the venv, then invoke pytest via `uv run --project python-bindings python -m pytest python-bindings/tests -q`. Use `python -m pytest`, NOT the `pytest.exe` console-script entrypoint: `classic_config.ClassicConfig.get_config_path()` anchors settings lookup to `sys.argv[0]`'s parent, and `.venv\Scripts\pytest.exe` triggers a script-directory shape that breaks `test_runtime_coverage_registry_cases`. `--inexact` is load-bearing on every `uv sync` — it prevents uv from pruning the maturin-built `classic-*-py` wheels (they are not declared in `pyproject.toml`). Skipping the rebuild yields `ModuleNotFoundError` at collection time. Use `--group drift-guards` on the `uv sync` line when you need `ruamel.yaml` for `tools/schema_version_gate.py`.
10. Put Rust unit tests in a sibling submodule file, never in an inline `#[cfg(test)] mod tests { ... }` block. For a source file `src/<name>.rs`, tests live in `src/<name>_tests.rs` and the parent declares them with a single line: `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;` (the `#[path]` attribute is required so the sibling resolves alongside `<name>.rs` instead of under a `<name>/` directory). This applies to every Rust crate under `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, `ui-applications/classic-tui/`, and any future crate added under those layer roots. Cargo integration tests in `tests/` and benches in `benches/` are out of scope and stay where they are. Full contract: `openspec/specs/rust-test-module-layout/spec.md`.

## Quick Notes

- The canonical Cargo workspace shell now lives at repo root (`Cargo.toml`, `.cargo/config.toml`, and `Cargo.lock`), and the live Rust crate tree now uses the repo-root layer directories (`foundation/`, `business-logic/`, `cpp-bindings/`, `node-bindings/`, `python-bindings/`, and `ui-applications/`).
- Native C++ targets are Windows-focused and MSVC-ABI-based; the build wrappers default to MSVC and also support `-Compiler clang-cl`, which keeps the MSVC ABI while using clang-cl for CMake, vcpkg, and Cargo `cc-rs`/`cxx_build` C++ bridge glue.
- When running Rust or C++ MSVC-targeted commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first, or run commands through it, so Git's `usr/bin/link.exe` does not override the MSVC-compatible linker.
- Belt-and-suspenders for the above: `cmake/ClassicLinkerCheck.cmake` is included by both `classic-gui/CMakeLists.txt` and `classic-cli/CMakeLists.txt` and validates the linker CMake resolved for the active MSVC/MSVC-ABI configure (falling back to PATH only when CMake has not resolved one yet). The guard still fails fast with `FATAL_ERROR` when it detects Git for Windows' `link.exe` or any other non-MSVC-compatible linker, but it no longer rejects a valid VS Code/CMake Tools configure just because Git's `usr/bin` appears earlier on PATH.
- Python bindings under `python-bindings/` should stay in sync with Rust core logic.
- Before any cargo command that touches pyo3 (workspace builds/tests, `rebuild_rust.ps1 -Target python`, the Python parity gate), set `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` for the current shell. `.cargo/config.toml` intentionally omits a global pin (a `[env]` entry would leak to non-Windows targets and break Linux/macOS builds); contributors set it per-shell. A stale global `VIRTUAL_ENV` — pointing at a removed or moved Python install — will otherwise win and fail pyo3-build-config with "The system cannot find the file specified".
- Node bindings under `node-bindings/classic-node/` should stay in sync with Rust core logic.
- Use the project skill whenever you need repo-specific commands, parity checklists, CI context, or architecture-routing guidance.
- App-update notification publishes are triggered by the `app-notification-v*` tag namespace and the `.github/workflows/publish-app-notification.yml` workflow. The source-of-truth artifact is `CLASSIC Data/app-notification.yaml`; the validator and generator live under `tools/publish_app_notification/`. This tag namespace is disjoint from the `yaml-data-v*` publish channel and from the `v*` binary-release tag; the binary-release "latest" pointer is preserved via `--latest=false` at every `gh release edit` step. Full contract: `docs/api/app-update-notification-delivery.md`.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- For graphify extraction, rebuild, clustering, or labeling commands that accept a backend, pass `--backend openai` unless the user explicitly requests another backend.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
