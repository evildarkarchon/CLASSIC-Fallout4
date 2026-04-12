---
phase: 6
slug: repo-root-workspace-cutover
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` under `pytest` + PowerShell clean-run proof |
| **Config file** | none - per-phase audit files under `tests/planning/` |
| **Quick run command** | `python -m pytest tests/planning/test_phase06_validation.py -q` |
| **Full suite command** | `pwsh -File tests/planning/phase06_clean_run.ps1` |
| **Estimated runtime** | ~180 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase06_validation.py -q`
- **After every plan wave:** Run `pwsh -File tests/planning/phase06_clean_run.ps1`
- **Before `/gsd-verify-work`:** `pwsh -File tests/planning/phase06_clean_run.ps1` must be green
- **Max feedback latency:** 180 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-00-01 | 00 | 0 | ROOT-01, ROOT-02 | unit/bootstrap audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "validation_bootstrap or clean_target_guard"` | ✅ / ✅ | ✅ green |
| 06-01-01 | 01 | 1 | ROOT-01 | unit/file audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "workspace_root_manifest or core_root_files"` | ✅ Wave 0 | ✅ green |
| 06-01-02 | 01 | 1 | ROOT-02 | unit/workflow audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "stub_validator or rebuild_script or cargo_aliases"` | ✅ Wave 0 | ✅ green |
| 06-02-01 | 02 | 2 | ROOT-01, ROOT-02 | unit/file audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "benchmark_support_set"` | ✅ Wave 0 | ✅ green |
| 06-03-01 | 03 | 3 | ROOT-01, ROOT-02 | unit/workflow audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "repo_root_workflows or benchmark_workflow_paths"` | ✅ Wave 0 | ✅ green |
| 06-03-02 | 03 | 3 | ROOT-01, ROOT-02 | phase-gate integration | `pwsh -File tests/planning/phase06_clean_run.ps1` | ✅ / ✅ Wave 0 | ✅ green |
| 06-03-03 | 03 | 3 | ROOT-01, ROOT-02 | unit/doc audit | `python -m pytest tests/planning/test_phase06_validation.py -q -k "readme_sync or agents_sync"` | ✅ Wave 0 | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase06_validation.py` - planning audit for repo-root workspace detection, old-manifest retirement, and active workflow/doc audits
- [x] `tests/planning/phase06_clean_run.ps1` - clean-state proof helper that renames or bypasses `ClassicLib-rs/target` before repo-root cargo validation

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
