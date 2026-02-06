# Phase 27: Coverage Baseline

**Measured:** 2026-02-06
**Tool:** cargo-llvm-cov 0.8.3, rustc 1.91.1 (stable)
**Exclusions:** Slint generated code, build artifacts (`--ignore-filename-regex "(target[/\\]|build[/\\]|\.slint)"`)
**Features:** `gui-bridge` enabled for classic-shared-core AsyncBridge tests

## Workspace Summary

- Total crates measured: 21 (2 foundation + 18 business-logic + 1 GUI)
- Crates at/above 60%: 18
- Crates below 60%: 3
- Workspace aggregate: 15,615 / 21,679 lines (72.0%)

## Per-Crate Coverage

### Foundation

| Crate | Lines Covered | Lines Total | Coverage | Status |
|-------|--------------|-------------|----------|--------|
| classic-shared-core | 429 | 872 | 49.2% | GAP |

### Business Logic

| Crate | Lines Covered | Lines Total | Coverage | Status |
|-------|--------------|-------------|----------|--------|
| classic-config-core | 1,092 | 1,228 | 88.9% | PASS |
| classic-constants-core | 378 | 425 | 88.9% | PASS |
| classic-database-core | 873 | 976 | 89.4% | PASS |
| classic-file-io-core | 1,816 | 2,008 | 90.4% | PASS |
| classic-message-core | 396 | 396 | 100.0% | PASS |
| classic-path-core | 1,152 | 1,363 | 84.5% | PASS |
| classic-perf-core | 233 | 234 | 99.6% | PASS |
| classic-pybridge-core | 146 | 146 | 100.0% | PASS |
| classic-registry-core | 161 | 181 | 89.0% | PASS |
| classic-resource-core | 154 | 223 | 69.1% | PASS |
| classic-scangame-core | 1,397 | 1,944 | 71.9% | PASS |
| classic-scanlog-core | 3,120 | 5,033 | 62.0% | PASS |
| classic-settings-core | 878 | 902 | 97.3% | PASS |
| classic-update-core | 500 | 545 | 91.7% | PASS |
| classic-version-core | 194 | 215 | 90.2% | PASS |
| classic-version-registry-core | 1,392 | 1,568 | 88.8% | PASS |
| classic-web-core | 324 | 326 | 99.4% | PASS |
| classic-xse-core | 107 | 164 | 65.2% | PASS |
| classic-yaml-core | 246 | 1,253 | 19.6% | GAP |

### UI Applications

| Crate | Lines Covered | Lines Total | Coverage | Status |
|-------|--------------|-------------|----------|--------|
| classic-gui | 627 | 1,677 | 37.4% | GAP |

### Python Bindings (informational only -- excluded from 60% target)

PyO3 binding crates were excluded from the coverage test run because they require the Python DLL at runtime (`STATUS_DLL_NOT_FOUND` error). These crates are thin adapters over the `-core` business logic crates, which are fully measured. Use `--exclude` flags when running `cargo llvm-cov` to skip them.

**Excluded crates (19):**
classic-shared-py, classic-yaml-py, classic-database-py, classic-file-io-py, classic-scanlog-py, classic-config-py, classic-scangame-py, classic-registry-py, classic-perf-py, classic-pybridge-py, classic-settings-py, classic-message-py, classic-path-py, classic-constants-py, classic-version-py, classic-resource-py, classic-xse-py, classic-web-py, classic-update-py

## Gap Prioritization

Crates below 60% line coverage, sorted by impact (lines_total * gap_to_60%) descending:

| Priority | Crate | Coverage | Lines Total | Lines Needed to Reach 60% | Impact Score |
|----------|-------|----------|-------------|--------------------------|--------------|
| 1 | classic-yaml-core | 19.6% | 1,253 | ~507 | 50,641 |
| 2 | classic-gui | 37.4% | 1,677 | ~380 | 37,899 |
| 3 | classic-shared-core | 49.2% | 872 | ~95 | 9,418 |

### Gap Analysis

**classic-yaml-core (19.6%)** -- Largest gap. Has 65 inline tests that all pass, but coverage is low because the global `YAML_CACHE` (DashMap) and the `YamlOperations` struct have extensive code paths (batch loading, async loading, cache management, save operations) that existing tests exercise via the cache-aware API. The `test_cache_stats_empty` test is flaky due to global state contamination from parallel tests. Estimated effort: Medium-high (many I/O-dependent code paths).

**classic-gui (37.4%)** -- GUI crate has 39 inline tests covering markdown parsing, results formatting, and state management. Uncovered areas include settings logic, worker orchestration, and window state persistence. Many functions are pure Rust logic behind the GUI (no Slint dependency), making them testable via the existing `lib.rs` exports. Estimated effort: Medium (testable modules exist, need more test cases).

**classic-shared-core (49.2%)** -- Foundation crate with 19 passing tests (15 AsyncBridge + 4 other). The `gui-bridge` feature was enabled during measurement. Gap is primarily in the `path_lru` module and `performance_core` module's less-exercised paths. Estimated effort: Low (small gap, ~95 lines to cover).

## Notes

- **Generated code excluded:** Slint bindings (~85K generated lines in `target/debug/build/`) and build artifacts are excluded from all metrics.
- **PyO3 binding crates reported separately:** Thin adapters whose business logic lives in `-core` crates. Cannot run tests without Python interpreter.
- **gui-bridge feature enabled:** classic-shared-core's AsyncBridge module (15 tests) was measured with `--features gui-bridge`.
- **Flaky test noted:** `classic-yaml-core::tests::test_cache_stats_empty` fails intermittently due to global state contamination from parallel tests. This is a pre-existing issue (Pitfall 3 from research), not introduced by coverage tooling.
- **Surprise: Most crates already pass.** 18 of 21 measurable crates already exceed 60% line coverage. Only 3 crates need gap-filling work.
- **High performers:** classic-message-core (100%), classic-pybridge-core (100%), classic-perf-core (99.6%), classic-web-core (99.4%), classic-settings-core (97.3%) demonstrate excellent existing test coverage.
- **Workspace aggregate (72%)** is strong -- the 60% target is achievable with focused work on just 3 crates.
