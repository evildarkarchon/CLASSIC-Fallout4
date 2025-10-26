# PyInstaller Data Bundling Guide for CLASSIC-Fallout4

## Overview

This document describes how CLASSIC-Fallout4 handles data file bundling for PyInstaller executables, ensuring seamless operation in both development and production (frozen) environments.

## Key Components

### 1. ResourceLoader Module (`ClassicLib/ResourceLoader.py`)

The ResourceLoader module has been enhanced to detect and handle PyInstaller's frozen state:

- **`_check_frozen_state()`**: Detects if running as a PyInstaller executable and locates bundled data
- **`is_frozen()`**: Helper function to check execution context
- **Automatic fallback**: Falls back to development paths when not frozen

### 2. PyInstaller Spec Files

All spec files have been updated to properly bundle the `CLASSIC Data` directory:

#### CLASSIC.spec (GUI Application)
- Bundles full PySide6 dependencies
- Includes all CLASSIC Data files
- Creates a folder-based distribution for better performance
- Optimized with UPX compression (excludes Qt and Python modules)

#### CLASSIC-CLI.spec (Command-Line Interface)
- Excludes GUI frameworks for smaller size
- Bundles all data files
- Creates a single-file executable for convenience
- Optimized for command-line usage

#### CLASSIC-TUI.spec (Terminal UI)
- Includes Textual framework dependencies
- Excludes GUI frameworks
- Creates a single-file executable
- Optimized for terminal interfaces

#### CLASSIC-Test.spec (Debug Build)
- No optimization for easier debugging
- Console enabled for debug output
- No UPX compression
- Includes all dependencies for testing

## Data Resolution Strategy

The ResourceLoader uses a hierarchical strategy to find data files:

1. **Frozen State Check** (Highest Priority)
   - Checks `sys._MEIPASS` for PyInstaller bundle
   - Used when running as `.exe` file

2. **Local Directory**
   - Checks GlobalRegistry LOCAL_DIR setting
   - Useful for custom installations

3. **Package Installation**
   - Checks pip/setuptools installation paths
   - Supports both `classic-fallout4` and `classic_fallout4` naming

4. **Source Installation**
   - Checks relative to module location
   - Used during development

5. **Current Working Directory**
   - Checks `./CLASSIC Data`
   - Fallback for portable installations

6. **User App Data** (Last Resort)
   - Creates in `%APPDATA%/CLASSIC-Fallout4/CLASSIC Data`
   - Ensures application can always run

## Building Executables

### Prerequisites

1. Install PyInstaller:
   ```bash
   poetry install  # Includes pyinstaller in dev dependencies
   # or
   pip install pyinstaller
   ```

2. Ensure UPX is available (optional, for compression):
   - Download UPX from https://upx.github.io/
   - Add to PATH or specify in build command

### Build Commands

```bash
# GUI Application (folder distribution)
poetry run pyinstaller --clean CLASSIC.spec

# CLI Application (single file)
poetry run pyinstaller --clean CLASSIC-CLI.spec

# TUI Application (single file)
poetry run pyinstaller --clean CLASSIC-TUI.spec

# Debug/Test Build
poetry run pyinstaller --clean CLASSIC-Test.spec

# With UPX compression (if not in PATH)
poetry run pyinstaller --clean --upx-dir "C:\Path\To\UPX" CLASSIC.spec
```

### Output Locations

- **GUI**: `dist/CLASSIC/` (folder with CLASSIC.exe and dependencies)
- **CLI**: `dist/CLASSIC-CLI.exe` (single executable)
- **TUI**: `dist/CLASSIC-TUI.exe` (single executable)
- **Test**: `dist/CLASSIC-Test.exe` (single executable with debug info)

## Testing Resource Loading

A test script is provided to verify resource loading in both modes:

```bash
# Test in development mode
python test_resource_loading.py

# Test frozen executable (after building)
dist/CLASSIC-Test.exe
```

The test script verifies:
- Execution mode detection
- Data directory resolution
- Essential file accessibility
- Cached path functions

## Important Notes

### Data File Extraction

When running as a frozen executable:
- PyInstaller extracts data files to a temporary directory
- Location accessible via `sys._MEIPASS`
- Files are automatically cleaned up on exit
- No manual cleanup required

### Performance Considerations

1. **Folder vs Single-File**:
   - GUI uses folder distribution for faster startup
   - CLI/TUI use single-file for portability
   - Single-file has slower initial startup (extraction time)

2. **UPX Compression**:
   - Reduces file size significantly
   - May trigger false positives in some antivirus software
   - Slightly slower startup time
   - Excluded for Python modules and Qt libraries to prevent issues

### Cross-Platform Compatibility

While primarily designed for Windows, the resource loading system uses `pathlib.Path` for cross-platform compatibility. Future Linux/macOS support would require:
- Updating spec files for platform-specific binaries
- Testing data directory resolution on each platform
- Adjusting icon paths for non-Windows platforms

## Troubleshooting

### Common Issues

1. **"CLASSIC Data not found" error**:
   - Ensure CLASSIC Data directory exists in project root
   - Check spec file is using correct PROJECT_ROOT path
   - Verify PyInstaller bundled the data (check build output)

2. **Missing dependencies**:
   - Add to `hiddenimports` in spec file
   - Use `collect_all()` for complex packages
   - Check PyInstaller warnings during build

3. **Antivirus false positives**:
   - Disable UPX compression (`upx=False`)
   - Sign the executable with a code certificate
   - Add to antivirus whitelist

4. **Slow startup**:
   - Use folder distribution instead of single-file
   - Disable UPX compression for faster extraction
   - Exclude unnecessary packages in spec file

## Migration from Previous Versions

If upgrading from a version without proper data bundling:

1. **Update ResourceLoader imports**:
   ```python
   from ClassicLib.ResourceLoader import get_resource_path
   # Use for all data file access
   data_file = get_resource_path("databases/CLASSIC Main.yaml")
   ```

2. **Replace hardcoded paths**:
   ```python
   # Old
   data_dir = Path("CLASSIC Data")

   # New
   from ClassicLib.ResourceLoader import ResourceLoader
   data_dir = ResourceLoader.get_data_directory()
   ```

3. **Check frozen state when needed**:
   ```python
   from ClassicLib.ResourceLoader import is_frozen

   if is_frozen():
       # Production behavior
   else:
       # Development behavior
   ```

## Conclusion

The enhanced data bundling system ensures CLASSIC-Fallout4 works seamlessly whether:
- Running from source code during development
- Installed via pip/poetry as a package
- Distributed as a PyInstaller executable
- Executed via uvx for temporary usage

This provides maximum flexibility for both developers and end-users while maintaining a consistent experience across all deployment methods.
