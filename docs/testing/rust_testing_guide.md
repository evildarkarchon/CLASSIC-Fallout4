# Rust Testing Guide

## Overview

This guide covers testing patterns, fixtures, and coverage requirements for CLASSIC's Rust crates. The Rust components follow a three-layer architecture with pure business logic (`-core` crates), Python bindings (`-py` crates), and applications.

## Rust Test Structure

```
ClassicLib-rs/
├── foundation/
│   └── classic-shared-core/
│       └── tests/                    # Foundation layer tests
│           ├── test_rolling_stats.rs
│           └── test_path_lru.rs
│
├── business-logic/
│   ├── classic-yaml-core/
│   │   └── tests/
│   │       └── integration_tests.rs  # YAML operations tests
│   ├── classic-database-core/
│   │   └── tests/
│   │       └── integration_tests.rs  # Database pool tests
│   ├── classic-config-core/
│   │   └── tests/
│   │       └── integration_tests.rs  # Configuration loading tests
│   └── ... (other -core crates)
│
├── python-bindings/
│   └── classic-*-py/                 # Tested via Python integration
│
└── ui-applications/
    ├── classic-cli/
    │   └── tests/
    │       ├── integration_tests.rs
    │       └── memory_tests.rs
    └── classic-tui/
        └── tests/
            ├── widget_integration_tests.rs
            ├── memory_tests.rs
            └── dirty_tracking_tests.rs
```

## Running Rust Tests

### Run All Rust Tests

```bash
# From workspace root
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml

# Run with output
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml -- --nocapture
```

### Run Tests for Specific Crate

```bash
# Run classic-yaml-core tests
cargo test -p classic-yaml-core --manifest-path ClassicLib-rs/Cargo.toml

# Run classic-database-core tests (requires async runtime)
cargo test -p classic-database-core --manifest-path ClassicLib-rs/Cargo.toml

# Run classic-config-core tests
cargo test -p classic-config-core --manifest-path ClassicLib-rs/Cargo.toml
```

### Run Integration Tests Only

```bash
# Run all integration tests
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml --test integration_tests

# Run specific crate integration tests
cargo test -p classic-yaml-core --test integration_tests --manifest-path ClassicLib-rs/Cargo.toml
```

## Test Patterns

### 1. Use `tempfile` for File System Tests

Always use temporary files/directories for tests that interact with the filesystem.

```rust
use tempfile::{tempdir, NamedTempFile};
use std::fs;

#[test]
fn test_file_operation() {
    let temp_dir = tempdir().expect("Failed to create temp dir");
    let file_path = temp_dir.path().join("test.yaml");
    
    fs::write(&file_path, "key: value").expect("Failed to write");
    
    // Test operations...
    
    // temp_dir is automatically cleaned up when dropped
}
```

### 2. Use `serial_test` for Global State

When tests modify global state (caches, metrics), use `#[serial]` to prevent interference.

```rust
use serial_test::serial;

#[test]
#[serial]
fn test_global_cache() {
    // Clear global state before test
    clear_global_yaml_cache();
    
    // Test operations...
}
```

### 3. Use `#[tokio::test]` for Async Tests

For async operations (database, file I/O), use the tokio test runtime.

```rust
#[tokio::test]
async fn test_async_database_operation() {
    let pool = DatabasePool::new(Some(4), Duration::from_secs(60), "TestTable".to_string());
    pool.initialize(vec![db_path]).await.expect("Init should succeed");
    
    let result = pool.get_entry("12345678", "Plugin.esp", None).await;
    assert!(result.is_ok());
    
    pool.close().await.expect("Close should succeed");
}
```

### 4. Test Module Organization

Organize tests into logical modules within the test file.

```rust
//! Integration tests for my-crate

mod file_workflows {
    use super::*;
    
    #[test]
    fn test_complete_workflow() { /* ... */ }
}

mod cache_workflows {
    use super::*;
    
    #[test]
    fn test_cache_hit_miss() { /* ... */ }
}

mod error_handling {
    use super::*;
    
    #[test]
    fn test_file_not_found() { /* ... */ }
}
```

### 5. Concurrent Access Testing

Test thread-safety with multiple threads/tasks.

```rust
use std::sync::Arc;
use std::thread;

#[test]
fn test_concurrent_access() {
    let shared_resource = Arc::new(MyResource::new());
    
    let handles: Vec<_> = (0..4).map(|_| {
        let resource = shared_resource.clone();
        thread::spawn(move || {
            for _ in 0..100 {
                resource.operation();
            }
        })
    }).collect();
    
    for handle in handles {
        handle.join().expect("Thread should complete");
    }
}
```

