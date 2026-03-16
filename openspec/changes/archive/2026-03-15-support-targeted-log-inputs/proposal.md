## Why

CLASSIC's native frontends currently assume crash logs come from the managed `Crash Logs` workflow plus one optional custom directory. That makes it awkward to inspect only a few logs, or logs stored elsewhere, unless the user first moves or copies them into those expected locations.

## What Changes

- Add targeted crash-log selection to the native frontends so users can scan explicit log files or directories without depending only on convention-based discovery.
- Add GUI drag-and-drop support for crash-log files and folders, with a visible pending-input state that makes it clear what will be scanned before the run starts.
- Add CLI path input support for one or more explicit log files or directories while preserving the current default auto-discovery workflow and `--scan-path` compatibility.
- Extend the shared Rust/C++ log collection boundary to normalize, validate, and deduplicate explicit inputs so GUI and CLI scans produce the same log set and report placement rules.
- Update tests and user-facing docs to cover arbitrary-path scanning, partial-log workflows, and invalid input handling.

## Capabilities

### New Capabilities
- `targeted-log-inputs`: Native CLASSIC frontends can scan explicitly selected crash-log files or directories from arbitrary locations in addition to the standard auto-discovery paths.

### Modified Capabilities
- None.

## Impact

- Affected code: `classic-gui/` main-window and scan-controller flow, `classic-cli/` argument parsing and scan startup, `ClassicLib-rs/business-logic/classic-file-io-core/` log collection, and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/` file-collection entry points.
- APIs/interfaces: native CLI invocation syntax, GUI scan-input behavior, and the bridge/core log-collection contract used by C++ frontends.
- Tooling/tests: CLI argument coverage, GUI/controller tests for explicit selections, Rust log-collection tests, and docs updates for `docs/guides/` plus affected `docs/api/` bridge/file-I/O pages if the public collection contract changes.
- Compatibility: default scan behavior remains available for existing users; new explicit-input paths must coexist with current `Crash Logs` and custom-folder flows without breaking report generation.
