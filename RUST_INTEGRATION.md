# Rust Integration for CLASSIC-Fallout4

This document explains how Rust extensions are integrated into CLASSIC-Fallout4 for performance optimization while maintaining Python fallback compatibility.

## Overview

CLASSIC-Fallout4 uses a hybrid Python-Rust architecture where performance-critical operations are accelerated with Rust while maintaining pure Python fallbacks. This ensures the application works everywhere while providing optimal performance when Rust extensions are available.

### Key Features
- ✅ **NO pip installation required** - Extensions are bundled directly
- ✅ **NO GitHub Actions needed** - Everything builds locally
- ✅ **Works with uvx** - Extensions are committed to the repo
- ✅ **Works with PyInstaller** - Extensions are bundled in executables
- ✅ **Automatic fallback** - Pure Python if Rust unavailable

## Architecture

```
CLASSIC-Fallout4/
├── classic-rust/            # Rust source code
│   ├── src/                # Rust implementation
│   ├── python/            # Python wrapper
│   │   └── classic_core/  # Python package
│   └── pyproject.toml     # Maturin configuration
├── rust_extensions/        # Built extensions (committed to git!)
│   ├── classic_core._rust.pyd  # Windows extension
│   └── MANIFEST.txt       # Build information
├── ClassicLib/
│   ├── rust_loader.py     # Multi-path extension loader
│   ├── ResourceLoader.py  # Integrated resource/extension loading
│   └── rust_ext/         # Backward compatibility location
└── *.spec files           # PyInstaller specs with Rust bundling
```

## Building Rust Extensions

### Prerequisites
1. **Rust**: Install from https://rustup.rs/
2. **maturin**: Install with `pip install maturin` or `uv tool install maturin`
3. **uv** (recommended): Install from https://github.com/astral-sh/uv

### Build Process

#### Option 1: Quick Build (Recommended)
```batch
# Builds Rust extensions and places them in all required locations
build_rust_local.bat

# Or with PowerShell
.\build_rust_local.ps1
```

#### Option 2: Complete Build with Executables
```batch
# Builds Rust extensions first, then all PyInstaller executables
build_all.bat

# Or with PowerShell
.\build_all.ps1
```

#### Option 3: Manual Build
```batch
# Build the extension
maturin build --release --out dist-rust

# Extract the .pyd file
python -c "import zipfile; z=zipfile.ZipFile('dist-rust/*.whl'); z.extractall('rust_extensions')"

# The extension is now ready for use
```

## How It Works

### 1. Extension Loading (rust_loader.py)

The `RustExtensionLoader` class searches for extensions in multiple locations:

