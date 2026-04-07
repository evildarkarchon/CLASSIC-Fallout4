# Phase 10: Pattern Caching Verification Backfill - Research

**Researched:** 2026-04-06
**Domain:** Verification-backfill for Rust pattern-caching work and Phase 5 audit closure
**Confidence:** HIGH

## Summary

Phase 10 is a verification-closure phase, not a new implementation phase. The missing work is not new Rust behavior in `mod_detector.rs` or `classic-cpp-bridge`; it is the absence of explicit Phase 5 verification evidence for `PERF-03` and `CONS-04`, even though Phase 5 summaries already claimed those requirements complete. The repo’s established gap-closure pattern, confirmed by Phase 9, is to refresh the original phase verification artifact in place with current command-backed evidence and reconcile `.planning/REQUIREMENTS.md` traceability in the same change.

The safest plan is to make `.planning/phases/05-pattern-caching-and-performance/05-VERIFICATION.md` the authoritative Phase 5 story again, using `05-VALIDATION.md` as the command source of truth, `05-01-SUMMARY.md` and `05-03-SUMMARY.md` as provenance only, and current source/docs/benchmark artifacts as evidence. Do not invent new implementation claims, and do not treat old summaries as proof.

**Primary recommendation:** Refresh `05-VERIFICATION.md` in repo-standard re-verification form, explicitly cover `PERF-03` and `CONS-04` with current evidence, and update `.planning/REQUIREMENTS.md` so Phase 10 closes the orphaned traceability while Phase 5 regains a coherent verification narrative.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-03 | Replace per-call `LogParser::new(None)` in C++ bridge `detect_crash_pattern` with module-level `LazyLock<LogParser>` | Use `05-03-PLAN.md`, current `scanner.rs`, bridge tests, API doc note, and existing Phase 5 benchmark proof as verification evidence |
| CONS-04 | Use `LazyLock` with `Regex::new().unwrap()` for static patterns in `mod_detector` to move compilation failure to startup | Re-verify against `05-01-PLAN.md`, current `mod_detector.rs`, `docs/api/classic-scanlog-core.md`, and the plan’s explicit “do not invent fake statics” rule |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs`.
- Keep all business logic in Rust; shared behavior, validation, persistence rules, and state transitions belong in Rust core crates unless the task is explicitly interface-only.
- Keep non-interface layers thin; C++, Python, Node, and other bindings should wrap Rust APIs rather than reimplement logic.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce independent runtimes.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if contract-shaping behavior changes, update the affected `docs/api/` pages in the same change.
- Never run C++ tests by invoking test binaries or raw `ctest`; use the repo PowerShell wrappers for C++ tests.

## Standard Stack

> This is a verification-only phase. Use the repo-pinned stack already present; do not upgrade dependencies in this phase.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `std::sync::LazyLock` | std 1.94.1 docs verified | Canonical lazy singleton primitive for the cached parser and any constant regex statics | Official Rust docs confirm thread-safe first-access init for statics; repo already standardized on `LazyLock` |
| `regex` | workspace `1.12.2` | Underlying regex type referenced by `CONS-04` evidence | Existing workspace dependency; requirement is about compile-once static usage, not dependency choice |
| `criterion` | pinned `0.6.0` in `classic-scanlog-core` dev-dependencies | Benchmark proof backing Phase 5 hotspot claims | Existing Phase 5 proof artifact and harness already use it; no new benchmark system should be introduced |
| `ripgrep` (`rg`) | env `15.1.0` | Fast source/doc audit for verification tables | Already used in `05-VALIDATION.md` and milestone audit workflows |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `cargo test` / Rust harness | cargo `1.94.0`, rustc `1.94.0` | Runtime proof for `detect_crash_pattern` behavior | Use for current bridge evidence instead of inferring from unchanged files |
| `quick_cache` | workspace `0.6` | Repo-standard bounded cache pattern referenced by Phase 5 docs | Use only as cited implementation evidence; do not reopen cache design |
| `aho-corasick` | workspace `1.1.4` | Existing Phase 5 PERF-02 context | Only cite for Phase 5 consistency if the refreshed artifact re-lists all Phase 5 requirements |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Refreshing `05-VERIFICATION.md` in place | New Phase 10-only closure note for Phase 5 evidence | Bad tradeoff; duplicates authority and repeats the stale-story problem Phase 9 already solved |
| Rerun-command evidence | Summary prose only | Bad tradeoff; summaries are provenance, not proof |
| Reusing `05-VALIDATION.md` commands | Ad hoc new verification commands | Bad tradeoff; weakens traceability and invites drift |

**Installation:**

No new dependencies. This phase should stay docs/traceability-focused.

**Version verification:**

- Workspace pins verified from `ClassicLib-rs/Cargo.toml`: `regex 1.12.2`, `aho-corasick 1.1.4`, `quick_cache 0.6`, `serial_test 3.4.0`
- Phase 5 bench pin verified from `classic-scanlog-core/Cargo.toml`: `criterion 0.6.0`
- Local execution tools verified: `cargo 1.94.0`, `rustc 1.94.0`, `rg 15.1.0`, `pwsh 7.6.0`

## Architecture Patterns

### Recommended Project Structure
```text
.planning/
├── REQUIREMENTS.md                                            # completion + traceability closure
└── phases/
    ├── 05-pattern-caching-and-performance/
    │   ├── 05-VALIDATION.md                                   # command source of truth
    │   ├── 05-VERIFICATION.md                                 # authoritative Phase 5 artifact to refresh
    │   ├── 05-01-SUMMARY.md                                   # CONS-04 provenance only
    │   ├── 05-03-SUMMARY.md                                   # PERF-03 provenance only
    │   └── 05-BENCHMARK-PROOF.md                              # PERF-03 performance proof source
    └── 10-pattern-caching-verification-backfill/
        └── 10-RESEARCH.md                                     # this research
