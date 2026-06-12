# yaml-app-version-field Specification

## Purpose

Defines the contract for the `CLASSIC_Info.version` field in `CLASSIC Data/databases/CLASSIC Main.yaml`: the YAML stores a bare SemVer value (no product-name prefix), any product-decorated form is constructed by consumers at format time, and value-shape changes to this field trigger a MAJOR bump of the containing file's `schema_version`.

## Requirements

### Requirement: CLASSIC_Info.version stores bare SemVer without display prefix

The value of `CLASSIC_Info.version` in `CLASSIC Data/databases/CLASSIC Main.yaml` SHALL be a bare SemVer string of the form `<MAJOR>.<MINOR>.<PATCH>` with an optional leading `v` or `V` (e.g., `v9.1.0`, `9.1.0`). The string SHALL NOT contain any SemVer prerelease suffix (e.g., `-beta.1`, `-rc.2`, `-alpha`), SemVer build metadata (e.g., `+build.5`), or display-only decoration such as the legacy `CLASSIC ` product-name prefix or trailing descriptive text. Prerelease status for a given published version is signaled by the sibling `is_prerelease` + `version_date` fields defined in this capability, not by annotating the version string.

#### Scenario: Well-formed release version

- **WHEN** `CLASSIC Main.yaml` declares `CLASSIC_Info.version: v9.1.0`
- **THEN** the YAML loader accepts the value as-is
- **AND** `ConfigData.classic_version` holds exactly `"v9.1.0"`

#### Scenario: SemVer prerelease suffix is rejected

- **WHEN** `CLASSIC Main.yaml` declares `CLASSIC_Info.version: v9.2.0-beta.1`
- **THEN** the YAML loader returns `MainYamlVersionError::VersionInvalid`
- **AND** the diagnostic identifies the non-digit component and states that prerelease suffixes and build metadata are not allowed
- **AND** `ConfigData.classic_version` is not populated from the invalid value

#### Scenario: SemVer build metadata is rejected

- **WHEN** `CLASSIC Main.yaml` declares `CLASSIC_Info.version: 9.1.0+build.5`
- **THEN** the YAML loader returns `MainYamlVersionError::VersionInvalid`
- **AND** the diagnostic identifies the non-digit component and states that prerelease suffixes and build metadata are not allowed

#### Scenario: Rejection of legacy decorated value

- **WHEN** `CLASSIC Main.yaml` declares `CLASSIC_Info.version: CLASSIC v9.1.0` under `schema_version: "2.0"` or higher
- **THEN** the value is treated as invalid per this requirement
- **AND** producers (`set_version.ps1`, maintainer workflow) never emit the decorated form

### Requirement: Prerelease status is signaled via `is_prerelease` + `version_date`, not via SemVer suffix

The prerelease status of a published CLASSIC version SHALL be communicated through the sibling `CLASSIC_Info.is_prerelease` boolean (together with the monotonic `CLASSIC_Info.version_date` in `YY.MM.DD` form) in `CLASSIC Data/databases/CLASSIC Main.yaml`. The `CLASSIC_Info.version` field SHALL NOT carry SemVer prerelease or build-metadata suffixes for this purpose. Producers (the maintainer `set_version.ps1` tool and the `publish-yaml-data` workflow) SHALL write these two sibling fields in lockstep with the stable or prerelease intent of the publish, and consumers that need the stable/prerelease distinction SHALL read `is_prerelease` rather than parse the version string.

#### Scenario: Prerelease publish sets the sibling fields

- **WHEN** a maintainer runs `set_version.ps1 -Version "9.2.0" -IsPrerelease $true -Date "26.05.01"`
- **THEN** the tool writes `CLASSIC_Info.version: v9.2.0`, `CLASSIC_Info.version_date: 26.05.01`, and `CLASSIC_Info.is_prerelease: true` to `CLASSIC Main.yaml`
- **AND** the YAML loader accepts the bare-triple version
- **AND** downstream consumers classify the release as a prerelease based on `is_prerelease: true`

#### Scenario: Stable publish sets the sibling fields

