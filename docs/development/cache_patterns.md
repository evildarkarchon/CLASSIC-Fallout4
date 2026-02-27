# Cache Patterns in CLASSIC Rust Codebase

This document describes the different caching patterns used in the CLASSIC Rust codebase. Each pattern serves a specific use case, and this guide helps developers choose the appropriate pattern for new implementations.

## Overview

| Pattern | Crate | Key Type | Value Type | Invalidation | Use Case |
|---------|-------|----------|------------|--------------|----------|
| File Mod-Time Cache | `classic-yaml-core` | `PathBuf` | YAML + metadata | Automatic (file change) | Config files |
| String-Key Cache | `classic-settings-core` | `String` | `Arc<Vec<Yaml>>` | Manual | Loaded YAML settings |
| Dynamic Registry | `classic-registry-core` | `String` | `Arc<dyn Any>` | Manual | Application state |
| Path Hash Cache | `classic-file-io-core` | `PathBuf` | `String` | Manual | File integrity |
| Time Series Metrics | `classic-perf-core` | `String` | `Vec<f64>` | Manual | Performance data |
| Typed FormID Lookup Cache | `classic-database-core` | `CacheKey` | `CacheEntry` | TTL + capacity eviction | FormID DB lookups |

## Pattern Details

### 1. File Mod-Time Cache (YAML)

**Location**: `ClassicLib-rs/business-logic/classic-yaml-core/src/lib.rs`

**Purpose**: Cache parsed YAML files with automatic invalidation when the source file changes.

**Key Features**:
- Stores file modification timestamp alongside cached data
- Automatically reloads when file is newer than cache
- Preserves raw content for format-aware operations

**Data Structure**:
```rust
struct CachedYaml {
    data: Arc<Yaml>,
    modified: SystemTime,
    raw_content: Option<String>,
}

static CACHE: LazyLock<DashMap<PathBuf, CachedYaml>> = LazyLock::new(DashMap::new);
```

**When to Use**:
- Caching parsed file content (YAML, JSON, TOML, etc.)
- Files that may be modified externally
- When cache staleness detection is important

**Example Usage**:
```rust
// Check if file has changed since caching
if let Some(cached) = CACHE.get(&path) {
    let current_mtime = fs::metadata(&path)?.modified()?;
    if current_mtime <= cached.modified {
        return Ok(cached.data.clone()); // Cache hit
    }
    // File changed - reload needed
}
```

---

### 2. String-Key Cache (Settings)

**Location**: `ClassicLib-rs/business-logic/classic-settings-core/src/cache.rs`

**Purpose**: Cache loaded YAML settings with logical names for fast lookup.

**Key Features**:
- Uses string keys (logical names or file paths)
- Thread-safe with DashMap
- Supports batch loading operations
- Provides sync and async APIs

**Data Structure**:
```rust
static SETTINGS_CACHE: Lazy<DashMap<String, Arc<Vec<Yaml>>>> = Lazy::new(DashMap::new);
```

**When to Use**:
- Caching configuration data loaded at startup
- When files are identified by logical names (e.g., "game_config", "user_prefs")
- Batch loading multiple configuration files

**Example Usage**:
```rust
// Load and cache
load_settings_sync("game_config", Path::new("config.yaml"))?;

// Retrieve cached
if let Some(docs) = get_cached("game_config") {
    // Use cached YAML documents
}

// Check/invalidate
if is_cached("game_config") {
    invalidate("game_config");
}
```

---

### 3. Dynamic Registry

**Location**: `ClassicLib-rs/business-logic/classic-registry-core/src/registry.rs`

**Purpose**: Store application-wide state with dynamic typing.

**Key Features**:
- Stores any `Send + Sync + 'static` type
- Type-safe retrieval with `downcast_ref`
- Predefined keys for common values
- Convenience getters for typed access

**Data Structure**:
```rust
type RegistryValue = Arc<dyn Any + Send + Sync>;
static REGISTRY: Lazy<DashMap<String, RegistryValue>> = Lazy::new(DashMap::new);
```

**When to Use**:
- Global application state (current game, GUI mode, paths)
- Sharing data across modules without tight coupling
- When value types vary (strings, bools, paths, custom types)

**Example Usage**:
```rust
// Register values
register(Keys::GAME, "Fallout4".to_string());
register(Keys::IS_GUI_MODE, true);
register(Keys::LOCAL_DIR, PathBuf::from("/app/path"));

// Retrieve with type specification
let game: Option<String> = get(Keys::GAME);
let gui_mode: Option<bool> = get(Keys::IS_GUI_MODE);

// Use convenience functions
let game = get_game(); // Returns String with default
let is_gui = is_gui_mode(); // Returns bool
```

---

### 4. Path Hash Cache

**Location**: `ClassicLib-rs/business-logic/classic-file-io-core/src/hash.rs`

**Purpose**: Cache SHA256 file hashes to avoid redundant calculations.

**Key Features**:
- Path-based keys for direct file lookup
- Pre-allocated capacity for expected load
- Parallel batch hashing with Rayon
- Explicit cache management

**Data Structure**:
```rust
static HASH_CACHE: LazyLock<Arc<DashMap<PathBuf, String>>> =
    LazyLock::new(|| Arc::new(DashMap::with_capacity(256)));
```

**When to Use**:
- File integrity verification
- Detecting file changes via content hash
- When the same files are hashed multiple times

**Example Usage**:
```rust
// Single file (uses cache)
let hash = FileHasher::hash_file(Path::new("game.exe"))?;

// Batch parallel (all use cache)
let files = vec![Path::new("a.bin"), Path::new("b.bin")];
let hashes = FileHasher::hash_files_parallel(&files)?;

// Cache management
FileHasher::clear_cache();
let size = FileHasher::cache_size();
```

