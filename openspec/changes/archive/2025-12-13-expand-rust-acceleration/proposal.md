# Change: Expand Rust Acceleration Usage

## Why

Investigation reveals that several Rust acceleration components exist but are not being utilized in the Python codebase. The factory pattern and integration infrastructure are well-designed, but some components either:
1. Have factory functions that return `None` (no Python consumer integration)
2. Exist in the factory but are never called from the codebase
3. Have partial integration that could be expanded

This represents missed performance opportunities of 10-150x speedups in various operations.

## What Changes

### High Priority (40x+ speedup potential)

1. **RecordScanner Integration** (40x speedup)
   - Factory `get_record_scanner()` exists but `OrchestratorCore` uses pure Python `RecordScanner`
   - Change `OrchestratorCore.py` to use factory function instead of direct instantiation
   - Affected: `ClassicLib/ScanLog/OrchestratorCore.py:114`

2. **Consistent File I/O Factory Usage** (10-40x speedup)
   - Some code instantiates `FileIOCore` directly instead of using `get_file_io()`
   - Audit and update all direct instantiations to use factory pattern
   - Ensures singleton pattern and Rust acceleration are consistently applied

### Medium Priority (10-50x speedup potential)

3. **Path Operations Integration** (10-50x speedup)
   - Factory `get_path_operations()` currently returns `None` for Python fallback
   - Implement Python fallback and integrate into path validation code
   - Accelerates registry queries and game path detection

4. **Phase 4 Utility Module Integration**
   - `get_constants()` - Not integrated into Python consumers
   - `get_version_utils()` - Version utilities not using Rust
   - `get_resource_mgmt()` - Resource detection not optimized
   - `get_xse_utils()` - XSE detection could use Rust
   - `get_web_utils()` - Web utilities not using Rust

### Testing & Validation

5. **Integration Tests for Expanded Usage**
   - Add tests verifying RecordScanner uses Rust when available
   - Add tests for path operations Rust/Python parity
   - Add performance regression tests

## Impact

- **Affected specs**: `rust-orchestrator`
- **Affected code**:
  - `ClassicLib/ScanLog/OrchestratorCore.py` - RecordScanner integration
  - `ClassicLib/ScanLog/HybridOrchestrator.py` - Verify complete factory usage
  - `ClassicLib/integration/factory.py` - Path operations fallback
  - `ClassicLib/Utils/` - Utility integrations
  - `tests/rust_integration/` - New integration tests

- **Performance gains**:
  - RecordScanner: 40x speedup for record detection in callstacks
  - Path operations: 10-50x speedup for game path detection
  - File I/O: Consistent 10-40x speedup across codebase

- **Risk**: Low - All changes use existing factory pattern with Python fallbacks
