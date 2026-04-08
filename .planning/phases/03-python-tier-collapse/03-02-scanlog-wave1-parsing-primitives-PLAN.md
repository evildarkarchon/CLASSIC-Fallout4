---
phase: 03-python-tier-collapse
plan: 02
type: execute
wave: 2
depends_on: [03-01]
files_modified:
  - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
  - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
autonomous: true
requirements: [PYT-02, PYT-04, PYT-05]
must_haves:
  truths:
    - "All 74 scanlog Wave 1 deferred entries (parser + formid + formid_analyzer + record_scanner + plugin_analyzer + patterns sub-modules) are promoted to parity_contract.json tier1Mappings"
    - "classic_scanlog.pyi covers every new row's pythonExportPath (no tier1_missing_python gap rows for Wave 1)"
    - "test_promoted_scanlog_wave1_smoke.py contains at least one pytest function per promoted #[pyclass] (PyLogParser, ScanOutput, PyRustFormIDAnalyzer, PyFormIDAnalyzerCore, PyRecordScanner, PyPluginAnalyzer, PyPatternMatcher) and one grouped test per free-function group"
    - "runtime_coverage_registry.json python-tier1-scanlog selector entry contractCount bumped to reflect new total; contractIdsHash recomputed"
    - "5-step verification chain exits 0 at plan close"
  artifacts:
    - path: "ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs"
      provides: "pub use additions for any Wave 1 symbols not already at crate root (per A3 expected to be ~0 new lines)"
    - path: "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"
      provides: "Stub entries for all 74 Wave 1 promoted symbols"
      contains: "class LogParser:"
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py"
      provides: "Per-class smoke tests for Wave 1 #[pyclass] types + grouped free-fn tests"
      min_lines: 120
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings.length grows by 74 (from 59 to 133)"
    - path: "ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json"
      provides: "python-tier1-scanlog selector row updated with new contractCount and contractIdsHash"
  key_links:
    - from: "classic_scanlog.pyi::class LogParser"
      to: "classic-scanlog-core::parser::LogParser (via PyLogParser wrapper)"
      via: "parity_contract.json tier1Mapping row"
      pattern: "\"rustSymbol\":\\s*\"LogParser\""
    - from: "test_promoted_scanlog_wave1_smoke.py"
      to: "classic_scanlog module runtime"
      via: "import classic_scanlog"
      pattern: "import classic_scanlog"
---

<objective>
Promote the 74 deferred Python parity entries for scanlog Wave 1 (parsing primitives) to the single enforced Tier-1 contract. Wave 1 covers 6 sub-modules of `classic-scanlog-core`: `parser`, `formid`, `formid_analyzer`, `record_scanner`, `plugin_analyzer`, `patterns` — totaling 74 rows per RESEARCH.md Question 2.

Per RESEARCH Amendment A3, nearly all Wave 1 symbols are already `pub use`d at `classic-scanlog-core/src/lib.rs` lines 46-71, so this plan's dominant work is contract row authoring + `.pyi` stub additions + per-class smoke tests + runtime coverage registry updates — NOT `pub use` plumbing.

Purpose: Land the first scanlog wave, prove the Phase 3 promotion pattern works end-to-end, and establish the commit-atomic shape downstream waves will copy.

Output:
- 74 new `tier1Mappings` rows in `parity_contract.json` (Wave 1 sub-modules)
- Updated `classic_scanlog.pyi` covering every promoted `pythonExportPath`
- New `test_promoted_scanlog_wave1_smoke.py` with ~12-15 pytest functions
- `runtime_coverage_registry.json::python-tier1-scanlog` selector row refreshed (bumped contractCount + recomputed contractIdsHash)
- Refreshed parity baseline per D-03 cadence
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-python-tier-collapse/03-CONTEXT.md
@.planning/phases/03-python-tier-collapse/03-RESEARCH.md
@.planning/phases/03-python-tier-collapse/03-VALIDATION.md
@.planning/phases/03-python-tier-collapse/03-01-SUMMARY.md
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- Wave 1 inventory from RESEARCH.md Question 2 + Question 6 -->