---

### 5. Time Series Metrics

**Location**: `ClassicLib-rs/business-logic/classic-perf-core/src/metrics.rs`

**Purpose**: Record and summarize performance timing data.

**Key Features**:
- Stores multiple samples per operation
- Computes summary statistics (count, total, avg, min, max)
- Thread-safe concurrent recording

**Data Structure**:
```rust
static METRICS: Lazy<DashMap<String, Vec<f64>>> = Lazy::new(DashMap::new);
```

**When to Use**:
- Performance profiling
- Tracking operation timing over time
- When statistical analysis is needed

**Example Usage**:
```rust
// Record timings
record_timing("database_query", 0.123);
record_timing("database_query", 0.145);
record_timing("file_load", 0.045);

// Get summary statistics
let summary = get_summary();
if let Some(stats) = summary.get("database_query") {
    println!("DB queries: {} calls, avg: {:.3}s", stats.count, stats.average);
}

// Reset for next profiling session
clear_metrics();
```

---

### 6. Typed FormID Lookup Cache

**Location**: `ClassicLib-rs/business-logic/classic-database-core/src/pool_sqlx.rs`

**Purpose**: Cache FormID database lookups with explicit key normalization semantics and lower allocation pressure on hot paths.

**Data Structure**:
```rust
struct CacheKey {
    hash: u64,
    game_table: String,
    formid: String,
    plugin: String, // normalized to lowercase
}

query_cache: DashMap<CacheKey, CacheEntry>
```

**Normalization Contract**:
- `plugin` is normalized once via `CacheKey::normalize_plugin()` (lowercase) and then reused.
- `game_table` and `formid` are not normalized; they remain exact-match components.
- Equivalent cache keys require matching `game_table`, `formid`, and normalized `plugin`.
- Distinct non-equivalent components remain separate cache entries, even with hash collisions.

**Performance Trade-offs**:
- **Benefit**: avoids repeated `format!("{table}:{formid}:{plugin}")` churn in single/batch lookups.
- **Benefit**: avoids repeated `to_lowercase()` work inside tight loops by sharing normalization helpers.
- **Benefit**: precomputed `hash` reduces repeated hashing overhead during map operations.
- **Cost**: key storage keeps owned `String` components for collision-safe equality checks.

**Example Usage**:
```rust
let normalized = CacheKey::normalize_plugin(plugin);
let key = CacheKey::from_normalized_plugin(game_table, formid, &normalized);

if let Some(entry) = query_cache.get(&key) {
    // cache hit
}
```

---

## Choosing the Right Pattern

### Decision Tree

1. **Is the data loaded from a file?**
   - Yes, and file may change externally → **File Mod-Time Cache**
   - Yes, loaded once at startup → **String-Key Cache**
   - No → Continue

2. **Is the data a computed result?**
   - Yes, file hash → **Path Hash Cache**
   - Yes, timing measurement → **Time Series Metrics**
   - No → Continue

3. **Is the data application state?**
   - Yes → **Dynamic Registry**

### Quick Reference

| Scenario | Pattern |
|----------|---------|
| Parse config file once, reload if changed | File Mod-Time Cache |
| Load multiple config files at startup | String-Key Cache |
| Store current game name | Dynamic Registry |
| Store GUI mode flag | Dynamic Registry |
| Cache file SHA256 hashes | Path Hash Cache |
| Track operation performance | Time Series Metrics |
---

## Implementation Guidelines

### Thread Safety

All cache patterns use `DashMap` for lock-free concurrent access. Key considerations:

```rust
// DashMap iteration is safe during concurrent modifications
for entry in CACHE.iter() {
    let key = entry.key();
    let value = entry.value();
    // Process...
}

// Entry API for conditional updates
CACHE.entry(key.to_string())
    .and_modify(|v| v.push(new_value))
    .or_insert_with(|| vec![new_value]);
```

### Memory Management

- Use `Arc<T>` for shared ownership of cached values
- Consider capacity hints for expected load:
  ```rust
  DashMap::with_capacity(256)
  ```
- Implement `clear_*()` functions for testing and memory management

### Lazy Initialization

Use `once_cell::sync::Lazy` or `std::sync::LazyLock` for static caches:

```rust
// once_cell (works on stable Rust)
static CACHE: Lazy<DashMap<K, V>> = Lazy::new(DashMap::new);

// std::sync::LazyLock (Rust 1.80+)
static CACHE: LazyLock<DashMap<K, V>> = LazyLock::new(DashMap::new);
```

### Testing

Always provide cache clearing for test isolation:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;

    #[test]
    #[serial] // Prevents concurrent test interference with global state
    fn test_cache_operation() {
        clear_cache(); // Start clean

        // Test code...

        clear_cache(); // Clean up
    }
}
```

---

## Why Not Consolidate?

These cache patterns serve different purposes and have different requirements:

1. **Different invalidation strategies**: Mod-time vs manual vs TTL
2. **Different value types**: Typed vs dynamic vs time series
3. **Different access patterns**: Single lookup vs batch vs iteration
4. **Domain-specific APIs**: Each pattern provides domain-appropriate methods

Forcing consolidation would either:
- Create an overly complex generic cache that's harder to use
- Lose type safety and domain-specific optimizations
- Require excessive configuration for simple use cases

Instead, each pattern is optimized for its specific use case while following consistent conventions (DashMap, thread safety, clear functions, test isolation).
