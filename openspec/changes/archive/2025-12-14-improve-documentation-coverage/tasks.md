# Tasks: Improve Documentation Coverage

## Phase 1: Python Docstring Returns Sections

### Task 1.1: Add Returns sections to rust_loader.py
- [x] **File**: `ClassicLib/rust_loader.py`
- [x] **Functions**: `is_loaded()`, `get_load_info()`, `load_extension()`, `load_rust_extensions()`, `is_rust_available()`, `get_rust_info()`
- [x] **Verification**: `uv run ruff check ClassicLib/rust_loader.py --select D`

### Task 1.2: Add Returns sections to FileIO modules
- [x] **Files**: `ClassicLib/FileIO/Async.py`, `ClassicLib/FileIO/core.py`, `ClassicLib/FileIO/sync_adapters.py`
- [x] **Functions**: 6 total (see proposal)
- [x] **Verification**: `uv run ruff check ClassicLib/FileIO/ --select D`

### Task 1.3: Add Returns sections to MessageHandler modules
- [x] **Files**: `ClassicLib/MessageHandler/handler.py`, `ClassicLib/MessageHandler/qt_compat.py`, `ClassicLib/MessageHandler/qt_handler.py`
- [x] **Functions**: 6 total
- [x] **Verification**: `uv run ruff check ClassicLib/MessageHandler/ --select D`

### Task 1.4: Add Returns sections to Utils/Async.py
- [x] **File**: `ClassicLib/Utils/Async.py`
- [x] **Functions**: `smart_run_in_executor()`, `async_map()`, `async_map_smart()`, `batch_process()`, `batch_process_smart()`
- [x] **Verification**: `uv run ruff check ClassicLib/Utils/Async.py --select D`

### Task 1.5: Add Returns sections to remaining files
- [x] **Files**: `ClassicLib/ScanGame/`, `ClassicLib/rust/file_io_rust.py`, others
- [x] **Functions**: ~12 remaining
- [x] **Verification**: Run Python docstring check script to confirm zero missing Returns

## Phase 2: Rust Documentation Warnings

### Task 2.1: Fix HTML tag warnings in file-io crates
- [x] **Files**: `rust/python-bindings/classic-file-io-py/src/generation.rs`, `rust/business-logic/classic-file-io-core/`
- [x] **Issue**: Escape `<GAME>`, `<String>`, `<Duration>` as `` `GAME` ``, `` `String` ``, etc.
- [x] **Verification**: `cargo doc -p classic-file-io-py -p classic-file-io-core --no-deps 2>&1 | grep warning`

### Task 2.2: Fix HTML tag warnings in shared crates
- [x] **Files**: `rust/foundation/classic-shared-py/`, `rust/foundation/classic-shared-core/`
- [x] **Issue**: Same HTML tag escaping
- [x] **Verification**: `cargo doc -p classic-shared-py -p classic-shared-core --no-deps 2>&1 | grep warning`

### Task 2.3: Fix broken links in TUI handlers
- [x] **Files**: `rust/ui-applications/classic-tui/src/handlers/mod.rs`
- [x] **Issue**: Fix or escape `[UiState]`, `[handle_*_keys]` links
- [x] **Verification**: `cargo doc -p classic-tui --no-deps 2>&1 | grep warning`

### Task 2.4: Fix remaining Rust doc warnings
- [x] **Files**: Various crates (path-core, message-core, scanlog-core)
- [x] **Issue**: Broken links (`[Archive]`, `[FF]`), empty code blocks
- [x] **Verification**: `cargo doc --workspace --no-deps 2>&1 | grep warning | wc -l` should be 0

## Phase 3: Spec Updates (Optional)

### Task 3.1: Add documentation completeness requirement to code-organization spec
- [x] **File**: `openspec/specs/code-organization/spec.md`
- [x] **Content**: Requirement for Returns sections in all public functions with non-None return types
- [x] **Verification**: `openspec validate improve-documentation-coverage`

## Verification

### Final Verification Commands
```bash
# Python - zero missing Returns sections
uv run python -c "... docstring checker script ..." | grep "Total: 0"

# Rust - zero documentation warnings
cargo doc --workspace --no-deps 2>&1 | grep -c "warning:" | grep "^0$"
```

## Dependencies
- Tasks can be executed in parallel within each phase
- Phase 2 (Rust) can run in parallel with Phase 1 (Python)
- Phase 3 depends on Phase 1 and 2 completion