## Coverage Requirements

### Overall Target

- **Business logic crates (`-core`)**: 60%+ line coverage
- **Foundation crates**: 80%+ line coverage
- **Python binding crates (`-py`)**: Excluded (tested via Python)

### Per-Crate Requirements

| Crate | Current | Target | Priority |
|-------|---------|--------|----------|
| classic-database-core | 11% | 60% | CRITICAL |
| classic-file-io-core/core.rs | 15% | 70% | CRITICAL |
| classic-config-core/yamldata.rs | 0% | 70% | HIGH |
| classic-scanlog-core (5 modules) | 0% | 60% | HIGH |
| classic-yaml-core | 57% | 75% | MEDIUM |
| classic-file-io-core/encoding.rs | 53% | 80% | MEDIUM |

### Well-Covered Crates (No Action Needed)

| Crate | Line Coverage |
|-------|---------------|
| classic-message-core | 100% |
| classic-perf-core | 98-100% |
| classic-pybridge-core | 100% |
| classic-settings-core | 85-100% |
| classic-constants-core | 89% |

### Running Coverage Locally

```bash
# Install cargo-llvm-cov
cargo install cargo-llvm-cov

# Run coverage for workspace
cargo llvm-cov --workspace --manifest-path ClassicLib-rs/Cargo.toml

# Generate HTML report
cargo llvm-cov --workspace --manifest-path ClassicLib-rs/Cargo.toml --html

# View report
start target/llvm-cov/html/index.html  # Windows
open target/llvm-cov/html/index.html   # macOS

# Exclude Python binding crates (not tested via Rust)
cargo llvm-cov --workspace --manifest-path ClassicLib-rs/Cargo.toml \
  --exclude classic-yaml-py \
  --exclude classic-database-py \
  --exclude classic-file-io-py \
  --exclude classic-scanlog-py \
  --exclude classic-config-py \
  --exclude classic-scangame-py \
  --exclude classic-registry-py \
  --exclude classic-perf-py \
  --exclude classic-settings-py \
  --exclude classic-message-py \
  --exclude classic-path-py \
  --exclude classic-constants-py \
  --exclude classic-version-py \
  --exclude classic-resource-py \
  --exclude classic-xse-py \
  --exclude classic-web-py \
  --exclude classic-update-py \
  --exclude classic-shared-py
```

## Test Fixtures and Helpers

### Creating Test Databases

```rust
/// Create a temporary SQLite database with test data.
async fn create_test_database(
    table_name: &str,
    entries: &[(&str, &str, &str)], // (formid, plugin, entry)
) -> Result<(NamedTempFile, PathBuf), DatabaseError> {
    let temp_file = NamedTempFile::with_suffix(".db")?;
    let db_path = temp_file.path().to_path_buf();

    let conn_str = format!("sqlite://{}?mode=rwc", db_path.display());
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect(&conn_str)
        .await?;

    // Create table
    let create_sql = format!(
        "CREATE TABLE {} (formid TEXT, plugin TEXT, entry TEXT, PRIMARY KEY (formid, plugin))",
        table_name
    );
    sqlx::query(&create_sql).execute(&pool).await?;

    // Insert test data
    for (formid, plugin, entry) in entries {
        let insert_sql = format!(
            "INSERT INTO {} (formid, plugin, entry) VALUES (?, ?, ?)",
            table_name
        );
        sqlx::query(&insert_sql)
            .bind(*formid)
            .bind(*plugin)
            .bind(*entry)
            .execute(&pool)
            .await?;
    }

    pool.close().await;
    Ok((temp_file, db_path))
}
```

### Test YAML Content Fixtures

```rust
/// Minimal valid main YAML content for testing
fn minimal_main_yaml() -> &'static str {
    r#"
CLASSIC_Info:
  version: "7.31.0"
  version_date: "2024-01-15"
catch_log_records:
  - "LAND"
  - "REFR"
"#
}

/// Minimal valid game YAML content for testing
fn minimal_game_yaml() -> &'static str {
    r#"
Game_Info:
  XSE_Acronym: "F4SE"
  GameVersion: "1.10.163"
"#
}
```

### Shared Test Utilities

Consider creating a test utilities crate or module in `classic-shared-core` for:

- Temporary file creation helpers
- Mock YAML data generators
- Test database setup/teardown
- Common assertion helpers

