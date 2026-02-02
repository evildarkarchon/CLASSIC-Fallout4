# Phase 5: Fallback Pruning - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove Python fallback implementations in `ClassicLib/integration/python/` where Rust is proven stable, make factory functions return typed Rust objects directly (or raise clear errors), and update all PyInstaller spec files. Currently 8 fallback files exist: `database_py.py`, `file_io_py.py`, `formid_py.py`, `mod_detector_py.py`, `parser_py.py`, `plugin_py.py`, `record_py.py`, `report_py.py`.

</domain>

<decisions>
## Implementation Decisions

### Removal criteria
- A Rust module is "proven stable" if the full test suite (`uv run pytest -n auto`) passes with the fallback removed
- No production runtime proof required — test suite passage is sufficient
- Remove fallbacks one-by-one: remove each fallback, run full tests, commit. Isolate breakage to one module at a time
- Deleted fallback files are removed entirely from the repo (git history preserves them)

### Error behavior
- Hard error at startup: app checks for all required Rust modules at launch and refuses to start if any are missing
- Fail fast: stop at the first missing module and report it immediately
- Error messages include technical details: name the missing module, show import error, suggest reinstall (aimed at developers/power users)
- For any fallbacks that ARE kept (if Claude validates one genuinely needs it): log a warning that Rust acceleration is unavailable for that component

### Retention decisions
- Target: zero fallbacks remaining (remove all 8 files)
- Zero preferred, but Claude validates: if a module's Rust implementation genuinely can't cover all code paths, keep that one fallback
- If all fallbacks are removed, delete the `integration/python/` directory entirely
- Each fallback removal also updates `factory.py` in the same step: remove the try/except fallback import path and type-narrow the return type

### Build verification
- No baseline build needed — current state assumed working after Phase 4
- PyInstaller build after all removals complete
- Minimum smoke test: GUI launches without `ModuleNotFoundError` (no crash log scan required)
- Auto-update ALL project spec files: `CLASSIC.spec`, `CLASSIC-GUI-OneFile.spec`, `CLASSIC-CLI.spec`, `CLASSIC-QML.spec`, `CLASSIC-QML-Dir.spec`, `CLASSIC-Test.spec`
- Remove deleted fallback modules from hiddenimports, add any new Rust-only imports needed

### Claude's Discretion
- Order of fallback removal (which module to remove first/last)
- Whether any specific fallback genuinely needs to be retained based on Rust coverage analysis
- Exact startup validation implementation pattern
- How to structure the one-by-one removal commits

</decisions>

<specifics>
## Specific Ideas

- User wants this to be thorough but fast — one-by-one removal with full test suite, but no extra baseline builds
- The `integration/python/` directory should be completely eliminated if possible — clean break from the fallback era
- Factory.py cleanup is atomic with each fallback removal, not a separate pass

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-fallback-pruning*
*Context gathered: 2026-02-02*
