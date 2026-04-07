---
phase: 05
slug: pattern-caching-and-performance
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in test harness + `serial_test`; Criterion 0.6.0 |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml`, `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/Cargo.toml`, `ClassicLib-rs/criterion.toml` |
| **Quick run command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_` |
| **Full suite command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_ && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern && cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's listed automated command.
- **After every plan wave:** Run `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_ && cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern && cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test`.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | PERF-01 | unit-regression | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | CONS-04 | source-doc-audit | `rg -n "LazyLock|quick_cache|bounded matcher-cache" ClassicLib-rs/business-logic/classic-scanlog-core/src/mod_detector.rs docs/api/classic-scanlog-core.md` | ✅ | ✅ green |
| 05-02-01 | 02 | 2 | PERF-02 | parity-unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important` | ✅ | ✅ green |
| 05-02-02 | 02 | 2 | PERF-02 | matcher-swap-regression | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important` | ✅ | ✅ green |
| 05-03-01 | 03 | 1 | PERF-03 | bridge-unit | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml detect_crash_pattern` | ✅ | ✅ green |
| 05-03-02 | 03 | 1 | PERF-03 | docs-contract | `rg -n "detect_crash_pattern|cached default parser" docs/api/classic-cpp-bridge-data-entrypoints.md` | ✅ | ✅ green |
| 05-04-01 | 04 | 3 | PERF-04 | benchmark-smoke | `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks -- --test` | ✅ | ✅ green |
| 05-04-02 | 04 | 3 | PERF-04 | baseline-doc-audit | `rg -n "scanlog_benchmarks|--save-baseline|--baseline|phase5-before|05-BENCHMARK-PROOF.md" performance_baselines/README.md` | ✅ | ✅ green |
| 05-05-01 | 05 | 1 | PERF-01 | exact-unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml mod_detector::tests::test_detect_mods_double_reuses_cached_matcher_for_same_conflict_set -- --exact` | ✅ | ✅ green |
| 05-05-02 | 05 | 1 | PERF-01 | grouped-unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_` | ✅ | ✅ green |
| 05-06-01 | 06 | 1 | PERF-04 | proof-audit | `rg -n "phase5_cached_regex_paths|phase5_detect_mods_important|phase5_bridge_crash_pattern_replica|PASS" .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` | ✅ | ✅ green |
| 05-06-02 | 06 | 1 | PERF-04 | requirements-audit | `rg -n "PERF-04|SAFE-05|mmap throughput" .planning/REQUIREMENTS.md .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` | ✅ | ✅ green |
| 05-07-01 | 07 | 3 | PERF-04 | benchmark-slice-smoke | `cargo bench -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml --bench scanlog_benchmarks phase5_detect_mods_important -- --test` | ✅ | ✅ green |
| 05-07-02 | 07 | 3 | PERF-02 | parity-regression | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml detect_mods_important` | ✅ | ✅ green |
| 05-07-03 | 07 | 3 | PERF-04 | proof-refresh-audit | `rg -n "79.6% faster|22.8% faster|aho_compile_only_synthetic_literals|aho_build_haystack_only_real_fixture_plugin_surface" .planning/phases/05-pattern-caching-and-performance/05-BENCHMARK-PROOF.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60 seconds
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