## Common Anti-Patterns

### ❌ Don't Hardcode Paths

```rust
// BAD
let path = Path::new("C:\\Users\\Test\\config.yaml");

// GOOD
let temp_dir = tempdir().unwrap();
let path = temp_dir.path().join("config.yaml");
```

### ❌ Don't Ignore Test Cleanup

```rust
// BAD
#[test]
fn test_cache() {
    // Modifies global cache, leaves it dirty
    GLOBAL_CACHE.insert("key", "value");
}

// GOOD
#[test]
#[serial]
fn test_cache() {
    clear_global_cache();
    GLOBAL_CACHE.insert("key", "value");
    // Clear at end or use RAII guard
}
```

### ❌ Don't Block on Async Code

```rust
// BAD - blocks the test runtime
#[test]
fn test_async_code() {
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async_function());  // May cause issues
}

// GOOD - use tokio::test
#[tokio::test]
async fn test_async_code() {
    async_function().await;
}
```

### ❌ Don't Use Shared State Without Synchronization

```rust
// BAD - race condition
static mut COUNTER: u32 = 0;

#[test]
fn test_increment() {
    unsafe { COUNTER += 1; }  // Data race!
}

// GOOD - use Arc/Mutex or serial_test
#[test]
#[serial]
fn test_increment() {
    let counter = Arc::new(AtomicU32::new(0));
    // Thread-safe operations
}
```

## Integration with Python Tests

Python binding crates (`-py` crates) are tested via Python integration tests in `tests/rust_integration/`. These tests verify:

1. PyO3 bindings work correctly
2. Error handling propagates properly
3. Type conversions are correct
4. Async/await bridges function

```bash
# Run Python integration tests for Rust bindings
uv run pytest tests/rust_integration/ -v
```

## CI Integration

The GitHub Actions CI workflow includes dedicated Rust jobs that run independently:

1. **Rust Formatting** (10 min timeout)
   - `cargo fmt --all -- --check`
   - Non-blocking (formatting issues don't fail CI)

2. **Rust Linting** (60 min timeout)
   - `cargo clippy --workspace --all-targets --all-features -- -D warnings`
   - Clippy warnings treated as errors

3. **Rust Build** (60 min timeout)
   - `cargo build --workspace --release`
   - Produces build artifacts for Python bindings

4. **Rust Tests** (30 min timeout) - **NEW**
   - Runs independently of Python tests
   - Two test phases:
     1. `cargo test --workspace --release` - Default feature tests
     2. `cargo test --workspace --release --all-features` - All-features tests
   - Full backtrace enabled (`RUST_BACKTRACE=full`)
   - Output captured (`--nocapture`)

5. **Python Bindings** (30 min timeout)
   - Maturin builds for all `-py` crates
   - Depends on Rust Build job

6. **Coverage** (future)
   - `cargo llvm-cov` with 55% minimum threshold
   - Exclude `-py` crates from coverage requirements

## Writing New Tests

When adding tests to Rust crates:

1. **Choose Test Type**
   - Unit tests: In `src/` files with `#[cfg(test)]` module
   - Integration tests: In `tests/` directory

2. **Use Appropriate Attributes**
   - `#[test]` for sync tests
   - `#[tokio::test]` for async tests
   - `#[serial]` for tests touching global state

3. **Follow Naming Conventions**
   - Test files: `test_*.rs` or `*_tests.rs`
   - Test functions: `test_*`
   - Test modules: `mod tests { ... }`

4. **Document Test Purpose**
   - Add `///` doc comments to test functions
   - Group related tests in modules

5. **Handle Cleanup**
   - Use `tempfile` for filesystem tests
   - Clear caches in tests that modify global state
   - Close database connections explicitly

## Troubleshooting

### Test Hangs

```bash
# Run with timeout
cargo test --workspace -- --test-threads=1

# Check for deadlocks
RUST_BACKTRACE=1 cargo test -p problematic-crate
```

### Flaky Tests

- Use `#[serial]` for tests that share state
- Increase timeouts for async operations
- Check for race conditions in concurrent tests

### Coverage Not Updating

```bash
# Clean and rebuild
cargo clean
cargo llvm-cov --workspace --manifest-path ClassicLib-rs/Cargo.toml
```

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Main project documentation
- [Rust Workspace Architecture](../development/rust_workspace_architecture.md)
- [Async Development Guide](../development/async_development_guide.md)
- [PyO3 Integration Patterns](../development/pyo3_integration_patterns.md)
