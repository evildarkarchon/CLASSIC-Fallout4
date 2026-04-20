## Why

Rust source files in CLASSIC carry their unit tests inline via `#[cfg(test)] mod tests { ... }`, and many have grown past the point where that layout is comfortable to maintain — for example `business-logic/classic-scanlog-core/src/orchestrator.rs` is 2,829 lines, `parser.rs` is 1,740 lines, and `business-logic/classic-config-core/src/config.rs` is 1,481 lines, with the test block making up a large fraction of each. Long mixed files make it harder to scan production logic without scrolling through fixtures and assertions, and they raise the risk that a reader (or another contributor) mistakes a test helper for real code. Splitting tests into sibling submodule files keeps each `cargo test` invocation identical while shrinking the production-facing surface of every module to just production code.

## What Changes

- Adopt a repo-wide convention: every existing in-source `#[cfg(test)] mod tests { ... }` block in any Rust crate under `foundation/`, `business-logic/`, `cpp-bindings/classic-cpp-bridge/`, `node-bindings/classic-node/`, `python-bindings/`, and `ui-applications/classic-tui/` moves to a sibling file colocated with the source module.
- Adopt a single sibling layout pattern across the workspace so contributors do not have to guess which form a given crate uses. Default pattern (finalized in `design.md`): for `src/<name>.rs`, the tests live in `src/<name>_tests.rs`, brought in by a single line `#[cfg(test)] mod tests;` (with `#[path = "<name>_tests.rs"]` where Rust's default module resolution would otherwise require renaming `<name>.rs` to `<name>/mod.rs`).
- Update contributor guidance so new tests land in the sibling file from the start. New crates created via the existing `rust-crate` skill must scaffold the sibling test file alongside the module.
- Verify behavior is unchanged: `cargo test --workspace` and the existing parity gates (CXX, Node, Python) must produce the same results before and after the move on a per-crate basis.
- **Non-goals**: this change does not rename, add, remove, or rewrite any test cases; does not move integration tests already living under each crate's `tests/` directory; does not touch C++ (`classic-cli`, `classic-gui`) or Python test layouts; does not change CI commands.

## Capabilities

### New Capabilities
- `rust-test-module-layout`: defines the workspace-wide rule that Rust unit tests must live in sibling submodule files (`<name>_tests.rs`) rather than inline `#[cfg(test)] mod tests` blocks, and the verification expectations that accompany the move.

### Modified Capabilities
<!-- None. Existing capabilities define behavior visible to consumers; relocating internal test files does not change any spec-level behavior. -->

## Impact

- **Affected code**: every Rust source file in the workspace that currently contains an inline `#[cfg(test)] mod tests` block — at least 100 files spread across all 16 business-logic crates, both foundation crates, the C++ bridge, the Node binding, all 14 Python binding crates, and the Rust TUI. Each affected file loses its test block and gains a single `#[cfg(test)] mod tests;` declaration; a new sibling `<name>_tests.rs` file appears alongside it.
- **Affected APIs**: none. No public Rust, CXX bridge, Node, or Python API surfaces change. `docs/api/` pages are not touched.
- **Affected tooling**: the `rust-crate` skill's scaffolding template should be updated so newly generated crates produce a sibling test file by default. Parity gate baselines (`docs/implementation/{cxx,node,python}_api_parity/baseline/`) should remain byte-stable since the public surface does not change; this becomes a verification checkpoint per crate.
- **Risk**: low per-file (move is mechanical) but broad (touches the whole workspace). Largest concrete risks are (a) test helpers that referenced `super::` items now needing `use super::super::*;` style adjustments depending on the chosen layout — `design.md` selects a layout that keeps `super::*` working, and (b) merge conflicts with in-flight branches that still edit the inline blocks. Mitigation: stage the conversion crate-by-crate behind small reviewable commits so any single regression is easy to bisect, and announce a short freeze window for inline-test edits in each crate just before its conversion lands.
- **Dependencies/CI**: no new dependencies. CI commands (`cargo test --workspace`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo fmt --all -- --check`, the three parity gates) are unchanged; they simply continue to pass after each per-crate conversion.
