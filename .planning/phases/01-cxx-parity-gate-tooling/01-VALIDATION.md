---
phase: 1
slug: cxx-parity-gate-tooling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing, via `uv run pytest`) |
| **Config file** | none — Wave 0 creates `tools/cxx_api_parity/tests/` |
| **Quick run command** | `uv run pytest tools/cxx_api_parity/tests/ -q` |
| **Full suite command** | `uv run pytest tools/cxx_api_parity/tests/ -v` |
| **Estimated runtime** | ~10 seconds (pure Python parsing, fixture-based, no network or build) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tools/cxx_api_parity/tests/ -q`
- **After every plan wave:** Run `uv run pytest tools/cxx_api_parity/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green AND `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` must exit 0
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Filled by gsd-planner against the actual task IDs it generates. Initial mapping below tracks the requirement → test relationship surfaced by RESEARCH.md §Validation Architecture (lines 779-799).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 0 | CXXG-01 | scaffolding | `test -d tools/cxx_api_parity/tests/fixtures` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_extern_rust_functions -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_shared_structs -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_enums -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_opaque_types -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_extern_cpp -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_parse_build_rs -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_build_rs_missing_bridges -x` | ❌ W0 | ⬜ pending |
| TBD | 01 | 1 | CXXG-01 | unit | `uv run pytest tools/cxx_api_parity/tests/test_parser.py::test_deterministic_output -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-02 | integration | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_baseline_file_exists -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-02 | integration | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_baseline_covers_14_modules -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-03 | smoke | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_passes_on_unchanged_source -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-03 | drift | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_added_function -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-03 | drift | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_removed_function -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-03 | drift | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_struct_field_rename -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-03 | stale-artifact | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_gate_fails_on_stale_artifact -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-04 | CLI surface | `uv run pytest tools/cxx_api_parity/tests/test_gate.py::test_no_deferred_registry_arg -x` | ❌ W0 | ⬜ pending |
| TBD | 02 | 2 | CXXG-04 | smoke | `python tools/cxx_api_parity/check_parity_gate.py --help` exits 0 | ❌ W0 | ⬜ pending |
| TBD | 03 | 3 | CXXG-02 | end-to-end | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` exits 0 against committed baseline | ❌ W0 | ⬜ pending |
| TBD | 03 | 3 | CXXG-05 | doc presence | `test -f docs/api/cxx-parity-gate.md && grep -q "## Local Run" docs/api/cxx-parity-gate.md` | ❌ W0 | ⬜ pending |

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

> Existing infrastructure provides: `pyproject.toml` at repo root with pytest dependency, `uv` runner. No new framework install needed.

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

**Approval:** pending — gsd-planner fills concrete task IDs in Step 1; gsd-plan-checker verifies before VERIFICATION PASSED
