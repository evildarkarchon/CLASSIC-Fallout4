# Change: Refactor AsyncBridge Usage to Follow Documented Architecture

## Why

Per project documentation (`.claude/rules/08-memories.md`), AsyncBridge is ONLY for GUI workers (Qt threads) and testing. Production CLI code MUST use the async-first pattern with a single `asyncio.run()` at the entry point. Currently, ~22 files misuse AsyncBridge in non-GUI contexts, creating unnecessary event loops and performance overhead.

**Current State**: 32+ files reference AsyncBridge
**Expected**: 5-10 files (GUI workers + test utilities + AsyncBridge implementation)
**Violation**: ~22 files using AsyncBridge in non-GUI production contexts

## What Changes

### Phase 1: Establish Specification (This Proposal)
- Create `async-patterns` capability spec defining AsyncBridge usage boundaries
- Document legitimate vs. inappropriate usage patterns
- Define the async-first CLI pattern as the standard

### Phase 2: Categorize and Audit
- Categorize all AsyncBridge imports by legitimacy
- Identify files that need refactoring
- Document migration path for each violation

### Phase 3: Refactor Violations
- Refactor non-GUI production code to use async-first pattern
- Update sync wrappers to be GUI-only (with enforcement)
- Remove unnecessary AsyncBridge imports

## Impact

**Affected specs**: Creates new `async-patterns` capability

**Affected code** (estimated violations):
- `ClassicLib/ScanGame/ScanModInis.py` - Direct `AsyncBridge.get_instance()` calls
- `ClassicLib/ScanGame/Config.py` - AsyncBridge in FCXModeConfig methods
- `ClassicLib/ScanGame/GameFilesManager.py` - AsyncBridge for sync wrapper
- `ClassicLib/ScanGame/GameIntegrityOrchestrator.py` - Multiple AsyncBridge calls
- `ClassicLib/ScanGame/core/ini_fallback.py` - Direct bridge usage
- `ClassicLib/ScanLog/FormIDAnalyzerCore.py` - Uses `run_async`
- `ClassicLib/ScanLog/ScanLogsUtils.py` - Uses `run_async`
- `ClassicLib/rust/file_io_rust.py` - AsyncBridge in class methods
- `ClassicLib/FileGeneration.py` - Direct bridge usage

**Legitimate usage (no change needed)**:
- `ClassicLib/Interface/Workers.py` - QThread workers (correct)
- `ClassicLib/AsyncBridge.py` - Implementation itself
- `ClassicLib/_async_utils/bridge_helpers.py` - Helper module
- `ClassicLib/FileIO/sync_adapters.py` - Sync adapters for GUI
- `ClassicLib/YamlSettings/sync/cache.py` - Lazy GUI initialization
- Test files in `tests/` - Testing is valid use case

## Benefits

1. **Performance**: Eliminates ~22 unnecessary event loop creations per CLI invocation
2. **Clarity**: Clear boundaries between GUI and CLI code paths
3. **Maintainability**: Consistent async patterns across codebase
4. **Documentation**: Enforced architecture through specifications
