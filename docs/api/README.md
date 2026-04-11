# CLASSIC API Docs

Contributor-facing API guides for active Rust business-logic crates live here.

Current contract note: `Mods_FREQ` and `Mods_SOLU` are now documented as structured ordered sequences across config, scanlog, and binding-facing surfaces rather than key/value maps.

Use this directory in this order:

1. [`QUICK_START.md`](QUICK_START.md) - repo-level setup, build, and test workflow
2. [`classic-shared-core.md`](classic-shared-core.md) - shared runtime, error, path, performance, and string foundation helpers
3. [`classic-perf-core.md`](classic-perf-core.md) - global timing sample collection, summaries, and scoped timer helpers
4. [`classic-registry-core.md`](classic-registry-core.md) - process-wide typed singleton registry and convenience key helpers
5. [`classic-message-core.md`](classic-message-core.md) - shared message DTOs, routing enums, and startup/log formatting helpers
6. [`classic-settings-core.md`](classic-settings-core.md) - shared YAML stream parse/merge helpers, settings cache and sync/async loaders, plus the absorbed `YamlOperations` path-backed cache, merge-key resolver, and validator surface
7. [`classic-version-registry-core.md`](classic-version-registry-core.md) - version registry and OG/NG/AE/VR selection metadata
8. [`classic-constants-core.md`](classic-constants-core.md) - shared game/version/YAML identifiers and small convenience enums
9. [`classic-version-core.md`](classic-version-core.md) - version parsing, text extraction, and PE-version helpers
10. [`classic-web-core.md`](classic-web-core.md) - small URL, user-agent, and mod-site helper layer
11. [`classic-update-core.md`](classic-update-core.md) - async GitHub release/update-check client and DTO layer
12. [`classic-config-core.md`](classic-config-core.md) - YAML/config loading built on top of YAML and Version Registry metadata, AND the absorbed crashgen rule model (formerly its own crate, merged into config-core in v9.1.0 Phase 2)
13. [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md) - standalone runtime contract for settings discovery, merged YAML semantics, and consumed schema keys
14. [`classic-path-core.md`](classic-path-core.md) - game-path, documents-path, validation, and backup helpers
15. [`classic-xse-core.md`](classic-xse-core.md) - XSE loader/version detection helpers used by setup checks and bindings
16. [`game-setup-workflow.md`](game-setup-workflow.md) - current cross-crate setup/install validation flow across path, XSE, scangame, and version registry crates
17. [`formid-settings-boundary.md`](formid-settings-boundary.md) - current split between Rust config serialization and scan-time FormID DB path consumption
18. [`classic-file-io-core.md`](classic-file-io-core.md) - shared file I/O, traversal, hashing, and log collection helpers
19. [`classic-resource-core.md`](classic-resource-core.md) - lightweight resource classification, enumeration, and per-file validation helpers
20. [`classic-database-core.md`](classic-database-core.md) - SQLite/FormID lookup pool used by analysis paths
21. [`formid-sqlite-conventions.md`](formid-sqlite-conventions.md) - practical fixture/schema/path rules for contributor FormID DB work
22. [`classic-scangame-core.md`](classic-scangame-core.md) - game-installation, archive, loose-file, and setup validation workflows
23. [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md) - active C++ bridge entry points for path, game, and scangame workflows
24. [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md) - active C++ bridge entry points for config, file I/O, database, and scanlog workflows
25. [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md) - current batch scan progress callback contract for `classic::scanner`
26. [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md) - how `classic-gui` consumes bridge scan progress through `ScanWorker`, `BatchProgressModel`, `ScanController`, and `MainWindow`
27. [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md) - current Qt-side behavior for completion-order batch results, `input_index` correlation, and Results-tab ordering boundaries
28. [`binding-parity-overview.md`](binding-parity-overview.md) - complete C++ bridge, Node, and Python binding surface reference for all shared Rust crates
29. [`cxx-parity-gate.md`](cxx-parity-gate.md) - contributor guide for the CXX parity gate that enumerates the bridge surface from `build.rs` and detects drift against a committed baseline
30. [`node-python-contract-map.md`](node-python-contract-map.md) - where the active Node and Python public contracts, wrapper files, and parity artifacts live
31. [`binding-contract-refresh-note.md`](binding-contract-refresh-note.md) - when Node `index.d.ts` and Python `.pyi` contract artifacts should refresh separately versus together
32. [`classic-scanlog-core.md`](classic-scanlog-core.md) - crash-log analysis built on top of loaded config data and optional DB lookups
33. [`binding-parity-policy.md`](binding-parity-policy.md) - one-tier binding parity policy, gate ownership, and new-API contributor workflow
34. [`error-contract.md`](error-contract.md) - per-binding error shape conventions for C++ (CXX), Node (NAPI-RS), and Python (PyO3)