1. **PyInstaller _internal** - Highest priority for bundled executables
2. **rust_extensions/** - Committed extensions for uvx/development
3. **classic-rust/python/** - Development build location
4. **ClassicLib/rust_ext/** - Backward compatibility

```python
from ClassicLib.rust_loader import load_rust_extensions, is_rust_available

# Load extensions (happens automatically on import)
if load_rust_extensions():
    print("Rust extensions loaded!")
else:
    print("Using Python fallback")
```

### 2. Resource Integration (ResourceLoader.py)

The ResourceLoader provides high-level access to Rust extensions:

```python
from ClassicLib.ResourceLoader import ResourceLoader

# Load Rust extensions
rust_loaded = ResourceLoader.load_rust_extension()

# Get loading information
info = ResourceLoader.get_rust_extension_info()
print(f"Rust loaded: {info['loaded']}")
print(f"Extension path: {info['path']}")
```

### 3. Using Rust-Accelerated Components

When Rust is available, components automatically use accelerated implementations:

```python
# This automatically uses Rust if available, Python if not
from classic_core import FileIOCore, FormIDAnalyzer, LogParser

# Create instances - they'll be Rust-accelerated if available
io_core = FileIOCore()
analyzer = FormIDAnalyzer()
parser = LogParser()

# Use them normally - the API is identical
content = io_core.read_file("crash.log")
formids = analyzer.analyze(content)
```

### 4. PyInstaller Bundling

All spec files are configured to bundle Rust extensions:

```python
# From CLASSIC.spec (and all other specs)
rust_extensions_dir = PROJECT_ROOT / "rust_extensions"
if rust_extensions_dir.exists():
    for ext_file in rust_extensions_dir.glob("*.pyd"):
        binaries.append((str(ext_file), "_internal/rust_extensions"))
```

The extensions are placed in `_internal/rust_extensions/` within the executable.

## Deployment Scenarios

### 1. PyInstaller Executables (End Users)
```batch
# Build everything
build_all.bat

# Distribute dist/CLASSIC.exe
# Extensions are bundled inside
```

### 2. uvx from GitHub (Power Users)
```bash
# Extensions are committed to repo, so this just works:
uvx --from github:evildarkarchon/CLASSIC-Fallout4 classic
```

### 3. Local Development
```bash
# Clone and build
git clone https://github.com/evildarkarchon/CLASSIC-Fallout4.git
cd CLASSIC-Fallout4
build_rust_local.bat  # Or .ps1

# Run with uv
uv run python CLASSIC_Interface.py
```

## Testing

### Test Extension Loading
```python
# Run the example script
python example_rust_usage.py
```

### Test in Executable
```batch
# Build test executable
build_all.bat

# The test executable will verify Rust loading
dist\CLASSIC-Test.exe
```

## Troubleshooting

### Extension Not Found
- Run `build_rust_local.bat` to build extensions
- Check that `rust_extensions/` directory exists
- Verify `.pyd` files are present

### Import Errors
- Ensure Python version matches (3.12+)
- Check that all dependencies are installed
- Try rebuilding with `build_rust_local.bat -Clean`

### Performance Not Improved
- Verify Rust is actually loaded: check application logs
- Use `ResourceLoader.get_rust_extension_info()` to debug
- Ensure you're using components that have Rust implementations

## Components with Rust Acceleration

| Component | Python Location | Rust Implementation | Performance Gain |
|-----------|----------------|-------------------|------------------|
| FileIOCore | ClassicLib/FileIOCore.py | classic-rust/src/file_io/ | 5-10x |
| FormIDAnalyzer | ClassicLib/ScanLog/ | classic-rust/src/scanlog/ | 10-20x |
| LogParser | ClassicLib/ScanLog/ | classic-rust/src/scanlog/ | 15-30x |
| PatternMatcher | ClassicLib/Utils/ | classic-rust/src/utils/ | 20-50x |
| DatabasePool | ClassicLib/Database/ | classic-rust/src/database/ | 3-5x |

## Development Workflow

1. **Make Rust changes** in `classic-rust/src/`
2. **Build locally** with `build_rust_local.bat`
3. **Test** with `python example_rust_usage.py`
4. **Commit** the `rust_extensions/` directory
5. **Push** - uvx users get the update immediately
6. **Build executables** with `build_all.bat` for releases

## Best Practices

1. **Always maintain Python fallback** - Rust should be optional
2. **Keep APIs identical** - Python and Rust versions must match
3. **Commit built extensions** - Include `rust_extensions/` in git
4. **Document performance gains** - Help users understand benefits
5. **Test both paths** - Verify Python and Rust implementations

## FAQ

**Q: Why commit built extensions to git?**
A: This enables uvx to work without requiring users to build Rust code. The extensions are small (~2-5MB) and platform-specific branches can be used if needed.

**Q: What if Rust isn't available?**
A: The application falls back to pure Python implementations automatically. Performance is reduced but functionality is identical.

**Q: How do I disable Rust?**
A: Delete or rename the `rust_extensions/` directory. The application will use Python fallbacks.

**Q: Can I use pip install?**
A: No, this project is designed for uvx and PyInstaller distribution only. Use `uvx --from github:...` or download the executables.

**Q: How do I add a new Rust component?**
A:
1. Implement in `classic-rust/src/`
2. Expose via PyO3 in `lib.rs`
3. Create Python wrapper in `classic-rust/python/classic_core/`
4. Add fallback in ClassicLib
5. Update this documentation

## Conclusion

The Rust integration provides significant performance improvements while maintaining complete compatibility. The build system ensures easy distribution through both uvx and PyInstaller, with no complex deployment requirements.
