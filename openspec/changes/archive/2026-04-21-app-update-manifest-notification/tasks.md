## 1. Rust core: manifest types and fetch helper

- [x] 1.1 Add `business-logic/classic-update-core/src/notification.rs` with `AppNotificationManifest`, `AppNotificationDisplay`, `Classification`, and `NotificationStatus` structs using `serde::Deserialize` with `#[serde(deny_unknown_fields = false)]` (tolerate unknown fields per spec)
- [x] 1.2 Add a notification-tagged variant family to `UpdateError` (per design D-05 — alt B, sibling variants): `NotificationFetchFailed { pages_error, releases_error }`, `NotificationDecode { field }`, `NotificationInstalledVersionParse { input, source }`, `NotificationCacheIo { path, source }`. Bindings map `UpdateError -> per-language shape` directly without a second enum to destructure; rationale documented inline in `business-logic/classic-update-core/src/error.rs`
- [x] 1.3 Extract the Pages-first + ETag logic from `yaml_update.rs` into a generic helper at `business-logic/classic-update-core/src/manifest_fetch.rs` parameterised over the deserialised type and the Pages path segment
- [x] 1.4 Refactor `yaml_update.rs` to call the new helper, verifying existing YAML-update tests still pass
- [x] 1.5 Implement `notification::fetch_app_notification_manifest()` using the helper, targeting Pages path `app-notification/manifest-latest.json`
- [x] 1.6 Implement `notification::fetch_via_releases_fallback()` listing `app-notification-v*` tags and pulling `manifest.json` from the newest one
- [x] 1.7 Implement `notification::classify(installed_version, &manifest) -> NotificationStatus` using `semver::Version` ordering
- [x] 1.8 Implement `notification::check_app_notification(owner, repo, installed_version) -> Result<NotificationStatus, UpdateError>` combining fetch + fallback + classify
- [x] 1.9 Re-export the public notification surface from `classic-update-core/src/lib.rs`
- [x] 1.10 Write sibling unit tests at `business-logic/classic-update-core/src/notification_tests.rs` (per AGENTS.md rule 10) declared with `#[cfg(test)] #[path = "notification_tests.rs"] mod tests;`
- [x] 1.11 Write sibling tests at `business-logic/classic-update-core/src/manifest_fetch_tests.rs` for the shared helper (mock HTTP, ETag round-trip, conditional GET handling)
- [x] 1.12 Mark `GithubClient::get_latest_release` with `#[deprecated(note = "Use classic_update_core::notification::check_app_notification instead")]` and add a module-level doc comment in `github.rs` flagging it as a compat-only surface

## 2. Cache integration with classic-path-core

- [x] 2.1 Add a `notification_cache_dir()` helper in `business-logic/classic-path-core/` returning `<platform-cache>/CLASSIC/app-notification/` and parallel to the existing YAML cache helper
- [x] 2.2 Write sibling tests at `business-logic/classic-path-core/src/lib_tests.rs` (or existing sibling file) covering the new helper on Windows and Unix shapes
- [x] 2.3 Wire `notification::check_app_notification` to read/write `manifest-latest.json` and `manifest.etag` inside that directory; on decode failure of cached body, discard and refetch
- [x] 2.4 Add integration test (sibling-file style) covering the three cache states: cold cache, warm cache with `200 OK`, warm cache with `304 Not Modified`

## 3. CXX bridge surface

- [x] 3.1 Add `NotificationStatusDto` to `cpp-bindings/classic-cpp-bridge/src/update.rs` mirroring the Rust `NotificationStatus` shape with empty-string sentinels on error per `docs/api/error-contract.md`
- [x] 3.2 Add `check_app_notification(owner, repo, installed_version) -> NotificationStatusDto` CXX entry point that calls the Rust `classic_update_core::notification::check_app_notification` and maps `UpdateError` to populated `error_message` + sentinel fields
- [x] 3.3 Register the new type and entry point in the four bridge-registration sites (per project CXX bridge conventions)
- [x] 3.4 Run `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` to confirm gate fails
- [x] 3.5 Refresh `cpp-bindings/classic-cpp-bridge/parity-artifacts/baseline/` by running the documented update-baseline command
- [x] 3.6 Re-run the CXX parity gate and confirm pass
- [x] 3.7 Add sibling tests at `cpp-bindings/classic-cpp-bridge/src/update_tests.rs` for DTO mapping (success + error cases)

