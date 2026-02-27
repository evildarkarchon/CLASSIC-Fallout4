## Context

Rust-backed modules are already the primary execution path for scanning, YAML/config access, and related Python integration points, but the codebase still carries conditional checks that treat Rust as optional. This creates split behavior (Rust vs fallback), increases maintenance overhead, and preserves test coverage for an execution mode that is no longer supported by product direction.

This change is cross-cutting because fallback branching appears in runtime detection, integration factories, feature flags, error handling, and tests. The design must standardize a single contract: Python code requires Rust bindings to be present and functional.

Key constraints:
- Preserve current user-facing behavior when Rust bindings are available.
- Fail fast and clearly when bindings are missing or import initialization fails.
- Keep changes aligned with existing architecture (mandatory `classic_registry`, shared runtime rules, and existing module boundaries).

## Goals / Non-Goals

**Goals:**
- Remove optional Rust detection and fallback branching from Python runtime paths.
- Define a consistent "Rust required" initialization and error model across Python entry points.
- Update tests so they validate the supported Rust-only contract and remove fallback-mode expectations.
- Ensure CI and local development assumptions match the Rust-mandatory runtime model.

**Non-Goals:**
- Re-architect Rust crates or binding APIs beyond what is needed to remove fallback conditionals.
- Add new Python fallback implementations.
- Change crash analysis logic semantics unrelated to Rust-availability branching.

## Decisions

1. **Adopt hard-required Rust imports at integration boundaries**
   - Decision: replace availability probes and boolean feature switches with direct imports/initialization and explicit startup errors on failure.
   - Why: removes dual-path execution and makes unsupported environments fail immediately.
   - Alternative considered: keep `detect_component()` but force-true in configuration. Rejected because dead fallback code paths would still exist and continue to complicate testing and maintenance.

2. **Use a single error contract for missing/broken bindings**
   - Decision: normalize failures into a small set of clear runtime errors (for example, import failure vs initialization failure) with actionable messages.
   - Why: avoids inconsistent exception types/messages from ad hoc fallback removal and keeps CLI/GUI behavior predictable.
   - Alternative considered: allow raw import exceptions to bubble everywhere. Rejected because user-facing diagnostics become inconsistent across entry points.

3. **Remove fallback tests and replace with Rust-contract tests**
   - Decision: delete or rewrite tests that assert Python fallback behavior; add assertions for mandatory Rust behavior and clear failures when bindings are unavailable.
   - Why: tests should reflect supported behavior only and prevent accidental reintroduction of fallback logic.
   - Alternative considered: keep fallback tests as "legacy" coverage. Rejected because it institutionalizes unsupported behavior.

4. **Update developer/CI workflow assumptions to prebuild/install bindings**
   - Decision: ensure docs/scripts/test setup treat Rust binding build/installation as prerequisite for Python execution.
   - Why: runtime contract and development workflow must match.
   - Alternative considered: leave workflow docs unchanged. Rejected because it causes recurring setup confusion and flaky local test runs.

## Risks / Trade-offs

- [Risk] Hidden fallback branches remain in less-traveled code paths -> Mitigation: targeted grep-based audit for fallback markers (`detect_component`, `RUST_*_AVAILABLE`, "fallback", optional import guards) and test updates that fail if fallback path resurfaces.
- [Risk] Breaking local developer flows that ran Python without rebuilt bindings -> Mitigation: update run/test instructions and emit clear startup guidance when binding imports fail.
- [Risk] Inconsistent error messaging across CLI/GUI/TUI after fallback removal -> Mitigation: centralize binding-failure exception mapping in shared integration helpers and add coverage for each entry point.
- [Risk] Large refactor scope across runtime and tests -> Mitigation: sequence work by module (integration layer first, call sites second, tests last) and keep behavior-preserving changes isolated per commit.

## Migration Plan

1. Inventory and remove Python fallback branches in integration and runtime entry modules.
2. Standardize binding import/initialization errors and wire them through Python entry points.
3. Update tests to Rust-only expectations; remove fallback fixtures and assertions.
4. Update docs/scripts used by contributors and CI to require binding build/install before Python runs.
5. Validate with lint and targeted test execution, then full Python suite under Rust-enabled environment.

Rollback strategy:
- Revert the change set if a critical regression is found; no data migration is involved.
- If partial rollback is needed, temporarily restore prior branch points in affected modules while preserving new error diagnostics where safe.

## Open Questions

- Should all binding import failures terminate immediately at process start, or are there approved deferred-init entry points that may surface errors later?
- Do we want one shared exception type for all Rust binding failures, or a small typed hierarchy for diagnostics and telemetry?
