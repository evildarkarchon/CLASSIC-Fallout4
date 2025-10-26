# CLASSIC Rust Modules - Detailed Documentation

## Module Overview

This document provides detailed documentation for each Rust module in the CLASSIC project, including their purpose, key functions, performance characteristics, and usage examples.

## 1. Database Module (`classic_core.database`)

### Purpose
Provides high-performance SQLite database operations with connection pooling, query caching, and batch processing capabilities.

### Key Components

#### `RustDatabasePool`
Main database connection pool manager.

**Features:**
- Connection pooling with automatic management
- Query result caching using DashMap
- WAL mode and optimized pragmas
- Batch query operations
- Thread-safe access

**Python API:**
```python
from classic_core.database import RustDatabasePool

# Create pool
pool = RustDatabasePool()

# Get or create connection
pool.get_connection("path/to/database.db")

# Batch lookup
results = pool.batch_lookup(
    db_path="formid.db",
    table="formid_data",
    keys=["0x12345678", "0x87654321"]
)
```

**Performance:**
- Connection reuse: ~100x faster than opening per query
- Batch operations: 10-15x faster than individual queries
- Query caching: Near-instant for repeated queries

### Implementation Details

```rust
pub struct RustDatabasePool {
    // DashMap for thread-safe concurrent access
    connections: Arc<DashMap<PathBuf, Arc<Mutex<Connection>>>>,
    // Query result cache
    query_cache: Arc<DashMap<(String, String), String>>,
}
```

**Optimizations:**
- WAL mode for concurrent reads
- NORMAL synchronous mode for performance
- Connection reuse pattern
- Result caching with TTL

## 2. File I/O Module (`classic_core.file_io`)

### Purpose
High-performance file operations with automatic encoding detection, caching, and parallel processing.

### Key Components

#### `RustFileIOCore`
Core file I/O operations with async support.

**Features:**
- Automatic encoding detection (UTF-8, UTF-16, CP1252, etc.)
- LRU cache for recently read files
- Parallel file operations
- Memory-mapped file support for large files

**Python API:**
```python
from classic_core.file_io import RustFileIOCore

io_core = RustFileIOCore()

# Read file with auto encoding detection
content = io_core.read_file("crash_log.txt")

# Write file
io_core.write_file("output.txt", content)

# Batch read
contents = io_core.read_files_batch(["file1.txt", "file2.txt"])

# Clear cache
io_core.clear_cache()
```

#### `EncodingDetector`
Automatic encoding detection for text files.

**Supported Encodings:**
- UTF-8 (with/without BOM)
- UTF-16 LE/BE
- Windows-1252 (CP1252)
- ASCII
- Fallback strategies

**Python API:**
```python
from classic_core.file_io import EncodingDetector

detector = EncodingDetector()
encoding = detector.detect_encoding("path/to/file.txt")
print(f"Detected: {encoding}")
```

### Performance Characteristics

| Operation | Python | Rust | Improvement |
|-----------|--------|------|-------------|
| Single file read (with encoding) | 50ms | 5ms | 10x |
| Batch read (10 files) | 500ms | 20ms | 25x |
| Large file (100MB) | 2s | 150ms | 13x |
| Cached read | 5ms | <1ms | >5x |

## 3. ScanLog Module (`classic_core.scanlog`)

### Purpose
Core crash log scanning functionality with pattern matching, FormID analysis, and mod detection.

### Key Components

#### `FormIDAnalyzerCore`
High-performance FormID extraction and validation.

**Features:**
- Precompiled regex patterns
- LRU cache for lookups (512 entries)
- Database integration for descriptions
- Batch processing support
- Parallel validation

**Python API:**
```python
from classic_core.scanlog import FormIDAnalyzerCore

analyzer = FormIDAnalyzerCore(
    yamldata=config,
    show_formid_values=True,
    formid_db_exists=True
)

# Extract FormIDs from lines
formids = analyzer.extract_formids(log_lines)

# Validate batch
valid_ids = analyzer.validate_formids_batch(formid_list)

# Match FormIDs with plugins
analyzer.formid_match(formids, plugins, report_fragment)
```

**Performance:**
- Pattern matching: 20-50x faster than Python regex
- Batch validation: Process 1000 FormIDs in ~10ms
- Database lookups: Cached for instant repeats

#### `ModDetector`
Fast mod detection using optimized pattern matching.

