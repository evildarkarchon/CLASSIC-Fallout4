## Why

Python paths in CLASSIC already provide high-value operational visibility (clear levels, actionable context, and consistent diagnostics), while Rust/C++/Node paths do not yet provide equivalent signal quality. This gap makes cross-language troubleshooting slower and increases risk when behavior differs by runtime.

## What Changes

- Define a cross-language logging contract so Rust, C++, and Node emit logs with parity to Python semantics.
- Standardize event taxonomy, severity mapping, and required contextual fields across Python, Rust, C++, and Node boundaries.
- Add redaction and sensitive-data handling rules so parity improvements do not leak secrets or local machine-sensitive details.
- Add startup/runtime diagnostics for each non-Python stack that match Python's operator-facing clarity (environment, binding health, dependency readiness, and actionable failure hints).
- Add testable acceptance criteria for logging parity (format, field presence, level mapping, and representative workflow coverage).

## Capabilities

### New Capabilities
- `cross-language-logging-parity`: Defines required logging behavior and diagnostics quality across Rust, C++, and Node to match Python's observability standards.

### Modified Capabilities
- None.

## Impact

- Affected code: Rust crates in `ClassicLib-rs/`, C++ surfaces in `classic-cli/` and `classic-gui/`, Node bindings in `ClassicLib-rs/node-bindings/classic-node/`, and shared integration points in `ClassicLib/integration/`.
- APIs/interfaces: Logging wrapper interfaces, bridge-layer diagnostics emission, and language-specific level/field adapters.
- Tooling/tests: New or expanded parity tests in language-specific test suites and CI workflows to verify cross-language logging requirements.
- Operations: Improved supportability for crash triage, binding diagnostics, and multi-language runtime troubleshooting.
