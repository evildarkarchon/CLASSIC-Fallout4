# Implementation Tasks

**Status: COMPLETED** (2025-12-11)

## 1. Update Entry Points
- [x] 1.1 Update `CLASSIC_Interface.py` - Change imports from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`
- [x] 1.2 Update `CLASSIC_ScanLogs.py` - Change imports from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`
- [x] 1.3 Update `CLASSIC_Interface_QML.py` - Change imports from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`

## 2. Update ClassicLib Root Modules
- [x] 2.1 Update `ClassicLib/__init__.py` - Change re-exports from `ClassicLib.YamlSettingsCache` to `ClassicLib.YamlSettings`
- [x] 2.2 Update `ClassicLib/BackupManager.py`
- [x] 2.3 Update `ClassicLib/DocumentsChecker.py`
- [x] 2.4 Update `ClassicLib/DocsPath.py`
- [x] 2.5 Update `ClassicLib/FileGeneration.py`
- [x] 2.6 Update `ClassicLib/GameIntegrity.py`
- [x] 2.7 Update `ClassicLib/GamePath.py`
- [x] 2.8 Update `ClassicLib/GuiComponents.py`
- [x] 2.9 Update `ClassicLib/PapyrusLog.py`
- [x] 2.10 Update `ClassicLib/PathValidator.py`
- [x] 2.11 Update `ClassicLib/ResourceLoader.py`
- [x] 2.12 Update `ClassicLib/SetupCoordinator.py`
- [x] 2.13 Update `ClassicLib/Update.py`
- [x] 2.14 Update `ClassicLib/XseCheck.py`

## 3. Update ScanGame Subsystem
- [x] 3.1 Update `ClassicLib/ScanGame/CheckCrashgen.py`
- [x] 3.2 Update `ClassicLib/ScanGame/CheckXsePlugins.py`
- [x] 3.3 Update `ClassicLib/ScanGame/Config.py`
- [x] 3.4 Update `ClassicLib/ScanGame/GameFilesManager.py`
- [x] 3.5 Update `ClassicLib/ScanGame/GameIntegrityOrchestrator.py`
- [x] 3.6 Update `ClassicLib/ScanGame/ScanGameCore.py`
- [x] 3.7 Update `ClassicLib/ScanGame/WryeCheck.py`
- [x] 3.8 Update `ClassicLib/ScanGame/core/log_processor.py`
- [x] 3.9 Update `ClassicLib/ScanGame/core/validators.py`

## 4. Update ScanLog Subsystem
- [x] 4.1 Update `ClassicLib/ScanLog/AsyncReformat.py`
- [x] 4.2 Update `ClassicLib/ScanLog/OrchestratorCore.py`
- [x] 4.3 Update `ClassicLib/ScanLog/ScanLogsExecutor.py`
- [x] 4.4 Update `ClassicLib/ScanLog/Util.py`
- [x] 4.5 Update `ClassicLib/ScanLog/scanloginfo/classic_scan_logs_info.py`

## 5. Update Interface Subsystem
- [x] 5.1 Update `ClassicLib/Interface/FolderManagement.py`
- [x] 5.2 Update `ClassicLib/Interface/FolderManagementMixin.py`
- [x] 5.3 Update `ClassicLib/Interface/HelpAndAboutMixin.py`
- [x] 5.4 Update `ClassicLib/Interface/ResultsViewerMixin.py`
- [x] 5.5 Update `ClassicLib/Interface/ScanOperations.py`
- [x] 5.6 Update `ClassicLib/Interface/UIHelpers.py`
- [x] 5.7 Update `ClassicLib/Interface/UpdateManager.py`
- [x] 5.8 Update `ClassicLib/Interface/WindowGeometryMixin.py`
- [x] 5.9 Update `ClassicLib/Interface/Settings/dialog.py`
- [x] 5.10 Update `ClassicLib/Interface/Settings/path_manager.py`

## 6. Update Other ClassicLib Modules
- [x] 6.1 Update `ClassicLib/integration/status.py`
- [x] 6.2 Update `ClassicLib/MessageHandler/progress/context.py`

## 7. Update Test Imports
- [x] 7.1 Update `tests/stress/test_memory_stress.py`
- [x] 7.2 Update `tests/stress/test_performance_stress.py`
- [x] 7.3 Update `tests/stress/test_concurrency_stress.py`
- [x] 7.4 Update `tests/settings/test_yaml_sync_wrapper_unit.py` (imports + patches)
- [x] 7.5 Update `tests/settings/test_yaml_sync_wrapper_integration.py`
- [x] 7.6 Update `tests/settings/test_yaml_cache_singleton_regression.py` (imports + patches)
- [x] 7.7 Update `tests/settings/test_yaml_batch_operations.py`
- [x] 7.8 Update `tests/performance/test_orchestrator_rust_vs_python.py`
- [x] 7.9 Update `tests/mods/test_mod_detection_patterns.py`
- [x] 7.10 Update `tests/interface/test_yaml_settings_rust.py`
- [x] 7.11 Update `tests/fixtures/registry_fixtures.py` (imports + patches)
- [x] 7.12 Update `tests/fixtures/mock_fixtures.py` (patches)
- [x] 7.13 Update `tests/rust_integration/fixtures/mock_data_factory.py` (docstrings) - Not needed (only local MockYamlSettingsCache class)

## 8. Update GUI Test Files
- [x] 8.1 Update `tests/gui/settings/conftest.py` (imports + patches)
- [x] 8.2 Update `tests/gui/settings/test_dialog_behavior_e2e.py`
- [x] 8.3 Update `tests/gui/settings/test_dialog_behavior_unit.py`
- [x] 8.4 Update `tests/gui/settings/test_integration_e2e.py`
- [x] 8.5 Update `tests/gui/settings/test_integration_unit.py`
- [x] 8.6 Update `tests/gui/settings/test_settings_persistence_e2e.py`
- [x] 8.7 Update `tests/gui/settings/test_settings_persistence_unit.py`
- [x] 8.8 Update `tests/gui/settings/test_ui_structure_e2e.py`
- [x] 8.9 Update `tests/gui/test_scan_error_dialog_integration.py` (patches)

## 9. Update Other Test Files
- [x] 9.1 Update `tests/setup/test_setup_initialization.py` (patches)
- [x] 9.2 Update `tests/setup/test_initial_setup.py` (patches)
- [x] 9.3 Update `tests/scanning/test_scan_mods_unpacked.py` (patches)
- [x] 9.4 Update `tests/scanning/test_scan_mods_archived.py` (patches)
- [x] 9.5 Update `tests/scanning/test_scan_log_errors.py` (patches)
- [x] 9.6 Update `tests/scanning/test_scan_game_integration.py` (patches)
- [x] 9.7 Update `tests/game/test_game_integrity_synthetic.py` (patches)
- [x] 9.8 Update `tests/game/integrity/test_integrity_configuration.py` (patches)
- [x] 9.9 Update `tests/core/test_message_handler.py` (patches)
- [x] 9.10 Update `tests/core/test_file_generation.py` (patches)
- [x] 9.11 Update `tests/core/test_documents_checker.py` (patches)
- [x] 9.12 Update `tests/backup/test_backup_configuration.py` (patches)

## 10. Delete Compatibility Module
- [x] 10.1 Delete `ClassicLib/YamlSettingsCache.py`

## 11. Verification
- [x] 11.1 Run `uv run ruff check .` to verify no linting errors
- [x] 11.2 Run `uv run pytest tests/settings/test_yaml_sync_wrapper_unit.py -v` to verify unit tests pass
- [x] 11.3 Verify no remaining imports from `ClassicLib.YamlSettingsCache` via search
- [ ] 11.4 Run full test suite (deferred to CI)

## Notes

### Import Replacement Pattern
Replace:
```python
from ClassicLib.YamlSettingsCache import yaml_settings, classic_settings
```

With:
```python
from ClassicLib.YamlSettings import yaml_settings, classic_settings
```

### Patch Path Replacement Pattern
Replace:
```python
@patch("ClassicLib.YamlSettingsCache.yaml_settings")
```

With:
```python
@patch("ClassicLib.YamlSettings.yaml_settings")
```

### Special Cases
1. `tests/settings/test_yaml_cache_singleton_regression.py` has `import ClassicLib.YamlSettingsCache` statements that need to change to `import ClassicLib.YamlSettings`
2. Some test files reference `_get_yaml_cache` which should be imported from `ClassicLib.YamlSettings.sync.convenience`
3. `ClassicLib/__init__.py` re-exports need to maintain backward compatibility for users importing from `ClassicLib` directly