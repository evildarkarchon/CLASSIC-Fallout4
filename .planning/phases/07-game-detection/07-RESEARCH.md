# Phase 7: Game Detection - Research

**Researched:** 2026-02-02
**Domain:** Rust GamePathFinder Wire-up + XSE/ENB Validation
**Confidence:** HIGH

## Summary

This phase wires the existing Rust `GamePathFinder` (in `classic-path-core` / `classic-path-py`) to Python, making Rust the primary code path for all game path detection. The Rust implementation is already complete: multi-strategy detection (cache, registry, XSE log parsing), path validation, and error handling. The Python `game_path.py` (~700 lines) currently has fallback logic between Rust and Python - this becomes a thin wrapper (<100 lines) with no Python fallback.

XSE integrity checking exists in `classic-scangame-core` (`xse.rs`) with `XseChecker` for Address Library validation. ENB validation (checking `d3d11.dll`, `enbseries.ini`) is not yet implemented in Rust and will need to be added. Both validation types are gated by FCX Mode setting per CONTEXT.md decisions.

**Primary recommendation:** Remove Python fallback code from `game_path.py`, delegate all detection to Rust `GamePathFinder`, add ENB validation to Rust `classic-scangame-core`, and store validation results (`XSE_VALID`, `ENB_PRESENT`) in GlobalRegistry for other components.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| classic-path-core | 8.2.0 | Rust game path detection (registry, XSE log, validation) | Already exists, tested, multi-strategy |
| classic-path-py | 8.2.0 | PyO3 bindings for GamePathFinder, PathValidator | Already exists with full API |
| classic-scangame-core | 8.2.0 | XseChecker for Address Library validation | Already exists and tested |
| classic-settings-core | 8.2.0 | Rust YAML cache for settings loading | Phase 6 dependency |
| winreg | 0.55.0 | Windows registry access (Rust) | Standard Rust crate for registry |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GlobalRegistry | project | Store detection results | XSE_VALID, ENB_PRESENT flags |
| configparser | 3.1 | INI parsing (Rust) | ENB config validation (`enbseries.ini`) |
| sha2 | 0.10 | Hash comparison | Game exe version validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Rust registry query | Python winreg | Decision locked: Rust-only, no fallback |
| MessageHandler for errors | User-friendly translation | Decision locked: Technical errors shown directly |

**Installation:**
No new dependencies required - all libraries already in project.

## Architecture Patterns

### Recommended Project Structure
```
ClassicLib/support/
    game_path.py            # Thin wrapper (<100 lines) - delegates to Rust
    resources.py            # Cache path helpers - unchanged

rust/business-logic/
    classic-path-core/
        src/game_path.rs    # GamePathFinder (existing)
        src/platform/windows.rs  # Registry queries (existing)
    classic-scangame-core/
        src/xse.rs          # XseChecker (existing)
        src/integrity.rs    # GameIntegrityChecker (existing)
        src/enb.rs          # ENB validation (new)

rust/python-bindings/
    classic-path-py/
        src/lib.rs          # GamePathFinder Python bindings (existing)
    classic-scangame-py/
        src/lib.rs          # Add ENB validation bindings (new)
```

### Pattern 1: Thin Python Wrapper (No Fallback)
**What:** Python delegates directly to Rust with no Python fallback path
**When to use:** Per CONTEXT.md decision - Rust-only, hard fail
**Example:**
```python
# Source: CONTEXT.md decision - Rust-only, hard fail
from classic_path import GamePathFinder

class GamePathFinder:
    """Thin wrapper delegating game path detection to Rust."""

    def __init__(self) -> None:
        """Initialize finder using Rust GamePathFinder directly.

        Raises:
            RuntimeError: If Rust module import fails (no fallback).
        """
        self.exe_name = f"{GlobalRegistry.get_game()}{GlobalRegistry.get_vr()}.exe"
        # Rust constructor - no try/except, let it bubble up
        self._rust_finder = RustGamePathFinder(
            self.exe_name,
            None,  # xse_loader - optional
            GlobalRegistry.get_game(),
            bool(GlobalRegistry.get_vr()),
        )

    def find_game_path(self) -> None:
        """Find game path using Rust multi-strategy detection.

        Strategy order (handled by Rust):
        1. Cached path (if valid)
        2. Windows registry query
        3. XSE log parsing
        4. Returns NotFound error -> Python prompts user

        Raises:
            FileNotFoundError: Game not found by any method.
        """
        try:
            cached_path = self._get_cached_path()
            xse_log_path = self._get_xse_log_path()

            path_str = self._rust_finder.find_game_path(
                cached_path=cached_path,
                xse_log_path=xse_log_path
            )
            self._save_game_path(Path(path_str))

        except FileNotFoundError:
            # Prompt user for manual entry per CONTEXT.md
            game_path = self._get_path_from_user()
            # Validate with Rust before saving
            self._rust_finder.validate_game_path(str(game_path))
            self._save_game_path(game_path)
```

