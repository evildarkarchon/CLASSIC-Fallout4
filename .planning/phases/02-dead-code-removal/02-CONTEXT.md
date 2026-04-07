# Phase 2: Dead Code Removal - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Delete all dead code items (`SEGMENT_BOUNDARIES`, `YamlFormatConfig`, `PluginAnalyzer.case_cache`, `PyGpuDetector.inner`), remove deprecated methods (`parse_segments`, `parse_segments_parallel`, `is_outdated`) now that Phase 1 migrated all callers, eliminate the `scan_all_settings_legacy_bucketed` legacy fallback path, convert `PyGpuDetector` to a stateless class, and add an assertion test confirming production configs never hit the legacy path. No new features, no binding API redesigns.

</domain>

<decisions>
## Implementation Decisions

### Adjacent Dead Code Scope
- **D-01:** Clean as you go -- also remove `fast_contains` (parser.rs:1208) and the `test_custom_format_config` integration test (integration_tests.rs:490) alongside the required dead code items, since we're already editing those files. No point leaving known dead code behind.

### Deprecated Shim Test Disposition
- **D-02:** Migrate the 3 remaining `#[allow(deprecated)]` tests (`test_segment_parsing_deprecated_shim`, `test_segment_parsing_with_patches_first_boundary`, `test_deprecated_parse_segments_preserves_xse_modules_slot`) to use `parse_all_sections`/`parse_all_sections_arc` first, ensuring segment boundary parsing, patch ordering, and XSE module slot preservation behavior are covered under the current API. Then delete the deprecated methods.

### Legacy Fallback Elimination Strategy
- **D-03:** Two-step approach. First add the assertion test (TEST-02) proving production configs never hit `scan_all_settings_legacy_bucketed` while the legacy code is still present. Validate the test passes. Then remove the legacy code in a second step. This gives confidence before deletion.

### Claude's Discretion
- Order of deletion within the phase (which dead code item first)
- Exact test structure for migrated deprecated shim tests
- How `PyGpuDetector` constructor changes when converting to stateless (no `inner` field)
- Whether `SEGMENT_BOUNDARIES` removal also removes the `once_cell::sync::Lazy` import if it becomes unused in that file (note: Phase 7 does a full `Lazy` -> `LazyLock` sweep, but removing an unused import is fine now)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dead Code Locations
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` -- `SEGMENT_BOUNDARIES` (line ~70), `fast_contains` (line ~1208), deprecated `parse_segments` (line ~459) and `parse_segments_parallel` (line ~475), 3 deprecated shim tests (lines ~1615, ~1625, ~1642)
- `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs` -- `YamlFormatConfig` struct and `format_config` field on `YamlOperations` (line ~507)
- `ClassicLib-rs/business-logic/classic-yaml-core/tests/integration_tests.rs` -- `test_custom_format_config` test using `YamlFormatConfig` (line ~490)
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs` -- `PluginAnalyzer.case_cache` field (line ~67)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/gpu_detector.rs` -- `PyGpuDetector.inner` field (line ~118)
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` -- `is_outdated` deprecated method (line ~200)

### Legacy Fallback Path
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/settings_validator.rs` -- `scan_all_settings` fallback call (line ~192) and `scan_all_settings_legacy_bucketed` method (line ~195)

### Contract Files
- `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` -- Python type stub (may need update after `PyGpuDetector` stateless conversion)
- `ClassicLib-rs/Cargo.toml` -- workspace lint config (`deprecated = "deny"`)

### Prior Phase Context
- `.planning/phases/01-deprecated-api-migration/01-CONTEXT.md` -- Phase 1 decisions (D-04: lint stays at deny, D-05: test migration expands coverage)

### API Docs
- `docs/api/classic-scanlog-core.md` -- scanlog API reference
- `docs/api/classic-yaml-core.md` -- yaml API reference
- `docs/api/binding-parity-overview.md` -- binding surface comparison

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_all_sections_arc` is the canonical replacement for `parse_segments`/`parse_segments_parallel` -- already used by Python binding (parser.rs:227)
- `check_version_status` is the canonical replacement for `is_outdated` -- Phase 1 migrated tests to use it
- `GpuDetector` methods are all static -- `PyGpuDetector` needs no inner state

### Established Patterns
- Phase 1 set the pattern for deprecated API removal: migrate callers first, then delete
- `#[allow(dead_code)]` annotations mark all dead code items -- easy to find via grep
- Integration tests in `classic-yaml-core/tests/integration_tests.rs` import `YamlFormatConfig` directly -- will fail on removal

### Integration Points
- Python parity gate: `python tools/python_api_parity/check_parity_gate.py --repo-root .`
- Node parity gate: `bun run parity:gate:local` (from node-bindings dir)
- `cargo build --workspace` must pass after all removals
- `cargo test --workspace` must pass after test migrations and removals

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches for dead code deletion and test migration.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 02-dead-code-removal*
*Context gathered: 2026-04-05*
