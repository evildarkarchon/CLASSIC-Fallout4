# Phase 7: Consistency Sweep - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the remaining `once_cell::sync::Lazy` statics with standard-library lazy primitives across the workspace, remove `once_cell` dependency declarations where the migration makes them unnecessary, and align affected contributor API docs so they no longer describe stale `once_cell` usage. This phase is a consistency and cleanup sweep, not a broader redesign of the touched crates.

</domain>

<decisions>
## Implementation Decisions

### Sweep Breadth
- **D-01:** Phase 7 should cover production source, Cargo manifests, and affected `docs/api` pages together. Do not leave stale `once_cell` references behind in touched docs or dependency declarations.
- **D-02:** Remove stale `once_cell` dependency declarations from crates that no longer use it, including already-converted crates such as `classic-yaml-core`, `classic-settings-core`, and `classic-scangame-core`, plus workspace/root declarations if the final audit shows no remaining `once_cell` APIs.

### once_cell Exit Strategy
- **D-03:** Treat full `once_cell` removal as the desired end state for Phase 7, not merely `Lazy` replacement.
- **D-04:** Migrate the remaining `OnceCell` usage in `ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs` to `std::sync::OnceLock` if the semantics stay one-for-one, so the dependency can leave the workspace entirely after the sweep.
- **D-05:** If execution discovers any additional non-`Lazy` `once_cell` APIs beyond the current audit, review them before removal rather than keeping `once_cell` by default.

### Verification Bar
- **D-06:** Verification should include targeted tests for touched crates with global/static behavior, plus a workspace-level build to catch manifest and integration breakage.
- **D-07:** Binding parity gates are not required by default for this phase unless execution unexpectedly changes a binding-visible contract.

### Churn Style
- **D-08:** Reuse the established Phase 4/5 `LazyLock` style instead of redesigning modules during the sweep.
- **D-09:** Small cleanup is allowed only when it stays adjacent to the touched files or modules and directly improves the migration result; no broader crate-wide refactors.

### the agent's Discretion
- Exact ordering and grouping of touched files and crates.
- Exact import style and constructor expressions for `LazyLock` and `OnceLock`, as long as semantics stay unchanged.
- Exact targeted test list and command sequencing, as long as it satisfies the locked verification bar above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Contract
- `.planning/ROADMAP.md` - Phase 7 goal, dependency ordering, and success criteria.
- `.planning/PROJECT.md` - milestone-wide health-only scope and consistency constraints.
- `.planning/REQUIREMENTS.md` - `CONS-01` plus the milestone out-of-scope guardrails.
- `.planning/STATE.md` - carried-forward decisions showing that Phase 4 and Phase 5 already standardized new work on `LazyLock`, and that Phase 7 follows those phases.
- `.planning/phases/04-bounded-cache-replacement/04-CONTEXT.md` - locked repo pattern for new global `LazyLock` statics and same-change contract cleanup.
- `.planning/phases/05-pattern-caching-and-performance/05-CONTEXT.md` - explicit deferral of the repo-wide `once_cell::sync::Lazy` sweep to Phase 7 plus recent `LazyLock` usage inside `classic-scanlog-core`.

### Contributor Docs To Align
- `docs/api/README.md` - rule that source-visible behavior and contributor docs must stay aligned in the same change.
- `docs/api/classic-scanlog-core.md` - contributor-facing scanlog crate contract and recent `LazyLock` guidance inside the crate.
- `docs/api/classic-registry-core.md` - currently documents registry storage as `once_cell::sync::Lazy`; must be updated if migrated.
- `docs/api/classic-perf-core.md` - currently documents metrics storage as `once_cell::sync::Lazy`; must be updated if migrated.
- `docs/api/classic-settings-core.md` - still references `dashmap` and `once_cell` in dependency notes even though source now uses `LazyLock`.

