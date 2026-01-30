# Codebase Concerns

**Analysis Date:** 2026-01-29

## Known Bugs

**Arboard Heap Corruption on Windows (Clipboard Integration):**
- **Issue**: The `arboard` crate causes heap corruption in Windows CI environments when handling clipboard operations.
- **Files**: `rust/business-logic/classic-tui-deprecated/src/handlers/clipboard_handler.rs` (historical reference in commit fd625b60)
- **Current State**: Clipboard tests marked with `#[ignore]` attribute to prevent CI failures. Can be executed manually when needed.
- **Workaround**: Manual testing only; CI skips these tests. `is_clipboard_available()` test remains enabled as it doesn't interact with clipboard.
- **Impact**: TUI clipboard integration is untested in CI. Users may encounter unexpected behavior if clipboard operations fail silently.
- **Fix approach**: Monitor arboard crate updates for Windows heap safety improvements. Consider alternative clipboard library (e.g., `clipboard-win`) if arboard issues persist.

## Tech Debt

**Unresolved ConfigFileCache Initialization Error Handling:**
- **Issue**: When game root path is not found during ConfigFileCache initialization, the code raises `FileNotFoundError` without clear messaging to users.
- **Files**:
  - `ClassicLib/scanning/game/config.py` lines 172-173
  - `ClassicLib/scanning/game/scan_mod_inis.py` lines 58, 139
- **Impact**: Silent failures in INI scanning pipeline. Users get exception stack trace instead of helpful message. Unclear whether to raise or return error message.
- **Dependencies**: Related to `scan_mod_inis()` function which has same unresolved pattern.
- **Fix approach**: Implement consistent error handling pattern:
  1. Define whether this should be a fatal error or degraded mode
  2. Return `None` or error message object instead of raising
  3. Add user-facing notification via MessageHandler
  4. Update all call sites to handle returned error state

**Incomplete YAML Cache Path Implementation (Rust):**
- **Issue**: Cache YAML path in `classic-config-core` hardcoded as placeholder; doesn't retrieve actual user config directory.
- **Files**: `rust/business-logic/classic-config-core/src/config.rs` line 83-84 (YamlSource::Cache variant)
- **Current Behavior**: Returns `CLASSIC-Fallout4/cache.yaml` instead of platform-specific config directory (e.g., `~/.config/CLASSIC-Fallout4/` on Linux, `%APPDATA%/CLASSIC-Fallout4/` on Windows).
- **Impact**: Cache files may be created in wrong location across platforms. No cross-platform config directory support yet.
- **Fix approach**:
  1. Use `dirs` or `appdirs` crate for platform-specific paths
  2. Implement `get_config_home()` function in `classic-path-core`
  3. Update YamlSource::Cache to use proper config directory
  4. Add tests for each platform's expected path

## Performance Bottlenecks

**ConfigFileCache Hash Recalculation Overhead:**
- **Problem**: While hash caching exists (`_hash_cache`), ConfigFileCache scans entire game root on initialization using `Path.walk()`. File hashing uses `calculate_file_hash()` which reads entire file into memory.
- **Files**: `ClassicLib/scanning/game/config.py` lines 175-211 (initialization loop) and line 232 (`calculate_file_hash()` in Utils)
- **Scale Issue**: In large mod folders (100+ INI files spread across many directories), startup can stall for 2-5 seconds while hashing all duplicates.
- **Cause**:
  - No early termination for non-INI files (wasteful walk)
  - All files hashed even if not duplicates
  - Hash comparison runs before similarity check (redundant I/O)
- **Improvement path**:
  1. Add `.glob()` filtering instead of walk + manual extension checks
  2. Implement two-phase detection: hash only files with matching names first
  3. Cache hashes between runs (persist to disk)
  4. Consider async file I/O for parallel hash calculation

