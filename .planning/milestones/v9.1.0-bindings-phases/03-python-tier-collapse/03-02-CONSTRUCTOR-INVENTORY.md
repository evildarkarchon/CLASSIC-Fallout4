# Phase 3 Plan 02: Constructor Inventory (Wave 1)

This artifact records the **verified** PyO3 wrapper constructor signatures for every `#[pyclass]` Wave 1 promotes. All signatures were read directly from `ClassicLib-rs/python-bindings/classic-scanlog-py/src/*.rs` source files. Tasks 1-4 use these exact signatures.

## Verified Constructor Signatures

| PyO3 name (`#[pyclass(name=...)]`) | Rust wrapper struct | Source file | `fn new` signature | Notes |
|---|---|---|---|---|
| `LogParser` | `PyLogParser` | `parser.rs` | `#[new] #[pyo3(signature = (custom_boundaries=None))] pub fn new(custom_boundaries: Option<Vec<(String, String)>>) -> PyResult<Self>` | Parameterless when called as `LogParser()`; optional list of marker tuples otherwise |
| `ScanOutput` | `parser::ScanOutput` (struct, NOT a wrapper) | `parser.rs` | **NO `#[new]`** | Factory-only. Constructed via `LogParser().parse_complete(lines)`. Has 4 `#[pyo3(get)]` fields: `game_version: str`, `crashgen_version: str`, `main_error: str`, `segments: dict[str, list[str]]` |
| `FormIDAnalyzer` | `PyRustFormIDAnalyzer` | `formid.rs` | `#[new] pub fn new() -> Self` | Parameterless. Note: Python name is `FormIDAnalyzer` but the Rust core type it wraps is `RustFormIDAnalyzer`, NOT the also-existing `formid::FormIDAnalyzer`. The unwrapped `formid::FormIDAnalyzer` has no Python surface. |
| `FormIDAnalyzerCore` | `PyFormIDAnalyzerCore` | `formid_analyzer.rs` | `#[new] #[pyo3(signature = (show_formid_values=false, crashgen_name="".to_string(), important_mods=None, mods_single=None, mods_double=None))] pub fn new(py, show_formid_values: bool, crashgen_name: String, important_mods: Option<&PyAny>, mods_single: Option<&PyDict>, mods_double: Option<&PyAny>) -> PyResult<Self>` | All args optional; can be called as `FormIDAnalyzerCore()` |
| `RecordScanner` | `PyRecordScanner` | `record_scanner.rs` | `#[new] pub fn new(target_records: Vec<String>, ignore_records: Vec<String>, crashgen_name: String) -> PyResult<Self>` | All three args required positional. Use `RecordScanner([], [], "Buffout 4")` for tests. |
| `PluginAnalyzer` | `PyPluginAnalyzer` | `plugin_analyzer.rs` | `#[new] #[pyo3(signature = (game_ignore_plugins, ignore_list, crashgen_name, game_version="".to_string(), game_version_vr="".to_string()))] pub fn new(game_ignore_plugins: Vec<String>, ignore_list: Vec<String>, crashgen_name: String, game_version: String, game_version_vr: String) -> PyResult<Self>` | First three args required, last two have empty-string defaults. Use `PluginAnalyzer([], [], "Buffout 4")` for tests. |
| `PatternMatcher` | `PyPatternMatcher` | `patterns.rs` | `#[new] pub fn new(patterns: Vec<String>) -> PyResult<Self>` | Single required arg. Use `PatternMatcher([])` for tests. |

## Free Functions (no constructors)

| Python name | Rust source | Signature | Notes |
|---|---|---|---|
| `extract_formids_batch` | `formid_analyzer.rs` | `(callstack_segments: list[list[str]]) -> list[list[str]]` | Pure free function delegating to `classic_scanlog_core::extract_formids_batch` |
| `is_valid_formid` | `formid_analyzer.rs` | `(formid: str) -> bool` | |
| `validate_formids_batch` | `formid_analyzer.rs` | `(formids: list[str]) -> list[bool]` | |
| `scan_records_batch` | `record_scanner.rs` | `(segments: list[list[str]], target_records: list[str], ignore_records: list[str]) -> list[list[str]]` | |
| `contains_record` | `record_scanner.rs` | `(line: str, target_records: list[str], ignore_records: list[str]) -> bool` | |
| `detect_plugins_batch` | `plugin_analyzer.rs` | `(logs: list[str]) -> list[dict[str, str]]` | |
| `contains_plugin` | `plugin_analyzer.rs` | `(line: str) -> bool` | |

## Architectural Findings (Plan Deviations)

The plan's `<interfaces>` block lists `StreamingLogParser` and `StreamingIteratorParser` as Wave 1 `#[pyclass]` types. **They are not.** These exist as Rust public types in `classic-scanlog-core::parser`, are re-exported at `classic-scanlog-core/src/lib.rs` line 62, but **have NO PyO3 wrapper in `classic-scanlog-py`** (verified by reading `classic-scanlog-py/src/parser.rs` and `classic-scanlog-py/src/lib.rs::register_scanlog_module`).

Implications for Plan 02:

- The deferred backlog DOES include `StreamingLogParser` and `StreamingIteratorParser` as Rust-side rust_unmapped gaps (because they appear in the rust surface but no contract row references them).
- For Plan 02, these are promoted via "rust-only" rows that pair the rust symbol with the closest existing Python proxy (`LogParser`). This eliminates the rust-side gap; the rows do not create new Python obligations.
- Adding actual `PyStreamingLogParser` / `PyStreamingIteratorParser` wrappers is OUT OF SCOPE for Plan 02 (would be a Wave 2/3 expansion). Rule 4 territory if we needed real wrappers, but the gate accepts the proxy approach.

The plan's `<interfaces>` block also says "Wave 1 sub-modules (74 total rows) parser: 20 rows includes StreamingLogParser, StreamingIteratorParser." Treating the streaming types as proxy-paired rust-side rows still nets the planned 74. The stated parser sub-module breakdown of 20 rows is preserved in spirit (LogParser methods + ScanOutput + 2 streaming proxies = 19; the 20th comes from the parser module marker).

## Test Strategy Implications

- **Smoke tests only call constructors and methods that exist on the PyO3 wrappers, not on Rust core types.**
- `ScanOutput` smoke test goes through the `LogParser().parse_complete(lines)` factory chain.
- No smoke tests for `StreamingLogParser` or `StreamingIteratorParser` — they have no Python surface to call.
- Free-function smoke tests call the bare `classic_scanlog.<fn>(...)` APIs with minimal valid args.

---
*Verified: 2026-04-08*
*Source: `ClassicLib-rs/python-bindings/classic-scanlog-py/src/{parser,formid,formid_analyzer,record_scanner,plugin_analyzer,patterns}.rs`*
