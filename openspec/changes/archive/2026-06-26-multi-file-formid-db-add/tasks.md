## 1. Multi-file Add dialog (C++ GUI)

- [x] 1.1 In `classic-gui/src/app/settingsdialog.cpp::onAddFormIdDb()` (settingsdialog.cpp:587-594), replace the single-select `QFileDialog::getOpenFileName` call with `QFileDialog::getOpenFileNames` returning a `QStringList`; set the window title to the plural `QStringLiteral("Select FormID Databases")` and keep the existing filter `QStringLiteral("Database Files (*.db *.sqlite);;All Files (*)")` unchanged. (D1, D3)
- [x] 1.2 In the same slot, build a `QSet<QString> seen` from the existing `m_listFormIdDbs` entries keyed by `QDir::cleanPath(text).toLower()`; iterate the returned `QStringList` in selection order and `addItem` only for paths whose normalized key is not already in `seen`, inserting the key as each is added, so duplicates are silently skipped. (D2)
- [x] 1.3 Confirm `classic-gui/src/app/settingsdialog.h` needs no edit — `onAddFormIdDb()` declaration and `m_listFormIdDbs` are unchanged; the dedup set stays a local in the slot. (D4)

## 2. GUI source-inspection test

- [x] 2.1 Add a `settings_dialog_adds_multiple_formid_databases` private slot to `classic-gui/tests/test_scan_settings_wiring.cpp` that reads `src/app/settingsdialog.cpp`, extracts the `void SettingsDialog::onAddFormIdDb()` body (between its signature and the next `\nvoid SettingsDialog::`), and asserts the body calls `getOpenFileNames`, iterates the returned `QStringList` to append each selected file, and contains a duplicate-skip guard (`QSet<QString>` and a `contains`/insert check) before `addItem`. (D5)
- [x] 2.2 Declare the new slot in the `ScanSettingsWiringTests` `private slots:` block alongside the existing `settings_dialog_*` tests. No `classic-gui/tests/CMakeLists.txt` change (reuses the `classic-gui-test-scan-settings-wiring` target registered at CMakeLists.txt:170).

## 3. Build + verify (repo-approved commands)

- [x] 3.1 GUI build: `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1` succeeds.
- [x] 3.2 GUI tests: `pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test -CTestName classic-gui-test-scan-settings-wiring` is green (covers the new slot plus existing settings-dialog wiring).
- [x] 3.3 Manual smoke: open Settings → Paths → Additional FormID Databases → Add..., select 3 files including one already listed; confirm the 2 new files are appended in selection order and the duplicate is skipped; save, reopen the dialog for the same game, and confirm all entries persist.
- [x] 3.4 Confirm scope is C++-GUI-only: no `cpp-bindings/`, `python-bindings/`, `node-bindings/`, `foundation/`, `business-logic/`, or `docs/api/` files changed, so no CXX/Node/Python parity gates or `cargo` flows are required for this change.
