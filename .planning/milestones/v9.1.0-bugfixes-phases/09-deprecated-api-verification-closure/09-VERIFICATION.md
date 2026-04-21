---
phase: 09-deprecated-api-verification-closure
verified: 2026-04-07T03:21:32Z
status: passed
score: 3/3 must-haves verified
---

# Phase 09: Deprecated API Verification Closure Verification Report

**Phase Goal:** Phase 1 audit blockers are cleared by re-verifying the deprecated API migration work against the current planning state and evidence
**Verified:** 2026-04-07T03:21:32Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Phase 1 verification no longer reports a stale `gaps_found` status once current evidence is rerun | ✓ VERIFIED | `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md:3-15` shows `status: passed` with `re_verification.previous_status: gaps_found`; body at `:25-38` records fresh rerun commands rather than the old gap narrative. |
| 2 | DEBT-05, DEBT-06, DEBT-07, and DEBT-10 are each backed by explicit current evidence in `01-VERIFICATION.md` | ✓ VERIFIED | Requirement table at `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md:53-60` covers all four IDs; supporting source/tests exist in `parser.rs:102-124`, `report.rs:307-329`, `formid_analyzer.rs:103-149`, `version.rs:420-621`, `classic_scanlog.pyi:322-330`, `classic_scanlog.pyi:1299-1304`, and `test_tier1_parity_smoke.py:527-605`. |
| 3 | Python and Node parity proof for the deprecated API migration is either rerun and recorded or explicitly called out as residual proof, never assumed | ✓ VERIFIED | `01-VERIFICATION.md:31-38` and `:62-79` record Python and Node parity snapshots; current spot-checks also passed with Python Tier-1 `59/59` and Node Tier-1 `261/261` from the generated gate reports. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md` | Repo-standard re-verification artifact for the Phase 1 closure | ✓ VERIFIED | Exists, substantive (99 lines), includes `re_verification:` block, fresh command table, requirement coverage, and parity snapshots. |
| `.planning/REQUIREMENTS.md` | Requirement checklist and traceability aligned with the closure result | ✓ VERIFIED | Exists, substantive (130 lines), marks DEBT-05/06/07/10 checked at `:16-21` and maps all four to Phase 9 Complete at `:91-96`. |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs` | DEBT-05 implementation evidence | ✓ VERIFIED | Deprecated wrapper emits warning and delegates to `parse_all_sections_arc` before building dict output (`:109-123`). |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` | DEBT-06 implementation evidence | ✓ VERIFIED | Deprecated method warns, builds header + footer via replacement methods, and returns combined fragment (`:317-328`). |
| `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs` | DEBT-10 implementation evidence | ✓ VERIFIED | Legacy `mods_single` dict path emits `PyErr::warn` and still constructs structured entries (`:103-149`). |
| `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` | DEBT-07 implementation evidence | ✓ VERIFIED | Test module exercises `check_version_status()` scenarios; grep found no `#[allow(deprecated)]` or `is_outdated(` in this file. |
| `ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py` | Runtime proof for DEBT-05/06/10 | ✓ VERIFIED | Contains targeted `pytest.warns` coverage for all three deprecated Python surfaces (`:527-605`). |
| `ClassicLib-rs/node-bindings/classic-node/package.json` | Node parity script wiring for SC5 | ✓ VERIFIED | Contains `parity:gate:local`, `parity:gate`, and `dts:freshness:check` scripts (`:22-28`). |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `.planning/phases/01-deprecated-api-migration/01-VALIDATION.md` | `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md` | rerun the declared Rust and Python commands, then record the fresh results | ✓ VERIFIED | `gsd-tools verify key-links` passed; `01-VALIDATION.md:20-24,41-44` matches `01-VERIFICATION.md:31-38`. |
| `ClassicLib-rs/node-bindings/classic-node/package.json` | `.planning/phases/01-deprecated-api-migration/01-VERIFICATION.md` | record the local Node parity-gate result for SC5 instead of inferring it from unchanged files | ✓ VERIFIED | `gsd-tools verify key-links` passed; script exists in `package.json:22-28` and Node proof is recorded in `01-VERIFICATION.md:49,71-79`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `classic-scanlog-py/src/parser.rs` | `named_sections` | `self.inner.parse_all_sections_arc(&arc_lines)` | Yes — returned sections are converted into the Python dict that `parse_segments_parallel` returns | ✓ FLOWING |
| `classic-scanlog-py/src/report.rs` | `header` + `footer` | `generate_suspect_section_header()` + `generate_suspect_found_footer(found_suspect)` | Yes — deprecated API returns the real combined replacement output | ✓ FLOWING |
| `classic-scanlog-py/src/formid_analyzer.rs` | legacy `mods_single` path | `mods_single.is_some()` branch + `legacy_mod_map_to_entries(...)` | Yes — warning is emitted on real legacy input before constructing the core analyzer | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| DEBT-07 replacement tests stay green | `cargo test -p classic-scanlog-core --manifest-path ClassicLib-rs/Cargo.toml -- version::tests` | `24 passed; 0 failed` | ✓ PASS |
| Deprecated Python wrappers still warn and behave correctly | `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py -q -k "parse_segments_parallel or generate_suspect_section or formid_analyzer_legacy_dict_deprecation_warning"` | `3 passed, 11 deselected` | ✓ PASS |
| Python parity gate remains green | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | Generated Tier-1 report shows `59/59` matched, `0` missing Rust/Python, `0` signature mismatch; runtime summary notes `1` newly uncovered non-gating Python surface | ✓ PASS |
| Node parity proof remains green without inference | `bun run parity:gate && bun run dts:freshness:check` | Tier-1 report shows `261/261` matched and freshness check passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| DEBT-05 | `09-01-PLAN.md` | Migrate Python binding `parse_segments_parallel` caller to wrapper over `parse_all_sections_arc`, update `.pyi` contract | ✓ SATISFIED | `parser.rs:102-124` delegates to `parse_all_sections_arc`; `classic_scanlog.pyi:322-330` advertises `dict[str, list[str]]`; `test_tier1_parity_smoke.py:527-557` passed; `01-VERIFICATION.md:57` records current proof. |
| DEBT-06 | `09-01-PLAN.md` | Migrate Python `generate_suspect_section` legacy method to call `generate_suspect_section_header` + `generate_suspect_found_footer` separately | ✓ SATISFIED | `report.rs:307-329` combines header/footer replacements; `test_tier1_parity_smoke.py:559-589` passed; `01-VERIFICATION.md:58` records current proof. |
| DEBT-07 | `09-01-PLAN.md` | Rewrite tests using `#[allow(deprecated)]` on `CrashgenVersion::is_outdated` to exercise `check_version_status()` instead | ✓ SATISFIED | `version.rs:420-621` contains `check_version_status()` tests; grep found no `#[allow(deprecated)]` in `src/version.rs`; targeted cargo command passed; `01-VERIFICATION.md:59` records current proof. |
| DEBT-10 | `09-01-PLAN.md` | Add deprecation warning via `PyErr::warn` when `PyFormIDAnalyzerCore::new` receives legacy `PyDict` format for `mods_single` | ✓ SATISFIED | `formid_analyzer.rs:103-111` emits `PyErr::warn`; `test_tier1_parity_smoke.py:592-605` passed; `01-VERIFICATION.md:60` records current proof. |

Orphaned Phase 9 requirements in `.planning/REQUIREMENTS.md`: **none**.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| — | — | No blocker anti-patterns found in the touched planning artifacts or requirement-facing source/test files scanned for Phase 09 | ℹ️ Info | No evidence of placeholder verification text, TODO-backed closure claims, or deprecated-test reintroduction in the verified surfaces |

### Human Verification Required

None.

### Gaps Summary

No blocking gaps found. Phase 09 achieved its goal: the stale Phase 1 verification state has been replaced by a current passed re-verification artifact, all four required debt items are explicitly accounted for in both the Phase 1 verification report and `REQUIREMENTS.md`, and current automated proof confirms the Rust/Python/Node evidence the closure depends on.

---

_Verified: 2026-04-07T03:21:32Z_
_Verifier: the agent (gsd-verifier)_
