# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v9.1.0-bugfixes — CLASSIC Codebase Health

**Shipped:** 2026-04-07
**Phases:** 11 (8 planned + 3 gap-closure follow-ups) | **Plans:** 32 | **Tasks:** 61
**Internal label during execution:** v1.0 (renamed at ship time to continue v8.x progression)

### What Was Built

- **Tech debt cleanup (Phases 1-2):** All deprecated APIs migrated and removed (`parse_segments`, `parse_segments_parallel`, `is_outdated`); dead code deleted (`SEGMENT_BOUNDARIES`, `YamlFormatConfig`, `PluginAnalyzer.case_cache`, `PyGpuDetector.inner`); legacy `scan_all_settings_legacy_bucketed` fallback eliminated with assertion test
- **FCX state hardening (Phase 3):** Blocking reset with typed `FcxResetError`; C++ bridge auto-resets before scan sessions; Node bindings expose flat `resetFcxGlobalState()` / `getFcxConfigIssues()` with same-process isolation coverage
- **Bounded caches with canonical stats (Phase 4):** YAML (128) / settings (64) / hash (1024) caches now use `quick_cache::sync::Cache`; one canonical 5-field `CacheStats` (`hits`, `misses`, `hit_rate`, `size`, `capacity`) surfaces consistently across Rust core, Node, Python, and C++ bridge
- **Hot-path performance (Phase 5):** Bounded `LazyLock<Cache>` matcher caches for `detect_mods_single`/`double`/`batch`/`important`; cached Aho-Corasick `LeftmostLongest` important-mod detection; module-level `LazyLock<LogParser>` for the C++ bridge `detect_crash_pattern`; Criterion benchmark proof in `05-BENCHMARK-PROOF.md`
- **mmap TOCTOU safety (Phase 6):** `read_file_mmap` switched to `MmapOptions::map_copy_read_only()` with three-way Windows benchmark proof and a parity test
- **Consistency sweep (Phase 7):** Zero `once_cell::sync::Lazy` in production source; registry/perf/scanlog all on `std::sync::LazyLock` / `OnceLock`
- **Workspace and infrastructure (Phase 8):** `winreg`/`phf` workspace-promoted; Linux Proton docs-path wired with `find_docs_path_linux_with()` validating Proton before fallback; `index.d.ts` snapshot tracked with CI freshness gate via `dts:freshness:check`
- **Verification gap closure (Phases 9, 10, 11):** Re-verified Phase 1 with command-backed evidence; refreshed Phase 5 verification to cover PERF-03 and CONS-04; created the missing authoritative Phase 8 verification artifact

### What Worked

- **Three-source requirement traceability** (VERIFICATION + SUMMARY frontmatter + REQUIREMENTS.md) caught the original 12 verification gaps that would otherwise have shipped silently with claimed-complete summaries.
- **Gap-closure phase pattern (Phases 9/10/11):** Refreshing the parent phase verification artifact in place — instead of inventing a parallel "10-VERIFICATION.md" — kept one authoritative story per phase. This pattern is now documented in 10-01-SUMMARY.md and 11-01-SUMMARY.md.
- **Five-field canonical CacheStats:** Defining the contract once in core (`hits, misses, hit_rate, size, capacity`) and forcing every binding to adapt downward eliminated parity drift and made all four binding surfaces directly comparable.
- **Bounded `LazyLock<quick_cache::Cache>` for input-derived alternation regexes:** Phase 5 chose this over fake static regexes because the input set (mod lists) is content-derived. The contributor doc rule "bounded caches own input-derived alternation, only true constants get standalone `LazyLock`" prevented later cargo-culting.
- **Treating `FcxResetError::Unnecessary` as success across all binding surfaces:** Lets binding code keep the no-op reset path benign without breaking explicit-failure handling. Validated by contention test plus same-process isolation tests.
- **Phase 6 narrow `#[allow(unsafe_code)]` helpers:** When the inline benchmark unsafe blocks tripped the crate clippy gate, Phase 6.3 refactored them into narrow helper functions instead of weakening the lint policy.

### What Was Inefficient

- **First milestone audit failed on 12 verification gaps** that should have been caught during phase verification. Three follow-up phases (9/10/11) were needed to close them — each gap was a documentation/proof issue, not a code defect.
- **SUMMARY frontmatter `requirements-completed` is empty in many plan summaries** (01-02, 02-01, 02-03, 03-03, 04-01/02/04/06, 05-01/04/05/06/07, 08-01, 11-01). The verification reports cite the requirements explicitly, so audit traceability worked, but the SUMMARY frontmatter index is not consistently maintained. Tooling-only consumers that read frontmatter would miss these.
- **Phase 5 important-mod regression took multiple plans to close** (05-02 → 05-05 → 05-06 → 05-07). Initial Aho-Corasick replacement showed a regression on synthetic and real-fixture surfaces; only after splitting the cost into compile-only vs haystack-prep slices in 05-07 did the bounded cached matcher beat the legacy comparator.
- **Documentation drift (`DashMap` references in Python binding stubs and comments)** persisted into Phase 4 even after the runtime moved to `quick_cache`. Caught by the verification report as warning-severity but never blocking.
- **Internal milestone label `v1.0`** conflicted with the project's existing `v1.0 Codebase Cleanup` (2026-02-02). Not noticed until ship time, requiring a rename to `v9.1.0-bugfixes` during `/gsd:complete-milestone`.

