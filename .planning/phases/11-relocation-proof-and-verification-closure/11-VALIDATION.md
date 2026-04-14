---
phase: 11
slug: relocation-proof-and-verification-closure
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
---

# Phase 11 — Validation Strategy

> Validation contract for refreshing stale Phase 7 proof and closing `MOVE-01` / `MOVE-02` with current verification evidence.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` driving `unittest.TestCase` planning audits + repo-root Cargo metadata commands |
| **Config file** | none |
| **Quick run command** | `python -m pytest tests/planning/test_phase11_validation.py -q` |
| **Full suite command** | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q && python -m pytest tests/planning/test_phase11_validation.py -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** run the task-specific selector below
- **After every plan wave:** run the full suite command
- **Before `/gsd-verify-work`:** full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | MOVE-01, MOVE-02 | scaffold parse | `python -m py_compile tests/planning/test_phase11_validation.py` | ✅ | ⬜ pending |
| 11-02-01 | 02 | 2 | MOVE-01, MOVE-02 | relocation audit refresh | `python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ | ⬜ pending |
| 11-02-02 | 02 | 2 | MOVE-01, MOVE-02 | cargo metadata spot-check | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps` | ✅ | ⬜ pending |
| 11-03-01 | 03 | 3 | MOVE-01, MOVE-02 | verification-report contract | `python -m pytest tests/planning/test_phase11_validation.py -q` | ✅ | ⬜ pending |
| 11-03-02 | 03 | 3 | MOVE-01, MOVE-02 | final closure proof | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q && python -m pytest tests/planning/test_phase11_validation.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase11_validation.py` exists and is reserved as the Phase 11 closure audit surface.

---

## Manual-Only Verifications

None. Phase 11 is entirely file-backed and command-verifiable.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verification
- [x] Sampling continuity is preserved across all plans
- [x] Wave 0 covers the phase-local audit scaffold
- [x] No watch-mode or interactive verification required
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-14
