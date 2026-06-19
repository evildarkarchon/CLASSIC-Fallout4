## Context

`classic-update-core` runs a two-leg app-notification check: a Pages-first fetch of `manifest-latest.json`, then a Releases-API fallback listing `app-notification-v*` tags. Today, when nothing has been published yet:

- The Pages leg gets `404`. In `manifest_fetch.rs::try_pages` (manifest_fetch.rs:160-165) any non-2xx status — including `404` — becomes `PagesError::Transport(UpdateError::GithubError("pages GET returned 404 Not Found"))`, which triggers the fallback.
- The Releases leg finds no matching release, so `fetch_via_releases_fallback_bytes` returns `UpdateError::NotFound(...)` (notification.rs:232-236).
- The orchestrator `check_app_notification_with` (notification.rs:520-563) folds both into `UpdateError::NotificationFetchFailed { pages_error, releases_error }`.

Every consumer renders that error: GUI `QMessageBox::warning("Error checking for updates")` (mainwindow.cpp:1927-1932), settings label `"Error: ..."` (settingsdialog.cpp:616-620), CLI stderr + exit 1 (app_update.cpp:92-97), TUI `"Update check failed"` (update_workflow.rs + app.rs:500), Python `ClassicNotificationFetchFailed` (notification.rs:189-191), Node rejection. The classification dispatch is uniform across frontends because the CXX bridge already converts an `Err` into a DTO with `classification = "error"` (update.rs:389-401) and each frontend switches on the classification string.

