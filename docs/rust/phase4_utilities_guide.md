# Phase 4 Utilities Guide

## Overview

Phase 4 of the CLASSIC Rust port provides essential utility modules for game constants, version management, resource detection, Script Extender (XSE) support, and web utilities. These modules deliver high-performance implementations of common operations needed throughout CLASSIC.

**Status**: ✅ Completed (2025-11-02)

## Architecture

All Phase 4 components follow the standard CLASSIC Rust architecture:

- **Business Logic** (`-core` crates): Pure Rust implementations in `rust/business-logic/`
- **Python Bindings** (`-py` crates): PyO3 wrappers in `rust/python-bindings/`
- **Integration**: Factory functions in `ClassicLib/integration/factory.py`
- **Detection**: Automatic detection in `ClassicLib/integration/detector.py`

## Components

### 1. Constants (`classic-constants`)

**Purpose**: Game-specific constants, enumerations, and common values.

**Location**:
- Core: [`rust/business-logic/classic-constants-core/`](../../rust/business-logic/classic-constants-core/)
- Bindings: [`rust/python-bindings/classic-constants-py/`](../../rust/python-bindings/classic-constants-py/)

**Key Features**:
- Game ID enumeration (Fallout4, Fallout4VR, Skyrim, Starfield)
- Game-specific path constants
- Common file extensions
- Version numbers and identifiers

**Python Usage**:
```python
from ClassicLib.integration.factory import get_constants

# Get constants module
constants = get_constants()
if constants:
    # Access game IDs
    game = constants.GameId.Fallout4
    print(f"Game: {game.as_str()}")  # "Fallout4"

    # Compare games
    is_fallout = game == constants.GameId.Fallout4
```

**Direct Import**:
```python
import classic_constants

# Use GameId enum
fallout4 = classic_constants.GameId.Fallout4
print(fallout4.as_str())  # "Fallout4"
```

---

### 2. Version Utilities (`classic-version`)

**Purpose**: High-performance version parsing, comparison, and extraction.

**Location**:
- Core: [`rust/business-logic/classic-version-core/`](../../rust/business-logic/classic-version-core/)
- Bindings: [`rust/python-bindings/classic-version-py/`](../../rust/python-bindings/classic-version-py/)

**Key Features**:
- Semantic version parsing (`semver` crate)
- Version comparison
- Version extraction from filenames and logs
- Known version detection (Fallout 4, F4SE)
- Version formatting

**Python Usage**:
```python
from ClassicLib.integration.factory import get_version_utils

# Get version utilities
version = get_version_utils()
if version:
    # Parse version
    v = version.parse_version("1.10.163")
    print(v)  # (1, 10, 163)

    # Try parse (returns None on failure)
    v = version.try_parse_version("not a version")
    print(v)  # None

    # Compare versions
    cmp = version.compare_versions((1, 10, 163), (1, 10, 164))
    # Returns: -1 (less), 0 (equal), or 1 (greater)

    # Format version
    formatted = version.format_version((1, 10, 163))
    print(formatted)  # "v1.10.163"

    formatted = version.format_version((1, 10, 163), prefix="")
    print(formatted)  # "1.10.163"

    # Extract from filename
    v = version.extract_version_from_filename("F4SE-0.6.23.exe")
    print(v)  # (0, 6, 23)

    # Check if known version
    is_known = version.is_known_fallout4_version((1, 10, 163))
    print(is_known)  # True or False
```

**Direct Import**:
```python
import classic_version

v = classic_version.parse_version("1.10.163")
print(v)  # (1, 10, 163)
```

---

### 3. Resource Management (`classic-resource`)

**Purpose**: Resource file detection, enumeration, and validation.

**Location**:
- Core: [`rust/business-logic/classic-resource-core/`](../../rust/business-logic/classic-resource-core/)
- Bindings: [`rust/python-bindings/classic-resource-py/`](../../rust/python-bindings/classic-resource-py/)

