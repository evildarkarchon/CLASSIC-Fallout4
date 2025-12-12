# Continuous Integration

CLASSIC uses GitHub Actions for automated testing and validation on every PR and push.

## CI Pipeline
- **Python Linting**: Ruff code quality checks (10 min timeout)
- **Rust Linting**: Clippy and rustfmt validation (15 min timeout)
- **Rust Build**: Full workspace compilation and testing (20 min timeout)
- **Python Bindings**: Maturin builds all PyO3 modules (30 min timeout)
- **Python Tests**: pytest suite with Rust acceleration (30 min timeout)
  - Unit tests: 300s per-test timeout
  - Integration tests: 600s per-test timeout
  - Rust integration tests: 300s per-test timeout
- **Type Checking**: mypy validation (non-blocking, 15 min timeout)

## Running CI Checks Locally
```bash
# Python checks
uv run ruff check .
uv run ruff format --check .

# Rust checks
cargo fmt --all --manifest-path rust/Cargo.toml -- --check
cargo clippy --workspace --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings

# Build and test
cargo build --workspace --release --manifest-path rust/Cargo.toml
cargo test --workspace --release --manifest-path rust/Cargo.toml
uv run pytest -n 4 -m "unit and not slow"
```

## Key Features
- **Comprehensive Caching**: Cargo registry, build artifacts, and Python dependencies
- **Timeout Protection**: All jobs and individual tests have timeouts to prevent deadlocks
- **Parallel Execution**: Tests run in parallel with pytest-xdist
- **Artifact Uploads**: Wheels and test results available for debugging

**Complete Guide**: See [CI/CD Guide](docs/development/ci_cd_guide.md) for troubleshooting and release process