That order matches the current layering in `ClassicLib-rs/business-logic/`:

- `classic-shared-core` provides the shared Tokio runtime plus common error, path, performance, and string helpers
- `classic-perf-core` provides process-wide timing buckets, scoped timers, and summary computation for lightweight metrics collection
- `classic-registry-core` provides process-wide typed singleton storage and key helpers for callers that share state across boundaries
- `classic-message-core` provides shared message DTOs, routing enums, and structured/startup logging helpers used by bindings and bridge code
- `classic-settings-core` provides shared YAML stream parsing/merge helpers, raw settings loading, a sync/async cache layer keyed by caller-chosen strings, AND the absorbed path-backed `YamlOperations` file cache with mtime-based invalidation (merged from the former ``yaml-core`` crate during the v9.1.0 Phase 1 consolidation)
- `classic-version-registry-core` loads registry-backed version and crashgen metadata on top of YAML helpers
- `classic-constants-core` provides small shared enums/constants that higher layers use to label games, YAML files, and Fallout 4 mode selections
- `classic-version-core` adds low-level version parsing, text extraction, and PE-version helpers on top of constants and registry re-exports
- `classic-web-core` provides small web-oriented helpers without owning an HTTP client or runtime
- `classic-update-core` provides async GitHub release/update-check behavior for callers running on the shared runtime
- `classic-config-core` loads YAML and uses Version Registry metadata to build config data; in v9.1.0 Phase 2 it absorbed the former crashgen rules crate, so the typed crashgen rule model and evaluator now live at `classic_config_core::crashgen_rules::*` (re-exported at the crate root)
- `classic-config-core-yaml-schema.md` captures the runtime YAML contract for merged settings files and the Main/Game/Ignore sections that `classic-config-core` actually consumes
- `classic-path-core` handles game-path discovery, documents-folder checks, path validation, and versioned backups
- `classic-xse-core` builds on path/version helpers to detect XSE installation state and parse XSE versions
- `game-setup-workflow.md` explains how current setup/install validation is split across path, XSE, scangame, and Version Registry crates
- `formid-settings-boundary.md` documents the current split between `ClassicConfig.formid_databases` and the legacy scan-startup settings path still used by the C++ bridge
- `classic-file-io-core` provides shared file-system, decoding, hashing, and log collection helpers used by higher layers
- `classic-resource-core` provides lightweight resource classification and enumeration helpers used alongside broader file and scan workflows
- `classic-database-core` manages async SQLite pools and FormID lookups for analysis consumers
- `formid-sqlite-conventions.md` captures the current source-backed fixture/schema/path assumptions around FormID databases
- `classic-scangame-core` handles game setup validation, archive/loose-file checks, and related install-scanning workflows
- `classic-cpp-bridge-game-entrypoints.md` documents how the active C++ bridge narrows and forwards path/game/scangame Rust APIs
- `classic-cpp-bridge-data-entrypoints.md` documents how the active C++ bridge narrows and forwards config/file/database/scanner Rust APIs plus bridge-local helper behavior
- `classic-cpp-bridge-scan-progress-callback.md` documents the current `classic::scanner` batch progress callback contract, event ordering expectations, and bridge-local drain behavior
- `classic-gui-scan-progress-consumer.md` documents how the active Qt frontend consumes that batch callback contract and turns it into visible progress and status-bar state
- `classic-gui-scan-result-ordering.md` documents how the active Qt frontend handles completion-order batch results, uses `input_index` to recover original row identity, and keeps Results-tab ordering separate from scan ordering
- `binding-parity-overview.md` provides the complete per-crate binding surface reference for all shared Rust crates across C++, Node, and Python
- `node-python-contract-map.md` points contributors to the active Node and Python contract files, wrapper modules, and parity-report entry points
- `binding-contract-refresh-note.md` explains the current maintainer expectation for refreshing C++ baseline, Node `index.d.ts`, and Python `.pyi` contract artifacts separately or in the same change
- `classic-scanlog-core` consumes config data, crashgen rules, and optional DB lookups while treating OG/VR selection as a Version Registry-backed config-building concern
- `binding-parity-policy.md` states the one-tier parity policy, gate ownership, and the step-by-step workflow for adding a new public Rust API across all three bindings
- `error-contract.md` documents the intentionally different error shapes used by each binding surface (C++ empty-string sentinels, Node error codes, Python typed exceptions) with concrete source examples

Scope notes:

- These pages document contributor-relevant public Rust APIs, not every internal helper.
- The docs describe behavior visible in source today; if source and docs diverge, update both in the same change.
- Runtime ownership stays outside these crates. Follow the shared-runtime guidance in [`AGENTS.md`](../../AGENTS.md).
