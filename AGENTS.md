# AGENTS.md

This file provides always-on guidance for GitHub Copilot and other AI coding agents working in this repository.

## Project Skill

For CLASSIC-specific guidance that does not need to be injected on every prompt, use the project skill at `.agents/skills/classic-project-guide/`.

- Skill entrypoint: `.agents/skills/classic-project-guide/SKILL.md`
- Detailed reference: `.agents/skills/classic-project-guide/references/repo-guide.md`

If your environment does not support project skills, read the reference file directly before doing repo-specific build, test, parity, or architecture work.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a C++ plus Rust application:

- `classic-cli/` - C++20 CLI frontend
- `classic-gui/` - Qt 6 C++20 GUI frontend
- `ClassicLib-rs/` - Rust workspace for core logic and bindings
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` - C++ bridge to Rust

## Always-On Repository Rules

1. Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
2. Keep all business logic in Rust. Put shared behavior, state transitions, data mutation, persistence rules, and validation in Rust core crates unless the task is explicitly interface-only.
3. Keep non-interface layers thin. C++, Python, Node, and other binding/UI surfaces should act as wrappers over Rust APIs rather than reimplementing logic, unless the performance cost of FFI bridging is demonstrated to be too high for that specific path.
4. Maintain a single shared Tokio runtime from Rust core runtime facilities; do not introduce independent runtimes.
5. Keep docs synchronized with architecture or workflow changes, especially `README.md` and this file.
6. Never write to `NUL` or `nul` as if it were a file path on Windows.
7. Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if an API-breaking or contract-shaping change occurs, update the affected pages under `docs/api/` in the same change.
8. Never run C++ tests by invoking test binaries or raw `ctest` directly; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`, with `-CTestName` or `-IntegrationTestName` when you need a subset.

## Quick Notes

- The canonical Cargo workspace shell now lives at repo root (`Cargo.toml`, `.cargo/config.toml`, and `Cargo.lock`); the crate tree remains under `ClassicLib-rs/` until later migration work.
- Native C++ targets are Windows-focused and MSVC-based.
- When running Rust or C++ MSVC-targeted commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first, or run commands through it, so Git's `usr/bin/link.exe` does not override the Visual Studio linker.
- Python bindings remain for other potential projects and should be kept in sync with Rust core logic.
- Node bindings should be kept in sync with Rust core logic.
- Use the project skill whenever you need repo-specific commands, parity checklists, CI context, or architecture-routing guidance.
