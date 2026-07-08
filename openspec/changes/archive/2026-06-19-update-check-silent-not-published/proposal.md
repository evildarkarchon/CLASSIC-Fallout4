## Why

When no app-update notification has been published yet, the Pages manifest URL returns **404** and the Releases-API fallback finds no `app-notification-v*` release. The orchestrator folds both into `UpdateError::NotificationFetchFailed`, which every frontend renders as a hard failure — the GUI pops a `QMessageBox::warning("Error checking for updates")`, the CLI prints to stderr and exits non-zero, the TUI shows `"Update check failed"`, and the Python/Node bindings raise/throw. "No update has been published yet" is a normal, benign state, not an error, and surfacing it as one is disruptive — especially on the silent start-up check.

## What Changes

- Treat a genuinely-absent notification (Pages `404` **and** no matching `app-notification-v*` release) as a benign "no notification published" outcome instead of a fetch failure.
- Add a fifth classification, `Classification::NotPublished` (binding string `not_published`), returned as `Ok(NotificationStatus)` with empty manifest fields — so the result stays in the success channel rather than the error channel.
- Map a Pages `404` to `UpdateError::NotFound` (not the generic `GithubError`) inside the shared Pages fetch helper, so the orchestrator can distinguish "manifest absent" from "Pages errored" (5xx / network / rate limit).
- Keep genuine failures unchanged: Pages 5xx/network/timeout/rate-limit, malformed manifests, and decode/version/cache errors still surface as before. `NotificationFetchFailed` only fires when at least one channel actually failed.
- Surface `NotPublished` quietly across every frontend: no warning/error dialog, no stderr, no non-zero exit, no error exception/rejection. Start-up checks stay silent; explicit/manual checks may show a benign informational message.
- Update the public API contract docs and binding stubs (`.pyi`, `index.d.ts`) and refresh parity baselines for the new classification value.

## Capabilities

### New Capabilities
<!-- None: this refines existing notification behavior. -->

### Modified Capabilities
- `app-update-notification`: The fetch-fold and classification requirements change so an absent (not-yet-published) notification is a benign `NotPublished` outcome rather than an error, and bindings/consumers surface it without an error dialog, error exit, or raised exception.

## Impact

- **Core (Rust):** `business-logic/classic-update-core/src/manifest_fetch.rs` (404 → `NotFound`), `src/notification.rs` (`Classification` enum, `NotificationStatus` constructor, orchestrator fold in `check_app_notification_with`), `src/error.rs` (doc only). Sibling `*_tests.rs` for new scenarios.
- **C++ bridge:** `cpp-bindings/classic-cpp-bridge/src/update.rs` — new `CLASSIFICATION_NOT_PUBLISHED` label + `classification_label` arm; `NotificationStatusDto` doc.
- **Frontends:** `classic-gui` (`mainwindow.cpp`, `settingsdialog.cpp`, `updateworker.*`), `classic-cli` (`app_update.cpp`), `classic-tui` (`update_workflow.rs`).
- **Bindings:** `python-bindings/classic-update-py` (classification mapping + `.pyi`), `node-bindings/classic-node` (classification mapping + `index.d.ts`).
- **Docs / gates:** `docs/api/app-update-notification-delivery.md`, `docs/api/error-contract.md`; CXX/Node/Python parity baselines.
- No new dependencies. Additive to the success enum; not a breaking change to existing classifications or error variants.
