# CLASSIC Core - Rust Extensions

High-performance Rust extensions for CLASSIC Fallout 4 crash log analyzer.

## Overview

This package provides optimized Rust implementations of performance-critical components:
- **File I/O**: 10-20x faster file operations with encoding detection
- **FormID Analysis**: 20-50x faster FormID parsing and validation
- **Pattern Matching**: 15-30x faster log parsing using Aho-Corasick algorithm
- **Database Operations**: 5-15x faster SQLite queries with connection pooling
- **String Processing**: Parallel string operations with interning

## Prerequisites

- Python 3.12 or later
- Rust 1.75 or later
- Visual Studio 2022 Build Tools (Windows)

## Installation

### From Source

1. Install Rust from https://rustup.rs/

2. Install maturin:
```bash
uv pip install maturin
```

3. Build and install:
```bash
cd classic-rust
maturin develop --release
```

### For Development

```bash
# Install in editable mode with debug symbols
maturin develop

# Run tests
cargo test
pytest python/tests/
```

## Usage

The Rust extensions provide drop-in replacements for Python components:

```python
from classic_core import FileIOCore, FormIDAnalyzer, RUST_AVAILABLE

if RUST_AVAILABLE:
    print("Using Rust-accelerated components!")

# Use exactly like Python versions
file_io = FileIOCore()
content = file_io.read_file_sync(Path("crash.log"))

analyzer = FormIDAnalyzer()
formid = analyzer.parse_formid("0x12345678")
```

## Integration with CLASSIC

To integrate with the main CLASSIC application:

1. **Automatic Detection**: The application automatically uses Rust extensions when available:

```python
# In ClassicLib/FileIOCore.py
try:
    from classic_core import FileIOCore as RustFileIOCore
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

def get_file_io_core():
    if RUST_AVAILABLE and not os.environ.get("CLASSIC_DISABLE_RUST"):
        return RustFileIOCore()
    return PythonFileIOCore()
```

2. **Disable Rust Extensions**: Set environment variable to force Python implementation:
```bash
export CLASSIC_DISABLE_RUST=1
```

## Building for Distribution

### Windows Wheels

```bash
# Build wheel for current Python version
maturin build --release

# Build wheels for multiple Python versions
maturin build --release --abi3 --target x86_64-pc-windows-msvc
```

### Including in PyInstaller

Add to your `.spec` file:

```python
# CLASSIC.spec
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('classic_core')

a = Analysis(
    ['CLASSIC_Interface.py'],
    binaries=binaries,
    # ... rest of config
)
```

## Performance Benchmarks

Run benchmarks to verify performance improvements:

```bash
# Rust benchmarks
cargo bench

# Python comparison benchmarks
python benchmarks/benchmark_suite.py
```

Expected improvements:
- FormID Analysis: 25x faster
- Log Parsing: 25x faster
- File I/O: 10x faster
- Database Lookups: 10x faster

## Development

### Project Structure

```
classic-rust/
├── Cargo.toml           # Rust dependencies
├── pyproject.toml       # Python build config
├── src/
│   ├── lib.rs          # Module entry point
│   ├── file_io/        # File operations
│   ├── scanlog/        # Log parsing
│   ├── database/       # SQLite operations
│   └── utils/          # String utilities
├── python/
│   └── classic_core/   # Python adapters
└── tests/              # Test suites
```

### Adding New Modules

1. Create Rust implementation in `src/`
2. Add PyO3 bindings with `#[pyclass]` and `#[pymethods]`
3. Register in `lib.rs`
4. Create Python adapter in `python/classic_core/adapters.py`
5. Add tests in both `tests/` (Rust) and `python/tests/` (Python)

### Testing

```bash
# Run all tests
cargo test --all-features
pytest python/tests/ -v

# Test specific module
cargo test file_io
pytest python/tests/test_file_io.py -v

# Test with coverage
cargo tarpaulin --out Html
pytest --cov=classic_core --cov-report=html
```

## Troubleshooting

### Import Error: "No module named 'classic_core._rust'"

The Rust extension hasn't been built. Run:
```bash
maturin develop --release
```

### Performance Not Improved

1. Verify Rust extensions are loaded:
```python
from classic_core import RUST_AVAILABLE
print(f"Rust available: {RUST_AVAILABLE}")
```

2. Check for GIL contention - ensure CPU-intensive operations release GIL
3. Profile with `py-spy` to identify bottlenecks

### Build Errors on Windows

Ensure Visual Studio Build Tools are installed:
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

## License

MIT License - See parent project LICENSE file

## Contributing

1. Follow Rust best practices and idioms
2. Maintain Python API compatibility
3. Add tests for all new functionality
4. Run `cargo clippy` and `cargo fmt` before commits
5. Update benchmarks for performance changes
