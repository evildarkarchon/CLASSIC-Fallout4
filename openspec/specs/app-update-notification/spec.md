## Purpose

Define requirements for the payload-free app-update notification channel consumed by `classic-update-core`: the notification manifest schema, the Pages-first fetch with ETag caching and Releases-API fallback, classification of the installed build against the manifest, binding-surface exposure across all three bindings, parity-gate coverage, and the consumer migration from the legacy `GithubClient`-based update check.

## Requirements

### Requirement: Notification manifest schema

The system SHALL define a JSON notification-manifest shape published at a well-known URL and parsed by `classic-update-core`. The manifest SHALL contain a root `manifest_version` (MAJOR.MINOR string matching `^\d+\.\d+$`), a `release_tag` string matching the binary-release tag pattern, a `latest_version` string matching semantic-version format, a `published_at` RFC 3339 timestamp, an optional `min_supported_version` string, and an optional `display` object containing `title`, `body`, and `cta_url` fields. When `display.cta_url` is present, it SHALL be an `https://` URL; the client SHALL refuse non-HTTPS schemes (`http://`, `file://`, `javascript:`, `data:`, etc.) so a typo'd or compromised manifest cannot downgrade users onto an unauthenticated destination at the moment they are being asked to fetch an update. The manifest SHALL NOT contain any file payload, SHA-256 checksum, or asset download URL.

#### Scenario: Valid manifest parses into typed DTO

- **WHEN** the client fetches a manifest whose root object has `manifest_version: "1.0"`, `release_tag: "v9.2.0"`, `latest_version: "9.2.0"`, `published_at: "2026-05-01T12:00:00Z"`, and no `display` block
- **THEN** the parser SHALL return an `AppNotificationManifest` value whose fields match the source JSON
- **AND** the `display` field SHALL be `None`

#### Scenario: Unknown fields are tolerated

- **WHEN** the client fetches a manifest containing an unrecognized root-level field (for forward compatibility)
- **THEN** parsing SHALL succeed
- **AND** the unknown field SHALL be ignored without warning

#### Scenario: Missing required field rejects manifest

- **WHEN** a manifest lacks `manifest_version`, `latest_version`, or `published_at`
- **THEN** parsing SHALL return a typed decode error identifying the missing field
- **AND** the client SHALL NOT treat the absent manifest as "up to date"

#### Scenario: Non-HTTPS cta_url rejects manifest

- **WHEN** a manifest's `display.cta_url` is present but does not parse as a URL with the `https` scheme (e.g. `"http://example/changelog"`, `"javascript:alert(1)"`, `"file:///etc/passwd"`)
- **THEN** the runtime validator SHALL return `UpdateError::NotificationDecode { field: "display.cta_url" }`
- **AND** the manifest SHALL NOT classify or reach a UI surface
- **AND** the publish-side validator (`tools/publish_app_notification/validate.py`) SHALL reject the same shapes at publish time so the bad manifest never ships in the first place

### Requirement: Pages-first fetch with ETag caching

The client SHALL fetch the notification manifest from `https://<owner>.github.io/<repo>/app-notification/manifest-latest.json` first and persist an ETag alongside the cached JSON body. On subsequent fetches the client SHALL send the stored ETag as `If-None-Match`; on `304 Not Modified` it SHALL reuse the cached body. The cache location SHALL live inside the CLASSIC platform cache directory as defined by `classic-path-core`, under a sub-path distinct from the YAML-update cache.

#### Scenario: Fresh fetch stores ETag and body

- **WHEN** the client has no cached manifest and fetches from Pages successfully with a `200 OK` and `ETag: "abc"`
- **THEN** the client SHALL write `manifest-latest.json` and `manifest.etag` to its cache directory
- **AND** the returned in-memory manifest SHALL reflect the `200` body

#### Scenario: Conditional revalidation reuses cache

- **WHEN** the client has a cached manifest and ETag and the server replies with `304 Not Modified`
- **THEN** the client SHALL return the cached manifest body without writing the cache files again
- **AND** the check SHALL complete without an additional body download

#### Scenario: Cache directory is separate from YAML cache

- **WHEN** both YAML-update and app-notification caches exist on the same machine
- **THEN** the on-disk layout SHALL place app-notification artifacts at `<platform-cache>/CLASSIC/app-notification/` (or platform equivalent)
- **AND** corruption of one cache SHALL NOT affect the other

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

### Requirement: Absent notification surfaces quietly across consumers