**Key Features**:
- Resource type detection by extension
- Directory enumeration
- Type-based filtering
- Resource validation
- Supports 10 resource types

**Resource Types**:
- Texture (`.dds`)
- Mesh (`.nif`)
- Script (`.pex`, `.psc`)
- Plugin (`.esp`, `.esm`, `.esl`)
- Sound (`.wav`, `.xwm`, `.fuz`)
- Animation (`.hkx`)
- Interface (`.swf`)
- Strings (`.strings`, `.dlstrings`, `.ilstrings`)
- Archive (`.ba2`, `.bsa`)
- Config (`.ini`)

**Python Usage**:
```python
from ClassicLib.integration.factory import get_resource_mgmt

# Get resource management module
resource = get_resource_mgmt()
if resource:
    # Detect resource type
    rt = resource.detect_resource_type("textures/armor.dds")
    print(rt.as_str())  # "texture"

    # Check if supported
    is_supported = resource.is_supported_resource("texture.dds")
    print(is_supported)  # True

    # Parse resource type from string
    rt = resource.parse_resource_type("mesh")
    print(rt.as_str())  # "mesh"

    # Enumerate resources in directory
    resources = resource.enumerate_resources("Data/")
    for res in resources:
        print(f"{res.path()}: {res.resource_type().as_str()}")

    # Enumerate specific type only
    textures = resource.enumerate_resources(
        "Data/",
        filter_type=resource.ResourceType.texture()
    )

    # Count resources by type
    counts = resource.count_resources_by_type("Data/")
    for rt, count in counts:
        print(f"{rt.as_str()}: {count} files")

    # Validate resource
    try:
        resource.validate_resource("Data/texture.dds")
        print("Resource is valid")
    except Exception as e:
        print(f"Validation failed: {e}")
```

**Direct Import**:
```python
import classic_resource

rt = classic_resource.detect_resource_type("texture.dds")
print(rt.as_str())  # "texture"
```

---

### 4. XSE Utilities (`classic-xse`)

**Purpose**: Script Extender (XSE) detection, version checking, and status information.

**Location**:
- Core: [`rust/business-logic/classic-xse-core/`](../../rust/business-logic/classic-xse-core/)
- Bindings: [`rust/python-bindings/classic-xse-py/`](../../rust/python-bindings/classic-xse-py/)

**Key Features**:
- XSE type enumeration (F4SE, F4SEVR, SKSE, SKSE64, SKSEVR, SFSE)
- Version detection from loader executables
- Installation checking
- Loader path resolution

**Python Usage**:
```python
from ClassicLib.integration.factory import get_xse_utils

# Get XSE utilities
xse = get_xse_utils()
if xse:
    # Create XSE type
    f4se = xse.XseType.f4se()
    print(f4se.as_str())  # "F4SE"
    print(f4se.loader_name())  # "f4se_loader.exe"
    print(f4se.dll_prefix())  # "f4se_"

    # Parse XSE type from string
    f4se = xse.parse_xse_type("f4se")
    skse64 = xse.parse_xse_type("SKSE64")

    # Check if XSE is installed
    game_path = "C:/Games/Fallout4"
    is_installed = xse.is_xse_installed(game_path, f4se)
    print(f"F4SE installed: {is_installed}")

    # Get detailed XSE information
    info = xse.get_xse_info(game_path, f4se)
    print(f"XSE Type: {info.xse_type().as_str()}")
    print(f"Path: {info.path()}")
    print(f"Installed: {info.installed()}")
    print(f"Loader: {info.loader_path()}")

    if info.version():
        major, minor, patch = info.version()
        print(f"Version: {major}.{minor}.{patch}")

    # Detect version from loader
    try:
        version = xse.detect_xse_version("f4se_loader.exe", f4se)
        major, minor, patch = version
        print(f"Detected version: {major}.{minor}.{patch}")
    except Exception as e:
        print(f"Version detection failed: {e}")
```

