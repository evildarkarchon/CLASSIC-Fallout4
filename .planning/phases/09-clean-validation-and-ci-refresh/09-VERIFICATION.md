---
phase: 09-clean-validation-and-ci-refresh
verified: 2026-04-15T00:00:00Z
status: passed
score: 6/6 must-haves verified
---

# Phase 9: Clean Validation and CI Refresh Verification Report

**Phase Goal:** Clean-state verification and CI prove the repo-root workspace works without stale caches, stale outputs, or legacy `ClassicLib-rs` artifacts.
**Verified:** 2026-04-15T00:00:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Contributors can inspect current PR CI workflows and see repo-root Rust, Python, TypeScript, C++, and benchmark contracts wired to relocated paths. | ✓ VERIFIED | `09-VALIDATION.md` maps `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, and `.github/workflows/benchmarks.yml` to green task-level checks `09-02-01`, `09-02-02`, `09-03-01`, and `09-03-02`; `tests/planning/test_phase09_validation.py` locks the same workflow paths, repo-root hash inputs, root cache paths, working directories, and parity-artifact diagnostics. |
| 2 | Contributors can run the required GUI package-sensitive proof surface from the repo root and keep its package outputs tied to the relocated workspace. | ✓ VERIFIED | `09-CLEAN-VALIDATION-AUDIT.md` names `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Package` as the required package proof per D-06/D-07 and records `classic-gui/build/packages/CLASSIC-1.0.0-win64.zip` plus `classic-gui/install/CLASSIC.exe` as the live outputs; `tests/planning/test_phase09_validation.py` and `tests/planning/phase09_clean_run.ps1` both pin `classic-gui/build_gui.ps1 -Package` in the committed replay flow. |
| 3 | Contributors can rerun a deliberate fresh-state proof that recreates `python-bindings/.venv`, replays the repo-root Python wrapper, regenerates only Phase 9-owned path-bearing artifacts, and leaves no new generated residue under `ClassicLib-rs/`. | ✓ VERIFIED | `09-CLEAN-VALIDATION-AUDIT.md` documents the targeted-clean inventory from D-01 through D-03 and the legacy residue rule from D-10/D-11; `tests/planning/phase09_clean_run.ps1` deletes `target`, `python-bindings/.venv`, Node outputs, and parity-artifact working dirs, then reruns `uv venv python-bindings/.venv`, `uv pip install --python python-bindings/.venv/Scripts/python.exe -r python-bindings/requirements-ci.txt`, `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -BuildOnly`, parity gates, and the GUI package proof before comparing `$PreProofLegacyState` and `$PostProofLegacyState`; `tests/planning/test_phase09_validation.py` asserts the same ordered replay contract. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/planning/test_phase09_validation.py` | Canonical Phase 9 workflow/package/clean-state audit | ✓ VERIFIED | Exists, is substantive, and checks workflow contracts, artifact scope, clean replay order, `.venv` bootstrap, GUI package proof, and legacy residue rules. |
| `tests/planning/phase09_clean_run.ps1` | End-to-end fresh-state replay harness | ✓ VERIFIED | Exists and quarantines legacy `ClassicLib-rs/target`, clears high-risk generated outputs, recreates `python-bindings/.venv`, runs wrapper/parity/package proof commands, and rejects new legacy residue. |
| `.planning/phases/09-clean-validation-and-ci-refresh/09-CLEAN-VALIDATION-AUDIT.md` | Canonical clean-state, artifact-scope, and package-proof contract | ✓ VERIFIED | Exists and records the targeted clean inventory, workflow contract matrix, scoped artifact refresh rules, live artifact outcomes, command order, and residue policy. |
| `.planning/phases/09-clean-validation-and-ci-refresh/09-VALIDATION.md` | Approved Phase 9 validation contract | ✓ VERIFIED | Exists and maps every Phase 9 task to executable checks, including the clean-proof harness and workflow audit selectors. |
| `.planning/phases/09-clean-validation-and-ci-refresh/09-01-SUMMARY.md` through `09-04-SUMMARY.md` | Per-plan summaries with machine-checkable requirement metadata | ✓ VERIFIED | All four summaries now expose `phase`, `plan`, and `requirements-completed` frontmatter so `INTG-03` and `INTG-04` are not summary-only claims. |
| `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, `.github/workflows/benchmarks.yml` | Active CI closure surface uses repo-root contracts only | ✓ VERIFIED | The workflow files are the direct evidence surface for D-04/D-05 and are asserted by the planning audit and validation tests. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `09-VERIFICATION.md` | `09-VALIDATION.md` | direct command-backed evidence | ✓ WIRED | This report cites the approved validation matrix rather than summary-only prose. |
| `09-VERIFICATION.md` | `tests/planning/test_phase09_validation.py` | executable workflow/package/clean-state audit | ✓ WIRED | The verifier points at the committed test that locks workflow paths, artifact ownership, and ordered clean replay commands. |
| `09-VERIFICATION.md` | `tests/planning/phase09_clean_run.ps1` | command-backed clean-state replay and residue proof | ✓ WIRED | The harness is the canonical direct proof for `.venv` recreation, wrapper replay, GUI packaging, and no-new-residue guarantees. |
| `09-VERIFICATION.md` | `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, `.github/workflows/benchmarks.yml` | active CI workflow coverage | ✓ WIRED | Phase 9 closure cites live workflow files directly for INTG-03 instead of relying on historical summaries. |
| `09-VERIFICATION.md` | `classic-gui/build_gui.ps1` | package-sensitive GUI proof surface | ✓ WIRED | The package flow remains the required native proof and is recorded in both the audit contract and replay harness. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| N/A | N/A | Planning/docs/tests only | N/A | SKIPPED - Phase 9 closure artifacts are verification surfaces, not runtime data renderers. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase 9 planning audit passes | `python -m pytest tests/planning/test_phase09_validation.py -q` | Current replay proof passes and remains the canonical workflow/package/clean-state audit. | ✓ PASS |
| Deliberate clean-state replay recreates `.venv`, reruns wrapper/parity/package proof, and leaves no new legacy residue | `pwsh -ExecutionPolicy Bypass -File tests/planning/phase09_clean_run.ps1` | Current harness runs the ordered proof flow from repo root and enforces the post-proof residue comparison. | ✓ PASS |
| Rust, C++, benchmark, Python, and TypeScript workflow contracts stay repo-root-only | `python -m pytest tests/planning/test_phase09_validation.py -q -k "rust_cpp_benchmark_workflows or python_node_workflows"` | Workflow assertions confirm repo-root hash inputs, caches, working directories, and diagnostics paths with no `ClassicLib-rs` runtime workflow regression. | ✓ PASS |
| GUI package surface stays part of closure | `python -m pytest tests/planning/test_phase09_validation.py -q -k "gui_package_surface"` | The test requires `classic-gui/build_gui.ps1 -Package` in both the audit and clean-run harness. | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| INTG-03 | `09-02`, `09-03`, `09-04` | Contributor can run CI and path-sensitive build or packaging jobs against the relocated workspace using the new repository-root layout | ✓ SATISFIED | `09-VALIDATION.md` records green proof for the active CI workflows and GUI package surface; `tests/planning/test_phase09_validation.py` directly checks `.github/workflows/ci-rust.yml`, `.github/workflows/ci-python-bindings.yml`, `.github/workflows/ci-typescript.yml`, `.github/workflows/ci-cpp.yml`, `.github/workflows/benchmarks.yml`, and `classic-gui/build_gui.ps1 -Package`; `09-CLEAN-VALIDATION-AUDIT.md` records the package outputs and repo-root path contracts. |
| INTG-04 | `09-01`, `09-04` | Contributor can verify the relocation from a clean state with regenerated path-bearing artifacts instead of relying on stale caches or outputs | ✓ SATISFIED | `09-CLEAN-VALIDATION-AUDIT.md` records the targeted clean inventory, scoped artifact refreshes, `.venv` recreation, wrapper replay, and no-new-residue outcome; `tests/planning/phase09_clean_run.ps1` performs the clean replay directly; `tests/planning/test_phase09_validation.py` asserts the ordered commands and residue comparison that make the proof replayable. |

Orphaned requirements: none. Phase 9 summaries now expose `requirements-completed` metadata, and this verifier provides direct evidence rows for `INTG-03` and `INTG-04`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No blocker stubs, placeholder verification text, or summary-only requirement claims were needed for Phase 9 closure. | - | No impact |

### Human Verification Required

None. Phase 9 closure is command-backed and replayable through the committed validation surfaces.

### Gaps Summary

No Phase 9 gaps remain within the phase boundary. CI workflows, GUI packaging, targeted clean replay, and residue protection now have direct verification evidence, and requirement traceability no longer depends on summary-only prose.

---

_Verified: 2026-04-15T00:00:00Z_
_Verifier: the agent_
