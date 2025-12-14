## ADDED Requirements

### Requirement: Canonical Import Paths for Utils
ClassicLib SHALL provide utility functionality exclusively through the `ClassicLib.Utils` module and its submodules. No backward compatibility aliases SHALL be maintained.

#### Scenario: Utils imports use canonical submodule paths
- **WHEN** utility functionality is needed
- **THEN** imports MUST come from `ClassicLib.Utils` or specific submodules:
  - `ClassicLib.Utils.string_utils` for string manipulation (normalize_list, append_or_extend)
  - `ClassicLib.Utils.path_utils` for path operations (validate_path, remove_readonly)
  - `ClassicLib.Utils.file_utils` for file operations (calculate_file_hash, calculate_similarity, open_file_with_encoding)
  - `ClassicLib.Utils.version_utils` for version handling (get_game_version, crashgen_version_gen)
  - `ClassicLib.Utils.logging_utils` for logging setup (configure_logging)
  - `ClassicLib.Utils.web_utils` for network operations (pastebin_fetch, async_pastebin_fetch)

#### Scenario: Backward compatibility module removed
- **WHEN** code attempts to import from `ClassicLib.Util`
- **THEN** an ImportError SHALL be raised

#### Scenario: Test mock paths use canonical module
- **WHEN** tests need to mock utility functionality
- **THEN** patches MUST use `ClassicLib.Utils` submodule paths, not the legacy `ClassicLib.Util` alias

## MODIFIED Requirements

### Requirement: No Legacy Import Aliases for Core Modules
Core functionality modules that have been migrated to new canonical paths SHALL NOT maintain backward compatibility import aliases beyond their migration period. This includes:
- YAML settings: `ClassicLib.YamlSettings` (no `ClassicLib.YamlSettingsCache`)
- File I/O: `ClassicLib.FileIO` (no legacy aliases)
- Async utilities: `ClassicLib.Utils.Async` (no legacy aliases)
- Utils: `ClassicLib.Utils` (no `ClassicLib.Util`)

#### Scenario: Removed import alias raises ImportError
- **WHEN** code imports from a removed legacy alias path
- **THEN** Python SHALL raise `ImportError` or `ModuleNotFoundError`

#### Scenario: Migration documentation provided
- **WHEN** a legacy import alias is removed
- **THEN** the change proposal MUST include a migration guide with old-to-new import mappings