### Pattern 2: Async with run_in_executor
**What:** Async contexts wrap Rust calls with executor to prevent blocking
**When to use:** Per CONTEXT.md - async contexts use asyncio.run_in_executor()
**Example:**
```python
# Source: CONTEXT.md async decision
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="rust_path_")

async def find_game_path_async(self) -> None:
    """Async version using run_in_executor for Rust calls."""
    loop = asyncio.get_running_loop()

    # Run Rust detection in executor to not block event loop
    path_str = await loop.run_in_executor(
        _executor,
        lambda: self._rust_finder.find_game_path(
            cached_path=cached_path,
            xse_log_path=xse_log_path
        )
    )

    # Registry operations are sync-safe, run directly
    GlobalRegistry.register(GlobalRegistry.Keys.GAME_PATH, Path(path_str))
```

### Pattern 3: FCX Mode Gated Validation
**What:** XSE/ENB validation only runs when FCX Mode is enabled
**When to use:** Per CONTEXT.md - validation is separate from detection
**Example:**
```python
# Source: CONTEXT.md validation scope decision
def validate_game_installation(game_path: Path) -> None:
    """Run integrity checks only if FCX Mode is enabled."""
    from ClassicLib.io.yaml import yaml_settings

    fcx_mode = yaml_settings(bool, YAML.Settings, "FCX_Mode", False)

    if not fcx_mode:
        logger.debug("FCX Mode disabled, skipping installation validation")
        return

    # XSE validation
    xse_result = validate_xse(game_path)
    GlobalRegistry.register("XSE_VALID", xse_result.is_valid)

    # ENB validation
    enb_result = validate_enb(game_path)
    GlobalRegistry.register("ENB_PRESENT", enb_result.is_present)
```

### Pattern 4: Cache Auto-Invalidation
**What:** Invalid cached paths are cleared and detection retries
**When to use:** Per CONTEXT.md - self-healing cache
**Example:**
```python
# Source: CONTEXT.md error handling decision
def _get_cached_path_validated(self) -> str | None:
    """Get cached path, auto-invalidate if invalid."""
    cached = ResourceLoader.get_cached_game_path()

    if cached:
        try:
            self._rust_finder.validate_game_path(str(cached))
            return str(cached)
        except ValueError:
            # Invalid cache - clear and retry detection
            logger.warning(f"Cached path invalid, clearing: {cached}")
            ResourceLoader.clear_cached_path("GamePath")

    return None
```

### Anti-Patterns to Avoid
- **Python fallback:** Don't implement Python path detection as fallback - CONTEXT.md specifies Rust-only
- **Translating errors:** Don't convert Rust exceptions to user-friendly messages - show technical details
- **Validating during detection:** Keep detection and validation separate steps per CONTEXT.md
- **Blocking async with Rust:** Always use run_in_executor for Rust calls in async contexts

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Windows registry queries | Python winreg wrapper | classic_path.GamePathFinder | Rust handles all registry edge cases |
| XSE log parsing | Regex in Python | GamePathFinder.parse_xse_log() | Rust handles encoding, path extraction |
| Address Library validation | File existence checks | XseChecker from classic_scangame | Version detection, VR/non-VR logic |
| Path validation | os.path.exists() | PathValidator from classic_path | Required files check, permission validation |
| Async thread pool | asyncio.to_thread | ThreadPoolExecutor | Control over max workers, naming |

**Key insight:** The Rust implementations handle edge cases (registry errors, encoding, path normalization) that would require substantial Python code to replicate correctly.

## Common Pitfalls

### Pitfall 1: Registry Query Failures Treated as Errors
**What goes wrong:** GOG installs or non-Steam setups raise exceptions during registry lookup
**Why it happens:** Windows registry keys don't exist for GOG/manual installs
**How to avoid:** Per CONTEXT.md - log registry failures at DEBUG level, expected for GOG/non-Steam
**Warning signs:** Excessive warning logs for non-Steam users

