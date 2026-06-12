# Binding Parity Overview

As of the active Phase 4 closure state, the surviving 16 Rust business-logic crates are exposed through the maintained binding surfaces: C++ via CXX, Node via NAPI-RS, and Python via PyO3. The sole exception is `classic-resource-core`, which still has no dedicated C++ bridge module.

Historical consolidation note: `classic-settings-core` now owns the former `classic-yaml-core` surface, and `classic-config-core` now owns the former crashgen-settings rule surface. Those retired crate names remain here only as migration breadcrumbs.

This page is a contributor-facing reference for the complete binding surface.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Per-Crate Binding Table

Each shared Rust crate and its corresponding binding module across all three surfaces:

| Rust Crate | C++ Bridge Module | Node Module | Python Module |
| --- | --- | --- | --- |
| `classic-shared-core` | [`runtime.rs`](../../cpp-bindings/classic-cpp-bridge/src/runtime.rs) | [`shared.rs`](../../node-bindings/classic-node/src/shared.rs) | [`classic-shared-py`](../../foundation/classic-shared-py/src/lib.rs) |
| `classic-registry-core` | [`registry.rs`](../../cpp-bindings/classic-cpp-bridge/src/registry.rs) | (via [`shared.rs`](../../node-bindings/classic-node/src/shared.rs)) | [`classic-registry-py`](../../python-bindings/classic-registry-py/) |
| `classic-perf-core` | [`perf.rs`](../../cpp-bindings/classic-cpp-bridge/src/perf.rs) | (via [`shared.rs`](../../node-bindings/classic-node/src/shared.rs)) | [`classic-perf-py`](../../python-bindings/classic-perf-py/) |
| `classic-message-core` | [`message.rs`](../../cpp-bindings/classic-cpp-bridge/src/message.rs) | [`message.rs`](../../node-bindings/classic-node/src/message.rs) | [`classic-message-py`](../../python-bindings/classic-message-py/) |
| `classic-settings-core` (historical note: absorbed the former `classic-yaml-core` in v9.1.0 Phase 1) | [`settings.rs`](../../cpp-bindings/classic-cpp-bridge/src/settings.rs) | [`settings.rs`](../../node-bindings/classic-node/src/settings.rs) | [`classic-settings-py`](../../python-bindings/classic-settings-py/) |
| `classic-version-registry-core` | [`version_registry.rs`](../../cpp-bindings/classic-cpp-bridge/src/version_registry.rs) | [`version_registry.rs`](../../node-bindings/classic-node/src/version_registry.rs) | [`classic-version-registry-py`](../../python-bindings/classic-version-registry-py/) |
| `classic-version-core` | (via [`game.rs`](../../cpp-bindings/classic-cpp-bridge/src/game.rs)) | [`version.rs`](../../node-bindings/classic-node/src/version.rs) | [`classic-version-py`](../../python-bindings/classic-version-py/) |
| `classic-web-core` | [`web.rs`](../../cpp-bindings/classic-cpp-bridge/src/web.rs) | [`web.rs`](../../node-bindings/classic-node/src/web.rs) | [`classic-web-py`](../../python-bindings/classic-web-py/) |
| `classic-update-core` | [`update.rs`](../../cpp-bindings/classic-cpp-bridge/src/update.rs) | [`update.rs`](../../node-bindings/classic-node/src/update.rs) | [`classic-update-py`](../../python-bindings/classic-update-py/) |
| `classic-config-core` (historical note: absorbed the former `classic-crashgen-settings-core` owner in v9.1.0 Phase 2; rule model now at `classic_config_core::crashgen_rules::*`) | [`config.rs`](../../cpp-bindings/classic-cpp-bridge/src/config.rs) | [`config.rs`](../../node-bindings/classic-node/src/config.rs) + [`crashgen_rules.rs`](../../node-bindings/classic-node/src/crashgen_rules.rs) | [`classic-config-py`](../../python-bindings/classic-config-py/) (plus crashgen-rule surfaces in [`classic-scanlog-py`](../../python-bindings/classic-scanlog-py/) and [`classic-scangame-py`](../../python-bindings/classic-scangame-py/)) |
| `classic-path-core` | [`path.rs`](../../cpp-bindings/classic-cpp-bridge/src/path.rs) | [`path.rs`](../../node-bindings/classic-node/src/path.rs) | [`classic-path-py`](../../python-bindings/classic-path-py/) |
| `classic-xse-core` | [`xse.rs`](../../cpp-bindings/classic-cpp-bridge/src/xse.rs) | [`xse.rs`](../../node-bindings/classic-node/src/xse.rs) | [`classic-xse-py`](../../python-bindings/classic-xse-py/) |
| `classic-file-io-core` | [`files.rs`](../../cpp-bindings/classic-cpp-bridge/src/files.rs) | [`fileio.rs`](../../node-bindings/classic-node/src/fileio.rs) | [`classic-file-io-py`](../../python-bindings/classic-file-io-py/) |
| `classic-resource-core` | **Not exposed** | [`resource.rs`](../../node-bindings/classic-node/src/resource.rs) | [`classic-resource-py`](../../python-bindings/classic-resource-py/) |
| `classic-database-core` | [`database.rs`](../../cpp-bindings/classic-cpp-bridge/src/database.rs) | [`database.rs`](../../node-bindings/classic-node/src/database.rs) | [`classic-database-py`](../../python-bindings/classic-database-py/) |
| `classic-scangame-core` | [`scangame.rs`](../../cpp-bindings/classic-cpp-bridge/src/scangame.rs) | [`scangame.rs`](../../node-bindings/classic-node/src/scangame.rs) | [`classic-scangame-py`](../../python-bindings/classic-scangame-py/) |
| `classic-scanlog-core` | [`scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) | [`scanlog.rs`](../../node-bindings/classic-node/src/scanlog.rs) | [`classic-scanlog-py`](../../python-bindings/classic-scanlog-py/) |

**Historical Phase 3 note (v9.1.0):** the retired constants crate, Python wrapper crate, and binding-side `constants` modules no longer exist as parity owners. `Fallout4Version` and `NULL_VERSION` now belong to `classic-version-registry-core`, `YamlFile` plus settings constants belong to `classic-settings-core`, and `GameId` belongs to `classic-shared-core` with matching C++ `shared.rs`, Node `shared.rs`, and `classic-shared-py` exposure.

**Note on app-update notification surface (`classic-update-core`):** the `notification` module adds a single cross-binding entry point in addition to the legacy `GithubClient` surface. Contract map:

| Binding | Entry point | DTO / return | Error shape |
| --- | --- | --- | --- |
| C++ (CXX) | `classic::update::check_app_notification(owner, repo, installed_version)` | `NotificationStatusDto` | `classification == "error"` + populated `error_message`; empty-string sentinels on every other string field |
| Node (NAPI-RS) | `checkAppNotification({ owner, repo, installedVersion })` | `Promise<JsNotificationStatus>` | `Promise.reject(Error)` whose `message` is prefixed with the variant-keyed code: `FETCH_FAILED: …` / `DECODE: …` / `INSTALLED_VERSION_PARSE: …` / `CACHE_IO: …` / `UPDATE_ERROR: …` (catch-all). Discriminate via `err.message.startsWith("FETCH_FAILED:")`. Shape rationale (napi-rs 3.x async `Status`-enum constraint) documented in [`error-contract.md`](error-contract.md#notification-errors-app-update-manifest-notification) |
| Python (PyO3) | `classic_update_py.check_app_notification(owner, repo, installed_version)` | `NotificationStatus` | `ClassicNotificationError` subclass under the existing `ClassicUpdateError` hierarchy |

Full cross-crate flow: [`app-update-notification-delivery.md`](app-update-notification-delivery.md). Error shapes: [`error-contract.md`](error-contract.md). The legacy `github_check_for_updates` / `GithubClient::get_latest_release` surface is retained as compat-only and is no longer called from user-facing update checks.

**Note on `classic-resource-core`**: This crate provides lightweight resource classification helpers used by `classic-file-io-core`. It has no dedicated C++ bridge module. C++ frontends access resource classification functionality transitively through the `classic-file-io-core` bridge surface (`files.rs`) where needed.

---

## FFI Adaptation By Binding

### C++ (CXX)

The C++ surface in [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge/src/lib.rs) uses CXX shared structs for DTOs, opaque Rust types behind `Box` pointers, and `block_on()` for async-to-sync conversion. Fail-soft returns often use empty-string sentinels (e.g., `""` when a lookup misses) because Qt callers check `.isEmpty()` rather than catching exceptions. The bridge is compiled behind `#[cfg(windows)]` and produces a static library linked into `classic-cli` and `classic-gui`.

See: [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md), [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md).

### Node (NAPI-RS)

The Node surface in [`classic-node`](../../node-bindings/classic-node/src/lib.rs) uses `#[napi(object)]` structs for DTOs, `JsXxx` wrapper types with `inner:` fields holding core Rust types, and async Rust functions that map naturally to JavaScript promises. NAPI-RS auto-converts `snake_case` Rust identifiers to `camelCase` at the JS boundary. The committed [`index.d.ts`](../../node-bindings/classic-node/index.d.ts) is the tracked generated contract artifact.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

### Python (PyO3)

The Python surface is a set of per-crate PyO3 modules under [`python-bindings/`](../../python-bindings/). Each module uses `#[pyclass]` wrappers with `#[getter]` properties and `#[pyo3(name="...")]` for Python-convention naming. Error conversion uses typed Python exception classes wired through `classic-shared-py`'s `define_exceptions!`, `register_exceptions!`, and `ToPyErr` trait.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

---

## Gate Coverage

Gate run instructions, ownership, and the step-by-step workflow for adding a new public Rust API across all three bindings are documented in [`binding-parity-policy.md`](binding-parity-policy.md).

Need an old-to-new path translation first? Use the shared [`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Source-Backed Caveats

This document describes binding exposure visible in source today. If source and this document diverge, update both in the same change. Runtime ownership stays outside these crates -- follow the shared-runtime guidance in [`AGENTS.md`](../../AGENTS.md).
