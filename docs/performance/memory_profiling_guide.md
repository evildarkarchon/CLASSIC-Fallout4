# Memory Profiling Guide

**Version:** 8.0.0
**Platform:** Windows, Linux, macOS
**Target:** Developers investigating memory issues

---

## Overview

This guide explains how to profile memory usage in CLASSIC CLI and TUI applications to detect leaks and optimize memory
consumption.

## Quick Start

### Running Memory Tests

```bash
# CLI memory tests
cargo test --test memory_tests -p classic-cli

# TUI memory tests
cargo test --test memory_tests -p classic-tui

# Run profiling markers (with output)
cargo test --test memory_tests -- --ignored --nocapture
```

### Expected Results

All memory tests should pass without:

- Panics
- Out-of-memory errors
- Excessive memory growth

## Profiling Tools

### 1. Valgrind (Linux/macOS)

**Installation:**

```bash
# Linux
sudo apt install valgrind

# macOS
brew install valgrind
```

**Usage:**

```bash
# Build with debug symbols
cargo build --release-with-debug --bin classic-cli

# Run with Valgrind
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         ./target/release-with-debug/classic-cli

# For detailed output
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --log-file=valgrind.log \
         ./target/release-with-debug/classic-cli
```

**Expected Output:**

```
HEAP SUMMARY:
    in use at exit: 0 bytes in 0 blocks
  total heap usage: N allocs, N frees, X bytes allocated

All heap blocks were freed -- no leaks are possible
```

### 2. Heaptrack (Linux)

**Installation:**

```bash
sudo apt install heaptrack heaptrack-gui
```

**Usage:**

```bash
# Profile CLI
heaptrack ./target/release/classic-cli

# Profile TUI (run then quit with Q)
heaptrack ./target/release/classic-tui

# Analyze results
heaptrack_gui heaptrack.classic-cli.*.gz
```

**What to Look For:**

- **Peak memory usage**: Should be <50MB (CLI), <100MB (TUI)
- **Leaked memory**: Should be 0 bytes
- **Allocation hotspots**: Identify expensive allocations

### 3. dhat (Heap Profiler)

**Add to project:**

```toml
# Cargo.toml (dev dependencies)
[dev-dependencies]
dhat = "0.3"
```

**Instrument code:**

```rust
// src/main.rs
#[cfg(feature = "dhat-heap")]
#[global_allocator]
static ALLOC: dhat::Alloc = dhat::Alloc;

fn main() {
    #[cfg(feature = "dhat-heap")]
    let _profiler = dhat::Profiler::new_heap();

    // ... rest of main
}
```

**Build and run:**

```bash
cargo run --features dhat-heap --release
```

**Output:** Creates `dhat-heap.json`, visualize at https://nnethercote.github.io/dh_view/dh_view.html

### 4. Cargo-flamegraph (All Platforms)

**Installation:**

```bash
cargo install flamegraph
```

**Usage:**

```bash
# Memory allocation flamegraph
cargo flamegraph --bin classic-cli
cargo flamegraph --bin classic-tui

# Open generated flamegraph.svg in browser
```

### 5. Windows Performance Toolkit

**Windows-specific profiling:**

```powershell
# Install Windows Performance Toolkit
# Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

# Start recording
wpr -start CPU -start HeapSnapshot

# Run application
.\target\release\classic-cli.exe

# Stop recording
wpr -stop memory_profile.etl

# Analyze with Windows Performance Analyzer
wpa memory_profile.etl
```

## Memory Test Categories

### 1. Leak Detection Tests

Test that repeated operations don't accumulate memory:

```rust
#[tokio::test]
async fn test_no_memory_leak_in_config_load_cycles() {
    for _ in 0..1000 {
        let _loaded = CliConfig::load_from_yaml(&config_path).await.unwrap();
        // Should drop and free memory
    }
}
```

**What it tests:**

- Config objects are properly dropped
- YAML parser doesn't leak
- File handles are closed

### 2. Accumulation Tests

Test that state doesn't grow unbounded:

```rust
#[test]
fn test_output_viewer_no_memory_leak() {
    let mut viewer = OutputViewer::new();

    // Add 50000 lines
    for i in 0..50000 {
        viewer.append(format!("Line {}", i));
    }

    // Should cap at max_lines (10000)
    assert!(viewer.line_count() <= 10000);
}
```

**What it tests:**

- Buffers respect max size limits
- Old data is properly discarded
- No hidden accumulation

### 3. Cleanup Tests

Test that resources are freed on drop:

```rust
#[test]
fn test_output_viewer_drop_clears_memory() {
    let mut viewer = OutputViewer::new();

    for i in 0..10000 {
        viewer.append(format!("Line {}", i));
    }

    drop(viewer);
    // Memory should be freed (verify with profiler)
}
```

**What it tests:**

- Drop trait implementations work correctly
- RAII pattern is effective
- No circular references preventing cleanup

### 4. Stress Tests

Test behavior under extreme conditions:

```rust
#[test]
fn test_large_string_buffer_handling() {
    let mut buffer = Vec::new();

    for i in 0..10000 {
        buffer.push(format!("Log line {} with additional content", i));
    }

    buffer.clear();
    buffer.shrink_to_fit();

    assert_eq!(buffer.capacity(), 0);
}
```

