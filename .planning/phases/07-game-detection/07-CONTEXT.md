# Phase 7: Game Detection - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Rust GamePathFinder to Python wrapper, making Rust the primary code path for all game path detection. Reduce Python `game_path.py` from ~700 lines to <100 lines of thin delegation. XSE/ENB integrity validation is included but gated by FCX Mode setting (only validates when checking your own installation, not when analyzing others' logs).

</domain>

<decisions>
## Implementation Decisions

### Fallback Strategy
- **Rust-only, hard fail** — No Python fallback if Rust module fails to import
- When game detection fails (path not found), prompt user for manual path entry (GUI dialog or console)
- User-provided paths validated by Rust `GamePathFinder.validate_game_path()` — full Rust validation, not Python
- Rust handles cache reading and validation — Python passes cache file paths, Rust reads and validates

### Error Handling
- **Technical errors shown directly** — Let Rust exceptions bubble up without translation to user-friendly messages
- Registry query failures (Windows) logged at **debug level** — expected on GOG/non-Steam installs
- XSE log parsing failures logged at **warning level** — helps users understand auto-detection issues
- Invalid cached paths **auto-invalidate** — clear bad cache entries and retry detection (self-healing)

### Async Support
- **Both sync and async versions wire to Rust** — preserve existing dual-interface pattern
- Async contexts use `asyncio.run_in_executor()` for Rust calls — prevents blocking event loop
- Keep `create_async()` factory method — matches existing async initialization pattern for YAML loading
- Use **Phase 6 Rust settings cache** (`classic_settings`) for YAML settings loading — consistent with migration

### Validation Scope
- **XSE/ENB validation only runs when FCX Mode is enabled** — not when analyzing other users' logs
- Complete XSE integrity checking:
  - XSE loader exists (`f4se_loader.exe` in game directory)
  - XSE version compatibility (read log, verify against game version)
  - XSE DLLs exist (`f4se_*.dll` in Data/F4SE/Plugins)
- ENB validation:
  - ENB binaries exist (`d3d11.dll`, `d3dcompiler_46e.dll` in game folder)
  - ENB config exists and is readable (`enbseries.ini`)
- **Store validation results in GlobalRegistry** — XSE_VALID, ENB_PRESENT flags for other components
- Validation is **separate step** from detection — `game_path_find()` returns path, caller validates

### Claude's Discretion
- Exact error message formatting for Rust exceptions
- Whether to log successful detection at debug level
- Implementation details for cache file path passing to Rust
- GlobalRegistry key names for validation status flags

</decisions>

<specifics>
## Specific Ideas

- "Python is the UI, Rust is the engine" — this phase embodies that principle for game detection
- FCX Mode gate ensures CLASSIC works for analyzing others' crash logs without requiring local game installation
- Phase 6 Rust cache should be leveraged for settings/cache reading consistency

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-game-detection*
*Context gathered: 2026-02-03*
