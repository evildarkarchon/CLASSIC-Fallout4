## 1. Setup and Convention Lock-In

- [x] 1.1 Confirm baseline `cargo test --workspace` passes locally and capture the total test count (one number) so post-conversion runs can compare.
- [x] 1.2 Capture per-crate pre-conversion test counts via `cargo test -p <crate> -- --list` for every Rust crate in `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/`. Store the counts in a scratch file (gitignored) keyed by crate name; this file is the per-crate verification reference for tasks 4–10.
- [x] 1.3 Confirm CXX, Node, and Python parity gates are green before any conversion lands (`python tools/cxx_api_parity/check_parity_gate.py --repo-root .`, `bun run parity:gate` from `node-bindings/classic-node/`, `python tools/python_api_parity/check_parity_gate.py --repo-root .`).

## 2. Update Scaffolding So New Crates Use the Sibling Layout

- [x] 2.1 Update `.agents/skills/rust-crate/` (skill entrypoint + any template files it references) so generated `src/lib.rs` emits `#[cfg(test)] #[path = "lib_tests.rs"] mod tests;` and writes a sibling `src/lib_tests.rs` containing `use super::*;` plus one trivial smoke test, matching what the current template emits but in the new file. *(Note: the `rust-crate` skill actually lives at `.claude/skills/rust-crate/SKILL.md`, `.gemini/skills/rust-crate/SKILL.md`, and `.kilocode/skills/rust-crate/SKILL.md` — all three byte-identical. Edit applied to all three mirrors.)*
- [x] 2.2 Smoke-check the updated skill by running it against a throwaway crate name in a scratch directory; confirm the generated layout matches the spec's "scaffolds sibling test files" scenarios. Discard the throwaway crate. *(The `rust-crate` skill is markdown guidance rather than an executable generator; verification is a text-search confirming the skill now shows `#[cfg(test)] #[path = "lib_tests.rs"] mod tests;` with a sibling `src/lib_tests.rs` block containing `use super::*;` plus a trivial smoke test in both its Step 1.3 and Step 4.1 examples.)*
- [x] 2.3 Update any contributor docs that demonstrate the old inline `mod tests` pattern (if any references exist in the active doc set) to show the new sibling form. *(Updated: `docs/rust/pyo3_quick_reference.md`, `docs/development/cache_patterns.md`, `.claude/skills/tdd-classic/SKILL.md` (2 examples), `.gemini/skills/tdd/SKILL.md` (2 examples). Historical .planning/ docs left untouched per "active doc set" scoping.)*

## 3. Reference Conversion (classic-perf-core)

- [x] 3.1 Pick `business-logic/classic-perf-core` as the reference crate. For each source file with `#[cfg(test)] mod tests { ... }` (`src/lib.rs`, `src/metrics.rs`, `src/timer.rs`), create a sibling `<stem>_tests.rs` containing the verbatim block body (including `use super::*;` and any test-only helpers from inside the block).
- [x] 3.2 In each parent file, replace the entire former `#[cfg(test)] mod tests { ... }` block with the single line `#[cfg(test)] #[path = "<stem>_tests.rs"] mod tests;`.
- [x] 3.3 Run `cargo test -p classic-perf-core` and confirm the pass count matches the value captured in 1.2. *(16 passed unit-tests after conversion; matches baseline 16.)*
- [x] 3.4 Run `cargo fmt --all -- --check` and `cargo clippy -p classic-perf-core --all-targets --all-features -- -D warnings`. Fix any formatting drift in the new sibling files only (do not reformat unrelated code). *(classic-perf-core files are fmt-clean; pre-existing fmt drift exists in unrelated crates `classic-file-io-core`, `classic-update-core`, `classic-cpp-bridge` and is NOT modified here. `cargo clippy -p classic-perf-core --all-targets --all-features -- -D warnings` passed.)*
- [x] 3.5 Commit as a single self-contained per-crate commit; include "before: N tests, after: N tests, all pass" in the commit body so reviewers can verify at a glance.

## 4. Convert foundation/ Crates

- [ ] 4.1 Convert `foundation/classic-shared-core` (touches `src/lib.rs`, `src/async_bridge.rs`, `src/errors.rs`, `src/game_id.rs`, `src/path_core.rs`, `src/performance_core.rs`, `src/strings_core.rs`). Per-crate verification per the steps in 3.1–3.5. Commit.
- [ ] 4.2 Convert `foundation/classic-shared-py` (touches `src/error_convert.rs`, `src/exceptions.rs`, `src/indexmap_utils.rs`, `src/path.rs`). Per-crate verification. Commit.

## 5. Convert business-logic/ Wave A — Smaller Leaf Crates