### Patterns Established

- **Gap-closure phases refresh the parent verification artifact in place** rather than creating a parallel `NN-VERIFICATION.md`. The phase's own artifacts are SUMMARY + VALIDATION + the diff to the parent verification.
- **Canonical 5-field cache stats contract** (`hits`, `misses`, `hit_rate`, `size`, `capacity`) is the project standard for all bounded caches and their cross-binding adapters.
- **Bounded `LazyLock<quick_cache::Cache<...>>` is the default for input-derived alternation regexes**; standalone `LazyLock<Regex>` is reserved for true constants.
- **`FcxResetError::Unnecessary` is "success-with-no-op"** across all binding surfaces.
- **Verification audit gates require 3-source cross-reference** (VERIFICATION.md status + SUMMARY frontmatter + REQUIREMENTS.md checkbox); missing any source forces "verify manually".
- **Phase verification reports must record fresh command-backed evidence**, not inherit summary prose. This rule was enforced in the Phase 9/10/11 closure work.
- **Benchmark-only `#[allow(unsafe_code)]` helpers must be narrow functions**, not inline match arms, so the crate clippy gate stays green.

### Key Lessons

1. **Verification is not optional and not delegated.** The first audit found 12 gaps where summaries claimed complete but verification was missing or stale. The fail-gate matrix (VERIFICATION ∧ SUMMARY ∧ REQUIREMENTS) caught it; without that matrix the milestone would have shipped broken.
2. **Backfill the SUMMARY frontmatter `requirements-completed` field at plan time** instead of relying on body text. This is the cheapest fix for the audit traceability tooling drift identified in this milestone.
3. **Keep a single authoritative verification artifact per phase.** When 05-VERIFICATION.md and 05-07-VERIFICATION.md disagreed on the important-mod benchmark story, the milestone audit flagged it as `PARTIAL RISK`. Phase 10 had to refresh the parent in place to fix it.
4. **Validate version numbers against the existing MILESTONES.md before kicking off planning.** Internal label `v1.0` should never have been chosen for a project that already had a v1.0 entry — caught at ship time, but should be a planning-time check.
5. **Performance work needs slice-level benchmarks**, not just full-call benchmarks. Phase 5.7 only succeeded once compile-only vs haystack-prep variants were added to the harness; the original full-call benchmark hid the cost center.
6. **When a phase is independent housekeeping** (Phase 8 workspace deps), it still needs an authoritative verification artifact. Skipping it because "the work is obviously done" is exactly what produced the original Phase 8 audit hole.

### Cost Observations

- Model mix: not tracked for this milestone (no per-session token telemetry)
- Sessions: ~4 days of execution (2026-04-04 → 2026-04-07)
- Notable: The three gap-closure phases (9/10/11) were each ~5-12 minutes of execution work because the underlying code already worked — the gap was documentation. Cheap to close but could have been avoided with stricter verification rules during the original phase execution.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 Codebase Cleanup (2026-02-02) | unknown | 5 | Initial cleanup of Python-Rust hybrid; eliminated redundancies |
| v8.2.0-part2 Rust Migration (2026-02-04) | unknown | 6 | Python → Rust migration with golden file parity |
| v8.3.0 Performance & Polish (2026-02-05) | unknown | 7 | Criterion benchmark infrastructure + GIL release audit |
| v9.1.0-bugfixes CLASSIC Codebase Health (2026-04-07) | ~4 days | 11 (8 + 3 gap closure) | Three-source verification audit pattern; gap-closure phases refresh parent verification in place |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 Codebase Cleanup | 71% baseline | — | Vulture CI |
| v8.2.0-part2 Rust Migration | 3,849 tests passing | — | Golden file parity infrastructure |
| v8.3.0 Performance & Polish | 77+ Criterion benchmarks | — | Flamegraph, py-spy, dhat, DashMap instrumentation |
| v9.1.0-bugfixes CLASSIC Codebase Health | added Phase 5/6 benchmark groups + Phase 6 mmap parity test + tests/planning artifact regression | — | `dts:freshness:check`, three-source audit matrix |

### Top Lessons (Verified Across Milestones)

1. **Phase verification must record fresh command-backed evidence**, not inherit summary prose. Verified across v8.3.0 (where benchmark proof discipline was new) and v9.1.0-bugfixes (where 12 verification gaps were the entire audit blocker).
2. **Bounded caches with explicit eviction policy are non-negotiable for long-running processes.** v9.1.0-bugfixes Phase 4 was the first milestone to enforce this universally; future caches inherit the canonical 5-field `CacheStats` contract.
3. **Single authoritative verification artifact per phase.** When parallel verification files disagree, the milestone audit flags it. Gap-closure phases should refresh the parent in place, not create siblings.
4. **Validate version numbers against MILESTONES.md before planning kickoff.** v9.1.0-bugfixes was originally labeled `v1.0` and only renamed at ship time after the duplicate-version conflict surfaced.
