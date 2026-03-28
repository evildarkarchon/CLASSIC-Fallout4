# Binding Parity Overview

Contributor-facing notes for the active Rust binding surfaces in:

- [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/)
- [`ClassicLib-rs/node-bindings/classic-node/src/`](../../ClassicLib-rs/node-bindings/classic-node/src/)
- [`ClassicLib-rs/node-bindings/classic-node/index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts)
- [`ClassicLib-rs/python-bindings/`](../../ClassicLib-rs/python-bindings/)

This page compares the binding surfaces that exist in source today.

It is intentionally about current exposure, current narrowing, and current omissions. It does **not** define a future parity target, and it does **not** promise that every shared Rust crate must be exposed identically across C++, Node, and Python.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to understand:

- which shared Rust crates are exposed through the active C++ bridge, Node bindings, and Python bindings
- where one binding is intentionally narrower than another
- where the binding layer reshapes Rust types into DTOs, strings, primitive tuples, or fail-soft return values
- which source files are the practical starting points for contributor parity work
- which gaps are real current behavior versus assumed parity

This page is for contributor maintenance and debugging.

For crate-level Rust behavior, see the existing docs in this directory, especially:

- [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md)
- [`classic-config-core.md`](classic-config-core.md)
- [`classic-path-core.md`](classic-path-core.md)
- [`classic-scangame-core.md`](classic-scangame-core.md)
- [`classic-scanlog-core.md`](classic-scanlog-core.md)
- [`classic-version-core.md`](classic-version-core.md)
- [`classic-version-registry-core.md`](classic-version-registry-core.md)
- [`classic-xse-core.md`](classic-xse-core.md)

---

## Binding Shapes Today

## C++ bridge

The active C++ surface is the Windows-only [`classic-cpp-bridge`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs) static library.

Current characteristics:

- organized as CXX namespaces such as `classic::game`, `classic::path`, `classic::scangame`, and `classic::scanner`
- compiled behind `#[cfg(windows)]`, with no non-Windows bridge surface today
- often narrows Rust APIs into sync helper calls, sentinel DTOs, `bool`, `String`, or flattened `Vec<String>` payloads
- tends to prioritize active frontend workflows over full crate-shaped parity

## Node bindings

The active Node surface is the single [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node/src/lib.rs) NAPI package, with the generated TypeScript contract in [`index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts).

Current characteristics:

- one package exposes many shared crates through a flat JS/TS export surface
- DTOs usually stay closer to Rust model shape than the C++ bridge does
- async Rust APIs remain async at the JS boundary where that improves fidelity
- `index.d.ts` is the quickest contributor view of the current public Node contract

## Python bindings

The active Python surface is a set of per-crate PyO3 modules under [`ClassicLib-rs/python-bindings/`](../../ClassicLib-rs/python-bindings/).

Current characteristics:

- public contract is spread across `classic_*.pyi` stub files, one module per binding crate
- many modules are closer to crate-shaped exposure than the C++ bridge is
- repo guidance treats Python bindings as compatibility and deprecation-support work, not the default place for new product behavior
- for parity questions, the `.pyi` files are the fastest way to see current public behavior

---

## Current Exposure By Shared Crate

| Shared Rust crate or concern | C++ bridge today | Node today | Python today | Current parity notes |
| --- | --- | --- | --- | --- |
| `classic-shared-core` plus runtime helpers | Exposes runtime init/check helpers in [`runtime.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/runtime.rs). | Exposes runtime diagnostics plus shared path/string helpers in [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs). | No single `classic_shared` module; shared-runtime use is mostly internal to other Python modules. | Same shared runtime exists underneath, but only C++ and Node expose explicit runtime-facing helpers. |
| `classic-registry-core` | Exposes typed primitive get/set helpers and a few convenience keys in [`registry.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/registry.rs). | Exposes JSON-shaped registry get/set plus convenience helpers in [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs). | Exposes a broader Python object registry in [`classic_registry.pyi`](../../ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi). | C++ is the narrowest surface here: string/bool/i32 only, while Node and Python preserve more dynamic value shapes. |
| `classic-perf-core` | Exposes record/clear plus stringified summaries in [`perf.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/perf.rs). | Exposes structured timing summaries in [`shared.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/shared.rs). | Exposes structured metric objects and RAII timers in [`classic_perf.pyi`](../../ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi). | C++ reshapes metrics into summary strings and a couple scalar accessors; Node and Python keep richer metric structures. |
| `classic-message-core` | Exposes logging entry points only in [`message.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/message.rs). | Exposes message creation, formatting, targets, and logger helpers through `classic-node` public exports. | Exposes full message and logger types in [`classic_message.pyi`](../../ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi). | C++ is log-oriented, not message-model-oriented. |
| `classic-yaml-core` | Exposes a mutable `YamlOps` wrapper in [`yaml.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/yaml.rs), with `YamlValue` used as a typed fallback because CXX cannot pass YAML nodes directly. | Exposes `YamlDocument` and YAML helper functions through `classic-node` public exports and [`src/yaml.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/yaml.rs). | Exposes a broad `YamlOperations` API returning native Python values in [`classic_yaml.pyi`](../../ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi). | C++ is forced to flatten more aggressively; Node and Python can return native object trees. |
| `classic-config-core` | Exposes `YamlDataCore` through many field getters in [`config.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/config.rs). | Exposes both `YamlData` and runtime `ClassicConfigJs` in [`src/config.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/config.rs). | Exposes `YamlData` in [`classic_config.pyi`](../../ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi). | Suspect detection now uses structured rule lists in Rust, Node, and Python. C++ remains narrower and currently exposes only suspect rule ids and names/ids instead of full structured rule DTOs. |
| `classic-file-io-core` | Exposes backups, game-file operations, log collection, similarity, basic read/write, and report helpers in [`files.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/files.rs). | Exposes a broad async file-I/O surface, backup managers, DDS helpers, and log collection through `classic-node` exports. | Exposes a broad async file-I/O surface in [`classic_file_io.pyi`](../../ClassicLib-rs/python-bindings/classic-file-io-py/classic_file_io.pyi). | C++ is practical but narrower: many results are reduced to strings or simple counts, while Node and Python keep richer async and typed helper surfaces. |
| `classic-database-core` | Exposes an opaque pool in [`database.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/database.rs), with single-string lookups and tab-delimited batch results. | Exposes `JsDatabasePool` and structured batch access through `classic-node` public exports. | Exposes async structured lookups in [`classic_database.pyi`](../../ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi). | C++ is the narrowest surface and loses structured row shape at the FFI edge. |
| `classic-path-core` | Exposes FO4-specific convenience detection in [`path.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/path.rs) plus a few generic helpers in [`game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs). | Exposes `GamePathFinder`, `DocsPathFinder`, `DocumentsChecker`, `parseXseLog`, and validator functions in [`src/path.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/path.rs). | Exposes the same crate more fully in [`classic_path.pyi`](../../ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi). | This is a major current narrowing point: C++ has the active GUI-focused helpers, but Node and Python expose more of the crate's finder and validator surface, especially documents checks and INI validation. |
| `classic-xse-core` | Exposes only string-based version detection and install checks in [`game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs). | Exposes typed `JsXseType`, `getXseInfo`, and helper functions in [`src/xse.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/xse.rs). | Exposes typed `XseType` and `XseInfo` in [`classic_xse.pyi`](../../ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi). | C++ drops typed `XseType` and the combined `XseInfo` model; Node and Python preserve them. |
| `classic-version-core` | Exposes `parse_game_version()` and PE-version string extraction in [`game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs). | Exposes parse/compare/extract/format helpers in [`src/version.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/version.rs). | Exposes the broadest current version helper surface, including PE extraction, in [`classic_version.pyi`](../../ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi). | Parity is split rather than hierarchical here: C++ has PE probing that Node does not expose, while Node has broader semver-style helpers than C++ does. Python currently covers both areas more fully. |
| `classic-version-registry-core` | Exposes only a narrowed DTO subset in [`game.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs). | Exposes near-full registry DTOs and enumeration/matching helpers in [`src/version_registry.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/version_registry.rs). | Exposes a broad registry object model in [`classic_version_registry.pyi`](../../ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi). | C++ omits fields such as `display_name`, `description`, `address_library`, `compatible_range`, `exe_hash`, `script_hashes`, and unknown-version policy details that Node and Python expose. |
| `classic-scangame-core` | Exposes only `run_setup_checks()` and `needs_path_detection()` in [`scangame.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scangame.rs). | Exposes BA2, unpacked, INI, TOML, ENB, XSE, crashgen, Wrye, orchestrator, and setup helpers in [`src/scangame.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/scangame.rs). | Exposes a similarly broad game-analysis surface in [`classic_scangame.pyi`](../../ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi). | This is the clearest active parity gap: the C++ bridge intentionally exposes only a setup-time subset, not the full crate. |
| `classic-scanlog-core` | Exposes app-oriented orchestration, batch processing with progress callbacks, and Papyrus helpers in [`scanner.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/scanner.rs). | Exposes async scanlog orchestration plus config-building and parsing utilities in [`src/scanlog.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/scanlog.rs). | Exposes the broadest crate-shaped analysis surface in [`classic_scanlog.pyi`](../../ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi). | All three surfaces expose scanlog behavior, but they expose different slices: C++ is frontend-pipeline-oriented, Node mixes orchestration with utility helpers, and Python exposes the most individual analyzers and report-building pieces. |
| `classic-update-core` | Exposes quick semver and one-shot release-check helpers in [`update.rs`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/update.rs). | Exposes a full `GithubClient` plus one-shot convenience helpers in [`src/update.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/update.rs). | Exposes a full `GithubClient` in [`classic_update.pyi`](../../ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi). | C++ is narrower and front-end-oriented; Node and Python preserve the client model and richer DTOs. |
| `classic-constants-core` and `classic-web-core` | No active direct C++ bridge module today. | Exposed directly in [`src/constants.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/constants.rs) and [`src/web.rs`](../../ClassicLib-rs/node-bindings/classic-node/src/web.rs). | Exposed directly in [`classic_constants.pyi`](../../ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi) and [`classic_web.pyi`](../../ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi). | These are current Node/Python-only binding surfaces among the shared crates covered here. |

---

## Where The Current Surfaces Narrow Or Reshape Rust APIs

## C++ bridge narrows hardest at the FFI edge

The CXX bridge most often trades fidelity for straightforward frontend consumption:

- `classic-version-registry-core` becomes small DTOs with sentinel `found = false` behavior instead of `Option`-rich models
- `classic-path-core` gets both generic helpers and FO4-specific convenience entry points, but not the full documents-checking surface
- `classic-database-core` batch lookups become tab-delimited strings instead of structured maps
- `classic-config-core` still narrows some fields for C++, and the suspect-rule bridge is currently much thinner than the Rust, Node, and Python surfaces

## Node usually keeps object shape closer to Rust

The Node binding surface still adapts types for JavaScript, but it usually preserves more model structure:

- registry and version-registry calls return object-shaped DTOs instead of sentinel strings
- async operations such as scanlog, database, file I/O, and update checks stay async at the binding boundary
- generated [`index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts) is effectively the current public contract

## Python often keeps crate-shaped module boundaries

Python does not mirror Node's single-package design or C++'s namespace design.

Instead, it usually exposes one extension module per crate boundary, which means:

- `classic_path`, `classic_xse`, `classic_version_registry`, `classic_scangame`, and `classic_scanlog` remain easier to map back to their Rust crate owners
- `.pyi` files are often the clearest contributor reference for what Python actually exports today
- Python is broad in coverage, but broad coverage does not imply it is the preferred surface for new product features

## Some parity differences cut both directions

Current parity gaps are not always "C++ has less" or "Python has more":

- C++ exposes PE-version extraction through `classic::game`, while Node's public version helpers focus on semver-style parsing and comparison instead
- Node exposes `classic-web-core` and `classic-constants-core` directly, while the active C++ bridge does not
- Python exposes many fine-grained scanlog analyzers directly, while C++ focuses more on orchestrator-style app flows

---

## Practical Contributor Notes For Parity Work

## Start from the public contract files first

For parity debugging, these are usually the fastest source-of-truth files:

- C++: the relevant `classic-cpp-bridge` source file in [`ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/`](../../ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/)
- Node: [`ClassicLib-rs/node-bindings/classic-node/index.d.ts`](../../ClassicLib-rs/node-bindings/classic-node/index.d.ts), then the matching `src/*.rs` file
- Python: the matching `classic_*.pyi` stub, then the corresponding `src/*.rs` file under that `*-py` crate

## Distinguish crate behavior from binding behavior

When one surface appears "missing" compared with another, check whether the gap is actually in:

- the Rust core crate
- the binding adapter DTO shape
- error mapping and fail-soft conventions
- frontend-specific convenience wrappers that intentionally narrow the call path

Example: C++ `run_setup_checks()` is not a full parity stand-in for `classic-scangame-core`; it builds a limited `SetupCheckConfig`, ignores the `_game_root` input, and passes an empty `xse_hashes` list today.

## Expect different error styles

Current binding styles differ materially:

- C++ often returns `""`, `false`, or a sentinel DTO on failure
- Node often returns `null` for fail-soft helpers but throws for validation-heavy calls
- Python usually raises Python exceptions or returns `None`, depending on the module

Many cross-surface "parity bugs" are really error-contract differences.

## Keep parity artifacts aligned when Node or Python contracts change

If you change a Node or Python binding surface, the repo has explicit parity workflow follow-up in:

- [`J:/CLASSIC-Fallout4/.opencode/skills/classic-project-guide/references/repo-guide.md`](../../.opencode/skills/classic-project-guide/references/repo-guide.md)
- `docs/implementation/node_api_parity/`
- `docs/implementation/python_api_parity/`

This page is only a contributor overview; it is not the parity gate itself.

## Update docs when current public behavior changes

If you add, remove, or materially reshape a public binding surface:

- update the binding source and its generated or stubbed public contract
- update this page if the crate-to-surface comparison changed
- update crate-level docs such as [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md) when the change is C++-specific

---

## Source-Backed Caveats And Non-Goals

- This page covers active binding surfaces under `ClassicLib-rs/`; it does not cover the archived implementation under `deprecated/`.
- This page is about contributor-visible public behavior, not every internal helper inside each binding crate.
- This page does not define a mandatory "all surfaces must match exactly" policy.
- This page does not replace the Node or Python parity gate artifacts under `docs/implementation/`.
- This page does not describe frontend-only helpers that are not exposing shared Rust crate behavior.
- The C++ bridge is Windows-gated today, so "parity" with Node or Python should not be read as cross-platform runtime equivalence.

If source and this document diverge, update both in the same change.