A `NotPublished` classification represents the benign "no update has been published yet" state and SHALL NOT be surfaced to the user as a failure. Across every consumer surface - the C++ bridge DTO, the CLI, the GUI, the TUI, the Python binding, and the Node binding - a `NotPublished` result SHALL NOT trigger an error/warning dialog, SHALL NOT write to a standard-error stream, SHALL NOT produce a non-zero process exit code, and SHALL NOT raise/throw an exception or reject a promise. Silent start-up/background checks SHALL produce no user-visible interruption; explicit user-initiated checks MAY display a benign, non-error informational message (e.g. "No update information is currently available").

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

### Requirement: Binding surface exposes notification check on all three bindings

The C++ bridge, Node binding, and Python binding SHALL each expose a single notification-check entry point whose return value carries the classification, latest version, published-at timestamp, optional min-supported version, and optional display payload. The CXX surface SHALL emit a dedicated DTO rather than reusing `UpdateCheckResult`. The Node surface SHALL expose the function via camelCase (`checkAppNotification`) and refresh `index.d.ts` accordingly. The Python surface SHALL expose the function via snake_case (`check_app_notification`) and refresh the `.pyi` stub accordingly.

#### Scenario: CXX binding returns structured DTO

- **WHEN** a C++ caller invokes `classic::update::check_app_notification(owner, repo, installed_version)`
- **THEN** the return SHALL be a `NotificationStatusDto` with fields `classification`, `latest_version`, `published_at`, `min_supported_version`, and optional `display`
- **AND** the old `UpdateCheckResult` SHALL NOT be reused for notification results

#### Scenario: Node binding exposes camelCase function

- **WHEN** a Node consumer imports `@evildarkarchon/classic-node` and calls `checkAppNotification({ owner, repo, installedVersion })`
- **THEN** the returned promise SHALL resolve to an object whose shape matches `JsNotificationStatus`
- **AND** the refreshed `index.d.ts` SHALL declare the new function and type

#### Scenario: Python binding exposes snake_case function

- **WHEN** a Python consumer calls `classic_update_py.check_app_notification(owner, repo, installed_version)`
- **THEN** the return SHALL be a typed object whose dataclass-style fields match `NotificationStatus`
- **AND** the refreshed `.pyi` stub SHALL declare the function and type

### Requirement: Binding parity gates cover the new surface

The CXX, Node, and Python parity gates SHALL fail until their baselines are updated in the same change that introduces the notification-check API, ensuring the new entry point is exposed on all three bindings simultaneously.

#### Scenario: Baseline-out-of-date fails CXX gate

- **WHEN** the new `check_app_notification` CXX entry point is added but `cpp-bindings/classic-cpp-bridge/parity-artifacts/baseline/` is not refreshed
- **THEN** the CXX parity gate SHALL exit non-zero

#### Scenario: Baseline-out-of-date fails Node gate

- **WHEN** the new `checkAppNotification` NAPI entry point is added but the Node parity baseline is not refreshed
- **THEN** `bun run parity:gate` SHALL exit non-zero

#### Scenario: Baseline-out-of-date fails Python gate

- **WHEN** the new `check_app_notification` PyO3 entry point is added but the Python parity baseline is not refreshed
- **THEN** `python tools/python_api_parity/check_parity_gate.py --repo-root .` SHALL exit non-zero

### Requirement: Consumer migration from GithubClient-based update check

The CLI, GUI, and TUI update-check call sites SHALL migrate from `GithubClient::get_latest_release` + `has_update` + asset-filename comparison to `classic_update_core::notification::check_app_notification`. The legacy `GithubClient` update-check path SHALL remain available as a compat surface used only by diagnostic tooling and SHALL NOT be invoked by user-facing start-up checks after the migration.

#### Scenario: TUI update check uses notification API

- **WHEN** the TUI start-up check runs in `ui-applications/classic-tui/src/app.rs`
- **THEN** it SHALL call `check_app_notification(...)` rather than `GithubClient::get_latest_release(...)`
- **AND** the `AsyncMessage` payload SHALL carry classification and display fields rather than a single free-form string

#### Scenario: GUI update controller uses notification API

- **WHEN** the GUI update controller runs its periodic/manual check
- **THEN** it SHALL invoke the CXX `check_app_notification` entry point and render the returned `NotificationStatusDto`

#### Scenario: CLI update check uses notification API

- **WHEN** the CLI update-check subcommand runs
- **THEN** it SHALL invoke the notification API and format the returned classification for the terminal
