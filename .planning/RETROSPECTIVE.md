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

## Milestone: v9.1.0-bindings — Full Bindings Parity

**Shipped:** 2026-04-10
**Phases:** 7 | **Plans:** 32 | **Tasks:** 90

### What Was Built

- **C++ bridge parity gate (Phase 1):** First-class source-only gate that parses `#[cxx::bridge]` source files, produces a baseline JSON contract (316 entries across 19 modules), and fails on drift — no Rust build required
- **CXX bridge surface expansion (Phase 2):** Widened from 202 to 316 entries, closing all narrowing gaps and adding first-time C++ surfaces for `classic-constants-core`, `classic-web-core`, and FCX issue inspection
- **Python tier collapse (Phase 3):** Promoted all deferred entries from 59 to 1098 tier1Mappings across 19 binding crate pairs; `classic_shared` wired as gate-enrolled build target; `deferred_total == 0`
- **Node tier collapse (Phase 4):** Promoted all 109 deferred entries; added `extractPeVersion`/`isValidPePath` for PE-version extraction parity; `deferred_total == 0`
- **CI enforcement (Phase 5):** All three parity gates wired into CI; triple-gate canary assertion proves new public Rust APIs fail CI until all three bindings cover them; CI-04 branch protection user-deferred
- **Documentation reset (Phase 6):** Deleted all 8 Tier-2 governance files; rewrote `binding-parity-overview.md`; created `binding-parity-policy.md` and `error-contract.md`; 18K-line promotion audit trail preserved
- **Milestone cleanup (Phase 7):** Closed all 6 audit gaps — traceability corrections, CXX baseline path fix, vestigial tier2 label removal, stale comment cleanup

### What Worked

- **Wave-based promotion pattern** in Phases 3/4: Breaking 1000+ entries into domain-grouped waves (scanlog, config, version_registry, file_io, aux) with independent verification at each wave boundary caught errors early and kept each plan manageable.
- **`@rust`-suffix proxy row pattern:** Rust-only symbols (no PyO3/NAPI wrapper) paired with the nearest wrapped class via an `@rust`-suffixed contract row. Eliminated the gap without requiring speculative new binding wrappers. Pattern generalized from scanlog to config to all domains.
- **M7 atomic cascade pattern:** Structural Tier-2 cleanup (gap branch deletion + tierDefinitions.tier2 removal + backlog emptying + floor assertion update + baseline refresh) committed atomically to prevent bisect-breaking intermediate states. Established in Phase 3 Plan 09b, reapplied in Phase 4 Plan 06.
- **Cross-AI review for Phase 2:** Codex review caught real issues (Path-taking vs &str API signatures, missing CXX build.rs FILES list entries) that the internal plan checker missed. Justified the review-before-execute policy for plans that encode domain-specific logic.
- **Source-only CXX gate (no build required):** Phase 1 design decision to parse source rather than inspecting compiled output made the gate fast (~2s), CI-friendly, and independent of the Rust build toolchain.

### What Was Inefficient

- **Plan scaffold divergence from reality** was the single largest time cost. Nearly every plan in Phases 3 and 4 needed inventory-first corrections (wrong deferred counts, missing owner modules, stale API signatures) because the plan was written against plan-time estimates rather than live source. The correction overhead was manageable per plan but compounded across 16 plans.
- **Phase 3 Plan 09a scope explosion:** The A10 sizing report revealed 593 rows across 14 new owners instead of the estimated ~50-150. A single plan had to absorb all of them because they shared a common promotion pattern and splitting would have created unnecessary plan-per-owner overhead.
- **Phase 5 CI-04 branch protection deferred:** Branch protection requires GitHub repository admin access that cannot be automated through code changes. This was correctly identified during planning but still consumed discussion time during the audit.
- **MILESTONES.md accomplishments too granular:** The CLI `milestone complete` command dumped all 18 plan-level one-liners instead of condensing to 4-6 milestone-level achievements. Required manual cleanup during completion.

### Patterns Established

- **`@rust`-suffix proxy rows** are the standard for enrolling Rust-only symbols in Python and Node parity contracts without inventing speculative binding wrappers.
- **M7 atomic cascade** for structural parity infrastructure deletion: all related edits in one commit to prevent bisect breakage.
- **Inventory-first plan correction:** Before executing any promotion wave, read the live deferred backlog and surface to verify row counts match the plan scaffold. Correct before writing code.
- **CXX gate is source-only:** The C++ bridge parity gate parses Rust source, not compiled output. Keep it that way for speed and CI independence.
- **Triple-gate canary assertion:** `tools/test_triple_gate_failure.py` injects a temporary public API and proves all three gates fail. Run as part of CI enforcement verification.
- **Promotion audit trail before governance deletion:** Snapshot governance file contents to `.planning/milestones/` BEFORE deleting them. The audit trail is the only record of what was promoted from where.

