# CLASSIC API Docs

Contributor-facing API guides for active Rust business-logic crates live here.

Use this directory in this order:

1. [`QUICK_START.md`](QUICK_START.md) - repo-level setup, build, and test workflow
2. [`classic-shared-core.md`](classic-shared-core.md) - shared runtime, error, path, performance, and string foundation helpers
3. [`classic-perf-core.md`](classic-perf-core.md) - global timing sample collection, summaries, and scoped timer helpers
4. [`classic-registry-core.md`](classic-registry-core.md) - process-wide typed singleton registry and convenience key helpers
5. [`classic-message-core.md`](classic-message-core.md) - shared message DTOs, routing enums, and startup/log formatting helpers
6. [`classic-yaml-core.md`](classic-yaml-core.md) - shared YAML loading, caching, and extraction helpers
7. [`classic-settings-core.md`](classic-settings-core.md) - shared YAML stream parse/merge helpers plus settings cache and sync/async loaders
8. [`classic-version-registry-core.md`](classic-version-registry-core.md) - version registry and OG/NG/AE/VR selection metadata
9. [`classic-constants-core.md`](classic-constants-core.md) - shared game/version/YAML identifiers and small convenience enums
10. [`classic-version-core.md`](classic-version-core.md) - version parsing, text extraction, and PE-version helpers
11. [`classic-web-core.md`](classic-web-core.md) - small URL, user-agent, and mod-site helper layer
12. [`classic-update-core.md`](classic-update-core.md) - async GitHub release/update-check client and DTO layer
13. [`classic-crashgen-settings-core.md`](classic-crashgen-settings-core.md) - shared crashgen settings rule model and evaluator
14. [`classic-config-core.md`](classic-config-core.md) - YAML/config loading built on top of YAML and Version Registry metadata
15. [`classic-config-core-yaml-schema.md`](classic-config-core-yaml-schema.md) - standalone runtime contract for settings discovery, merged YAML semantics, and consumed schema keys
16. [`classic-path-core.md`](classic-path-core.md) - game-path, documents-path, validation, and backup helpers
17. [`classic-xse-core.md`](classic-xse-core.md) - XSE loader/version detection helpers used by setup checks and bindings
18. [`game-setup-workflow.md`](game-setup-workflow.md) - current cross-crate setup/install validation flow across path, XSE, scangame, and version registry crates
19. [`formid-settings-boundary.md`](formid-settings-boundary.md) - current split between Rust config serialization and scan-time FormID DB path consumption
20. [`classic-file-io-core.md`](classic-file-io-core.md) - shared file I/O, traversal, hashing, and log collection helpers
21. [`classic-resource-core.md`](classic-resource-core.md) - lightweight resource classification, enumeration, and per-file validation helpers
22. [`classic-database-core.md`](classic-database-core.md) - SQLite/FormID lookup pool used by analysis paths
23. [`formid-sqlite-conventions.md`](formid-sqlite-conventions.md) - practical fixture/schema/path rules for contributor FormID DB work
24. [`classic-scangame-core.md`](classic-scangame-core.md) - game-installation, archive, loose-file, and setup validation workflows
25. [`classic-cpp-bridge-game-entrypoints.md`](classic-cpp-bridge-game-entrypoints.md) - active C++ bridge entry points for path, game, and scangame workflows
26. [`classic-cpp-bridge-data-entrypoints.md`](classic-cpp-bridge-data-entrypoints.md) - active C++ bridge entry points for config, file I/O, database, and scanlog workflows
27. [`classic-cpp-bridge-scan-progress-callback.md`](classic-cpp-bridge-scan-progress-callback.md) - current batch scan progress callback contract for `classic::scanner`
28. [`classic-gui-scan-progress-consumer.md`](classic-gui-scan-progress-consumer.md) - how `classic-gui` consumes bridge scan progress through `ScanWorker`, `BatchProgressModel`, `ScanController`, and `MainWindow`
29. [`classic-gui-scan-result-ordering.md`](classic-gui-scan-result-ordering.md) - current Qt-side behavior for completion-order batch results, `input_index` correlation, and Results-tab ordering boundaries
30. [`binding-parity-overview.md`](binding-parity-overview.md) - current C++ bridge, Node, and Python exposure comparison for shared Rust crates
31. [`node-python-contract-map.md`](node-python-contract-map.md) - where the active Node and Python public contracts, wrapper files, and parity artifacts live
32. [`binding-contract-refresh-note.md`](binding-contract-refresh-note.md) - when Node `index.d.ts` and Python `.pyi` contract artifacts should refresh separately versus together
33. [`classic-scanlog-core.md`](classic-scanlog-core.md) - crash-log analysis built on top of loaded config data and optional DB lookups

That order matches the current layering in `ClassicLib-rs/business-logic/`:

- `classic-shared-core` provides the shared Tokio runtime plus common error, path, performance, and string helpers
- `classic-perf-core` provides process-wide timing buckets, scoped timers, and summary computation for lightweight metrics collection
- `classic-registry-core` provides process-wide typed singleton storage and key helpers for callers that share state across boundaries
- `classic-message-core` provides shared message DTOs, routing enums, and structured/startup logging helpers used by bindings and bridge code
- `classic-yaml-core` provides shared YAML parsing, caching, and merge helpers
- `classic-settings-core` provides shared YAML stream parsing/merge helpers plus raw settings loading and a sync/async cache layer keyed by caller-chosen strings
- `classic-version-registry-core` loads registry-backed version and crashgen metadata on top of YAML helpers
- `classic-constants-core` provides small shared enums/constants that higher layers use to label games, YAML files, and Fallout 4 mode selections
- `classic-version-core` adds low-level version parsing, text extraction, and PE-version helpers on top of constants and registry re-exports
- `classic-web-core` provides small web-oriented helpers without owning an HTTP client or runtime
- `classic-update-core` provides async GitHub release/update-check behavior for callers running on the shared runtime
- `classic-crashgen-settings-core` defines the reusable rule/evaluator model consumed by higher layers
- `classic-config-core` loads YAML and uses Version Registry plus crashgen-settings types to build config data
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
- `binding-parity-overview.md` compares which shared Rust crates are currently exposed through C++, Node, and Python bindings, and where those surfaces diverge
- `node-python-contract-map.md` points contributors to the active Node and Python contract files, wrapper modules, and parity-report entry points
- `binding-contract-refresh-note.md` explains the current maintainer expectation for refreshing Node `index.d.ts` and Python `.pyi` contract artifacts separately or in the same change
- `classic-scanlog-core` consumes config data, crashgen rules, and optional DB lookups while treating OG/VR selection as a Version Registry-backed config-building concern

Scope notes:

- These pages document contributor-relevant public Rust APIs, not every internal helper.
- The docs describe behavior visible in source today; if source and docs diverge, update both in the same change.
- Runtime ownership stays outside these crates. Follow the shared-runtime guidance in [`AGENTS.md`](../../AGENTS.md).
