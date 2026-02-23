## 1. Update `parse_all_sections()` — anchor-first segmentation

- [x] 1.1 Add a `SegmentKey` constants module (or `const` statics) for the 8 named keys (`settings`, `system`, `callstack`, `modules`, `xse_modules`, `plugins`, `registers`, `stack_dump`) to prevent bare string literals at call sites
- [x] 1.2 Rewrite the `settings` collection in `parse_all_sections()`: collect all lines from line 1 until the first occurrence of `SYSTEM SPECS:` (exclusive); remove the `[Compatibility]`/`[Patches]` start-marker logic entirely
- [x] 1.3 Capture the first bracket-line (`[...]`) in the settings content as `settings_header` metadata alongside the returned map
- [x] 1.4 Add `xse_modules` sub-section detection within MODULES content: split on the first line matching `^[A-Z][A-Z0-9 ]+:\s*$` or starting with `[` (trimmed); lines before → `modules`, lines after (exclusive) → `xse_modules`
- [x] 1.5 Guarantee all 8 named keys are always present in the output map; insert an empty `Vec` for any anchor not found in the log
- [x] 1.6 Update the LRU segment cache value type from `Vec<Vec<Arc<str>>>` to `HashMap<String, Vec<Arc<str>>>`
- [x] 1.7 Mark `parse_segments()` as `#[deprecated]` with a shim body that calls `parse_all_sections()` and reconstructs the positional `Vec` for backward compatibility; add a removal tracking comment
- [x] 1.8 Update `StreamingLogParser::is_boundary_marker()` — remove `[Compatibility]` from the checked list (it is no longer a segment boundary)
- [x] 1.9 Write Rust unit tests covering: unknown bracket header segments correctly, no header segments correctly, `xse_modules` split on unknown sub-header, missing anchor produces empty list for that key, all 8 keys always present

## 2. Add `CrashgenRegistry`

- [x] 2.1 Add `CheckId` enum to `classic-scanlog-core` with variants: `Achievements`, `MemoryManagement`, `ArchiveLimit`, `LooksMenu`
- [x] 2.2 Add `CrashgenEntry` struct: `display_section: String`, `ignore_keys: HashSet<String>`, `checks: Vec<CheckId>`
- [x] 2.3 Add `CrashgenRegistry` struct with a `lookup(name: &str) -> &CrashgenEntry` method; normalize both sides (strip whitespace, lowercase) before comparison; return the `default` entry if no match
- [x] 2.4 Add YAML deserialization for `Crashgen_Registry` in `classic-config-core`; wire loading into the existing config initialization path
- [x] 2.5 Add `Crashgen_Registry` section to `CLASSIC Fallout4.yaml` with entries for `"Buffout 4"` (full ignore list, all 4 checks), `"Addictol"` (empty ignore list, no checks), and `default` (empty ignore list, no checks)
- [x] 2.6 Remove `Game_Info.CRASHGEN_Ignore` from `CLASSIC Fallout4.yaml` (superseded by per-crashgen `ignore_keys` in the registry; `GameVR_Info` is already deprecated and requires no action)
- [x] 2.7 Write unit tests for registry lookup: known crashgen returns its entry, unknown crashgen returns default, lookup is case-insensitive and whitespace-normalized

## 3. Update `SettingsValidator` — registry-driven routing

- [x] 3.1 Update `SettingsValidator::new()` to accept a pre-resolved `CrashgenEntry` instead of a raw `crashgen_name` string
- [x] 3.2 Replace the `buffout_settings_checks_enabled()` gate on each of the four named check methods with `self.entry.checks.contains(CheckId::X)` guards
- [x] 3.3 Update `check_disabled_settings()` to use `self.entry.ignore_keys` as the skip set (replacing the old `crashgen_ignore` field sourced from game-level config)
- [x] 3.4 Update the F4EE warning message in `scan_buffout_looksmenu_setting()` to reference `self.entry.display_section` instead of the hardcoded string `[Compatibility]`
- [x] 3.5 Remove `buffout_settings_checks_enabled()` method
- [x] 3.6 Update the orchestrator to resolve `CrashgenEntry` from the registry before constructing `SettingsValidator`
- [x] 3.7 Write unit tests: Buffout 4 entry runs all 4 named checks; Addictol entry runs 0 named checks; both run `check_disabled_settings()`; default entry runs only `check_disabled_settings()`

## 4. Switch orchestrator to `parse_all_sections()`

