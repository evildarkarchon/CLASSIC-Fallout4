---
phase: 07
slug: consistency-sweep
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in test harness + crate-local test modules |
| **Config file** | `ClassicLib-rs/Cargo.toml` plus touched crate `Cargo.toml` files |
| **Quick run command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml && cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Estimated runtime** | ~3-5 minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's listed `<automated>` command.
- **After every plan wave:** Run `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml`.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 5 minutes.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | CONS-01 | crate-test | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |
| 07-01-02 | 01 | 1 | CONS-01 | source-doc-audit | `pwsh -Command "if (rg -n 'once_cell' 'ClassicLib-rs/business-logic/classic-scanlog-core' 'ClassicLib-rs/business-logic/classic-scanlog-core/Cargo.toml' 'docs/api/classic-scanlog-core.md') { exit 1 }"` | ✅ | ⬜ pending |
| 07-02-01 | 02 | 2 | CONS-01 | crate-test | `cargo test -p classic-registry-core --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-perf-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |
| 07-02-02 | 02 | 2 | CONS-01 | manifest-doc-audit | `pwsh -Command "if (rg -n 'once_cell' 'ClassicLib-rs/Cargo.toml' 'ClassicLib-rs/business-logic/classic-registry-core' 'ClassicLib-rs/business-logic/classic-perf-core' 'ClassicLib-rs/business-logic/classic-yaml-core/Cargo.toml' 'ClassicLib-rs/business-logic/classic-settings-core/Cargo.toml' 'ClassicLib-rs/business-logic/classic-scangame-core/Cargo.toml' 'docs/api/classic-registry-core.md' 'docs/api/classic-perf-core.md' 'docs/api/classic-settings-core.md') { exit 1 }"` | ✅ | ⬜ pending |
| 07-02-03 | 02 | 2 | CONS-01 | workspace-build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing crate-local tests already cover the touched global/static surfaces. No new validation infrastructure is required before execution.

---

## Manual-Only Verifications

All required phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10 minutes
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
