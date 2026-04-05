---
phase: 2
slug: dead-code-removal
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test (Rust), pytest (Python bindings) |
| **Config file** | ClassicLib-rs/Cargo.toml (workspace) |
| **Quick run command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -q` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && uv run pytest ClassicLib-rs/python-bindings/tests -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DEBT-01 | build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |
| 02-01-02 | 01 | 1 | DEBT-02 | build+test | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |
| 02-01-03 | 01 | 1 | DEBT-03 | build | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |
| 02-01-04 | 01 | 1 | DEBT-04 | build+parity | `cargo build --workspace && python tools/python_api_parity/check_parity_gate.py --repo-root .` | N/A | ⬜ pending |
| 02-02-01 | 02 | 2 | DEBT-08 | build+test | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |
| 02-03-01 | 03 | 3 | TEST-02 | test | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |
| 02-03-02 | 03 | 3 | DEBT-09 | build+test | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