- [ ] 5.1 Convert `business-logic/classic-registry-core` (`src/lib.rs`, `src/registry.rs`, `src/keys.rs`). Per-crate verification. Commit.
- [ ] 5.2 Convert `business-logic/classic-web-core` (`src/lib.rs`). Per-crate verification. Commit.
- [ ] 5.3 Convert `business-logic/classic-version-core` (`src/lib.rs`, `src/pe_version.rs`). Per-crate verification. Commit.
- [ ] 5.4 Convert `business-logic/classic-version-registry-core` (`src/defaults.rs`, `src/fallout4_version.rs`, `src/matching.rs`, `src/models.rs`, `src/registry.rs`, `src/version.rs`). Per-crate verification. Commit.
- [ ] 5.5 Convert `business-logic/classic-message-core` (`src/lib.rs`, `src/enums.rs`, `src/formatter.rs`, `src/logging.rs`, `src/message.rs`, `src/redaction.rs`). Per-crate verification. Commit.
- [ ] 5.6 Convert `business-logic/classic-resource-core` (`src/lib.rs`). Per-crate verification. Commit.
- [ ] 5.7 Convert `business-logic/classic-xse-core` (`src/lib.rs`). Per-crate verification. Commit.

## 6. Convert business-logic/ Wave B — Medium Crates

- [ ] 6.1 Convert `business-logic/classic-path-core` (`src/backup.rs`, `src/checker.rs`, `src/docs_path.rs`, `src/game_path.rs`, `src/ini_parser.rs`, `src/validator.rs`, `src/yaml_cache.rs`, `src/platform/linux.rs`, `src/platform/windows.rs`). Per-crate verification. Commit.
- [ ] 6.2 Convert `business-logic/classic-settings-core` (`src/lib.rs`, `src/cache.rs`, `src/loader.rs`, `src/schema_version.rs`, `src/validators.rs`, `src/yaml_file.rs`, `src/yaml_merge.rs`, `src/yaml_ops.rs`). Per-crate verification. Commit.
- [ ] 6.3 Convert `business-logic/classic-file-io-core` (`src/atomic_install.rs`, `src/backup.rs`, `src/core.rs`, `src/dds.rs`, `src/encoding.rs`, `src/game_files.rs`, `src/generation.rs`, `src/hash.rs`, `src/log_collection.rs`, `src/similarity.rs`). Per-crate verification. Commit.
- [ ] 6.4 Convert `business-logic/classic-database-core` (`src/pool_sqlx.rs`). Per-crate verification. Commit.
- [ ] 6.5 Convert `business-logic/classic-update-core` (`src/lib.rs`, `src/error.rs`, `src/github.rs`, `src/yaml_update.rs`). Per-crate verification. Commit.

## 7. Convert business-logic/ Wave C — Large Crates

- [ ] 7.1 Convert `business-logic/classic-config-core` (`src/config.rs`, `src/crashgen_rules.rs`, `src/shippable.rs`, `src/yamldata.rs`). Note: `yamldata.rs` has two `#[cfg(test)]` attributes — only the `mod tests { ... }` block moves; any other `#[cfg(test)]`-gated parent-scope items stay in the parent file (per design.md Decision 3). Per-crate verification. Commit.
- [ ] 7.2 Convert `business-logic/classic-scangame-core` (`src/ba2.rs`, `src/config.rs`, `src/config_cache.rs`, `src/crashgen_orchestrator.rs`, `src/enb.rs`, `src/game_report.rs`, `src/ini.rs`, `src/integrity.rs`, `src/logs.rs`, `src/mod_ini.rs`, `src/orchestrator.rs`, `src/setup.rs`, `src/toml.rs`, `src/unpacked.rs`, `src/wrye.rs`, `src/xse.rs`). Per-crate verification. Commit.
- [ ] 7.3 Convert `business-logic/classic-scanlog-core` (`src/crashgen_registry.rs`, `src/fcx_handler.rs`, `src/formid.rs`, `src/formid_analyzer.rs`, `src/gpu_detector.rs`, `src/mod_detector.rs`, `src/orchestrator.rs`, `src/papyrus.rs`, `src/parser.rs`, `src/patterns.rs`, `src/plugin_analyzer.rs`, `src/record_scanner.rs`, `src/report.rs`, `src/settings_validator.rs`, `src/suspect_scanner.rs`, `src/version.rs`). Note: `mod_detector.rs` has two `#[cfg(test)]` attributes — apply the Decision 3 rule. Per-crate verification. Commit.

## 8. Convert cpp-bindings/classic-cpp-bridge

