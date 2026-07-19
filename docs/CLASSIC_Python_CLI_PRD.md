# CLASSIC Python CLI - Product Requirements Document

**Version:** 1.0  
**Date:** 2026-05-31  
**Status:** Draft  
**Target Runtime:** Python 3.12+  
**Target Command:** `classic-py`

---

## 1. Executive Summary

### 1.1 Purpose

This document specifies a fully featured Python command-line application for CLASSIC, built on the maintained Rust-backed Python bindings. The primary internal use case is binding compliance testing: the CLI should exercise the Python binding surface through real workflows, stable exit codes, and machine-readable reports. It must still be treated as a standalone product rather than a thin pytest or parity-script wrapper.

The CLI should let contributors and automation run meaningful CLASSIC operations from Python: inspect configuration, resolve paths, scan crash logs, run game setup checks, query version metadata, validate binding health, and produce compliance evidence. All product behavior must come from the Python bindings, which in turn delegate to Rust core logic.

### 1.2 Goals

- Provide a polished, documented Python CLI that can be used directly by humans and CI.
- Exercise the maintained Python binding modules through realistic product workflows.
- Make binding compliance failures easy to reproduce, classify, and explain.
- Preserve CLASSIC architecture rules: Rust owns business logic; Python owns CLI orchestration, argument parsing, output formatting, and binding boundary validation.
- Produce stable text, JSON, Markdown, and optional CI-friendly reports without relying on fragile console scraping.
- Support Windows-first local development while keeping source-level checks usable in CI and cloud runners where possible.

### 1.3 Non-Goals

- Replacing the native C++ `classic-cli`.
- Replacing the binding compliance suite or lower-level parity gates.
- Reimplementing scan, config, path, database, update, or version behavior in Python.
- Standardizing C++, Node, and Python error shapes.
- Adding GUI, TUI, daemon, web server, or long-running watch mode behavior.
- Publishing external packages before the in-repo product and compliance workflows are stable.

---

## 2. Current State

### 2.1 Python Binding Surface

The maintained Python bindings are split across per-module PyO3 extension crates under `python-bindings/`:

| Module Area | Binding Crates |
| --- | --- |
| Configuration and settings | `classic-config-py`, `classic-settings-py` |
| Scanning | `classic-scanlog-py`, `classic-scangame-py` |
| Data and file operations | `classic-database-py`, `classic-file-io-py`, `classic-resource-py` |
| Runtime and utilities | `classic-message-py`, `classic-path-py`, `classic-perf-py`, `classic-registry-py`, `classic-web-py`, `classic-xse-py` |
| Versioning and update flow | `classic-version-py`, `classic-version-registry-py`, `classic-update-py` |

The Python project is currently a tooling project. `python-bindings/pyproject.toml` manages `maturin` and `pytest` through uv and explicitly sets `package = false`.

### 2.2 Existing Compliance Tooling

The repository already has strong compliance infrastructure:

- Canonical umbrella suite: `tools/binding_compliance/check_compliance.py`
- Python parity gate: `tools/python_api_parity/check_parity_gate.py`
- Stub validation: `validate_stubs.py`
- Runtime coverage registry: `python-bindings/tests/fixtures/runtime_coverage_registry.json`
- Generated Python parity artifacts: `python-bindings/parity-artifacts/`

The new CLI must reuse and complement this tooling. It should not weaken, bypass, or duplicate the canonical gates. Its value is that it turns binding verification into product-shaped workflows that can be run manually, scripted in CI, and used as regression evidence.

### 2.3 Local Setup And Invocation

The in-repo implementation lives in `python-bindings/classic-py-cli/` as a dedicated local package. The parent `python-bindings/pyproject.toml` remains a uv tooling project with `package = false`; it exposes the CLI through an editable path dependency so the console script is available after the usual binding setup.

Typical local workflow from the repository root:

