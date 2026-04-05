---
phase: 01-deprecated-api-migration
verified: 2026-04-05T09:00:00Z
status: gaps_found
score: 4/5 success criteria verified
re_verification: false
gaps:
  - truth: "REQUIREMENTS.md traceability table reflects completed status for DEBT-05, DEBT-06, DEBT-10"
    status: partial
    reason: "REQUIREMENTS.md shows DEBT-05, DEBT-06, DEBT-10 as '[ ] Pending' in both the requirement list and traceability table. Only DEBT-07 is marked complete. The code implementations exist and are correct, but planning artifacts were not updated to reflect completion."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "Lines 16-17, 21: requirement items still show '[ ]' (unchecked). Lines 91-92, 96 in traceability table still show 'Pending' for DEBT-05, DEBT-06, DEBT-10."
    missing:
      - "Mark DEBT-05, DEBT-06, DEBT-10 as '[x]' in the requirement list (lines 16, 17, 21)"
      - "Update traceability table entries for DEBT-05, DEBT-06, DEBT-10 from 'Pending' to 'Complete' (lines 91, 92, 96)"
human_verification:
  - test: "Run Python binding deprecation warning tests against the built wheel"
    expected: "All three pytest.warns tests pass: test_parse_segments_parallel_deprecation_warning, test_generate_suspect_section_deprecation_warning, test_formid_analyzer_legacy_dict_deprecation_warning"
    why_human: "Requires rebuilding the classic-scanlog-py wheel with maturin and running pytest against the installed binding — cannot verify runtime warning emission without the Python runtime and compiled extension"
  - test: "Run Node parity gate (parity:gate:local) to confirm no regression"
    expected: "Node parity gate exits 0 — no Node binding files were changed in this phase so the gate should pass unchanged"
    why_human: "Requires bun and the compiled Node .node addon — cannot verify without the runtime environment"
---

# Phase 01: Deprecated API Migration Verification Report

**Phase Goal:** All binding surfaces use current APIs with deprecation warnings emitted for end-users still calling legacy Python methods
**Verified:** 2026-04-05T09:00:00Z
**Status:** gaps_found (1 documentation gap; all code implementations verified)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | Python `parse_segments_parallel` internally delegates to `parse_all_sections_arc` and `.pyi` contract updated | VERIFIED | `parser.rs:117` calls `self.inner.parse_all_sections_arc`; `classic_scanlog.pyi:324` shows `-> dict[str, list[str]]` with `.. deprecated::` doc |
| SC2 | Python `generate_suspect_section` internally calls `generate_suspect_section_header` + `generate_suspect_found_footer` | VERIFIED | `report.rs:323-325` calls both replacement methods; delegating correctly with `py: Python<'_>` first param |
| SC3 | All tests formerly using `#[allow(deprecated)]` on `is_outdated` now exercise `check_version_status()` | VERIFIED | `version.rs` has zero `#[allow(deprecated)]` annotations in test block; 7 new `test_check_version_status_*` functions present at lines 456-527 |
| SC4 | `PyFormIDAnalyzerCore::new` emits `DeprecationWarning` when receiving legacy `PyDict` format for `mods_single` | VERIFIED | `formid_analyzer.rs:105-112` checks `mods_single.is_some()` and calls `PyErr::warn` with `c"Passing mods_single as dict[str, str] is deprecated..."` |
| SC5 | Python and Node parity gates pass after all migrations | VERIFIED (Python) / UNCERTAIN (Node) | Python parity gate artifact shows 59/59 tier-1 matched; Node gate not run but no Node files modified |