Wave 1 sub-modules (74 total rows):
- parser: 20 rows (includes StreamingLogParser, StreamingIteratorParser)
- formid: 10 rows (includes RustFormIDAnalyzer)
- formid_analyzer: 16 rows
- record_scanner: 11 rows
- plugin_analyzer: 12 rows
- patterns: 5 rows

Key PyO3 wrapper classes (from classic-scanlog-py/src/*.rs) — the `#[pyclass(name = "...")]` renamed names:
- `PyLogParser` → Python name: `LogParser` (in parser.rs)
- `parser::ScanOutput` → `ScanOutput` (factory via LogParser)
- `PyRustFormIDAnalyzer` → `RustFormIDAnalyzer`
- `PyFormIDAnalyzerCore` → `FormIDAnalyzerCore`
- `PyRecordScanner` → `RecordScanner`
- `PyPluginAnalyzer` → `PluginAnalyzer`
- `PyPatternMatcher` → `PatternMatcher`

Free-function groups:
- formid_analyzer: `extract_formids_batch`, `is_valid_formid`, `validate_formids_batch`
- record_scanner: `scan_records_batch`, `contains_record`
- plugin_analyzer: `detect_plugins_batch`, `contains_plugin`

From classic-scanlog-core/src/lib.rs (verified A3 — all these are already pub use'd):
```rust
// Lines 46-71 already re-export Wave 1 symbols:
// LogParser, ScanOutput, FormIDAnalyzerCore, RecordScanner, PluginAnalyzer,
// PatternMatcher, RustFormIDAnalyzer, StreamingLogParser, StreamingIteratorParser,
// extract_formids_batch, is_valid_formid, validate_formids_batch,
// scan_records_batch, contains_record, detect_plugins_batch, contains_plugin
```

Existing contract row shape (from parity_contract.json) for reference:
```json
{
  "id": "scanlog.parser.LogParser",
  "rustSymbol": "LogParser",
  "rustCrate": "classic-scanlog-core",
  "rustKind": "struct",
  "pythonModule": "classic_scanlog",
  "pythonExportPath": "LogParser",
  "pythonKind": "class",
  "pythonArity": null,
  "ownerModule": "scanlog",
  "tier": "tier1"
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Read source, enumerate all 74 Wave 1 symbols, verify `-core/lib.rs` coverage, and author contract rows</name>
  <files>
    ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs
    docs/implementation/python_api_parity/baseline/parity_contract.json
  </files>
  <read_first>
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/lib.rs (full file — confirm A3: all Wave 1 symbols already pub use'd; if any are missing, Task 1 adds them before authoring the contract row)
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/parser.rs (read public declarations)
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/formid.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/formid_analyzer.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/record_scanner.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/plugin_analyzer.rs
    - ClassicLib-rs/business-logic/classic-scanlog-core/src/patterns.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs (PyO3 wrapper signatures)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/record_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/plugin_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/patterns.rs
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (filter ownerModule=scanlog for Wave 1 rows)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (understand existing row shape to copy)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 2" (lines 237-281) — Wave 1 sub-module counts
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6" (lines 694-709) — Wave 1 #[pyclass] inventory
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"Research Amendment A3"
  </read_first>
  <action>
    Step 1: Verify A3. For each of the 6 Wave 1 sub-modules, confirm every deferred symbol is already `pub use`d at `classic-scanlog-core/src/lib.rs`. Use a loop through the deferred backlog filtered to ownerModule=scanlog wave1 sub-modules, and grep `pub use` in `lib.rs`. If any symbol is missing, add a narrow `pub use` line (matching the existing style at lines 46-71).

    Expected: ~0 new `pub use` lines needed per A3.

    Step 2: Author 74 tier1Mapping rows in `parity_contract.json`. For each deferred Wave 1 entry, craft a row with this shape:
    ```json
    {
      "id": "scanlog.<sub_module>.<python_export_path>",
      "rustSymbol": "<core symbol name>",
      "rustCrate": "classic-scanlog-core",
      "rustKind": "struct|enum|function|type",
      "pythonModule": "classic_scanlog",
      "pythonExportPath": "<python-facing identifier after #[pyo3(name=...)] rename>",
      "pythonKind": "class|method|function|attribute",
      "pythonArity": <int or null>,
      "ownerModule": "scanlog",
      "tier": "tier1"
    }
    ```

    Source the `rustSymbol` from the `-core` sub-module declaration; source the `pythonExportPath` from the `-py` wrapper's `#[pyclass(name = "...")]` or `#[pymethods]` or `#[pyfunction(name = "...")]` attribute.

    Specifically, author rows for:
    - **parser sub-module (20 rows):** `LogParser` class + all its `#[pymethods]` (e.g., `parse_all_sections`, `parse_main_error`, etc.); `ScanOutput` class + its getters; `StreamingLogParser`, `StreamingIteratorParser` classes
    - **formid sub-module (10 rows):** `RustFormIDAnalyzer` class + methods
    - **formid_analyzer sub-module (16 rows):** `FormIDAnalyzerCore` class + methods + `extract_formids_batch`, `is_valid_formid`, `validate_formids_batch` free fns
    - **record_scanner sub-module (11 rows):** `RecordScanner` class + methods + `scan_records_batch`, `contains_record` free fns
    - **plugin_analyzer sub-module (12 rows):** `PluginAnalyzer` class + methods + `detect_plugins_batch`, `contains_plugin` free fns
    - **patterns sub-module (5 rows):** `PatternMatcher` class + methods

    Each row's ID must be unique. Use dotted notation: `scanlog.parser.LogParser`, `scanlog.parser.LogParser.parse_all_sections`, `scanlog.formid_analyzer.extract_formids_batch`, etc.

    Step 3: Insert all 74 rows into `parity_contract.json::tier1Mappings` (sort alphabetically by ID to keep diffs stable). Final length should be 59 + 74 = 133.

    Step 4: Do NOT regenerate the baseline yet — that happens in Task 4 after the stub and tests are also in place (atomic commit per D-06).
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "import json; c = json.loads(open('docs/implementation/python_api_parity/baseline/parity_contract.json').read()); rows = [m for m in c['tier1Mappings'] if m.get('ownerModule') == 'scanlog' and m['id'].startswith(('scanlog.parser.', 'scanlog.formid.', 'scanlog.formid_analyzer.', 'scanlog.record_scanner.', 'scanlog.plugin_analyzer.', 'scanlog.patterns.'))]; print(f'Wave 1 rows: {len(rows)}'); assert len(rows) >= 74, f'Expected >=74 Wave 1 rows, got {len(rows)}'"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings` contains at least 74 rows where `ownerModule == 'scanlog'` AND `id` starts with one of `scanlog.parser.`, `scanlog.formid.`, `scanlog.formid_analyzer.`, `scanlog.record_scanner.`, `scanlog.plugin_analyzer.`, `scanlog.patterns.`
    - Every new row has non-empty `rustSymbol`, `pythonModule == 'classic_scanlog'`, non-empty `pythonExportPath`, `ownerModule == 'scanlog'`, `tier == 'tier1'`
    - `classic-scanlog-core/src/lib.rs` contains `pub use` lines for all 74 Wave 1 symbols (verify by grep; per A3 most already exist — only add what's missing)
    - `parity_contract.json` length grows from 59 to 133
  </acceptance_criteria>
  <done>74 Wave 1 contract rows authored; -core/lib.rs pub use coverage verified (A3); no baseline refresh yet (Task 4).</done>
</task>

<task type="auto">
  <name>Task 2: Update classic_scanlog.pyi with Wave 1 stub entries</name>
  <files>
    ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi (full file — understand existing stub shape, preserve docstrings, keep per-class structure)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs (exact `#[pymethods]` signatures for LogParser — source of truth for stub types)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/record_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/plugin_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/patterns.rs
    - docs/implementation/python_api_parity/baseline/parity_contract.json (read the 74 rows from Task 1 — the pythonExportPath field tells you what names to add to the stub)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"FEATURES anti-feature: auto-generated .pyi" — stubs are HAND-EDITED
  </read_first>
  <action>
    Hand-edit `classic_scanlog.pyi` to add stub entries for every Wave 1 contract row's `pythonExportPath`. For each row:
    - If it's a class, add `class <Name>:` with a docstring and all its `#[pymethods]` as `def` entries
    - If it's a method, add a `def` entry inside the class block with matching argument types
    - If it's a free function, add a top-level `def` with matching signature
    - If it's a getter/attribute (`#[pyo3(get)]`), add as a class attribute annotation

    PyO3 0.27 type mapping:
    - Rust `Vec<X>` → Python `list[X]`
    - Rust `(A, B)` → Python `tuple[A, B]`
    - Rust `Option<X>` → Python `X | None`
    - Rust `HashMap<K, V>` → Python `dict[K, V]`
    - Rust `String` / `&str` → Python `str`
    - Rust `bool` → Python `bool`
    - Rust `u32` / `i32` / `usize` → Python `int`
    - Rust `f32` / `f64` → Python `float`
    - Rust `#[pyo3(get)]` struct field → class attribute in stub

    Preserve ALL existing docstrings and annotations. Add new stub content in the same structural style. For class additions, group methods logically (constructors first, then instance methods alphabetical, then getters).

    Example new stub entries:
    ```python
    class LogParser:
        """Parses Fallout 4 crash logs from raw text input."""

        def __init__(self) -> None: ...

        def parse_all_sections(self, lines: list[str]) -> dict[str, list[str]]:
            """Parse a crash log into named sections.

            Args:
                lines: Raw crash log lines.

            Returns:
                Dictionary mapping section name to list of lines in that section.
            """
            ...

        def parse_main_error(self, lines: list[str]) -> str:
            """Extract the main error string from a crash log."""
            ...

        # ... etc for all #[pymethods] on PyLogParser

    class ScanOutput:
        """Output from a LogParser scan operation."""

        success: bool
        error: str | None
        sections_found: int
        # ... getters from PyO3 ScanOutput struct

    class StreamingLogParser:
        """Streaming variant of LogParser for large files."""
        def __init__(self, path: str) -> None: ...
        # ... methods

    # ... and so on for formid, formid_analyzer, record_scanner, plugin_analyzer, patterns
    ```

    Do NOT auto-generate via stubgen (explicit anti-feature per FEATURES research). Hand-edit only.
  </action>
  <verify>
    <automated>uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `classic_scanlog.pyi` contains `class LogParser:` at a top-level module position
    - `classic_scanlog.pyi` contains `class ScanOutput:`
    - `classic_scanlog.pyi` contains `class RustFormIDAnalyzer:`
    - `classic_scanlog.pyi` contains `class FormIDAnalyzerCore:`
    - `classic_scanlog.pyi` contains `class RecordScanner:`
    - `classic_scanlog.pyi` contains `class PluginAnalyzer:`
    - `classic_scanlog.pyi` contains `class PatternMatcher:`
    - `classic_scanlog.pyi` contains top-level `def extract_formids_batch(`, `def is_valid_formid(`, `def validate_formids_batch(`, `def scan_records_batch(`, `def contains_record(`, `def detect_plugins_batch(`, `def contains_plugin(`
    - `mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` exits 0
  </acceptance_criteria>
  <done>Stub covers all Wave 1 classes, methods, and free functions; mypy --strict clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_promoted_scanlog_wave1_smoke.py with per-class + grouped free-fn smoke tests</name>
  <files>
    ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py (reference pattern — read structure)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/parser.rs (understand PyLogParser constructor and method signatures — source of truth for test bodies)
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/formid_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/record_scanner.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/plugin_analyzer.rs
    - ClassicLib-rs/python-bindings/classic-scanlog-py/src/patterns.rs
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 6 — classic-scanlog-py Wave 1" (lines 694-709)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-07" (per-class smoke test depth)
  </read_first>
  <behavior>
    Per D-07: "Every promoted #[pyclass] gets at least one pytest test that constructs an instance and calls one real method. Related free functions are grouped into one test each."

    Tests to include (one test function each):
    - `test_log_parser_smoke` — constructs `LogParser()`, calls `parse_all_sections([])`, asserts returns dict
    - `test_scan_output_field_access` — constructs a log parser, runs minimal parse, inspects ScanOutput.success
    - `test_streaming_log_parser_smoke` — constructs with a tmp file, reads once
    - `test_streaming_iterator_parser_smoke` — constructs and iterates one chunk
    - `test_rust_formid_analyzer_smoke` — constructs `RustFormIDAnalyzer({})`, calls `analyze([])`
    - `test_formid_analyzer_core_smoke` — constructs `FormIDAnalyzerCore({})`, calls `extract_formids("")`
    - `test_formid_analyzer_free_functions_group` — calls `extract_formids_batch([])`, `is_valid_formid("")`, `validate_formids_batch([])`
    - `test_record_scanner_smoke` — constructs `RecordScanner()`, calls `scan("")`
    - `test_record_scanner_free_functions_group` — calls `scan_records_batch([])`, `contains_record("", "")`
    - `test_plugin_analyzer_smoke` — constructs `PluginAnalyzer()`, calls `analyze([])`
    - `test_plugin_analyzer_free_functions_group` — calls `detect_plugins_batch([])`, `contains_plugin("", "")`
    - `test_pattern_matcher_smoke` — constructs `PatternMatcher([])`, calls `find_first("")`

    Target total: ~12-15 test functions per D-07 + RESEARCH Q6.

    Each test should:
    - Use minimal valid input (empty list, empty string, empty dict where signature allows)
    - Assert the return type matches the stub (e.g., `assert isinstance(result, dict)`)
    - NOT require network, file I/O beyond tmp_path, or large fixtures
    - Run in <500ms total

    Edge case: If a constructor requires a config dict, use `{}` if the wrapper accepts it; otherwise use the minimal valid shape documented in RESEARCH.md Question 6 or verified from the `-py` source.
  </behavior>
  <action>
    Create `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py`. Scaffold:

    ```python
    """Per-class smoke tests for Phase 3 Plan 02 — scanlog Wave 1 (parsing primitives).

    Covers 74 promoted contract rows across 6 sub-modules: parser, formid,
    formid_analyzer, record_scanner, plugin_analyzer, patterns.

    Each #[pyclass] gets at least one test that constructs it and calls one
    real method (per D-07). Related free functions are grouped.
    """
    from __future__ import annotations

    import classic_scanlog


    # ========================================================================
    # parser sub-module
    # ========================================================================

    def test_log_parser_construct_and_parse_empty() -> None:
        parser = classic_scanlog.LogParser()
        result = parser.parse_all_sections([])
        assert isinstance(result, dict)


    def test_log_parser_parse_main_error_empty() -> None:
        parser = classic_scanlog.LogParser()
        result = parser.parse_main_error([])
        assert isinstance(result, str)


    def test_scan_output_field_access_after_parse() -> None:
        parser = classic_scanlog.LogParser()
        # ScanOutput is returned indirectly; verify it can be constructed via factory
        # If ScanOutput has no direct constructor, test via LogParser.scan() or similar
        # (Implementer: verify exact factory path from classic-scanlog-py/src/parser.rs)
        result = parser.parse_all_sections([])
        assert result is not None  # minimal smoke — stronger field access requires real input


    def test_streaming_log_parser_construct(tmp_path) -> None:
        import pathlib
        log_file = tmp_path / "empty.log"
        log_file.write_text("")
        # Verify exact constructor signature from classic-scanlog-py/src/parser.rs
        streaming = classic_scanlog.StreamingLogParser(str(log_file))
        assert streaming is not None


    def test_streaming_iterator_parser_construct(tmp_path) -> None:
        import pathlib
        log_file = tmp_path / "empty.log"
        log_file.write_text("")
        iterator = classic_scanlog.StreamingIteratorParser(str(log_file))
        assert iterator is not None


    # ========================================================================
    # formid / formid_analyzer sub-modules
    # ========================================================================

    def test_rust_formid_analyzer_construct() -> None:
        analyzer = classic_scanlog.RustFormIDAnalyzer({})
        result = analyzer.analyze([])
        assert result is not None


    def test_formid_analyzer_core_extract_empty() -> None:
        core = classic_scanlog.FormIDAnalyzerCore({})
        result = core.extract_formids("")
        assert isinstance(result, (list, tuple))


    def test_formid_analyzer_free_functions_group() -> None:
        # Grouped test for extract_formids_batch, is_valid_formid, validate_formids_batch
        batch_result = classic_scanlog.extract_formids_batch([])
        assert isinstance(batch_result, (list, tuple))

        valid = classic_scanlog.is_valid_formid("")
        assert isinstance(valid, bool)

        validate_result = classic_scanlog.validate_formids_batch([])
        assert isinstance(validate_result, (list, tuple, dict))


    # ========================================================================
    # record_scanner sub-module
    # ========================================================================

    def test_record_scanner_scan_empty() -> None:
        scanner = classic_scanlog.RecordScanner()
        result = scanner.scan("")
        assert result is not None


    def test_record_scanner_free_functions_group() -> None:
        batch_result = classic_scanlog.scan_records_batch([])
        assert isinstance(batch_result, (list, tuple, dict))

        contains = classic_scanlog.contains_record("", "")
        assert isinstance(contains, bool)


    # ========================================================================
    # plugin_analyzer sub-module
    # ========================================================================

    def test_plugin_analyzer_analyze_empty() -> None:
        analyzer = classic_scanlog.PluginAnalyzer()
        result = analyzer.analyze([])
        assert result is not None


    def test_plugin_analyzer_free_functions_group() -> None:
        batch_result = classic_scanlog.detect_plugins_batch([])
        assert isinstance(batch_result, (list, tuple, dict))

        contains = classic_scanlog.contains_plugin("", "")
        assert isinstance(contains, bool)


    # ========================================================================
    # patterns sub-module
    # ========================================================================

    def test_pattern_matcher_find_first_empty() -> None:
        matcher = classic_scanlog.PatternMatcher([])
        result = matcher.find_first("")
        # Empty pattern list + empty haystack — result is None or empty
        assert result is None or isinstance(result, (str, tuple, int))
    ```

    Notes for executor:
    - Before committing, verify every `classic_scanlog.<Name>` attribute exists by running the test file against the current wheel. Any `AttributeError` means the class needs `m.add_class::<PyXxx>()?;` in `classic-scanlog-py/src/lib.rs::classic_scanlog` (Pitfall 4).
    - If the exact constructor signature differs from the scaffold (e.g., `RustFormIDAnalyzer` takes `(config: dict, validator: bool)` instead of just `({})`), read the `#[pymethods]` `new` declaration in the `-py` source and update the test.
    - Use `tmp_path` fixture for file-based constructors.
    - Do not import `pytest` unless you use `pytest.raises` — vanilla pytest auto-collects `test_*` functions.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py -v 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py` exists
    - File contains at least 12 `def test_*` functions
    - File contains `import classic_scanlog` at the top
    - `pytest test_promoted_scanlog_wave1_smoke.py -v` exits 0 after rebuild (all tests pass)
    - Each `#[pyclass]` from Wave 1 (LogParser, ScanOutput, StreamingLogParser, StreamingIteratorParser, RustFormIDAnalyzer, FormIDAnalyzerCore, RecordScanner, PluginAnalyzer, PatternMatcher) is referenced by at least one test
    - Free-function groups (extract_formids_*, scan_records_*, detect_plugins_*) each have one grouped test
  </acceptance_criteria>
  <done>Wave 1 smoke test file exists with ~12-15 passing tests covering every promoted class + grouped free functions.</done>
</task>

<task type="auto">
  <name>Task 4: Update runtime_coverage_registry.json, refresh baseline, run 5-step verification chain</name>
  <files>
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  </files>
  <read_first>
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (full file — find the `python-tier1-scanlog` selector entry)
    - tools/binding_parity_runtime_coverage.py (understand `_stable_id_hash` and `contractIdsHash` recomputation)
    - .planning/phases/03-python-tier-collapse/03-RESEARCH.md §"Question 7 — Path A (selector)" (lines 829-860)
    - .planning/phases/03-python-tier-collapse/03-CONTEXT.md §"D-08" (1:1 registry row per contract row; selector path satisfies this)
  </read_first>
  <action>
    Step 1: Update `runtime_coverage_registry.json`. Find the `python-tier1-scanlog` selector entry:
    ```json
    {
      "coverageId": "python-tier1-scanlog",
      "classification": "runtime_verified",
      "ownerModule": "scanlog",
      "tier": "tier1",
      "contractSelector": {"ownerModule": "scanlog", "tier": "tier1"},
      "contractCount": <old_value>,
      "contractIdsHash": "<old_hash>",
      "verificationMode": "workflow_smoke",
      "testSuite": "ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py",
      "testCaseId": "<existing>",
      ...
    }
    ```
    Bump the `contractCount` to reflect the new total scanlog Tier-1 rows (20 existing + 74 Wave 1 = 94). The hash will be recomputed by `generate_baseline.py --write-baseline` in Step 2.

    Update the `testSuite` field to reference both the existing file AND the new Wave 1 smoke file:
    ```json
    "testSuite": "ClassicLib-rs/python-bindings/tests/test_tier1_parity_smoke.py,ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py"
    ```
    (Or whatever multi-file separator the existing schema uses; check other entries for precedent.)

    Step 2: Refresh the baseline in lockstep (D-03 cadence):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 3: Run the Python parity gate:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```
    Expected: exit 0, output contains "Tier-1 parity gate passed.", `tier1_contract_total` = 133, `tier1_matched` = 133, `tier1_missing_rust` = 0, `tier1_missing_python` = 0, `tier1_missing_runtime_total` = 0.

    Step 4: Run `validate_stubs.py`:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings"
    ```
    Expected: exit 0.

    Step 5: Rebuild the scanlog wheel:
    ```powershell
    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog
    ```
    Expected: exit 0, wheel produced and installed into `ClassicLib-rs/python-bindings/.venv`.

    Step 6: Run the full pytest suite:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
    ```
    Expected: exit 0, all existing tests + new `test_promoted_scanlog_wave1_smoke.py` pass.

    Step 7: Run `mypy --strict` on the updated stub:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
    ```
    Expected: `Success: no issues found in 1 source file`.

    If any step fails, fix and re-run. Do NOT commit partial state.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi"</automated>
  </verify>
  <acceptance_criteria>
    - `runtime_coverage_registry.json::python-tier1-scanlog` entry has `contractCount >= 94`
    - `parity_contract.json::tier1Mappings.length == 133`
    - `parity_diff_report.json::summary.tier1_missing_rust == 0`
    - `parity_diff_report.json::summary.tier1_missing_python == 0`
    - `parity_diff_report.json::summary.tier1_signature_mismatch == 0`
    - `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0`
    - `runtime_coverage_summary.json::summary.registry_mismatch_total == 0`
    - `python tools/python_api_parity/check_parity_gate.py --repo-root .` exits 0
    - `python ClassicLib-rs/validate_stubs.py --fail-on-warnings` exits 0
    - `pytest ClassicLib-rs/python-bindings/tests/test_promoted_scanlog_wave1_smoke.py -q` exits 0
    - `mypy --strict classic_scanlog.pyi` exits 0
    - All 9 baseline files have refreshed timestamps (atomic with code change per D-03/D-06)
  </acceptance_criteria>
  <done>5-step verification chain exits 0; baseline refreshed in lockstep; repository gate-green after the atomic Plan 02 commit.</done>
</task>

</tasks>

<verification>
Plan-close 5-step verification chain (non-negotiable):
1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exit 0
2. `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — exit 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python classic_scanlog` — exit 0
4. `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q` — exit 0
5. `uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi` — exit 0
</verification>

<success_criteria>
- `parity_contract.json::tier1Mappings.length` grew by 74 (59 → 133)
- All 74 Wave 1 scanlog sub-module rows present with valid `rustSymbol`, `pythonExportPath`, `ownerModule`, `tier`
- `classic_scanlog.pyi` covers every Wave 1 `pythonExportPath`; `mypy --strict` clean
- `test_promoted_scanlog_wave1_smoke.py` contains ~12-15 tests covering every `#[pyclass]` + grouped free-fns
- `runtime_coverage_registry.json::python-tier1-scanlog::contractCount` bumped; hash recomputed
- 5-step verification chain exits 0
- Atomic single commit per D-06 contains all source + stub + tests + registry + baseline files
</success_criteria>

<output>
After completion, create `.planning/phases/03-python-tier-collapse/03-02-SUMMARY.md` containing:
- Files modified
- Final `tier1Mappings.length` (133)
- Smoke test count added
- Verification chain results (all 5 steps)
- Any symbols that required `pub use` additions (expected: 0 per A3)
</output>
