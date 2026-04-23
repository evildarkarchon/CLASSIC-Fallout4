# `classic-update-core` API Guide

Contributor-facing API documentation for [`business-logic/classic-update-core/`](../../business-logic/classic-update-core).

Crate metadata:

- Crate: `classic-update-core`
- Description: `Pure Rust business logic for auto-update system (NO PyO3)`

This crate is CLASSIC's small async update-check layer for GitHub-hosted releases. It owns GitHub release DTOs, a reusable `GithubClient`, strict semver comparison for release tags, and the crate-specific `UpdateError` model.

It is an async business-logic crate, but it does not own or expose a Tokio runtime. In this repository, callers are expected to run its async methods on CLASSIC's shared runtime from [`classic-shared-core`](classic-shared-core.md).

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- query GitHub releases for a repository's latest published release
- enumerate repository releases and optionally filter out prereleases or drafts
- compare a local version string against a GitHub tag using strict semver precedence
- surface release metadata such as notes, asset names, asset sizes, and browser download URLs
- build update-check wrappers in bindings, TUIs, or other frontends without embedding GitHub JSON parsing logic there

Do not use this crate for:

- owning a Tokio runtime or creating a second runtime for update work
- lenient Fallout/game-version parsing; this crate intentionally uses strict semver instead
- downloading assets to disk, resuming downloads, verifying checksums, or unpacking archives
- general-purpose GitHub API coverage beyond the small releases-focused surface in `github.rs`
- non-GitHub update providers

Those concerns live in callers, binding layers, or other crates such as [`classic-shared-core`](classic-shared-core.md) and [`classic-version-core`](classic-version-core.md).

---

## Module And API Map

This crate exposes four public modules plus a small root-level convenience surface.

## Root-level API

- `VERSION` - crate package version from Cargo metadata
- `Result<T>` - `std::result::Result<T, UpdateError>` re-export
- `UpdateError` - crate-wide error enum re-export
- `GithubClient`, `GithubRelease`, `GithubAsset` - GitHub API types re-exported from `github`
- `AppNotificationDisplay`, `AppNotificationManifest`, `Classification`, `NotificationStatus`, `check_app_notification`, `check_app_notification_with`, `classify`, `fetch_app_notification_manifest`, `fetch_via_releases_fallback`, `build_app_notification_pages_url` - app-update notification surface re-exported from `notification`

## Public modules

### `error`

- `UpdateError` - typed update/checking error enum
- `Result<T>` - crate-local result alias

### `github`

**Compat-only surface.** User-facing update checks go through the `notification` module; `github` is retained for diagnostic tooling and legacy test harnesses. `GithubClient::get_latest_release` carries `#[deprecated(note = "Use classic_update_core::notification::check_app_notification instead")]` and will emit a warning at every use site.

- `GithubClient` - async GitHub releases client
- `GithubRelease` - deserializable release DTO
- `GithubAsset` - deserializable asset DTO

### `notification`

Payload-free app-update notification channel: fetches a published JSON manifest from GitHub Pages (with ETag caching) or falls back to the `app-notification-v*` Releases namespace. See [`app-update-notification-delivery.md`](app-update-notification-delivery.md) for the full cross-crate delivery contract.

- `AppNotificationManifest` - decoded manifest DTO (`manifest_version`, `release_tag`, `latest_version`, `published_at`, optional `min_supported_version`, optional `display`)
- `AppNotificationDisplay` - optional display payload (`title`, `body`, `cta_url`)
- `Classification` - discriminated outcome (`UpToDate`, `UpdateAvailable`, `DeprecatedClient`, `Unknown`)
- `NotificationStatus` - classification + echoed manifest fields
- `check_app_notification(owner, repo, installed_version)` - orchestrator; Pages-first with Releases fallback
- `check_app_notification_with(client, pages_url, cache_dir, installed)` - testable form that takes a caller-built `GithubClient` and explicit cache dir
- `classify(installed, &manifest)` - pure classifier
- `fetch_app_notification_manifest(client, pages_url, cache_dir)` - low-level Pages fetch
- `fetch_via_releases_fallback(client)` - low-level Releases-API fallback
- `build_app_notification_pages_url(client)` - canonical Pages URL builder (shared with binding layers)

Error variants for notification failures live on `UpdateError` as `NotificationFetchFailed`, `NotificationDecode`, `NotificationInstalledVersionParse`, and `NotificationCacheIo` (design D-05 — nested on `UpdateError` rather than a sibling enum so the per-binding error mapping does not double). `ManifestUnsupportedVersion` is shared with YAML updates but can also surface directly from the notification path when a fetched notification manifest advertises a newer `manifest_version` major. See [`error-contract.md`](error-contract.md) for per-binding shapes.

