## Why

The current app-update check in `classic-update-core` hits GitHub's REST API directly (`/releases/latest`) and compares `tag_name` — an unauthenticated path capped at 60 requests/hour per IP that silently fails once a busy user or CI pipeline exhausts the budget. It also parses release tag strings and relies on asset name conventions to decide whether the installed CLASSIC is current, which makes the check brittle to maintainer formatting mistakes and forces every frontend (CLI, GUI, TUI) to round-trip the GitHub API on start-up. The repository already operates a proven manifest-based delivery channel for shippable YAML data — Pages-first with ETag caching, GitHub Releases fallback, and a deterministic maintainer workflow. Reusing that channel for app-update notification removes the rate-limit surface, eliminates string-parsing fragility, and gives maintainers a single publishing discipline for both YAML data and client-version signalling.

## What Changes

- Introduce a payload-free **notification manifest** (`app-notification-latest.json`) published alongside the existing YAML manifest: a small JSON document carrying `schema_version`, `latest_version`, `published_at`, optional `min_supported_version`, and an optional display payload (`title`, `body`, `cta_url`).
- Add a new `notification` submodule under `classic-update-core` that mirrors `yaml_update`'s Pages-first / Releases-fallback fetch path and ETag cache, minus file install, atomic rename, SHA-256 freshness, and rollback.
- Replace the current `GithubClient::get_latest_release` + `has_update` pathway used by CLI/GUI/TUI start-up checks with the manifest-driven API. Keep the old `GithubClient` as a **compat-only** surface used by diagnostic tooling (not by end-user update checks).
- Extend maintainer publish workflow (`.github/workflows/publish-yaml-data.yml` or a sibling) to emit the notification manifest on app releases and push it to both the GitHub Pages mirror and a Releases asset fallback.
- Update C++ bridge, Node, and Python bindings to expose the new notification-check API (`notification_check`, `checkAppNotification`, `check_app_notification`). Keep parity-gate baselines aligned in the same change.
- Refresh `docs/api/classic-update-core.md`, create a new `docs/api/app-update-notification-delivery.md` doc (companion to `yaml-update-delivery.md`), and adjust consumer docs (TUI `app.rs` call site note, any GUI update docs).
- **BREAKING** for frontend callers: The `AsyncMessage::UpdateResult(String)` payload shape and the `UpdateCheckResult` CXX/NAPI DTOs gain `latest_version`, `published_at`, and optional display fields. TUI/GUI/CLI consumers must migrate from the old release-asset-name comparison to `NotificationStatus` classification.

## Capabilities

### New Capabilities
- `app-update-notification`: Manifest-based, payload-free notification that signals whether the installed CLASSIC build is the latest published release. Covers manifest schema, Pages-first fetch with ETag caching, classification (`UpToDate`, `UpdateAvailable`, `DeprecatedClient`, `Unknown`), binding-layer surface, and consumer integration (TUI/GUI/CLI start-up checks).

### Modified Capabilities
- `update-core-error-propagation`: Add a new `NotificationError` variant family (or extend `UpdateError`) so manifest-fetch, decode, and classification failures propagate through bindings with the same error-contract discipline as `YamlUpdateError`. This is a requirement-level change because the error surface documented in the spec grows.
- `yaml-release-publishing`: Extend the maintainer publish workflow to also publish the app-notification manifest alongside YAML data, using the same Pages-first + prerelease-probe discipline. Requirement changes because the publish contract now covers a second manifest shape.

## Impact

- **Affected Rust crates**: `business-logic/classic-update-core/` (new `notification` module, updated re-exports), `business-logic/classic-path-core/` (new cache sub-dir for notification ETag), `business-logic/classic-file-io-core/` (minor helper reuse for JSON read/write — no atomic install / rollback), `foundation/classic-shared-core/` (error variants), `foundation/classic-message-core/` (async message payload shape).
- **Bindings**: `cpp-bindings/classic-cpp-bridge/src/update.rs` (new CXX DTO + entry point), `node-bindings/classic-node/src/update.rs` (new NAPI function + `index.d.ts` contract refresh), `python-bindings/classic-update-py/` (new PyO3 function, `.pyi` contract refresh). All three parity gates (CXX, Node, Python) need baseline refreshes in the same change.
- **Frontends**: `ui-applications/classic-tui/src/app.rs` (`check_updates` rewrite), `classic-cli/` update-check command, `classic-gui/` update-check controller + settings page.
- **Maintainer workflow**: `.github/workflows/publish-yaml-data.yml` (or new `publish-app-notification.yml`) to produce and probe the notification manifest. `CLASSIC Data/databases/client-schema-ranges.yaml`-style source-of-truth artifact for notification schema bounds.
- **Docs**: New `docs/api/app-update-notification-delivery.md`; edits to `docs/api/classic-update-core.md`, `docs/api/README.md` index, and any GUI/TUI consumer docs that mention the old `GithubClient` update path.
- **Out of scope**: Keeping `GithubClient` around for diagnostic/CI parity with the existing `checkForUpdates` CLI tooling is fine; removing it is a follow-up change. Auto-install of new CLASSIC builds is explicitly not in scope — this is notification-only.
