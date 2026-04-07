---
phase: 06-mmap-toctou-safety
verified: 2026-04-06T10:58:32.2795290Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "Declared Phase 6 crate validation commands pass cleanly"
  gaps_remaining: []
  regressions: []
---

# Phase 6: mmap TOCTOU Safety Verification Report

**Phase Goal:** Memory-mapped file reads are safe against time-of-check-to-time-of-use races on Windows
**Verified:** 2026-04-06T10:58:32.2795290Z
**Status:** passed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Large-file reads use `map_copy_read_only()` instead of shared `Mmap::map()` access | ✓ VERIFIED | `read_file_mmap()` now uses `MmapOptions::new().map_copy_read_only(&file)` in `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs:1029-1047`, and grep found no `Mmap::map(` in `classic-file-io-core`. |
| 2 | Large-file and small-file reads still return the same decoded text contract as before | ✓ VERIFIED | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` passed all 3 mmap regression tests, including the large non-UTF-8 contract check. |
| 3 | Contributor-facing docs and milestone docs all describe the locked `map_copy_read_only()` contract | ✓ VERIFIED | `docs/api/classic-file-io-core.md`, `.planning/PROJECT.md`, and `.planning/REQUIREMENTS.md` all contain `map_copy_read_only()` wording for Phase 6 / SAFE-05. |
| 4 | Phase 6 benchmark coverage compares `map()`, `map_copy()`, and `map_copy_read_only()` on files that definitely exercise the mmap branch | ✓ VERIFIED | `file_io_benchmarks.rs` defines `phase6_mmap_variants`, benchmarks all 3 variants, and locks sizes at `1_048_576 + 4_096`, `4 * 1_048_576`, and `16 * 1_048_576`. |
| 5 | The committed proof artifact records commands, sizes, results, and an acceptability call for Windows validation | ✓ VERIFIED | `.planning/phases/06-mmap-toctou-safety/06-BENCHMARK-PROOF.md` includes save/compare/test commands, tested sizes, medians, and an explicit Windows acceptability call for `map_copy_read_only()`. |
| 6 | Raw Criterion baselines stay local-only while the repo keeps a shareable markdown proof | ✓ VERIFIED | `performance_baselines/README.md` keeps raw output under `ClassicLib-rs/target/criterion/` and points contributors to the committed Phase 6 proof artifact. |
| 7 | Declared Phase 6 crate validation commands pass cleanly | ✓ VERIFIED | `cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` now passes; the prior inline unsafe benchmark constructors were refactored into narrow helper functions with local allow annotations. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` | Phase 6 mmap strategy and regression tests | ✓ VERIFIED | Exists, substantive, and wired through `read_file()` → `read_file_mmap()`; `gsd-tools verify artifacts` passed for 06-01. |
| `docs/api/classic-file-io-core.md` | Updated file-io mmap behavior contract | ✓ VERIFIED | Exists and documents the 1 MB split plus `map_copy_read_only()` contract; `gsd-tools verify artifacts` passed for 06-01. |
| `.planning/PROJECT.md` | Milestone wording aligned to Phase 6 mmap contract | ✓ VERIFIED | Exists and uses `map_copy_read_only()` for the active Phase 6 item and decision log. |
| `.planning/REQUIREMENTS.md` | SAFE-05 wording aligned to Phase 6 mmap contract | ✓ VERIFIED | Exists and maps SAFE-05 to `MmapOptions::map_copy_read_only()`. |
| `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` | Phase 6 mmap throughput benchmark group in existing harness | ✓ VERIFIED | Exists, substantive, wired into `criterion_group!`, benchmark smoke passes, and clippy is green after the helper refactor; `gsd-tools verify artifacts` passed for 06-02 and 06-03. |
| `.planning/phases/06-mmap-toctou-safety/06-BENCHMARK-PROOF.md` | Committed Windows-focused mmap throughput proof | ✓ VERIFIED | Exists and records commands, sizes, results, and acceptability call. |
| `performance_baselines/README.md` | Contributor workflow for local Phase 6 benchmark baselines | ✓ VERIFIED | Exists and documents the local-only save/compare workflow for `phase6_mmap_variants`. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `core.rs` | `memmap2::MmapOptions` | large-file branch in `read_file_mmap()` | ✓ WIRED | `gsd-tools verify key-links` for 06-01 found the `map_copy_read_only` pattern in source. |
| `core.rs` | `tokio::fs::metadata` | 1 MB threshold branch before mapping | ✓ WIRED | `gsd-tools verify key-links` for 06-01 verified the `MMAP_THRESHOLD` / metadata split. |
| `docs/api/classic-file-io-core.md` | `core.rs` | documented `read_file()` / `read_file_mmap()` behavior | ✓ WIRED | `gsd-tools verify key-links` for 06-01 verified matching contract wording. |
| `file_io_benchmarks.rs` | `core.rs` | benchmark-local helpers mirror the production decode path after 06-01 | ✓ WIRED | `gsd-tools verify key-links` for 06-02 verified the benchmark-to-core linkage. |
| `06-BENCHMARK-PROOF.md` | `performance_baselines/README.md` | same local-only baseline workflow and artifact location | ✓ WIRED | `gsd-tools verify key-links` for 06-02 verified the baseline workflow link. |
| `file_io_benchmarks.rs` | `memmap2::MmapOptions` | narrow helper functions for the three mmap variants | ✓ WIRED | `gsd-tools verify key-links` for 06-03 verified `map_file_shared|map_file_copy|map_file_copy_read_only`. |
| `file_io_benchmarks.rs` | `read_file_with_variant` | variant match dispatch through helpers instead of inline unsafe blocks | ✓ WIRED | `gsd-tools verify key-links` for 06-03 verified helper-based dispatch. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-file-io-core/src/core.rs` | `mmap` / decoded text | `tokio::fs::metadata(path)` → `File::open(path)` → `MmapOptions::map_copy_read_only(&file)` | Yes — real file bytes are mapped and decoded into the returned API result | ✓ FLOWING |
| `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` | benchmark input `path` / decoded text | synthetic files written once with `std::fs::write`, then reopened and mapped in `read_file_with_variant()` | Yes — the benchmark exercises real on-disk files above the mmap threshold | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| mmap regression coverage works | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` | 3 tests passed (`small_file`, `large_file`, `large_non_utf8_matches_existing_decode_contract`) | ✓ PASS |
| benchmark group is runnable | `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test` | All 9 Phase 6 benchmark cases reported `Success` | ✓ PASS |
| phase validation lint gate is green | `cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | Passed cleanly | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `SAFE-05` | `06-01-PLAN.md`, `06-02-PLAN.md`, `06-03-PLAN.md` | Switch `read_file_mmap` from `Mmap::map()` to `MmapOptions::map_copy_read_only()` for TOCTOU safety on Windows | ✓ SATISFIED | Production code uses `map_copy_read_only()`, decode behavior is regression-tested, benchmark coverage and proof exist, and the declared clippy gate now passes. |

Orphaned requirements for Phase 6 in `.planning/REQUIREMENTS.md`: none. The only Phase 6 requirement is `SAFE-05`, and all three phase plans declare it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` | 153 | `#[allow(unsafe_code)]` on `map_file_shared` helper | ℹ️ Info | Expected narrow benchmark-only unsafe boundary; no longer trips crate clippy gate. |
| `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` | 160 | `#[allow(unsafe_code)]` on `map_file_copy` helper | ℹ️ Info | Expected narrow benchmark-only unsafe boundary; scoped to helper instead of inline match arm. |
| `ClassicLib-rs/business-logic/classic-file-io-core/benches/file_io_benchmarks.rs` | 171 | `#[allow(unsafe_code)]` on `map_file_copy_read_only` helper | ℹ️ Info | Expected narrow benchmark-only unsafe boundary; scoped and documented. |

### Human Verification Required

None.

### Gaps Summary

The prior blocker is closed. Phase 6 now achieves its goal end-to-end: production large-file reads use the locked `map_copy_read_only()` strategy, the public decode contract remains covered by tests, the benchmark harness and proof artifact cover the required three-way Windows-focused throughput comparison, raw Criterion baselines remain local-only, and the crate's declared validation commands all pass cleanly.

---

_Verified: 2026-04-06T10:58:32.2795290Z_
_Verifier: the agent (gsd-verifier)_
