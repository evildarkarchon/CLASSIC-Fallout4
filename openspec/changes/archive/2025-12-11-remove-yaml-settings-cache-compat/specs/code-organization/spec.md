**Status: IMPLEMENTED** (2025-12-11)

## MODIFIED Requirements

### Requirement: Canonical Import Paths for YAML Settings
ClassicLib SHALL provide YAML settings functionality exclusively through the `ClassicLib.YamlSettings` module. No backward compatibility aliases SHALL be maintained.

#### Scenario: YAML settings imports use YamlSettings module
- **WHEN** YAML settings functionality is needed
- **THEN** imports MUST come from `ClassicLib.YamlSettings` or `ClassicLib.YamlSettings.async_`

#### Scenario: Backward compatibility module removed
- **WHEN** code attempts to import from `ClassicLib.YamlSettingsCache`
- **THEN** an ImportError SHALL be raised

#### Scenario: Test mock paths use canonical module
- **WHEN** tests need to mock YAML settings functionality
- **THEN** patches MUST use `ClassicLib.YamlSettings` as the module path, not legacy aliases

## ADDED Requirements

### Requirement: No Legacy Import Aliases for Core Modules
Core functionality modules that have been migrated to new canonical paths SHALL NOT maintain backward compatibility import aliases beyond their migration period. This includes:
- YAML settings: `ClassicLib.YamlSettings` (no `ClassicLib.YamlSettingsCache`)
- File I/O: `ClassicLib.FileIO` (no legacy aliases)
- Async utilities: `ClassicLib.Utils.Async` (no legacy aliases)

#### Scenario: Removed import alias raises ImportError
- **WHEN** code imports from a removed legacy alias path
- **THEN** Python SHALL raise `ImportError` or `ModuleNotFoundError`

#### Scenario: Migration documentation provided
- **WHEN** a legacy import alias is removed
- **THEN** the change proposal MUST include a migration guide with old-to-new import mappings