# Phase 6: mmap TOCTOU Safety - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `read_file_mmap()` safe against time-of-check-to-time-of-use races by replacing the current direct file mapping with a copy-on-write read-only mapping, then prove the throughput cost is acceptable on Windows with Criterion benchmarks. This phase stays inside the mmap read path and its benchmark evidence; it does not broaden into general file-I/O redesign or unrelated scanlog performance work.

</domain>

<decisions>
## Implementation Decisions

### Canonical mmap contract
- **D-01:** The Phase 6 target is `MmapOptions::map_copy_read_only()`, not `MmapOptions::map_copy()` and not `Mmap::map()`.
- **D-02:** Treat `.planning/ROADMAP.md`, `.planning/STATE.md`, and the repo research notes as canonical for this phase's mmap contract; the older `map_copy()` wording in `.planning/PROJECT.md` and `.planning/REQUIREMENTS.md` should be aligned to the `map_copy_read_only()` decision during planning/execution.

### Benchmark proof location
- **D-03:** Put the Phase 6 throughput proof in `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` rather than creating a new mmap-only harness or reusing the scanlog benchmark harness.
- **D-04:** Follow the established benchmark-proof pattern from Phase 5: raw Criterion baselines stay local-only, while the committed artifact is a markdown proof summary with the commands, compared variants, and results.

### Benchmark coverage
- **D-05:** The representative throughput proof should use near-threshold plus larger synthetic inputs so the mmap branch is definitely exercised and scaling above the 1 MB cutoff is visible.

### Rollout policy
- **D-06:** After the benchmark work lands, `read_file_mmap()` should use the safer mapping on all platforms. Windows benchmarking is the required validation target because that is the risky platform, but the rollout itself is not Windows-only.

### the agent's Discretion
- Exact benchmark sizes, as long as they bracket the 1 MB mmap cutoff and include larger synthetic files.
- Exact Criterion group names, baseline names, and helper structure inside `file_io_benchmarks.rs`.
- Exact doc-alignment edits across planning docs and API docs, as long as they converge on the locked `map_copy_read_only()` contract.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone contract
- `.planning/ROADMAP.md` - Phase 6 goal, success criteria, and the locked `map_copy_read_only()` benchmark requirement.
- `.planning/PROJECT.md` - milestone constraints and the stale `map_copy()` wording that must be reconciled with Phase 6 decisions.
- `.planning/REQUIREMENTS.md` - `SAFE-05` traceability entry and the stale `map_copy()` wording that must be aligned during this phase.
- `.planning/STATE.md` - carry-forward note that Windows `map_copy_read_only()` behavior must be validated empirically.

### Prior benchmark policy
- `.planning/phases/05-pattern-caching-and-performance/05-CONTEXT.md` - prior decision pattern for benchmark proof, existing-harness preference, and local-only raw baselines.
- `.planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` - committed proof-artifact format and the explicit handoff that mmap throughput validation belongs to Phase 6.
- `performance_baselines/README.md` - current repo policy for local-only Criterion baselines and committed proof summaries.

### Safety research
- `.planning/research/SUMMARY.md` - Phase 6 rationale for `map_copy_read_only()` over `map_copy()` and the Windows validation requirement.
- `.planning/research/PITFALLS.md` - the Windows memory-doubling pitfall for `map_copy()` and the recommendation to benchmark `map()`, `map_copy()`, and `map_copy_read_only()`.
- `.planning/codebase/CONCERNS.md` - the original TOCTOU fragility note on `read_file_mmap()`.

### Public API and implementation files
- `docs/api/README.md` - required doc-update rule for public Rust API behavior changes.
- `docs/api/classic-file-io-core.md` - current `read_file()` / `read_file_mmap()` behavior contract and the documented mmap safety caveat.
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` - current `read_file_mmap()` implementation, 1 MB threshold, and existing mmap tests.
- `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` - existing Criterion harness in the same crate where the mmap proof should land.
- `ClassicLib-rs/python-bindings/classic-file-io-py/src/core.rs` - direct Python exposure of `read_file_mmap()` that inherits the core behavior change.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`: `read_file()` already delegates large-file reads to `read_file_mmap()`, so Phase 6 can change one core path instead of chasing multiple call sites.
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs`: existing small-file and large-file `read_file_mmap()` tests provide a starting point for validating unchanged behavior after the mapping swap.
- `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs`: existing Criterion harness already uses shared repo benchmark configuration and has a natural home for file-I/O throughput groups.
- `performance_baselines/README.md`: existing local-baseline workflow can be mirrored for the Phase 6 proof artifact.

### Established Patterns
- Business logic and safety semantics stay in Rust core; bindings inherit the changed behavior instead of reimplementing file-mapping logic.
- Benchmark evidence in this repo uses Criterion with committed markdown proof and local-only raw baseline directories.
- Public contract and planning docs are expected to move with source-visible behavior changes when a phase locks a clearer contract than the current docs state.

### Integration Points
- `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` is the implementation site for the mmap safety change.
- `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` is the benchmark integration point for throughput proof.
- `docs/api/classic-file-io-core.md`, `.planning/PROJECT.md`, and `.planning/REQUIREMENTS.md` are the main docs that need contract alignment once Phase 6 executes.
- `ClassicLib-rs/python-bindings/classic-file-io-py/src/core.rs` is the direct binding surface that should remain a thin wrapper over the changed core behavior.

</code_context>

<specifics>
## Specific Ideas

- Resolve the roadmap-vs-requirements mismatch in favor of `map_copy_read_only()`; do not preserve the older `map_copy()` wording just because it already exists.
- Treat Windows validation as empirical proof work, not as a reason to keep a separate Windows-only implementation by default.
- Keep the benchmark story file-I/O-local rather than folding it into the Phase 5 scanlog hotspot harness.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 06-mmap-toctou-safety*
*Context gathered: 2026-04-06*
