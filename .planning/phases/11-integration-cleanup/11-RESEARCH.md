# Phase 11: Integration & Cleanup - Research

**Researched:** 2026-02-03
**Domain:** Python-Rust Migration Cleanup, Factory Simplification, PyInstaller Build
**Confidence:** HIGH

## Summary

Phase 11 is cleanup work that finalizes the Python-to-Rust migration. The phase addresses four domains: (1) fixing parity differences identified in Phase 10 validation, (2) removing Python business logic files that now have Rust replacements, (3) simplifying the factory to return Rust directly without fallback branches, and (4) verifying PyInstaller build includes all Rust modules.

The codebase is already 90-100% migrated to Rust, with comprehensive wrapper modules in `ClassicLib/integration/rust/` that bridge Rust and Python APIs. The primary work involves removing obsolete Python fallback code, updating wrappers to require Rust (no fallback), and ensuring the PyInstaller build bundles all 18 Rust `.pyd` modules correctly.

**Primary recommendation:** Execute cleanup incrementally by component (parser, analyzers, validators, etc.) with validation after each removal to enable git bisect if issues arise.

## Standard Stack

The established tools for this domain:

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| PyInstaller | 6.x | Bundling Python + Rust extensions | Project already uses it via CLASSIC.spec |
| maturin | 1.x | Building PyO3 Rust extensions | Existing build pipeline in rebuild_rust.ps1 |
| pytest | 8.x+ | Verification of parity and functionality | Existing test infrastructure |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| git bisect | Finding regression source | After incremental component removal |
| unified_diff | Parity comparison | Golden file validation |

### What's Already In Place
| Component | Status | Notes |
|-----------|--------|-------|
| 18 Rust .pyd modules | Built in rust_extensions/ | All required modules present |
| pyinstaller_rust_helper.py | Functional | Auto-discovers .pyd files |
| CLASSIC.spec | Functional | Uses helper for hiddenimports |
| Golden file infrastructure | Complete | 20 report golden files captured |

## Architecture Patterns

### Pattern 1: Factory Simplification (Required)

**Current state:** Factory functions have try-import with fallback branches
```python
# BEFORE: Current pattern with fallback
def get_gpu_detector():
    if gpu_rust.RUST_AVAILABLE:
        return gpu_rust  # Rust path
    else:
        return py_gpu_detector  # Python fallback
```

**Target state:** Factory functions require Rust, raise on failure
```python
# AFTER: Simplified pattern - Rust required
def get_gpu_detector():
    import classic_scanlog
    return classic_scanlog.GpuDetector()  # RuntimeError if import fails
```

**When to use:** All factory functions returning components with Rust replacements.

### Pattern 2: Wrapper Module Simplification (Required)

**Current state:** Wrapper modules detect Rust availability and delegate
```python
# BEFORE: wrapper with fallback
RUST_AVAILABLE, RustClass = detect_component("classic_scanlog", "Class")
class Wrapper:
    def __init__(self):
        if RUST_AVAILABLE:
            self._impl = RustClass()
        else:
            self._impl = PythonClass()  # Fallback
```

**Target state:** Wrapper requires Rust, raises RuntimeError on failure
```python
# AFTER: wrapper requires Rust
class Wrapper:
    def __init__(self):
        from classic_scanlog import Class
        self._impl = Class()  # ImportError/RuntimeError if unavailable
```

**When to use:** All wrapper modules in `ClassicLib/integration/rust/`.

### Pattern 3: Incremental Removal Order (Recommended)

Remove components in dependency order to minimize breakage:

```
Phase 11 Removal Order (Claude's Discretion):
1. Analyzers (leaf nodes - no other Python code depends on them)
   - GPUDetector.py
   - PluginAnalyzer.py
   - RecordScanner.py
   - SettingsScanner.py
   - SuspectScanner.py
   - FormIDAnalyzerCore.py

2. Mid-level (used by orchestrator)
   - detect_mods.py
   - fcx_mode_handler.py
   - parser.py (if Python impl exists)

3. High-level (orchestration)
   - report_generator.py (Python impl)

4. Wrappers (after Python impls removed)
   - Remove fallback imports from wrappers
   - Remove RUST_AVAILABLE flags
```

### Anti-Patterns to Avoid

- **Big-bang deletion:** Deleting all Python files at once prevents git bisect from finding regression source
- **Leaving orphan tests:** Tests for deleted Python code will fail with import errors
- **Incomplete wrapper cleanup:** Leaving RUST_AVAILABLE checks in wrappers that always return True

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| .pyd module discovery | Manual hiddenimports list | pyinstaller_rust_helper.py | Auto-discovers all classic_*.pyd files |
| Report format parity | Manual diff comparison | Golden file infrastructure | generate_diff() with unified_diff |
| Component detection | Custom availability flags | detect_component() | Centralized in factory.py |

