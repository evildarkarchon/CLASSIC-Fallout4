## Context

CLASSIC's Rust workspace has accumulated large mixed source files. Concrete examples in `business-logic/classic-scanlog-core/src/` include `orchestrator.rs` at 2,829 lines, `parser.rs` at 1,740 lines, and `business-logic/classic-config-core/src/config.rs` at 1,481 lines, with substantial fractions of each file devoted to inline `#[cfg(test)] mod tests { ... }` blocks. A repo-wide grep for `#[cfg(test)]` finds 131 occurrences across 129 files spread over every layer root: 16 business-logic crates, both foundation crates, the C++ bridge, the Node binding, all 14 Python binding crates, and the Rust TUI. The current convention is universal: every test block uses `use super::*;` to reach items in the parent module, and almost every file has a single test block (two files — `mod_detector.rs`, `yamldata.rs` — show two `#[cfg(test)]` attributes, of which only one is the test module).

Constraints that shape this design:

- The repo enforces a Rust-first architecture with thin C++/Node/Python wrappers. Internal layout changes that do not touch public Rust APIs must also leave the CXX, Node, and Python binding surfaces untouched, and the parity gates under `docs/implementation/{cxx,node,python}_api_parity/baseline/` must stay green.
- Cargo workflows (`cargo build --workspace`, `cargo test --workspace`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, `cargo fmt --all -- --check`) are run from the repo root and must keep working without any new flags or invocation changes.
- Native C++ targets are MSVC-on-Windows-only. The Rust test relocation must not affect those builds, so any layout choice should not interact with the CXX `build.rs`-driven bridge surface generation in `cpp-bindings/classic-cpp-bridge/`.
- Some crates already use a `mod.rs`-style directory layout (e.g., `business-logic/classic-path-core/src/platform/` with `windows.rs` and `linux.rs` siblings); whatever layout this change picks must work in both flat-file and `platform/`-style submodule trees.
- Stakeholders: every contributor touching Rust code, plus the maintainer of the `rust-crate` scaffolding skill at `.agents/skills/rust-crate/`.

## Goals / Non-Goals

**Goals:**
- Move every existing inline `#[cfg(test)] mod tests { ... }` block in the workspace into a sibling submodule file colocated with the module under test, using one consistent layout pattern across all crates.
- Pick a layout that lets `use super::*;` and other `super::`-prefixed paths inside test code keep working unchanged, so the relocation is a pure file-split rather than a refactor of test imports.
- Preserve `cargo test --workspace` results bit-for-bit on a per-crate basis: same test count, same names, same pass/fail, same module paths visible to `cargo test <filter>`.
- Keep the CXX, Node, and Python parity baselines untouched — this work has zero public-API impact.
- Update the `rust-crate` scaffolding skill so newly created crates default to the sibling layout from day one.
- Allow the conversion to land incrementally, crate by crate, behind small reviewable commits that are individually safe to merge and easy to bisect.