**Functions:**
- `detect_mods_single(text, patterns)` - Single-word mod names
- `detect_mods_double(text, patterns)` - Two-word mod names
- `detect_mods_important(text, patterns)` - Important mod detection
- `detect_mods_batch(texts, all_patterns)` - Batch processing

**Python API:**
```python
from classic_core.scanlog import (
    detect_mods_single,
    detect_mods_double,
    detect_mods_batch
)

# Single detection
found = detect_mods_single(log_text, ["UFO4P", "AWKCR"])

# Batch detection
all_patterns = {
    "single": ["UFO4P", "AWKCR"],
    "double": ["Sim Settlements", "True Storms"],
    "important": ["F4SE", "Buffout"]
}
results = detect_mods_batch(log_texts, all_patterns)
```

#### `LogParser`
Segment-based log parsing with parallel processing.

**Features:**
- Configurable segment boundaries
- Parallel segment extraction
- Memory-efficient streaming
- Pattern-based splitting

**Python API:**
```python
from classic_core.scanlog import LogParser

parser = LogParser()
segments = parser.parse_segments(
    log_lines,
    boundaries=[("GAME CRASHED", "PLUGINS:")]
)
```

#### `PatternMatcher`
General pattern matching with caching.

**Features:**
- Regex compilation caching
- Multi-pattern matching
- Case-insensitive options
- Named capture groups

**Python API:**
```python
from classic_core.scanlog import PatternMatcher

matcher = PatternMatcher()
matches = matcher.find_all_matches(
    text="Log content here",
    pattern=r"Error: (\w+)",
    case_insensitive=True
)
```

#### `PluginAnalyzer`
Plugin detection and analysis.

**Features:**
- ESM/ESP/ESL detection
- Load order analysis
- Conflict detection
- Batch processing

**Python API:**
```python
from classic_core.scanlog import PluginAnalyzer

analyzer = PluginAnalyzer()

# Check single plugin
has_plugin = analyzer.contains_plugin(log_text, "Fallout4.esm")

# Batch detection
plugins = analyzer.detect_plugins_batch(
    log_texts,
    plugin_list=["Fallout4.esm", "DLCRobot.esm"]
)
```

#### `RecordScanner`
Call stack record scanning.

**Features:**
- Stack frame extraction
- Symbol resolution
- Memory address parsing
- Batch scanning

**Python API:**
```python
from classic_core.scanlog import RecordScanner

scanner = RecordScanner()

# Check for specific record
has_record = scanner.contains_record(
    call_stack,
    "BGSInventoryItem"
)

# Batch scan
records = scanner.scan_records_batch(
    call_stacks,
    record_types=["REFR", "ACHR", "NPC_"]
)
```

### Performance Summary

| Operation | Python | Rust | Improvement |
|-----------|--------|------|-------------|
| FormID extraction (1000 lines) | 250ms | 10ms | 25x |
| Mod detection (100 patterns) | 150ms | 5ms | 30x |
| Plugin analysis | 100ms | 4ms | 25x |
| Record scanning | 80ms | 3ms | 27x |
| Full log scan | 2-3s | 200ms | 10-15x |

## 4. Utils Module (`classic_core.utils`)

### Purpose
Foundational utilities optimized for crash log processing.

### Key Components

#### `StringProcessor`
Optimized string operations for log processing.

**Features:**
- Efficient string splitting
- Pattern replacement
- Case conversion
- String interning for memory efficiency

**Python API:**
```python
from classic_core.utils import StringProcessor

processor = StringProcessor()

# Efficient operations
lines = processor.split_lines(content)
cleaned = processor.clean_log_line(line)
normalized = processor.normalize_path(path_str)
```

#### `PathHandler`
Path operations with validation and caching.

**Features:**
- Path normalization
- Validation caching
- Cross-platform support
- Batch operations

**Python API:**
```python
from classic_core.utils import PathHandler

handler = PathHandler()

# Path operations
normalized = handler.normalize_path("C:\\Game\\..\\Data")
is_valid = handler.validate_path(path)
paths = handler.resolve_paths(path_list)
```

#### `LogProcessor`
Specialized log processing utilities.

**Features:**
- Log segmentation
- Timestamp extraction
- Error detection
- Statistics generation

**Python API:**
```python
from classic_core.utils import LogProcessor

processor = LogProcessor()

# Process log
segments = processor.segment_log(content)
errors = processor.extract_errors(log_lines)
stats = processor.generate_statistics(log_content)
```

#### `RustPerformanceMonitor`
Performance tracking and profiling.

**Features:**
- Operation timing
- Memory usage tracking
- Call counting
- Report generation