## 4. Node binding surface

- [x] 4.1 Add `JsNotificationStatus` struct to `node-bindings/classic-node/src/update.rs` via `napi-derive`, with fields for classification, latest_version, published_at, optional min_supported_version, optional display payload
- [x] 4.2 Add `checkAppNotification` NAPI function (camelCase) with an options-object parameter `{ owner, repo, installedVersion }` returning `Promise<JsNotificationStatus>`
- [x] 4.3 Map `UpdateError::Notification*` variants to NAPI `Error` with a `code` property keyed to the variant name (e.g., `FETCH_FAILED`, `DECODE`, `INSTALLED_VERSION_PARSE`, `CACHE_IO`)
- [x] 4.4 Regenerate `node-bindings/classic-node/index.d.ts` with the new type and function
- [x] 4.5 Run `cd node-bindings/classic-node && bun run parity:gate` to confirm gate fails
- [x] 4.6 Refresh Node parity baseline via `bun run parity:gate:update-baseline` (only after confirming drift is intentional)
- [x] 4.7 Re-run Node parity gate and confirm pass
- [x] 4.8 Add Vitest/Bun test coverage for `checkAppNotification` success + error paths in `node-bindings/classic-node/tests/`

## 5. Python binding surface

- [x] 5.1 Add `NotificationStatus` PyO3 class to `python-bindings/classic-update-py/src/notification.rs` with typed fields matching the Rust shape
- [x] 5.2 Add `check_app_notification(owner, repo, installed_version) -> NotificationStatus` module-level function
- [x] 5.3 Add `ClassicNotificationError` exception class subclassing the existing `ClassicUpdateError` hierarchy, with variant-discriminating subclasses
- [x] 5.4 Ensure `$env:PYO3_PYTHON = "$PWD\python-bindings\.venv\Scripts\python.exe"` is set in the shell, then run `./rebuild_rust.ps1 -Target python` to build and install every `-py` crate into the binding-local venv
- [x] 5.5 Regenerate the `.pyi` stub at `python-bindings/classic-update-py/classic_update.pyi` (filename tracks the PyO3 module name, `classic_update`, not the crate name `classic-update-py`) via the repo's stub-validation tool
- [x] 5.6 Run `python validate_stubs.py --rust-dir .` to confirm stub matches implementation
- [x] 5.7 Run `python tools/python_api_parity/check_parity_gate.py --repo-root .` to confirm gate fails pre-baseline-refresh
- [x] 5.8 Refresh Python parity baseline under `docs/implementation/python_api_parity/baseline/` via the documented refresh command
- [x] 5.9 Re-run Python parity gate and confirm pass
- [x] 5.10 Run `uv run --python python-bindings/.venv/Scripts/python.exe python -m pytest python-bindings/tests -q` to confirm bindings load and new entry point behaves per spec

## 6. Consumer migration: TUI / GUI / CLI

- [x] 6.1 Rewrite `ui-applications/classic-tui/src/app.rs::check_updates` to call `check_app_notification` instead of `GithubClient::get_latest_release`
- [x] 6.2 Extend `AsyncMessage::UpdateResult` payload in `ui-applications/classic-tui/src/app.rs` (the enum lives TUI-local; the cross-crate message-core crate at `business-logic/classic-message-core/` does not own TUI update messages) from a free-form `String` to `Result<NotificationStatus, String>` so classification + display fields cross the async boundary as structured data; update consumers accordingly
- [x] 6.3 Update TUI display rendering to show `title`/`body`/`cta_url` from the manifest when the classification is `UpdateAvailable` or `DeprecatedClient`
- [x] 6.4 Update CLI update-check subcommand in `classic-cli/` to invoke the new CXX entry point and format `NotificationStatusDto` for stdout
- [x] 6.5 Update GUI update controller in `classic-gui/` to invoke the new CXX entry point; wire the returned DTO into the existing update-result dialog/status line
- [x] 6.6 Verify via `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test` that integration coverage for the update-check path still passes