```

### Pattern 1: Re-verify the original phase artifact in place
**What:** Update `05-VERIFICATION.md`, not a new parallel Phase 5 closure artifact.

**When to use:** Audit-gap closure phases where implementation already landed and only verification coverage is stale or incomplete.

**Prescriptive rules:**
- Add `re_verification:` metadata if the artifact is being refreshed.
- Treat earlier Phase 5 summaries as historical claims only.
- Put fresh or current command-backed evidence directly in the refreshed verification artifact.
- Keep Phase 10 ownership in `.planning/REQUIREMENTS.md` traceability, even though the authoritative implementation story lives in the Phase 5 verification file.

**Example:**
```markdown
---
phase: 05-pattern-caching-and-performance
verified: 2026-04-06T00:00:00Z
status: passed
re_verification:
  previous_status: gaps_found
  gaps_closed:
    - "PERF-03 and CONS-04 now have explicit current evidence in 05-VERIFICATION.md"
---

## Re-Verification Summary

Phase 10 closes an audit gap in the original Phase 5 artifact. The Phase 5 summaries remain provenance only.
```

### Pattern 2: Promote validation-map entries into verification evidence
**What:** Use `05-VALIDATION.md` as the canonical list of commands and behaviors, then record their evidence in `05-VERIFICATION.md`.

**When to use:** Whenever a phase already has a validation contract but the verification artifact under-reports some requirements.

**Prescriptive rules:**
- Reuse the declared `05-03-01`, `05-03-02`, and `05-01-02` style checks.
- Prefer targeted commands already proven in the phase.
- Cross-link source, docs, and proof artifacts in the requirement coverage table.

**Example:**
```markdown
| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `PERF-03` | `05-03-PLAN.md` | Cached bridge parser reuse for `detect_crash_pattern` | ✓ SATISFIED | `scanner.rs:43-44,1128-1156`; `docs/api/classic-cpp-bridge-data-entrypoints.md:541-555`; `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern`; `05-BENCHMARK-PROOF.md:55-62` |
```

### Pattern 3: Verify requirement intent, not a fake implementation shape
**What:** For `CONS-04`, verify the actual accepted Phase 5 outcome: no touched input-invariant regex is compiled per call, and no fake static regex was invented just to satisfy wording.

**When to use:** Requirements whose plain wording can be misread more rigidly than the plan/summary/implementation history allows.

**Prescriptive rules:**
- Use `05-01-PLAN.md` Task 2 and `05-01-SUMMARY.md` as interpretive guardrails.
- Cite the docs note in `classic-scanlog-core.md` that truly constant regexes belong behind dedicated `LazyLock` statics, while input-derived alternation regexes stay on bounded caches.
- Do not claim a new `LazyLock<Regex>` exists in `mod_detector.rs` if the touched code intentionally kept only bounded caches.

### Anti-Patterns to Avoid
- **Creating a second authoritative Phase 5 closure file:** makes the audit story worse, not better.
- **Using summaries as proof:** they are claims, not evidence.
- **Backfilling only PERF-03/CONS-04 and leaving the phase artifact internally fragmented:** Phase 5’s final verification story should read coherently across all remaining Phase 5 requirements.
- **Over-literal reading of CONS-04:** the plan explicitly forbade inventing fake static regexes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gap-closure proof | New ad hoc markdown note outside the original phase artifact | Refresh `05-VERIFICATION.md` | Repo-standard pattern already established by Phase 9 |
| Requirement evidence | Summary-only narrative | `05-VALIDATION.md` commands + current source/docs/proof artifacts | Preserves traceability and auditability |
| PERF-03 performance proof | New benchmark harness or manual timing | Existing `05-BENCHMARK-PROOF.md` + Criterion-backed Phase 5 harness | The proof already exists and is explicitly scoped |
| CONS-04 justification | Invented static regex refactor narrative | Actual `05-01-PLAN.md`/summary outcome | Avoids false claims about implementation shape |

**Key insight:** Phase 10 should not “re-implement” Phase 5 in prose. It should re-state Phase 5 truth using the repo’s existing command, source, docs, and benchmark evidence model.

## Common Pitfalls

### Pitfall 1: Treating summary files as verification
**What goes wrong:** The refreshed artifact still cites `05-01-SUMMARY.md` or `05-03-SUMMARY.md` as if they were proof.
**Why it happens:** Summaries are easy to read and already mention the missing requirements.
**How to avoid:** Use summaries only for provenance; pair every requirement with source lines, docs lines, and a rerunnable command or committed proof artifact.
**Warning signs:** Requirement table evidence column contains only summary filenames or commit hashes.

### Pitfall 2: Misreporting CONS-04 as “a new static regex exists in mod_detector”
**What goes wrong:** Verification claims a concrete static-regex implementation that the Phase 5 plan explicitly said not to invent.
**Why it happens:** The requirement wording is shorter than the accepted implementation nuance.
**How to avoid:** Anchor on `05-01-PLAN.md` Task 2 and `05-01-SUMMARY.md` decisions: input-derived regexes stay on bounded caches; only true constants should use dedicated `LazyLock` statics.
**Warning signs:** Evidence for CONS-04 cannot point to a real line in `mod_detector.rs` without stretching the truth.

### Pitfall 3: Confusing plan verification with phase verification
**What goes wrong:** `05-07-VERIFICATION.md` is treated as the phase-wide authoritative artifact.
**Why it happens:** It is newer and passed, but it is scoped to Plan 07 only.
**How to avoid:** Keep `05-VERIFICATION.md` authoritative for phase-wide closure; use `05-07-VERIFICATION.md` only as supporting provenance for PERF-02/PERF-04 consistency if needed.
**Warning signs:** The refreshed Phase 5 artifact omits PERF-02 or PERF-04 because “05-07 already covered them.”

### Pitfall 4: Updating the verification file without closing traceability
**What goes wrong:** `05-VERIFICATION.md` is fixed, but `.planning/REQUIREMENTS.md` still shows `PERF-03` and `CONS-04` pending.
**Why it happens:** Docs work is split mentally from checklist ownership.
**How to avoid:** Update the checklist and traceability rows in the same change, following the Phase 9 pattern.
**Warning signs:** Milestone audit would still classify the requirements as orphaned after the backfill.

## Code Examples

Verified patterns from repo and official sources:

### Refresh re-verification metadata in-place
```markdown
---
phase: 05-pattern-caching-and-performance
verified: 2026-04-06T00:00:00Z
status: passed
score: 5/5 success criteria verified
re_verification:
  previous_status: passed
  previous_score: 2/2 must-haves verified
  gaps_closed:
    - "Added explicit PERF-03 bridge parser reuse evidence"
    - "Added explicit CONS-04 mod_detector regex-init evidence"
  gaps_remaining: []
  regressions: []
