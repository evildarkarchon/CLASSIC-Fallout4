## Context

`SettingsDialog::onAddFormIdDb()` in `classic-gui/src/app/settingsdialog.cpp:587-594` adds additional FormID databases to `m_listFormIdDbs` (a `QListWidget`). It currently opens a single-select static dialog:

```cpp
QString file = QFileDialog::getOpenFileName(this, QStringLiteral("Select FormID Database"), QString(),
                                            QStringLiteral("Database Files (*.db *.sqlite);;All Files (*)"));
if (!file.isEmpty()) {
    m_listFormIdDbs->addItem(file);
}
```

Everything around it already handles N entries: `loadSettings()` (settingsdialog.cpp:415-422) repopulates the list from `CLASSIC_Settings.FormID Databases.<game>` via `yaml_ops_get_vec`; `saveSettings()` (settingsdialog.cpp:498-506) writes every list item back via `yaml_ops_set_vec_setting`; `resetToDefaults()` clears it. The CXX bridge orchestrator (`cpp-bindings/classic-cpp-bridge/src/scanner/orchestrator.rs:386`) reads the same per-game list into the pool, so the storage/pool side is multi-entry already. Only the Add dialog is single-select.

The original configurable-databases design (`docs/plans/2026-02-08-configurable-formid-databases-design.md:50,71`) specified multi-select (`getOpenFileNames()` / `rfd::FileDialog` multi-select) and "Duplicate path added → silently skipped." The shipped C++ GUI diverged to single-select and dropped the duplicate skip. There is no Slint/Rust GUI surface for this in the current tree; the change is C++-GUI-only.

GUI tests are source-inspection style: `classic-gui/tests/test_scan_settings_wiring.cpp` reads `settingsdialog.cpp` and asserts patterns (e.g. `settings_dialog_wires_game_folder_path_controls`, `settings_dialog_handles_not_published_as_benign`). No existing test asserts the FormID dialog, so nothing breaks; the new behavior gets a new source-inspection slot in the same file/target (`classic-gui-test-scan-settings-wiring`, registered in `classic-gui/tests/CMakeLists.txt:170`).

## Goals / Non-Goals

**Goals:**
- Make the FormID Database Add dialog multi-select so several databases can be added in one action.
- Skip duplicates at add time so multi-select cannot create redundant list entries.
- Add a source-inspection test pinning the multi-select add behavior.

**Non-Goals:**
- No change to the YAML storage format, `loadSettings`/`saveSettings`/`resetToDefaults`, the CXX bridge, `ClassicConfig.formid_databases`, Python, or Node surfaces.
- No change to the `Additional FormID Databases` UI layout (group, help label, list widget, Add/Remove button row).
- No expansion of the file filter beyond the existing `*.db *.sqlite` + All Files set, and no drag-and-drop or folder support.
- No new `SettingsDialog` slots or members; `settingsdialog.h` is unchanged.

## Decisions

**D1 — Static `getOpenFileNames` over an instantiated `QFileDialog`.**
Use the static `QFileDialog::getOpenFileNames(this, QStringLiteral("Select FormID Databases"), QString(), <filter>)`, mirroring the existing static calls in this file (`getExistingDirectory` for Game/INI folder, the old `getOpenFileName`). It returns a `QStringList` of absolute paths.
*Alternative:* instantiate `QFileDialog` and `setFileMode(QFileDialog::ExistingFiles)`. *Rejected:* more code, no behavioral gain — the native Windows dialog already multi-selects via the static call (Ctrl/Shift-click), and the rest of the dialog code uses the static form.

**D2 — Skip duplicates at add time with a case-insensitive normalized set.**
Build a `QSet<QString> seen` of existing entries keyed by lowercased `QDir::cleanPath(...)`. Iterate the returned `QStringList` in order; for each path, compute the same normalized key, and `addItem` only if the key is not already present (then insert the key). This is O(n+m), preserves selection order, and matches the design doc's "silently skipped (compared by resolved absolute path)" plus the repo's existing `Qt::CaseInsensitive` path-comparison convention (e.g. game-folder checks in `settingsdialog.cpp:482`).
*Alternative A:* no dedup. *Rejected:* multi-select makes accidental dupes likely and the design mandates skip.
*Alternative B:* dedup only on save. *Rejected:* duplicates would be visible in the list before save, contradicting the design's add-time skip and hurting UX.

**D3 — Keep the existing filter; change only the title to plural.**
Reuse `QStringLiteral("Database Files (*.db *.sqlite);;All Files (*)")` unchanged and switch the window title to the plural `"Select FormID Databases"`.
*Alternative:* widen the filter to the design doc's `*.db *.sqlite *.sqlite3 *.db3 *.sdb`. *Rejected as out of scope* — widening extensions is a separate filter decision; keeping it minimizes the change surface. Noted as an open question.

**D4 — Edit only `onAddFormIdDb()`; no header change.**
The dedup set is a local variable inside the slot. `settingsdialog.h` (`onAddFormIdDb()` declaration, `m_listFormIdDbs` member) is unchanged, so no moc/CMake regeneration concerns.

**D5 — Test via source inspection, not a live dialog.**
Add a slot to `classic-gui/tests/test_scan_settings_wiring.cpp` that extracts the `onAddFormIdDb` body and asserts it calls `getOpenFileNames`, iterates the returned `QStringList` (per-file append), and performs a duplicate check against existing entries (presence of dedup logic, e.g. a `QSet<QString>`/`contains` guard). Reuse the existing `classic-gui-test-scan-settings-wiring` target; no `CMakeLists.txt` edit.
*Alternative:* a runtime test driving the real `QFileDialog`. *Rejected:* native file dialogs cannot be scripted under the offscreen/minimal QPA platform used by CI; the repo's established pattern for dialog wiring is source inspection.

## Risks / Trade-offs

- **Native multi-select dialog is not unit-drivable.** → Mitigated by the source-inspection test (D5) plus a manual smoke step in tasks (select 3 files incl. one already listed; confirm 2 added).
- **Relative-vs-absolute duplicate mismatch.** Loaded entries may be relative strings (e.g. `databases/FOLON FormIDs.db`), while the native dialog returns absolute paths. A user re-selecting a shipped relative DB by its absolute path would not dedup against the relative entry. → Accepted trade-off: this is pre-existing (single-file add had the same gap), and the built-in Main database is outside this list. Dedup is conservative (normalized exact match). Captured as an open question rather than expanding scope.
- **Order/normalization differences across platforms.** `QDir::cleanPath` normalizes separators; case-insensitive lowercasing handles Windows drive letters. → Matches existing repo path-comparison convention; no new platform risk.
- **No behavioral change to scan/pool.** → Verified: orchestrator already consumes the list as-is; no pool or query code changes.

## Open Questions

- Should the file filter be widened to `*.db *.sqlite *.sqlite3 *.db3 *.sdb` to match the original design doc? Left out of this change; revisit as a follow-up if users report extension gaps.
- Should relative shipped entries be canonicalized to absolute on load so dedup can catch relative-vs-absolute collisions? Out of scope here; tracked as a possible follow-up to D2.
