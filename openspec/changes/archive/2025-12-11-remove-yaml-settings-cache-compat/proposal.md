# Change: Remove YamlSettingsCache Backward Compatibility Module

**Status: COMPLETED** (2025-12-11)

## Why
The `ClassicLib/YamlSettingsCache.py` backward compatibility module was introduced during the modularization
of YAML settings functionality into `ClassicLib.YamlSettings`. Now that the migration period has passed and
the canonical import paths are established in the code-organization spec, this compatibility shim should be
removed to:
1. Eliminate code duplication and maintenance overhead
2. Enforce consistent import patterns across the codebase
3. Reduce cognitive load for developers by having a single source of truth

## What Changes
- **REMOVED** `ClassicLib/YamlSettingsCache.py` - The backward compatibility re-export module
- **MODIFIED** 44 production files - Update imports from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`
- **MODIFIED** 27 test files - Update imports and mock/patch paths from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`
- **MODIFIED** `ClassicLib/__init__.py` - Update re-exports to use `ClassicLib.YamlSettings`

## Impact
- **Affected specs**: code-organization
- **Affected code**:
  - Entry points: `CLASSIC_Interface.py`, `CLASSIC_ScanLogs.py`, `CLASSIC_Interface_QML.py`
  - ScanGame subsystem: 8 files
  - ScanLog subsystem: 5 files  
  - Interface subsystem: 9 files
  - Core utilities: 10 files
  - Test suite: 27 files (imports + patches)
- **Breaking change**: Any external code importing from `ClassicLib.YamlSettingsCache` will break

## Migration Guide

### Import Migrations

| Old Import                                                        | New Import                                                             |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `from ClassicLib.YamlSettingsCache import yaml_settings`          | `from ClassicLib.YamlSettings import yaml_settings`                    |
| `from ClassicLib.YamlSettingsCache import yaml_settings_async`    | `from ClassicLib.YamlSettings import yaml_settings_async`              |
| `from ClassicLib.YamlSettingsCache import classic_settings`       | `from ClassicLib.YamlSettings import classic_settings`                 |
| `from ClassicLib.YamlSettingsCache import classic_settings_async` | `from ClassicLib.YamlSettings import classic_settings_async`           |
| `from ClassicLib.YamlSettingsCache import yaml_cache`             | `from ClassicLib.YamlSettings import yaml_cache`                       |
| `from ClassicLib.YamlSettingsCache import YamlSettingsCache`      | `from ClassicLib.YamlSettings import YamlSettingsCache`                |
| `from ClassicLib.YamlSettingsCache import AsyncYamlSettingsCore`  | `from ClassicLib.YamlSettings import AsyncYamlSettingsCore`            |
| `from ClassicLib.YamlSettingsCache import _get_yaml_cache`        | `from ClassicLib.YamlSettings.sync.convenience import _get_yaml_cache` |

### Patch Path Migrations (Tests)

**Important**: Patch paths depend on where the function is imported in the module under test:
- If the module imports from `ClassicLib.YamlSettings`, patch at `ClassicLib.YamlSettings.<function>`
- For more targeted mocking at the source, patch at `ClassicLib.YamlSettings.sync.convenience.<function>`

| Old Patch Path                                        | New Patch Path (re-export)                       | Alternative (source)                                        |
| ----------------------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| `ClassicLib.YamlSettingsCache.yaml_settings`          | `ClassicLib.YamlSettings.yaml_settings`          | `ClassicLib.YamlSettings.sync.convenience.yaml_settings`    |
| `ClassicLib.YamlSettingsCache.yaml_settings_async`    | `ClassicLib.YamlSettings.yaml_settings_async`    | `ClassicLib.YamlSettings.async_.yaml_settings_async`        |
| `ClassicLib.YamlSettingsCache.classic_settings`       | `ClassicLib.YamlSettings.classic_settings`       | `ClassicLib.YamlSettings.sync.convenience.classic_settings` |
| `ClassicLib.YamlSettingsCache.classic_settings_async` | `ClassicLib.YamlSettings.classic_settings_async` | `ClassicLib.YamlSettings.async_.classic_settings_async`     |
| `ClassicLib.YamlSettingsCache.yaml_cache`             | `ClassicLib.YamlSettings.yaml_cache`             | `ClassicLib.YamlSettings.sync.convenience.yaml_cache`       |
| `ClassicLib.YamlSettingsCache.YamlSettingsCache`      | `ClassicLib.YamlSettings.YamlSettingsCache`      | `ClassicLib.YamlSettings.sync.cache.YamlSettingsCache`      |
| `ClassicLib.YamlSettingsCache.AsyncBridge`            | N/A (import directly)                            | `ClassicLib.AsyncBridge.AsyncBridge`                        |

**Module Structure Reference**:
```
ClassicLib.YamlSettings                      # Top-level re-exports
├── ClassicLib.YamlSettings.sync            # Sync submodule re-exports
│   ├── YamlSettingsCache                   # from .cache
│   ├── yaml_settings                       # from .convenience
│   ├── classic_settings                    # from .convenience
│   └── yaml_cache                          # from .convenience
├── ClassicLib.YamlSettings.async_          # Async submodule re-exports
│   ├── AsyncYamlSettingsCore               # from .core
│   ├── yaml_settings_async                 # from .core
│   └── classic_settings_async              # from .core
└── ClassicLib.YamlSettings.sync.convenience  # Actual sync implementations
```