### Key Lessons

1. **Plan scaffolds based on estimates diverge from reality.** Every plan that estimated deferred row counts needed correction against the live baseline. Future milestone plans should require a live-count verification step before execution, not just during.
2. **Wave-based domain grouping is the right granularity for binding promotion.** Per-plan waves of 30-80 rows with independent verification caught errors early without excessive plan overhead. The 593-row exception (Plan 09a) worked because all rows shared the same promotion pattern.
3. **Cross-AI review pays for itself on CXX bridge plans** because CXX FFI constraints (shared enum rules, Files list requirements, Path-taking signatures) are easy to get wrong and hard to debug at compile time. The time invested in review was less than the time saved avoiding compile failures.
4. **Governance file deletion is irreversible — always audit-trail first.** The 18K-line promotion audit trail preserved exactly which entries came from which governance file. Without it, the deletion history would only exist in git history, which is harder to query.
5. **Branch protection is outside code scope.** CI-04 should have been scoped as "document the required branch protection configuration" rather than "configure branch protection" to avoid the deferred-requirement pattern.

### Cost Observations

- Model mix: not tracked for this milestone (no per-session token telemetry)
- Sessions: ~4 days of execution (2026-04-07 to 2026-04-10)
- Notable: Phase 3 (Python tier collapse, 10 plans) was the largest single phase and consumed roughly half the milestone's execution time. The wave pattern kept individual plans in the 8-15 minute range despite the total scope.

---

## Milestone: v9.1.0-consolidation — Crate Consolidation

**Shipped:** 2026-04-12
**Phases:** 5 | **Plans:** 16 | **Tasks:** 38

### What Was Built

- **YAML/settings consolidation (Phase 1):** `classic-yaml-core` was absorbed into `classic-settings-core`, all bindings/consumers were migrated, and the parity generators were upgraded to scan Rust sub-modules so the merged surface remained visible to the gates.
- **Crashgen/config consolidation (Phase 2):** `classic-crashgen-settings-core` was absorbed into `classic-config-core`, all downstream Rust/Python/Node consumers moved to the new owner, and docs/parity ownership were reparented without drift.
- **Constants redistribution (Phase 3):** `classic-constants-core` was split into semantic owners across version-registry, settings, and shared, with matching Rust, Python, Node, CXX, GUI, docs, and parity updates.
- **Closure proof (Phase 4):** Workspace tests, CLI/GUI wrapper validation, and plain CXX/Python/Node parity reruns were all recorded in a single Phase 4 verification artifact.
- **Audit cleanup (Phase 5):** Top-level docs routing, Phase 3 verification bookkeeping, and every Node parity contract artifact were reconciled to the live one-tier 705-row baseline with persistent planning-audit and tripwire guards.

### What Worked

- **Owner-reparent reuse across phases:** The parity contract owner-merge helper from Phase 1 carried cleanly into later merges and kept parity metadata edits deterministic.
- **Single-source verification artifacts:** Refreshing parent verification artifacts in place kept closure evidence understandable and let the milestone audit reason over one canonical verifier per phase.
- **Audit-driven cleanup plans:** Phase 5 showed that narrow cleanup plans plus deterministic planning tests are an effective way to close documentation and contract drift without reopening already-correct runtime code.

### What Was Inefficient

- **Planning-state drift lasted longer than implementation drift.** The code and parity gates were green before ROADMAP/VALIDATION bookkeeping fully caught up, which forced extra cleanup work late in the milestone.
- **Node parity contract narrative drift happened in layers.** The markdown contract, then the JSON contract description, each lagged behind the already-correct runtime/report truth, which created multiple tiny follow-up plans.
- **Milestone archive scaffolding was only partial.** `gsd-tools milestone complete` copied the files, but the active roadmap and archive surfaces still needed manual cleanup to become true shipped-state records.

### Patterns Established

- **Planning audits should assert real filesystem and artifact truths, not just copied text fragments.** Phase 5 only closed cleanly once the tests checked on-disk absence and contract wording directly.
- **Human-readable and machine-readable parity contracts both need executable anti-drift checks.** Narrative drift is cheap to introduce and easy to miss unless both surfaces are guarded.
- **Milestone completion still needs a manual archive-quality pass.** Auto-archival is useful for bootstrapping, but shipped planning artifacts need human cleanup for roadmap collapse, project evolution, and archive readability.

### Key Lessons

