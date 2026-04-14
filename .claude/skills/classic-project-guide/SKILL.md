---
name: classic-project-guide
description: CLASSIC-specific repository guidance for architecture routing, repo-approved build/test/package commands, Windows/MSVC constraints, Node and Python parity workflows, and repo-specific docs or CI follow-up. Use when work depends on where code belongs in CLASSIC, which local validation commands or release gates apply, which parity artifacts or docs must change, or how repository runtime/platform rules affect implementation. Skip for generic coding, debugging, design, or language-only tasks that do not depend on CLASSIC-specific workflow or architecture.
---

Use this skill only when the task depends on CLASSIC-specific repository policy or structure.

## Route The Work

Classify the request before editing or recommending commands.

- Put shared product behavior in the repo-root Rust layers, especially `foundation/` and `business-logic/`, for validation, persistence rules, runtime facilities, and binding-facing behavior.
- Keep `classic-cli/` and `classic-gui/` focused on native frontend and integration concerns.
- Keep `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/` aligned with Rust APIs instead of reimplementing logic.

For legacy-to-live path and command translation, use `docs/workspace-migration-matrix.md`.

## Read Only What You Need

Load `references/repo-guide.md` selectively.

- Read `Architecture Map` when deciding where code belongs.
- Read `Build, Test, and Validation Commands` before suggesting or running repo commands.
- Read `Node API Parity Workflow` when Node-exposed Rust APIs or generated TypeScript artifacts may change.
- Read `Python API Parity Workflow` when Python-exposed Rust APIs, stubs, or parity artifacts may change.
- Read `CI and Platform Notes` when workflow expectations, portability, or Windows/MSVC constraints matter.

## Apply Repo Guardrails

- Keep business logic in Rust and keep non-interface layers thin unless the task is explicitly interface-only.
- Maintain the single shared Tokio runtime from Rust core facilities; do not introduce a separate runtime.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs. If the contract changes, update the affected `docs/api/` pages in the same change.
- NEVER run C++ tests by invoking test binaries or raw `ctest` directly. Always use the repo PowerShell C++ wrappers for test execution.
- If running Rust or MSVC-targeted C++ commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first, or run commands through it so Git's `usr/bin/link.exe` does not shadow the Visual Studio linker.
- Never write to `NUL` or `nul` as if it were a normal file path on Windows.

## Match Validation To The Touched Surface

- For `classic-cli/` or `classic-gui/`, use the repo PowerShell wrapper scripts from the reference guide for build, install, package, clean rebuild, and all C++ test flows, including targeted runs via `-CTestName` and `-IntegrationTestName`.
- For Rust workspace changes, expect `cargo fmt`, `cargo clippy`, and the relevant `cargo test` commands from the repo-root workspace.
- For Node binding changes, treat parity artifacts and binding tests as part of the same change and use the local parity gate plus Bun and Node test commands from the reference guide.
- For Python binding changes, use `python-bindings/.venv` rather than a repo-root virtual environment, then run the parity gate, stub validation, rebuild, and pytest steps from the reference guide.
- For Linux or cloud validation, prefer portable Rust-only subsets when native Windows-focused surfaces are not practical to build.

## State Repo-Specific Follow-Up Explicitly

- Name the repo surface you chose and why.
- Name the exact validation commands that fit the touched area.
- Call out skipped parity artifacts, docs, packaging, or CI-relevant checks instead of implying they were handled.
