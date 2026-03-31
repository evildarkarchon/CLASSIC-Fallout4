## MODIFIED Requirements

### Requirement: Runtime path cache uses a single namespace
All runtime-discovered filesystem paths (game root, docs root, exe path, data folders, etc.) SHALL be stored under a single `Game_Info` namespace in `YAML.Game_Local`, regardless of whether the active version is VR, OG, NG, or AE. The `GameVR_Info` namespace has been fully removed from all code paths, YAML templates, and documentation. Consumers SHALL use `"Game_Info.{key}"` unconditionally when reading or writing runtime paths. No code path, template, or fixture SHALL reference the `GameVR_Info` namespace.

#### Scenario: VR paths written to Game_Info namespace
- **WHEN** the active version is `FO4_VR` and the game installation path is discovered
- **THEN** the path is written to `Game_Info.Root_Folder_Game` in `YAML.Game_Local`

#### Scenario: OG paths written to same Game_Info namespace
- **WHEN** the active version is `FO4_OG` and the game installation path is discovered
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

## REMOVED Requirements

### Requirement: get_config_suffix API exists
**Reason**: The `get_config_suffix()` function in `classic-registry-core` (and its Python/Node binding exports) existed solely to build `"GameVR_Info"` key paths. With `GameVR_Info` fully removed and all consumers using `"Game_Info"` unconditionally, this function has no legitimate callers.
**Migration**: Callers that need to determine VR status should use `is_vr_version()` instead. No caller should construct `"GameVR_Info"` key paths.
