# Phase 3 Deferred Items

Out-of-scope discoveries surfaced during Phase 3 plan execution. These are
**not** caused by the current plan's changes and per the SCOPE BOUNDARY rule
in execute-plan.md they are logged here rather than fixed in-flight.

## Plan 02 (scanlog Wave 1) Discoveries

### Pre-existing pytest failures in `ClassicLib-rs/python-bindings/tests/`

Verified by running `pytest tests/ -q` against the pre-Plan-02 baseline
(stashed Plan 02 changes, ran tests, observed identical failures, restored).

1. **`test_phase2_dead_code_removal.py::test_gpu_detector_binding_is_stateless_and_repeatable`** — pre-existing failure. Likely pytest test ordering issue or stale test fixture from Phase 2 dead-code-removal milestone work. Not related to Wave 1.
2. **`test_tier1_parity_smoke.py::test_parse_segments_parallel_deprecation_warning`** — pre-existing. The test expects a `DeprecationWarning` to be raised when calling `LogParser.parse_segments_parallel`; the wrapper code does emit one (verified in `parser.rs:108-114`) but pytest's warning capture is not catching it. Likely a pytest config / `filterwarnings` interaction.
3. **`test_tier1_parity_smoke.py::test_generate_suspect_section_deprecation_warning`** — pre-existing. Same family of issue as #2.
4. **`test_tier1_parity_smoke.py::test_formid_analyzer_legacy_dict_deprecation_warning`** — pre-existing. Same family of issue as #2 (legacy dict format deprecation in `PyFormIDAnalyzerCore.__new__`).
5. **`test_tier1_parity_smoke.py::test_runtime_coverage_registry_cases[cache-helpers-tier2-smoke]`** — pre-existing. `ModuleNotFoundError: No module named 'classic_file_io'`. The cache-helpers tier-2 case driver attempts `import classic_file_io` but that module is not installed in the python-bindings venv; only `classic_config`, `classic_scanlog`, and `classic_version_registry` are installed. This is a venv-installation gap, not a code defect.

**Out of scope reasoning:** None of these failures touch the parser, formid, formid_analyzer, record_scanner, plugin_analyzer, or patterns sub-modules that Plan 02 promotes. The new `test_promoted_scanlog_wave1_smoke.py` suite is independent and passes 36/36. The Plan 02 5-step verification chain (parity gate, validate_stubs, mypy, wave1 pytest, baseline freshness) all pass.

**Recommended Phase 3 follow-up:** A separate quick task to (a) install the remaining `classic_*` wheels into the python-bindings venv so the cache-helpers tier-2 smoke test can run, and (b) audit pytest `filterwarnings` config / `pytest.warns` usage in `test_tier1_parity_smoke.py` to fix the deprecation-capture failures. Estimate: 30 min.