**AsyncBridge Overhead in GUI Workers:**
- **Problem**: All GUI worker methods that need async functionality use `AsyncBridge.run_async()`, which creates event loop polling overhead on every call.
- **Files**: `ClassicLib/scanning/game/scan_mod_inis.py` lines 87-88 (sync wrapper), `ClassicLib/scanning/game/config.py` lines 328, 564
- **Symptom**: GUI becomes unresponsive during large scan operations (500+ files to parse).
- **Current Approach**: Documented as "GUI workers only" - not for CLI/TUI use. Causes additional event loop overhead.
- **Improvement path**:
  1. Migrate to native async in PyO3 boundary (eliminate sync wrapper phase)
  2. Use Python's `asyncio` event loop directly in GUI via `qasync` (already dependency)
  3. Batch async operations to reduce context switches
  4. Profile actual overhead with performance benchmarks

## Fragile Areas

**Dual Interface Pattern in FormIDAnalyzer (Deprecated Sync Wrappers):**
- **Files**: `ClassicLib/scanning/logs/analyzers/FormIDAnalyzer.py` (deprecated) and `FormIDAnalyzerCore.py` (async)
- **Why Fragile**: Maintains both sync and async versions of same logic:
  - `analyze_segment()` async and sync versions
  - `analyze_extended_crash_data()` async and sync versions
  - Sync versions documented as "GUI-only" but could be called from CLI
- **Safe Modification**:
  1. Remove all sync wrapper methods
  2. Update imports: `from ClassicLib.scanning.logs.analyzers.FormIDAnalyzerCore import analyze_segment_async`
  3. Use async everywhere; wrap at application entry points only
  4. Add tests ensuring async is used in non-GUI contexts
- **Test Coverage Gaps**: No tests verify sync wrappers aren't called in CLI/TUI mode. No type hints preventing misuse.

**ConfigFileCache Duplicate Detection Logic:**
- **Files**: `ClassicLib/scanning/game/config.py` lines 191-208
- **Why Fragile**: Three sequential checks (hash equality, similarity ≥90%, ini comparison) with inconsistent thresholds:
  - Exact hash match: stored as duplicate
  - Similarity ≥0.90 + same size + same mtime: stored as duplicate
  - INI section comparison: stored as duplicate
- **Risk**: Similarity threshold (90%) is arbitrary; could produce false positives/negatives. Mtime equality unreliable on network shares.
- **Safe Modification**:
  1. Add configuration option for similarity threshold (currently hardcoded)
  2. Replace mtime check with content-based verification
  3. Add debug logging at each decision point
  4. Unit test each comparison method independently
- **Test Coverage**: No tests validate duplicate detection accuracy against known data sets

**Global _VERSION_WARNING_LOGGED Flag:**
- **Files**: `ClassicLib/support/game_path.py` lines 40, 53-58
- **Why Fragile**: Module-level mutable state to prevent repeated warnings:
  ```python
  _VERSION_WARNING_LOGGED = False

  def _log_version_warning():
      global _VERSION_WARNING_LOGGED
      if not _VERSION_WARNING_LOGGED:
          logger.warning(...)
          _VERSION_WARNING_LOGGED = True
  ```
- **Risk**: In tests with multiple game instances or version checks, flag doesn't reset between tests. Test isolation requires manual reset (`_VERSION_WARNING_LOGGED = False`).
- **Test Coverage**: Tests manually reset flag (`test_game_path_generation_unit.py` line 153). No automatic fixture cleanup.
- **Safe Modification**:
  1. Replace global flag with instance variable in GamePath class
  2. Or use `functools.lru_cache` with cache_clear() in test fixtures
  3. Add autouse fixture to reset in conftest

## Scaling Limits

**YAML Settings Loading Under High Memory Pressure:**
- **Current Approach**: `yaml_settings()` function imports YAML files eagerly in `__init__` of many classes.
- **Memory Profile**: Each YAML file loaded fully into memory (Main.yaml ≈ 2MB, game-specific databases ≈ 5MB each).
- **Limit**: With 20+ simultaneous game scans in thread pool, memory usage could exceed 200MB just for YAML caches.
- **Scaling Path**:
  1. Implement lazy YAML loading (load only on access)
  2. Use streaming YAML parser for large databases
  3. Cache in SQLite instead of in-memory dictionaries
  4. Monitor memory with `tracemalloc` during scans

