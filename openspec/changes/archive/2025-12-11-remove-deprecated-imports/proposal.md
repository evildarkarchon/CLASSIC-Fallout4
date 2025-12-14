# Change: Remove Deprecated Import Modules and Migrate Usages

## Why
The codebase contains several deprecated shim modules that re-export functionality from refactored module locations. These deprecated modules:
1. Emit DeprecationWarning on import, creating noise in logs and test output
2. Add maintenance burden by duplicating exports
3. Create confusion about which import paths are canonical
4. Violate the project rule "Deprecated APIs = ERRORS"

Per CLAUDE.md guidelines: "Tests are exempt from API stability - Always use current APIs, never deprecated ones."

## What Changes

### Deprecated Modules to Remove
- `ClassicLib/FileIOCore.py` → Use `ClassicLib.FileIO` instead
- `ClassicLib/AsyncUtil.py` → Use `ClassicLib.FileIO.Async` instead
- `ClassicLib/AsyncYamlSettingsCore.py` → Use `ClassicLib.YamlSettings.async_` instead
- `ClassicLib/AsyncYamlSettings/` (directory) → Use `ClassicLib.YamlSettings.async_` instead
- `ClassicLib/AsyncUtilities.py` → Use `ClassicLib.Utils.Async` instead
- `ClassicLib/AsyncUtilities_Enhanced.py` → Use `ClassicLib.Utils.Async` instead

### Deprecated Function to Remove
- `ClassicLib.rust_loader.get_rust_module()` → Use specific modules (e.g., `classic_scanlog`) instead

### Deprecated Enum Values (Tests Only)
- `MessageTarget.GUI_ONLY` → Use `MessageTarget.GUI` instead (tests only)
- `MessageTarget.CLI_ONLY` → Use `MessageTarget.CONSOLE` instead (tests only)

### Files Requiring Migration
1. `tests/mods/test_mod_detection_patterns.py` - Update AsyncYamlSettings import
2. `ClassicLib/FileGeneration.py` - Update AsyncYamlSettings imports (2 locations)
3. `tests/core/test_message_handler.py` - Update MessageTarget enum values (8 usages)

## Impact
- Affected specs: code-organization (internal refactoring)
- Affected code:
  - 3 production/test files need import updates
  - 6 deprecated module files will be deleted
  - 1 deprecated function will be removed
- **No external consumers**: This is internal library code; no public API changes
- **No breaking changes for production**: All usages are either in tests (exempt from API stability) or internal to ClassicLib