### Active once_cell Usage In Scope
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/fcx_handler.rs` - `GLOBAL_FCX_HANDLER` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` - `COMMON_PATTERNS` and `CRASHGEN_HEADER_PATTERN` still use `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` - `VERSION_PATTERN` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs` - `PLUGIN_PATTERN` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs` - `STRING_POOL` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/orchestrator.rs` - local static `MODULE_PATTERN` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs` - `FORMID_PATTERN` still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/formid.rs` - `FORMID_EXTRACTION_PATTERN` and `FORMID_PARSE_PATTERN` still use `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs` - remaining `once_cell::sync::OnceCell` site that determines whether `once_cell` can leave the workspace entirely.
- `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs` - process-global registry static still uses `once_cell::sync::Lazy`.
- `ClassicLib-rs/business-logic/classic-perf-core/src/metrics.rs` - process-global metrics static still uses `once_cell::sync::Lazy`.

### Manifest Cleanup Targets
- `ClassicLib-rs/Cargo.toml` - workspace-level `once_cell` dependency that should be removed if the full migration succeeds.
- `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml` - current scanlog-core `once_cell` dependency.
- `ClassicLib-rs/business-logic/classic-registry-core/Cargo.toml` - direct version-pinned `once_cell` dependency in an affected crate.
- `ClassicLib-rs/business-logic/classic-perf-core/Cargo.toml` - direct version-pinned `once_cell` dependency in an affected crate.
- `ClassicLib-rs/business-logic/classic-yaml-core/Cargo.toml` - stale `once_cell` declaration already eligible for cleanup.
- `ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml` - stale `once_cell` declaration already eligible for cleanup.
- `ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml` - stale `once_cell` declaration already eligible for cleanup.

### Existing LazyLock Patterns To Reuse
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` - current bounded cache initialized with `std::sync::LazyLock`.
- `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs` - current bounded cache initialized with `std::sync::LazyLock`.
- `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs` - current bounded hash cache initialized with `std::sync::LazyLock`.
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` - repo-standard global runtime `LazyLock` pattern.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs` - recent Phase 5 `LazyLock` usage inside the same crate family.
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` - recent module-level `LazyLock` parser example in a nearby crate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs`: concrete `LazyLock` cache pattern already used in a business-logic crate.
- `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs`: another current `LazyLock` example with adjacent stats counters.
- `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs`: simple `LazyLock` static for a global cache in a core crate.
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`: repo-standard global runtime `LazyLock` pattern.
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs`: same-crate example showing Phase 5 already introduced `LazyLock` in scanlog-core.

### Established Patterns
- New shared initialization in Rust core crates now prefers standard-library primitives (`LazyLock`, and `OnceLock` where lazy deref is not the right fit).
- Earlier phases kept contract docs and manifests aligned with source changes instead of leaving planning or contributor-doc drift behind.
- Workspace dependency cleanup requires auditing both crate-level `Cargo.toml` files and the root workspace manifest.
- Global-state crates rely on focused tests around observable behavior rather than deep implementation assertions.

### Integration Points
- Primary source sweep lands in `classic-scanlog-core`, `classic-registry-core`, and `classic-perf-core`.
- Full dependency removal also touches the root `ClassicLib-rs/Cargo.toml` plus stale crate manifests already no longer using `once_cell`.
- Documentation alignment lands in `docs/api/classic-scanlog-core.md`, `docs/api/classic-registry-core.md`, `docs/api/classic-perf-core.md`, and `docs/api/classic-settings-core.md`.

</code_context>

<specifics>
## Specific Ideas

- Finish the sweep end-to-end rather than leaving stale manifests or contributor docs for later.
- Treat `record_scanner.rs` as part of the same dependency-exit story, not as a separate future cleanup.
- Reuse the already-established Phase 4/5 `LazyLock` style and keep any extra cleanup tightly adjacent to the migrated files.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 07-consistency-sweep*
*Context gathered: 2026-04-06*