**Score:** 4/5 truths fully verified (SC5 is partial — Python confirmed, Node unconfirmed by artifact but unchanged)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` | Expanded check_version_status test suite | VERIFIED | Contains all 7 new test functions; zero `#[allow(deprecated)]` in test block; zero `.is_outdated(` calls in test block |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs` | Migrated parse_segments_parallel with DeprecationWarning | VERIFIED | Returns `PyResult<Bound<'py, PyDict>>`; imports `PyDeprecationWarning`; calls `parse_all_sections_arc` |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` | Migrated generate_suspect_section with DeprecationWarning | VERIFIED | Accepts `py: Python<'_>`; returns `PyResult<PyReportFragment>`; emits warning; delegates to both replacement methods |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs` | DeprecationWarning on legacy PyDict mods_single | VERIFIED | `py: Python<'_>` as first param; warning emitted when `mods_single.is_some()` |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` | Updated type stub with dict return type | VERIFIED | `parse_segments_parallel` returns `dict[str, list[str]]`; both `parse_segments_parallel` and `generate_suspect_section` have `.. deprecated::` doc; `FormIDAnalyzerCore.__init__` has mods_single deprecation note |
| `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` | Three pytest.warns(DeprecationWarning) tests | VERIFIED | All 3 tests present with `pytest.warns(DeprecationWarning)` context managers and regex `match=` assertions |
| `docs/api/classic-scanlog-core.md` | Updated API doc for Python binding return type change | VERIFIED | Line 211 states `dict[str, list[str]]` return type; line 473 notes the Python binding return type change |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `parser.rs parse_segments_parallel` | `LogParser::parse_all_sections_arc` | direct delegation | WIRED | `parser.rs:117` calls `self.inner.parse_all_sections_arc(&arc_lines)` |
| `report.rs generate_suspect_section` | `ReportGenerator::generate_suspect_section_header` | delegation | WIRED | `report.rs:323` calls `self.inner.generate_suspect_section_header()` |
| `report.rs generate_suspect_section` | `ReportGenerator::generate_suspect_found_footer` | delegation | WIRED | `report.rs:324-325` derives `found_suspect` and calls `generate_suspect_found_footer` |
| `formid_analyzer.rs PyFormIDAnalyzerCore::new` | `PyErr::warn with PyDeprecationWarning` | warning before conversion | WIRED | `formid_analyzer.rs:105-112` warns when `mods_single.is_some()` |
| `test_tier1_parity_smoke.py deprecation tests` | all three deprecated Python methods | `pytest.warns` | WIRED | All 3 tests use `pytest.warns(DeprecationWarning, match=...)` context managers |

### Data-Flow Trace (Level 4)

Not applicable — this phase modifies binding wrappers and test code, not data-rendering components. The binding methods delegate to core Rust APIs that produce real data; the deprecation warnings are side-effects appended to correct delegation paths.

### Behavioral Spot-Checks

| Behavior | Check | Result | Status |
|----------|-------|--------|--------|
| version.rs has 7 new test functions and zero deprecated annotations | `grep -n "test_check_version_status_\|allow(deprecated)" version.rs` | 7 test functions found, 0 deprecated annotations in test block | PASS |
| parser.rs returns PyDict not PyList | `grep -n "PyResult<Bound<'py, PyDict>>" parser.rs` | Found at line 108 | PASS |
| report.rs delegates to both replacement methods | `grep -n "generate_suspect_section_header\|generate_suspect_found_footer" report.rs` | Both found at lines 323-325 | PASS |
| formid_analyzer.rs first param is `py: Python<'_>` | `grep -n "py: Python" formid_analyzer.rs` | Found at line 66 | PASS |
| .pyi returns dict[str, list[str]] | `grep -n "dict\[str, list\[str\]\]" classic_scanlog.pyi` | Found at line 324 | PASS |
| Python parity gate artifact shows pass | parity-artifacts/tier1_gate_report.md | "Tier-1 gate passed. 59/59" | PASS |
| All 3 deprecation warning tests use pytest.warns | `grep -n "pytest.warns" test_tier1_parity_smoke.py` | 3 occurrences at lines 504, 516, 528 | PASS |
| Commits exist for both plans | `git log --oneline -10` | 4 commits from plans 01-01 and 01-02 present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEBT-07 | 01-01-PLAN.md | Rewrite tests using `#[allow(deprecated)]` on `is_outdated` | SATISFIED | `version.rs` has 7 new `check_version_status` tests, zero deprecated annotations in test block |
| DEBT-05 | 01-02-PLAN.md | Migrate Python `parse_segments_parallel` to `parse_all_sections_arc`, update `.pyi` | SATISFIED | `parser.rs` delegates to `parse_all_sections_arc`, returns `PyDict`; `.pyi` updated |
| DEBT-06 | 01-02-PLAN.md | Migrate Python `generate_suspect_section` to header+footer | SATISFIED | `report.rs` delegates to both replacement methods with `PyDeprecationWarning` |
| DEBT-10 | 01-02-PLAN.md | Add `DeprecationWarning` to `PyFormIDAnalyzerCore::new` for legacy `PyDict` | SATISFIED | `formid_analyzer.rs` emits warning when `mods_single.is_some()` |