Contributor note:

- there are no public traits in this crate today
- the `notification` module is implemented in [`src/notification.rs`](../../business-logic/classic-update-core/src/notification.rs); the shared Pages-first + ETag helper it uses lives in [`src/manifest_fetch.rs`](../../business-logic/classic-update-core/src/manifest_fetch.rs)
- almost all legacy GitHub-API behavior lives in [`src/github.rs`](../../business-logic/classic-update-core/src/github.rs); the module header flags it as compat-only

---

## Public API Surface

## `VERSION`

`VERSION` is a root-level constant:

```rust
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
```

Current behavior:

- it reflects the crate package version, not the target application's installed version
- tests in `src/lib.rs` assert that it is parseable as semver

## `GithubRelease`

`GithubRelease` is the main response DTO returned by GitHub release queries.

Fields:

- `tag_name`
- `name`
- `body`
- `prerelease`
- `draft`
- `html_url`
- `assets: Vec<GithubAsset>`
- `created_at`
- `published_at: Option<String>`

Derived traits visible in source:

- `Debug`, `Clone`, `Serialize`, `Deserialize`

Contributor notes:

- timestamps remain raw strings; this crate does not parse them into chrono/time types
- `body` is passed through as GitHub returns it, typically Markdown release notes
- `published_at` can be `None`, especially for drafts

## `GithubAsset`

`GithubAsset` represents one downloadable file attached to a release.

Fields:

- `name`
- `size: u64`
- `browser_download_url`
- `content_type`
- `download_count: u64`

Derived traits visible in source:

- `Debug`, `Clone`, `Serialize`, `Deserialize`

Important scope boundary:

- this crate only surfaces asset metadata and direct browser download URLs
- there is no API here to choose the right asset for a platform, stream the bytes, or save the file locally

## `GithubClient`

`GithubClient` is the crate's main integration type.

Construction:

- `GithubClient::new(owner, repo) -> Result<GithubClient>`
- `GithubClient::with_token(owner, repo, token) -> Result<GithubClient>`

Read-only accessors:

- `owner() -> &str`
- `repo() -> &str`
- `repo_url() -> String`

Network/version methods:

- `get_latest_release().await -> Result<GithubRelease>`
- `get_all_releases(include_prereleases, include_drafts).await -> Result<Vec<GithubRelease>>`
- `has_update(current_version, latest_version) -> Result<bool>`

Behavior visible in source:

- both constructors build a `reqwest::Client` with a 30 second timeout
- the user agent is `CLASSIC-Update/<crate-version>`
- `new()` calls `dotenvy::dotenv()` first, then reads `GITHUB_TOKEN` from the environment
- empty token strings are filtered out and treated as `None`
- when a token exists, requests send `Authorization: Bearer <token>`
- the client is `Clone`, and cloning is cheap because `reqwest::Client` is internally shared

Contributor notes:

- current source does not validate owner or repo strings beyond storing them and interpolating them into URLs
- `base_url` is stored internally and defaults to `https://api.github.com`; there is no public setter for tests or alternate GitHub hosts

## `get_latest_release()`

`get_latest_release()` is the one-shot "check the newest published release" API.

Source-visible flow:

1. Build `GET https://api.github.com/repos/{owner}/{repo}/releases/latest`.
2. Add `Authorization` when a token is configured.
3. Send the request with `reqwest`.
4. On `200 OK`, deserialize the JSON body into `GithubRelease`.
5. On `404 Not Found`, return `UpdateError::NotFound("No releases found".to_string())`.
6. On `403 Forbidden`, return `UpdateError::RateLimitExceeded(None)`.
7. On any other HTTP status, return `UpdateError::GithubError(format!("API returned status {}", status))`.

Important behavior:

- the method depends on GitHub's `/releases/latest` endpoint rather than manually sorting all releases
- current source does not inspect rate-limit headers, so `RateLimitExceeded` always carries `None`
- JSON decode failures from `response.json().await` are surfaced as `UpdateError::HttpError`, not `UpdateError::JsonError`

## `get_all_releases()`

`get_all_releases(include_prereleases, include_drafts)` fetches the repository's releases collection and then filters it locally.

Source-visible flow:

1. Build `GET https://api.github.com/repos/{owner}/{repo}/releases`.
2. Deserialize the response body into `Vec<GithubRelease>` on `200 OK`.
3. Retain each release only if it passes the two boolean filters.
4. Return the filtered vector.

