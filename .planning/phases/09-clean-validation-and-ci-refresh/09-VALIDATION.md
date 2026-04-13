---
phase: 9
slug: clean-validation-and-ci-refresh
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Python `unittest` executed via `pytest 9.0.3`, plus existing PowerShell contract suites and parity-tool pytest suites |
| **Config file** | none — repo uses direct `python -m pytest` and PowerShell wrapper invocations |
| **Quick run command** | `python -m pytest tests/planning/test_phase09_validation.py -q` |
| **Full suite command** | `python -m pytest tests/planning/test_phase09_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q` |
| **Estimated runtime** | ~240 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase09_validation.py -q`
- **After every plan wave:** Run `python -m pytest tests/planning/test_phase09_validation.py -q && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | INTG-04 | planning audit scaffold | `python -m pytest tests/planning/test_phase09_validation.py -q -k "workflow_and_package_surface or clean_state_and_residue"` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | INTG-04 | clean harness | `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1 -WhatIf` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | INTG-03 | workflow audit | `python -m pytest tests/planning/test_phase09_validation.py -q -k "rust_cpp_benchmark_workflows"` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | INTG-03 | workflow smoke | `python -m pytest tests/planning/test_phase09_validation.py -q -k "gui_package_surface"` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | INTG-03 | workflow audit | `python -m pytest tests/planning/test_phase09_validation.py -q -k "python_node_workflows"` | ❌ W0 | ⬜ pending |
| 09-03-02 | 03 | 2 | INTG-03 | parity-path smoke | `python -m pytest tests/planning/test_phase09_validation.py -q -k "artifact_scope_rules"` | ❌ W0 | ⬜ pending |
| 09-04-01 | 04 | 3 | INTG-03, INTG-04 | artifact refresh proof | `python -m pytest tests/planning/test_phase09_validation.py -q -k "artifact_scope_rules or no_new_legacy_residue"` | ❌ W0 | ⬜ pending |
| 09-04-02 | 04 | 3 | INTG-03, INTG-04 | targeted clean + package proof | `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/planning/test_phase09_validation.py` — phase-local audit for workflow paths, cache keys, artifact uploads, clean-state contract, and GUI package proof surface
- [ ] `tests/planning/phase09_clean_run.ps1` — executable targeted-clean harness stronger than Phase 6
- [ ] Assertions that no active workflow still references `ClassicLib-rs/target`, `ClassicLib-rs/**/*.rs`, or `ClassicLib-rs/.../parity-artifacts`
- [ ] Assertions that required regenerated artifacts stay scoped to touched proof surfaces only
- [ ] Post-proof residue check that fails on newly generated output under `ClassicLib-rs/`

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
