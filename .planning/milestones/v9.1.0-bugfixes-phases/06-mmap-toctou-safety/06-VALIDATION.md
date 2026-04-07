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
| **Focused parity command** | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --test mmap_variant_parity -- --nocapture` |
| **Full suite command** | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture && cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --test mmap_variant_parity -- --nocapture && cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test && cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run the narrowest relevant command (`read_file_mmap`, `--test mmap_variant_parity`, docs `rg`, or benchmark smoke) for the touched artifact.
- **After every plan wave:** Run `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test` and `cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` once benchmark code is in scope.
- **Before `/gsd-verify-work`:** Full suite including the clippy gate must be green.
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | SAFE-05 | unit | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` | ✅ | ✅ green |
| 06-01-02 | 01 | 1 | SAFE-05 | docs-contract | `rg "map_copy_read_only" docs/api/classic-file-io-core.md .planning/PROJECT.md .planning/REQUIREMENTS.md` | ✅ | ✅ green |
| 06-02-01 | 02 | 2 | SAFE-05 | benchmark-smoke | `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test` | ✅ | ✅ green |
| 06-02-02 | 02 | 2 | SAFE-05 | benchmark-proof | `$env:BENCH_MODE='thorough'; cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --save-baseline phase6-mmap-baseline; cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --baseline phase6-mmap-baseline` | ✅ | ✅ green |
| 06-03-01 | 03 | 3 | SAFE-05 | benchmark-lint | `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test && cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | ✅ | ✅ green |
| 06-AUDIT-01 | audit | post-phase | SAFE-05 | integration | `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --test mmap_variant_parity -- --nocapture` | ✅ | ✅ green |

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

**Approval:** approved 2026-04-06

---

## Validation Audit 2026-04-06

- Updated the per-task verification map to mark completed Phase 6 tasks green and added the missing `06-03-01` row.
- Added focused automated parity coverage in `ClassicLib-rs/business-logic/classic-file-io-core/tests/mmap_variant_parity.rs` for `map`, `map_copy`, and `map_copy_read_only` on the locked Phase 6 sizes above the mmap threshold.
- Sampling and full-suite guidance now explicitly includes the final `cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` gate.

### Commands Re-run During Audit

| Command | Outcome |
|---------|---------|
| `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --test mmap_variant_parity -- --nocapture` | PASS — 1 test passed |
| `cargo test -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml read_file_mmap -- --nocapture` | PASS — 3 mmap regression tests passed |
| `cargo bench -p classic-file-io-core --manifest-path ClassicLib-rs/Cargo.toml --bench file_io_benchmarks phase6_mmap_variants -- --test` | PASS — all 9 benchmark smoke cases reported `Success` |
| `cargo clippy -p classic-file-io-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | PASS |
| `rg "map_copy_read_only" docs/api/classic-file-io-core.md .planning/PROJECT.md .planning/REQUIREMENTS.md` | PASS — aligned contract present in all active docs |

### Audit Notes

- `06-02-02` remains green based on the committed proof in `06-BENCHMARK-PROOF.md` and the already-captured thorough baseline workflow recorded on 2026-04-06.
- Phase 06 is Nyquist-compliant after this audit: every mapped task now has deterministic automated coverage or proof, the final clippy gate is represented in validation sampling, and the stale pending statuses are cleared.
