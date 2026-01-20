---
name: ci-check
description: Run local CI checks before committing or creating PRs. Validates Python linting, Rust linting, builds, and tests.
---

This skill runs the same checks as the GitHub Actions CI pipeline locally, helping catch issues before pushing.

## Quick Check (Pre-Commit)

Run these before every commit:

```bash
# Python formatting and linting
uv run ruff format .
uv run ruff check . --fix

# Rust formatting
cargo fmt --all --manifest-path rust/Cargo.toml
```

## Full CI Check (Pre-PR)

Run all checks before creating a pull request.

### Step 1: Python Checks

```bash
# Format check (no changes)
uv run ruff format --check .

# Lint check
uv run ruff check .
```

### Step 2: Rust Checks

```bash
# Format check
cargo fmt --all --manifest-path rust/Cargo.toml -- --check

# Clippy (treat warnings as errors)
cargo clippy --workspace --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings
```

### Step 3: Rust Build and Test

```bash
# Build all crates
cargo build --workspace --release --manifest-path rust/Cargo.toml

# Run Rust tests
cargo test --workspace --release --manifest-path rust/Cargo.toml
```

### Step 4: Python Bindings

```bash
# Rebuild all Python bindings
./rebuild_rust.ps1 -Clean
```

### Step 5: Python Tests

```bash
# Quick unit tests
uv run pytest -m "unit and not slow"

# Integration tests
uv run pytest -m "integration"

# Rust integration tests
uv run pytest tests/rust_integration/ -v
```

### Step 6: Type Checking (Optional)

```bash
# MyPy check (non-blocking in CI)
uv run mypy ClassicLib/ --ignore-missing-imports
```

## One-Liner Commands

### Minimal Check
```bash
uv run ruff check . && cargo clippy --workspace --manifest-path rust/Cargo.toml -- -D warnings
```

### Full Check
```bash
uv run ruff format --check . && uv run ruff check . && cargo fmt --all --manifest-path rust/Cargo.toml -- --check && cargo clippy --workspace --all-targets --all-features --manifest-path rust/Cargo.toml -- -D warnings && cargo test --workspace --release --manifest-path rust/Cargo.toml && uv run pytest -m "unit and not slow"
```

## CI Timeouts Reference

| Job | Timeout |
|-----|---------|
| Python Linting | 10 min |
| Rust Linting | 15 min |
| Rust Build | 20 min |
| Python Bindings | 30 min |
| Python Tests | 30 min |
| Per-test (unit) | 300s |
| Per-test (integration) | 600s |

## Common Issues

### Ruff Errors
```bash
# Auto-fix what can be fixed
uv run ruff check . --fix

# Show specific error explanation
uv run ruff rule <ERROR_CODE>
```

### Clippy Warnings
```bash
# See suggested fixes
cargo clippy --workspace --manifest-path rust/Cargo.toml -- -D warnings 2>&1 | head -100
```

### Test Failures
```bash
# Run single failing test with output
uv run pytest tests/path/to/test.py::test_name -v -s

# Run with more debugging
uv run pytest tests/path/to/test.py::test_name -v -s --tb=long
```

### Rust Build Failures
```bash
# Check specific crate
cargo build -p classic-<name>-core --manifest-path rust/Cargo.toml 2>&1
```

## Checklist

Before creating a PR:

- [ ] `uv run ruff format --check .` passes
- [ ] `uv run ruff check .` passes
- [ ] `cargo fmt --check` passes
- [ ] `cargo clippy -- -D warnings` passes
- [ ] `cargo test --workspace` passes
- [ ] `uv run pytest -m "unit and not slow"` passes
- [ ] Rust integration tests pass (if Rust code changed)
- [ ] Full integration tests pass (if significant changes)
