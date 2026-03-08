# AGENTS.md

This file provides always-on guidance for GitHub Copilot and other AI coding agents working in this repository.

## Project Skill

For CLASSIC-specific guidance that does not need to be injected on every prompt, use the project skill at `.opencode/skills/classic-project-guide/`.

- Skill entrypoint: `.opencode/skills/classic-project-guide/SKILL.md`
- Detailed reference: `.opencode/skills/classic-project-guide/references/repo-guide.md`

If your environment does not support project skills, read the reference file directly before doing repo-specific build, test, parity, or architecture work.

## Project Overview

CLASSIC (Crash Log Auto Scanner & Setup Integrity Checker) is a C++ plus Rust application:

- `classic-cli/` - C++20 CLI frontend
- `classic-gui/` - Qt 6 C++20 GUI frontend
- `ClassicLib-rs/` - Rust workspace for core logic and bindings
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` - C++ bridge to Rust

The prior Python implementation is archived under `deprecated/`.

## Always-On Repository Rules

1. Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
2. Treat `deprecated/` as archival unless the task explicitly targets migration or legacy maintenance.
3. Maintain a single shared Tokio runtime from Rust core runtime facilities; do not introduce independent runtimes.
4. Keep docs synchronized with architecture or workflow changes, especially `README.md` and this file.
5. Never write to `NUL` or `nul` as if it were a file path on Windows.

## Quick Notes

- Native C++ targets are Windows-focused and MSVC-based.
- Python bindings remain for legacy/deprecation support; they are not the default destination for new feature work.
- Use the project skill whenever you need repo-specific commands, parity checklists, CI context, or architecture-routing guidance.
