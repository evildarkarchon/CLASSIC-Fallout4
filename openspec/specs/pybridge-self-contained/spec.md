## Purpose

Define requirements for making `classic-pybridge-py` self-contained while preserving the existing Python API behavior.

## Requirements

### Requirement: classic-pybridge-py is self-contained
`classic-pybridge-py` SHALL own its bridge metrics and runtime helper logic directly, with no separate `-core` counterpart crate. The `classic-pybridge-core` crate SHALL NOT exist in the workspace.

#### Scenario: Workspace member absent
- **WHEN** the workspace `Cargo.toml` is inspected
- **THEN** `"business-logic/classic-pybridge-core"` SHALL NOT appear in the `members` array

#### Scenario: Crate directory absent
- **WHEN** the `ClassicLib-rs/business-logic/` directory is listed
- **THEN** no `classic-pybridge-core/` subdirectory SHALL exist

### Requirement: Bridge metrics use a single lock layer
The global metrics store SHALL use a `DashMap` directly, without an outer `RwLock` or `Mutex` wrapper, to avoid redundant lock acquisitions.

#### Scenario: Metric record path acquires one lock
- **WHEN** `record_bridge_operation()` is called
- **THEN** only the `DashMap` shard lock SHALL be acquired (no outer lock)

#### Scenario: Metrics are still thread-safe
- **WHEN** multiple Tokio tasks call `record_bridge_operation()` concurrently
- **THEN** all operations SHALL complete without data races or panics

### Requirement: Python API surface is unchanged
The `classic_pybridge` Python extension module SHALL expose the same functions, classes, and behaviour as before this change.

#### Scenario: Module imports successfully
- **WHEN** Python executes `import classic_pybridge`
- **THEN** the import SHALL succeed and `classic_pybridge.__version__` SHALL be accessible

#### Scenario: Record and retrieve metrics
- **WHEN** Python calls `classic_pybridge.record_operation(BridgeOperationType.RunAsync, 0.1, True)`
- **THEN** a subsequent call to `classic_pybridge.get_metrics()` SHALL return a `BridgeMetrics` with `run_async_count >= 1`

#### Scenario: Runtime info available
- **WHEN** Python calls `classic_pybridge.is_runtime_available()`
- **THEN** the return value SHALL be `True`

### Requirement: Architecture documentation reflects the exception
CLAUDE.md, AGENTS.md, and GEMINI.md SHALL document that `classic-pybridge-py` is an explicit exception to the `*-core -> *-py` pairing rule.

#### Scenario: Exception documented in agent files
- **WHEN** the architecture section of any agent instruction file is read
- **THEN** it SHALL note that `classic-pybridge-py` contains its own logic directly, with no `-core` counterpart, and that this is intentional
