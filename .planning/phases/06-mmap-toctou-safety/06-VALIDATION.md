---
phase: 06
slug: mmap-toctou-safety
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in test harness + `tokio::test`; Criterion 0.6.0 |
| **Config file** | `ClassicLib-rs/business-logic/classic-file-io-core/Cargo.toml`, `ClassicLib-rs/criterion.toml` |
| **Quick run command** | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` |
| **Full suite command** | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml && cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks -- --test` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture`
- **After every plan wave:** Run `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml && cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks -- --test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SAFE-05 | unit | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 1 | SAFE-05 | docs-contract | `rg "map_copy_read_only" docs/api/classic-file-io-core.md .planning/PROJECT.md .planning/REQUIREMENTS.md` | ✅ | ⬜ pending |
| 06-02-01 | 02 | 2 | SAFE-05 | benchmark-smoke | `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 2 | SAFE-05 | benchmark-proof | `$env:BENCH_MODE='thorough'; cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --save-baseline phase6-mmap-baseline; cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --baseline phase6-mmap-baseline` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
