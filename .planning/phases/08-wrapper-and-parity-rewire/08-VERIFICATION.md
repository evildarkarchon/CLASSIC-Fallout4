---
phase: 08-wrapper-and-parity-rewire
verified: 2026-04-14T16:51:05.8317688-07:00
status: passed
score: 6/6 must-haves verified
---

# Phase 8: Wrapper and Parity Rewire Verification Report

**Phase Goal:** Existing Rust-consuming wrappers, native frontends, and parity gates continue to operate against the relocated workspace.
**Verified:** 2026-04-14T16:51:05.8317688-07:00
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Contributors can run the repo-root rebuild wrappers against relocated Python and Node binding paths. | ✓ VERIFIED | `tests/planning/test_phase08_validation.py` includes live smoke for `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -BuildOnly`, `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target node -BuildOnly`, and both `rebuild_node.ps1` entrypoints; `08-VALIDATION.md` records the same wrapper contract under `08-01-01`, `08-01-02`, and `08-06-01`. |
| 2 | Contributors can run the native CLI, GUI, and TUI integration surfaces from the repo root without restoring `ClassicLib-rs/` as the workspace root. | ✓ VERIFIED | `08-VALIDATION.md` maps native proof to `classic-cli/build_cli.ps1 -Test`, `classic-gui/build_gui.ps1 -Test`, and `cargo run -p classic-tui -- --version`; `python -m pytest tests/planning/test_phase08_validation.py -q` passed with native and TUI smoke coverage enabled. |
| 3 | Contributors can run the Python, Node, and CXX parity gates plus Node d.ts freshness checks against repo-root paths with no parity-contract drift caused by the move. | ✓ VERIFIED | `08-VALIDATION.md` records green proof for `python tools/python_api_parity/check_parity_gate.py --repo-root .`, `python validate_stubs.py --rust-dir . ...`, `bun run parity:gate`, `bun run dts:freshness:check`, and `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`; `tests/planning/test_phase08_validation.py` also locks repo-root-only paths and checked-in baseline invariants. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `tests/planning/test_phase08_validation.py` | Canonical Phase 8 wrapper/native/parity audit | ✓ VERIFIED | Exists, is substantive, and includes live smoke plus checked-in artifact invariants for wrapper, native, Python, Node, and CXX flows. |
| `.planning/phases/08-wrapper-and-parity-rewire/08-VALIDATION.md` | Approved Phase 8 validation contract | ✓ VERIFIED | Exists and records green task-level commands for all Phase 8 proof surfaces. |
| `.planning/phases/08-wrapper-and-parity-rewire/08-01-SUMMARY.md` through `08-06-SUMMARY.md` | Per-plan summaries with machine-checkable requirement metadata | ✓ VERIFIED | All six summaries now expose `phase`, `plan`, and `requirements-completed` frontmatter for `INTG-01` and `INTG-02` traceability. |
| `rebuild_rust.ps1` and `rebuild_node.ps1` | Repo-root wrapper entrypoints stay canonical | ✓ VERIFIED | Phase 8 audit locks repo-root binding paths, alias delegation, and live wrapper replay. |
| `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1`, and `ui-applications/classic-tui` | Native proof surfaces remain repo-root based | ✓ VERIFIED | Phase 8 audit proves CLI/GUI `-Test` flows and a lightweight TUI repo-root run. |
| `validate_stubs.py`, `tools/python_api_parity/*`, `tools/node_api_parity/*`, `tools/cxx_api_parity/*`, and `node-bindings/classic-node/package.json` | Parity and freshness tooling stay root-only | ✓ VERIFIED | Phase 8 audit proves root-only path defaults, legacy-path rejection, and no checked-in parity drift. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `tests/planning/test_phase08_validation.py` | `rebuild_rust.ps1` | live wrapper smoke and root-only path assertions | ✓ WIRED | The audit both parses wrapper paths and executes the Python and Node rebuild flows from repo root. |
| `tests/planning/test_phase08_validation.py` | `rebuild_node.ps1` | alias delegation proof | ✓ WIRED | The audit checks `rebuild_node.ps1` stays a thin alias and runs both normal and debug entrypoints. |
| `tests/planning/test_phase08_validation.py` | `classic-cli/build_cli.ps1` and `classic-gui/build_gui.ps1` | native `-Test` smoke | ✓ WIRED | The audit runs both native wrapper test flows instead of raw `ctest` or direct binaries. |
| `tests/planning/test_phase08_validation.py` | `ui-applications/classic-tui` | `cargo run -p classic-tui -- --version` | ✓ WIRED | The TUI remains a repo-root Cargo proof surface, matching Phase 8 decision D-04/D-15. |
| `08-VERIFICATION.md` | `08-VALIDATION.md` | direct command-backed evidence | ✓ WIRED | This report cites the approved validation contract rather than summary-only prose. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| N/A | N/A | Planning/docs/tests only | N/A | SKIPPED - Phase 8 closure artifacts are verification surfaces, not runtime data renderers. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Repo-root wrapper and parity audit passes | `python -m pytest tests/planning/test_phase08_validation.py -q` | `11 passed in 185.45s` when Phase 8 closed; the audit remains the canonical replay surface. | ✓ PASS |
| Repo-root rebuild wrappers stay usable | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -BuildOnly` and `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target node -BuildOnly` | Wrapper smoke is required by `test_phase08_validation.py` and recorded in `08-VALIDATION.md`. | ✓ PASS |
| Native CLI/GUI flows stay wrapper-owned | `pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test` and `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test` | Both native `-Test` flows passed under the committed Phase 8 audit. | ✓ PASS |
| TUI repo-root entrypoint stays live | `cargo run -p classic-tui -- --version` | `classic-tui 0.1.0` printed under the committed Phase 8 audit. | ✓ PASS |
| Python, Node, and CXX parity gates stay green at repo-root paths | `python tools/python_api_parity/check_parity_gate.py --repo-root .`, `bun run parity:gate`, `bun run dts:freshness:check`, `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | All commands are recorded green in `08-VALIDATION.md` and replayed or smoke-checked by `test_phase08_validation.py`. | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| INTG-01 | `08-01`, `08-02`, `08-06` | Contributor can run the existing Rust-consuming wrapper entrypoints after relocation, including repo rebuild scripts and native CLI/GUI/TUI integration flows | ✓ SATISFIED | `08-VALIDATION.md` records wrapper and native proof for `rebuild_rust.ps1`, `rebuild_node.ps1`, `classic-cli/build_cli.ps1 -Test`, `classic-gui/build_gui.ps1 -Test`, and `cargo run -p classic-tui -- --version`; `tests/planning/test_phase08_validation.py` executes those same repo-root surfaces directly. |
| INTG-02 | `08-03`, `08-04`, `08-05`, `08-06` | Contributor can run the Python, Node, and CXX parity gates against the relocated workspace without path drift or parity-contract changes | ✓ SATISFIED | `08-VALIDATION.md` records green proof for `python tools/python_api_parity/check_parity_gate.py --repo-root .`, `python validate_stubs.py --rust-dir . --parity-contract ...`, `bun run parity:gate`, `bun run dts:freshness:check`, and `python tools/cxx_api_parity/check_parity_gate.py --repo-root .`; `tests/planning/test_phase08_validation.py` also locks root-only paths and checked-in parity artifacts. |

Orphaned requirements: none. Phase 8 summaries now expose `requirements-completed` metadata for every executed plan, and this verifier provides the direct evidence row for both `INTG-01` and `INTG-02`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| None | - | No blocker stubs, placeholder verification text, or summary-only requirement claims were needed for Phase 8 closure. | - | No impact |

### Human Verification Required

None. Phase 8 closure is command-backed and replayable through the committed validation surfaces.

### Gaps Summary

No Phase 8 gaps remain within the phase boundary. Wrapper, native, and parity surfaces have direct verification evidence, and requirement traceability no longer depends on summary-only prose.

---

_Verified: 2026-04-14T16:51:05.8317688-07:00_
_Verifier: the agent_
