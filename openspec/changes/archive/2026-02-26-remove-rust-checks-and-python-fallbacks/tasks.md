## 1. Inventory and Runtime Contract

- [x] 1.1 Audit Python code for Rust-optional branches (`detect_component`, `RUST_*_AVAILABLE`, optional imports, fallback selectors) and record affected files.
- [x] 1.2 Define the mandatory-binding contract per entry point (CLI, GUI, TUI, library entry modules) including required binding modules.
- [x] 1.3 Add/centralize binding-failure error types/messages for missing import vs initialization failure with actionable remediation text.

## 2. Remove Fallback Execution Paths

- [x] 2.1 Refactor `ClassicLib/integration/` factories/adapters to resolve Rust implementations only and remove Python fallback selection branches.
- [x] 2.2 Update runtime initialization call sites to fail fast when required bindings are unavailable, instead of continuing with fallback paths.
- [x] 2.3 Remove stale fallback helper functions, flags, and dead code paths left behind after integration refactors.

## 3. Update Tests to Rust-Only Expectations

- [x] 3.1 Remove or rewrite tests that validate successful Python fallback execution.
- [x] 3.2 Update fixtures and test setup to assume Rust bindings are prebuilt/preinstalled and remove optional-Rust branching.
- [x] 3.3 Add or update tests to assert consistent diagnostics for binding import and binding initialization failures.

## 4. Align Tooling, Docs, and CI

- [x] 4.1 Update contributor docs and runbooks to state Rust bindings are mandatory for Python execution.
- [x] 4.2 Ensure Python CI jobs build/install required Rust bindings before running pytest.
- [x] 4.3 Update local helper scripts (where applicable) so Python test/run flows enforce binding prerequisites.

## 5. Verification

- [x] 5.1 Run Python lint/format checks and fix any issues introduced by fallback removal.
- [x] 5.2 Run targeted tests for integration/runtime modules touched by the refactor and ensure Rust-only expectations pass.
- [x] 5.3 Run full relevant Python test suite in a Rust-enabled environment and confirm no fallback behavior remains.