```powershell
uv sync --project python-bindings --inexact
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings classic-py --help
uv run --project python-bindings python -m classic_py_cli --help
```

`--inexact` remains required so uv does not prune the maturin-built `classic-*-py` wheels from `python-bindings/.venv` during repeated local syncs.

---

## 3. Product Principles

1. **Bindings-first behavior.** Every command that performs CLASSIC behavior must load and call the public Python binding modules. Calling Rust tools, private source parsers, or lower-level Python scripts is only allowed for explicit diagnostic/compliance commands that document that delegation.

2. **Compliance through real use.** Compliance scenarios should call the same command handlers that users call. A command that only exists to make tests pass is a product smell.

3. **Thin Python boundary.** Python may parse arguments, resolve fixture paths, format output, normalize CLI exit status, and route binding exceptions. It must not recreate business rules owned by Rust core crates.

4. **Stable automation surface.** JSON schemas, exit codes, and artifact filenames are part of the product contract.

5. **Useful without CI.** A contributor should be able to run the CLI locally to understand what is broken before opening logs or generated reports.

6. **Diagnostics are explicit.** Environment, stale build, missing wheel, stale artifact, and true binding compliance failures must be separated in output.

---

## 4. Users And Use Cases

### 4.1 Binding Maintainer

Runs a Python CLI compliance profile after changing a Rust API or Python wrapper. Needs a concise failure summary, exact failing command, generated artifacts, and clear classification of whether the problem is parity drift, stale stubs, missing runtime coverage, or local environment setup.

### 4.2 Contributor

Uses the CLI to reproduce a CI binding failure locally. Needs discoverable help, actionable `doctor` output, and focused commands for one module or scenario.

### 4.3 Automation

Runs the CLI in CI to produce JSON, Markdown, and optional JUnit-style output. Needs stable exit codes and reports that do not depend on terminal color or progress text.

### 4.4 Power User Or Modding Tool Author

Uses the CLI as a standalone way to scan logs, inspect game/version metadata, validate paths, query FormID databases, or check updates without launching a GUI.

---

## 5. Scope

### 5.1 In Scope

- A Python package and console script for a command named `classic-py`.
- A module entry point: `python -m classic_py_cli`.
- Human-readable default output plus `--json` for machine-readable output.
- Product command groups backed by Python bindings.
- Binding health and compliance command groups.
- Stable exit codes.
- Generated run artifacts for compliance profiles.
- Documentation for local setup, rebuild requirements, command examples, and CI use.
- Tests that invoke the CLI as a process, not only internal functions.

### 5.2 Out Of Scope

- Native binary packaging.
- External PyPI publishing.
- Replacing `classic-cli`, `classic-gui`, or `classic-tui`.
- Network-dependent checks in the default smoke profile.
- Long-lived background services or file watchers.
- Interactive prompts in CI-oriented commands.

---

## 6. Architecture Overview

### 6.1 Proposed Layers

```
CLASSIC Python CLI
  |
  |-- Command Layer
  |     Argument parsing, subcommand routing, help text, exit status
  |
  |-- Output Layer
  |     Text, JSON, Markdown, progress, errors, CI reports
  |
  |-- Binding Service Layer
  |     Thin facades over classic_* PyO3 modules
  |
  |-- Compliance Scenario Runner
  |     Scenario catalog, profiles, fixture setup, report generation
  |
  |-- Environment Resolver
  |     Binding import checks, venv/build diagnostics, repo path discovery
  |
  `-- Python Binding Modules
        classic_config, classic_scanlog, classic_scangame, ...