**Key insight:** The pyinstaller_rust_helper.py already handles .pyd bundling correctly. Updates to CLASSIC.spec hiddenimports are automatic via `rust_hidden_imports`.

## Common Pitfalls

### Pitfall 1: Import Order in Wrappers

**What goes wrong:** Removing Python fallback but leaving import at module level causes ImportError at load time even when Rust is available.

**Why it happens:** The fallback import is at module scope, not inside the `else` branch.

**How to avoid:** Check each wrapper for module-level imports of Python fallback classes before deletion.

**Warning signs:** Wrapper has `from ClassicLib.scanning... import` outside of `if not RUST_AVAILABLE` block.

### Pitfall 2: Test Import Errors After Deletion

**What goes wrong:** Tests importing deleted Python modules fail with ImportError, not test assertion failures.

**Why it happens:** Test files have direct imports of Python business logic being deleted.

**How to avoid:** Search for imports of each Python file before deletion:
```bash
grep -r "from ClassicLib.scanning.logs.analyzers.GPUDetector" tests/
```

**Warning signs:** Test file names matching deleted module names (e.g., `test_gpu_detector.py`).

### Pitfall 3: Circular Import After Factory Simplification

**What goes wrong:** Simplifying factory to direct imports creates circular import chains.

**Why it happens:** Factory imports Rust module, Rust module (via PyO3) imports Python types from ClassicLib.

**How to avoid:** Use lazy imports (inside function body) for Rust modules in factory functions.

**Warning signs:** ImportError mentioning "partially initialized module" or "circular import".

### Pitfall 4: Missing Settings Validation in Rust Output

**What goes wrong:** Parity test fails because Rust report lacks "Settings-related Issues" section.

**Why it happens:** The Rust ReportGenerator doesn't call SettingsValidator methods.

**How to avoid:** Verify Rust orchestrator includes settings validation in report generation pipeline.

**Warning signs:** Golden file diff shows entire "Checking for Settings-related Issues" section missing.

## Code Examples

### Example 1: Factory Function Simplification

```python
# Source: Existing factory.py pattern + required changes

# BEFORE (current)
def get_gpu_detector() -> GpuDetectorProtocol:
    from ClassicLib.integration.rust import gpu_rust
    if gpu_rust.RUST_AVAILABLE:
        logger.debug("Using Rust-accelerated GpuDetector")
    else:
        logger.debug("Using Python GPUDetector implementation")
    return gpu_rust

# AFTER (Phase 11)
def get_gpu_detector() -> GpuDetectorProtocol:
    """Get GPU detector module (Rust required)."""
    try:
        from ClassicLib.integration.rust import gpu_rust
        logger.debug("Using Rust-accelerated GpuDetector")
        return gpu_rust
    except ImportError as e:
        msg = f"Required Rust module for GPU detector not available: {e}"
        raise RuntimeError(msg) from e
```

### Example 2: Wrapper Module Cleanup

```python
# Source: Pattern from parser_rust.py (already Rust-required)

# AFTER (Phase 11 - all wrappers follow this pattern)
class RustAcceleratedSuspectScanner:
    def __init__(self, yamldata: ClassicScanLogsInfo) -> None:
        # Import Rust directly - no fallback
        from classic_scanlog import SuspectScanner

        suspects_error_list = getattr(yamldata, "suspects_error_list", {})
        suspects_stack_list = getattr(yamldata, "suspects_stack_list", {})

        self._scanner = SuspectScanner(suspects_error_list, suspects_stack_list)

    # Methods delegate to Rust, converting types as needed
```

### Example 3: PyInstaller hiddenimports Verification

```python
# Source: pyinstaller_rust_helper.py - no changes needed

# The existing helper already handles .pyd discovery:
def find_rust_extensions(project_root):
    """Find all classic_*.pyd files in rust_extensions/ or site-packages."""
    # Returns (binaries, datas, hidden_imports, found)
    # hidden_imports contains module names like ['classic_yaml', 'classic_scanlog', ...]
```

Current rust_extensions/ contains 18 modules:
- classic_config, classic_constants, classic_database
- classic_file_io, classic_message, classic_path
- classic_perf, classic_pybridge, classic_registry
- classic_resource, classic_scangame, classic_scanlog
- classic_settings, classic_shared, classic_update
- classic_version, classic_web, classic_xse, classic_yaml

### Example 4: Parity Fix - Version String Format

