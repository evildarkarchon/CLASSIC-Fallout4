## MODIFIED Requirements

### Requirement: Registry is configurable via YAML without code changes
The per-crashgen settings registry SHALL be driven by YAML configuration in `CLASSIC Fallout4.yaml` (and equivalent game-specific YAML files). Adding a new crashgen entry, updating its ignore list, assigning existing named checks, or updating existing TOML/settings criteria and user-facing messages SHALL require only a YAML change. Implementing a new predicate/operator or a brand-new evaluator capability MAY require a code change. The crashgen identity fields (`CRASHGEN_LogName`, `CRASHGEN_Acronym`, `CRASHGEN_DLL_File`, `CRASHGEN_LatestVer`) previously stored in `Game_Info`/`GameVR_Info` are NOT part of this registry — they are now sourced from the Version Registry's `CrashgenConfig` entries. The `Crashgen_Registry` section in YAML is exclusively for per-crashgen settings validation configuration.

#### Scenario: New crashgen entry added via YAML
- **WHEN** a new crashgen entry is added to the YAML `Crashgen_Registry` with an `ignore_keys` list and `checks: []`
- **THEN** logs from that crashgen use the new entry without any code deployment

#### Scenario: Existing named check assigned to new crashgen
- **WHEN** an already-implemented named check (e.g., `achievements`) is added to a new crashgen's `checks` list in YAML
- **THEN** that check runs for the new crashgen without any code change

#### Scenario: Existing rule criteria and message text updated in YAML
- **WHEN** a `Crashgen_Registry` entry updates `settings_rules` predicates, expected values, or message templates for an existing rule
- **THEN** scanlog and scangame settings checks use the new behavior and text without requiring source code changes

#### Scenario: Crashgen identity comes from Version Registry not YAML
- **WHEN** code needs the crashgen name, acronym, DLL filename, or latest version for the active game version
- **THEN** it reads from the Version Registry's `CrashgenConfig` entry, not from `Game_Info.CRASHGEN_*` or `GameVR_Info.CRASHGEN_*` YAML keys