### Pitfall 2: XSE Log Path Not Configured
**What goes wrong:** XSE log parsing fails because docs path not set up
**Why it happens:** Detection runs before docs path discovery
**How to avoid:** Per CONTEXT.md - log XSE failures at WARNING level to help users understand
**Warning signs:** "XSE log not found" errors on fresh installs

### Pitfall 3: Blocking Event Loop with Rust Calls
**What goes wrong:** GUI freezes during game detection
**Why it happens:** Rust calls are synchronous, blocking the Qt event loop
**How to avoid:** Per CONTEXT.md - use asyncio.run_in_executor() for async contexts
**Warning signs:** GUI unresponsive during path detection

### Pitfall 4: Cache Key Mismatch Between Python and Rust
**What goes wrong:** Rust cache stores path, Python looks up different key
**Why it happens:** Different path normalization (slashes, case)
**How to avoid:** Use consistent string normalization: `str(path.resolve())`
**Warning signs:** Repeated cache misses, settings loaded multiple times

### Pitfall 5: ENB Validation Without Game Path
**What goes wrong:** ENB check fails because game_path not yet in GlobalRegistry
**Why it happens:** Validation runs before detection completes
**How to avoid:** Detection stores path in GlobalRegistry first, validation is separate step
**Warning signs:** "Game path not found" during ENB validation

### Pitfall 6: Validation Running for Other Users' Logs
**What goes wrong:** CLASSIC validates local installation when analyzing uploaded crash logs
**Why it happens:** FCX Mode check not gated properly
**How to avoid:** Per CONTEXT.md - validation ONLY runs when FCX Mode enabled (checking own install)
**Warning signs:** Validation errors when analyzing logs without local game

## Code Examples

Verified patterns from official sources:

### Rust GamePathFinder API (from classic_path.pyi)
```python
# Source: j:\CLASSIC-Fallout4\rust\python-bindings\classic-path-py\src\lib.rs
from classic_path import GamePathFinder, PathValidator

# Create finder
finder = GamePathFinder(
    game_exe="Fallout4.exe",
    xse_loader="f4se_loader.exe",  # Optional
    game_name="Fallout4",
    is_vr=False
)

# Find game path (multi-strategy)
try:
    path = finder.find_game_path(
        cached_path="C:\\Games\\Fallout4",  # Optional
        xse_log_path="C:\\Users\\...\\F4SE\\f4se.log"  # Optional
    )
except FileNotFoundError:
    # Game not found by any method
    pass

# Validate a path manually
try:
    finder.validate_game_path("C:\\Games\\Fallout4")
except ValueError as e:
    print(f"Validation failed: {e}")

# Static method - parse XSE log
game_path = GamePathFinder.parse_xse_log("C:\\...\\f4se.log")
```

### Rust XseChecker API (from classic_scangame)
```python
# Source: j:\CLASSIC-Fallout4\rust\business-logic\classic-scangame-core\src\xse.rs
# Note: Python bindings needed for classic_scangame

# Rust struct - to be exposed via PyO3
class XseChecker:
    def __init__(self, plugins_path: str, is_vr_mode: bool, game_version: str):
        """Create checker for Address Library validation."""
        pass

    def check(self) -> str:
        """Returns: 'CorrectVersion', 'WrongVersion', 'NotFound', 'VersionNotDetected'"""
        pass

    def format_message(self, result: str) -> str:
        """Get user-friendly message for result."""
        pass

    def validate(self) -> str:
        """Combined check and format_message."""
        pass
```

### GlobalRegistry Keys for Validation Results
```python
# Source: Claude's Discretion per CONTEXT.md
# Recommended GlobalRegistry key names:

GlobalRegistry.Keys.XSE_VALID = "xse_validation_passed"
GlobalRegistry.Keys.ENB_PRESENT = "enb_binaries_present"
GlobalRegistry.Keys.XSE_VERSION = "xse_detected_version"
GlobalRegistry.Keys.GAME_VERSION_DETECTED = "game_exe_version"

# Usage in code:
GlobalRegistry.register(GlobalRegistry.Keys.XSE_VALID, True)
GlobalRegistry.register(GlobalRegistry.Keys.ENB_PRESENT, False)
```

