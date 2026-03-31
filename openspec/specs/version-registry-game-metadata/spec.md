## ADDED Requirements

### Requirement: VersionInfo carries game-identity metadata
Each `VersionInfo` entry in the Version Registry SHALL include `docs_name` (the My Documents subfolder name, e.g., `"Fallout4"`, `"Fallout4VR"`) and `steam_id` (the Steam application ID, e.g., `377160`, `611660`). These fields SHALL be populated for all registered versions. Consumers SHALL obtain these values from the registry instead of from YAML `Game_Info`/`GameVR_Info` sections.

#### Scenario: Non-VR version provides flat-game identity
- **WHEN** the active version is `FO4_OG`
- **THEN** `version_info.docs_name` returns `"Fallout4"` and `version_info.steam_id` returns `377160`

#### Scenario: VR version provides VR-specific identity
- **WHEN** the active version is `FO4_VR`
- **THEN** `version_info.docs_name` returns `"Fallout4VR"` and `version_info.steam_id` returns `611660`

---

### Requirement: XseConfig carries full display name and file count
Each `XseConfig` entry SHALL include `full_name` (the full display string, e.g., `"Fallout 4 Script Extender (F4SE)"`) and `file_count` (the expected number of script files, e.g., `29`). These fields SHALL be populated for all versions that have an XSE configuration.

#### Scenario: OG XSE provides full metadata
- **WHEN** the active version is `FO4_OG`
- **THEN** `xse.full_name` returns `"Fallout 4 Script Extender (F4SE)"` and `xse.file_count` returns `29`

#### Scenario: VR XSE provides VR-specific metadata
- **WHEN** the active version is `FO4_VR`
- **THEN** `xse.full_name` returns `"Fallout 4 Script Extender VR (F4SEVR)"` and `xse.file_count` returns `29`

---

### Requirement: CrashgenConfig carries acronym and DLL filename
Each `CrashgenConfig` entry SHALL include `acronym` (the short identifier, e.g., `"BO4"`, `"BO4 NG"`) and `dll_file` (the DLL filename, e.g., `"buffout4.dll"`). These fields SHALL be populated for all crash generator configurations.

#### Scenario: OG crashgen provides identity fields
- **WHEN** the OG version's legacy crashgen config (v1.28.6) is accessed
- **THEN** `crashgen.acronym` returns `"BO4"` and `crashgen.dll_file` returns `"buffout4.dll"`

#### Scenario: VR crashgen provides identity fields
- **WHEN** the VR version's crashgen config is accessed
- **THEN** `crashgen.acronym` returns `"BO4 NG"` and `crashgen.dll_file` returns `"buffout4.dll"`

---

### Requirement: All script hashes are populated in the registry
Each `XseConfig` entry that has script hashes SHALL contain the complete set of hashes for that version's script extender installation (all script `.pex` files). The registry SHALL NOT contain a partial subset of hashes. Versions for which hash data is unavailable (e.g., FO4_AE) SHALL have an empty `script_hashes` collection.

#### Scenario: OG version has all 29 script hashes
- **WHEN** the `FO4_OG` version's XSE config is accessed
- **THEN** `xse.script_hashes` contains exactly 29 `(filename, sha256_hash)` entries

#### Scenario: VR version has all 29 script hashes
- **WHEN** the `FO4_VR` version's XSE config is accessed
- **THEN** `xse.script_hashes` contains exactly 29 `(filename, sha256_hash)` entries

#### Scenario: AE version has no script hashes (data unavailable)
- **WHEN** the `FO4_AE` version's XSE config is accessed
- **THEN** `xse.script_hashes` is empty

---

### Requirement: Runtime path cache uses a single namespace
All runtime-discovered filesystem paths (game root, docs root, exe path, data folders, etc.) SHALL be stored under a single `Game_Info` namespace in `YAML.Game_Local`, regardless of whether the active version is VR, OG, NG, or AE. The `GameVR_Info` namespace has been fully removed from all code paths, YAML templates, and documentation. Consumers SHALL use `"Game_Info.{key}"` unconditionally when reading or writing runtime paths. No code path, template, or fixture SHALL reference the `GameVR_Info` namespace.

#### Scenario: VR paths written to Game_Info namespace
- **WHEN** the active version is `FO4_VR` and `game_path.py` discovers the VR game installation path
- **THEN** the path is written to `Game_Info.Root_Folder_Game` in `YAML.Game_Local`

#### Scenario: OG paths written to same Game_Info namespace
- **WHEN** the active version is `FO4_OG` and `game_path.py` discovers the OG game installation path
- **THEN** the path is written to `Game_Info.Root_Folder_Game` in `YAML.Game_Local`

#### Scenario: No GameVR_Info keys exist in local YAML
- **WHEN** any version is active and runtime path operations complete
- **THEN** no keys under `GameVR_Info` exist in `YAML.Game_Local`

