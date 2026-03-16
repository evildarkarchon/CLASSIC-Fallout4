## ADDED Requirements

### Requirement: Thin binding definition
A binding function SHALL be considered "thin" if and only if it performs exclusively these operations: (a) Python-to-Rust type conversion on inputs, (b) delegation to a single `-core` crate function or method, (c) Rust-to-Python type conversion on outputs, (d) GIL release via `without_gil()` for operations exceeding 1ms, and (e) PyO3 error mapping via `define_exceptions!` or equivalent. Any function performing validation, caching, state management, concurrency decisions, or data transformation beyond structural type conversion SHALL be classified as a violation.

#### Scenario: Pure delegation function passes audit
- **WHEN** a binding function receives Python arguments, converts them to Rust types, calls a single core method, and converts the result back to Python
- **THEN** the function SHALL be classified as compliant

#### Scenario: Function with business logic fails audit
- **WHEN** a binding function contains conditional branching based on data values (not type conversion), caches results, manages state, selects concurrency strategies, or validates business rules
- **THEN** the function SHALL be classified as a violation requiring relocation to core

#### Scenario: PyO3 enum redefinition is compliant
- **WHEN** a Rust enum is redefined as a `#[pyclass]` enum with bidirectional `From` conversions to the core type
- **THEN** the redefinition SHALL be classified as compliant (this is a required PyO3 pattern)

### Requirement: No dead code in binding layer
Every function, method, struct, and enum in a `-py` crate SHALL either be (a) exposed to Python via `#[pyfunction]`, `#[pymethods]`, or `#[pyclass]`, or (b) a private helper used exclusively for type conversion in support of an exposed API. Stub functions that return input unchanged, deprecated functions preserved solely for backward compatibility, and functions accepting parameters they ignore SHALL be removed.

#### Scenario: Stub function removal
- **WHEN** a binding function is a no-op stub (e.g., returns input unchanged or returns a hardcoded empty value)
- **THEN** the function SHALL be removed from the binding crate and its corresponding `.pyi` type stub

#### Scenario: Deprecated shim removal
- **WHEN** a binding function exists only for backward compatibility with a legacy Python API and a non-deprecated equivalent exists
- **THEN** the deprecated function SHALL be removed and any callers updated to use the current API

#### Scenario: Unused parameter cleanup
- **WHEN** a binding function accepts parameters that are ignored (prefixed with `_` or documented as unused)
- **THEN** the unused parameters SHALL be removed from the function signature, and the `.pyi` type stub SHALL be updated

### Requirement: Binding-layer type definitions must wrap core types
Every struct and enum defined in a `-py` binding crate with `#[pyclass]` SHALL wrap a corresponding type from a `-core` crate via composition (e.g., `inner: CoreType`). Types that exist only in the binding layer without a core counterpart SHALL be relocated to an appropriate `-core` crate.

#### Scenario: Binding-only metrics types relocated
- **WHEN** a `#[pyclass]` struct (such as `BridgeMetrics` or `RuntimeInfo`) is defined in a `-py` crate without wrapping a `-core` type
- **THEN** the struct's data and logic SHALL be moved to the appropriate `-core` crate, and the `-py` crate SHALL wrap the new core type

#### Scenario: Conversion-only helpers are exempt
- **WHEN** a private (non-`#[pyclass]`) helper function or struct exists solely to facilitate Python-to-Rust or Rust-to-Python type conversion
- **THEN** it SHALL be considered compliant and is not required to wrap a core type

### Requirement: Concurrency and scheduling decisions live in core
Any logic that determines parallelism levels, batch sizes, worker counts, or scheduling strategies for data processing SHALL reside in a `-core` crate. Binding crates SHALL pass through concurrency configuration from core or accept user-provided overrides without making autonomous decisions.

#### Scenario: Adaptive concurrency relocated
- **WHEN** a binding function contains logic to determine the number of parallel workers based on system resources (e.g., CPU count)
- **THEN** that logic SHALL be moved to the corresponding `-core` crate and the binding SHALL call the core function for concurrency decisions

### Requirement: No Python callbacks from binding layer
A binding function SHALL NOT call back into Python modules via `PyModule::import` when an equivalent Rust core implementation exists. Bindings exist to expose Rust to Python, not to orchestrate Python from Rust. Any binding function that imports and calls legacy Python modules SHALL be rewired to call the corresponding `-core` crate functions directly.

#### Scenario: fcx_handler rewired to Rust core
- **WHEN** the `fcx_handler.rs` `check_fcx_mode()` function needs to run setup checks and game file scanning
- **THEN** it SHALL call `classic-scangame-core::setup::run_combined_checks()` and `classic-scangame-core::orchestrator::detect_config_issues()` instead of importing `ClassicLib.SetupCoordinator` or `ClassicLib.ScanGame`

#### Scenario: No PyModule::import calls remain
- **WHEN** the audit is complete
- **THEN** no `-py` binding crate SHALL contain `PyModule::import` calls to legacy Python modules where a Rust core equivalent exists

### Requirement: Parity artifacts updated after API changes
After any binding API is removed, renamed, or has its signature changed, the parity tracking system SHALL be updated. This includes: (a) the parity diff report at `ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md`, (b) all affected `.pyi` type stub files, and (c) any parity gate tests under `ClassicLib-rs/python-bindings/tests/`.

#### Scenario: Removed API reflected in parity report
- **WHEN** a deprecated Python API function is removed from a binding crate
- **THEN** the parity diff report SHALL be regenerated and the removed function SHALL not appear as a "missing" entry

#### Scenario: Type stubs match binding signatures
- **WHEN** a binding function's signature is changed (parameters removed, return type changed)
- **THEN** the corresponding `.pyi` file SHALL be updated to match the new signature exactly