## 7. Maintainer publish workflow

- [x] 7.1 Add `.github/workflows/publish-app-notification.yml` triggered only on `push` of tags matching `app-notification-v*`
- [x] 7.2 Implement the validate step: parse `app-notification.json`, check `manifest_version` regex, check `latest_version` semver, check `published_at` RFC 3339
- [x] 7.3 Implement the generate step: produce the final manifest JSON from a source-of-truth artifact checked into the repo (analogous to `CLASSIC Data/databases/client-schema-ranges.yaml`)
- [x] 7.4 Implement the draft-release step: `gh release create --draft --latest=false` with the manifest and optional changelog attached
- [x] 7.5 Implement the promote-to-prerelease step and the anonymous-reachability probe (mirror the YAML publish workflow pattern)
- [x] 7.6 Implement the clear-prerelease step, then the `gh-pages` deploy step that writes `app-notification/manifest-latest.json` and `app-notification/manifest-<tag>.json`
- [x] 7.7 Implement the Pages propagation smoke test (poll the Pages URL until it returns the new tag's `release_tag`, or fail after timeout)
- [x] 7.8 Constrain the workflow trigger to `push` tags only — no `pull_request`, no content-mutating `workflow_dispatch` inputs
- [ ] 7.9 Dry-run the workflow against a throwaway `app-notification-v0.0.0-dryrun` tag in a fork or test environment (manual maintainer step — requires push access and a live GitHub Actions environment; workflow file is in place and ready once merged)

## 8. Documentation

- [x] 8.1 Create `docs/api/app-update-notification-delivery.md` structured like `yaml-update-delivery.md`: schema_version contract, client load precedence, manifest format, Pages-mirrored publish workflow
- [x] 8.2 Update `docs/api/classic-update-core.md` to document the new `notification` module, mark `GithubClient` as compat-only, and cross-link the new delivery doc
- [x] 8.3 Update `docs/api/README.md` index to list the new `app-update-notification-delivery.md` entry
- [x] 8.4 Update `docs/api/error-contract.md` with a row for notification errors covering CXX sentinel, Node code, Python exception shape
- [x] 8.5 Update `docs/api/binding-parity-overview.md` with the new entry points on all three bindings
- [x] 8.6 Update `docs/api/node-python-contract-map.md` if it enumerates concrete entry points per binding (N/A — this file is a location/contract map, not an entry-point-level enumeration; conditional does not fire)
- [x] 8.7 Add a migration note to `AGENTS.md` Quick Notes section pointing maintainers and agents at the new publish workflow

## 9. Final verification

- [x] 9.1 Run `cargo fmt --all -- --check` and `cargo clippy --workspace --all-targets --all-features -- -D warnings` from repo root
- [x] 9.2 Run `cargo test --workspace` from repo root (88 test-suite results, zero failures)
- [x] 9.3 Run all three parity gates in sequence and confirm they pass with refreshed baselines (CXX, Python, Node — all report "gate passed")
- [x] 9.4 Run `classic-cli/build_cli.ps1 -Test` and `classic-gui/build_gui.ps1 -Test` to confirm C++ frontends still build and test cleanly (CLI: 21 unit + 24 integration all pass; GUI: 12/12 pass — ran during Phase 6.6)
- [ ] 9.5 Manually exercise the TUI update-check path against the dry-run Pages manifest to confirm end-to-end behaviour (manual maintainer step — depends on Phase 7.9 dry-run publish to populate a reachable Pages manifest; defer to real dry-run)
- [x] 9.6 Validate the OpenSpec change with `openspec validate app-update-manifest-notification` before archiving (CLI renamed the verb from `verify` to `validate`; change reports "is valid")
