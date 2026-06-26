## Why

The Qt GUI Settings dialog adds additional FormID databases one file at a time: `onAddFormIdDb()` in `classic-gui/src/app/settingsdialog.cpp:587` opens a single-select `QFileDialog::getOpenFileName`. Adding several databases means reopening the dialog repeatedly. The per-game storage (`CLASSIC_Settings.FormID Databases.<game>`, a list of paths) already supports multiple entries, and the original configurable-databases design (`docs/plans/2026-02-08-configurable-formid-databases-design.md:50`) specified `getOpenFileNames()` multi-select — the shipped C++ GUI diverged from that intent. Multi-select makes batch additions a single action.

## What Changes

- The "Add..." FormID Database dialog becomes multi-select: switch `QFileDialog::getOpenFileName` to `QFileDialog::getOpenFileNames` in `SettingsDialog::onAddFormIdDb()`, returning a `QStringList`, and append every selected file to `m_listFormIdDbs`.
- Skip files already present in the list (compared by normalized path) so a multi-select that includes an already-listed database does not create duplicate entries; this matches the duplicate-handling row of the configurable-databases design and avoids redundant pool loads.
- Dialog title changes from the singular "Select FormID Database" to the plural "Select FormID Databases".
- No change to storage format, load (`loadSettings`), save (`saveSettings`), reset, or the `Additional FormID Databases` UI layout; the list widget already persists N entries.

## Capabilities

### New Capabilities
- `formid-database-settings`: User management of additional FormID databases from the GUI Settings dialog — list display, multi-file add, remove, and per-game persistence in `CLASSIC Settings.yaml`.

### Modified Capabilities
<!-- None: no existing spec covers the FormID database settings dialog. -->

## Impact

- **C++ GUI:** `classic-gui/src/app/settingsdialog.cpp` (`onAddFormIdDb()` only); `settingsdialog.h` is unchanged (no new slot/members).
- **GUI tests:** add a source-inspection test to `classic-gui/tests/test_scan_settings_wiring.cpp` asserting multi-select (`getOpenFileNames`), per-file appending, and duplicate skipping. No `CMakeLists.txt` change (reuses the existing `classic-gui-test-scan-settings-wiring` target).
- **No Rust core / bridge / binding changes:** `ClassicConfig.formid_databases`, the CXX bridge orchestrator (`cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator.rs`), Python, and Node surfaces are untouched — the YAML contract and pool initialization are unchanged.
- **No public API contract or `docs/api/` changes.**
- No new dependencies. Additive UI behavior; not a breaking change.
