# CLASSIC-Fallout4 uvx Deployment Guide

## Executive Summary

This document outlines the comprehensive steps required to prepare CLASSIC-Fallout4 for deployment via uvx, enabling users to run the application directly from your GitHub repository without permanent installation. uvx (part of the uv ecosystem) allows users to execute Python applications in isolated environments with a single command, making CLASSIC more accessible to a broader user base.

## Current State Analysis

### Project Structure
- **Framework**: Poetry-based Python 3.12+ application
- **Package Mode**: Currently set to `false` (application mode, not a distributable package)
- **Entry Points**: Three separate scripts for different interfaces
  - `CLASSIC_Interface.py` - PySide6 GUI application
  - `CLASSIC_TUI.py` - Textual-based Terminal UI
  - `CLASSIC_ScanLogs.py` - Command-line interface
- **Dependencies**: Complex dependency structure with optional groups (GUI, CLI, Windows-specific)
- **Build System**: PyInstaller for Windows executables

### Key Challenges for uvx Compatibility
1. Non-package mode in Poetry configuration
2. No defined console script entry points
3. Optional dependency groups that need handling
4. Platform-specific dependencies (Windows)
5. Data files and configuration that need to be packaged

## Required Changes

### 1. Project Configuration (pyproject.toml)

#### Enable Package Mode
```toml
[tool.poetry]
name = "classic-fallout4"
version = "7.35.0"
description = "Crash Log Auto-Scanner for Buffout 4"
authors = ["Poet", "evildarkarchon", "wxMichael"]
readme = "README.md"
package-mode = true  # Changed from false
packages = [
    { include = "ClassicLib" },
    { include = "CLASSIC_Interface.py" },
    { include = "CLASSIC_TUI.py" },
    { include = "CLASSIC_ScanLogs.py" },
    { include = "CLASSIC_ScanGame.py" }
]
```

#### Define Console Script Entry Points
```toml
[tool.poetry.scripts]
classic = "classic_fallout4.gui:main"        # Primary GUI entry point
classic-gui = "classic_fallout4.gui:main"    # Explicit GUI alias
classic-cli = "classic_fallout4.cli:main"    # Command-line interface
classic-tui = "classic_fallout4.tui:main"    # Terminal UI
classic-scan = "classic_fallout4.scan:main"  # Direct scanner access

# Alternative: Using project.scripts for PEP 621 compatibility
[project.scripts]
classic = "classic_fallout4.gui:main"        # Primary GUI entry point
classic-gui = "classic_fallout4.gui:main"    # Explicit GUI alias
classic-cli = "classic_fallout4.cli:main"    # Command-line interface
classic-tui = "classic_fallout4.tui:main"
```

### 2. Create Package Structure

Transform the current script-based structure into a proper Python package:

```
classic-fallout4/
├── src/
│   └── classic_fallout4/
│       ├── __init__.py
│       ├── cli.py          # Refactored from CLASSIC_ScanLogs.py
│       ├── gui.py          # Refactored from CLASSIC_Interface.py
│       ├── tui.py          # Refactored from CLASSIC_TUI.py
│       └── scan.py         # Refactored from CLASSIC_ScanGame.py
├── ClassicLib/             # Keep as is, already properly structured
├── CLASSIC Data/           # Include as package data
├── pyproject.toml
└── README.md
```

### 3. Entry Point Wrappers

Create minimal wrapper modules for clean entry points:

#### src/classic_fallout4/cli.py
```python
"""Command-line interface entry point for CLASSIC."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from CLASSIC_ScanLogs import main as scan_main


def main():
    """CLI entry point for uvx compatibility."""
    scan_main()


if __name__ == "__main__":
    main()
```

