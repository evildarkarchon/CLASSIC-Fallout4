# CLI and TUI architecture

This document describes the maintained command-line frontends in the repo-root workspace. The native CLI and Rust TUI are separate thin interfaces over the same Rust business-logic crates.

## Maintained applications

| Application | Location | Interface stack | Rust integration |
|---|---|---|---|
| Native CLI | `classic-cli/` | C++20, CLI11 | `classic-cpp-bridge` CXX static bridge |
| Terminal UI | `ui-applications/classic-tui/` | Rust, Ratatui, Crossterm | Direct `-core` crate dependencies |

The native CLI is the supported non-interactive scanner. The TUI is a native Rust interactive frontend. Neither frontend calls PyO3 or Node bindings.

## Shared architecture rules

- Business logic, validation, persistence, and state transitions live in Rust `-core` crates.
- `classic-cli/` packages arguments, typed settings facts, progress, and output around CXX bridge APIs.
- `classic-tui/` packages input, screens, widgets, and messages around direct Rust core APIs.
- Async Rust work uses the shared runtime from `classic-shared-core`; frontends do not create independent Tokio runtimes.
- User Settings source discovery, schema interpretation, defaults, serialization, previews, and commits belong exclusively to `classic-user-settings-core`.
- Generic YAML data and cache helpers in `classic-config-core` and `classic_shared_core::yaml` are not User Settings APIs.

## Native CLI flow

The native CLI is rooted at `classic-cli/src/main.cpp`. CLI11 parsing in `cli_args.cpp` produces explicit command options, and `scanner.cpp` coordinates scan requests through CXX.

The CLI launches every scan through Crash Log Scan Launch (`scan_run_launch_standard` / `scan_run_launch_targeted`, ADR-0009). `scan_run_cli.cpp` maps the documented flags onto per-run overrides and nothing more:

| Flag | Override |
|---|---|
| `--game`, `--game-version`, `--scan-path` | explicit value wins |
| `--max-concurrent` | explicit value wins; `0` is the adaptive-concurrency override |
| `--show-fid-values`, `--simplify-logs`, `--fcx-mode` | turn the option on for this run |

Rust reads saved User Settings read-only, applies the game-differs rule, and builds the request and its FCX setup context; the CLI keeps no settings-merge logic and no game-name table. A Standard scan looks for Crash Logs under the Installation Root (located by `installation_root.cpp`), never under the current working directory; `--scan-path` is the explicit way to scan elsewhere. Launch diagnostics are printed from their Rust-rendered Display Content lines.

`--unsolved-logs-destination` and `--reset-unsolved-logs-destination` stay an explicit User Settings preview/commit action in `user_settings_action.cpp`, run before the launch so the scan reads the saved destination. The CLI never interprets raw `CLASSIC_Settings` paths and never bootstraps from `CLASSIC_Info.default_settings`.

The scanner executes the launched request with `scan_run_contract_execute(...)` once. Rust owns Crash Log discovery, effective-concurrency selection, run-scoped FCX setup, analysis, Autoscan Report persistence, Unsolved Logs finalization, and discovery-order terminal results. The CLI owns only event/result presentation and a scoped Ctrl+C monitor that requests cooperative cancellation through the opaque run control.

## Rust TUI flow

The TUI entry point is `ui-applications/classic-tui/src/main.rs`, with application state and transitions in `src/app.rs` and rendering/input code under `src/tabs/` and `src/widgets/`.

The TUI opens `classic_user_settings_core::UserSettings` directly. It reads typed Crash Log Scan, Game Setup, and frontend-state projections and uses explicit preview/commit operations for accepted mutations. Legacy TUI state import is also an explicit, reviewable core operation.

Scan and game-setup work is delegated directly to Rust business-logic crates. UI code owns presentation state only; it does not duplicate settings parsing or scan rules.

## User Settings precedence

For both frontends, effective values follow this order:

1. Rust-published defaults or safety fallbacks.
2. Valid typed values from the selected User Settings document.
3. Explicit options from the current CLI or TUI action.

Malformed, incompatible, or migration-required documents remain observable through typed classifications and diagnostics. Frontends must not silently rewrite them.

## Build and test

Run native C++ builds and tests only through the repository wrappers:

```powershell
./classic-cli/build_cli.ps1 -Test
./classic-gui/build_gui.ps1 -Test
```

Run the Rust TUI and its core dependencies through the root workspace:

```powershell
$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"
cargo test --workspace --all-features
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

The CLI wrapper also runs its integration scenarios. Do not invoke C++ test executables or raw `ctest` directly.

## Adding behavior

- Add new business behavior to the appropriate Rust core crate first.
- Update every applicable binding contract when a public core API changes.
- Keep CLI/TUI changes limited to argument or input handling, explicit fact projection, presentation, and invocation.
- Use typed `classic-user-settings-core` projections and transactions for every User Settings read or write.
- Update the affected pages under `docs/api/` when a public or binding-facing contract changes.
