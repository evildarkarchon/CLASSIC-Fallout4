## ADDED Requirements

### Requirement: Notification manifest schema

The system SHALL define a JSON notification-manifest shape published at a well-known URL and parsed by `classic-update-core`. The manifest SHALL contain a root `manifest_version` (MAJOR.MINOR string matching `^\d+\.\d+$`), a `release_tag` string matching the binary-release tag pattern, a `latest_version` string matching semantic-version format, a `published_at` RFC 3339 timestamp, an optional `min_supported_version` string, and an optional `display` object containing `title`, `body`, and `cta_url` fields. The manifest SHALL NOT contain any file payload, SHA-256 checksum, or asset download URL.

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

#### Scenario: Pages unreachable falls through to Releases

- **WHEN** the Pages fetch returns a network error or an HTTP 5xx
- **THEN** the client SHALL call the GitHub Releases list endpoint filtered by `app-notification-v*` tags
- **AND** SHALL fetch the named asset `manifest.json` from the newest returned release
- **AND** SHALL parse the body with the same decoder used for Pages

#### Scenario: Fallback manifest populates cache

- **WHEN** the client successfully retrieves a manifest via the Releases fallback
- **THEN** it SHALL write the manifest body and a synthetic cache marker to the cache directory
- **AND** the ETag storage SHALL be left empty (ETag applies only to Pages)

#### Scenario: Both channels unavailable surfaces an error

- **WHEN** Pages and Releases both fail (network or non-2xx) within the fetch attempt
- **THEN** the client SHALL return a `NotificationError` describing both failure causes
- **AND** SHALL NOT silently report "up to date"

### Requirement: Classification of installed build against manifest

The client SHALL compare the caller-provided installed version string against `latest_version` and `min_supported_version` using semantic-version ordering (lowercase `v` prefix stripped, `PartialOrd` on `semver::Version`) and SHALL emit one of four classifications: `UpToDate`, `UpdateAvailable`, `DeprecatedClient`, or `Unknown`. The classification SHALL NOT perform any string-equality comparison against release asset filenames.

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
