# Building and Bundling Rust Extensions Locally

## Overview

This guide explains how to build and bundle Rust extensions for CLASSIC without any CI/CD, pip installation, or GitHub Actions. Everything is done locally on your development machine.

**Key Constraints:**
- ❌ NO pip installation (package cannot be on PyPI)
- ❌ NO GitHub Actions (no budget)
- ❌ NO site-packages installation
- ✅ ONLY uvx from GitHub OR PyInstaller executables
- ✅ Everything built and committed locally

## Directory Structure

After building, your project will have this structure:

```
CLASSIC-Fallout4/
├── rust_extensions/              # Committed to git for uvx users
│   ├── classic_core._rust.pyd    # Compiled Rust extension (Windows)
│   ├── some_dependency.dll       # Any required DLLs
│   └── MANIFEST.txt              # Build manifest
├── classic-rust/
│   ├── src/                      # Rust source code
│   ├── python/
│   │   └── classic_core/
│   │       ├── __init__.py       # Multi-strategy loader
│   │       ├── adapters.py       # Python API adapters
│   │       └── _rust.pyd         # Extension copied here too
│   └── pyproject.toml            # Maturin configuration
├── ClassicLib/
│   ├── rust_loader.py            # Smart multi-path loader
│   └── rust_ext/
│       └── _rust.pyd              # Backward compatibility copy
├── dist/                          # PyInstaller output
│   └── CLASSIC/
│       ├── CLASSIC.exe
│       └── _internal/
│           └── rust_extensions/   # Bundled in executable
│               └── *.pyd
└── Cargo.toml                     # Root Rust configuration
```

## Step-by-Step Build Process

### Prerequisites

1. **Install Rust** (if not already installed):
   ```cmd
   :: Download from https://rustup.rs/
   :: Or use winget on Windows:
   winget install Rust.Rust
   ```

2. **Install maturin** (Rust-Python build tool):
   ```cmd
   uv tool install maturin
   ```

3. **Install uv** (Python package manager):
   ```cmd
   :: Download from https://github.com/astral-sh/uv
   :: Or use the installer:
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

### Building Rust Extensions

1. **Run the local build script**:
   ```cmd
   :: This builds the Rust extension and places it in multiple locations
   build_rust_local.bat
   ```

   What this does:
   - Builds the Rust code with `maturin build --release`
   - Extracts the `.pyd` file from the wheel
   - Copies to `rust_extensions/` (for committing to git)
   - Copies to `classic-rust/python/classic_core/` (for development)
   - Copies to `ClassicLib/rust_ext/` (for backward compatibility)

2. **Commit the built extensions to git**:
   ```cmd
   git add rust_extensions/
   git commit -m "Add compiled Rust extensions for uvx distribution"
   git push
   ```

   This ensures uvx users get the pre-built extensions without needing Rust.

### Building PyInstaller Executable

1. **Build the executable with bundled Rust**:
   ```cmd
   :: This creates the distributable executable
   build_pyinstaller.bat
   ```

   What this does:
   - Checks for Rust extensions in `rust_extensions/`
   - Runs PyInstaller with the modified CLASSIC.spec
   - Bundles extensions into `_internal/rust_extensions/`
   - Creates `dist/CLASSIC/CLASSIC.exe`

2. **Distribute the executable**:
   - The entire `dist/CLASSIC/` folder is your distribution
   - Users need NO Python, NO Rust, NO dependencies
   - Rust extensions are bundled inside

## How Each Distribution Method Works

### 1. PyInstaller Executable (End Users)

When users run `CLASSIC.exe`:
1. PyInstaller extracts to a temp `_MEIPASS` directory
2. `rust_loader.py` checks `sys.frozen` flag
3. Looks in `_MEIPASS/_internal/rust_extensions/`
4. Loads the bundled `.pyd` file
5. Falls back to Python if not found

### 2. uvx from GitHub (Power Users)

When users run via uvx:
```bash
uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic
```

1. uvx clones the repository
2. Sets up a virtual environment
3. `rust_loader.py` finds extensions in `rust_extensions/`
4. Loads the pre-built, committed `.pyd` file
5. No compilation needed!

### 3. Local Development (Developers)

When developing locally:
```bash
uv run python CLASSIC_Interface.py
```

1. `rust_loader.py` searches multiple paths
2. Finds extensions in any of:
   - `rust_extensions/` (committed version)
   - `classic-rust/python/classic_core/` (fresh build)
   - `ClassicLib/rust_ext/` (backward compatibility)
3. Uses the first one found

## Loading Priority

The `rust_loader.py` module searches in this order:

1. **PyInstaller bundle** (`_MEIPASS/_internal/rust_extensions/`)
2. **Committed extensions** (`rust_extensions/`)
3. **Development build** (`classic-rust/python/classic_core/`)
4. **Backward compatibility** (`ClassicLib/rust_ext/`)
5. **Current directory** (`./rust_extensions/`)
6. **Module-relative** (`ClassicLib/rust_ext/`)

## Verifying the Build

### Test if Rust is loading correctly:

```python
# Run this to check Rust loading
python test_rust_loading.py
```

Expected output:
```
Testing Rust Extension Loading...
=================================
Rust Available: True
Load Path: C:\...\rust_extensions\classic_core._rust.pyd
Search Paths Checked:
  - C:\...\rust_extensions
  - C:\...\classic-rust\python\classic_core
