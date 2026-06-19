## MODIFIED Requirements

### Requirement: Releases-API fallback

When the Pages fetch fails with a network or non-304/200 HTTP status, or when the Pages mirror is structurally unreachable, the client SHALL fall back to GitHub Releases by listing releases tagged with a dedicated `app-notification-v*` prefix, downloading `manifest.json` from the newest such release, and parsing it as a notification manifest. The fallback SHALL NOT consult the binary-release "latest" pointer and SHALL NOT rely on asset filename parsing to locate the manifest.

A Pages `404 Not Found` SHALL be classified as "manifest absent" (carried as `UpdateError::NotFound`) rather than as a generic transport error, so the orchestrator can distinguish an unpublished manifest from a Pages outage (5xx), network error, timeout, or rate-limit. When the Pages leg reports the manifest absent AND the Releases fallback finds no release matching the `app-notification-v*` prefix, the check SHALL be treated as "no notification published yet" and SHALL NOT be reported as a fetch failure. A genuine failure on either channel (network error, timeout, HTTP 5xx, rate-limit, or a structurally invalid manifest body) SHALL still surface as an error.

#### Scenario: Pages unreachable falls through to Releases

- **WHEN** the Pages fetch returns a network error or an HTTP 5xx
- **THEN** the client SHALL call the GitHub Releases list endpoint filtered by `app-notification-v*` tags
- **AND** SHALL fetch the named asset `manifest.json` from the newest returned release
- **AND** SHALL parse the body with the same decoder used for Pages

#### Scenario: Fallback manifest populates cache

- **WHEN** the client successfully retrieves a manifest via the Releases fallback
- **THEN** it SHALL write the manifest body and a synthetic cache marker to the cache directory
- **AND** the ETag storage SHALL be left empty (ETag applies only to Pages)

#### Scenario: Genuine dual-channel failure surfaces an error

- **WHEN** the Pages fetch fails with a network error or a non-404 status (e.g. HTTP 5xx, timeout, or rate-limit) AND the Releases fallback also fails
- **THEN** the client SHALL return `UpdateError::NotificationFetchFailed` describing both failure causes
- **AND** SHALL NOT silently report "up to date"
- **AND** SHALL NOT report `NotPublished`

#### Scenario: Absent manifest on both channels reports NotPublished, not an error

- **WHEN** the Pages fetch returns HTTP `404 Not Found` AND the Releases fallback returns no release matching the `app-notification-v*` prefix
- **THEN** the client SHALL return `Ok` with classification `NotPublished`
- **AND** the result SHALL NOT be an `Err`/`NotificationFetchFailed`
- **AND** the result SHALL NOT be reported as `UpToDate`

### Requirement: Classification of installed build against manifest

The client SHALL compare the caller-provided installed version string against `latest_version` and `min_supported_version` using semantic-version ordering (lowercase `v` prefix stripped, `PartialOrd` on `semver::Version`) and SHALL emit one of five classifications: `UpToDate`, `UpdateAvailable`, `DeprecatedClient`, `Unknown`, or `NotPublished`. The first four are produced by comparing a successfully-fetched manifest against the installed build; `NotPublished` is produced when no manifest exists yet (the manifest is absent on both the Pages and Releases channels) and therefore carries no manifest fields. The classification SHALL NOT perform any string-equality comparison against release asset filenames.

#### Scenario: Installed version equal to latest

- **WHEN** the installed version is `9.2.0` and manifest `latest_version` is `9.2.0`
- **THEN** the classification SHALL be `UpToDate`

#### Scenario: Installed version older than latest

- **WHEN** the installed version is `9.1.0` and manifest `latest_version` is `9.2.0`
- **THEN** the classification SHALL be `UpdateAvailable`
- **AND** the result SHALL include the `latest_version`, `published_at`, and `display` payload from the manifest

#### Scenario: Installed version below min_supported_version

- **WHEN** the installed version is `8.5.0` and manifest `min_supported_version` is `9.0.0`
- **THEN** the classification SHALL be `DeprecatedClient`
- **AND** the result SHALL include the `min_supported_version` value

#### Scenario: Installed version cannot be parsed

- **WHEN** the installed version string fails semantic-version parsing
- **THEN** the classification SHALL be `Unknown`
- **AND** a `NotificationError::InstalledVersionParse` SHALL be included in the returned status

#### Scenario: No notification published yet

- **WHEN** no manifest could be fetched because none is published (Pages `404` and no `app-notification-v*` release)
- **THEN** the classification SHALL be `NotPublished`
- **AND** the `latest_version`, `published_at`, `min_supported_version`, `display`, and `parse_error` fields SHALL be empty/absent
- **AND** the consumer SHALL NOT treat this as `UpToDate`

## ADDED Requirements

### Requirement: Absent notification surfaces quietly across consumers

A `NotPublished` classification represents the benign "no update has been published yet" state and SHALL NOT be surfaced to the user as a failure. Across every consumer surface — the C++ bridge DTO, the CLI, the GUI, the TUI, the Python binding, and the Node binding — a `NotPublished` result SHALL NOT trigger an error/warning dialog, SHALL NOT write to a standard-error stream, SHALL NOT produce a non-zero process exit code, and SHALL NOT raise/throw an exception or reject a promise. Silent start-up/background checks SHALL produce no user-visible interruption; explicit user-initiated checks MAY display a benign, non-error informational message (e.g. "No update information is currently available").

#### Scenario: C++ bridge emits a dedicated benign classification

- **WHEN** the core returns classification `NotPublished`
- **THEN** the `NotificationStatusDto.classification` SHALL be the dedicated string `"not_published"`
- **AND** `error_message` SHALL be empty (the DTO SHALL NOT use the `"error"` classification)

#### Scenario: GUI does not pop an error dialog when nothing is published

- **WHEN** the GUI start-up or manual update check receives classification `not_published`
- **THEN** the GUI SHALL NOT show the `"Error checking for updates"` warning dialog
- **AND** a silent start-up check SHALL show no modal dialog at all

#### Scenario: CLI exits successfully without an error message

- **WHEN** the CLI update-check subcommand receives classification `not_published`
- **THEN** the CLI SHALL NOT print to stderr
- **AND** the process SHALL exit with code `0`

#### Scenario: TUI shows a benign status, not a failure

- **WHEN** the TUI update check receives classification `NotPublished`
- **THEN** the status line SHALL NOT read `"Update check failed"`
- **AND** the result SHALL flow through the success/`Ok` path rather than the error path

#### Scenario: Python and Node return a value rather than failing

- **WHEN** a Python or Node consumer invokes the notification check and the core returns `NotPublished`
- **THEN** the Python call SHALL return a `NotificationStatus` whose classification is `NotPublished` rather than raising `ClassicNotificationFetchFailed`
- **AND** the Node promise SHALL resolve to a status whose classification is `NotPublished` rather than rejecting
