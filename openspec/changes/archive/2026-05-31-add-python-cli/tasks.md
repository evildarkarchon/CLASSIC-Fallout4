## 1. Package And Entrypoints

- [x] 1.1 Add a dedicated local CLI package under `python-bindings/` with `classic_py_cli` sources and package metadata for the `classic-py` console script.
- [x] 1.2 Wire the local CLI package into the existing `python-bindings` uv project without converting the tooling project away from `package = false`.
- [x] 1.3 Add `classic_py_cli.__main__` so `uv run --project python-bindings python -m classic_py_cli --help` uses the same application entry point.
- [x] 1.4 Add initial process-level tests for `classic-py --help` and `python -m classic_py_cli --help`.

## 2. CLI Foundation

- [x] 2.1 Implement stdlib `argparse` parser construction with global options for JSON output, output path, repo root, fixture root, no color, verbose diagnostics, and tracebacks.
- [x] 2.2 Implement command context resolution for repo root, fixture root, output mode, verbosity, and trace behavior.
- [x] 2.3 Implement output envelope helpers for success, failure, artifacts, text rendering, JSON rendering, and stderr diagnostics.
- [x] 2.4 Implement exit-status mapping for success, product/compliance failure, usage/configuration failure, binding import/build failure, and interruption.
- [x] 2.5 Add unit tests for parser routing, output envelopes, stderr/stdout separation, and exit-status mapping.

## 3. Binding Loader And Doctor

- [x] 3.1 Implement `binding_loader` with the expected maintained `classic_*` module inventory and structured import diagnostics.
- [x] 3.2 Implement `classic-py bindings list` with text and JSON output including import status and discoverable public-surface metadata.
- [x] 3.3 Implement `classic-py doctor` checks for uv environment shape, rebuilt PyO3 wheel importability, repo paths, fixture paths, and required tooling.
- [x] 3.4 Add tests that simulate available bindings, missing bindings, stale import failures, and JSON diagnostic output.

## 4. Scenario Catalog And Smoke Commands

- [x] 4.1 Define a data-backed scenario catalog with stable IDs, owner modules, covered exports, command invocations, fixture requirements, expected exit codes, profiles, and failure classification hints.
- [x] 4.2 Implement `classic-py compliance list` using the catalog with text and JSON output.
- [x] 4.3 Implement `classic-py compliance explain <id>` using the catalog metadata.
- [x] 4.4 Implement `classic-py bindings smoke` for cheap representative imports and calls where deterministic binding APIs are available.
- [x] 4.5 Add catalog validation tests that ensure each scenario has owner, covered exports, expected status, profile membership, and fixture metadata.

## 5. Compliance Runner And Reports

- [x] 5.1 Implement `classic-py compliance run --profile smoke` using the same command handlers exercised by user-facing commands.
- [x] 5.2 Implement focused `surface:<name>` profile selection from scenario catalog ownership metadata.
- [x] 5.3 Generate `classic_python_cli_report.json` with profile, environment summary, scenario results, covered exports, artifacts, command lines, exit codes, and failure classifications.
- [x] 5.4 Generate `classic_python_cli_report.md` from the same report data.
- [x] 5.5 Add delegated `python-ci` profile hooks for existing parity, stub validation, runtime coverage, or canonical binding compliance tooling where required.
- [x] 5.6 Add process-level tests for smoke profile results, report files, failure classification fields, and JSON stdout cleanliness.

## 6. Product Workflow Commands

- [x] 6.1 Implement deterministic utility commands for version parsing, config main-version/inspection, path validation, and file hashing through public bindings.
- [x] 6.2 Implement initial database, XSE, update, and resource command stubs or handlers only where deterministic binding-backed behavior is available.
- [x] 6.3 Implement `classic-py scan logs` with explicit scan path/fixture support, binding-backed scan execution, summary output, artifact reporting, and stable exit semantics.
- [x] 6.4 Implement `classic-py scan game` with binding-backed game setup checks and structured findings where fixtures can make behavior deterministic.
- [x] 6.5 Add fixture-backed integration tests for representative utility and scan commands.

## 7. Documentation And CI

- [x] 7.1 Document local setup with `uv sync --project python-bindings --inexact`, `PYO3_PYTHON`, `rebuild_rust.ps1 -Target python`, and `classic-py` examples.
- [x] 7.2 Document command groups, JSON envelopes, report artifacts, exit codes, and failure classifications.
- [x] 7.3 Update Python binding CI or add transitional CI coverage for `classic-py doctor`, `bindings list --json`, and `compliance run --profile smoke` after rebuilt wheels are installed.
- [x] 7.4 Record any intentionally deferred product commands, live-network behavior, JUnit report output, or fixture limitations in docs.

## 8. Validation

- [x] 8.1 Run `uv sync --project python-bindings --inexact` before Python binding validation.
- [x] 8.2 Set `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` before PyO3-touching validation.
- [x] 8.3 Run `uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .`.
- [x] 8.4 Run `uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings`.
- [x] 8.5 Run `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python`.
- [x] 8.6 Run `uv run --project python-bindings python -m pytest python-bindings/tests -q`.
- [x] 8.7 Run `uv run --project python-bindings classic-py doctor` and `uv run --project python-bindings classic-py compliance run --profile smoke`.
- [x] 8.8 Run `uv run --project python-bindings python tools/binding_compliance/check_compliance.py --repo-root . --profile python-ci` after the CLI profile delegates to canonical compliance tooling.
