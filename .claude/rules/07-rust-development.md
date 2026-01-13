# Rust Development

## Rust Documentation Standards

**CRITICAL**: All new Rust code MUST be fully documented according to Rust documentation standards. Missing documentation warnings are treated as errors.

**Requirements**:
- All `pub struct`, `pub enum`, `pub fn`, `pub mod` require `///` doc comments
- All public struct fields and enum variants require documentation
- Crate-level documentation with `//!` at top of `lib.rs` or `main.rs`
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html)
- Only suppress `missing_docs` for generated code (e.g., Slint UI)

**Complete Guide**: See [Rust Documentation Standards](docs/development/rust_documentation_standards.md)

## Core Guides
- **[Rust Workspace Architecture](docs/development/rust_workspace_architecture.md)** - Crate structure and dependency hierarchy
- **[Rust 2024 Edition Guide](docs/development/rust_2024_edition_guide.md)** - Modern Rust features and best practices
- **[Async Development Guide](docs/development/async_development_guide.md)** - Async patterns for Python and Rust
- **[PyO3 Integration Patterns](docs/development/pyo3_integration_patterns.md)** - PyO3 module registration and troubleshooting
- **[Rust Acceleration Guide](docs/development/rust_acceleration_guide.md)** - Performance monitoring and debugging
- **[Slint GUI Development](docs/development/slint_gui_development.md)** - Slint GUI patterns and AsyncBridge usage

## Reference Documentation
- **[Rust Documentation Index](docs/RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust docs
- **[Rust Usage Guide](docs/rust/rust_usage_guide.md)** - User guide for Rust features
- **[Performance Monitoring](docs/performance/performance_monitoring.md)** - Monitor Rust performance
- **[Troubleshooting Guide](docs/rust/troubleshooting_rust.md)** - Debug Rust issues
- **[Development Guide](docs/rust/development_with_rust.md)** - Develop with Rust components

## PyO3 0.27 Documentation
- **[PyO3 0.27 Migration Guide](docs/rust/PyO3-0.27-migration.md)** - Migration from 0.22 to 0.27
- **[PyO3 Quick Reference](docs/rust/pyo3_quick_reference.md)** - Quick reference for common patterns
- **[Official PyO3 Docs](https://pyo3.rs/v0.27.0/)** - Official PyO3 documentation

## Key Rust Rules
- **ONE RUNTIME RULE**: All Rust crates use `classic_shared::get_runtime()` to share global Tokio runtime
- **PyO3 module registration**: `#[pyclass]` types ONLY export from standalone cdylib modules
- **Standalone module pattern**: Each Rust crate exporting Python classes must have `crate-type = ["cdylib", "rlib"]`
- **GIL handling for parallel work**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in worker threads (PyO3 0.27)
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context
- **Business logic separation**: ALL new Rust code MUST separate business logic (`-core` crates) from Python bindings (`-py` crates)
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