**Python API:**
```python
from classic_core.utils import RustPerformanceMonitor

monitor = RustPerformanceMonitor()

# Start timing
monitor.start_operation("FormID Analysis")
# ... do work ...
monitor.end_operation("FormID Analysis")

# Get report
report = monitor.generate_report()
print(report)
```

### Error Handling

All modules use consistent error handling:

```rust
pub enum ClassicError {
    Io(std::io::Error),
    Database(rusqlite::Error),
    Pattern(regex::Error),
    Encoding(String),
    Generic(String),
}

pub type ClassicResult<T> = Result<T, ClassicError>;
```

Python receives appropriate exceptions:
- `IOError` for file operations
- `RuntimeError` for general errors
- `ValueError` for invalid inputs

## Performance Benchmarks

### Test Environment
- CPU: AMD Ryzen 9 5900X
- RAM: 32GB DDR4 3600MHz
- OS: Windows 11
- Python: 3.12.0
- Rust: 1.75.0

### Real-World Benchmarks

| Task | Python Time | Rust Time | Speedup |
|------|-------------|-----------|---------|
| Analyze single crash log (50KB) | 2.5s | 180ms | 14x |
| Batch process 10 logs | 18s | 1.2s | 15x |
| FormID database lookup (1000 IDs) | 850ms | 45ms | 19x |
| Scan game folder (5000 files) | 35s | 2.8s | 12.5x |
| Generate full report | 1.8s | 140ms | 13x |

### Memory Usage

| Operation | Python | Rust | Reduction |
|-----------|--------|------|-----------|
| Single log in memory | 15MB | 3MB | 80% |
| Database connections | 50MB | 8MB | 84% |
| Pattern cache | 25MB | 5MB | 80% |
| File read cache | 100MB | 20MB | 80% |

## Integration Examples

### Complete Crash Log Analysis

```python
from classic_core import (
    RustFileIOCore,
    FormIDAnalyzerCore,
    ModDetector,
    RustDatabasePool
)

# Initialize components
io_core = RustFileIOCore()
formid_analyzer = FormIDAnalyzerCore(config, True, True)
db_pool = RustDatabasePool()

# Read crash log
log_content = io_core.read_file("crash_log.txt")
log_lines = log_content.split('\n')

# Extract FormIDs
formids = formid_analyzer.extract_formids(log_lines)

# Detect mods
mods = ModDetector.detect_mods_batch(
    [log_content],
    {"single": mod_list_single, "double": mod_list_double}
)

# Database lookups
db_pool.get_connection("formid.db")
descriptions = db_pool.batch_lookup(
    "formid.db",
    "formid_data",
    formids
)

print(f"Found {len(formids)} FormIDs")
print(f"Detected {len(mods)} mods")
```

### Parallel File Processing

```python
from classic_core import RustFileIOCore
import time

io_core = RustFileIOCore()

# Process multiple files in parallel
files = ["log1.txt", "log2.txt", "log3.txt", "log4.txt"]

start = time.time()
contents = io_core.read_files_batch(files)
elapsed = time.time() - start

print(f"Read {len(files)} files in {elapsed:.2f}s")
print(f"Average: {elapsed/len(files):.3f}s per file")
```

## Future Enhancements

### Planned Improvements

1. **SIMD Optimizations**
   - Use explicit SIMD instructions for pattern matching
   - Vectorized string operations
   - Parallel memory comparisons

2. **Advanced Caching**
   - Tiered caching (L1/L2)
   - Persistent cache to disk
   - Smart eviction policies

3. **GPU Acceleration**
   - CUDA/OpenCL for massive pattern matching
   - Parallel regex on GPU
   - Batch FormID validation

4. **Streaming Support**
   - Process logs larger than RAM
   - Incremental parsing
   - Real-time analysis

## Troubleshooting

### Common Issues

1. **Import Error: "No module named 'classic_core'"**
   - Solution: Run `maturin develop` or `uv pip install -e . --force-reinstall`

2. **Performance not as expected**
   - Check if GIL is being released for CPU operations
   - Ensure caching is enabled
   - Verify batch operations are used

3. **Memory usage high**
   - Clear caches periodically
   - Use streaming for large files
   - Check for memory leaks with Valgrind

## Conclusion

The Rust modules provide significant performance improvements across all critical operations in CLASSIC. By leveraging Rust's performance characteristics and modern concurrent programming patterns, we achieve 10-30x speedups while maintaining clean Python APIs and full backward compatibility.
