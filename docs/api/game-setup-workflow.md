# Game Setup Intake Workflow

Contributor-facing workflow notes for setup and install validation across:

- [`classic-path-core`](../../business-logic/classic-path-core)
- [`classic-xse-core`](../../business-logic/classic-xse-core)
- [`classic-scangame-core`](../../business-logic/classic-scangame-core)
- [`classic-version-registry-core`](../../business-logic/classic-version-registry-core)
- [`classic-version-core`](../../business-logic/classic-version-core)

This page documents the current source-backed Game Setup Intake contract.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Game Setup Intake prepares a supported game install for setup validation. The workflow resolves saved or detected paths, selects or detects the game version, looks up Version Registry expectations, and returns typed setup diagnostics plus a Rust-rendered report.

It is intentionally setup-only. It does not run Crash Log analysis, ENB checks, crashgen TOML checks, Wrye parsing, loose-file scans, BA2 scans, or mod INI scans.

Use this workflow when you need to understand:

- game-root and documents-root detection
- executable version and hash checks
- setup-time Version Registry metadata
- documents-folder readiness checks
- XSE loader/version, Address Library, and script-hash setup diagnostics
- path updates callers may choose to persist later

For crate-by-crate API details, see:

- [`classic-path-core.md`](classic-path-core.md)
- [`classic-xse-core.md`](classic-xse-core.md)
- [`classic-scangame-core.md`](classic-scangame-core.md)
- [`classic-version-registry-core.md`](classic-version-registry-core.md)
- [`classic-version-core.md`](classic-version-core.md)

---

## Owning API

`classic-scangame-core::GameSetupIntake` is the top-level Rust entry point.

Important public items:

- `GameSetupIntake::new(game_id, selected_game_version)`
- `GameSetupIntake::from_config(config, game_id)`
- `with_game_root(path)`
- `with_docs_root(path)`
- `with_xse_log_path(path)`
- `run() -> GameSetupIntakeResult`
- `normalize_game_setup_version_selection(value)`
- `game_setup_needs_path_detection(game_path, docs_path)`

`GameSetupIntakeResult` contains:

- `rendered_report`
- `status: GameSetupIntakeStatus`
- `paths: GameSetupResolvedPaths`
- `path_updates: Vec<GameSetupPathUpdate>`
- `version: GameSetupVersionFacts`
- `checks: Vec<GameSetupCheck>`
- `actions: Vec<GameSetupRequiredAction>`

The top-level status is `ActionRequired` only when the caller needs user input before all relevant checks can run. Failed setup diagnostics are represented by typed `GameSetupCheck` values and `has_errors()`.

---

## Current Cross-Crate Flow

## 1. Cheap Missing-Path Gate

If a caller only needs to know whether saved path settings are missing, call:

```rust
classic_scangame_core::game_setup_needs_path_detection(game_path, docs_path)
```

This helper treats missing or blank strings as missing. It does not validate or resolve paths.

## 2. Build Intake

Callers provide the facts they already have:

```rust
use classic_scangame_core::GameSetupIntake;
use classic_shared_core::GameId;

let intake = GameSetupIntake::new(GameId::Fallout4, "auto")
    .with_game_root(r"C:\Games\Fallout 4")
    .with_docs_root(r"C:\Users\Name\Documents\My Games\Fallout4");
```

All fields are read-only inputs. Running intake may return proposed `GameSetupPathUpdate` values, but it never persists them.

## 3. Resolve Paths

Game Setup Intake delegates path discovery to `classic-path-core`:

- `GamePathFinder` resolves the game root and executable path.
- `DocsPathFinder` resolves the documents root.

The intake uses game-root detection without requiring the XSE loader. Missing loaders are reported as XSE diagnostics, not as path detection failures.

## 4. Resolve Version Context

The intake normalizes the selected version with `normalize_game_setup_version_selection()`.

Supported selections are:

- `auto`
- `Original`
- `NextGen`
- `AnniversaryEdition`
- `VR`

When the selection is `auto`, the intake reads executable PE version metadata through `classic-version-core` and attempts a Version Registry match. If the executable exists but no supported registry entry matches, the result asks the caller to collect `ChooseGameVersion`.

## 5. Read Version Registry Expectations

For supported registry metadata, the intake uses `classic-version-registry-core` to obtain:

- display/version metadata
- executable hash expectations
- documents folder metadata
- Steam app metadata for documents discovery where available
- XSE metadata, including loader, compatible version, Address Library, and script hashes

When curated registry data is not available for a `GameId`, the result contains `Unsupported` diagnostics instead of pretending the check passed.

## 6. Run Setup Diagnostics

The intake returns typed checks for:

- game path
- documents path
- registry metadata
- executable version
- executable hash
- installation location
- documents folder
- XSE loader
- XSE version
- Address Library
- XSE script hashes

These checks use `Passed`, `Failed`, `Warning`, `Skipped`, `Unsupported`, or `ActionRequired` states. Adapters should prefer the typed states for UI logic and use `rendered_report` for plain-text display.

---

## Flow Sketch

```text
saved settings / frontend inputs
        |
        +--> classic-scangame-core::GameSetupIntake
                  |
                  +--> classic-path-core
                  |         - game root
                  |         - documents root
                  |
                  +--> classic-version-core
                  |         - executable PE version
                  |
                  +--> classic-version-registry-core
                  |         - version match
                  |         - executable hash expectations
                  |         - XSE metadata
                  |
                  +--> classic-xse-core
                            - loader installed?
                            - detected XSE version?
        |
        +--> GameSetupIntakeResult
                  - typed checks
                  - required actions
                  - path updates
                  - rendered report
```

---

## Adapter Surfaces

Current binding surfaces should stay thin:

- C++ bridge: `classic::scangame::run_game_setup_intake(...)`, `game_setup_intake_checks(...)`, and `game_setup_needs_path_detection(...)`
- Node binding: `runGameSetupIntake(...)`, `normalizeGameSetupVersionSelection(...)`, and `gameSetupNeedsPathDetection(...)`
- Python binding: `GameSetupIntake`, `run_game_setup_intake(...)`, `normalize_game_setup_version_selection(...)`, and `game_setup_needs_path_detection(...)`

Adapters should not rebuild executable-hash, XSE, Address Library, or documents logic locally. If a setup diagnostic needs to change, change `classic-scangame-core::game_setup_intake`.

---

## Contributor Debugging Checklist

When setup validation behaves unexpectedly, debug in this order:

1. confirm the caller is using Game Setup Intake rather than a broader game-file scan
2. inspect the intake inputs: `GameId`, selected version, game root, docs root, and XSE log path
3. check whether the issue is missing user input (`actions`) or a failed diagnostic (`checks`)
4. inspect `version` facts to see whether registry matching selected the expected entry
5. verify whether a check is `Unsupported` because curated registry metadata is not available for that game
6. inspect adapter code only after the Rust result looks correct

Source files most often involved:

- [`business-logic/classic-scangame-core/src/game_setup_intake.rs`](../../business-logic/classic-scangame-core/src/game_setup_intake.rs)
- [`cpp-bindings/classic-cpp-bridge/src/scangame.rs`](../../cpp-bindings/classic-cpp-bridge/src/scangame.rs)
- [`node-bindings/classic-node/src/scangame.rs`](../../node-bindings/classic-node/src/scangame.rs)
- [`python-bindings/classic-scangame-py/src/setup.rs`](../../python-bindings/classic-scangame-py/src/setup.rs)