```python
# Source: Golden file inspection

# EXPECTED (Python output):
# **Detected Buffout 4 Version:** Buffout 4 v1.28.6

# RUST FIX: Ensure version string formatting matches exactly
# Check ReportGenerator/ReportComposer in Rust for version display
```

### Example 5: Parity Fix - Blank Line Normalization

```python
# Source: Parity test failure patterns

# EXPECTED: Single blank line between sections
# ---
#
# ### Next Section

# ACTUAL (Rust may produce): Double blank lines
# ---
#
#
# ### Next Section

# FIX: Audit Rust ReportComposer line joining logic
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hybrid Rust/Python with fallback | Rust-required, no fallback | Phase 11 | Simpler code, faster imports |
| RUST_AVAILABLE flags | Direct Rust imports | Phase 11 | Remove detection overhead |
| Python business logic | Rust in -core crates | Phases 6-9 | 10-150x performance |

**Deprecated/outdated after Phase 11:**
- `RUST_AVAILABLE` flags in wrapper modules
- Python fallback imports in wrappers
- Python analyzer classes in ClassicLib/scanning/logs/analyzers/
- Tests for Python implementations

## Open Questions

### 1. Settings Validation Section in Rust

**What we know:** Golden files show "Checking for Settings-related Issues" section is present in Python output. Parity failures indicate this section may be missing or different in Rust output.

**What's unclear:** Whether SettingsValidator is being called by Rust orchestrator, or if the output format differs.

**Recommendation:** Examine Rust ReportGenerator to verify SettingsValidator integration. Add integration test if missing.

### 2. Additional Suspects in Rust Output

**What we know:** Phase 10 identified that Rust finds additional suspects not found by Python.

**What's unclear:** Whether these are valid improvements (Rust catches more issues) or false positives.

**Recommendation:** Per CONTEXT.md, this is Claude's Discretion. Review specific differences in parity test output to determine if they're valid detections. If valid, update golden files; if not, adjust Rust detection logic.

### 3. Whitespace/Blank Line Differences

**What we know:** Parity tests fail due to extra blank lines in Rust output.

**What's unclear:** Exact locations and pattern of extra blank lines.

**Recommendation:** Run single parity test with verbose diff output to identify specific locations. Fix in Rust ReportComposer line joining logic.

## Sources

### Primary (HIGH confidence)
- Project codebase analysis: factory.py, wrapper modules, CLASSIC.spec, pyinstaller_rust_helper.py
- Git history: deletion patterns from phases 4, 5, 9
- rust_extensions/ directory: 18 .pyd modules present
- tests/golden/captured/: 20 golden report files

### Secondary (MEDIUM confidence)
- [PyInstaller hiddenimports documentation](https://pyinstaller.org/en/stable/hooks.html) - .pyd bundling patterns
- [PyInstaller with *.pyd files discussion](https://github.com/orgs/pyinstaller/discussions/7010) - Extension handling

### Tertiary (LOW confidence)
- None - all findings verified from codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all tools already in use
- Architecture: HIGH - patterns derived from existing code
- Pitfalls: HIGH - based on codebase analysis and git history

**Research date:** 2026-02-03
**Valid until:** 30 days (stable domain - cleanup work, not new features)

---

## Appendix: Files Identified for Removal

### Python Business Logic (Delete After Validation)

```
ClassicLib/scanning/logs/analyzers/
  - FormIDAnalyzerCore.py
  - GPUDetector.py
  - PluginAnalyzer.py
  - RecordScanner.py
  - SettingsScanner.py
  - SuspectScanner.py

ClassicLib/scanning/logs/
  - detect_mods.py (if Rust replacement exists)
  - fcx_mode_handler.py
  - parser.py (if Python impl exists beyond wrapper)
  - report_generator.py (Python impl)
```

### Tests to Delete (Obsolete After Python Removal)

```
tests/ (search for direct imports of deleted modules)
  - Tests importing ClassicLib.scanning.logs.analyzers.*
  - Tests importing deleted Python business logic
```

### Wrapper Modules to Simplify (Remove Fallback)

```
ClassicLib/integration/rust/
  - gpu_rust.py - remove Python fallback import
  - fcx_rust.py - remove Python fallback import
  - settings_rust.py - remove Python fallback import
  - suspect_rust.py - remove Python fallback import
```

### Factory Functions to Simplify

```
ClassicLib/integration/factory.py
  - get_suspect_scanner() - remove RUST_AVAILABLE check
  - get_settings_validator() - remove RUST_AVAILABLE check
  - get_gpu_detector() - remove RUST_AVAILABLE check
  - get_fcx_handler() - remove RUST_AVAILABLE check
  - get_database_pool() - remove Python fallback
  - get_yamldata() - remove Python fallback
```