**Orphaned requirements check:** No Phase 1 requirements in REQUIREMENTS.md are unaccounted for in plan frontmatter — all four (DEBT-05, DEBT-06, DEBT-07, DEBT-10) are claimed by plans.

**Documentation gap:** REQUIREMENTS.md traceability table still shows DEBT-05, DEBT-06, DEBT-10 as `Pending` (only DEBT-07 is marked `Complete`). The implementations are in the code; the planning doc was not updated. This is classified as a minor gap rather than a blocker.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/REQUIREMENTS.md` | 16, 17, 21, 91, 92, 96 | DEBT-05/06/10 marked as `[ ]` and `Pending` despite code implementation being complete | Warning | Planning documentation is out of sync with code state; no code impact |
| `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` | 1615, 1625, 1641 | `#[allow(deprecated)]` annotations | Info | These are in tests for the core `parse_segments` method (different from `is_outdated`); these are in-scope for Phase 2 (DEBT-08) removal, not Phase 1 |

### Human Verification Required

#### 1. Python Binding Runtime Warning Emission

**Test:** Build the `classic-scanlog-py` wheel with `rebuild_rust.ps1 -Target python -Crates classic-scanlog-py` and run `uv run pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -k "deprecation_warning" -v`
**Expected:** All three tests (`test_parse_segments_parallel_deprecation_warning`, `test_generate_suspect_section_deprecation_warning`, `test_formid_analyzer_legacy_dict_deprecation_warning`) pass with no errors
**Why human:** Requires the compiled PyO3 extension `.pyd`/`.so` to be built and installed into the test environment — cannot verify at the Python source level that `PyErr::warn` actually reaches the Python `warnings` module at runtime

#### 2. Node Parity Gate Confirmation

**Test:** From `ClassicLib-rs/node-bindings/classic-node/`, run `bun run parity:gate:local`
**Expected:** Parity gate exits 0 — no Node binding files were changed so the gate should be unaffected
**Why human:** Requires the compiled NAPI `.node` addon and bun runtime

## Gaps Summary

One documentation gap was found: REQUIREMENTS.md was not updated after plans 01-01 and 01-02 completed. The traceability table (lines 91, 92, 96) still shows DEBT-05, DEBT-06, and DEBT-10 as "Pending" instead of "Complete", and the requirement checklist items (lines 16, 17, 21) are still `[ ]` instead of `[x]`. This is a planning artifact maintenance issue — all four requirement implementations (DEBT-05, DEBT-06, DEBT-07, DEBT-10) exist and are correct in the codebase. The gap does not affect Phase 2 planning but does leave the requirements doc inaccurate.

The `#[allow(deprecated)]` annotations remaining in `classic-scanlog-core/src/parser.rs` (lines 1615, 1625, 1641) are not a gap for this phase — they guard tests of the core `parse_segments` method which is separate from `is_outdated`, and these tests are correctly targeted for removal in Phase 2 under DEBT-08.

---

_Verified: 2026-04-05T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