- **WHEN** a maintainer runs `set_version.ps1 -Version "9.2.0" -Date "26.05.15"` (without `-IsPrerelease`)
- **THEN** the tool writes `CLASSIC_Info.version: v9.2.0`, `CLASSIC_Info.version_date: 26.05.15`, and `CLASSIC_Info.is_prerelease: false` to `CLASSIC Main.yaml`
- **AND** downstream consumers classify the release as stable based on `is_prerelease: false`

#### Scenario: SemVer suffix passed to the maintainer tool is rejected before any file is written

- **WHEN** a maintainer invokes `set_version.ps1 -Version "9.2.0-beta.1"`
- **THEN** the tool fails at `-Version` parameter validation with a SemVer-shape error
- **AND** no file under the repository is modified
- **AND** the maintainer is directed to use `-IsPrerelease $true` together with a bumped `-Date` instead

#### Scenario: GitHub release-flag gate mirrors `is_prerelease`

- **WHEN** `CLASSIC_Info.is_prerelease: true` is published to the Pages-mirrored YAML-data channel
- **THEN** the `publish-yaml-data` workflow's `gh release --prerelease=true/false` gate (see `yaml-release-publishing`) is aligned with that value for the same release
- **AND** the two prerelease signals (YAML sibling field and GitHub release flag) agree for any single published version

### Requirement: Display decoration is applied by consumers, not stored in YAML

Any consumer that needs the product-decorated form (e.g., `CLASSIC v9.1.0` for crash-log report headers, user-visible labels, or user-agent strings) SHALL construct it by prepending the product-name prefix to the YAML value at format time. Consumers that need the bare SemVer (e.g., `QApplication::setApplicationVersion`, CMake `project(VERSION ...)` guard, update-check comparisons) SHALL consume `CLASSIC_Info.version` directly without stripping a prefix.

#### Scenario: Scanlog report header decoration

- **WHEN** `classic-scanlog-core` generates a report header for a config whose `classic_version` is `"v9.1.0"`
- **THEN** the rendered header contains the literal text `**AUTOSCAN REPORT GENERATED BY CLASSIC v9.1.0**`
- **AND** the `CLASSIC ` prefix is produced by the report generator, not read from the YAML

#### Scenario: Qt application version consumes bare SemVer

- **WHEN** `classic-gui` reads `CLASSIC_Info.version` from `CLASSIC Main.yaml`
- **THEN** it passes the YAML value directly to `QApplication::setApplicationVersion` without a `startsWith("CLASSIC v")` strip step
- **AND** the stored application version equals the raw YAML value (optionally with a single leading `v` trimmed for Qt's display preference)

#### Scenario: CMake build-time guard consumes bare SemVer

- **WHEN** `classic-cli/CMakeLists.txt` extracts `CLASSIC_APP_VERSION` from `CLASSIC Main.yaml` at configure time
- **THEN** the regex matches a line of the form `  version: v<MAJOR>.<MINOR>.<PATCH>` (without any `CLASSIC ` literal)
- **AND** the captured `CLASSIC_APP_VERSION` equals the bare `<MAJOR>.<MINOR>.<PATCH>` component
- **AND** the `PROJECT_VERSION STREQUAL CLASSIC_APP_VERSION` guard still fires on mismatch

### Requirement: schema_version MAJOR bump when CLASSIC_Info.version shape changes

A change to the value-shape of `CLASSIC_Info.version` (such as the removal of the legacy `CLASSIC ` display prefix defined in this spec) SHALL be accompanied by a MAJOR bump of the `schema_version` top-level field in the same YAML file, consistent with the existing `yaml-schema-versioning` MAJOR/MINOR contract.

#### Scenario: Prefix-removal bump

- **WHEN** the YAML file is modified so that `CLASSIC_Info.version` no longer carries the `CLASSIC ` prefix
- **THEN** `schema_version` is incremented from `"1.<X>"` to `"2.0"` in the same commit
- **AND** clients declaring `SchemaCompat { accepted_major: 1, ... }` refuse to load the updated file per the existing `yaml-schema-versioning` gate
