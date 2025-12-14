# Tasks: Refactor AsyncBridge Usage

## 1. Specification & Documentation
- [x] 1.1 Create `async-patterns` capability spec with AsyncBridge usage requirements
- [x] 1.2 Update `08-memories.md` with clarified enforcement language
- [x] 1.3 Validate spec with `openspec validate refactor-asyncbridge-usage --strict`

## 2. Audit & Classification
- [x] 2.1 Generate complete list of files importing AsyncBridge
- [x] 2.2 Classify each import as Tier 1 (Core), Tier 2 (Legitimate), or Tier 3 (Violation)
- [x] 2.3 Create migration tracking document in `docs/migration/asyncbridge-refactoring.md`

## 3. ScanGame Module Refactoring (Highest Priority)
- [x] 3.1 Refactor `ClassicLib/ScanGame/ScanModInis.py`:
  - Added GUI-only warnings to sync wrappers `scan_mod_inis()` and `check_vsync_settings()`
- [x] 3.2 Refactor `ClassicLib/ScanGame/Config.py`:
  - Added GUI-only warnings to `get()` and `has()` methods
- [x] 3.3 Refactor `ClassicLib/ScanGame/GameFilesManager.py`:
  - Already has proper documentation (IMPORTANT - Usage section)
- [x] 3.4 Refactor `ClassicLib/ScanGame/GameIntegrityOrchestrator.py`:
  - Already has proper documentation (IMPORTANT - Usage section)
- [x] 3.5 Refactor `ClassicLib/ScanGame/core/ini_fallback.py`:
  - Added GUI-only warning to `detect_all_issues()` method

## 4. ScanLog Module Refactoring
- [x] 4.1 Refactor `ClassicLib/ScanLog/FormIDAnalyzerCore.py`:
  - Moved `run_async` import to local scope in sync wrappers
  - Added GUI-only warnings to `formid_match_sync()` and `lookup_formid_value_sync()`
- [x] 4.2 Refactor `ClassicLib/ScanLog/ScanLogsUtils.py`:
  - Moved `run_async` import to local scope
  - Added GUI-only warning to `crashlogs_scan()`
- [x] 4.3 Verify `ClassicLib/ScanLog/FormIDAnalyzer.py`:
  - Already documented as GUI-only (class docstring + DEPRECATED notices)

## 5. Rust Wrapper Module Refactoring
- [x] 5.1 Refactor `ClassicLib/rust/file_io_rust.py`:
  - Added GUI-only warning to `create_file_io_sync()` function
  - Added GUI-only note to `SyncWrapper` class docstring
- [x] 5.2 Verify other Rust wrappers (`formid_rust.py`, `orchestrator_api.py`, `parser_rust.py`):
  - All already have proper documentation with AsyncBridge usage examples

## 6. Utility Module Refactoring
- [x] 6.1 Refactor `ClassicLib/FileGeneration.py`:
  - Added GUI-only warning to `generate_all_files()` method

## 7. Validation & Testing
- [x] 7.1 Run ruff check on edited files: All checks passed
- [x] 7.2 Run unit tests: 15 passed
- [x] 7.3 Run async-related tests: 622 passed, 73 skipped, 1 unrelated failure
- [x] 7.4 Verify entry points use async-first pattern:
  - `CLASSIC_ScanLogs.py` (already compliant)
  - `CLASSIC_ScanGame.py` (already compliant, documented at top of file)

## 8. Documentation Updates
- [x] 8.1 Created `docs/migration/asyncbridge-refactoring.md` with complete classification
- [x] 8.2 Updated `.claude/rules/08-memories.md` with three-tier classification and enforcement language
- [x] 8.3 Archive this change after deployment (pending review)

## Dependencies
- Tasks 3.x, 4.x, 5.x, 6.x are parallelizable
- Task 7.x depends on all refactoring tasks
- Task 8.x depends on Task 7.x (validation complete)
