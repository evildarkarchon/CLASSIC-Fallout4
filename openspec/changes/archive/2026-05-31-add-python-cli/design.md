## Context

The Python binding tree currently exists as a uv-managed tooling project under `python-bindings/` with `package = false`; it builds and tests PyO3 extension crates but does not expose an installable product CLI. Existing parity, stub, and compliance tools already provide source-level and runtime checks, while the proposed CLI adds a human and CI-facing workflow surface that exercises the maintained public `classic_*` modules through command handlers.

The CLI must stay within CLASSIC architecture rules: Rust owns business logic, Python owns command routing, output formatting, process exit normalization, fixture selection, and binding-boundary diagnostics. The initial implementation uses Python 3.12+ and stdlib `argparse`, runs inside `python-bindings/.venv`, and assumes PyO3 wheels are rebuilt before runtime validation.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated `classic-py` console script and `python -m classic_py_cli` entry point without turning the existing `python-bindings` tooling project into a packaged product.
- Keep command handlers thin and visibly backed by public `classic_*` Python binding modules.
- Produce stable text and JSON output, report artifacts, and exit codes suitable for local troubleshooting and CI.
- Add binding diagnostics, smoke coverage, compliance scenario listing/running, and selected product commands from the PRD.
- Reuse existing parity, stub validation, runtime coverage, and binding compliance tooling where source-level checks are needed.

**Non-Goals:**
- Replacing the native C++ `classic-cli`, GUI, TUI, or canonical lower-level compliance gates.
- Reimplementing scan, config, path, database, update, or version behavior in Python.
- Adding a separate Rust/Tokio runtime, daemon behavior, file watch mode, or network-dependent default smoke checks.
- Publishing to PyPI or producing native binary packages as part of the first implementation.

## Decisions

1. Create a dedicated local CLI package under `python-bindings/`.

   The package should own `classic_py_cli` sources and entry point metadata while the existing `python-bindings/pyproject.toml` remains the uv/maturin tooling project. This avoids disturbing `package = false`, maturin wheel installation, and current pytest workflows. An editable/local dependency can expose `classic-py` to `uv run --project python-bindings`.

   Alternative considered: convert `python-bindings/pyproject.toml` into the product package. That would couple CLI packaging to the binding build harness and increase the risk of uv pruning or installing the wrong project shape during PyO3 validation.

2. Use stdlib `argparse` and small internal modules instead of a richer CLI framework.

   The PRD resolves the CLI framework question in favor of `argparse`. This keeps dependencies minimal, avoids adding packaging churn to the binding environment, and is sufficient for the required subcommand tree, global options, and process-level tests.

   Alternative considered: use Typer/Click/Rich. Those would improve ergonomics but add dependency and rendering contracts before the CLI behavior is stable.

3. Use a thin command-handler architecture with shared context, output, binding loading, scenario catalog, and exit status modules.

   Command handlers should mostly parse command-specific arguments, request a binding module from `binding_loader`, call public binding APIs, and return a result envelope. Shared modules own repo-root discovery, fixture roots, JSON/text rendering, report artifact writing, import diagnostics, and exception-to-exit-code mapping.

   Alternative considered: one large CLI file. That would be faster initially but makes compliance scenarios, process tests, and hidden business-logic review harder.

4. Treat the scenario catalog as product data.

   Scenario metadata should record stable IDs, owner modules, covered exports, command invocation, fixture requirements, expected status, blocking profiles, and failure classification hints. The same catalog powers `compliance list`, `compliance explain`, `compliance run`, report generation, and coverage-oriented tests.

   Alternative considered: encode scenarios only as pytest cases. That would not provide discoverable CLI output or report metadata for maintainers and CI.

5. Preserve existing compliance tools as delegated gates.

   `compliance run --profile smoke` should execute CLI scenarios directly. `python-ci` and `full` profiles may delegate to `tools/python_api_parity/check_parity_gate.py`, `validate_stubs.py`, and `tools/binding_compliance/check_compliance.py` where appropriate, then add CLI scenario evidence and structured reports.

   Alternative considered: rewrite parity/stub/compliance checks inside the CLI. That would duplicate canonical policy and risk divergent failure classification.

6. Keep stdout clean for machine-readable output.

   When `--json` is set, the primary JSON envelope goes to stdout and all progress, diagnostics, and human hints go to stderr. Report files are written only through explicit output/report options or compliance profile artifact paths.

   Alternative considered: mixed progress and JSON stdout. That would make CI parsing fragile and violate the PRD output contract.

## Risks / Trade-offs

- CLI package installation conflicts with maturin-built wheels -> Keep the CLI package separate and validate invocation through `uv run --project python-bindings classic-py`; document that `uv sync --inexact` remains required.
- Command handlers accidentally grow business logic -> Add tests that monkeypatch/fake binding modules and assert commands route through the binding boundary; keep behavior-specific logic in Rust bindings.
- Missing PyO3 wheels look like product failures -> `doctor`, binding import diagnostics, and exit code `3` classify missing builds before scenarios run.
- Compliance profiles duplicate existing gates -> Delegate source-level checks and reserve CLI scenarios for product-shaped runtime evidence.
- JSON/report schemas drift -> Include `schemaVersion`, snapshot representative envelopes/reports, and test that stderr progress does not corrupt JSON stdout.
- Scan/game workflows can be fixture-heavy -> Start with deterministic sample logs and fixture-backed smoke scenarios; keep network and environment-dependent checks out of the default smoke profile.

## Migration Plan

1. Add the dedicated CLI package and expose `classic-py` in the existing uv-managed environment.
2. Implement foundation modules, `doctor`, `bindings list`, and output/exit contracts with process-level tests.
3. Add scenario catalog, `bindings smoke`, `compliance list`, and smoke compliance reports.
4. Add product workflow commands in phases, prioritizing deterministic config/path/version/file workflows before scan/game workflows.
5. Wire `python-ci` profile delegation and update CI/docs after the smoke profile is stable.

Rollback is straightforward before external publishing: remove the local CLI package dependency/entry point and delete the new package/tests/docs without changing Rust binding APIs.

## Open Questions

- Which exact subset of `sample_logs/FO4` becomes the first stable scanlog scenario fixture set?
- Should optional JUnit output be implemented with a minimal local XML writer first, or deferred until JSON/Markdown reports stabilize?
- Should `python-ci` initially run in the existing `ci-python-bindings.yml` only, or also add a separate workflow once the CLI report shape is stable?