---
```

### PERF-03 implementation evidence shape
```rust
// Source: ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs
static CRASH_PATTERN_PARSER: LazyLock<classic_scanlog_core::LogParser> =
    LazyLock::new(|| LogParser::new(None).expect("default crash-pattern parser should initialize"));

#[test]
fn test_detect_crash_pattern_repeated_calls_keep_same_positive_result() {
    let first = detect_crash_pattern(input);
    let second = detect_crash_pattern(input);
    assert_eq!(first, second);
}
```

### CONS-04 verification framing
```markdown
`mod_detector.rs` now keeps input-derived alternation regexes on bounded `LazyLock<quick_cache::sync::Cache<...>>`
caches, while contributor docs explicitly state that truly constant regex helpers should compile once through
dedicated `LazyLock` statics instead of per-call construction.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Verification artifact drifted from later summaries and audit findings | In-place re-verification of the original artifact with fresh command-backed evidence | Established in Phase 9 on 2026-04-07 | Gap-closure phases should refresh authoritative artifacts, not append parallel notes |
| `once_cell::sync::Lazy` examples commonly used in regex docs/readmes | Repo-standard `std::sync::LazyLock` for new owned statics | Rust std stabilized `LazyLock` in 1.80; repo codified this in Phase 7 | Verification should describe `LazyLock`, even if older upstream examples still show `once_cell` |

**Deprecated/outdated:**
- Summary-only closure claims: outdated for audit-facing verification work.
- New ad hoc benchmark proof mechanisms: outdated here because Phase 5 already has committed Criterion proof.

