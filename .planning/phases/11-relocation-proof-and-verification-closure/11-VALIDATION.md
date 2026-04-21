---
phase: 11
slug: relocation-proof-and-verification-closure
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
last_audited: 2026-04-14
---

# Phase 11 — Validation Strategy

> Audited against executed Phase 11 plans, summaries, and current green validation artifacts for `MOVE-01` / `MOVE-02`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` driving `unittest.TestCase` planning audits + repo-root Cargo metadata commands |
| **Config file** | none |
| **Quick run command** | `python -m pytest tests/planning/test_phase11_validation.py -q` |
| **Full suite command** | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q && python -m pytest tests/planning/test_phase11_validation.py -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** run the task-specific selector below
- **After every plan wave:** run the full suite command
- **Before `/gsd-verify-work`:** full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | MOVE-01, MOVE-02 | scaffold parse | `python -m py_compile tests/planning/test_phase11_validation.py` | ✅ | ✅ green |
| 11-02-01 | 02 | 2 | MOVE-01, MOVE-02 | relocation audit refresh | `python -m pytest tests/planning/test_phase07_validation.py -q -k "relocation_audit_complete or mapping_matches_workspace_exactly or legacy_residue_inventory_matches_disk"` | ✅ | ✅ green |
| 11-02-02 | 02 | 2 | MOVE-01, MOVE-02 | cargo-root proof | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q` | ✅ | ✅ green |
| 11-03-01 | 03 | 3 | MOVE-01, MOVE-02 | verification-report contract | `python -m pytest tests/planning/test_phase11_validation.py -q` | ✅ | ✅ green |
| 11-03-02 | 03 | 3 | MOVE-01, MOVE-02 | final closure proof | `cargo locate-project --workspace --message-format plain && cargo metadata --format-version 1 --no-deps && python -m pytest tests/planning/test_phase07_validation.py -q && python -m pytest tests/planning/test_phase11_validation.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase11_validation.py` exists and is reserved as the Phase 11 closure audit surface.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verification
- [x] Sampling continuity is preserved across all plans
- [x] Wave 0 covers the phase-local audit scaffold
- [x] No watch-mode or interactive verification required
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-14

---

## Validation Audit 2026-04-14

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Notes:
Existing automated coverage was already complete. This audit updated the stored per-task verification map from pending to green, aligned Plan `11-02` with the exact `<automated>` commands from the executed plans, and re-ran the Phase 11 quick/full validation commands successfully.
