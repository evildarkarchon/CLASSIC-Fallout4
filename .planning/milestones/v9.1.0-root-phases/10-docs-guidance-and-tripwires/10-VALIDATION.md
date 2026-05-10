---
phase: 10
slug: docs-guidance-and-tripwires
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
---

# Phase 10 — Validation Strategy

> Reconstructed from executed plans, summaries, and current green validation artifacts.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` driving `unittest.TestCase` planning audits + standalone PowerShell 7 tripwire |
| **Config file** | none — `pytest` auto-discovers `tests/planning/test_phase10_validation.py`; PowerShell tripwire is file-backed and standalone |
| **Quick run command** | `python -m pytest tests/planning/test_phase10_validation.py -q` |
| **Full suite command** | `python -m pytest tests/planning/test_phase10_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/phase10_guidance_tripwires.test.ps1` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-specific selector from the map below; fallback to `python -m pytest tests/planning/test_phase10_validation.py -q`
- **After every plan wave:** Run `python -m pytest tests/planning/test_phase10_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/phase10_guidance_tripwires.test.ps1`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-00-01 | 00 | 1 | DOCS-03 | static parse | `python -m py_compile tests/planning/test_phase10_validation.py` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-00-02 | 00 | 1 | DOCS-03 | script parse | `pwsh -NoProfile -Command "$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile('tests/powershell/phase10_guidance_tripwires.test.ps1',[ref]$tokens,[ref]$errors) > $null; if ($errors.Count -gt 0) { exit 1 }"` | ✅ `tests/powershell/phase10_guidance_tripwires.test.ps1` | ✅ green |
| 10-01-01 | 01 | 1 | DOCS-01, DOCS-02 | doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "matrix_and_top_level_docs_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-01-02 | 01 | 1 | DOCS-01, DOCS-02 | doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "matrix_and_top_level_docs_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-02-01 | 02 | 2 | DOCS-01, DOCS-02 | api hub contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_hubs_and_binding_workflow_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-02-02 | 02 | 2 | DOCS-01, DOCS-02 | api hub contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_hubs_and_binding_workflow_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-03-01 | 03 | 2 | DOCS-01 | api reference | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_core_group_a_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-04-01 | 04 | 2 | DOCS-01 | api reference | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_core_group_b_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-04-02 | 04 | 2 | DOCS-01 | api reference | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_core_group_b_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-05-01 | 05 | 2 | DOCS-01 | workflow doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_runtime_group_c_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-05-02 | 05 | 2 | DOCS-01 | workflow doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_runtime_group_c_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-06-01 | 06 | 2 | DOCS-01 | workflow doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_runtime_group_d_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-06-02 | 06 | 2 | DOCS-01 | workflow doc contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "api_runtime_group_d_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-07-01 | 07 | 2 | DOCS-01, DOCS-02 | agent guidance contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "agent_entrypoints_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-07-02 | 07 | 2 | DOCS-01, DOCS-02 | agent guidance contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "agent_entrypoints_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-08-01 | 08 | 3 | DOCS-01, DOCS-02 | repo-guide contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "repo_guide_mirrors_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-08-02 | 08 | 3 | DOCS-01, DOCS-02 | repo-guide contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "repo_guide_mirrors_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-09-01 | 09 | 2 | DOCS-01, DOCS-03 | codebase-map contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "codebase_maps_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |
| 10-09-02 | 09 | 2 | DOCS-01, DOCS-03 | codebase-map contract | `python -m pytest tests/planning/test_phase10_validation.py -q -k "codebase_maps_contract"` | ✅ `tests/planning/test_phase10_validation.py` | ✅ green |

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
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-14