- [x] 4.1 Replace the `parse_segments()` call in `process_log()` with `parse_all_sections()`
- [x] 4.2 Replace `segments[0]` (×2) with `segments[SegmentKey::SETTINGS]` for crashgen settings extraction
- [x] 4.3 Replace `segments[1]` with `segments[SegmentKey::SYSTEM]` for GPU info
- [x] 4.4 Replace all four `segments[2]` accesses with `segments[SegmentKey::CALLSTACK]` (suspects scan, plugin matching, FormID extraction, named record scanning)
- [x] 4.5 Replace both `segments[3]` accesses with `segments[SegmentKey::MODULES]` for XSE module extraction
- [x] 4.6 Replace the plugin segment reverse-scan (`segments.iter().rev().find(...)`) with direct `segments[SegmentKey::PLUGINS]` lookup
- [x] 4.7 Update `detect_incomplete_log()` to accept `segments: &HashMap<String, Vec<String>>` and check `segments[SegmentKey::PLUGINS].is_empty()`

## 5. Update PyO3 bindings

- [x] 5.1 Update `ScanOutput.segments` in `classic-scanlog-py` from `Py<PyList>` (list of lists) to a `Py<PyDict>` (string keys to lists of strings)
- [x] 5.2 Update `classic_scanlog.pyi` stub: `segments: dict[str, list[str]]`
- [x] 5.3 Add a binding-level integration test that accesses `scan_output.segments["callstack"]` and `scan_output.segments["plugins"]` by key

## 6. Update Python callers

- [x] 6.1 Remove `SEGMENT_BOUNDARIES_TEMPLATE` from `ClassicLib/integration/rust/parser_rust.py`
- [x] 6.2 Update `find_segments()` in `parser_rust.py` to unpack `scan_output.segments` as a `dict[str, list[str]]` and return it as such; update the return type annotation
- [x] 6.3 Update `ClassicLib/scanning/logs/parser.py` `extract_segments()`: remove `[Compatibility]` and `[Patches]` from the boundary list; replace segment-0 collection with anchor-first logic (collect from line 1 until `SYSTEM SPECS:`)
- [x] 6.4 Remove `_is_buffout_4_name()` and its call-site gate in `ClassicLib/scanning/game/check_crashgen.py`; replace with registry-aware routing (or remove if the Rust path fully handles it)
- [x] 6.5 Audit all Python call sites of `find_segments()` that unpack segments by integer index and update each to named key access (`segments["callstack"]`, `segments["plugins"]`, etc.)

## 7. Remove deleted code

- [x] 7.1 Remove the `[Patches]` / `is_compatibility_marker()` special-case block from `parse_segments()` in `parser.rs` (or remove the entire `parse_segments()` function if all callers have migrated to `parse_all_sections()`)
- [x] 7.2 Remove `is_compatibility_marker()` helper if no remaining callers exist after 7.1
- [x] 7.3 Remove `SEGMENT_BOUNDARIES_TEMPLATE` from `parser_rust.py` (done as part of 6.1; verify no remaining references)
- [x] 7.4 Confirm `buffout_settings_checks_enabled()` is fully removed (done in task 3.5; verify no remaining references across the workspace)

## 8. Update tests and fixtures

- [x] 8.1 Update `tests/fixtures/crash_log_fixtures.py`: replace `"\t[Compatibility]"` boundary entries, convert positional segment lists to `dict[str, list[str]]` format; update `segment_boundaries` fixture
- [x] 8.2 Update `tests/rust_integration/fixtures/mock_data_factory.py` and `crash_log_factory.py`: same fixture conversion
- [x] 8.3 Update parity tests in `tests/scanlog/parser/test_parser_parity.py` to assert named-key output rather than positional index
- [x] 8.4 Add test: Addictol log with `[Patches]` header produces correct non-empty segments under anchor-first approach
- [x] 8.5 Add test: log with an unknown bracket header (e.g., `[NewForkHeader]`) produces the same segment structure as a log with `[Compatibility]`
- [x] 8.6 Add test: log with no bracket header before `SYSTEM SPECS:` produces a valid (possibly empty) `settings` segment
- [x] 8.7 Add test: registry routing — `"Buffout 4"` runs `achievements`, `memory_management`, `archive_limit`, `looksmenu` and `check_disabled_settings()`; `"Addictol"` runs only `check_disabled_settings()`; unregistered crashgen runs only `check_disabled_settings()`
- [x] 8.8 Run full test suite and confirm no regressions (`uv run pytest --no-cov` and `cargo test --workspace`)