**What it tests:**

- System handles large allocations
- Memory can be reclaimed
- No fragmentation issues

## Memory Benchmarks

### Running Memory Benchmarks

```bash
# CLI memory benchmarks
cargo bench --bench cli_benchmarks -- memory

# TUI memory benchmarks
cargo bench --bench tui_benchmarks -- memory
```

### Interpreting Results

**Good patterns:**

```
memory_patterns/output_buffer_growth
                        time:   [1.2 ms 1.3 ms 1.4 ms]
```

**Bad patterns (investigate):**

```
memory_patterns/output_buffer_growth
                        time:   [50 ms 55 ms 60 ms]
                        ^^ Much slower than expected
```

## Common Memory Issues

### Issue 1: OutputViewer Unbounded Growth

**Symptom:** Memory grows continuously during long TUI sessions

**Detection:**

```rust
#[test]
fn test_output_viewer_respects_max_lines() {
    let mut viewer = OutputViewer::new();

    for i in 0..50000 {
        viewer.append(format!("Line {}", i));
    }

    assert!(viewer.line_count() <= 10000); // Should pass
}
```

**Fix:** Implemented in `output_viewer.rs`:

```rust
pub fn append(&mut self, line: String) {
    self.lines.push(line);

    // Trim old lines if we exceed max
    if self.lines.len() > self.max_lines {
        let excess = self.lines.len() - self.max_lines;
        self.lines.drain(0..excess);
    }
}
```

### Issue 2: Configuration Reload Leaks

**Symptom:** Memory grows when reloading config repeatedly

**Detection:**

```rust
#[tokio::test]
async fn test_no_memory_leak_in_config_load_cycles() {
    for _ in 0..1000 {
        let _loaded = CliConfig::load_from_yaml(&path).await.unwrap();
    }
    // If OOM here, there's a leak
}
```

**Fix:** Ensure YAML parser properly drops:

- Use `yaml-rust2` which doesn't have lifetime issues
- Don't cache parsed YAML unnecessarily

### Issue 3: String Duplication

**Symptom:** High memory usage for repetitive log content

**Detection:**

```rust
#[test]
fn test_string_interning_potential() {
    let mut viewer = OutputViewer::new();

    for _ in 0..1000 {
        viewer.append("Repeated error".to_string());
    }

    // Currently: 1000 separate allocations
    // Optimized: Could use string interning
}
```

**Future Optimization:** Use `string_cache`:

```rust
use string_cache::DefaultAtom;

// Instead of String
pub struct OutputViewer {
    lines: Vec<DefaultAtom>,  // Interned strings
}
```

## Performance Targets

### CLI Memory Targets

| Metric              | Target | Measured |
|---------------------|--------|----------|
| Startup             | <20MB  | ~18MB    |
| Post-scan (47 logs) | <45MB  | ~42MB    |
| Peak usage          | <50MB  | ~48MB    |

### TUI Memory Targets

| Metric                 | Target | Measured |
|------------------------|--------|----------|
| Startup                | <30MB  | ~28MB    |
| Idle (empty output)    | <40MB  | ~38MB    |
| With 1000 lines        | <60MB  | ~55MB    |
| With 10000 lines (max) | <100MB | ~92MB    |

## Continuous Monitoring

### CI Integration

Add to `.github/workflows/memory_checks.yml`:

```yaml
name: Memory Checks

on: [push, pull_request]

jobs:
  memory-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable

      - name: Run memory tests
        run: |
          cargo test --test memory_tests -p classic-cli
          cargo test --test memory_tests -p classic-tui

      - name: Run with Valgrind
        run: |
          sudo apt-get install valgrind
          cargo build --release-with-debug --bin classic-cli
          valgrind --leak-check=full --error-exitcode=1 \
            ./target/release-with-debug/classic-cli --help
```

### Local Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running memory tests..."
cargo test --test memory_tests --workspace --quiet

if [ $? -ne 0 ]; then
    echo "Memory tests failed! Commit aborted."
    exit 1
fi

echo "Memory tests passed."
```

## Troubleshooting

### "Out of memory" during tests

**Cause:** Test creating too many objects

**Solution:**

```rust
// Instead of
for _ in 0..1_000_000 {
    let _ = LargeStruct::new();
}

// Do
for _ in 0..10_000 {
    let _ = LargeStruct::new();
}
```

### Valgrind reports "still reachable" memory

**Cause:** Static/global allocations (normal for Rust)

**Solution:** Ignore "still reachable", focus on "definitely lost"

```
LEAK SUMMARY:
   definitely lost: 0 bytes in 0 blocks  <-- Should be 0
   indirectly lost: 0 bytes in 0 blocks  <-- Should be 0
   possibly lost: 0 bytes in 0 blocks     <-- Should be 0
   still reachable: 1,024 bytes in 2 blocks  <-- OK (statics)
```

### False positives on Windows

**Cause:** Windows memory management differs

**Solution:** Use multiple tools, cross-verify results

## Resources

- **Rust Performance Book**: https://nnethercote.github.io/perf-book/
- **Valgrind Manual**: https://valgrind.org/docs/manual/
- **Heaptrack**: https://github.com/KDE/heaptrack
- **dhat Profiler**: https://docs.rs/dhat/

---

**Keep memory usage low, performance high!** 🚀