**ThreadManager Pool Size:**
- **Current**: Default thread pool size set in `AccelerationCoordinator` (likely 4-8 threads).
- **Issue**: No dynamic scaling. Fixed pool can be bottleneck under load or waste resources when idle.
- **Limit**: Crashes with "too many open file handles" if pools exceed system limits (typically 1024 per process on Windows).
- **Scaling Path**:
  1. Use dynamic thread pool with min/max bounds
  2. Monitor queue depth; alert when backlog > 100
  3. Implement work stealing between thread pools
  4. Add telemetry: thread utilization % and queue depth

## Dependencies at Risk

**pefile (PE Header Parsing):**
- **Risk**: Constraint `pefile<2024.8.26` suggests breaking changes in newer versions. Older versions may have security issues.
- **Impact**: If newer pefile is required for Windows security updates, breaking changes will block deployment.
- **Files**: Used in `ClassicLib/support/xse.py` for XSE DLL hash validation
- **Migration Plan**:
  1. Profile actual pefile API usage in xse.py
  2. Test against newer pefile versions in isolated environment
  3. Either remove version constraint or update code to match new API
  4. Add integration tests for DLL signature validation

**regex (Enhanced Regex):**
- **Risk**: `regex>=2025.11.3` is pinned to very recent version. May introduce incompatibilities or CPU overhead.
- **Impact**: Used throughout codebase for pattern matching (error detection, log parsing). Slower regex = slower log scanning.
- **Files**: Imported in multiple modules; exact usage not catalogued
- **Mitigation**:
  1. Benchmark regex performance vs. `re` module on real crash logs
  2. Profile CPU usage of regex operations
  3. Consider reverting to `re` if regex overhead is significant and modern `re` features sufficient

**qasync (Qt Async Bridge):**
- **Risk**: `qasync>=0.28.0` integrates Tokio runtime with Qt event loop. Complex interaction point prone to deadlocks.
- **Impact**: Core GUI functionality depends on qasync. Deadlock = frozen UI.
- **Current Concerns**:
  - ONE RUNTIME RULE: Must use `classic_shared_core::get_runtime()`, not create new Tokio instances
  - Cross-thread context: Cannot use AsyncBridge in worker threads (documented in `04-development.md`)
- **Mitigation**:
  1. Add CI tests that exercise qasync under high load
  2. Monitor for deadlock patterns in stress tests
  3. Document exactly which Qt slots can call async code
  4. Consider replacing with native asyncio if qasync issues increase

## Security Considerations

**YAML Deserialization (ruamel.yaml):**
- **Risk**: Using `ruamel.yaml` with `yaml.unsafe_load()` anywhere could allow arbitrary code execution.
- **Files**: All YAML loading in `ClassicLib/io/yaml/` modules. Rust uses `yaml-rust2` (safe, no code execution).
- **Current Mitigation**: Project uses `classic_yaml` Rust module for YAML ops (pure data deserialization, no code eval).
- **Recommendation**: Audit all Python YAML loading to ensure no unsafe_load() calls exist. Enforce through type system.

**File Path Traversal (INI Config Files):**
- **Risk**: ConfigFileCache uses `Path.walk()` without validation. Malicious mod could create symlinks to parent directories.
- **Files**: `ClassicLib/scanning/game/config.py` line 175 (walk without validation)
- **Current Mitigation**: Game root path comes from registry/settings (trusted source). Still should validate.
- **Recommendation**:
  1. Use `Path.resolve()` with `strict=False` to canonicalize paths
  2. Check that resolved path is under game root
  3. Skip symlinks: `is_symlink()` check before processing

