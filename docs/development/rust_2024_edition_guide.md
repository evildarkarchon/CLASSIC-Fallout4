# Rust 2024 Edition Guide

This guide covers Rust 2024 edition features and best practices for CLASSIC development.

## Overview

CLASSIC uses **Rust 2024 edition** for all Rust code. This edition brings improved ergonomics, safety features, and modern idioms that align with our performance-critical architecture.

## Edition Configuration

All `Cargo.toml` files must specify Rust 2024:

```toml
[package]
edition = "2024"
```

## Rust 2024 Key Features

### 1. `-> impl Trait` in traits
- Return position `impl Trait` (RPIT) now works in trait definitions
- Enables more ergonomic async trait methods without `async-trait` macro
- Example:
  ```rust
  trait AsyncProcessor {
      async fn process(&self, data: String) -> impl Future<Output = Result<String>>;
  }
  ```

### 2. Improved pattern matching
- Exhaustiveness checking improvements
- Better error messages for complex match expressions
- Use exhaustive matches for enum variants

### 3. `if let` and `while let` chain improvements
- More flexible control flow patterns
- Better integration with `?` operator

### 4. Disjoint closure captures
- Closures capture only the fields they use, not entire structs
- Reduces false borrow checker conflicts
- Enables more concurrent patterns

### 5. Reserved syntax
- `gen` keyword reserved for generators (future feature)
- Plan ahead for generator patterns in async code

## Best Practices for Rust 2024

### ✅ DO: Use Modern Error Handling Patterns

```rust
// ✅ CORRECT - Use ? operator with Result
pub fn load_config(path: &Path) -> Result<Config, ClassicError> {
    let content = std::fs::read_to_string(path)?;
    let config = parse_yaml(&content)?;
    Ok(config)
}

// ✅ CORRECT - Use thiserror for error types
#[derive(Debug, thiserror::Error)]
pub enum ClassicError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Parse error: {0}")]
    Parse(String),
}
```

### ✅ DO: Leverage Async Traits Without Macros

```rust
// ✅ CORRECT - Native async in traits (Rust 2024)
pub trait AsyncFileProcessor {
    async fn read_file(&self, path: &Path) -> Result<String>;
    async fn write_file(&self, path: &Path, content: &str) -> Result<()>;
}

// Implementation
impl AsyncFileProcessor for FileIOCore {
    async fn read_file(&self, path: &Path) -> Result<String> {
        tokio::fs::read_to_string(path).await
            .map_err(ClassicError::from)
    }
}
```

### ✅ DO: Use Disjoint Capture for Better Borrowing

```rust
// ✅ CORRECT - Closure captures only needed fields
struct Config {
    database_path: PathBuf,
    log_level: String,
    max_threads: usize,
}

impl Config {
    fn spawn_worker(&self) {
        let max_threads = self.max_threads;  // Only capture this field
        std::thread::spawn(move || {
            // Can still borrow other fields in parent scope
            println!("Using {} threads", max_threads);
        });
    }
}
```

### ✅ DO: Leverage Pattern Matching Improvements

```rust
// ✅ CORRECT - Exhaustive enum matching
match analysis_result {
    AnalysisResult::Success { data, warnings } => {
        log_warnings(&warnings);
        process_data(data)
    }
    AnalysisResult::PartialSuccess { data, errors } => {
        log_errors(&errors);
        process_partial(data)
    }
    AnalysisResult::Failure { error } => {
        handle_failure(error)
    }
}

// ✅ CORRECT - Use if let chains for complex conditions
if let Some(config) = load_config(path)?
    && config.is_valid()
    && let Some(db) = open_database(&config.db_path)?
{
    // All conditions met, proceed
    process_with_db(config, db)?;
}
```

### ✅ DO: Follow Rust 2024 Naming Conventions

```rust
// ✅ CORRECT - Use snake_case for functions and variables
pub async fn parse_crash_log(log_path: &Path) -> Result<CrashLog> {
    let raw_content = read_file_async(log_path).await?;
    let parsed_log = parse_log_content(&raw_content)?;
    Ok(parsed_log)
}

// ✅ CORRECT - Use CamelCase for types
pub struct FormIDAnalyzer {
    cache: HashMap<FormID, PluginRecord>,
    database_pool: DatabasePool,
}

// ✅ CORRECT - Use SCREAMING_SNAKE_CASE for constants
pub const MAX_LOG_SIZE_BYTES: usize = 100 * 1024 * 1024;  // 100 MB
pub const DEFAULT_WORKER_THREADS: usize = 4;
```

### ✅ DO: Use Result Early Returns