### ENB Validation (New - Needs Implementation)
```rust
// Source: CONTEXT.md requirements - to be added to classic-scangame-core
pub struct EnbChecker {
    game_path: PathBuf,
}

impl EnbChecker {
    pub fn new(game_path: impl AsRef<Path>) -> Self;

    /// Check if ENB binaries exist
    pub fn check_binaries(&self) -> EnbResult {
        // d3d11.dll and d3dcompiler_46e.dll in game folder
    }

    /// Check if ENB config exists and is readable
    pub fn check_config(&self) -> EnbConfigResult {
        // enbseries.ini exists
    }

    /// Combined validation
    pub fn validate(&self) -> EnbValidationResult;
}

pub enum EnbResult {
    Present,      // Both DLLs found
    Partial,      // Only some DLLs found
    NotInstalled, // No ENB files
}
```

### Async Pattern with run_in_executor
```python
# Source: CONTEXT.md async decision + Python asyncio docs
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Module-level executor for Rust calls
_rust_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="rust_game_"
)

@classmethod
async def create_async(cls) -> "GamePathFinder":
    """Async factory method for async contexts."""
    from ClassicLib.io.yaml import yaml_settings_async

    instance = cls.__new__(cls)

    # YAML settings can use Rust async directly
    instance.xse_file = await yaml_settings_async(
        str, YAML.Game_Local, "Game_Info.Docs_File_XSE"
    )

    # Rust finder initialization is sync, use executor
    loop = asyncio.get_running_loop()
    instance._rust_finder = await loop.run_in_executor(
        _rust_executor,
        lambda: RustGamePathFinder(
            instance.exe_name, None,
            GlobalRegistry.get_game(),
            bool(GlobalRegistry.get_vr())
        )
    )

    return instance
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Python fallback if Rust fails | Rust-only, hard fail | This phase | Simpler code, surfaces issues |
| User-friendly error translation | Technical errors shown | This phase | Better debugging |
| Validation during detection | Separate detection/validation | This phase | FCX Mode gating works |
| Python cache validation | Rust validates cached paths | This phase | Consistent validation |

**Deprecated/outdated:**
- `_HAS_RUST_PATH` checks - No longer needed, Rust is required
- Python `winreg` imports in game_path.py - Rust handles registry
- `_parse_xse_log_for_path()` Python implementation - Replaced by Rust
- `_game_path_find_registry()` Python implementation - Replaced by Rust

## Open Questions

Things that couldn't be fully resolved:

1. **ENB Validation Rust Implementation**
   - What we know: Requires checking d3d11.dll, d3dcompiler_46e.dll, enbseries.ini
   - What's unclear: Should ENB be in classic-scangame-core or separate crate?
   - Recommendation: Add to classic-scangame-core alongside XseChecker for consistency

2. **XseChecker Python Bindings**
   - What we know: XseChecker exists in classic-scangame-core but may not be exposed via classic-scangame-py
   - What's unclear: Current PyO3 bindings coverage
   - Recommendation: Verify classic-scangame-py exports XseChecker, add if missing

3. **Game Version Detection for Validation**
   - What we know: XseChecker needs GameVersion enum (Null, Original, NextGen, AE, VR)
   - What's unclear: How Python passes detected version to Rust XseChecker
   - Recommendation: Use VersionRegistry integration already in xse.rs

## Sources

### Primary (HIGH confidence)
- `j:\CLASSIC-Fallout4\rust\business-logic\classic-path-core\src\game_path.rs` - Full GamePathFinder implementation
- `j:\CLASSIC-Fallout4\rust\python-bindings\classic-path-py\src\lib.rs` - Complete Python bindings
- `j:\CLASSIC-Fallout4\rust\business-logic\classic-scangame-core\src\xse.rs` - XseChecker implementation
- `j:\CLASSIC-Fallout4\rust\business-logic\classic-scangame-core\src\integrity.rs` - GameIntegrityChecker
- `j:\CLASSIC-Fallout4\ClassicLib\support\game_path.py` - Current Python implementation to simplify
- `j:\CLASSIC-Fallout4\.planning\phases\07-game-detection\07-CONTEXT.md` - User decisions

### Secondary (MEDIUM confidence)
- `j:\CLASSIC-Fallout4\rust\business-logic\classic-path-core\src\platform\windows.rs` - Registry query patterns
- `j:\CLASSIC-Fallout4\.planning\phases\06-foundation-settings\06-RESEARCH.md` - Settings cache patterns

### Tertiary (LOW confidence)
- ENB binary detection requirements - Based on community knowledge of ENB structure

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All core libraries already exist and are tested
- Architecture: HIGH - Patterns derived from existing Rust code and CONTEXT.md decisions
- Pitfalls: HIGH - Based on project memories and current code analysis

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - stable domain)
