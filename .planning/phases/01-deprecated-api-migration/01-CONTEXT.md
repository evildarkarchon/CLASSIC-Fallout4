# Phase 1: Deprecated API Migration - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all callers off deprecated Rust methods (`parse_segments_parallel`, `generate_suspect_section`, `is_outdated`) and add Python binding deprecation warnings for legacy API usage. No new features, no dead code removal (that's Phase 2), no binding API redesigns.

</domain>

<decisions>
## Implementation Decisions

### Return Type Migration (DEBT-05)
- **D-01:** `parse_segments_parallel` changes its Python return type from `list[list[str]]` to `dict[str, list[str]]` to match the underlying `parse_all_sections_arc` API. The `.pyi` contract updates accordingly. Callers must adapt to named sections instead of positional indexing.

### Deprecation Warning Strategy (DEBT-05, DEBT-06, DEBT-10)
- **D-02:** All three legacy Python methods emit `DeprecationWarning` via `PyErr::warn` when called:
  - `parse_segments_parallel` -> warns to use `parse_all_sections` (the dict-returning method)
  - `generate_suspect_section` -> warns to use `generate_suspect_section_header` + `generate_suspect_found_footer`
  - `PyFormIDAnalyzerCore::new` with legacy `PyDict` for `mods_single` -> warns to use structured `ModSolutionEntry` format
- **D-03:** Warning messages must name the replacement API explicitly so callers know where to migrate.

### Workspace Lint Handling
- **D-04:** The `deprecated = "deny"` workspace lint stays at `deny` throughout the phase. Migration call sites use surgical `#[allow(deprecated)]` annotations that are removed once the underlying call is replaced. No temporary workspace-wide lint relaxation.

### Test Migration (DEBT-07)
- **D-05:** The three `is_outdated` tests are not just rewritten as minimal equivalents -- coverage is expanded to exercise `check_version_status` with VR-specific scenarios and edge cases (e.g., VR-specific `NewerThanKnown`, empty valid lists in VR mode, version between valid entries). The migration is an opportunity to strengthen the test suite.

### Claude's Discretion
- Exact `DeprecationWarning` message wording
- Internal conversion approach for `generate_suspect_section` delegating to header + footer (deriving `bool` from `found_suspects` list)
- Specific VR edge case test scenarios beyond the ones discussed
- Order of migration within the phase (which DEBT item first)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deprecated API Locations
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs` -- `parse_segments` and `parse_segments_parallel` deprecated methods (lines ~459, ~475)
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` -- `is_outdated` deprecated method (line ~200) and `check_version_status` replacement (line ~266)
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/report.rs` -- `generate_suspect_section` legacy method in core

### Python Binding Callers
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs` -- `parse_segments_parallel` binding (line ~99) and `parse_all_sections` dict-returning method (line ~227)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/report.rs` -- `generate_suspect_section` binding (line ~307), `generate_suspect_section_header` (line ~245), `generate_suspect_found_footer` (line ~255)
- `ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs` -- `PyFormIDAnalyzerCore::new` with `legacy_mod_map_to_entries` (line ~11, ~101)

### Contract Files
- `ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` -- Python type stub that must be updated for return type change
- `ClassicLib-rs/Cargo.toml` -- workspace lint config (`deprecated = "deny"` at line ~188)

### Test Locations
- `ClassicLib-rs/business-logic/classic-scanlog-core/src/version.rs` -- `is_outdated` tests (lines ~456-484) and existing `check_version_status` tests (lines ~500-619)

### API Docs
- `docs/api/classic-scanlog-core.md` -- scanlog API reference
- `docs/api/binding-parity-overview.md` -- binding surface comparison

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_all_sections_arc` already exists and is used in the dict-returning `parse_all_sections` Python method (parser.rs:227) -- the migration target is already implemented
- `generate_suspect_section_header` and `generate_suspect_found_footer` are already exposed in Python bindings (report.rs:245, 255) -- delegation targets exist
- `check_version_status` has comprehensive tests covering Valid, Outdated, NewerThanKnown, NoSupportedVersion (version.rs:500-619) -- test patterns to follow
- `PyErr::warn` is the standard PyO3 deprecation warning mechanism

### Established Patterns
- Python bindings use `without_gil` wrapper for parallel/async operations (parser.rs:109)
- PyO3 `#[pyo3(name = "...")]` convention for method naming overrides
- `#[allow(deprecated)]` used surgically at call sites (parser.rs:98)
- `legacy_mod_map_to_entries` conversion function already exists for FormID dict->entries (formid_analyzer.rs:11)

### Integration Points
- Python parity gate: `python tools/python_api_parity/check_parity_gate.py --repo-root .`
- Node parity gate: `bun run parity:gate:local` (from node-bindings dir)
- Both gates must pass after all migrations

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches for PyO3 deprecation warnings and test expansion patterns.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 01-deprecated-api-migration*
*Context gathered: 2026-04-05*
