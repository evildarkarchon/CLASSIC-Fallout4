# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the CLASSIC project.

## Workflows

### ci.yml - Continuous Integration
**Triggers**: Push and PR to `main`, `classic-next`, `develop` branches

**Jobs**:
1. **lint-python** - Ruff code quality checks
2. **lint-rust** - Clippy and rustfmt validation
3. **build-rust** - Build Rust workspace and run tests
4. **build-python-bindings** - Build PyO3 modules with maturin
5. **test-python** - Run pytest suite (unit, integration, Rust integration)
6. **type-check** - Mypy type validation (non-blocking)

**Features**:
- Comprehensive caching (Cargo registry, build artifacts, Python deps)
- Timeouts on all jobs to prevent deadlocks (10-30 min per job)
- Individual test timeouts via pytest-timeout (300-600s per test)
- Parallel test execution with pytest-xdist
- Artifact uploads for debugging (wheels, test results)

**Run Time**: ~15-25 minutes for full pipeline

## Quick Start

### Running Checks Locally

Before pushing to ensure CI will pass:

```bash
# Python checks
uv run ruff check .
uv run ruff format --check .

# Rust checks
cargo fmt --all --manifest-path rust/Cargo.toml -- --check
cargo clippy --workspace --all-targets --manifest-path rust/Cargo.toml -- -D warnings

# Build and test
cargo build --workspace --release --manifest-path rust/Cargo.toml
cargo test --workspace --release --manifest-path rust/Cargo.toml
uv run pytest -n 4 -m "unit and not slow"
```

### Debugging CI Failures

1. Check the Actions tab on GitHub for detailed logs
2. Download artifacts (wheels, test results) for local inspection
3. Look for timeout issues if jobs are cancelled after timeout period
4. Check caching - clear caches from Actions → Caches if needed

## Documentation

For detailed CI/CD documentation, see:
- **[CI/CD Guide](../../docs/development/ci_cd_guide.md)** - Comprehensive guide with troubleshooting
- **[Async Development Guide](../../docs/development/async_development_guide.md)** - Async patterns and testing
- **[PyO3 Integration Patterns](../../docs/development/pyo3_integration_patterns.md)** - Rust-Python integration

## Architecture

The CI is designed for the hybrid Python-Rust architecture:

```
┌─────────────────────────────────────────────────┐
│              Lint Jobs (Parallel)               │
├────────────────────┬────────────────────────────┤
│   Python (Ruff)    │    Rust (Clippy/fmt)       │
└─────────┬──────────┴────────────┬───────────────┘
          │                       │
          │                       ▼
          │              ┌────────────────┐
          │              │  Build Rust    │
          │              │  Workspace     │
          │              └────────┬───────┘
          │                       │
          └───────────┬───────────┘
                      ▼
          ┌───────────────────────┐
          │ Build Python Bindings │
          │    (maturin)          │
          └─────┬─────────────────┘
                │
       ┌────────┴──────────┐
       ▼                   ▼
┌──────────────┐   ┌───────────────┐
│ Python Tests │   │  Type Check   │
│  (pytest)    │   │    (mypy)     │
└──────────────┘   └───────────────┘
```

## Release Process

**Note**: Releases are currently **manual** due to large file requirements.

See [CI/CD Guide - Release Process](../../docs/development/ci_cd_guide.md#release-process) for detailed steps.

## Maintenance

### Updating Workflows

When modifying workflows:

1. Test changes in a fork or feature branch first
2. Update this README if adding/removing jobs
3. Update the main CI/CD guide documentation
4. Consider cache invalidation if changing dependencies

### Cache Management

Caches are automatically managed but can be manually cleared:
1. Go to Actions tab on GitHub
2. Click "Caches" in the left sidebar
3. Delete specific caches if needed

Cache keys:
- `{os}-cargo-registry-{Cargo.lock hash}`
- `{os}-cargo-index-{Cargo.lock hash}`
- `{os}-cargo-build-{Cargo.lock hash}-{source hash}`

## Timeout Configuration

All jobs have timeouts to prevent deadlocks:

| Job | Timeout | Rationale |
|-----|---------|-----------|
| lint-python | 10 min | Fast linting checks |
| lint-rust | 15 min | Clippy can be slow |
| build-rust | 20 min | Full workspace compilation |
| build-python-bindings | 30 min | Multiple maturin builds |
| test-python | 30 min | Comprehensive test suite |
| type-check | 15 min | Mypy analysis |

Individual tests also have timeouts:
- Unit tests: 300s (5 minutes)
- Integration tests: 600s (10 minutes)

## Contributing

When adding new Rust crates or Python modules:

1. Update `build-python-bindings` job if adding `-py` crates
2. Add new test markers to pytest if needed
3. Consider cache implications for new dependencies
4. Update timeout values if builds become slower

## Support

For CI/CD issues:
1. Check [CI/CD Guide troubleshooting section](../../docs/development/ci_cd_guide.md#debugging-ci-failures)
2. Review recent workflow runs for similar issues
3. Create an issue with CI logs and error details
4. Tag maintainers for urgent CI breakage