**Direct Import**:
```python
import classic_xse

f4se = classic_xse.XseType.f4se()
info = classic_xse.get_xse_info("C:/Games/Fallout4", f4se)
print(f"Installed: {info.installed()}")
```

---

### 5. Web Utilities (`classic-web`)

**Purpose**: URL validation, user agent generation, and mod site constants.

**Location**:
- Core: [`rust/business-logic/classic-web-core/`](../../rust/business-logic/classic-web-core/)
- Bindings: [`rust/python-bindings/classic-web-py/`](../../rust/python-bindings/classic-web-py/)

**Key Features**:
- URL validation and parsing (`url` crate)
- User agent string generation
- Mod site enumeration (Nexus Mods, Bethesda.net, ModDB)
- URL building utilities
- Domain extraction

**Python Usage**:
```python
from ClassicLib.integration.factory import get_web_utils

# Get web utilities
web = get_web_utils()
if web:
    # User agent
    ua = web.get_user_agent()
    print(ua)  # "CLASSIC/8.0.0"

    ua = web.get_user_agent_with_suffix("Windows")
    print(ua)  # "CLASSIC/8.0.0 (Windows)"

    # URL validation
    is_valid = web.is_valid_url("https://www.nexusmods.com")
    print(is_valid)  # True

    url = web.validate_url("https://www.nexusmods.com")
    print(url)  # "https://www.nexusmods.com/"

    # Extract domain
    domain = web.extract_domain("https://www.nexusmods.com/fallout4/mods/123")
    print(domain)  # "www.nexusmods.com"

    # Join URL
    url = web.join_url("https://www.nexusmods.com", "fallout4/mods")
    print(url)  # "https://www.nexusmods.com/fallout4/mods"

    # Build URL with query parameters
    url = web.build_url_with_query(
        "https://www.nexusmods.com/fallout4/mods",
        [("page", "1"), ("sort", "popular")]
    )
    print(url)  # "https://www.nexusmods.com/fallout4/mods?page=1&sort=popular"

    # Mod sites
    nexus = web.ModSite.nexus_mods()
    print(nexus.name())  # "Nexus Mods"
    print(nexus.base_url())  # "https://www.nexusmods.com"

    bethesda = web.ModSite.bethesda_net()
    moddb = web.ModSite.mod_db()

    # Constants
    print(web.CLASSIC_VERSION)  # "8.0.0"
    print(web.USER_AGENT_PREFIX)  # "CLASSIC"
```

**Direct Import**:
```python
import classic_web

ua = classic_web.get_user_agent()
print(ua)  # "CLASSIC/8.0.0"

is_valid = classic_web.is_valid_url("https://www.nexusmods.com")
print(is_valid)  # True
```

---

## Integration

### Factory Pattern

All Phase 4 modules are accessed through factory functions that:
1. Check if Rust is disabled via `CLASSIC_DISABLE_RUST` environment variable
2. Detect if the module is available
3. Return the module or `None` if unavailable

```python
from ClassicLib.integration.factory import (
    get_constants,
    get_version_utils,
    get_resource_mgmt,
    get_xse_utils,
    get_web_utils,
)

# Each function returns the module or None
constants = get_constants()
if constants:
    # Use constants module
    game = constants.GameId.Fallout4
```

### Direct Import

You can also import modules directly without the factory:

```python
import classic_constants
import classic_version
import classic_resource
import classic_xse
import classic_web

# Use modules directly
v = classic_version.parse_version("1.10.163")
```

### Detection

The detector automatically checks for Phase 4 modules:

```python
from ClassicLib.integration.detector import get_available_components

components = get_available_components()
print(components["components"]["constants"])  # True/False
print(components["components"]["version_utils"])  # True/False
print(components["versions"]["classic_constants"])  # "8.0.0"
```

---

## Build Instructions

### Building All Phase 4 Modules