```

### 6.2 Deep Modules

The implementation should extract a few stable modules with small interfaces:

| Module | Responsibility |
| --- | --- |
| `binding_loader` | Imports binding modules, captures import errors, reports module versions/capabilities. |
| `output` | Owns output schemas, text rendering, progress routing, and error envelopes. |
| `scenario_catalog` | Maps compliance scenarios to commands, fixtures, expected status, and covered binding exports. |
| `command_context` | Carries repo root, output mode, verbosity, fixture roots, and environment diagnostics. |
| `exit_status` | Converts product outcomes and exceptions into stable CLI process codes. |

These modules keep command implementations narrow and make compliance tests easier to reason about.

### 6.3 Runtime And Dependency Rules

- The CLI must not create an independent Rust/Tokio runtime. Binding crates use the shared Rust runtime facilities.
- Long-running or blocking behavior should be called through binding APIs that already release the GIL where appropriate.
- The first implementation should minimize Python package dependencies. If a richer CLI framework or terminal renderer is desired, it should be a deliberate product dependency with CI coverage.
- The CLI must use `python-bindings/.venv` for in-repo validation workflows and must assume the PyO3 wheels have been rebuilt before runtime tests.

---

## 7. Command Surface

### 7.1 Global Options

| Option | Behavior |
| --- | --- |
| `--json` | Write the primary result as JSON to stdout. |
| `--output <path>` | Write JSON or Markdown report output to a file. |
| `--repo-root <path>` | Override automatic repository root discovery. |
| `--fixture-root <path>` | Use a fixture tree for scan/compliance scenarios. |
| `--no-color` | Disable terminal color. |
| `--verbose` | Include diagnostic details. |
| `--trace` | Include Python traceback and binding exception details on failure. |

Progress and diagnostics should go to stderr when stdout is reserved for JSON.

The implemented flag name is `--tracebacks` to make Python-boundary behavior explicit. The CLI accepts global options before or after subcommands, so both `classic-py --json bindings list` and `classic-py bindings list --json` produce one JSON envelope on stdout.

### 7.2 Core Product Commands

| Command | Purpose |
| --- | --- |
| `classic-py scan logs` | Run fail-soft crash-log scanning through `classic_scanlog` and report the complete terminal run result, including Installed YAML Data metadata and per-log failures, in structured output. |
| `classic-py scan game` | Run game setup checks through `classic_scangame` and related bindings. |
| `classic-py config inspect` | Open and summarize typed User Settings at an explicit CLASSIC root through `classic_user_settings`. |
| `classic-py config main-version` | Read the schema-gated main YAML version through the binding contract. |
| `classic-py path find-game` | Resolve a game installation path through `classic_path` and registry-aware helpers. |
| `classic-py path validate` | Validate paths through binding-backed validators. |
| `classic-py version parse` | Parse and normalize version strings through `classic_version`. |
| `classic-py version registry` | Query and match game/crashgen metadata through `classic_version_registry`. |
| `classic-py file hash` | Hash one or more files through `classic_file_io`. |
| `classic-py file collect-logs` | Discover candidate logs through `classic_file_io`. |
| `classic-py database lookup` | Query FormID data through `classic_database`. |
| `classic-py xse detect` | Detect XSE installation/version through `classic_xse`. |
| `classic-py update check` | Check release/update metadata through `classic_update`. |

### 7.3 Binding And Compliance Commands

| Command | Purpose |
| --- | --- |
| `classic-py bindings list` | List importable binding modules and public surfaces. |
| `classic-py bindings smoke` | Import every binding and run a cheap representative call where available. |
| `classic-py doctor` | Diagnose venv, missing wheels, stale rebuild, missing fixtures, and tool availability. |
| `classic-py compliance list` | List compliance scenarios and covered binding exports. |
| `classic-py compliance run` | Run a scenario profile and write structured reports. |
| `classic-py compliance explain <id>` | Explain one scenario, expected behavior, and failure classification. |
| `classic-py compliance artifacts` | Summarize current Python parity artifacts and coverage reports. |

The initial implementation writes compliance reports to `python-bindings/parity-artifacts/` by default, or to `--output <dir>` when supplied. `classic_python_cli_report.json` and `classic_python_cli_report.md` are generated from the same report data.

Live-network behavior, native binary packaging, external publishing, and JUnit XML output are intentionally deferred until the JSON and Markdown report contracts stabilize. Default smoke scenarios stay deterministic and avoid network-dependent update checks.

---

## 8. Compliance Model

### 8.1 Profiles

| Profile | Purpose |
| --- | --- |
| `smoke` | Fast local import and representative-call validation; no network and no rebuild. |
| `python-ci` | Python-focused source and runtime checks suitable for CI. |
| `full` | Local release/backstop profile including rebuilt PyO3 wheels and Python smoke tests. |
| `surface:<name>` | Focused profile for one binding owner, such as `scanlog` or `config`. |
| `changed` | Optional future profile that selects scenarios from changed files or refreshed parity metadata. |

Where possible, `python-ci` and `full` should delegate to the existing canonical compliance suite and lower-level parity tools, then enrich the result with CLI scenario evidence.

### 8.2 Scenario Catalog

Each compliance scenario must record:

- Stable scenario ID.
- Owning binding module.
- Covered public export paths.
- Command invocation.
- Fixture requirements.
- Expected exit code.
- Required stdout/stderr/report assertions.
- Failure classification hints.
- Whether the scenario is blocking for a given profile.

The catalog should live as data, not scattered test code, so it can generate help output, reports, and coverage summaries.

### 8.3 Failure Classification

The CLI should preserve the failure vocabulary already used by the binding compliance suite:

| Failure Kind | Meaning |
| --- | --- |
| `local_environment_failure` | Missing tools, missing venv, missing wheels, missing fixtures, path issues. |
| `stale_generated_artifact` | Generated binding or report artifact does not match source. |
| `stale_baseline` | Checked-in baseline needs an intentional refresh. |
| `missing_runtime_coverage` | A tracked public surface lacks runtime evidence. |
| `policy_source_contradiction` | Docs/policy and source behavior disagree. |
| `true_binding_compliance_gap` | The binding surface is genuinely missing or wrong. |

### 8.4 Reports

`classic-py compliance run` should write:

- `classic_python_cli_report.json` - complete structured report.
- `classic_python_cli_report.md` - human-readable summary.
- Optional `classic_python_cli_junit.xml` - CI annotation format.

Reports should include command lines, profile, environment summary, scenario results, covered exports, generated artifact paths, and failure classifications.

---

## 9. Exit Semantics

| Exit Code | Meaning |
| ---: | --- |
| 0 | Command succeeded. For Python CLI scans, no fatal workflow failure occurred; "no logs found" and fail-soft per-log scan failures are success with structured failure counts. |
| 1 | Command completed but found product/compliance failures for commands that define findings as process failures. Examples: failed scenarios and validation findings. |
| 2 | Usage, configuration, or startup failure before the product workflow could run. |
| 3 | Python binding import/build failure, including missing PyO3 wheels. |
| 4 | Interrupted or cancelled by the user. |

Commands must not silently return success after failing to load a required binding.

`classic-py scan logs` intentionally follows the scanlog binding's fail-soft batch contract: malformed, missing, or otherwise failed logs appear in the JSON summary as per-log failures, but a completed batch still exits `0`. Automation that wants strict CI behavior should inspect the structured failure count rather than relying on the process status.

The JSON envelope's `data.result` field is a structured projection of the final `ScanRunResult`, not a Python object representation. It preserves discovery/setup optionals, aggregate counts, complete per-log results, and optional `installedYamlData` metadata for the immutable run snapshot: selected Main/game provenance and identity, Local Ignore state and identity, and structured selection or generation diagnostics. Terminal setup and cancellation failures retain the same structured result under `data.result`.

---

## 10. Error Handling

### 10.1 User-Facing Errors

Errors should include:

- Short summary.
- Recommended next action.
- Original binding exception type when available.
- Failure classification for compliance commands.
- Traceback only when `--trace` is passed.

### 10.2 Python Binding Exceptions

Python binding modules intentionally expose typed Python exception classes. The CLI must preserve that information in JSON output:

```json
{
  "ok": false,
  "error": {
    "kind": "binding_exception",
    "module": "classic_config",
    "exceptionType": "ClassicMainYamlVersionInvalidError",
    "message": "..."
  }
}
```

The CLI should not catch typed exceptions and replace them with vague strings unless the original type is still present in structured output.

---

## 11. Output Contracts

### 11.1 Standard Success Envelope

```json
{
  "schemaVersion": 1,
  "command": "scan logs",
  "ok": true,
  "summary": {},
  "artifacts": []
}
```

### 11.2 Standard Failure Envelope

```json
{
  "schemaVersion": 1,
  "command": "compliance run",
  "ok": false,
  "exitCode": 1,
  "failureKind": "true_binding_compliance_gap",
  "error": {
    "message": "..."
  },
  "artifacts": []
}
```

### 11.3 Text Output

Default text output should be concise:

- One-line command result.
- Important counts.
- Artifact paths.
- First few actionable failures.
- "Run with --json" and "Run with --trace" hints only when useful.

---

## 12. Packaging And Invocation

### 12.1 Recommended In-Repo Shape

Create a dedicated Python package for the CLI rather than converting the current tooling project into an installable package. A separate package avoids disturbing the uv/maturin test environment while keeping the product close to the binding modules.

Recommended command names:

- Console script: `classic-py`
- Module entry point: `python -m classic_py_cli`

### 12.2 Local Developer Invocation

The expected local validation path remains:

```powershell
uv sync --project python-bindings --inexact
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings classic-py doctor
uv run --project python-bindings classic-py compliance run --profile smoke
```

`--inexact` remains required so uv does not prune maturin-built `classic-*-py` wheels.

---

## 13. Testing Requirements

### 13.1 Unit Tests

- Argument parsing and command routing.
- Output envelope generation.
- Exit-code mapping.
- Scenario catalog validation.
- Error classification.
- Binding-loader diagnostics with fake import failures.

### 13.2 Integration Tests

- Invoke `classic-py` as a subprocess through `uv run --project python-bindings`.
- Verify `doctor`, `bindings list`, and `bindings smoke`.
- Run fixture-backed commands for config, path validation, version parsing, file hashing, and selected scanlog/scangame workflows.
- Verify JSON output is valid and stable.
- Verify progress and diagnostics do not corrupt JSON stdout.

### 13.3 Compliance Tests

- `compliance list` includes every scenario with owner and covered export metadata.
- `compliance run --profile smoke` succeeds after the Python bindings are rebuilt.
- `compliance run --profile python-ci` delegates to the existing Python parity/stub/compliance checks where applicable.
- Failure tests simulate missing wheels, stale artifacts, missing runtime coverage metadata, and binding exceptions.

### 13.4 Repository Validation Commands

For changes that touch the CLI and Python binding workflows, expected validation includes:

```powershell
uv sync --project python-bindings --inexact
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
uv run --project python-bindings python tools/python_api_parity/check_parity_gate.py --repo-root .
uv run --project python-bindings python validate_stubs.py --rust-dir . --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
uv run --project python-bindings python -m pytest python-bindings/tests -q
uv run --project python-bindings classic-py compliance run --profile smoke
```

If the canonical compliance suite is wired into the CLI profile, also run:

```powershell
uv run --project python-bindings python tools/binding_compliance/check_compliance.py --repo-root . --profile python-ci
```

---

## 14. Acceptance Criteria

### 14.1 Product Acceptance

- A contributor can run `classic-py --help` and discover all major command groups.
- `classic-py doctor` clearly explains whether the Python binding environment is ready.
- `classic-py bindings list --json` reports all expected binding modules and import status.
- Product commands call public Python binding modules and fail if the required binding is unavailable.
- Scan and inspect commands produce useful text output and equivalent JSON output.
- Machine-readable output is written to stdout without progress noise.

### 14.2 Compliance Acceptance

- `classic-py compliance list --json` emits a catalog of scenarios, owners, and covered exports.
- `classic-py compliance run --profile smoke` exercises representative imports and calls across all maintained binding owner modules.
- `classic-py compliance run --profile python-ci` can produce structured evidence suitable for CI.
- Reports classify failures using the canonical compliance failure kinds.
- Missing wheels, stale artifacts, and real binding gaps are distinguishable without reading raw traceback text.

### 14.3 Architecture Acceptance

- No command reimplements CLASSIC business logic in Python.
- Command handlers are thin enough that the binding module being exercised is obvious.
- The CLI does not create a separate Rust/Tokio runtime.
- Public API changes that affect Python bindings still follow the existing parity, stub, artifact, and runtime coverage workflows.

---

## 15. Implementation Phases

### Phase 1: CLI Foundation

- Package skeleton and entry points.
- Command context, output envelopes, exit status module.
- `doctor`, `bindings list`, and import diagnostics.
- Process-level tests for help, JSON output, and basic failures.

### Phase 2: Binding Smoke Coverage

- Scenario catalog format.
- `bindings smoke`.
- `compliance list`.
- Smoke scenarios for every maintained binding owner module.
- JSON and Markdown compliance reports.

### Phase 3: Product Workflow Commands

- Config, path, version, version registry, file, database, XSE, update, and resource command groups.
- Fixture-backed integration tests.
- Error contract checks for representative typed Python exceptions.

### Phase 4: Scan Workflows

- `scan logs` with custom scan path, scan options, JSON summary, and report artifact listing.
- `scan game` with game path/mod path checks and structured findings.
- Stable exit semantics for no logs, fail-soft per-log scan failures, and fatal startup failures.

### Phase 5: Compliance Profiles

- `compliance run --profile smoke`.
- `compliance run --profile python-ci`.
- Optional JUnit output.
- Delegation to existing parity/stub/compliance gates where appropriate.
- Failure classification coverage.

### Phase 6: CI And Documentation

- CI workflow integration or extension of the Python binding workflow.
- Contributor docs and README entry.
- Examples for local development, focused troubleshooting, and release/backstop checks.

---

## 16. Risks And Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| CLI grows hidden business logic | High | Code review rule: product behavior must trace to a `classic_*` binding call. Add tests that monkeypatch bindings to prove routing. |
| Missing or stale PyO3 wheels look like product bugs | High | `doctor` and exit code 3 must identify rebuild/venv problems before scenarios run. |
| Compliance runner duplicates existing gates | Medium | Delegate to canonical tools for source-level checks and reserve CLI scenarios for binding runtime/product workflows. |
| Network-dependent commands become flaky | Medium | Keep network checks out of default smoke profile and use fixture/mockable flows for CI. |
| Packaging disrupts existing uv/maturin project | Medium | Prefer a dedicated CLI package or explicit local editable dependency instead of flipping the current tooling project into a package without a migration plan. |
| JSON schemas drift silently | Medium | Snapshot schema tests and schemaVersion fields in every report. |

---

## 17. Open Questions

1. Should the final command name be `classic-py`, `classic-python`, or `classic-bindings`? Answer: `classic-py`
2. Should the first implementation use only stdlib `argparse`, or is a richer CLI dependency acceptable? Answer: Use `argparse`
3. Should the CLI package live as a dedicated package under `python-bindings/`, or should `python-bindings/pyproject.toml` become installable? Answer: Dedicated package.
4. Should `python-ci` be owned by the existing `ci-python-bindings.yml` workflow, a new workflow, or both during transition? Answer: Both during transition 
5. Which scanlog fixture set should define the first stable end-to-end scan scenario? Answer: Subset of logs from `sample_logs/FO4`, the sample set should include both compliant and non-compliant logs.

---

*End of Document*