Constraints: business logic stays in Rust (AGENTS rule #2); bindings are thin wrappers (rule #3); public/binding-facing API changes require updating `docs/api/` in the same change (rule #7); Rust unit tests live in sibling `*_tests.rs` files (rule #10); parity gates must be refreshed when the binding surface changes.

## Goals / Non-Goals

**Goals:**
- Distinguish "manifest not published yet" (Pages `404` + no matching release) from a genuine fetch failure.
- Surface the absent state as a benign success (`Ok`) so no frontend renders an error dialog, stderr, non-zero exit, or raised/rejected error.
- Keep all genuine failure paths (5xx, network, timeout, rate-limit, malformed manifest, decode/version/cache errors) exactly as they are today.
- Make the change additive and uniform across the existing classification-dispatch pattern in all five frontends and three bindings.

**Non-Goals:**
- Reworking the cache, ETag, or fallback mechanics.
- Changing the deprecated `GithubClient::get_latest_release` compat path.
- Adding retries/backoff or any new network behavior.
- Removing or renaming any existing `Classification` value or `UpdateError` variant.

## Decisions

### D1 — Add `Classification::NotPublished` and return it as `Ok`, rather than swallowing an error in each frontend

`check_app_notification` returns `Ok(NotificationStatus)` with a new `Classification::NotPublished` (serde `not_published`) and empty manifest fields. The result stays in the success channel.

- **Why:** All five frontends already dispatch on `classification`, and the CXX bridge converts `Result` into a DTO classification string. A new success classification flows through that existing seam uniformly. The alternative — keep returning an `Err` and have each binding/frontend special-case-swallow it — would require divergent handling across the throw-based bindings (Node/Python) and the DTO-based bridge, and would leave "the check failed" semantics on a non-failure.
- **Alternative considered:** Return `Result<Option<NotificationStatus>>` (`None` = not published). Rejected: changes the signature across all three bindings and every call site; far larger blast radius than an additive enum value.
- **Alternative considered:** New `UpdateError::NotificationNotPublished` swallowed downstream. Rejected: keeps a benign state in the error channel; Node/Python would still throw/raise unless every caller adds a catch.

### D2 — Map a Pages `404` to `UpdateError::NotFound` inside `try_pages`

In `manifest_fetch.rs::try_pages`, branch on `reqwest::StatusCode::NOT_FOUND` before the generic non-2xx arm and return `PagesError::Transport(UpdateError::NotFound(...))`. All other non-2xx statuses keep the existing `GithubError` mapping.

- **Why:** `404` uniquely means "the manifest file is not there", which is the publish-absent signal. Carrying it as `NotFound` (not `GithubError`) lets the orchestrator detect absence by matching the error *variant* instead of string-sniffing `"404"`. It stays a `Transport` error so the Releases fallback still runs (the manifest could still exist only via Releases).
- **Shared helper note:** `try_pages` is shared with the YAML-update channel. Mapping `404 → NotFound` there is harmless for YAML: it remains a `Transport` error that triggers the YAML Releases fallback exactly as before; only the carried variant/string differs, and the YAML orchestrator does not branch on `NotFound`.

### D3 — Detect absence in the orchestrator by matching `NotFound` on both legs

In `check_app_notification_with`, before folding into `NotificationFetchFailed`, add: if `matches!(pages_err, UpdateError::NotFound(_))` AND `matches!(fallback_err, UpdateError::NotFound(_))`, return `Ok(NotificationStatus::not_published())`.

- **Why:** Both legs reporting `NotFound` is precisely "manifest absent everywhere". A Pages 5xx yields `GithubError` (not `NotFound`) so a real outage with nothing published still folds into `NotificationFetchFailed` — correct, because Pages genuinely failed. A repo-level Releases `404` becomes `GithubError` via `get_all_releases` (github.rs:418-429), so a misconfigured repo stays an error too.
- **Scope of `NotFound` on the fallback leg:** `fetch_via_releases_fallback_bytes` returns `NotFound` for both "no matching release" and "matching release has no `manifest.json` asset" (notification.rs:256-265). Both are treated as absent/NotPublished. A half-published release that omits its asset will read as "not published yet" rather than erroring — an intentional, quieter choice consistent with the goal; documented as a trade-off below.
- **Ordering:** This new arm runs only after the existing short-circuits (unsupported-version, fallback-cache reuse, and the propagate-distinct `ManifestUnsupportedVersion | ManifestInvalid | NotificationDecode` arm), so structural/validation failures are unaffected.

### D4 — `NotificationStatus::not_published()` carries empty fields

Add a small constructor producing `classification = NotPublished`, empty `latest_version`/`published_at`, `min_supported_version = None`, `display = None`, `parse_error = None`. `classify()` is not involved (there is no manifest to compare).

### D5 — Surface `NotPublished` quietly in every consumer

- **CXX bridge (`update.rs`):** add `const CLASSIFICATION_NOT_PUBLISHED = "not_published"` and a `Classification::NotPublished => CLASSIFICATION_NOT_PUBLISHED` arm in `classification_label`. The existing `notification_status_to_dto` already tolerates empty fields; `error_message` stays empty (no `notification_error_dto`).
- **GUI:** add a `kClassificationNotPublished` constant on `UpdateWorker`; in `mainwindow.cpp` add a branch before the final `else` that, on a silent start-up check, shows no dialog, and on `explicitCheck` shows a benign `QMessageBox::information("No update information is currently available.")` — never the `warning` path. In `settingsdialog.cpp` set the label to a benign "No update information available." instead of `"Error: ..."`.
- **CLI (`app_update.cpp`):** add `kClassificationNotPublished`; print a benign one-liner to **stdout** and `return 0` (no stderr, no non-zero exit).
- **TUI (`update_workflow.rs`):** add `Classification::NotPublished => "No update information available".to_string()` to `format_update_status`. Because the core now returns `Ok`, the result already flows through the success path (app.rs `UpdateResult` `Ok` arm), not the `"Update check failed"` error arm.
- **Python (`classic-update-py`):** map `Classification::NotPublished` in `core_status_to_py`; expose the value on the Python `Classification`/status type and refresh the `.pyi` stub. The `Ok` return means no exception is raised.
- **Node (`classic-node`):** map the classification in the notification status conversion; refresh `index.d.ts`. The `Ok` return means the promise resolves.

### D6 — Update API contract docs and parity baselines

Update `docs/api/app-update-notification-delivery.md` (classification set now includes `not_published`, plus the absent-vs-failed fetch semantics) and `docs/api/error-contract.md` (clarify that absent-on-both-channels is no longer `NotificationFetchFailed`). Refresh CXX/Node/Python parity baselines so the gates pass with the new classification string and binding stubs.

## Risks / Trade-offs

- **A half-published release (tag present, `manifest.json` asset missing) now reads as `NotPublished` instead of an error** → Acceptable and intended: users should not be nagged during a publish race. The publish workflow/validators remain the guard against shipping a malformed/partial release; mention in the docs update.
- **Pages outage (5xx) while nothing is published still surfaces as `NotificationFetchFailed`** → Intended. Absence is signalled specifically by `404`; a 5xx is a real transport failure worth surfacing. Spec scenario "Genuine dual-channel failure surfaces an error" locks this in.
- **Binding surface grows by one classification string** → Parity gates will fail until baselines/stubs are refreshed; handled as explicit tasks. Additive only, so existing consumers that don't recognize `not_published` fall through to their benign default branch (CLI/GUI already have a catch-all that does not error).
- **`try_pages` is shared with the YAML channel** → The `404 → NotFound` remap is behavior-neutral for YAML (still a retryable `Transport` error). A YAML-channel regression test should confirm the fallback still fires on a Pages 404.

## Migration Plan

Additive, no data migration. Land core (D2–D4) with its sibling tests first so the new `Ok(NotPublished)` is observable, then the bridge/frontends/bindings (D5), then docs + parity baselines (D6) in the same change so gates stay green. Rollback is a straightforward revert — no persisted state or schema is affected.

## Open Questions

- Should an explicit, user-initiated CLI/GUI check print/show a brief "no update info available yet" message, or be fully silent like start-up? Current design: silent on start-up, brief benign info on explicit checks. Confirm during review if full silence is preferred everywhere.