#### Scenario: Default local YAML template has no GameVR_Info block
- **WHEN** a new local YAML file is generated from the `default_localyaml` template
- **THEN** the generated file contains a `Game_Info` section and does not contain a `GameVR_Info` section

#### Scenario: C++ frontends read XSE path without VR branching
- **WHEN** `scanner.cpp` or `scancontroller.cpp` reads the XSE docs folder path
- **THEN** it reads `"Game_Info.Docs_Folder_XSE"` unconditionally without checking or falling back to `"GameVR_Info.Docs_Folder_XSE"`

#### Scenario: Node CLI reads XSE path without VR branching
- **WHEN** `run-scan.ts` resolves the XSE path from local YAML
- **THEN** it uses `"Game_Info"` as the local key unconditionally, not a VR-conditional key

---

### Requirement: Static metadata reads use the Version Registry, not YAML
Consumers that previously read version-specific metadata (XSE acronym, game version, crashgen name, etc.) from `Game_Info`/`GameVR_Info` YAML sections SHALL instead obtain this data from the active `VersionInfo` in the Version Registry. The YAML database files SHALL NOT contain version-specific static metadata fields.

#### Scenario: XSE acronym comes from registry
- **WHEN** code needs the XSE acronym for the active version
- **THEN** it reads `version_info.xse.acronym` from the registry, not `yaml_settings(str, YAML.Game, "Game_Info.XSE_Acronym")`

#### Scenario: Crashgen name comes from registry
- **WHEN** code needs the crash generator name for the active version
- **THEN** it reads from `version_info.crashgen_versions[].name` from the registry, not `yaml_settings(str, YAML.Game, "Game_Info.CRASHGEN_LogName")`

#### Scenario: Steam ID comes from registry
- **WHEN** code needs the Steam app ID for path detection
- **THEN** it reads `version_info.steam_id` from the registry, not `yaml_settings(int, YAML.Game, "Game_Info.Main_SteamID")`

---

### Requirement: GameVR_Info YAML section is removed
The `GameVR_Info` section SHALL NOT exist in any YAML file (database or local), code path, template, test fixture, or documentation. All data previously in `GameVR_Info` is accessible through the Version Registry's `FO4_VR` entry. The `default_localyaml` template in `CLASSIC Main.yaml` SHALL NOT include a `GameVR_Info` block.

#### Scenario: YAML file has no GameVR_Info section
- **WHEN** `CLASSIC Fallout4.yaml` is loaded
- **THEN** it contains no `GameVR_Info` key

#### Scenario: YAML file has no version-specific fields in Game_Info
- **WHEN** `CLASSIC Fallout4.yaml` is loaded
- **THEN** `Game_Info` does not contain keys like `GameVersion`, `XSE_Acronym`, `CRASHGEN_LogName`, `EXE_HashedOLD`, `XSE_HashedScripts`, etc.

#### Scenario: Non-version YAML data is preserved
- **WHEN** `CLASSIC Fallout4.yaml` is loaded
- **THEN** sections like `Crashgen_Registry`, `Backup ENB`, `Game_Hints`, `Default_CustomINI`, `Warnings_CRASHGEN` remain present and unchanged

#### Scenario: Default local YAML template has no GameVR_Info
- **WHEN** the `default_localyaml` value in `CLASSIC Main.yaml` is inspected
- **THEN** it contains `Game_Info:` but does not contain `GameVR_Info:`

#### Scenario: No test fixtures reference GameVR_Info
- **WHEN** Node binding test fixtures (`cli.fixtures.ts`, `config.spec.ts`, `runtime.node.test.mjs`) are inspected
- **THEN** none contain `GameVR_Info` keys in their YAML literals

---

### Requirement: Python and Rust bindings expose new fields
All new fields (`docs_name`, `steam_id` on `VersionInfo`; `full_name`, `file_count` on `XseConfig`; `acronym`, `dll_file` on `CrashgenConfig`) SHALL be exposed through the PyO3 bindings (`classic-version-registry-py`), NAPI-RS bindings (`classic-node`), and CXX bridge (`classic-cpp-bridge`). The Python wrapper classes in `ClassicLib/support/versions/models.py` SHALL expose corresponding properties.

#### Scenario: Python code accesses new VersionInfo fields
- **WHEN** Python code calls `version_info.docs_name` and `version_info.steam_id`
- **THEN** the correct values are returned from the Rust backend

#### Scenario: Python code accesses new XseConfig fields
- **WHEN** Python code calls `version_info.xse.full_name` and `version_info.xse.file_count`
- **THEN** the correct values are returned from the Rust backend

#### Scenario: Python code accesses new CrashgenConfig fields
- **WHEN** Python code calls `crashgen.acronym` and `crashgen.dll_file`
- **THEN** the correct values are returned from the Rust backend