```rust
// ✅ CORRECT - Early return pattern with ?
pub fn validate_and_process(data: &str) -> Result<ProcessedData> {
    let parsed = parse_data(data)?;  // Early return on error
    let validated = validate_structure(&parsed)?;  // Early return
    let processed = transform_data(validated)?;  // Early return
    Ok(processed)
}

// ❌ WRONG - Nested match statements
pub fn validate_and_process(data: &str) -> Result<ProcessedData> {
    match parse_data(data) {
        Ok(parsed) => match validate_structure(&parsed) {
            Ok(validated) => match transform_data(validated) {
                Ok(processed) => Ok(processed),
                Err(e) => Err(e),
            },
            Err(e) => Err(e),
        },
        Err(e) => Err(e),
    }
}
```

### ✅ DO: Use impl Trait for Return Types

```rust
// ✅ CORRECT - Use impl Trait for iterator returns
pub fn filter_valid_plugins(plugins: &[Plugin]) -> impl Iterator<Item = &Plugin> {
    plugins.iter().filter(|p| p.is_valid())
}

// ✅ CORRECT - Use impl Trait for complex return types
pub fn create_parser() -> impl LogParser + Send + Sync {
    RustLogParser::new()
}
```

### ❌ DON'T: Use Outdated Patterns

```rust
// ❌ WRONG - Manually implementing async traits with Box
#[async_trait]  // Don't need this in Rust 2024!
pub trait OldAsyncTrait {
    async fn process(&self) -> Result<()>;
}

// ❌ WRONG - Capturing entire structs in closures
let closure = move || {
    // This captures the entire self, not just needed fields
    self.database.query()  // Use disjoint capture instead
};

// ❌ WRONG - Using unwrap() in library code
pub fn load_config(path: &Path) -> Config {
    std::fs::read_to_string(path).unwrap()  // Use ? instead!
}
```

## Integration with PyO3

When writing PyO3 bindings in `-py` crates, continue using Rust 2024 patterns:

```rust
// ✅ CORRECT - PyO3 with Rust 2024 patterns
#[pyclass]
pub struct RustLogParser {
    inner: Arc<LogParserCore>,
}

#[pymethods]
impl RustLogParser {
    #[new]
    pub fn new() -> PyResult<Self> {
        let inner = LogParserCore::new()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))?;
        Ok(Self {
            inner: Arc::new(inner),
        })
    }

    pub fn parse_log(&self, py: Python<'_>, path: String) -> PyResult<AnalysisResult> {
        let inner = self.inner.clone();
        py.allow_threads(|| {
            classic_shared::get_runtime()
                .block_on(async move {
                    inner.parse_async(&PathBuf::from(path)).await
                })
                .map_err(|e| PyErr::new::<PyRuntimeError, _>(e.to_string()))
        })
    }
}
```

## Migration Checklist

When migrating existing code to Rust 2024 or writing new code:

- [ ] Update `edition = "2024"` in all `Cargo.toml` files
- [ ] Replace `#[async_trait]` with native async in traits
- [ ] Use `?` operator instead of manual error propagation
- [ ] Leverage disjoint closure captures for better borrowing
- [ ] Use exhaustive pattern matching for all enums
- [ ] Replace `unwrap()` with proper error handling in library code
- [ ] Use `impl Trait` for return types where appropriate
- [ ] Follow naming conventions (snake_case, CamelCase, SCREAMING_SNAKE_CASE)
- [ ] Add `#![warn(rust_2024_compatibility)]` lint during migration period
- [ ] Run `cargo fix --edition` to auto-fix edition-related issues

## Lints and Warnings

Enable Rust 2024 compatibility lints in all crates:

```toml
[lints.rust]
rust_2024_compatibility = "warn"
unsafe_code = "forbid"  # Default for most crates
missing_docs = "warn"   # Encourage documentation
```

**Exception for Performance-Critical Crates**: In crates where `unsafe` is required for performance (e.g., `classic-file-io-core` for memory-mapped I/O), use `warn` instead:

```toml
[lints.rust]
unsafe_code = "warn"  # Allow unsafe with proper documentation
```

**Unsafe Code Requirements**:
- Minimize `unsafe` usage - only for performance-critical operations
- **ALWAYS** document safety invariants with `// Safety:` comment
- Prefer safe abstractions when performance difference is negligible
- Acceptable use cases: memory-mapped I/O, zero-copy operations, FFI
- Unacceptable: convenience, avoiding borrow checker

Example of properly documented unsafe:
```rust
// Large file: use memory-mapped I/O for zero-copy reading
let file = File::open(path)?;

// Safety: We're only reading, not writing, and the file won't be modified
// while we hold the mapping. The file remains open for the lifetime of the mmap.
let mmap = unsafe { Mmap::map(&file)? };
```

Common deny lints for code quality:

```rust
#![deny(
    clippy::unwrap_used,           // Forbid unwrap() in library code
    clippy::expect_used,           // Forbid expect() in library code
    clippy::panic,                 // Forbid explicit panic!()
    clippy::missing_errors_doc,    // Document error conditions
)]
```
