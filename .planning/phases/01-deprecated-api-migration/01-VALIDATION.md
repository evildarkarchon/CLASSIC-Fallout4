---
phase: 1
slug: deprecated-api-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test (Rust), pytest (Python), bun test / node --test (Node) |
| **Config file** | ClassicLib-rs/Cargo.toml (workspace), ClassicLib-rs/python-bindings/tests/ |
| **Quick run command** | `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-scanlog-core` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && uv run pytest ClassicLib-rs/python-bindings/tests -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-scanlog-core`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | DEBT-07 | unit | `cargo test --manifest-path ClassicLib-rs/Cargo.toml -p classic-scanlog-core -- check_version_status` | TBD | pending |
| TBD | 01 | 1 | DEBT-05 | unit+parity | `uv run pytest ClassicLib-rs/python-bindings/tests -q -k parse` | TBD | pending |
| TBD | 01 | 1 | DEBT-06 | unit+parity | `uv run pytest ClassicLib-rs/python-bindings/tests -q -k suspect` | TBD | pending |
| TBD | 01 | 1 | DEBT-10 | unit+parity | `uv run pytest ClassicLib-rs/python-bindings/tests -q -k formid` | TBD | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
