## Context

`classic-cli` and `classic-gui` both discover crash logs through the shared Rust `LogCollector` flow exposed by `classic::files::log_collector_collect_all(...)`. Today that flow combines the managed `Crash Logs` directory, the derived XSE/docs folder, and one optional custom directory, which means ad hoc logs outside those locations must be moved or copied before they can be scanned.

The requested change spans `classic-gui/`, `classic-cli/`, `ClassicLib-rs/business-logic/classic-file-io-core/`, and `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/`. It is cross-cutting because the GUI and CLI both need a new per-run input mode, but the actual path expansion, validation, and deduplication should stay in Rust so the C++ frontends remain thin wrappers.

Constraints:
- Keep shared discovery and validation logic in Rust business logic rather than duplicating it in Qt or CLI glue.
- Preserve the existing default auto-discovery flow and current `--scan-path` / Custom Scan Folder behavior when no explicit inputs are provided.
- Keep targeted selections ephemeral for the GUI so saved settings continue to represent persistent scan defaults, not one-off user actions.
- Treat bridge and Rust API changes as contributor-facing contract updates and refresh the affected `docs/api/` pages in the same implementation wave.

## Goals / Non-Goals

**Goals:**
- Add a targeted scan mode that accepts explicit crash-log files or directories for a single run.
- Support GUI drag-and-drop with visible pending-input state and a clear way to return to normal discovery.
- Support CLI file or directory path input for subset scans without breaking existing `--scan-path` automation.
- Centralize explicit-input validation, recursive folder expansion, deduplication, and rejection reporting in Rust.
- Preserve the existing batch scan pipeline and adjacent `-AUTOSCAN.md` report generation once the input list is resolved.

**Non-Goals:**
- Removing or replacing the existing managed `Crash Logs` plus custom-folder workflow.
- Persisting GUI drop selections into YAML settings.
- Expanding Node, Python, or TUI surfaces in the same change.
- Redesigning scan progress behavior beyond the new targeted-input state needed to start a run.

## Decisions

1. **Add a targeted-input mode beside the existing discovery workflow**
   - Decision: Any explicit GUI selection or CLI positional path input activates a targeted mode for that run. In targeted mode, CLASSIC scans only the logs resolved from those explicit inputs and does not widen the run with managed `Crash Logs`, XSE/docs, or persisted custom-folder discovery.
   - Rationale: The user goal is to scan only a chosen subset of logs, including logs stored outside the assumed directories.
   - Alternatives considered:
     - Union explicit inputs with default discovery: rejected because it does not guarantee subset-only scanning.
     - Replace the existing discovery path entirely: rejected because current automation and GUI settings still need the managed workflow.

2. **Resolve explicit inputs in Rust and expose them through an additive bridge API**
   - Decision: Add a dedicated targeted-input resolver in `classic-file-io-core` that accepts explicit file/directory paths, expands directories recursively for `crash-*.log`, normalizes and deduplicates results while preserving first-seen order, and returns both accepted logs and rejected inputs with reasons. Expose that through additive `classic::files` bridge entry points rather than changing the existing `log_collector_new(...)` contract.
   - Rationale: Path validation and expansion are business rules, not UI glue. Keeping them in Rust prevents drift between GUI and CLI while limiting parity churn for Node/Python surfaces that do not need the new mode yet.
   - Alternatives considered:
     - Resolve paths entirely in C++: rejected because GUI and CLI would drift and duplicate file-policy logic.
     - Change `LogCollector::new(...)` to require explicit-input support directly: rejected because it would force wider constructor churn across other bindings.

