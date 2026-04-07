---
phase: 3
slug: fcx-state-hardening
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
audited: 2026-04-06
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` + Bun test + Node `node:test` |
| **Config file** | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json` |
| **Quick run command** | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- fcx_reset` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings && bun run parity:gate:local && bun run test:bun && bun run test:node` |
| **Estimated runtime** | ~120 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's targeted command.
- **After every plan wave:** Run the full suite command for the touched surfaces.
- **Before `/gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 120 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SAFE-01, CONS-02, TEST-01 | unit | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- fcx_reset` | ✅ | ✅ green |
| 03-01-02 | 01 | 1 | SAFE-01, CONS-02 | docs + lint | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- fcx_reset && cargo clippy -p classic-scanlog-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | SAFE-02 | unit | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | SAFE-02 | build + docs | `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner && cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml` | ✅ | ✅ green |
| 03-03-01 | 03 | 2 | SAFE-03, SAFE-04 | unit | `bun test __test__/scanlog.spec.ts` | ✅ | ✅ green |
| 03-03-02 | 03 | 2 | SAFE-03, TEST-04 | integration | `bun test __test__/scanlog.spec.ts` | ✅ | ✅ green |
| 03-03-03 | 03 | 2 | SAFE-04, TEST-04 | parity + runtime | `bun run parity:gate:local && bun run test:bun && bun run test:node` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all MISSING references.
- [x] No watch-mode flags.
- [x] Feedback latency < 120s for targeted loops.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** automated audit complete

## Validation Audit 2026-04-06
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Audit Evidence

- Re-ran `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- fcx_reset` and `cargo clippy -p classic-scanlog-core --all-targets --manifest-path ClassicLib-rs/Cargo.toml -- -D warnings`.
- Re-ran `cargo test -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml scanner` and `cargo build -p classic-cpp-bridge --manifest-path ClassicLib-rs/Cargo.toml`.
- Re-ran `bun test __test__/scanlog.spec.ts`, `bun run parity:gate:local`, `bun run test:bun`, and `bun run test:node`.
