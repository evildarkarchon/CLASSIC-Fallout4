---
phase: 8
slug: wrapper-and-parity-rewire
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 8 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` driving `unittest` planning audit, PowerShell contract tests, and subprocess smoke checks for Cargo, Bun, parity gates, and wrapper/native entrypoints |
| **Config file** | none - phase audit in `tests/planning/test_phase08_validation.py` plus direct suites under `tests/powershell/` and `tools/*_api_parity/tests/` |
| **Quick run command** | `python -m pytest tests/planning/test_phase08_validation.py -q` |
| **Full suite command** | `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py tests/planning/test_phase08_validation.py -q` |
| **Estimated runtime** | ~210 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/planning/test_phase08_validation.py -q`
- **After every plan wave:** Run `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py tests/planning/test_phase08_validation.py -q`
- **Before `/gsd-verify-work`:** `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1 && python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py tests/planning/test_phase08_validation.py -q` must be green
- **Max feedback latency:** 210 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | INTG-01 | PowerShell contract | `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1 && pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | INTG-01 | smoke | `python -m pytest tests/planning/test_phase08_validation.py -q -k live_repo_root_rebuild_wrappers_smoke` | ✅ | ✅ green |
| 08-02-01 | 02 | 1 | INTG-01 | PowerShell contract | `pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1` | ✅ | ✅ green |
| 08-02-02 | 02 | 1 | INTG-01 | smoke | `python -m pytest tests/planning/test_phase08_validation.py -q -k "live_repo_root_tui_entrypoint_smoke or live_native_wrapper_test_flows_smoke"` | ✅ | ✅ green |
| 08-03-01 | 03 | 1 | INTG-02 | pytest regression | `python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py -q` | ✅ | ✅ green |
| 08-03-02 | 03 | 1 | INTG-02 | smoke | `python -m pytest tests/planning/test_phase08_validation.py -q -k live_python_parity_and_stub_flows_smoke` | ✅ | ✅ green |
| 08-04-01 | 04 | 1 | INTG-02 | pytest regression | `python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py -q` | ✅ | ✅ green |
| 08-04-02 | 04 | 1 | INTG-02 | smoke | `python -m pytest tests/planning/test_phase08_validation.py -q -k live_node_package_scripts_smoke` | ✅ | ✅ green |
| 08-05-01 | 05 | 1 | INTG-02 | pytest regression | `python -m pytest tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q` | ✅ | ✅ green |
| 08-05-02 | 05 | 1 | INTG-02 | gate integration | `python -m pytest tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q && python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | ✅ | ✅ green |
| 08-06-01 | 06 | 2 | INTG-01, INTG-02 | phase audit | `python -m pytest tests/planning/test_phase08_validation.py -q` | ✅ | ✅ green |
| 08-06-02 | 06 | 2 | INTG-02 | invariant audit | `python -m pytest tests/planning/test_phase08_validation.py -q -k "python_checked_in_artifacts_lock_semantics_and_repo_root_metadata or node_checked_in_artifacts_lock_semantics_and_repo_root_metadata"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/planning/test_phase08_validation.py` - phase-local smoke and invariant audit for wrapper, native, parity, and artifact-refresh coverage
- [x] Existing PowerShell and parity pytest suites were sufficient; no framework install or new harness was required

---

## Manual-Only Verifications

None. Phase 8 now has automated verification for wrapper/native entrypoints, parity gates, artifact no-drift invariants, and the previously heavyweight rebuild/package flows.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all Phase 8-local MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 210s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 5 |
| Resolved | 5 |
| Escalated | 0 |

### Audit Updates

| Gap | Action | Outcome |
|-----|--------|---------|
| Real repo-root TUI entrypoint only had structural assertions | Added subprocess smoke for `cargo run -p classic-tui -- --version` and native `build_cli.ps1 -Test` / `build_gui.ps1 -Test` flows to `tests/planning/test_phase08_validation.py` | ✅ green |
| Python happy-path parity and stub validation were not committed as executable proof | Added phase-local subprocess smoke for `check_parity_gate.py --repo-root .` and valid `validate_stubs.py --rust-dir .` | ✅ green |
| Node package-local validation only checked script text and defaults | Added phase-local subprocess smoke for `bun run parity:gate`, `bun run dts:freshness:check`, and `bun run build` | ✅ green |
| Repo-root rebuild wrapper success was not exercised by committed validation | Added phase-local subprocess smoke for `rebuild_rust.ps1` Python/Node flows and both `rebuild_node.ps1` entrypoints | ✅ green |
| Checked-in Python/Node parity artifacts only proved path rewrite, not semantic stability | Added exact contract/runtime metadata invariants for Python and Node checked-in baselines | ✅ green |

### Commands Run

| Command | Result |
|---------|--------|
| `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_rust.general_target.test.ps1` | ✅ pass |
| `pwsh -ExecutionPolicy Bypass -File tests/powershell/rebuild_node.wrapper_contract.test.ps1` | ✅ pass |
| `pwsh -ExecutionPolicy Bypass -File tests/powershell/cpp_build_scripts.test.ps1` | ✅ pass |
| `python -m pytest tools/python_api_parity/tests/test_check_parity_gate.py tools/python_api_parity/tests/test_generate_baseline_targets.py -q` | ✅ 15 passed |
| `python -m pytest tools/node_api_parity/tests/test_check_parity_gate.py tools/node_api_parity/tests/test_generate_baseline_targets.py -q` | ✅ 14 passed |
| `python -m pytest tools/cxx_api_parity/tests/test_parser.py tools/cxx_api_parity/tests/test_gate.py -q` | ✅ 24 passed |
| `python -m pytest tests/planning/test_phase08_validation.py -q` | ✅ 11 passed in 185.45s |