#### src/classic_fallout4/gui.py
```python
"""GUI entry point for CLASSIC."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """GUI entry point for uvx compatibility."""
    from PySide6.QtWidgets import QApplication
    from ClassicLib import GlobalRegistry
    from ClassicLib.SetupCoordinator import SetupCoordinator
    from CLASSIC_Interface import MainWindow

    app = QApplication(sys.argv)
    coordinator = SetupCoordinator()
    coordinator.initialize_application(is_gui=True)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        from ClassicLib.MessageHandler import msg_error
        msg_error(f"Error running GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### src/classic_fallout4/tui.py
```python
"""TUI entry point for CLASSIC."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from CLASSIC_TUI import main as tui_main


def main():
    """TUI entry point for uvx compatibility."""
    tui_main()


if __name__ == "__main__":
    main()
```

### 4. Handle Optional Dependencies

Create dependency extras for optional components:

```toml
[tool.poetry.dependencies]
python = ">=3.12,<3.14"
# Core dependencies (always installed)
beautifulsoup4 = ">=4.12.3"
requests = ">=2.32.3"
ruamel-yaml = ">=0.18.6"
tomlkit = ">=0.13.2"
urllib3 = ">=2.2.3"
chardet = ">=5.2.0"
aiohttp = ">=3.10.10"
regex = ">=2024.9.11"
iniparse = ">=0.5"
typed-argument-parser = ">=1.10.1"
packaging = ">=25.0"
aiofiles = ">=24.1.0"
aiosqlite = ">=0.21.0"
pefile = "<2024.8.26"
pyside6 = ">=6.8.0"  # GUI is primary, include by default

# Optional dependencies
textual = { version = ">=5.3.0", optional = true }
tqdm = { version = ">=4.67.1", optional = true }
pywin32 = { version = ">=310", optional = true, markers = "sys_platform == 'win32'" }

[tool.poetry.extras]
tui = ["textual"]
cli = ["tqdm"]
windows = ["pywin32"]
minimal = []  # Minimal installation without optional features
all = ["textual", "tqdm", "pywin32"]
```

### 5. Include Package Data

Ensure configuration and data files are included:

```toml
[tool.poetry]
include = [
    "CLASSIC Data/**/*.yaml",
    "CLASSIC Data/**/*.yml",
    "CLASSIC Data/**/*.db",
    "CLASSIC Data/**/*.txt",
    "CLASSIC Data/**/*.md",
    "docs/*.md",
    "LICENSE",
]

# Alternative: Using setuptools configuration
[tool.setuptools.package-data]
classic_fallout4 = [
    "data/*.yaml",
    "data/*.yml",
    "data/*.db",
]
```

### 6. Create __init__.py Files

Ensure proper package initialization:

#### src/classic_fallout4/__init__.py
```python
"""CLASSIC-Fallout4: Crash Log Auto-Scanner for Buffout 4."""

__version__ = "7.35.0"
__author__ = "Poet, evildarkarchon, wxMichael"

from pathlib import Path

# Set up data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "CLASSIC Data"

# Ensure data directory exists in package context
if not DATA_DIR.exists():
    # Try relative to package installation
    import pkg_resources
    try:
        DATA_DIR = Path(pkg_resources.resource_filename("classic_fallout4", "data"))
    except Exception:
        # Fallback to current directory
        DATA_DIR = Path.cwd() / "CLASSIC Data"
```

## uvx Usage Examples

Once the changes are implemented and pushed to GitHub, users can run CLASSIC directly:

### Basic Usage
```bash
# Run the GUI version (default)
uvx --from github:yourusername/CLASSIC-Fallout4 classic          # Launches GUI

# Run with specific interface
uvx --from github:yourusername/CLASSIC-Fallout4 classic-gui     # Explicit GUI
uvx --from github:yourusername/CLASSIC-Fallout4 classic-cli     # CLI version
uvx --from github:yourusername/CLASSIC-Fallout4 classic-tui     # TUI version
uvx --from github:yourusername/CLASSIC-Fallout4 classic-scan    # Direct scanner
```

### With Optional Dependencies
```bash
# Install with GUI support (already included by default)
uvx --from github:yourusername/CLASSIC-Fallout4 classic

# Install CLI-only version (without GUI dependencies)
uvx --from github:yourusername/CLASSIC-Fallout4[cli] classic-cli

# Install with all features
uvx --from github:yourusername/CLASSIC-Fallout4[all] classic-gui

# Install specific version/branch
uvx --from github:yourusername/CLASSIC-Fallout4@v7.35.0 classic
uvx --from github:yourusername/CLASSIC-Fallout4@main classic
```

### Advanced Usage
```bash
# Run with custom Python version
uvx --python 3.12 --from github:yourusername/CLASSIC-Fallout4 classic

# Persistent installation for frequent use
uvx install --from github:yourusername/CLASSIC-Fallout4 classic-fallout4
classic  # Now available as command

# Run with arguments (CLI mode for automation)
uvx --from github:yourusername/CLASSIC-Fallout4 classic-cli scan "Crash Logs/crash1.log"
```

## Implementation Strategy

### Phase 1: Minimal Changes for Basic uvx Support
1. Create entry point wrapper scripts in `src/classic_fallout4/`
2. Update pyproject.toml with:
   - `package-mode = true`
   - Console script entry points
   - Package includes
3. Test with local uvx: `uvx --from . classic`

### Phase 2: Optimize Package Structure
1. Refactor main scripts into the package structure
2. Handle data file packaging properly
3. Implement proper dependency extras
4. Test all entry points

### Phase 3: GitHub Release
1. Tag a release version
2. Update README with uvx instructions
3. Test from GitHub directly
4. Create GitHub Action for automated testing

## Testing uvx Compatibility

### Local Testing
```bash
# Build the package locally
poetry build

# Test with uvx from local directory
uvx --from . classic-cli --help
uvx --from . classic
uvx --from . classic-tui

# Test with specific extras
uvx --from .[gui] classic-gui
uvx --from .[tui] classic-tui
```

### GitHub Testing
```bash
# After pushing to GitHub
uvx --from github:yourusername/CLASSIC-Fallout4@branch-name classic --help

# Test different interfaces
uvx --from github:yourusername/CLASSIC-Fallout4@branch-name classic-gui
uvx --from github:yourusername/CLASSIC-Fallout4@branch-name classic-tui
```

## Backward Compatibility Considerations

### Maintaining Existing Usage Patterns
1. Keep original script files for direct Python execution
2. Entry point wrappers simply import and call existing code
3. No breaking changes to ClassicLib structure
4. PyInstaller builds continue to work as before

### Migration Path for Users
```markdown
# In README.md

## Installation Options

### Option 1: Quick Run with uvx (Recommended)
```bash
# Launches the GUI application directly
uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic

# For command-line automation
uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic-cli scan "path/to/log"
```

### Option 2: Traditional Installation
```bash
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4
cd CLASSIC-Fallout4
poetry install
poetry run python CLASSIC_Interface.py
```

### Option 3: Windows Executable
Download the latest release from the Releases page.
```

## Common Issues and Solutions

### Issue 1: Missing Dependencies
**Problem**: Optional TUI/CLI dependencies not installed
**Solution**: Use extras syntax: `uvx --from github:user/repo[tui,cli] classic-tui`

### Issue 2: Data Files Not Found
**Problem**: CLASSIC Data directory not accessible
**Solution**: Use pkg_resources or importlib.resources to locate package data

### Issue 3: Platform-Specific Dependencies
**Problem**: Windows-specific features not available on other platforms
**Solution**: Use environment markers in dependencies and conditional imports

### Issue 4: GUI Not Launching
**Problem**: PySide6 requires display server
**Solution**: Document display requirements, fallback to TUI/CLI

## Performance Considerations

### Startup Time
- uvx creates isolated environment on first run (cached afterward)
- Initial startup: 10-30 seconds (GUI includes PySide6)
- Subsequent runs: 2-5 seconds
- GUI is the default but CLI is available for automation needs

### Dependency Resolution
- Core dependencies with GUI: ~150MB (PySide6 included by default)
- Additional with TUI: ~160MB
- Full installation with all features: ~200MB

**Note on PySide6 Requirement**: After evaluation, PySide6 is kept as a required dependency rather than optional. This decision was made because:
1. The GUI is the primary interface for CLASSIC
2. The codebase already has proper fallback handling via `qt_compat.py` for non-GUI operations
3. Using extras would add complexity for users (`uvx install --with classic-fallout4[gui]` vs just `uvx install classic-fallout4`)
4. Most users expect the GUI to work out of the box
5. CLI and TUI users still get a working application even with PySide6 installed but unused

## Security Considerations

### Package Integrity
1. Sign commits and tags with GPG
2. Use GitHub's verified badges
3. Document checksums in releases
4. Enable Dependabot for security updates

### Runtime Security
1. Validate input paths
2. Sanitize user-provided data
3. Use proper file permissions
4. Avoid shell command injection

## Maintenance and Updates

### Version Management
```toml
# Use dynamic versioning
[tool.poetry-dynamic-versioning]
enable = true
vcs = "git"
style = "semver"
```

### Automated Testing
```yaml
# .github/workflows/uvx-test.yml
name: Test uvx Compatibility

on: [push, pull_request]

jobs:
  test-uvx:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - uses: astral/setup-uv@v4

      - name: Test GUI (default)
        run: uvx --from . classic --version

      - name: Test CLI
        run: uvx --from . classic-cli --version

      - name: Test TUI
        run: uvx --from . classic-tui --help

      - name: Test GUI with display (Linux)
        if: matrix.os == 'ubuntu-latest'
        run: |
          sudo apt-get install -y xvfb
          xvfb-run uvx --from . classic --version
```

## Next Steps

1. **Immediate Actions**:
   - Create `src/classic_fallout4/` directory structure
   - Write entry point wrapper scripts
   - Update pyproject.toml configuration
   - Test locally with uvx

2. **Short-term Goals**:
   - Refine dependency groups
   - Improve data file handling
   - Add comprehensive uvx tests
   - Update documentation

3. **Long-term Vision**:
   - Publish to PyPI for even easier access
   - Create Docker images for containerized deployment
   - Develop web-based interface for browser access
   - Implement automatic update mechanisms

## Conclusion

Preparing CLASSIC-Fallout4 for uvx deployment requires transforming it from a Poetry application into a proper Python package with defined entry points. While this requires some structural changes, the benefits include:

- **Easier Installation**: Users can run CLASSIC with a single command
- **Better Isolation**: Each run uses a clean environment
- **Cross-Platform Support**: Works on any system with Python
- **Version Management**: Users can easily run specific versions
- **Reduced Friction**: No need for git, poetry, or manual setup

The implementation can be done incrementally, starting with minimal wrapper scripts and gradually improving the package structure while maintaining full backward compatibility. Since CLASSIC is primarily a GUI application, the default `classic` command will launch the GUI interface, with CLI and TUI available as explicit alternatives for users who need them.