Important behavior:

- filtering happens after the full JSON payload is fetched
- the method preserves the order returned by the GitHub API; current source does not perform an extra sort step
- `403 Forbidden` becomes `UpdateError::RateLimitExceeded(None)`
- other non-`200` statuses become `UpdateError::GithubError(...)`

## `has_update()`

`has_update(current_version, latest_version) -> Result<bool>` compares two version strings using `semver::Version` ordering.

Source-visible behavior:

- strips a leading lowercase `v` before parsing
- uses strict `semver::Version::parse`, including prerelease and build metadata support
- returns `true` only when `latest_version > current_version`
- returns `false` for equal versions or downgrade cases

Important edge cases from the implementation and tests:

- `v1.2.3` parses, but uppercase `V1.2.3` does not because only lowercase `v` is stripped
- two-part game-style versions like `1.10` are invalid here even though they are accepted by [`classic-version-core`](classic-version-core.md)
- four-part version strings like `1.0.0.0` are invalid here
- prerelease ordering follows semver rules, so `1.0.0-alpha < 1.0.0-beta < 1.0.0`
- build metadata does not affect semver precedence

That difference from [`classic-version-core`](classic-version-core.md) is intentional: GitHub release tags are treated as proper semver, not as lenient game-version text.

---

## Update Check, Release Parsing, And Download Flow

This crate's public API supports a short update-check pipeline.

## Flow A: latest release check

1. Construct `GithubClient` for a target repo.
2. Call `get_latest_release().await`.
3. Inspect the returned `GithubRelease` fields such as `tag_name`, `body`, and `assets`.
4. Call `has_update(current_version, &release.tag_name)` if the caller wants a semver-based update decision.

