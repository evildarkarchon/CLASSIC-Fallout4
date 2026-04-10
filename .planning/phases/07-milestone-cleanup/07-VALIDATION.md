---
phase: 7
slug: milestone-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-10
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep / file-read verification (no test framework — pure doc/config edits) |
| **Config file** | none |
| **Quick run command** | `grep -c "tier.*2" tools/python_api_parity/generate_baseline.py tools/node_api_parity/generate_baseline.py` |
| **Full suite command** | `python tools/python_api_parity/check_parity_gate.py --repo-root . && python tools/node_api_parity/check_parity_gate.py --repo-root . && python tools/cxx_api_parity/check_parity_gate.py --repo-root .` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run grep verification for the specific success criterion addressed
- **After every plan wave:** Run full triple-gate check to ensure no regressions
- **Before `/gsd:verify-work`:** All 6 success criteria must pass
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | SC-1 | grep | `grep -E "CI-0[1-356].*Complete" .planning/REQUIREMENTS.md` | N/A | pending |
| 07-01-02 | 01 | 1 | SC-2 | grep | `grep "docs/implementation/cxx_api_parity/baseline/parity_contract.json" docs/api/binding-parity-policy.md` | N/A | pending |
| 07-01-03 | 01 | 1 | SC-3 | grep | `grep -c "tier.*2" tools/python_api_parity/generate_baseline.py tools/node_api_parity/generate_baseline.py` returns 0 | N/A | pending |
| 07-01-04 | 01 | 1 | SC-4 | read | Lines 40-44 of `tools/test_triple_gate_failure.py` no longer contain stale governance comment | N/A | pending |
| 07-01-05 | 01 | 1 | SC-5 | grep | `grep "3/3" .planning/ROADMAP.md` and `grep "1/2.*CI-04 deferred" .planning/ROADMAP.md` | N/A | pending |
| 07-01-06 | 01 | 1 | SC-6 | grep | `grep -c "Placeholder" ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs` returns 0 | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework or stubs needed — all verifications are grep/read-based.

---

## Manual-Only Verifications

All phase behaviors have automated verification (grep/read checks against concrete expected values).

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
