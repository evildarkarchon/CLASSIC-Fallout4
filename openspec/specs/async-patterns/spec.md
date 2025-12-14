# async-patterns Specification

## Purpose
TBD - created by archiving change refactor-asyncbridge-usage. Update Purpose after archive.
## Requirements
### Requirement: AsyncBridge Usage Boundaries
AsyncBridge SHALL only be used in GUI worker contexts (Qt threads) and testing. Production CLI code MUST NOT use AsyncBridge or `create_sync_wrapper()`.

#### Scenario: GUI worker uses AsyncBridge
- **WHEN** a QThread worker needs to call async functions
- **THEN** it SHALL use `AsyncBridge.get_instance().run_async(coro)`
- **AND** this is the correct pattern for GUI-to-async bridging

#### Scenario: CLI entry point uses async-first pattern
- **WHEN** a CLI application starts (e.g., `CLASSIC_ScanLogs.py`, `CLASSIC_ScanGame.py`)
- **THEN** the entry point SHALL use `asyncio.run(main())` with a single async `main()` function
- **AND** all operations within `main()` SHALL use direct `await` calls
- **AND** no AsyncBridge calls SHALL be made in the CLI execution path

#### Scenario: Test uses AsyncBridge for convenience
- **WHEN** a test needs to call async functions from a sync test context
- **THEN** it MAY use `create_sync_wrapper()` or `AsyncBridge`
- **AND** this is acceptable because tests are not production performance paths

#### Scenario: Non-GUI production code attempts AsyncBridge usage
- **WHEN** production code outside GUI workers imports or uses AsyncBridge
- **THEN** this SHALL be considered an architecture violation
- **AND** the code MUST be refactored to use async-first pattern

### Requirement: Dual Interface Pattern for Shared Modules
Modules used by both GUI and CLI SHALL provide separate async and sync interfaces with clear documentation of intended usage.

#### Scenario: Module provides async primary API
- **WHEN** a module provides async functionality
- **THEN** the async version SHALL be the primary API (e.g., `generate_result_async()`)
- **AND** documentation SHALL indicate this is for CLI and direct async usage

#### Scenario: Module provides GUI sync wrapper
- **WHEN** a module provides a sync wrapper for GUI use
- **THEN** the sync wrapper SHALL be clearly documented as "GUI-only"
- **AND** the wrapper SHALL use AsyncBridge internally
- **AND** the wrapper SHALL NOT be called from CLI production paths

#### Scenario: Sync wrapper documentation
- **WHEN** a sync wrapper is defined for GUI use
- **THEN** its docstring SHALL include "GUI-only" or "For GUI workers only"
- **AND** the docstring SHALL reference the async alternative for CLI use

### Requirement: Single Event Loop in CLI Applications
CLI applications SHALL maintain a single event loop throughout their execution to avoid the overhead of creating/destroying loops.

#### Scenario: CLI main function is async
- **WHEN** a CLI application is structured
- **THEN** it SHALL have an `async def main()` function
- **AND** `asyncio.run(main())` SHALL be called exactly once at the entry point
- **AND** all async operations SHALL occur within the `main()` function's execution scope

#### Scenario: CLI avoids multiple event loops
- **WHEN** a CLI operation needs to call multiple async functions
- **THEN** all calls SHALL use direct `await` within the same event loop
- **AND** no `asyncio.run()` or `create_sync_wrapper()` calls SHALL occur within the async context

### Requirement: AsyncBridge Import Classification
Files importing AsyncBridge SHALL be classified into tiers to enable systematic refactoring and enforcement.

#### Scenario: Tier 1 Core files
- **WHEN** `ClassicLib/AsyncBridge.py` or `ClassicLib/_async_utils/bridge_helpers.py` imports AsyncBridge
- **THEN** this is Tier 1 (Core) and SHALL NOT be refactored

#### Scenario: Tier 2 Legitimate files
- **WHEN** GUI worker files (e.g., `ClassicLib/Interface/Workers.py`), test files, or sync adapter modules import AsyncBridge
- **THEN** this is Tier 2 (Legitimate) and SHALL NOT be refactored
- **AND** these files MAY continue using AsyncBridge

#### Scenario: Tier 3 Violation files
- **WHEN** non-GUI production code imports AsyncBridge
- **THEN** this is Tier 3 (Violation) and SHALL be refactored
- **AND** the refactoring SHALL convert to async-first pattern

### Requirement: Entry Point Compliance
All Python CLI entry points SHALL follow the async-first pattern.

#### Scenario: CLASSIC_ScanLogs.py entry point
- **WHEN** `CLASSIC_ScanLogs.py` is executed
- **THEN** it SHALL call `asyncio.run(main())` with an async `main()` function
- **AND** no AsyncBridge usage SHALL occur in the execution path

#### Scenario: CLASSIC_ScanGame.py entry point
- **WHEN** `CLASSIC_ScanGame.py` is executed
- **THEN** it SHALL call `asyncio.run(main())` with an async `main()` function
- **AND** no AsyncBridge usage SHALL occur in the execution path

#### Scenario: Entry point with sync wrappers at module level
- **WHEN** an entry point module defines sync wrappers using `create_sync_wrapper()`
- **THEN** these wrappers SHALL only be exported for GUI use
- **AND** the CLI `main()` function SHALL NOT call these wrappers