This is the exact pattern used by the TUI in [`ui-applications/classic-tui/src/app.rs:661`](../../ui-applications/classic-tui/src/app.rs#L661).

## Flow B: release listing with caller-side policy

1. Construct `GithubClient`.
2. Call `get_all_releases(include_prereleases, include_drafts).await`.
3. Apply caller-side selection logic from the returned `Vec<GithubRelease>`.

Use this when "latest release" is not enough, such as when a frontend wants to surface prereleases or let contributors inspect multiple release assets.

## Release parsing details

- release JSON is deserialized directly into `GithubRelease` and `GithubAsset`
- no custom timestamp parsing, Markdown rendering, or asset-type classification happens here
- release notes and timestamps remain opaque strings from GitHub's API

## Download flow boundary

The crate stops at metadata discovery.

- `GithubRelease.assets` gives callers asset names and `browser_download_url` values
- there is no public method here that downloads an asset body
- there is no checksum, signature, retry, resume, or archive extraction API in current source

If contributors add real download/install behavior later, that is a public-surface expansion and this document should be updated with the exact API rather than assuming one exists now.

---

## Error Handling Model

This crate uses a single public error enum, `UpdateError`.

Variants:

- `ClientBuild(reqwest::Error)`
- `HttpError(reqwest::Error)`
- `JsonError(serde_json::Error)`
- `VersionError(semver::Error)`
- `UrlError(url::ParseError)`
- `GithubError(String)`
- `RateLimitExceeded(Option<std::time::Duration>)`
- `NotFound(String)`
- `Timeout`
- `Generic(String)`

## How the current APIs use those variants

- `GithubClient::new()` and `GithubClient::with_token()` can return `ClientBuild`
- request send failures and `response.json().await` failures in `github.rs` return `HttpError`
- `has_update()` returns `VersionError` for invalid semver input
- GitHub non-success statuses are mapped manually to `NotFound`, `RateLimitExceeded`, or `GithubError`

## Public variants that are currently wider than the visible API usage

Source-observed notes:

- `JsonError` is public, but current public GitHub methods do not visibly construct it because JSON parsing happens through `reqwest::Response::json()` and is mapped to `HttpError`
- `UrlError` is public, but this crate's current public API does not expose any URL parser that visibly returns it
- `Timeout` and `Generic` are public, but current `GithubClient` methods do not explicitly construct them

That means the error enum is slightly broader than the currently exercised surface. Document new behavior explicitly if future APIs start using those variants directly.

---

## Async And Runtime Notes

This crate is async, but runtime ownership stays outside the crate.

- `get_latest_release()` and `get_all_releases()` are async methods and require an external Tokio runtime
- `classic-update-core` does not re-export `get_runtime()` and does not create a process-global runtime itself
- repo guidance still applies: run this crate on the shared Tokio runtime from [`classic-shared-core`](classic-shared-core.md) instead of adding another runtime

In-repo runtime patterns:

- the TUI spawns update checks with `classic_shared_core::get_runtime().spawn(...)` in [`ui-applications/classic-tui/src/app.rs:672`](../../ui-applications/classic-tui/src/app.rs#L672)
- the C++ bridge blocks on `get_latest_release()` with the shared runtime in [`cpp-bindings/classic-cpp-bridge/src/update.rs:33`](../../cpp-bindings/classic-cpp-bridge/src/update.rs#L33)
- the Node bindings clone the shared runtime handle and spawn async update work in [`node-bindings/classic-node/src/update.rs:220`](../../node-bindings/classic-node/src/update.rs#L220)

Contributor note:

- `Cargo.toml` depends on `classic-shared-core`, but the current source in this crate does not visibly use it directly; the shared-runtime integration happens in callers and wrappers

---

## Important Dependencies And Related Crates

Important direct dependencies:

- `reqwest` - HTTP client used for GitHub API requests
- `tokio` and `futures` - async ecosystem dependencies; async methods require Tokio-compatible execution
- `semver` - strict release-tag parsing and precedence comparisons
- `serde` and `serde_json` - release DTO serialization/deserialization
- `thiserror` - `UpdateError` derive and display formatting
- `dotenvy` - optional `.env` loading for `GITHUB_TOKEN`
- `url` - error type dependency present in the public `UpdateError` enum

Related CLASSIC crates and consumers:

- [`classic-shared-core`](classic-shared-core.md) - shared Tokio runtime policy used by callers of this crate
- [`classic-version-core`](classic-version-core.md) - alternative version helper crate with intentionally different, more lenient parsing rules
- [`cpp-bindings/classic-cpp-bridge/src/update.rs`](../../cpp-bindings/classic-cpp-bridge/src/update.rs) - narrower frontend-oriented bridge over latest-release check + comparison
- [`node-bindings/classic-node/src/update.rs`](../../node-bindings/classic-node/src/update.rs) - fuller binding layer preserving `GithubClient` and DTOs
- [`python-bindings/classic-update-py/src/github.rs`](../../python-bindings/classic-update-py/src/github.rs) - Python wrapper over the same client model
- [`ui-applications/classic-tui/src/app.rs`](../../ui-applications/classic-tui/src/app.rs) - direct in-repo UI consumer

---

## Usage Example

This example follows the real public API: fetch the latest release, decide whether an update exists, and inspect the first asset URL if the release publishes one.

```rust,no_run
use classic_update_core::GithubClient;

# async fn example() -> Result<(), Box<dyn std::error::Error>> {
let client = GithubClient::new("evildarkarchon", "CLASSIC-Fallout4")?;
let latest = client.get_latest_release().await?;

if client.has_update("9.0.0", &latest.tag_name)? {
    println!("Update available: {}", latest.tag_name);
    println!("Release page: {}", latest.html_url);

    if let Some(asset) = latest.assets.first() {
        println!("First asset: {}", asset.name);
        println!("Download URL: {}", asset.browser_download_url);
    }
} else {
    println!("Already up to date");
}
# Ok(())
# }
```

If you only need a yes/no version comparison, `has_update()` is synchronous and does not make a network request.

---

## Contributor Notes And Known Limits

- the public surface is intentionally small: one client, two DTOs, one error enum, and root re-exports
- `GithubClient` only strips a lowercase `v` before semver parsing; uppercase `V` is currently invalid input
- `get_all_releases()` filters locally but does not add its own sorting pass
- rate-limit handling is coarse today: `403` becomes `RateLimitExceeded(None)` without parsing retry metadata from headers
- the crate exposes asset download URLs but not asset download/install behavior
- timestamps remain raw strings instead of typed date values
- `Cargo.toml` includes `classic-shared-core`, but runtime integration happens in callers rather than inside this crate's current source
- some public `UpdateError` variants are broader than the currently visible behavior in `GithubClient`

If you extend this crate, update this document when you change:

- root-level re-exports in [`business-logic/classic-update-core/src/lib.rs`](../../business-logic/classic-update-core/src/lib.rs)
- GitHub endpoint choices, request headers, or auth behavior in [`business-logic/classic-update-core/src/github.rs`](../../business-logic/classic-update-core/src/github.rs)
- semver parsing rules or `has_update()` comparison behavior
- how `UpdateError` variants are mapped from network, JSON, or rate-limit failures
- whether the crate begins owning download, install, checksum, or runtime responsibilities