## Files Summary

### Production Code (44 files)

**Entry Points:**
- `CLASSIC_Interface.py`
- `CLASSIC_ScanLogs.py`
- `CLASSIC_Interface_QML.py`

**ClassicLib Root:**
- `ClassicLib/__init__.py`
- `ClassicLib/BackupManager.py`
- `ClassicLib/DocumentsChecker.py`
- `ClassicLib/DocsPath.py`
- `ClassicLib/FileGeneration.py`
- `ClassicLib/GameIntegrity.py`
- `ClassicLib/GamePath.py`
- `ClassicLib/GuiComponents.py`
- `ClassicLib/PapyrusLog.py`
- `ClassicLib/PathValidator.py`
- `ClassicLib/ResourceLoader.py`
- `ClassicLib/SetupCoordinator.py`
- `ClassicLib/Update.py`
- `ClassicLib/XseCheck.py`

**ClassicLib/ScanGame:**
- `ClassicLib/ScanGame/CheckCrashgen.py`
- `ClassicLib/ScanGame/CheckXsePlugins.py`
- `ClassicLib/ScanGame/Config.py`
- `ClassicLib/ScanGame/GameFilesManager.py`
- `ClassicLib/ScanGame/GameIntegrityOrchestrator.py`
- `ClassicLib/ScanGame/ScanGameCore.py`
- `ClassicLib/ScanGame/WryeCheck.py`
- `ClassicLib/ScanGame/core/log_processor.py`
- `ClassicLib/ScanGame/core/validators.py`

**ClassicLib/ScanLog:**
- `ClassicLib/ScanLog/AsyncReformat.py`
- `ClassicLib/ScanLog/OrchestratorCore.py`
- `ClassicLib/ScanLog/ScanLogsExecutor.py`
- `ClassicLib/ScanLog/Util.py`
- `ClassicLib/ScanLog/scanloginfo/classic_scan_logs_info.py`

**ClassicLib/Interface:**
- `ClassicLib/Interface/FolderManagement.py`
- `ClassicLib/Interface/FolderManagementMixin.py`
- `ClassicLib/Interface/HelpAndAboutMixin.py`
- `ClassicLib/Interface/ResultsViewerMixin.py`
- `ClassicLib/Interface/ScanOperations.py`
- `ClassicLib/Interface/UIHelpers.py`
- `ClassicLib/Interface/UpdateManager.py`
- `ClassicLib/Interface/WindowGeometryMixin.py`
- `ClassicLib/Interface/Settings/dialog.py`
- `ClassicLib/Interface/Settings/path_manager.py`

**ClassicLib/integration:**
- `ClassicLib/integration/status.py`

**ClassicLib/MessageHandler:**
- `ClassicLib/MessageHandler/progress/context.py`

### Test Files (27 files)

**tests/stress:**
- `tests/stress/test_memory_stress.py`
- `tests/stress/test_performance_stress.py`
- `tests/stress/test_concurrency_stress.py`

**tests/settings:**
- `tests/settings/test_yaml_sync_wrapper_unit.py`
- `tests/settings/test_yaml_sync_wrapper_integration.py`
- `tests/settings/test_yaml_cache_singleton_regression.py`
- `tests/settings/test_yaml_batch_operations.py`

**tests/performance:**
- `tests/performance/test_orchestrator_rust_vs_python.py`

**tests/mods:**
- `tests/mods/test_mod_detection_patterns.py`

**tests/interface:**
- `tests/interface/test_yaml_settings_rust.py`

**tests/gui/settings:**
- `tests/gui/settings/conftest.py`
- `tests/gui/settings/test_dialog_behavior_e2e.py`
- `tests/gui/settings/test_dialog_behavior_unit.py`
- `tests/gui/settings/test_integration_e2e.py`
- `tests/gui/settings/test_integration_unit.py`
- `tests/gui/settings/test_settings_persistence_e2e.py`
- `tests/gui/settings/test_settings_persistence_unit.py`
- `tests/gui/settings/test_ui_structure_e2e.py`

**tests/setup:**
- `tests/setup/test_setup_initialization.py`
- `tests/setup/test_initial_setup.py`

**tests/scanning:**
- `tests/scanning/test_scan_mods_unpacked.py`
- `tests/scanning/test_scan_mods_archived.py`
- `tests/scanning/test_scan_log_errors.py`
- `tests/scanning/test_scan_game_integration.py`

**tests/game:**
- `tests/game/test_game_integrity_synthetic.py`
- `tests/game/integrity/test_integrity_configuration.py`

**tests/gui:**
- `tests/gui/test_scan_error_dialog_integration.py`

**tests/core:**
- `tests/core/test_message_handler.py`
- `tests/core/test_file_generation.py`
- `tests/core/test_documents_checker.py`

**tests/backup:**
- `tests/backup/test_backup_configuration.py`

**tests/fixtures:**
- `tests/fixtures/registry_fixtures.py`
- `tests/fixtures/mock_fixtures.py`

**tests/rust_integration:**
- `tests/rust_integration/fixtures/mock_data_factory.py`