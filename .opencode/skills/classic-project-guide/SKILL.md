---
name: classic-project-guide
description: CLASSIC-specific repository guidance for architecture routing, repo-approved build/test/parity/publish commands, Windows/MSVC constraints, PyO3 environment setup, and repo-specific docs or CI follow-up. Use when work depends on where code belongs in CLASSIC, which local validation or parity gates apply, which tracked artifacts or docs must change, or how repo-specific runtime/platform rules affect implementation. Skip for generic coding, debugging, design, or language-only tasks that do not depend on CLASSIC-specific workflow or architecture.
---

Use this skill only when the task depends on CLASSIC-specific repository policy or structure.

## Route The Work

Classify the request before editing or recommending commands.

- Put shared product behavior in the repo-root Rust layers, especially `foundation/` and `business-logic/`, for validation, persistence rules, runtime facilities, YAML/schema handling, and binding-facing behavior.
- Keep `classic-cli/` and `classic-gui/` focused on native frontend and integration concerns.
- Keep `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/` aligned with Rust APIs instead of reimplementing logic.
- Treat `ClassicLib-rs/` as historical residue only. For old-to-new path and command translation, use `docs/workspace-migration-matrix.md` instead of copying legacy path prose.

## Read Only What You Need

Load `references/repo-guide.md` selectively.

- Read `Architecture Map` when deciding where code belongs or translating older `ClassicLib-rs/...` guidance.
- Read `Build, Test, and Validation Commands` before suggesting or running repo commands.
- Read `CXX API Parity Workflow` when `cpp-bindings/classic-cpp-bridge/` or `#[cxx::bridge]` items may change.
- Read `Node API Parity Workflow` when Node-exposed Rust APIs or generated TypeScript artifacts may change.
- Read `Python API Parity Workflow` when Python-exposed Rust APIs, stubs, tracked parity artifacts, or PyO3 build flows may change.
- Read `YAML Data Publish Workflow` when changing `CLASSIC Data/databases/`, `schema_version` behavior, or YAML-data release automation.
- Read `CI and Platform Notes` when workflow expectations, portability, submodules, Windows/MSVC constraints, or release workflows matter.

## Apply Repo Guardrails

- Keep business logic in Rust and keep non-interface layers thin unless the task is explicitly interface-only.
- Maintain the single shared Tokio runtime from Rust core facilities; do not introduce a separate runtime.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs. If the contract changes, update the affected `docs/api/` pages in the same change.
- NEVER run C++ tests by invoking test binaries or raw `ctest` directly. Always use the repo PowerShell C++ wrappers for test execution.
- Before local cargo commands that touch PyO3 or `rebuild_rust.ps1 -Target python`, set `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` for the current shell. `.cargo/config.toml` intentionally does not pin it globally.
- Keep Rust unit tests in sibling `*_tests.rs` files declared with `#[cfg(test)] #[path = "<name>_tests.rs"] mod tests;`. Do not introduce inline `#[cfg(test)] mod tests { ... }` blocks.
- If running Rust or MSVC-targeted C++ commands from Git Bash, source `tools/use_msvc_from_git_bash.sh` first, or run commands through it so Git's `usr/bin/link.exe` does not shadow the Visual Studio linker.
- Never write to `NUL` or `nul` as if it were a normal file path on Windows.

## Match Validation To The Touched Surface

- For `classic-cli/` or `classic-gui/`, use the repo PowerShell wrapper scripts from the reference guide for build, install, package, clean rebuild, and all C++ test flows. CLI integration tests need `git submodule update --init --recursive` so `sample_logs/FO4` is present.
- For Rust workspace changes, use the repo-root `cargo fmt`, `cargo clippy`, and relevant `cargo test` commands from the reference guide. If the command touches PyO3, set `PYO3_PYTHON` first.
- For C++ bridge changes, run `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` and refresh the committed baseline only when the drift is intentional.
- For Node binding changes, treat `docs/implementation/node_api_parity/baseline/`, `node-bindings/classic-node/index.d.ts`, the runtime coverage registry, and the Bun/Node test flows as part of the same change. `node-bindings/classic-node/parity-artifacts/` are local diagnostics and should not be committed.
- For Python binding changes, use `python-bindings/.venv` rather than a repo-root virtual environment, then run the parity gate, stub validation, schema-version drift guard when relevant, rebuild, and pytest sequence from the reference guide. `python-bindings/parity-artifacts/` are tracked and may need refreshing in the same change.
- For YAML-data or `schema_version` changes, run the schema drift guard and publish validation commands from the reference guide, and account for the `publish-yaml-data.yml` workflow when describing release impact.
- For Linux or cloud validation, prefer Rust-only subsets or source-only parity gates when native Windows-focused surfaces are not practical to build.

## State Repo-Specific Follow-Up Explicitly

- Name the repo surface you chose and why.
- Name the exact validation commands that fit the touched area.
- Call out skipped parity artifacts, docs, schema/publish workflow, packaging, submodule setup, or CI-relevant checks instead of implying they were handled.
