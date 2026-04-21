---
phase: 9
slug: clean-validation-and-ci-refresh
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` executed via `pytest 9.0.3`, plus existing PowerShell contract suites and the Phase 9 clean-proof harness |
| **Config file** | none — repo uses direct `python -m pytest` and PowerShell wrapper invocations |
| **Quick run command** | `python -m pytest tests/planning/test_phase09_validation.py -q` |
| **Full suite command** | `python -m pytest tests/planning/test_phase09_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests -q && python -m pytest tools/node_api_parity/tests -q && python -m pytest tools/cxx_api_parity/tests -q` |
| **Estimated runtime** | ~30 seconds for the standard suite; live clean proof tracked separately |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase09_validation.py -q`
- **After every plan wave:** Run `python -m pytest tests/planning/test_phase09_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests -q && python -m pytest tools/node_api_parity/tests -q && python -m pytest tools/cxx_api_parity/tests -q`
- **Before `/gsd-verify-work`:** Full suite and `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1` must be green
- **Max feedback latency:** 30 seconds for the standard suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | INTG-04 | planning audit scaffold | `python -m pytest tests/planning/test_phase09_validation.py -q -k "workflow_and_package_surface or clean_state_and_residue"` | ✅ | ✅ green |
| 09-01-02 | 01 | 1 | INTG-04 | clean harness | `python -m pytest tests/planning/test_phase09_validation.py -q -k "clean_state_and_residue"` | ✅ | ✅ green |
| 09-02-01 | 02 | 2 | INTG-03 | workflow audit | `python -m pytest tests/planning/test_phase09_validation.py -q -k "rust_cpp_benchmark_workflows"` | ✅ | ✅ green |
| 09-02-02 | 02 | 2 | INTG-03 | workflow smoke | `python -m pytest tests/planning/test_phase09_validation.py -q -k "rust_cpp_benchmark_workflows or gui_package_surface"` | ✅ | ✅ green |
| 09-03-01 | 03 | 2 | INTG-03 | workflow audit | `python -m pytest tests/planning/test_phase09_validation.py -q -k "python_node_workflows"` | ✅ | ✅ green |
| 09-03-02 | 03 | 2 | INTG-03 | parity-path smoke | `python -m pytest tests/planning/test_phase09_validation.py -q -k "python_node_workflows or artifact_scope_rules"` | ✅ | ✅ green |
| 09-04-01 | 04 | 3 | INTG-03, INTG-04 | artifact refresh proof | `python -m pytest tests/planning/test_phase09_validation.py -q -k "artifact_scope_rules"` | ✅ | ✅ green |
| 09-04-02 | 04 | 3 | INTG-03, INTG-04 | targeted clean + package proof | `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1` | ✅ | ✅ green |

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
- [x] Feedback latency < 30s for the standard suite
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-13

---

## Validation Audit 2026-04-13

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

Notes:
Corrected the stored full-suite command to split the parity pytest suites and avoid the `conftest` import-path collision that occurs when Python, Node, and CXX parity tests share one invocation. The Phase 9 live clean/package proof also reran green after the initial transient `bun run build` failure.