1. **Bookkeeping debt compounds if left behind after phase verification.** The late Phase 5 work was almost entirely cleanup of planning/docs artifacts that could have been closed immediately after earlier verifier passes.
2. **Treat parity contract prose as part of the product surface.** Once parity policy becomes one-tier, every checked-in narrative artifact has to move with it or the next audit will surface contradictions.
3. **Milestone archives should be written as shipped records, not raw snapshots.** A copied roadmap that still says "in progress" is not a trustworthy historical artifact.
4. **Phase-cleanup work benefits from tiny, verifier-sourced plans.** Each Phase 5 gap plan stayed small, measurable, and easy to validate because it mapped one verifier finding to one concrete artifact set.

### Cost Observations

- Model mix: not tracked for this milestone (no per-session token telemetry)
- Sessions: ~3 days of execution and cleanup (2026-04-10 to 2026-04-12)
- Notable: Most post-Phase-4 work was artifact reconciliation, not runtime debugging. The expensive part was context switching across docs, audits, validation, and contract surfaces rather than implementing new code paths.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 Codebase Cleanup (2026-02-02) | unknown | 5 | Initial cleanup of Python-Rust hybrid; eliminated redundancies |
| v8.2.0-part2 Rust Migration (2026-02-04) | unknown | 6 | Python → Rust migration with golden file parity |
| v8.3.0 Performance & Polish (2026-02-05) | unknown | 7 | Criterion benchmark infrastructure + GIL release audit |
| v9.1.0-bugfixes CLASSIC Codebase Health (2026-04-07) | ~4 days | 11 (8 + 3 gap closure) | Three-source verification audit pattern; gap-closure phases refresh parent verification in place |
| v9.1.0-bindings Full Bindings Parity (2026-04-10) | ~4 days | 7 | Wave-based promotion pattern; @rust-suffix proxy rows; M7 atomic cascade; source-only CXX gate; triple-gate CI canary |
| v9.1.0-consolidation Crate Consolidation (2026-04-12) | ~3 days | 5 | Semantic crate consolidation plus audit-driven cleanup plans and parity-contract anti-drift guards |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 Codebase Cleanup | 71% baseline | — | Vulture CI |
| v8.2.0-part2 Rust Migration | 3,849 tests passing | — | Golden file parity infrastructure |
| v8.3.0 Performance & Polish | 77+ Criterion benchmarks | — | Flamegraph, py-spy, dhat, DashMap instrumentation |
| v9.1.0-bugfixes CLASSIC Codebase Health | added Phase 5/6 benchmark groups + Phase 6 mmap parity test + tests/planning artifact regression | — | `dts:freshness:check`, three-source audit matrix |
| v9.1.0-bindings Full Bindings Parity | CXX gate 316-entry baseline + Python 1098 tier1 rows + Node 109 promoted entries + triple-gate canary | — | CXX parity gate, promotion audit trail, `binding-parity-policy.md`, `error-contract.md` |
| v9.1.0-consolidation Crate Consolidation | 5 passed phase verifiers + 4/4 integration flows + Phase 5 planning audits/tripwires | — | semantic-owner parity routing, milestone cleanup audit guards, machine/human contract anti-drift checks |

### Top Lessons (Verified Across Milestones)

1. **Phase verification must record fresh command-backed evidence**, not inherit summary prose. Verified across v8.3.0 (where benchmark proof discipline was new) and v9.1.0-bugfixes (where 12 verification gaps were the entire audit blocker).
2. **Bounded caches with explicit eviction policy are non-negotiable for long-running processes.** v9.1.0-bugfixes Phase 4 was the first milestone to enforce this universally; future caches inherit the canonical 5-field `CacheStats` contract.
3. **Single authoritative verification artifact per phase.** When parallel verification files disagree, the milestone audit flags it. Gap-closure phases should refresh the parent in place, not create siblings.
4. **Validate version numbers against MILESTONES.md before planning kickoff.** v9.1.0-bugfixes was originally labeled `v1.0` and only renamed at ship time after the duplicate-version conflict surfaced.
5. **Plan scaffolds diverge from live state — verify row counts before execution.** v9.1.0-bindings Phases 3/4 needed inventory-first corrections in nearly every plan because estimates drifted from live baseline counts. Future binding-promotion plans should require a live-count verification step.
6. **Cross-AI review pays for itself on FFI-boundary plans.** CXX bridge plans encode domain-specific constraints (shared enum rules, Files lists, Path-taking signatures) that internal plan checkers miss. Verified in v9.1.0-bindings Phase 2.
7. **Governance file deletion is irreversible — always create an audit trail first.** The 18K-line promotion audit trail from v9.1.0-bindings Phase 6 is the only queryable record of which entries came from which governance file.
8. **Audit cleanup needs executable drift guards.** v9.1.0-consolidation Phase 5 only stayed closed once filesystem absence, markdown policy, and JSON contract wording were all guarded by tests instead of trusted as static prose.
