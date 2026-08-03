# Graph Report - D:\repos\CLASSIC-Fallout4\classic-cli  (2026-07-28)

## Corpus Check
- Corpus is ~19,361 words - fits in a single context window. You may not need a graph.

## Summary
- 358 nodes · 614 edges · 19 communities (17 shown, 2 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 13 edges (avg confidence: 0.81)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17

## God Nodes (most connected - your core abstractions)
1. `CliArgs` - 31 edges
2. `PreparedScanUserSettings` - 25 edges
3. `ProgressDisplay` - 21 edges
4. `path_` - 19 edges
5. `ThreadPool` - 18 edges
6. `BoundaryCancellingObserver` - 17 edges
7. `run_scan_pipeline()` - 13 edges
8. `impl_` - 12 edges
9. `CliScanRunObserver` - 12 edges
10. `CliScanRunMessage` - 11 edges

## Surprising Connections (you probably didn't know these)
- `resolve_classic_root()` --references--> `path_`  [EXTRACTED]
  src/app_update.cpp → tests/test_scan_run_contract.cpp
- `update_check_enabled_for_root()` --references--> `path_`  [EXTRACTED]
  src/app_update.cpp → tests/test_scan_run_contract.cpp
- `message_text()` --references--> `CliScanRunMessage`  [EXTRACTED]
  tests/test_scanner.cpp → src/scan_run_cli.h
- `minimal_settings()` --references--> `PreparedScanUserSettings`  [EXTRACTED]
  tests/test_scanner.cpp → src/user_settings_action.h
- `main()` --calls--> `run_check_app_update()`  [INFERRED]
  src/main.cpp → src/app_update.cpp

## Import Cycles
- None detected.

## Communities (19 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (44): BOOL, DWORD, ScanRunContractInfrastructureErrorStage, ScanRunContractLogFailureStage, ScanRunContractRunResult, ScanRunInstalledYamlDataDiagnosticKind, ScanRunInstalledYamlDataProvenance, ScanRunLocalIgnoreYamlDataState (+36 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (26): ScanRunContractStatus, string, vector, parse_args(), main(), print_version(), setup_console(), string (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (20): array, EventSnapshot, ScanRunContractEventKind, BoundaryCancellingObserver, events_, has_trigger_index_, trigger_, trigger_index_ (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (24): ScanRunContractDiscoverySource, set, string_view, string, make_settings_root(), ScopedCurrentPath, original, copy_shared_log() (+16 more)

### Community 4 - "Community 4"
Cohesion: 0.13
Nodes (22): atomic, id, InFlightEntry, map, string, string, time_point, key_for_thread() (+14 more)

### Community 5 - "Community 5"
Cohesion: 0.14
Nodes (20): Impl, scanner::ScanRunObserver, CliScanRunCancellation, unique_ptr, CliScanRunObserver, game_, progress_, ScanRunContractEvent (+12 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (16): condition_variable, queue, function, function, thread, vector, ThreadPool, active_tasks_ (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (21): string, vector, PreparedScanUserSettings, classification, commit_eligibility, configured_documents_root, custom_scan_directory, fcx_mode (+13 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (19): CliArgs, apply_yaml_updates, check_app_update, check_yaml_updates, fcx_mode, game, game_version, game_version_was_explicit (+11 more)

### Community 9 - "Community 9"
Cohesion: 0.32
Nodes (14): confirm_apply_prompt(), string, init_runtime_for_yaml_update(), read_update_check_setting(), report_rollback(), report_status(), resolve_settings_paths(), run_apply_yaml_updates() (+6 more)

### Community 10 - "Community 10"
Cohesion: 0.31
Nodes (12): CrashLogScanSettingsDto, GameSetupSettingsDto, Snapshot, optional, string, formid_database_applies_to_game(), persist_unsolved_logs_destination_option(), prepare_scan_user_settings() (+4 more)

### Community 11 - "Community 11"
Cohesion: 0.20
Nodes (10): atomic_bool, Box, impl_, monitor_, requested_, stop_, token_, request (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (10): NotificationStatusDto, optional, String, init_runtime_for_app_update(), is_classification(), or_unknown(), report_notification(), resolve_classic_root() (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.25
Nodes (9): classic_assert_msvc_linker, CLI Rust Bridge Tests, classic-cli Executable, classic-cli CMake Project, Bridge-Free CLI Unit Tests, classic-cpp-bridge Corrosion Target, CLI YAML-Sourced Version Identity, Shared Crash Log Scan-Run Fixture (+1 more)

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (6): initializer_list, ArgvBuilder, args, ptrs, string, vector

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (8): catch2, cli11, fmt, builtin-baseline, dependencies, name, $schema, version

## Knowledge Gaps
- **78 isolated node(s):** `game`, `game_version`, `game_was_explicit`, `game_version_was_explicit`, `fcx_mode` (+73 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CliArgs` connect `Community 8` to `Community 0`, `Community 1`, `Community 5`, `Community 9`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `PreparedScanUserSettings` connect `Community 7` to `Community 0`, `Community 1`, `Community 10`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `ProgressDisplay` connect `Community 4` to `Community 5`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **What connects `game`, `game_version`, `game_was_explicit` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.08383838383838384 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.07557354925775979 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09411764705882353 - nodes in this community are weakly interconnected._