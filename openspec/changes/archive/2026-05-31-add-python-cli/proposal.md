## Why

CLASSIC has mature Rust-backed Python bindings and compliance tooling, but no product-shaped Python CLI that exercises those bindings through realistic workflows. Adding `classic-py` gives contributors and CI a stable way to diagnose binding health, reproduce compliance failures, and run binding-backed CLASSIC operations without replacing the native C++ CLI.

## What Changes

- Add a dedicated Python CLI package with console script `classic-py` and module entry point `python -m classic_py_cli`.
- Provide stdlib `argparse` command groups for binding diagnostics, compliance profiles, and selected product workflows backed by public `classic_*` Python modules.
- Add stable output envelopes, JSON mode, report artifact generation, and process exit codes that distinguish product failures, usage/configuration failures, binding import/build failures, and interruption.
- Add a binding smoke/compliance scenario catalog that drives CLI behavior, reports, and tests instead of scattering scenario metadata across test code.
- Wire implementation and validation into existing Python binding workflows without bypassing parity, stub validation, runtime coverage, or canonical binding compliance gates.
- Document local setup, rebuild requirements, CI invocation, command examples, and report outputs.

## Capabilities

### New Capabilities
- `python-cli`: Defines the maintained Python CLI behavior for binding-backed command execution, diagnostics, compliance scenario reporting, output contracts, and validation workflows.

### Modified Capabilities

## Impact

- Affected code: new dedicated CLI package under `python-bindings/`, Python binding tests, compliance fixtures/scenario data, and documentation.
- Affected commands: `uv run --project python-bindings classic-py ...` and `uv run --project python-bindings python -m classic_py_cli ...`.
- Affected systems: Python binding local validation, CI binding workflows, generated compliance reports, and contributor troubleshooting docs.
- Dependencies: no new runtime CLI framework dependency; initial implementation uses Python stdlib `argparse` and existing uv/maturin binding environment.