**No Input Validation on YAML Key Names:**
- **Risk**: Using untrusted keys from YAML to access settings could enable key injection attacks.
- **Files**: `ClassicLib/io/yaml/yaml_settings.py` - functions that accept game names or key paths
- **Current Mitigation**: Game name comes from registry (trusted). Key paths are hardcoded.
- **Recommendation**: If key paths ever become user-configurable, validate against whitelist before use.

## Missing Critical Features

**No Crash Recovery for Incomplete Scans:**
- **Problem**: If log scanning is interrupted (network timeout, out of memory), no state saved. User must re-scan from scratch.
- **Impact**: Large crash log repositories (10GB+) cannot be scanned reliably if network/resource constraints exist.
- **Solution Path**:
  1. Implement checkpoint system: save scan progress every N logs
  2. On resume, skip already-scanned files
  3. Add resume option to CLI: `classic-scan --resume path/to/incomplete.db`

**No Live Log Monitoring:**
- **Problem**: Users must manually re-run scans to detect new crashes. No watcher pattern.
- **Impact**: Cannot provide real-time crash notifications or prevent crashes that occur after initial scan.
- **Solution Path**:
  1. Add `FileSystemWatcher` for XSE log file changes
  2. Re-scan only new content when log grows
  3. Implement as optional background service

**No Cross-Platform INI Comparison:**
- **Problem**: INI file comparison uses Python's `configparser`, which has different behavior on Windows vs. Unix (line ending handling, case sensitivity).
- **Impact**: Duplicate detection may produce false negatives on Unix, false positives on Windows.
- **Solution Path**:
  1. Implement cross-platform INI normalization
  2. Test on Windows, macOS, Linux
  3. Use Rust INI parser (more deterministic) for comparison

## Test Coverage Gaps

**AsyncBridge Integration in GUI Workers:**
- **Untested Area**: How AsyncBridge behaves when multiple workers call it simultaneously. Race conditions not verified.
- **Files**: `ClassicLib/Interface/workers/` - ThreadManager and worker implementations
- **Risk**: Data corruption, deadlocks, or incorrect results under concurrent load.
- **Priority**: HIGH - Affects stability of parallel scanning
- **Approach**:
  1. Add concurrent stress test: 10 workers each calling `AsyncBridge.run_async()` 100 times
  2. Instrument with deadlock detection (timeout per call)
  3. Verify results are consistent and not race-dependent

**Duplicate File Detection Edge Cases:**
- **Untested Area**: Files with unusual properties (0-byte files, very large files, permission denied, on network share)
- **Files**: `ClassicLib/scanning/game/config.py` lines 189-208
- **Risk**: Exceptions during hash calculation could crash ConfigFileCache initialization.
- **Priority**: MEDIUM - Affects robustness in edge case scenarios
- **Approach**:
  1. Add test fixtures for edge cases
  2. Wrap hash calculation in try-except
  3. Return sentinel value or skip unhashable files

**INI Parsing Error Handling:**
- **Untested Area**: Corrupted or malformed INI files. What happens when `configparser` fails?
- **Files**: `ClassicLib/scanning/game/config.py` lines 51-55 (compare_ini_files) and line 178 (get_async in cache)
- **Risk**: Uncaught exceptions during INI parsing could fail entire scan.
- **Priority**: MEDIUM
- **Approach**:
  1. Add test cases with malformed INI content
  2. Implement graceful degradation (log warning, skip file)
  3. Test recovery when partial INI is readable

**Rust Integration Compatibility (Windows 10 vs 11):**
- **Untested Area**: PyO3 wheel binary compatibility across Windows versions
- **Files**: All `*-py` crates in `python-bindings/`
- **Risk**: Binary incompatibility could silently fail Rust fallback, causing performance regression.
- **Priority**: MEDIUM - Important for deployment
- **Approach**:
  1. Add CI test matrix for Windows 10 and Windows 11
  2. Verify all `-py` wheels load without error
  3. Benchmark Rust vs Python implementations

---

*Concerns audit: 2026-01-29*
