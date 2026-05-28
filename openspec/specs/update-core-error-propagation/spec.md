## Purpose

Define requirements for propagating recoverable update-core and orchestrator initialization errors instead of panicking.

## Requirements

### Requirement: GitHubClient constructors return Result
`GitHubClient::new()` and `GitHubClient::new_with_token()` SHALL return `Result<Self, UpdateError>` to propagate HTTP client initialization failures rather than panicking.

#### Scenario: Successful construction
- **WHEN** the reqwest HTTP client builds successfully
- **THEN** both constructors SHALL return `Ok(GitHubClient { ... })`

#### Scenario: TLS initialization failure surfaces as error
- **WHEN** `reqwest::ClientBuilder::build()` returns an error (e.g., TLS backend unavailable)
- **THEN** the constructor SHALL return `Err(UpdateError::ClientBuild(...))` instead of panicking

### Requirement: UpdateError includes a ClientBuild variant
The `UpdateError` enum SHALL include a `ClientBuild(reqwest::Error)` variant representing HTTP client initialization failures.

#### Scenario: Error variant is displayable
- **WHEN** an `UpdateError::ClientBuild` is formatted with `Display`
- **THEN** the message SHALL include a human-readable description of the underlying reqwest error

### Requirement: FormIDAnalyzerCore creation errors propagate in orchestrator
The two `FormIDAnalyzerCore::new(...).expect(...)` call sites in `orchestrator.rs` SHALL be replaced with `?`-propagation.

#### Scenario: Creation error propagates to caller
- **WHEN** `FormIDAnalyzerCore::new()` returns `Err` (hypothetical future case)
- **THEN** the orchestrator function SHALL return that error to its caller rather than panicking

#### Scenario: Current behavior unchanged when Ok
- **WHEN** `FormIDAnalyzerCore::new()` returns `Ok` (current behavior)
- **THEN** the orchestrator SHALL continue processing identically to before this change

### Requirement: NotificationError propagates manifest fetch, decode, and classification failures

The `classic-update-core` crate SHALL introduce a `NotificationError` error family (either as a dedicated enum or as a grouped set of variants on `UpdateError`) that covers the notification-check pipeline without overloading binary-release error variants. The family SHALL include distinct variants for: Pages fetch failure, Releases-fallback fetch failure, manifest decode failure (including missing required fields), installed-version parse failure, and cache I/O failure. Every variant SHALL implement `Display` with a human-readable description and SHALL be convertible into each binding's public error shape per `docs/api/error-contract.md`.

#### Scenario: Pages fetch failure surfaces as typed error

- **WHEN** the Pages GET returns an HTTP 5xx and the Releases fallback also fails
- **THEN** the returned `Result` SHALL be an `Err(NotificationError::FetchFailed { .. })` (or equivalent tagged variant) referencing both channels
- **AND** no panic or `unwrap` SHALL be reachable on the error path

#### Scenario: Manifest decode failure identifies missing field

- **WHEN** the fetched manifest body is well-formed JSON but lacks `latest_version`
- **THEN** the returned `Err` SHALL be a `NotificationError::Decode { field: "latest_version", .. }` variant
- **AND** the `Display` rendering SHALL include the missing field name

#### Scenario: Installed-version parse failure surfaces distinctly

- **WHEN** the caller passes an installed-version string that fails semver parsing
- **THEN** the returned `Err` SHALL be a `NotificationError::InstalledVersionParse { input, .. }` variant
- **AND** the variant SHALL NOT be reused for manifest decode failures

#### Scenario: Cache I/O failure surfaces distinctly

- **WHEN** the cache directory cannot be created or the ETag file cannot be read or written
- **THEN** the returned `Err` SHALL be a `NotificationError::CacheIo { path, source, .. }` variant referencing the offending path

### Requirement: Binding error shapes mirror per-language contract

The notification-check entry point SHALL propagate errors through the bindings using the existing per-language contract: C++ SHALL continue to emit empty-string sentinels on its existing `UpdateCheckResult`-style DTO for failure and populate a new `error_message` field on `NotificationStatusDto`; Node SHALL surface the variant-keyed discriminator on the rejected `Error.message` as a stable `"<CODE>: "` prefix (the napi-rs 3.x async surface threads `Error<Status>` where `Status` is a fixed C-style enum, so a custom `Error.code` cannot survive the async FFI boundary; the message-prefix shape preserves variant discrimination and matches the equivalent contract on `loadMainYamlVersion`); Python SHALL raise a typed exception subclass, `ClassicNotificationError`, that subclasses the existing PyO3 update error hierarchy.

#### Scenario: CXX DTO on error

- **WHEN** `check_app_notification` on the C++ bridge cannot fetch or parse the manifest
- **THEN** the returned `NotificationStatusDto` SHALL have `classification = "error"`, `error_message` populated with the `Display` rendering of the Rust `NotificationError`, and empty-string sentinels on other fields per `error-contract.md`

#### Scenario: Node error message prefix on failure

- **WHEN** `checkAppNotification` on the Node binding cannot fetch or parse the manifest
- **THEN** the returned promise SHALL reject with an `Error` whose `message` is prefixed by one of the variant-keyed tokens followed by `": "` — `"FETCH_FAILED: "`, `"DECODE: "`, `"INSTALLED_VERSION_PARSE: "`, `"CACHE_IO: "`, or `"UPDATE_ERROR: "` (catch-all for non-notification variants surfaced through the same path)
- **AND** consumers SHALL discriminate via `err.message.startsWith("FETCH_FAILED:")` (or equivalent for the other tokens). The shape divergence from the general Node-binding `Error.code` convention is intentional and documented at `docs/api/error-contract.md` § "Notification errors"; it exists because the napi-rs 3.x `#[napi] async fn` surface threads `napi::Error<Status>` through `execute_tokio_future_with_finalize_callback`, and `Status` is a fixed C-style enum with no room for custom per-variant codes

#### Scenario: Python typed exception on failure

- **WHEN** `check_app_notification` on the Python binding cannot fetch or parse the manifest
- **THEN** the call SHALL raise a `ClassicNotificationError` subclass keyed to the underlying variant
- **AND** existing `ClassicUpdateError` catch blocks SHALL also catch the new subclass because it extends the existing hierarchy