**Non-Goals:**
- Renaming, adding, removing, or rewriting any test cases. The block boundaries move; the contents do not.
- Touching tests that already live outside source files (Cargo integration tests under each crate's `tests/`, criterion benches under `benches/`, shared `tests/common/` modules). Those stay where they are.
- Restructuring crate module trees (e.g., turning `foo.rs` into `foo/mod.rs` directories). The layout chosen below explicitly avoids that churn.
- Changing C++ test layout (`classic-cli`, `classic-gui`) or Python test layout (`python-bindings/.../tests/`). Those are governed by their own conventions and tools.
- Changing CI commands, parity baselines, or any docs under `docs/api/`.

## Decisions

### Decision 1: Sibling-file layout via `#[path = "<name>_tests.rs"] mod tests;`

The chosen layout is: for any source file `src/<name>.rs` that has unit tests, the tests live in a sibling file `src/<name>_tests.rs`, declared from the parent by a single line:

```rust
#[cfg(test)]
#[path = "<name>_tests.rs"]
mod tests;
```

The body of `<name>_tests.rs` is exactly what used to be inside the inline `mod tests { ... }` braces, including its `use super::*;` line and any `#[cfg(test)]`-only helper items.

**Why this over alternatives:**

- *Alternative A — drop `#[path]`, let Rust resolve `mod tests;` by default*: Rust's default rule for a non-`mod.rs` parent file like `src/foo.rs` puts the submodule at `src/foo/tests.rs`, which forces creating a `foo/` directory next to `foo.rs` for every converted module. With ~129 affected files, that is ~129 new directories and a more invasive diff. Rejected.
- *Alternative B — convert each `<name>.rs` to `<name>/mod.rs` first, then add `<name>/tests.rs`*: Same directory-explosion problem as A, plus it also moves the production source file, which complicates `git blame` history for the production code. Rejected.
- *Alternative C — push tests into each crate's `tests/` directory as integration tests*: Changes test semantics. Items currently exercised through `super::*` are crate-private; integration tests can only see `pub` items. This would either silently drop test coverage or force widening visibility. Rejected.
- *Alternative D — keep them inline*: This is the status quo the proposal is replacing. Rejected.

The chosen pattern (sibling file with `#[path]`) keeps `<name>.rs` exactly where it is, adds one neighbor file, leaves `git blame` for production code clean, preserves `super::*` imports, and produces a uniform grep-able layout (`*_tests.rs`).

### Decision 2: Naming rule, including for `lib.rs` / `main.rs` / `mod.rs`

The naming rule is mechanical: the test sibling for `<source-stem>.rs` is always `<source-stem>_tests.rs`. That gives:

- `src/foo.rs` → `src/foo_tests.rs`
- `src/lib.rs` → `src/lib_tests.rs`
- `src/main.rs` → `src/main_tests.rs`
- `src/platform/windows.rs` → `src/platform/windows_tests.rs`
- `src/foo/mod.rs` → `src/foo/mod_tests.rs`

A single uniform suffix is preferred over special-casing `lib.rs` to a bare `tests.rs`, because consistency makes the convention easier to grep, easier to enforce with simple tooling later, and easier to reason about when reviewing code from any crate. The `_tests.rs` suffix has no collision risk in this workspace (no source file currently ends with `_tests`).

### Decision 3: Files with multiple `#[cfg(test)]` attributes are split surgically

Two files (`business-logic/classic-scanlog-core/src/mod_detector.rs`, `business-logic/classic-config-core/src/yamldata.rs`) contain two `#[cfg(test)]` occurrences each. Only the `#[cfg(test)] mod tests { ... }` block moves. Other `#[cfg(test)]`-gated items (e.g., a `#[cfg(test)] fn helper(...)` declared at parent-module scope, or a `#[cfg(test)] use ...;`) stay in the parent file unchanged, because they are part of the parent module's compiled-under-test surface that the now-relocated `tests` submodule can still see via `use super::*;`.

The reverse is also true: if a `#[cfg(test)]` item only makes sense as a test helper inside the moved block, it moves with the block. The mechanical rule is "the block moves; everything outside the block stays."

### Decision 4: Conversion is incremental, one crate per commit

The work is sequenced crate-by-crate rather than as a single sweeping commit. Each per-crate commit:

1. Creates the new `_tests.rs` sibling files for that crate.
2. Replaces each former inline `mod tests { ... }` block in the parent file with the one-line `#[cfg(test)] #[path = "..."] mod tests;` declaration.
3. Runs `cargo test -p <crate>` and confirms the test count and pass/fail outcomes match the pre-conversion run for that crate.
4. Runs `cargo fmt --all -- --check` and `cargo clippy -p <crate> --all-targets --all-features -- -D warnings` for the touched crate.

This ordering means a regression in any single crate can be reverted in isolation, and reviewers see a small focused diff per crate. The order across crates does not matter for correctness, but a sensible approach is to start with smaller leaf crates (e.g., `classic-perf-core`, `classic-registry-core`, `classic-web-core`) to validate the mechanical pattern before tackling the larger ones (`classic-scanlog-core`, `classic-scangame-core`, `classic-config-core`).

After every per-crate commit, a workspace-wide `cargo build --workspace` and `cargo test --workspace` confirms nothing else broke. The CXX/Node/Python parity gates are run once at the end of each layer (foundation, business-logic, bindings, ui-applications) as the cheapest stable checkpoint, since no public surface changes.

### Decision 5: Mechanical conversion, not auto-generated

The relocation is performed by hand (or by a contributor's own one-off script) per file, not by a checked-in long-lived tool. The reason: this is a one-time migration. Investing in tooling that exists to be run once and then deleted has worse cost-to-value than doing the move directly with editor multi-cursor and `Edit`-tool calls and verifying via `cargo test`. The workspace gains no new build-time dependency, no new CI step, and no new code to maintain after this lands.

If a contributor *wants* to script the per-file move locally for their own convenience, that is fine — but the artifact that ships is just the relocated files plus the `rust-crate` skill update, not a tool.

### Decision 6: Update the `rust-crate` skill so future crates start in the new layout

The `.agents/skills/rust-crate/` skill that scaffolds new Rust crates will be edited so its `lib.rs` template emits `#[cfg(test)] #[path = "lib_tests.rs"] mod tests;` and writes a sibling `src/lib_tests.rs` containing a placeholder `use super::*;` and one trivial smoke test (matching whatever the current template produces, but in the new file). This prevents drift back to inline blocks via the most common path for new crates.

## Risks / Trade-offs

- **Risk**: Merge conflicts with in-flight branches that still edit inline `mod tests` blocks.
  → **Mitigation**: Land conversions crate-by-crate in small commits, and announce a short freeze window for inline-test edits in a given crate just before its conversion lands. Conflicts that do occur are mechanical (apply the change to the new `_tests.rs` file instead of the old inline location).

- **Risk**: A `#[cfg(test)] mod tests` block that internally declared further nested submodules (e.g., `mod tests { mod helpers { ... } #[test] fn foo() {...} }`) needs those nested modules to be moved verbatim.
  → **Mitigation**: The Decision 3 rule is "the block moves; everything outside the block stays." Nested submodules inside the block move with it as part of the block body, so behavior is preserved by construction.

- **Risk**: Tests that referenced parent items via `crate::` rather than `super::` continue to work — but tests that referenced *grandparent* items via `super::super::` need to be re-checked, since the test module's depth is unchanged but readers may assume otherwise.
  → **Mitigation**: The test module's path is unchanged (`<crate>::<parent>::tests`), because the sibling file is still declared as `mod tests` of the same parent. `super::*` and `crate::*` keep working without edits. Per-crate `cargo test` is the verification gate; if anything fails to compile after the move, fix it in the same per-crate commit.

- **Risk**: `#[path]`-attribute-based modules can mildly confuse some IDE tooling that only follows default module resolution.
  → **Mitigation**: rust-analyzer (the dominant choice for this workspace) handles `#[path]` correctly. Affected IDEs would still find the file via plain text search using the consistent `_tests.rs` suffix.

- **Risk**: Two separate files per module increase the surface area for "tests for X drifted from X" stale-helper bugs.
  → **Mitigation**: This is the same risk that exists today for any helper used across `tests/` and source. The naming rule (`<stem>_tests.rs`) makes the pairing visible in any file listing, and contributors continue to run `cargo test` locally before pushing.

- **Trade-off**: The `#[path]` attribute is a small amount of "noise" on the parent file compared to a bare `mod tests;`. We accept that cost in exchange for keeping `<name>.rs` as a flat sibling rather than churning every module into its own `<name>/` directory.

- **Trade-off**: `cargo test`'s test-name output is unchanged (`<crate>::<parent>::tests::<test_fn>`), but readers grepping for a failing test by name now have to know to look in `<parent>_tests.rs` rather than `<parent>.rs`. The naming convention is intended to make that one-step lookup obvious.

## Migration Plan

1. **Land the spec and the `rust-crate` skill update first.** This puts the convention in writing and prevents new inline blocks from being introduced while the bulk move is in flight.
2. **Convert one small leaf crate** (recommend `business-logic/classic-perf-core`) end-to-end as a reference commit. This validates the mechanical pattern and gives reviewers a known shape to look for in subsequent commits.
3. **Convert the remaining `foundation/` crates**, then the remaining `business-logic/` crates, then `cpp-bindings/classic-cpp-bridge/`, then `node-bindings/classic-node/`, then the `python-bindings/` crates, then `ui-applications/classic-tui/`. One commit per crate. Each commit runs the per-crate verification listed in Decision 4 and includes the test-count comparison output (or a short note: "before: N tests; after: N tests; all pass") in the commit body.
4. **At each layer boundary**, run the relevant parity gate(s) once to confirm zero drift: CXX gate after `cpp-bindings/`, Node gate after `node-bindings/`, Python gate after `python-bindings/`.
5. **At the end**, run a full `cargo build --workspace`, `cargo test --workspace`, `cargo clippy --workspace --all-targets --all-features -- -D warnings`, and `cargo fmt --all -- --check` from the repo root as a final sanity sweep.

**Rollback strategy:** Per-crate commits are the rollback unit. If a regression is found later (e.g., a contributor reports a test that no longer behaves the same), `git revert` the offending crate's conversion commit; the rest of the workspace is unaffected because each commit is self-contained.