## Open Questions

1. **Should refreshed `05-VERIFICATION.md` enumerate all current Phase 5 requirements or only the orphaned ones?**
   - What we know: success criterion 3 requires the final Phase 5 verification story to be internally consistent.
   - What's unclear: whether a minimal PERF-03/CONS-04 patch would satisfy that bar.
   - Recommendation: enumerate all still-relevant Phase 5 requirements in `05-VERIFICATION.md`, with PERF-03 and CONS-04 added explicitly and PERF-02/PERF-04 cross-linked to the existing follow-up proof where appropriate.

2. **Does `05-07-VERIFICATION.md` need edits?**
   - What we know: the audit complaint is about missing phase-wide coverage, not that Plan 07 omitted unrelated requirements.
   - What's unclear: whether future readers may misread the newer plan verification as authoritative phase coverage.
   - Recommendation: prefer no substantive edits there; only add a scope clarifier if review shows confusion risk.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cargo` | Rust proof commands in verification tables | ✓ | 1.94.0 | — |
| `rustc` | Rust test execution environment | ✓ | 1.94.0 | — |
| `rg` | Source/doc audit commands already declared in `05-VALIDATION.md` | ✓ | 15.1.0 | PowerShell `Select-String` if needed |
| `pwsh` | Repo-standard command/documentation style | ✓ | 7.6.0 | — |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in test harness + `serial_test`; Criterion `0.6.0`; `rg` source/doc audit |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `.planning/phases/05-pattern-caching-and-performance/05-VALIDATION.md` |
| Quick run command | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern` |
| Full suite command | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern && rg -n "LazyLock|quick_cache|bounded matcher-cache" ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs docs/api/classic-scanlog-core.md && rg -n "detect_crash_pattern|cached default parser" docs/api/classic-cpp-bridge-data-entrypoints.md .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-03 | `detect_crash_pattern` uses a cached module-level parser and preserves observable output across repeated calls | bridge-unit + docs/proof audit | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern` | ✅ |
| CONS-04 | Touched `mod_detector` regex behavior no longer relies on per-call constant-regex construction and docs describe the accepted LazyLock/bounded-cache split accurately | source-doc-audit | `rg -n "LazyLock|quick_cache|bounded matcher-cache" ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs docs/api/classic-scanlog-core.md` | ✅ |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern`
- **Per wave merge:** `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern && rg -n "LazyLock|quick_cache|bounded matcher-cache" ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs docs/api/classic-scanlog-core.md`
- **Phase gate:** Refresh `05-VERIFICATION.md` only after the evidence commands and artifact audits align with `.planning/REQUIREMENTS.md`

### Wave 0 Gaps
None — existing Phase 5 validation infrastructure already declares the commands this backfill should reuse.

## Sources

### Primary (HIGH confidence)
- Official Rust docs: `https://doc.rust-lang.org/std/sync/struct.LazyLock.html` — verified `LazyLock` semantics, initialization behavior, and poisoning model
- Context7 `/rust-lang/regex` — verified upstream guidance to compile reused regexes once rather than inside hot paths
- Context7 `/criterion-rs/criterion.rs` — verified `--save-baseline` / `--baseline` workflow used by the committed Phase 5 proof
- `.planning/ROADMAP.md` — Phase 5 and Phase 10 success criteria and ownership
- `.planning/v1.0-MILESTONE-AUDIT.md` — explicit orphaned requirement findings for `PERF-03` and `CONS-04`
- `.planning/phases/05-pattern-caching-and-performance/05-VALIDATION.md` — canonical commands already mapped to `PERF-03` and `CONS-04`
- `.planning/phases/05-pattern-caching-and-performance/05-01-PLAN.md` and `05-03-PLAN.md` — requirement intent and accepted verification shape
- `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` — current `LazyLock<LogParser>` implementation and repeated-call tests
- `docs/api/classic-cpp-bridge-data-entrypoints.md` and `docs/api/classic-scanlog-core.md` — current contributor-facing contract notes

### Secondary (MEDIUM confidence)
- `.planning/phases/05-pattern-caching-and-performance/05-01-SUMMARY.md` and `05-03-SUMMARY.md` — provenance for what was claimed complete
- `.planning/phases/09-deprecated-api-verification-closure/09-01-SUMMARY.md` and `09-VERIFICATION.md` — repo-standard gap-closure pattern for in-place verification refresh

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - repo-pinned tooling and official docs agree; no dependency selection ambiguity
- Architecture: HIGH - Phase 9 provides a direct in-repo precedent for this exact gap-closure shape
- Pitfalls: HIGH - directly evidenced by the milestone audit, current Phase 5 artifact gaps, and the accepted Phase 5 plan text

**Research date:** 2026-04-06
**Valid until:** 2026-05-06
