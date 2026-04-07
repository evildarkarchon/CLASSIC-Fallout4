---
phase: 1
slug: cxx-parity-gate-tooling
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (existing, installed in `ClassicLib-rs/python-bindings/.venv` from `requirements-ci.txt`) |
| **Config file** | none — Wave 0 creates `tools/cxx_api_parity/tests/`. The repo has no `pyproject.toml`; the python-bindings venv is hand-managed |
| **Venv location** | `ClassicLib-rs/python-bindings/.venv` (Windows: `Scripts/pytest`). **No venv lives at the repo root** — repo root must stay venv-free |
| **Quick run command** | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -q` |
| **Full suite command** | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -v` |
| **Estimated runtime** | ~10 seconds (pure Python parsing, fixture-based, no network or build) |

---

## Sampling Rate

- **After every task commit:** Run `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -q`
- **After every plan wave:** Run `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green AND `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` must exit 0
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Filled by gsd-planner against the actual task IDs it generates. Initial mapping below tracks the requirement → test relationship surfaced by RESEARCH.md §Validation Architecture (lines 779-799).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | CXXG-01 | scaffolding | `test -d tools/cxx_api_parity/tests/fixtures` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseExternRust::test_parse_extern_rust_functions -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseSharedStructs::test_parse_shared_structs -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseEnums::test_parse_enums -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseOpaqueTypes::test_parse_opaque_types -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseExternCpp::test_parse_extern_cpp -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseBuildRs::test_parse_build_rs -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestParseBuildRs::test_build_rs_missing_bridges -x` | ✅ created | ⬜ pending |
| 01-01-T2 | 01 | 1 | CXXG-01 | unit | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_parser.py::TestDeterminism::test_deterministic_output -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-02 | integration | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestBaselineExists::test_baseline_file_exists -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-02 | integration | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestBaselineExists::test_baseline_covers_14_modules -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-03 | smoke | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestGateSmoke::test_gate_passes_on_unchanged_source -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-03 | drift | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestDriftDetection::test_gate_fails_on_added_function -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-03 | drift | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestDriftDetection::test_gate_fails_on_removed_function -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-03 | drift | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestDriftDetection::test_gate_fails_on_struct_field_rename -x` | ✅ created | ⬜ pending |
| 01-02-T2 | 02 | 2 | CXXG-03 | stale-artifact | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestStaleArtifact::test_gate_fails_on_stale_artifact -x` | ✅ created | ⬜ pending |
| 01-02-T1 | 02 | 2 | CXXG-04 | CLI surface | `ClassicLib-rs/python-bindings/.venv/Scripts/pytest tools/cxx_api_parity/tests/test_gate.py::TestNoDeferredRegistry::test_no_deferred_registry_arg -x` | ✅ created | ⬜ pending |
| 01-02-T1 | 02 | 2 | CXXG-04 | smoke | `python tools/cxx_api_parity/check_parity_gate.py --help` exits 0 | ✅ created | ⬜ pending |
| 01-03-T1 | 03 | 3 | CXXG-02 | end-to-end | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 against committed baseline | ✅ created | ⬜ pending |
| 01-03-T1 | 03 | 3 | CXXG-05 | doc presence | `test -f docs/api/cxx-parity-gate.md && grep -q '## Local Run' docs/api/cxx-parity-gate.md` | ✅ created | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> The planner is responsible for assigning concrete `Task ID` and `Plan` numbers when it generates `*-PLAN.md` files. The Wave column reflects the dependency order from RESEARCH.md (Wave 0 = test scaffolding, Wave 1 = parser unit tests, Wave 2 = gate integration tests, Wave 3 = end-to-end + docs).

---

## Wave 0 Requirements

Test infrastructure must be created before any parser/gate code is written:

- [ ] `tools/cxx_api_parity/tests/__init__.py` — makes tests directory a Python package
- [ ] `tools/cxx_api_parity/tests/conftest.py` — shared fixtures (repo_root, fixture_dir)
- [ ] `tools/cxx_api_parity/tests/test_parser.py` — covers CXXG-01 parser unit tests (8+ tests)
- [ ] `tools/cxx_api_parity/tests/test_gate.py` — covers CXXG-02, CXXG-03, CXXG-04 (10+ tests)
- [ ] `tools/cxx_api_parity/tests/fixtures/simple_ffi.rs` — minimal `extern "Rust"` fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/struct_ffi.rs` — shared struct fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/enum_ffi.rs` — enum with `#[derive]` and explicit variant discriminants
- [ ] `tools/cxx_api_parity/tests/fixtures/opaque_ffi.rs` — opaque type fixture
- [ ] `tools/cxx_api_parity/tests/fixtures/mixed_ffi.rs` — scanner-like complex fixture (`unsafe extern "C++"`, `include!()`, multi-arg fns)
- [ ] `tools/cxx_api_parity/tests/fixtures/fake_build.rs` — fake `build.rs` for parser unit tests

> Existing infrastructure: `ClassicLib-rs/python-bindings/.venv` (hand-managed via `ClassicLib-rs/python-bindings/requirements-ci.txt`) ships pytest 9.x. No `pyproject.toml` or `.python-version` exists at the repo root; the gate tests run via the explicit venv-bin path. **Do not** add a venv at the repo root.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Contributor doc clarity | CXXG-05 | Doc readability is subjective; automated doc-presence check is in the table above, but a human must read once | Read `docs/api/cxx-parity-gate.md` end-to-end and confirm a contributor not familiar with the gate could (a) run it locally, (b) refresh the baseline after an intentional change, (c) understand what each contract row field means |

> All other phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING test files and fixtures
- [ ] No watch-mode flags in commands
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner fills Task IDs and Wave 0 is verified)

**Approval:** task IDs filled 2026-04-07 by gsd-planner; gsd-plan-checker verifies before VERIFICATION PASSED
