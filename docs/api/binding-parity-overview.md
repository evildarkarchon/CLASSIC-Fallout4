# Binding Parity Overview

As of the v9.1.0-bindings milestone, all shared Rust business-logic crates are exposed through all three binding surfaces: C++ via CXX, Node via NAPI-RS, and Python via PyO3. The sole exception is `classic-resource-core`, which has no C++ bridge module.

**Phase 1 consolidation note (v9.1.0):** ``yaml-core`` has been absorbed into `classic-settings-core`. The C++ bridge module was renamed `classic::yaml` -> `classic::settings` and expanded with the D-09 surface (cache operations and validators matching the Python surface). The Node `yaml.rs` module was folded into `settings.rs`. The Python `classic-yaml-py` crate was deleted and its `YamlOperations` surface folded into `classic-settings-py`. See `.planning/phases/01-yaml-settings-merge/` for details.

This page is a contributor-facing reference for the complete binding surface.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Per-Crate Binding Table

Each shared Rust crate and its corresponding binding module across all three surfaces:

| Rust Crate | C++ Bridge Module | Node Module | Python Module |
| --- | --- | --- | --- |
| `classic-shared-core` | [`runtime.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/runtime.rs) | [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs) | [`classic-shared-py`](../../ClassicLib-rs/foundation/classic-shared-py/src/lib.rs) |
| `classic-registry-core` | [`registry.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs) | (via [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs)) | [`classic-registry-py`](../../ClassicLib-rs/python-bindings/classic-registry-py/) |
| `classic-perf-core` | [`perf.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/perf.rs) | (via [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs)) | [`classic-perf-py`](../../ClassicLib-rs/python-bindings/classic-perf-py/) |
| `classic-message-core` | [`message.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/message.rs) | [`message.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/message.rs) | [`classic-message-py`](../../ClassicLib-rs/python-bindings/classic-message-py/) |
| `classic-settings-core` (absorbed the former ``yaml-core`` in Phase 1 of the v9.1.0 merge) | [`settings.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/settings.rs) | [`settings.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/settings.rs) | [`classic-settings-py`](../../ClassicLib-rs/python-bindings/classic-settings-py/) |
| `classic-version-registry-core` | [`version_registry.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/version_registry.rs) | [`version_registry.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs) | [`classic-version-registry-py`](../../ClassicLib-rs/python-bindings/classic-version-registry-py/) |
| `classic-constants-core` | [`constants.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/constants.rs) | [`constants.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/constants.rs) | [`classic-constants-py`](../../ClassicLib-rs/python-bindings/classic-constants-py/) |
| `classic-version-core` | (via [`game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs)) | [`version.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/version.rs) | [`classic-version-py`](../../ClassicLib-rs/python-bindings/classic-version-py/) |
| `classic-web-core` | [`web.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/web.rs) | [`web.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/web.rs) | [`classic-web-py`](../../ClassicLib-rs/python-bindings/classic-web-py/) |
| `classic-update-core` | [`update.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/update.rs) | [`update.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/update.rs) | [`classic-update-py`](../../ClassicLib-rs/python-bindings/classic-update-py/) |
| `classic-crashgen-settings-core` | (via [`config.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs)) | [`crashgen_rules.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/crashgen_rules.rs) | (via [`classic-scanlog-py`](../../ClassicLib-rs/python-bindings/classic-scanlog-py/) and [`classic-config-py`](../../ClassicLib-rs/python-bindings/classic-config-py/)) |
| `classic-config-core` | [`config.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs) | [`config.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/config.rs) | [`classic-config-py`](../../ClassicLib-rs/python-bindings/classic-config-py/) |
| `classic-path-core` | [`path.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs) | [`path.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/path.rs) | [`classic-path-py`](../../ClassicLib-rs/python-bindings/classic-path-py/) |
| `classic-xse-core` | [`xse.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/xse.rs) | [`xse.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/xse.rs) | [`classic-xse-py`](../../ClassicLib-rs/python-bindings/classic-xse-py/) |
| `classic-file-io-core` | [`files.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs) | [`fileio.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/fileio.rs) | [`classic-file-io-py`](../../ClassicLib-rs/python-bindings/classic-file-io-py/) |
| `classic-resource-core` | **Not exposed** | [`resource.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/resource.rs) | [`classic-resource-py`](../../ClassicLib-rs/python-bindings/classic-resource-py/) |
| `classic-database-core` | [`database.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs) | [`database.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/database.rs) | [`classic-database-py`](../../ClassicLib-rs/python-bindings/classic-database-py/) |
| `classic-scangame-core` | [`scangame.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs) | [`scangame.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/scangame.rs) | [`classic-scangame-py`](../../ClassicLib-rs/python-bindings/classic-scangame-py/) |
| `classic-scanlog-core` | [`scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs) | [`scanlog.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs) | [`classic-scanlog-py`](../../ClassicLib-rs/python-bindings/classic-scanlog-py/) |

**Note on `classic-resource-core`**: This crate provides lightweight resource classification helpers used by `classic-file-io-core`. It has no dedicated C++ bridge module. C++ frontends access resource classification functionality transitively through the `classic-file-io-core` bridge surface (`files.rs`) where needed.

---

## FFI Adaptation By Binding

### C++ (CXX)

The C++ surface in [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs) uses CXX shared structs for DTOs, opaque Rust types behind `Box` pointers, and `block_on()` for async-to-sync conversion. Fail-soft returns often use empty-string sentinels (e.g., `""` when a lookup misses) because Qt callers check `.isEmpty()` rather than catching exceptions. The bridge is compiled behind `#[cfg(windows)]` and produces a static library linked into `classic-cli` and `classic-gui`.

See: [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md), [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md).

### Node (NAPI-RS)

The Node surface in [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/lib.rs) uses `#[napi(object)]` structs for DTOs, `JsXxx` wrapper types with `inner:` fields holding core Rust types, and async Rust functions that map naturally to JavaScript promises. NAPI-RS auto-converts `snake_case` Rust identifiers to `camelCase` at the JS boundary. The committed [`index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts) is the tracked generated contract artifact.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

### Python (PyO3)

The Python surface is a set of per-crate PyO3 modules under [`ClassicLib-rs/python-bindings/`](../../ClassicLib-rs/python-bindings/). Each module uses `#[pyclass]` wrappers with `#[getter]` properties and `#[pyo3(name="...")]` for Python-convention naming. Error conversion uses typed Python exception classes wired through `classic-shared-py`'s `define_exceptions!`, `register_exceptions!`, and `ToPyErr` trait.

See: [`node-python-contract-map.md`](node-python-contract-map.md).

---

## Gate Coverage

Gate run instructions, ownership, and the step-by-step workflow for adding a new public Rust API across all three bindings are documented in [`binding-parity-policy.md`](binding-parity-policy.md).

---

## Source-Backed Caveats

This document describes binding exposure visible in source today. If source and this document diverge, update both in the same change. Runtime ownership stays outside these crates -- follow the shared-runtime guidance in [`AGENTS.md`](../../AGENTS.md).