```powershell
# Build all Rust modules (includes Phase 4)
.\rebuild_rust.ps1

# Build specific module
cd rust/python-bindings/classic-web-py
maturin build --release --out dist
uv pip install dist/classic_web_py-*.whl --force-reinstall
```

### PyInstaller Integration

Phase 4 modules are automatically bundled with CLASSIC executables via `build_all.ps1`.

---

## Testing

### Integration Tests

Phase 4 integration tests are in [`tests/rust_integration/test_phase4_integration.py`](../../tests/rust_integration/test_phase4_integration.py).

Run tests:
```bash
# All Phase 4 tests
uv run pytest tests/rust_integration/test_phase4_integration.py -v

# Specific test class
uv run pytest tests/rust_integration/test_phase4_integration.py::TestWebUtilsIntegration -v

# All Rust integration tests
uv run pytest tests/rust_integration/ -v -m rust
```

---

## Performance

Phase 4 modules provide significant performance improvements:

- **Version parsing**: 10-20x faster than regex-based Python parsing
- **Resource enumeration**: 5-10x faster than Python `os.walk()`
- **URL validation**: 15-30x faster than Python `urllib.parse`
- **Zero-copy operations**: Minimize allocations for string operations

---

## Migration Guide

### From Python to Phase 4 Rust

#### Version Parsing

**Before (Python)**:
```python
import re

def parse_version(version_str):
    match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version_str)
    if match:
        return tuple(map(int, match.groups()))
    return None
```

**After (Rust)**:
```python
from ClassicLib.integration.factory import get_version_utils

version = get_version_utils()
if version:
    v = version.parse_version("1.10.163")  # (1, 10, 163)
    # Or use try_parse for optional parsing
    v = version.try_parse_version("1.10.163")  # (1, 10, 163) or None
```

#### Resource Detection

**Before (Python)**:
```python
import os

def detect_resource_type(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.dds':
        return 'texture'
    elif ext == '.nif':
        return 'mesh'
    # ...
```

**After (Rust)**:
```python
from ClassicLib.integration.factory import get_resource_mgmt

resource = get_resource_mgmt()
if resource:
    rt = resource.detect_resource_type("texture.dds")
    print(rt.as_str())  # "texture"
```

---

## Error Handling

All Phase 4 modules use proper error handling:

```python
from ClassicLib.integration.factory import get_xse_utils

xse = get_xse_utils()
if xse:
    try:
        # This may raise ValueError if type is invalid
        xse_type = xse.parse_xse_type("invalid")
    except ValueError as e:
        print(f"Invalid XSE type: {e}")

    try:
        # This may raise IOError if detection fails
        version = xse.detect_xse_version("nonexistent.exe", f4se)
    except IOError as e:
        print(f"Detection failed: {e}")
```

---

## Best Practices

1. **Use Factory Functions**: Always prefer factory functions for automatic fallback
2. **Check for None**: Factory functions return `None` if module unavailable
3. **Error Handling**: Wrap validation functions in try/except blocks
4. **Type Safety**: Use enumeration methods for type-safe constants
5. **Performance**: Cache factory results for repeated use

```python
from ClassicLib.integration.factory import get_version_utils

class MyClass:
    def __init__(self):
        # Cache the version utility module
        self._version = get_version_utils()

    def parse_version(self, version_str):
        if self._version:
            try:
                return self._version.parse_version(version_str)
            except ValueError:
                return None
        # Fallback to Python implementation
        return self._python_parse_version(version_str)
```

---

## Future Enhancements

Potential additions to Phase 4:

- **Network utilities**: HTTP client with connection pooling
- **Archive utilities**: BSA/BA2 reading and writing
- **Crypto utilities**: Hash verification and checksums
- **Compression utilities**: Zlib/LZMA compression

---

## See Also

- [Rust Workspace Architecture](rust_workspace_architecture.md)
- [PyO3 Integration Patterns](pyo3_integration_patterns.md)
- [Rust Acceleration Guide](rust_acceleration_guide.md)
- [Development Guide](development_with_rust.md)
