## Why

The Python codebase still contains optional Rust availability checks and Python fallback paths that allow execution without Rust bindings. Rust is now mandatory for this project, so these dual paths create unnecessary complexity, inconsistent behavior, and test coverage for unsupported modes.

## What Changes

- **BREAKING** Remove runtime Rust availability detection and all Python fallback execution paths from Python application code.
- **BREAKING** Update Python integration layers to require Rust bindings and fail fast with clear errors if bindings are missing or broken.
- Remove fallback-oriented test cases, fixtures, and assertions; update tests to validate Rust-required behavior only.
- Align developer and CI expectations so Python workflows assume Rust bindings are always present.

## Capabilities

### New Capabilities
- `rust-mandatory-python-runtime`: Define and enforce Rust-required behavior across Python entry points, integration adapters, and runtime checks.
- `rust-only-python-test-contract`: Define test-suite requirements that validate Rust-mandatory behavior and remove fallback-mode expectations.

### Modified Capabilities
- None.

## Impact

- Affected code: `ClassicLib/integration/`, Python scanner/runtime entry points, Rust wrapper modules, and Python tests that currently cover fallback logic.
- Affected behavior: running Python components without Rust bindings is no longer supported and will error immediately.
- Affected CI/developer workflow: test and local run flows must build/install Rust bindings before Python execution.