Module Functions: ['FileIOCore', 'FormIDAnalyzer', ...]
```

### Check in PyInstaller bundle:

```cmd
:: After building, check the bundle
dir dist\CLASSIC\_internal\rust_extensions\

:: Run the exe and check for Rust in console output
dist\CLASSIC\CLASSIC.exe
```

## Updating Rust Extensions

When you modify Rust code:

1. **Rebuild locally**:
   ```cmd
   build_rust_local.bat
   ```

2. **Test the changes**:
   ```cmd
   uv run python test_rust_loading.py
   uv run pytest tests/rust/
   ```

3. **Commit the new binaries**:
   ```cmd
   git add rust_extensions/
   git commit -m "Update Rust extensions: <describe changes>"
   ```

4. **Rebuild PyInstaller** (if distributing):
   ```cmd
   build_pyinstaller.bat
   ```

## Troubleshooting

### "Rust extension not found"

1. Check if `rust_extensions/` exists and contains `.pyd` files
2. Run `build_rust_local.bat` to build
3. Check Python version compatibility (requires 3.12+)

### "Module import error"

1. Verify the `.pyd` filename matches the expected pattern
2. Check for missing DLL dependencies with:
   ```cmd
   dumpbin /dependents rust_extensions\*.pyd
   ```

### PyInstaller not bundling extensions

1. Ensure `rust_extensions/` exists before running PyInstaller
2. Check CLASSIC.spec has the bundling code
3. Look for bundling messages in PyInstaller output

### uvx users getting Python fallback

1. Ensure `rust_extensions/` is committed to git
2. Check file permissions (should be readable)
3. Verify Python version matches (3.12+)

## Manual Testing Commands

```cmd
:: Test 1: Check if extensions exist
dir rust_extensions\*.pyd

:: Test 2: Test loading in Python
uv run python -c "from ClassicLib.rust_loader import get_rust_info; print(get_rust_info())"

:: Test 3: Test in application
uv run python CLASSIC_Interface.py

:: Test 4: Test PyInstaller bundle
dist\CLASSIC\CLASSIC.exe

:: Test 5: Simulate uvx (clone to temp dir and run)
git clone . %TEMP%\classic-test
cd %TEMP%\classic-test
uv run python CLASSIC_Interface.py
```

## Platform Notes

### Windows (Primary Platform)
- Extensions are `.pyd` files
- May require Visual C++ Redistributables
- UPX compression works well

### Linux (Future Support)
- Extensions will be `.so` files
- Modify build scripts to use `maturin build --manylinux`
- Test with different glibc versions

### macOS (Future Support)
- Extensions will be `.dylib` files
- May need code signing for distribution
- Universal binaries for Intel/ARM

## Benefits of This Approach

1. **No CI/CD Required**: Everything builds on your local machine
2. **No pip/PyPI**: Users never need to `pip install` anything
3. **Version Control**: Binary extensions are in git for uvx
4. **Multiple Fallbacks**: Works even if Rust fails to load
5. **Zero User Friction**: PyInstaller users get a single .exe
6. **Developer Friendly**: Multiple load paths for different scenarios

## Summary

This approach ensures CLASSIC works in all required scenarios without any cloud services, CI/CD, or package repositories. Users get either:
- A single executable with everything bundled (PyInstaller)
- Direct execution from GitHub with pre-built extensions (uvx)

Both methods require zero setup from users and no ongoing infrastructure costs.
