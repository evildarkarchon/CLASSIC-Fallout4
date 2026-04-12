---
phase: 5
slug: milestone-cleanup
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-11
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 9.0.3 collecting `unittest.TestCase` planning audits |
| **Config file** | none detected for repo-root pytest; Node scripts in `ClassicLib-rs/node-bindings/classic-node/package.json` |
| **Quick run command** | `python -m pytest tests/planning/test_phase05_validation.py -q` |
| **Full suite command** | `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase05_validation.py -q`
- **After every plan wave:** Run `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SC-05-01 | unit/doc audit | `python -m pytest tests/planning/test_phase05_validation.py -q -k documentation_index` | ❌ Wave 0 | ⬜ pending |
| 05-01-02 | 01 | 1 | SC-05-02 | unit/artifact audit | `python -m pytest tests/planning/test_phase05_validation.py -q -k phase3_verification` | ❌ Wave 0 | ⬜ pending |
| 05-01-03 | 01 | 1 | SC-05-03 | unit + touched-surface parity | `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ❌ / ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/planning/test_phase05_validation.py` — audit guard for docs-index routing, refreshed Phase 3 verification bookkeeping, and Node floor reconciliation

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-11
