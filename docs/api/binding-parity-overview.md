# Binding Parity Overview

As of the active Phase 4 closure state, the surviving 17 Rust business-logic crates are exposed through the maintained binding surfaces: C++ via CXX, Node via NAPI-RS, and Python via PyO3. The sole exception is `classic-resource-core`, which still has no dedicated C++ bridge module.

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
| `classic-user-settings-core` | [`settings.rs`](../../cpp-bindings/classic-cpp-bridge/src/settings.rs) | [`user_settings.rs`](../../node-bindings/classic-node/src/user_settings.rs) | [`classic-user-settings-py`](../../python-bindings/classic-user-settings-py/) |
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
| `classic-scanlog-core` | [`scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) | [`scanlog.rs`](../../node-bindings/classic-node/src/scanlog.rs) + [`crashgen_settings_analyzer.rs`](../../node-bindings/classic-node/src/crashgen_settings_analyzer.rs) + [`crash_suspect_analyzer.rs`](../../node-bindings/classic-node/src/crash_suspect_analyzer.rs) + [`mod_guidance_analyzer.rs`](../../node-bindings/classic-node/src/mod_guidance_analyzer.rs) + [`plugin_evidence_analyzer.rs`](../../node-bindings/classic-node/src/plugin_evidence_analyzer.rs) + [`named_record_finding_analyzer.rs`](../../node-bindings/classic-node/src/named_record_finding_analyzer.rs) + [`formid_finding_analyzer.rs`](../../node-bindings/classic-node/src/formid_finding_analyzer.rs) | [`classic-scanlog-py`](../../python-bindings/classic-scanlog-py/) |

**Historical Phase 3 note (v9.1.0):** the retired constants crate, Python wrapper crate, and binding-side `constants` modules no longer exist as parity owners. `Fallout4Version` and `NULL_VERSION` now belong to `classic-version-registry-core`, `YamlFile` plus settings constants belong to `classic-settings-core`, and `GameId` belongs to `classic-shared-core` with matching C++ `shared.rs`, Node `shared.rs`, and `classic-shared-py` exposure.

`classic-database-core` also exposes the strict owned `FormIdValueLookup` facade across all three adapters. Each binding uses an opaque handle plus owned in-memory reply records and typed outcomes/errors for disabled, missing, found, malformed-result, and operational-failure states. SQLite and shared-pool work run through the existing shared runtime; no callback or binding-owned runtime is part of the contract.

**Semantic analyzer contract:** `CrashgenSettingsAnalyzer`,
`CrashSuspectAnalyzer`, `ModGuidanceAnalyzer`, `PluginEvidenceAnalyzer`,
`NamedRecordFindingAnalyzer`, and `FormIDFindingAnalyzer` are projected through all
three bindings as immutable reusable handles over owned input. Crashgen
Settings Analysis returns typed
Crashgen Expectation Outcomes separately from Disabled Setting Notices and
preserves YAML-owned placement and authored guidance. Crash Suspect Analysis
returns one typed finding per main-error rule, stack rule, or DLL involvement
notice. Mod Guidance Analysis evaluates conflict, frequent-crash, solution, and
important-mod configuration in one call while preserving authored guidance and
typed match state. Plugin Evidence Analysis returns normalized plugin identities
and per-line occurrence counts without report prose. Named Record Finding
Analysis returns distinct exact record identities and occurrence counts while
leaving sorting and prose to Autoscan Report Assembly. FormID Finding Analysis
returns aggregate identifiers and counts, optional resolved plugins and values,
and explicit lookup state while retaining unresolved identifiers. All six represent completed no-match analysis with
explicit empty results and expose no report presentation mechanics. Stable analyzer and error tokens
originate in Rust; see
[`error-contract.md`](error-contract.md#shared-focused-analyzer-errors).

This semantic surface replaced the public report-fragment architecture in one
coordinated breaking Rust, CXX, Node, and Python cutover. `ReportFragment`,
`ReportComposer`, `ReportGenerator`, `SettingsValidator`, presentation-only
`StringPool` operations, Python-only `ParallelReportProcessor`, and
fragment-producing analyzer methods have no compatibility aliases. Parity
therefore covers both the six positive Focused Semantic Analyzer contracts and negative
absence checks for the retired presentation surface. Complete scan output is
pinned separately as byte-identical persisted Autoscan Reports; see
[ADR-0005](../adr/0005-semantic-autoscan-report-contributions.md).

**Explicit YAML Data contract (`classic-config-core`):** Rust, C++, Node, and Python expose the same deterministic tooling operation over one explicitly identified Main file, game file, and Local Ignore file plus a typed game identity. Every surface returns an immutable snapshot with the parsed `YamlDataCore` view and SHA-256/byte-length identities derived from the exact retained bytes. Fallout 4 VR maps to the shared Fallout 4 data role; unsupported typed games and role-attributed read, UTF-8, parse, and validation failures remain typed per binding. No adapter performs installed selection, cache recovery, generation, backup, or fallback. Entry points are CXX `explicit_yaml_data_load(...)` plus its typed status/snapshot functions, Node `loadExplicitYamlData(...)`, and Python `classic_config.load_explicit_yaml_data(...)`.

**Installed YAML Data inspection contract (`classic-config-core`):** Rust, C++, Node, and Python also expose the config-owned, side-effect-limited selector used by first-party update freshness. Main and the typed game's registered data file are selected independently from compatible, semantically valid updated, previous-when-canonical-is-absent, or bundled candidates. Results expose provenance, schema, exact-byte SHA-256/length identity, and structured rejection diagnostics; Fallout 4 VR maps to Fallout 4 data, unsupported games remain typed, and Local Ignore is never inspected or modified. Entry points are CXX `installed_yaml_data_inspect(...)` plus its status/inspection functions, Node `inspectInstalledYamlData(...)`, and Python `classic_config.inspect_installed_yaml_data(...)`.

**Installed YAML Data load contract (`classic-config-core`):** Rust, C++, Node, and Python load one installation root, typed game, and separate selected-game-version mode into Ready, Local Ignore Recovery Required, or fatal error. Missing Local Ignore is strictly validated from retained selected-Main defaults, atomically published without clobbering a concurrent winner, and reread from the authoritative canonical file. Malformed bytes are retained with the selected Main/game snapshot, defaults, identity, mode, and diagnostics in an opaque single-use plan. Every surface exposes both decisions: Proceed Without Ignore returns the retained snapshot with an empty operation-scoped list and no filesystem mutation; Reset To Default conflict-checks exact bytes, durably publishes and verifies a byte-exact backup, and atomically publishes retained defaults without `.prev` update-channel state. Reset success returns canonical/backup paths, malformed/backup/replacement identities, the reset-ready snapshot, and structured reset diagnostics; changed or removed canonical bytes return a typed conflict, while operational failures retain stable stage metadata. The synchronous Rust reset is the non-interruptible critical section; Node runs it on its worker pool and Python releases the GIL. Snapshots expose parsed YAML Data, simplify-log removal entries retained from selected Main, independently selected Main/game provenance and schema, exact identities, all four Local Ignore states, and structured diagnostics without raw documents. Entry points are CXX `installed_yaml_data_load(...)` plus its status/snapshot/recovery-plan/reset functions, Node `loadInstalledYamlData(...)`, and Python `classic_config.load_installed_yaml_data(...)`.

**Crash Log Scan Run Installed YAML Data contract (`classic-scanlog-core`):** the final Rust-owned run accepts one installation root and typed game, performs one Installed YAML Data load after discovery, and retains that immutable snapshot through analysis. Existing or generated Ignore proceeds immediately. Malformed Ignore returns the distinct Local Ignore Recovery Required lifecycle state with completed discovery, structured diagnostics, and a Rust-owned opaque single-use continuation. CXX, Node, and Python explicitly pass Proceed Without Ignore to resume the same prepared intake in discovery order; no adapter rediscovers inputs, reselects Main/game data, mutates the malformed file, or serializes/clones the carrier. Pre-resume cancellation returns the normal cancelled-after-discovery result; replay rejects with `scan_run_continuation_consumed`. The shared fixture proves retained identities, discovery, malformed bytes, report-byte stability, cancellation, and replay across adapters.

**Note on app-update notification surface (`classic-update-core`):** the `notification` module adds a single cross-binding entry point in addition to the legacy `GithubClient` surface. Contract map:

| Binding | Entry point | DTO / return | Error shape |
| --- | --- | --- | --- |
| C++ (CXX) | `classic::update::check_app_notification(owner, repo, installed_version)` | `NotificationStatusDto`; absent manifests resolve as `classification == "not_published"` with empty `error_message` | Genuine failures use `classification == "error"` + populated `error_message`; empty-string sentinels on every other string field |
| Node (NAPI-RS) | `checkAppNotification({ owner, repo, installedVersion })` | `Promise<JsNotificationStatus>`; absent manifests resolve as `classification == "notPublished"` | Genuine failures use `Promise.reject(Error)` whose `message` is prefixed with the variant-keyed code: `FETCH_FAILED: …` / `DECODE: …` / `INSTALLED_VERSION_PARSE: …` / `CACHE_IO: …` / `UPDATE_ERROR: …` (catch-all). Discriminate via `err.message.startsWith("FETCH_FAILED:")`. Shape rationale (napi-rs 3.x async `Status`-enum constraint) documented in [`error-contract.md`](error-contract.md#notification-errors-app-update-manifest-notification) |
| Python (PyO3) | `classic_update_py.check_app_notification(owner, repo, installed_version)` | `NotificationStatus`; absent manifests return `classification == "notPublished"` | `ClassicNotificationError` subclass under the existing `ClassicUpdateError` hierarchy |

Full cross-crate flow: [`app-update-notification-delivery.md`](app-update-notification-delivery.md). Error shapes: [`error-contract.md`](error-contract.md). The legacy `github_check_for_updates` / `GithubClient::get_latest_release` surface is retained as compat-only and is no longer called from user-facing update checks.

**Note on YAML Data update surface (`classic-update-core`):** native C++ now has first-party helpers for the product YAML Data Update Channel, while Node/Python intentionally keep the lower-level generic manifest interface for compatibility.

| Binding | Preferred first-party/native API | Generic compatibility API |
| --- | --- | --- |
| C++ (CXX) | `classic::update::yaml_data_check_update(enabled)`, `yaml_data_apply_update(enabled, approved)`, `yaml_data_rollback_update()` | `yaml_check_update(pages_url, tag_prefix, entries, enabled, bundled_yaml_dir)`, `yaml_apply_update(request)`, `yaml_rollback_update(file_name)` |
| Node (NAPI-RS) | Not exposed in this scope | `checkYamlUpdate(...)`, `applyYamlUpdate(request)`, `rollbackYamlUpdate(fileName)` |
| Python (PyO3) | Not exposed in this scope | `check_yaml_update(...)`, `apply_yaml_update(request)`, `rollback_yaml_update(file_name)` |

The first-party C++ helpers centralize the Pages URL, `yaml-data-v*` tag namespace, config-inspected installed schema/content identity, first-party file set, and rollback target list in Rust. Generic compatibility APIs preserve caller-supplied installed metadata and use their retained bundled-directory hint to enrich entries whose installed version/digest are absent. Full cross-crate flow: [`yaml-update-delivery.md`](yaml-update-delivery.md).

**Note on `classic-resource-core`**: This crate provides lightweight resource classification helpers used by `classic-file-io-core`. It has no dedicated C++ bridge module. C++ frontends access resource classification functionality transitively through the `classic-file-io-core` bridge surface (`files.rs`) where needed.

---

## FFI Adaptation By Binding

### C++ (CXX)

The C++ surface in [`classic-cpp-bridge`](../../cpp-bindings/classic-cpp-bridge/src/lib.rs) uses CXX shared structs for DTOs, opaque Rust types behind `Box` pointers, and `block_on()` for async-to-sync conversion. Fail-soft returns often use empty-string sentinels (e.g., `""` when a lookup misses) because Qt callers check `.isEmpty()` rather than catching exceptions. User Settings distinguishes ordinary update preview from explicit missing-document bootstrap preview, while `run_game_setup_intake_from_user_settings` keeps GUI setup preparation inside typed Rust groups. The bridge is compiled behind `#[cfg(windows)]` and produces a static library linked into `classic-cli` and `classic-gui`.

See: [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md), [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md).

### Node (NAPI-RS)

The Node surface in [`classic-node`](../../node-bindings/classic-node/src/lib.rs) uses `#[napi(object)]` structs for DTOs, opaque native classes for invariant-preserving values, and async Rust functions that map naturally to JavaScript promises. NAPI-RS auto-converts `snake_case` Rust identifiers to `camelCase` at the JS boundary. User Settings exposes separate ordinary-update and explicit-bootstrap preview/commit pairs; frontends project an accepted snapshot into the opaque final Crash Log Scan Run request; and Game Setup has both explicit-facts and explicit-root typed entry points. The flat `ClassicConfigJs`/`JsPathConfig`/`createDefaultConfig` surface is removed across all layers. The committed [`index.d.ts`](../../node-bindings/classic-node/index.d.ts) is the tracked generated contract artifact.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

### Python (PyO3)

The Python surface is a set of per-crate PyO3 modules under [`python-bindings/`](../../python-bindings/). Each module uses `#[pyclass]` wrappers with `#[getter]` properties and `#[pyo3(name="...")]` for Python-convention naming. The intentional breaking User Settings cutover removed `ClassicConfig` and `PathConfig`; inspection, updates, conflicts, and migrations use the explicit-root `classic_user_settings` contract. Crash Log Scan Runs now use the same final Rust-owned contract as C++ and Node through invariant-preserving `ScanRunRequest` factories, separate opaque cancellation, complete serialized events, typed result/error mapping, and adapter-only observer failure data.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

---

## Gate Coverage

Gate run instructions, ownership, and the step-by-step workflow for adding a new public Rust API across all three bindings are documented in [`binding-parity-policy.md`](binding-parity-policy.md).

Need an old-to-new path translation first? Use the shared [`workspace migration matrix`](../workspace-migration-matrix.md).

---

## Source-Backed Caveats

This document describes binding exposure visible in source today. If source and this document diverge, update both in the same change. Runtime ownership stays outside these crates -- follow the shared-runtime guidance in [`AGENTS.md`](../../AGENTS.md).
