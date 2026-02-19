# CLASSIC Documentation

Welcome to the CLASSIC documentation! This directory contains comprehensive documentation organized by purpose.

## 📚 Quick Navigation

### Start Here
- **[Quick Start Guide](api/QUICK_START.md)** - Get up and running in 5 minutes
- **[API Reference](api/API_REFERENCE.md)** - Complete ClassicLib API documentation
- **[Architecture Overview](architecture/ARCHITECTURE_OVERVIEW.md)** - System design with diagrams
- **[Rust Documentation Index](RUST_DOCUMENTATION_INDEX.md)** - Complete guide to all Rust documentation

### Documentation by Category

#### 📖 API Documentation
**[api/](api/)** - API reference and getting started
- **[Quick Start Guide](api/QUICK_START.md)** - Get started in 5 minutes
- **[API Reference](api/API_REFERENCE.md)** - Complete ClassicLib API
- **[Code Examples](examples/CODE_EXAMPLES.md)** - Practical code patterns

#### 🛠️ Development
**[development/](development/)** - Development guides for working with CLASSIC
- **[Rust Integration Guide](development/RUST_INTEGRATION_GUIDE.md)** - Hybrid Python-Rust architecture
- Rust 2024 edition guide
- Rust workspace architecture
- PyO3 integration patterns
- Async development guide
- Rust acceleration guide

#### 📋 Planning
**[planning/](planning/)** - Strategic planning documents
- Classic core modularization plan
- PyO3 async runtimes implementation plan
- Rust CLI/TUI migration plan
- TUI feature parity plan

#### 🧪 Testing
**[testing/](testing/)** - Testing guides and standards
- Testing guide index
- Test structure documentation
- Test pollution guide
- Component-specific testing guides (AsyncBridge, FileIO, YAML, etc.)
- Async test patterns
- Fixture standards and migration

#### 🦀 Rust
**[rust/](rust/)** - Rust reference documentation
- Rust usage guide (start here for Rust features)
- Rust architecture overview
- Native async pattern guide
- Module-specific documentation
- PyO3 0.27 migration guide
- PyO3 quick reference
- Troubleshooting Rust issues
- Development with Rust components

#### ⚡ Performance
**[performance/](performance/)** - Performance optimization guides
- Performance monitoring
- Memory profiling
- FFI optimization
- Rust performance reports
- TUI dirty tracking optimization

#### 📖 User Guides
**[guides/](guides/)** - End-user documentation
- CLI user guide
- TUI user guide
- PyO3 async runtimes usage

#### 🏗️ Architecture
**[architecture/](architecture/)** - Architectural documentation
- **[Architecture Overview](architecture/ARCHITECTURE_OVERVIEW.md)** - Complete system design
- CLI/TUI architecture
- Help system schema

#### 📝 Implementation
**[implementation/](implementation/)** - Implementation summaries and reports
- Async YAML implementation summary
- Rust/Python verification reports
- ScanLog verification
- Max connections summary

#### 🔄 Migration
**[migration/](migration/)** - Migration guides and patterns
- API migration README
- Async YAML migration examples
- Async threading patterns guide
- Async YAML documentation

#### 🗂️ Other
**[other/](other/)** - Miscellaneous documentation
- PyInstaller data bundling

## 🎯 Documentation by Audience

### For End Users
1. Start with **[Rust Usage Guide](rust/rust_usage_guide.md)**
2. Check **[CLI User Guide](guides/cli_user_guide.md)** or **[TUI User Guide](guides/tui_user_guide.md)**
3. If issues arise: **[Troubleshooting Rust](rust/troubleshooting_rust.md)**

### For Developers
1. Read **[Development with Rust](rust/development_with_rust.md)**
2. Study **[Rust Workspace Architecture](development/rust_workspace_architecture.md)**
3. Follow **[Testing Guide Index](testing/TESTING_GUIDE_INDEX.md)**

### For Contributors
1. Review **[Rust Architecture](rust/rust_architecture.md)**
2. Understand **[Async Development Guide](development/async_development_guide.md)**
3. Follow **[Testing Standards](testing/test_pollution_guide.md)**

### For System Administrators
1. Set up **[Performance Monitoring](performance/performance_monitoring.md)**
2. Configure **[Troubleshooting](rust/troubleshooting_rust.md)** procedures
3. Review **[Architecture](architecture/cli_tui_architecture.md)** for deployment

## 📖 Key Documentation

### Essential Reading
- **[RUST_DOCUMENTATION_INDEX.md](RUST_DOCUMENTATION_INDEX.md)** - Master index for all Rust docs
- **[Rust Usage Guide](rust/rust_usage_guide.md)** - Understanding Rust acceleration
- **[Development with Rust](rust/development_with_rust.md)** - Developer's guide

### Most Referenced
- **[PyO3 Integration Patterns](development/pyo3_integration_patterns.md)** - PyO3 best practices
- **[Testing Guide Index](testing/TESTING_GUIDE_INDEX.md)** - Testing standards
- **[Performance Monitoring](performance/performance_monitoring.md)** - Monitoring Rust performance

## 🔍 Finding Documentation

1. **By topic**: Browse the category folders above
2. **By audience**: Use the "Documentation by Audience" section
3. **By keyword**: Use your editor's search or `grep -r "keyword" docs/`
4. **Index**: Start with [RUST_DOCUMENTATION_INDEX.md](RUST_DOCUMENTATION_INDEX.md)

## 🆕 Recent Additions

- **[Quick Start Guide](api/QUICK_START.md)** - Get up and running in 5 minutes
- **[API Reference](api/API_REFERENCE.md)** - Complete ClassicLib API documentation
- **[Architecture Overview](architecture/ARCHITECTURE_OVERVIEW.md)** - System design with Mermaid diagrams
- **[Rust Integration Guide](development/RUST_INTEGRATION_GUIDE.md)** - Hybrid Python-Rust architecture
- **[Code Examples](examples/CODE_EXAMPLES.md)** - Practical code patterns
- **[Rust 2024 Edition Guide](development/rust_2024_edition_guide.md)** - Modern Rust features
- **[Async Development Guide](development/async_development_guide.md)** - Comprehensive async patterns

## 📝 Contributing Documentation

When adding new documentation:
1. Place it in the appropriate category folder
2. Update the relevant index (RUST_DOCUMENTATION_INDEX.md for Rust-related docs)
3. Add cross-references to related documentation
4. Update this README if adding a new major document

## 🏗️ Documentation Structure

```
docs/
├── README.md (this file)
├── RUST_DOCUMENTATION_INDEX.md (master index)
├── api/                 (API reference and quick start)
├── architecture/        (architectural docs)
├── development/         (development guides)
├── examples/            (code examples)
├── guides/              (user guides)
├── implementation/      (implementation reports)
├── migration/           (migration guides)
├── other/               (miscellaneous)
├── performance/         (performance guides)
├── planning/            (strategic plans)
├── rust/                (Rust reference docs)
└── testing/             (testing documentation)
```

## ❓ Need Help?

- **Can't find documentation?** Check [RUST_DOCUMENTATION_INDEX.md](RUST_DOCUMENTATION_INDEX.md)
- **Documentation outdated?** Please open an issue or submit a PR
- **Broken links?** Report in GitHub issues

---

**Note**: This documentation structure was organized in October 2025 to improve discoverability and prevent accidental deletion of important documents.
