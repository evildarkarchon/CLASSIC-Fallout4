---
phase: 2
slug: crashgen-config-merge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test (workspace) + parity gates (Python/Node/CXX) |
| **Config file** | ClassicLib-rs/Cargo.toml |
| **Quick run command** | `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` |
| **Estimated runtime** | ~180 seconds (build) + ~300 seconds (test) |

---

## Sampling Rate

- **After every task commit:** Run `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **After every plan wave:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml`
- **Before `/gsd:verify-work`:** Full suite must be green + all 3 parity gates (CXX, Python, Node) exit 0 with zero drift
- **Max feedback latency:** 180 seconds (quick build)

---

## Per-Task Verification Map

*Populated by planner — see 02-01-PLAN.md and 02-02-PLAN.md task acceptance criteria.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | CGEN-01/02/03 | build+test | `cargo build/test --workspace` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Phase 2 is a strict structural refactor with zero new behavior — the 4 inline unit tests inside the moved `crashgen_rules.rs` carry forward via `git mv` and continue to run under `cargo test --workspace`. No new test files, no new fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | All behavior preserved by cargo + parity gates | — |

*All phase behaviors have automated verification via cargo build/test and the three parity gates.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (N/A — none needed)
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s (quick build)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
