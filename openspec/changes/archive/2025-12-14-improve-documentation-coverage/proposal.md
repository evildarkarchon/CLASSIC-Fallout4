# Proposal: Improve Documentation Coverage

## Summary
Add missing Returns sections to Python docstrings and fix Rust documentation warnings to achieve complete documentation coverage across the codebase.

## Motivation
Documentation completeness is critical for maintainability:
- **39 Python functions** have docstrings but are missing `Returns:` sections, violating Google-style docstring standards
- **~38 Rust documentation warnings** include broken intra-doc links and malformed HTML tags
- Project standards (06-python-documentation.md, 07-rust-development.md) require full documentation

## Scope

### In Scope
1. Add `Returns:` sections to 39 Python functions in ClassicLib
2. Fix ~38 Rust documentation warnings across workspace crates
3. Update code-organization spec with documentation completeness requirements

### Out of Scope
- Adding new docstrings where none exist (separate effort)
- Changing function signatures or behavior
- Adding Examples sections (optional enhancement)

## Technical Approach

### Python Docstring Completions
Target files with missing Returns sections:
- `ClassicLib/rust_loader.py` (6 functions)
- `ClassicLib/FileIO/` (6 functions)
- `ClassicLib/MessageHandler/` (6 functions)
- `ClassicLib/Utils/Async.py` (6 functions)
- `ClassicLib/ScanGame/` (1 function)
- `ClassicLib/rust/file_io_rust.py` (2 functions)
- Other scattered functions (~12 total)

Each function will receive a `Returns:` section matching its return type annotation.

### Rust Documentation Fixes
Fix categories:
1. **Malformed HTML tags** (~15 warnings): Escape `<GAME>`, `<String>`, etc. in doc comments
2. **Broken intra-doc links** (~20 warnings): Fix or escape `[UiState]`, `[Archive]`, etc.
3. **Empty code blocks** (2 warnings): Add content or remove empty blocks

## Impact Assessment
- **Risk**: LOW - Documentation-only changes with no behavioral modifications
- **Testing**: Run `cargo doc --workspace` and verify zero warnings
- **CI Impact**: None (documentation warnings not currently blocking)

## Success Criteria
1. All Python public functions with return types have `Returns:` sections
2. `cargo doc --workspace --no-deps` produces zero warnings
3. Documentation standards spec updated with completeness requirements
