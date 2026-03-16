## Context

The CLASSIC project has 19 PyO3 binding crates (`classic-*-py`) plus a shared `classic-shared-py` foundation crate. These originated as Rust optimizations for a pure-Python application. The project has since adopted a Rust-first architecture where all business logic lives in `-core` crates and bindings are thin wrappers.

An initial code exploration found the bindings are largely compliant -- most are genuine thin wrappers that delegate to core. However, several specific issues were identified:

1. **Dead code**: `PyParallelReportProcessor::process_batch()` is a stub returning input unchanged
2. **Deprecated shims**: `parse_segments` (marked `#[allow(deprecated)]`), `batch_lookup` wrapper, `crashgen_ignore` returning empty Vec, unused parameters in `parse_complete`
3. **Binding-layer legacy residue**: obsolete `classic-pybridge-py`, `fcx_handler.rs` Python-callback orchestration with global caching, adaptive concurrency strategy in `process_logs_batch()`
4. **No formal audit criteria**: The project lacks a documented definition of what constitutes a "thin wrapper" vs. a violation

## Goals / Non-Goals

**Goals:**
- Establish a formal, documented set of thin-binding criteria that can be applied to all current and future binding crates (Python, Node, C++)
- Remove all dead code and deprecated backward-compatibility shims from the Python binding layer
- Relocate any business logic or shared state management found in bindings into appropriate `-core` crates
- Update parity artifacts, type stubs, and tests to reflect API changes
- Leave the binding layer in a state where every function is clearly a type-conversion-and-delegation wrapper

**Non-Goals:**
- Auditing Node bindings (`classic-node`) or C++ bridge (`classic-cpp-bridge`) -- those are separate efforts
- Refactoring the internal architecture of any `-core` crate
- Adding new Python API surface area
- Changing the PyO3 version or maturin build configuration
- Modifying the shared Tokio runtime or async patterns (these are already correct)

## Decisions

### 1. Audit-then-fix approach (not rewrite)

**Decision**: Audit each crate against formal criteria, then make targeted fixes for violations. Do not rewrite bindings from scratch.

**Rationale**: The exploration found the architecture is already largely clean. A rewrite would be high-risk and low-reward. Targeted fixes address the ~5-6 specific issues found while preserving the working codebase.

**Alternatives considered**: Full rewrite of all 19 binding crates. Rejected because the vast majority of code is already compliant and a rewrite risks introducing regressions in a working system.

### 2. Remove deprecated APIs outright rather than adding deprecation warnings

**Decision**: Remove `parse_segments`, `batch_lookup`, `crashgen_ignore`, and unused parameters from `parse_complete` without a deprecation period.

**Rationale**: These are internal bindings consumed by CLASSIC's own code (not a public library). There are no external consumers, and the project is actively migrating to Rust-first frontends. Adding deprecation warnings would create maintenance burden with no practical benefit.

**Alternatives considered**: Adding `#[deprecated]` annotations and keeping shims for one release cycle. Rejected because there are no external consumers of these Python packages.

### 3. Move concurrency strategy to core

**Decision**: Relocate the adaptive concurrency selection logic from `classic-scanlog-py/src/orchestrator.rs` (lines 966-977) into `classic-scanlog-core`.

**Rationale**: Concurrency strategy (how many parallel workers to use for log processing) is a behavioral decision that should be consistent across all frontends. Currently only the Python binding makes this decision; C++ and Node consumers would need to reimplement it.

**Alternatives considered**: Leave in binding layer as "optimization hint". Rejected because the AGENTS.md rule states "Keep all business logic in Rust" and concurrency strategy affects processing behavior.

### 4. Rewire fcx_handler to use existing Rust core functions

**Decision**: Replace the Python callbacks in `fcx_handler.rs` `check_fcx_mode()` with calls to the existing Rust equivalents: `classic-scangame-core::setup::run_combined_checks()` for main files and `classic-scangame-core::orchestrator::detect_config_issues()` for game file scanning.

**Rationale**: The `check_fcx_mode()` method currently imports `ClassicLib.SetupCoordinator` and `ClassicLib.ScanGame` at runtime -- legacy Python modules that `ClassicLib-rs` was built to replace. The Rust core already has native implementations: `run_combined_checks()` in `classic-scangame-core/src/setup.rs` and `detect_config_issues()` in `classic-scangame-core/src/orchestrator.rs`. The Python callback is a leftover from when the Rust bindings were accelerators for the Python app, not a bridge waiting for a future port.

**Alternatives considered**: Document as tech debt and defer. Rejected because the Rust equivalents already exist, the Python callback is a clear thin-binding violation (calling back into the legacy codebase it replaces), and deferring perpetuates an unnecessary Python runtime dependency in what should be a pure Rust-to-Python direction.

### 5. Remove obsolete classic-pybridge-py instead of relocating it

**Decision**: Remove `classic-pybridge-py` entirely rather than relocating its metrics/runtime helpers into another core crate.

**Rationale**: `classic-pybridge-py` existed to support a Python application that no longer ships or receives active maintenance. No active CLASSIC product depends on it, but CI, parity tooling, and docs still carry it as if it were maintained. Deleting the crate is lower-risk and better aligned with the current Rust-first architecture than moving dead compatibility helpers into another crate.

**Alternatives considered**: Move `BridgeMetrics` / `RuntimeInfo` into `classic-perf-core`. Rejected because that preserves an API surface for an obsolete integration and adds maintenance burden to a crate that current products do not need.

## Risks / Trade-offs

- **[Breaking Python API]** Removing deprecated shims will break any remaining code that uses the old APIs. **Mitigation**: Search the codebase for usages before removal; update any call sites found.
- **[fcx_handler rewire complexity]** The Rust core functions (`run_combined_checks`, `detect_config_issues`) may have different signatures or return types than what the Python callbacks currently produce. **Mitigation**: Map the core return types (`SetupCheckResults`, `Vec<ConfigIssue>`) to the existing `FcxModeHandler` state fields; the handler is already a core type so the conversion should be straightforward. Add `classic-scangame-core` as a dependency of `classic-scanlog-py`.
- **[Parity drift]** Removing Python APIs without corresponding Node/C++ changes could cause parity report confusion. **Mitigation**: Update parity artifacts and mark removed APIs as intentionally removed (not missing).
- **[Parity / CI churn]** Removing `classic-pybridge-py` touches parity baselines, smoke tests, CI build lists, and docs. **Mitigation**: Remove all tracked references in the same change and regenerate the checked-in artifacts immediately after code changes.
