## 1. Shared Targeted-Input Resolution

- [x] 1.1 Add a Rust targeted-input resolver in `ClassicLib-rs/business-logic/classic-file-io-core/` that expands explicit file and directory inputs, searches directories recursively for supported crash logs, deduplicates resolved paths, and records rejected inputs with reasons.
- [x] 1.2 Add Rust tests that cover explicit files, recursive directory discovery, duplicate selections, invalid or non-matching inputs, and the unchanged default `collect_all()` behavior.

## 2. Bridge And CLI Integration

- [x] 2.1 Add additive `classic::files` bridge entry points and any small DTO wrappers needed to expose targeted-input resolution to C++ callers, and update the affected `docs/api/` pages for the new contract.
- [x] 2.2 Extend `classic-cli` argument parsing to accept positional input paths, reject mixed `--scan-path` plus positional-path usage, and switch scan startup to targeted mode when explicit inputs are present.
- [x] 2.3 Add or update CLI tests for positional inputs, legacy `--scan-path` compatibility, invalid mixed-mode invocation, and targeted scan discovery/report behavior.

## 3. GUI Targeted Scan Experience

- [x] 3.1 Add a dedicated GUI targeted-input surface with drag-and-drop support, visible pending-selection state, and a clear/reset action that does not overwrite the saved Custom Scan Folder setting.
- [x] 3.2 Update `ScanController` and related wiring so the GUI passes explicit selections through the new bridge resolver, uses targeted mode only when selections are queued, and falls back to the current discovery flow otherwise.
- [x] 3.3 Add GUI tests or wiring checks that cover drag-and-drop state, clear-to-default behavior, and the new controller parameter flow.

## 4. Docs And Validation

- [x] 4.1 Update the CLI and GUI user guides to explain targeted scans, drag-and-drop behavior, and the difference between positional input paths and `--scan-path`.
- [x] 4.2 Run the relevant Rust and native validation commands for the touched surfaces, including `cargo test` for the file-I/O and bridge changes plus the native CLI/GUI test workflows, and fix any regressions found.
