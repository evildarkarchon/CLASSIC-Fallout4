## Purpose

Define the client-side runtime flow for discovering, downloading, verifying, installing, and rolling back YAML data bundles from GitHub. Covers the Pages-first manifest lookup with anonymous API fallback, sha256-gated atomic install over a per-user cache directory, and a one-step `.prev`-based rollback. Establishes that the feature operates without any bundled GitHub credential.

## Requirements

### Requirement: Discovery of the latest YAML data release

The client SHALL provide an async API `check_yaml_update(current_schemas: ClientSchemaSet) -> YamlUpdateStatus` that retrieves the published YAML manifest and returns a structured decision without modifying on-disk state. The retrieval SHALL prefer the GitHub Pages manifest URL (`https://<owner>.github.io/<repo>/yaml-data/manifest-latest.json`) and SHALL fall back to the anonymous `GET /releases` endpoint filtered by the `yaml-data-v` tag prefix only when the Pages fetch fails or returns an invalid manifest.

#### Scenario: Update check succeeds via GitHub Pages with an available update

- **WHEN** a user triggers an update check and the manifest fetched from GitHub Pages lists at least one file whose `schema_version` passes the client's per-file `SchemaCompat` check
- **THEN** `check_yaml_update` returns `YamlUpdateStatus::UpdateAvailable { manifest, compatible_files, incompatible_files }`
- **AND** no call was made to `api.github.com`
- **AND** no file has been written to the YAML cache directory

#### Scenario: Pages unreachable, anonymous API fallback succeeds

- **WHEN** the GitHub Pages fetch times out or returns a non-2xx status
- **AND** the anonymous `GET /repos/<owner>/<repo>/releases` call succeeds and yields a valid manifest from the newest `yaml-data-v*` release's `manifest.json` asset
- **THEN** `check_yaml_update` returns a status computed from that manifest
- **AND** the request was sent without any `Authorization` header
- **AND** a warning is logged identifying the Pages failure mode

#### Scenario: No update available

- **WHEN** the fetched manifest shows every file at or below the `schema_version` currently installed in the cache directory
- **THEN** `check_yaml_update` returns `YamlUpdateStatus::UpToDate`

#### Scenario: Update check disabled by user setting

- **WHEN** the user has set `CLASSIC_Settings.Update Check: false`
- **THEN** `check_yaml_update` returns `YamlUpdateStatus::Disabled` without making any HTTP request

#### Scenario: No authentication is ever required in the default flow

- **WHEN** the client runs without a `GITHUB_TOKEN` environment variable set
- **THEN** both the Pages path and the Releases-API fallback complete without producing an authentication error
- **AND** no code path in the YAML update subsystem synthesizes, embeds, or requires a GitHub credential

#### Scenario: Network or API error

- **WHEN** both the Pages fetch and the anonymous API fallback fail
- **THEN** `check_yaml_update` returns `Result::Err` carrying an `UpdateError` variant consistent with `classic-update-core`'s existing error taxonomy
- **AND** the cache directory is unchanged

### Requirement: Asset downloads use only URLs listed in the manifest

Every asset download issued by `apply_yaml_update` SHALL target a URL taken verbatim from the `download_url` field of the fetched manifest. The client SHALL NOT construct asset URLs by string concatenation or by calling the GitHub API for asset metadata.

#### Scenario: Download targets exactly the manifest URL

- **WHEN** `apply_yaml_update` downloads a file whose manifest entry has `download_url: "https://github.com/<owner>/<repo>/releases/download/yaml-data-v2026.04.17/CLASSIC%20Main.yaml"`
- **THEN** the HTTP GET targets that exact URL
- **AND** no preceding call to `api.github.com` is made to resolve the asset

#### Scenario: Manifest entry missing download_url is rejected

- **WHEN** a manifest entry omits `download_url` or contains a non-HTTPS URL
- **THEN** the client returns `Err(UpdateError::ManifestInvalid { .. })` before any download is attempted

### Requirement: Manifest integrity validation

Before acting on a fetched `manifest.json`, the client SHALL validate that its `manifest_version` is supported, its declared files list is non-empty, and every entry carries `name`, `schema_version`, `sha256`, and `size_bytes`.

#### Scenario: Manifest with unsupported manifest_version

- **WHEN** the fetched manifest reports `manifest_version: 2` but the client supports only `1`
- **THEN** `check_yaml_update` returns `YamlUpdateStatus::Unknown { reason: "manifest_version 2 not supported" }` without downloading any file