3. **Use positional CLI paths for targeted scans and keep `--scan-path` as the legacy directory override**
   - Decision: Extend `classic-cli` to accept optional positional input paths (`classic-cli [OPTIONS] [INPUT_PATHS...]`). Positional paths may be files or directories. `--scan-path` remains supported for the existing directory-based override when no positional paths are present, and combining `--scan-path` with positional inputs is treated as invalid invocation.
   - Rationale: File-name specification is most natural as direct path arguments, and rejecting mixed modes keeps scan scope obvious.
   - Alternatives considered:
     - Add a repeated `--input-path` flag: rejected because it is more verbose and less natural for one-off file scans.
     - Let `--scan-path` accept both files and directories: rejected because it blurs the legacy directory workflow and makes compatibility harder to reason about.

4. **Represent GUI targeted inputs as ephemeral UI state with dedicated drag-and-drop affordances**
   - Decision: Add a dedicated drag-and-drop area or list on the main options tab that captures explicit files/folders, shows the pending targeted selection, and provides a clear/reset action. That selection remains in memory until the user clears or replaces it and is passed to `ScanController` separately from the persisted Custom Scan Folder field.
   - Rationale: The GUI needs visible state so users understand what will be scanned, and that state should not overwrite their saved default folder configuration.
   - Alternatives considered:
     - Reuse the Custom Scan Folder line edit as a drop target: rejected because it only models one directory and is persisted to YAML.
     - Clear targeted inputs automatically after every scan: rejected because users may want to rerun the same subset with different scan options.

5. **Keep the existing batch scanner and in-place report generation after input resolution**
   - Decision: Once GUI or CLI has a resolved log list, the current scan worker / thread-pool pipeline stays in place. Targeted scans write `-AUTOSCAN.md` reports adjacent to the original log paths and do not copy selected logs into the managed `Crash Logs` directory first.
   - Rationale: The current scan pipeline already handles bounded parallel analysis and per-log reporting well; the change is about discovery scope, not reworking analysis execution.
   - Alternatives considered:
     - Copy targeted logs into `Crash Logs` before scanning: rejected because it reintroduces unwanted side effects and breaks the point of ad hoc scanning.
     - Build a separate targeted-only scan execution path: rejected because it would duplicate worker, summary, and report-writing behavior.

## Risks / Trade-offs

- **[Risk]** Targeted scans may point at read-only, synced, or otherwise sensitive folders where report writes fail. -> **Mitigation:** Preserve existing per-log error reporting and make it clear when analysis succeeded but report output could not be written.
- **[Risk]** Users may confuse the persistent Custom Scan Folder with the one-shot targeted selection. -> **Mitigation:** Keep them as separate UI concepts, label targeted mode clearly, and provide an explicit clear action.
- **[Risk]** New bridge DTOs expand the contributor-facing API surface. -> **Mitigation:** Keep the new resolver API additive and narrow, and update `docs/api/classic-file-io-core.md` plus `docs/api/classic-cpp-bridge-data-entrypoints.md` in the same change.
- **[Risk]** Recursive directory expansion can unexpectedly include more logs than a user intended. -> **Mitigation:** Surface the resolved log count before scan start in the GUI and print a targeted-discovery summary in the CLI.

## Migration Plan

1. Add the Rust targeted-input resolver and tests while leaving `LogCollector::collect_all()` unchanged for the default workflow.
2. Add additive `classic::files` bridge entry points and any small result DTOs needed to return resolved and rejected inputs, then refresh the affected API docs.
3. Extend `classic-cli` argument parsing and scan startup to use targeted mode when positional inputs are present, including validation for mixed `--scan-path` usage.
4. Add GUI targeted-input state, drag-and-drop handling, and `ScanController` plumbing so the Qt frontend can request targeted resolution before starting the worker.
5. Update CLI and GUI user guides, then run the relevant native C++ and Rust validation commands.

Rollback strategy:
- Remove the new targeted-input UI and CLI plumbing and fall back to the existing `collect_all()` discovery path.
- If the bridge contract proves too broad, keep the Rust resolver internal and defer the frontend integration until a narrower DTO shape is ready.

## Open Questions

- None currently; the design is implementation-ready with the decisions above.
