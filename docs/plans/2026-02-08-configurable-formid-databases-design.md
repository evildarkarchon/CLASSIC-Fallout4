# Configurable FormID Databases

## Summary

Replace the hardcoded FormID database list with a user-configurable, game-specific list. The Main database remains a built-in constant. Users can add and remove additional `.db` files through a file browser in the Settings UI (both Python and Rust GUIs). The list is stored in the Settings YAML file.

## Current State

`get_db_paths()` in `ClassicLib/core/constants.py` returns a hardcoded tuple of three databases: Main, Local, and FOLON. All three are resolved dynamically based on `GlobalRegistry.get_game()`. The `DatabasePool` in Rust already supports an arbitrary number of databases via `Vec<PathBuf>`.

## Design

### Data Model & Settings Storage

**Main database** remains a constant in `constants.py`, returning a single game-specific path (e.g., `Fallout4 FormIDs Main.db`). The Local and FOLON constants are removed.

**User database list** is stored in `CLASSIC Settings.yaml` as a game-specific key:

```yaml
CLASSIC_Settings:
  FormID Databases:
    Fallout4:
      - databases/FOLON FormIDs.db
    Skyrim: []
```

**Path resolution**:
- Shipped databases (e.g., FOLON): stored as relative paths, resolved against `ResourceLoader.get_data_directory()` (handles both frozen PyInstaller executables and development source trees)
- User-added databases: stored as absolute paths

**Default population**: When the `FormID Databases` key is missing or a game entry is absent, defaults are populated automatically (FOLON for Fallout 4, empty for Skyrim). FOLON is pre-populated and removable.

**Rust side**: `ClassicConfig` in `classic-config-core` gets a new `formid_databases: HashMap<String, Vec<PathBuf>>` field with matching load/save/default logic and the same relative/absolute path resolution.

### Python UI (Settings Dialog)

New section in the **Paths tab** of `ClassicLib/Interface/Settings/tab_creators.py`, below INI Folder and Mods Folder:

```
+-- FormID Databases ----------------------------+
|  +---------------------------------------------+
|  | databases/FOLON FormIDs.db                   |
|  | D:/MyMods/Custom FormIDs.db                  |
|  +---------------------------------------------+
|  [Add...]  [Remove]                             |
+------------------------------------------------+
```

- **QListWidget** displays database paths
- **Add** opens `QFileDialog.getOpenFileNames()` with filter: `SQLite Databases (*.db *.sqlite *.sqlite3 *.db3 *.sdb);;All Files (*)`
- **Remove** deletes selected items (enabled only when selection exists)
- List is game-specific, read/written based on `GlobalRegistry.get_game()`
- Dedicated `load_database_list()` / `save_database_list()` methods (not part of `SETTINGS_MAP`)

### Rust GUI (Slint Settings Tab)

New section in `settings_paths.slint`, below INI Folder and Mods Folder:

```
+-- FormID Databases ----------------------------+
|  +---------------------------------------------+
|  |  FOLON FormIDs.db                         X  |
|  |  Custom FormIDs.db                        X  |
|  +---------------------------------------------+
|  [Add...]                                       |
+------------------------------------------------+
```

- **ListView** with `VecModel<SharedString>` (VecModel rebuild pattern)
- Each row has an inline remove button
- **Add** triggers native file dialog via `rfd::FileDialog` with multi-select and SQLite file filters
- Callbacks: `database-add-clicked()`, `database-remove-clicked(int)`
- Changes trigger `save_full_config()` (full config save pattern)
- Game switching refreshes the list to show the active game's databases

### Constants & Pool Integration

**Python `constants.py`**:
- `get_db_paths()` simplified to return Main database only (single `Path`)
- New `get_user_db_paths() -> list[Path]`: reads game-specific list from YAML, resolves relative paths, filters missing files with warning
- New `get_all_db_paths() -> list[Path]`: combines Main + user databases
- `DB_PATHS` wrapper updated for backward compatibility with deprecation warning

**Pool initialization**: Both Python (`rust_pool.py`) and Rust GUI (`scan.rs`) switch from the hardcoded 3-path tuple to the combined list from `get_all_db_paths()` / equivalent Rust function.

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing database file | Skipped with warning log, pool continues with remaining databases |
| Duplicate path added | Silently skipped (compared by resolved absolute path) |
| Invalid SQLite file | `DatabasePool` catches sqlx error, logs warning, continues |
| Empty user list | Only Main is loaded (valid state) |
| Missing settings key | Default population (FOLON for Fallout 4, empty for Skyrim) |

### Testing

**Python unit tests**:
- `get_db_paths()` returns Main-only for each game
- `get_user_db_paths()` loads from YAML, resolves relative paths, filters missing files
- `get_all_db_paths()` combines Main + user list
- Default population when key is missing
- Duplicate detection on add

**Python integration tests**:
- Settings dialog round-trip (add, save, reopen, verify)
- File browser mock with correct filter

**Rust unit tests**:
- `ClassicConfig` serialization/deserialization with `formid_databases`
- Default population and path resolution

**Rust GUI tests**:
- VecModel rebuild after add/remove
- Callback wiring

**No pool-level changes needed** — existing `DatabasePool` multi-database tests already cover the query behavior.
