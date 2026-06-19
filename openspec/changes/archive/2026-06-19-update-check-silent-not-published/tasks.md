## 1. Core: distinguish absent manifest (Rust)

- [x] 1.1 In `business-logic/classic-update-core/src/manifest_fetch.rs::try_pages`, add a `reqwest::StatusCode::NOT_FOUND` arm before the generic non-2xx check (manifest_fetch.rs:160-165) that returns `PagesError::Transport(UpdateError::NotFound(format!("pages GET returned {} (manifest absent)", response.status())))`; leave all other non-2xx statuses mapped to `GithubError` (D2).
- [x] 1.2 In `business-logic/classic-update-core/src/notification.rs`, add `NotPublished` to the `Classification` enum (notification.rs:118-133) with `#[serde(rename = "not_published")]` semantics and a doc comment explaining it is produced only when the manifest is absent on both channels.
- [x] 1.3 Add a `NotificationStatus::not_published()` constructor (or equivalent helper) returning `classification = NotPublished`, empty `latest_version`/`published_at`, `min_supported_version = None`, `display = None`, `parse_error = None` (D4).
- [x] 1.4 In `check_app_notification_with` (notification.rs:520-563), add a fold arm before the `NotificationFetchFailed` arm: when `matches!(pages_err, UpdateError::NotFound(_))` AND `matches!(fallback_err, UpdateError::NotFound(_))`, return `Ok(NotificationStatus::not_published())` (D3). Keep the existing `ManifestUnsupportedVersion | ManifestInvalid | NotificationDecode` propagation arm ahead of it.
- [x] 1.5 Update doc comments on `UpdateError::NotificationFetchFailed`/`NotFound` in `src/error.rs` to note that absence-on-both-channels now yields `Ok(NotPublished)` rather than `NotificationFetchFailed`.

## 2. Core: tests (sibling `*_tests.rs`)

- [x] 2.1 In `business-logic/classic-update-core/src/manifest_fetch_tests.rs`, add a mockito test asserting a Pages `404` yields a `Transport(UpdateError::NotFound)` (not `GithubError`).
- [x] 2.2 In `business-logic/classic-update-core/src/notification_tests.rs`, add a test using `check_app_notification_with` (mockito Pages `404` + empty `releases` list) asserting `Ok` with `Classification::NotPublished` and empty manifest fields.
- [x] 2.3 In `notification_tests.rs`, add a regression test that Pages `500` + empty releases still returns `Err(UpdateError::NotificationFetchFailed)` (absence requires a 404 specifically).
- [x] 2.4 In `notification_tests.rs`, add a test that Pages `404` + a valid `app-notification-v*` release still classifies normally (fallback success path unaffected).
- [x] 2.5 Add/extend a `yaml_update` test confirming a Pages `404` still triggers the YAML Releases fallback (behavior-neutral remap; D-trade-off).
- [x] 2.6 Run `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"; cargo test -p classic-update-core` and confirm green.

## 3. C++ bridge (CXX)

- [x] 3.1 In `cpp-bindings/classic-cpp-bridge/src/update.rs`, add `const CLASSIFICATION_NOT_PUBLISHED: &str = "not_published";` and a `Classification::NotPublished => CLASSIFICATION_NOT_PUBLISHED` arm in `classification_label` (update.rs:352-364).
- [x] 3.2 Update the `NotificationStatusDto` doc block (update.rs:534-566) to document the `"not_published"` classification: empty manifest fields, empty `error_message`, not the `"error"` classification.
- [x] 3.3 In `cpp-bindings/classic-cpp-bridge/src/update_tests.rs`, add a test asserting `Classification::NotPublished` maps to the `"not_published"` label and produces a DTO with empty `error_message`.

## 4. Frontends

- [x] 4.1 **CLI** — `classic-cli/src/app_update.cpp`: add `constexpr const char* kClassificationNotPublished = "not_published";` and a branch in `report_notification` that prints a benign one-liner to stdout (e.g. `"No update information is currently published."`) and `return 0` (no stderr, no non-zero exit).
- [x] 4.2 **GUI worker** — `classic-gui/src/workers/updateworker.h`: add the `kClassificationNotPublished` constant alongside the existing classification constants.
- [x] 4.3 **GUI main window** — `classic-gui/src/app/mainwindow.cpp`: add a `not_published` branch before the final `else` (around mainwindow.cpp:1986) that shows no dialog on a silent start-up check and a benign `QMessageBox::information` only when `explicitCheck`; ensure it never reaches the `kClassificationError` `warning` path.
- [x] 4.4 **GUI settings** — `classic-gui/src/app/settingsdialog.cpp`: add a `not_published` branch (around settingsdialog.cpp:615-639) setting the label to a benign "No update information available." instead of `"Error: ..."`.
- [x] 4.5 **TUI** — `ui-applications/classic-tui/src/app/update_workflow.rs`: add `Classification::NotPublished => "No update information available".to_string()` to `format_update_status` (verify the `Ok` result flows through the success arm in `app/app.rs`, not the `"Update check failed"` error arm).

## 5. Bindings (Python + Node)

- [x] 5.1 **Python** — `python-bindings/classic-update-py/src/notification.rs`: map `Classification::NotPublished` in `core_status_to_py` and expose the value on the Python classification/status type; confirm the `Ok` return path raises no exception.
- [x] 5.2 **Python stub** — refresh the `.pyi` stub for `classic_update_py` so the new classification value is declared.
- [x] 5.3 **Node** — `node-bindings/classic-node/src/update.rs`: map `Classification::NotPublished` in the notification status conversion so the promise resolves (no rejection) with the new classification.
- [x] 5.4 **Node types** — regenerate/refresh `node-bindings/classic-node/index.d.ts` for the new classification value.

## 6. Docs + parity gates

- [x] 6.1 Update `docs/api/app-update-notification-delivery.md`: add `not_published` to the classification set and document the absent-vs-failed fetch semantics (Pages `404` + no matching release ⇒ benign `NotPublished`).
- [x] 6.2 Update `docs/api/error-contract.md`: clarify that absence-on-both-channels is no longer `NotificationFetchFailed`, and the CXX DTO uses `"not_published"` (empty `error_message`) for that case.
- [x] 6.3 Refresh the CXX parity baseline under `cpp-bindings/classic-cpp-bridge/parity-artifacts/baseline/` and confirm the CXX parity gate passes.
- [x] 6.4 Refresh the Python parity baseline and confirm `python tools/python_api_parity/check_parity_gate.py --repo-root .` passes.
- [x] 6.5 Refresh the Node parity baseline and confirm `bun run parity:gate` passes.

## 7. Build + verify (repo-approved commands)

- [x] 7.1 Rust: `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"; cargo test -p classic-update-core -p classic-cpp-bridge` is green.
- [x] 7.2 Python: `uv sync --project python-bindings --inexact`, then `./rebuild_rust.ps1 -Target python`, then `uv run --project python-bindings python -m pytest python-bindings/tests -q` is green.
- [x] 7.3 CLI: `classic-cli/build_cli.ps1 -Test -CTestName <app-update test name>` builds and the update-check tests pass.
- [x] 7.4 GUI: `classic-gui/build_gui.ps1 -Test -CTestName <update worker test name>` builds and the update-check tests pass.
- [x] 7.5 Node: build the `classic-node` binding and confirm a `not_published` result resolves (no throw) via the binding's test/smoke path.
- [x] 7.6 Manual smoke: point a frontend at a repo/owner with no published `app-notification-v*` release and confirm the start-up check produces no error dialog/stderr/non-zero exit.
