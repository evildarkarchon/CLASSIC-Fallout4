---
phase: 2
slug: dead-code-removal
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
updated: 2026-04-06
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | cargo test (Rust), pytest (Python bindings) |
| **Config file** | `ClassicLib-rs/Cargo.toml` plus crate-local `tests/` targets |
| **Quick run command** | `cargo test -p classic-scanlog-core --test phase2_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-yaml-core --test phase2_yaml_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml && uv run pytest ClassicLib-rs/python-bindings/tests/test_phase2_dead_code_removal.py -q` |
| **Full suite command** | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && uv run pytest ClassicLib-rs/python-bindings/tests/test_phase2_dead_code_removal.py -q` |
| **Estimated runtime** | ~2-3 minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's listed `<automated>` command.
- **After every plan wave:** Run the focused audit suite command.
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DEBT-01, DEBT-08 | audit test | `cargo test -p classic-scanlog-core --test phase2_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml` | `ClassicLib-rs/business-logic/classic-scanlog-core/tests/phase2_dead_code_audit.rs` | ✅ green |
| 02-02-01 | 02 | 1 | DEBT-02 | audit test | `cargo test -p classic-yaml-core --test phase2_yaml_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml` | `ClassicLib-rs/business-logic/classic-yaml-core/tests/phase2_yaml_dead_code_audit.rs` | ✅ green |
| 02-02-02 | 02 | 1 | DEBT-03 | audit test | `cargo test -p classic-scanlog-core --test phase2_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml` | `ClassicLib-rs/business-logic/classic-scanlog-core/tests/phase2_dead_code_audit.rs` | ✅ green |
| 02-02-02 | 02 | 1 | DEBT-04 | smoke+audit | `uv run pytest ClassicLib-rs/python-bindings/tests/test_phase2_dead_code_removal.py -q` | `ClassicLib-rs/python-bindings/tests/test_phase2_dead_code_removal.py` | ✅ green |
| 02-03-01 | 03 | 2 | TEST-02 | invariant test + audit | `cargo test -p classic-scanlog-core --test phase2_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml` | `ClassicLib-rs/business-logic/classic-scanlog-core/tests/phase2_dead_code_audit.rs` | ✅ green |
| 02-03-02 | 03 | 2 | DEBT-09 | audit test | `cargo test -p classic-scanlog-core --test phase2_dead_code_audit --manifest-path ClassicLib-rs/Cargo.toml` | `ClassicLib-rs/business-logic/classic-scanlog-core/tests/phase2_dead_code_audit.rs` | ✅ green |

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
- [x] Feedback latency < 5 minutes
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** audited 2026-04-06

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 4 |
| Resolved | 4 |
| Escalated | 0 |

- Added `ClassicLib-rs/business-logic/classic-scanlog-core/tests/phase2_dead_code_audit.rs` to lock the removed parser/version/plugin/settings symbols behind executable source audits.
- Added `ClassicLib-rs/business-logic/classic-yaml-core/tests/phase2_yaml_dead_code_audit.rs` to keep `YamlFormatConfig`, `with_config`, and `format_config` out of source, tests, and benches.
- Added `ClassicLib-rs/python-bindings/tests/test_phase2_dead_code_removal.py` to keep the stateless `GpuDetector` binding contract covered by a focused Python smoke test.