#### Scenario: Manifest with missing required fields

- **WHEN** a manifest entry lacks `sha256` or `size_bytes`
- **THEN** the client returns `Result::Err(UpdateError::ManifestInvalid { … })` identifying the offending entry

### Requirement: Atomic installation of compatible updates

The client SHALL provide an async API `apply_yaml_update(decision: YamlUpdateStatus) -> YamlUpdateReport` that downloads and installs every file listed in `compatible_files`, using a temp-write + fsync + atomic-rename sequence, and preserves the previously installed copy as `<target>.prev`.

#### Scenario: Successful install with rollback copy preserved

- **WHEN** `apply_yaml_update` runs against a decision containing one compatible file and sha256 verification passes
- **THEN** the target path contains the new file content
- **AND** `<target>.prev` contains the previous file content (if one existed)
- **AND** the report's `installed` list contains the file name and its new `schema_version`

#### Scenario: sha256 mismatch during install

- **WHEN** a downloaded asset's sha256 does not match the manifest's declared value
- **THEN** the temporary file is deleted
- **AND** the original target and any prior `.prev` are unchanged
- **AND** the report's `failed` list contains an entry with reason `ChecksumMismatch`

#### Scenario: Partial batch with mixed outcomes

- **WHEN** `apply_yaml_update` processes two files, one of which fails checksum verification
- **THEN** the successful file is installed atomically and reported under `installed`
- **AND** the failed file leaves the original on disk and is reported under `failed`
- **AND** the overall call returns `Ok(report)`, not `Err`

### Requirement: Rollback to previous YAML copy

The client SHALL provide an API `rollback_yaml_update(file_name) -> RollbackOutcome` that promotes `<target>.prev` back to `<target>` atomically when a `.prev` exists.

#### Scenario: Rollback with a prev file present

- **WHEN** `rollback_yaml_update("CLASSIC Fallout4.yaml")` is invoked and `<cache>/CLASSIC Fallout4.yaml.prev` exists
- **THEN** the `.prev` file becomes the canonical `<cache>/CLASSIC Fallout4.yaml`
- **AND** the current file is swapped to `<cache>/CLASSIC Fallout4.yaml.prev` (one step of rollback retained)
- **AND** the outcome is `RollbackOutcome::RolledBack`

#### Scenario: Rollback with no prev file

- **WHEN** `rollback_yaml_update("CLASSIC Main.yaml")` is invoked and no `.prev` exists
- **THEN** no file is modified
- **AND** the outcome is `RollbackOutcome::NoPreviousVersion`

### Requirement: Cache directory is a dedicated per-user location

The client SHALL resolve the YAML cache directory via `classic-path-core` to a per-user writable location separate from the install directory, and the `YamlSource::Cache` variant of the loader SHALL resolve file paths under this directory.

#### Scenario: Windows cache path

- **WHEN** the client runs on Windows with `%LOCALAPPDATA%` set to `C:\Users\alice\AppData\Local`
- **THEN** the resolved cache path is `C:\Users\alice\AppData\Local\CLASSIC\yaml-cache\`

#### Scenario: Cache directory creation on first use

- **WHEN** the cache directory does not yet exist and the client attempts to install a YAML update
- **THEN** the directory is created with default permissions before any file write is attempted

### Requirement: Interrupted install is self-healing on next startup

The YAML loader SHALL, at startup, detect a post-rename crash state in which `<target>` is missing but `<target>.prev` exists, and promote `.prev` back to the canonical name before proceeding.

#### Scenario: Missing target with prev present

- **WHEN** the loader starts and `<cache>/CLASSIC Main.yaml` does not exist but `<cache>/CLASSIC Main.yaml.prev` does
- **THEN** the loader renames `.prev` to the canonical name before attempting to parse it
- **AND** logs a warning that a prior install was recovered

### Requirement: Update subsystem reuses the shared Tokio runtime and GithubClient

All HTTP calls in this subsystem SHALL use the shared Tokio runtime from `classic-shared-core::get_runtime()` and the existing `classic-update-core::GithubClient`. No new runtimes or HTTP clients are introduced.

#### Scenario: No independent runtime

- **WHEN** the source of `classic-update-core` is inspected for the new YAML-update module
- **THEN** no call to `tokio::runtime::Runtime::new()` or equivalent exists
- **AND** all async work is spawned on the shared runtime