- [ ] 8.1 Convert `cpp-bindings/classic-cpp-bridge` (every `src/*.rs` with a `mod tests` block: `src/config.rs`, `src/database.rs`, `src/files.rs`, `src/game.rs`, `src/markdown.rs`, `src/message.rs`, `src/path.rs`, `src/perf.rs`, `src/registry.rs`, `src/runtime.rs`, `src/scangame.rs`, `src/scanner.rs`, `src/settings.rs`, `src/shared.rs`, `src/types.rs`, `src/update.rs`, `src/version_registry.rs`, `src/web.rs`, `src/xse.rs`). Per-crate verification.
- [ ] 8.2 Run the CXX parity gate: `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`. Confirm zero drift against the committed CXX baseline under `docs/implementation/cxx_api_parity/baseline/`.
- [ ] 8.3 Build the C++ bridge consumers via the repo-approved scripts (`classic-cli/build_cli.ps1` and `classic-gui/build_gui.ps1`) to confirm the bridge still compiles for downstream MSVC consumers. Commit.

## 9. Convert node-bindings/classic-node

- [ ] 9.1 Convert `node-bindings/classic-node` (every `src/*.rs` with a `mod tests` block). Per-crate verification.
- [ ] 9.2 From `node-bindings/classic-node/`, run `bun run parity:gate`. Confirm zero drift against the committed Node baseline under `docs/implementation/node_api_parity/baseline/`. Commit.

## 10. Convert python-bindings/ Crates

- [ ] 10.1 Convert `python-bindings/classic-config-py`. Per-crate verification. Commit.
- [ ] 10.2 Convert `python-bindings/classic-database-py`. Per-crate verification. Commit.
- [ ] 10.3 Convert `python-bindings/classic-file-io-py`. Per-crate verification. Commit.
- [ ] 10.4 Convert `python-bindings/classic-message-py`. Per-crate verification. Commit.
- [ ] 10.5 Convert `python-bindings/classic-path-py`. Per-crate verification. Commit.
- [ ] 10.6 Convert `python-bindings/classic-perf-py`. Per-crate verification. Commit.
- [ ] 10.7 Convert `python-bindings/classic-registry-py`. Per-crate verification. Commit.
- [ ] 10.8 Convert `python-bindings/classic-resource-py`. Per-crate verification. Commit.
- [ ] 10.9 Convert `python-bindings/classic-scangame-py`. Per-crate verification. Commit.
- [ ] 10.10 Convert `python-bindings/classic-scanlog-py` (touches `src/lib.rs`, `src/orchestrator.rs`, `src/suspect_scanner.rs`). Per-crate verification. Commit.
- [ ] 10.11 Convert `python-bindings/classic-settings-py`. Per-crate verification. Commit.
- [ ] 10.12 Convert `python-bindings/classic-update-py`. Per-crate verification. Commit.
- [ ] 10.13 Convert `python-bindings/classic-version-py`. Per-crate verification. Commit.
- [ ] 10.14 Convert `python-bindings/classic-version-registry-py`. Per-crate verification. Commit.
- [ ] 10.15 Convert `python-bindings/classic-web-py`. Per-crate verification. Commit.
- [ ] 10.16 Convert `python-bindings/classic-xse-py`. Per-crate verification. Commit.
- [ ] 10.17 Run the Python parity gate: `python tools/python_api_parity/check_parity_gate.py --repo-root .`. Confirm zero drift against the committed Python baseline under `docs/implementation/python_api_parity/baseline/`.
- [ ] 10.18 Run the binding-local Python smoke tests: `uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q`.

## 11. Convert ui-applications/classic-tui

- [ ] 11.1 Convert `ui-applications/classic-tui` (touches `src/app.rs`, `src/results_markdown.rs`, `src/tabs/main_tab.rs`). Per-crate verification. Commit.

## 12. Final Workspace Sweep and Verification

- [ ] 12.1 Run a workspace-wide grep for `^#\[cfg\(test\)\]\s*\nmod tests \{` across the active layer roots (`foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, `ui-applications/classic-tui/`). Expect zero matches. If any survive, convert them and commit.
- [ ] 12.2 Run `cargo build --workspace` from the repo root. Expect a clean build.
- [ ] 12.3 Run `cargo test --workspace` from the repo root. Expect the same total test count captured in 1.1, and all tests passing.
- [ ] 12.4 Run `cargo clippy --workspace --all-targets --all-features -- -D warnings` from the repo root. Expect zero warnings (treated as errors).
- [ ] 12.5 Run `cargo fmt --all -- --check` from the repo root. Expect no formatting drift.
- [ ] 12.6 Re-run all three parity gates as a final closeout (`python tools/cxx_api_parity/check_parity_gate.py --repo-root .`, `bun run parity:gate` from `node-bindings/classic-node/`, `python tools/python_api_parity/check_parity_gate.py --repo-root .`). Expect zero drift across all three.
- [ ] 12.7 Delete the scratch per-crate test-count file from 1.2.
