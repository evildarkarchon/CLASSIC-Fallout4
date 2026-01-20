# Memories

Historical decisions and lessons learned that inform future development.

## General Practices

- Output test results to file to avoid truncation
- Use Mixins with TYPE_CHECKING for MainWindow extensions
- Maintain API compatibility with deprecation warnings (production only)

## Architecture Decisions

- **Direct module imports**: Import Rust modules directly (`import classic_yaml`)
- **Facade removed**: classic-core facade eliminated - Python imports individual modules
- **FCX mode read-only**: Detects issues but never modifies files; use `detect_*` functions

## AsyncBridge Usage

- **GUI and testing only**: AsyncBridge is for same-thread GUI contexts and testing
- **CLI uses async-first**: Single `asyncio.run(main())` at entry point
- **Thread-local**: Cannot use in cross-thread workers (QRunnable, QThread) - use `asyncio.run()` instead
- **Dual interface pattern**: Async methods primary (CLI), sync wrappers documented as "GUI-only"

## Bug Fixes

- **YAML helper methods**: Use `.get()` on Hash nodes, not index notation (returns BadValue for missing keys)
- **Parallel YAML loading**: Use `tokio::join!` (preserves order), not `JoinSet::join_next()` (completion order)

## PyO3 Patterns

- **GIL handling**: Use `py.detach()` to release GIL, `Python::attach()` to reacquire in workers
- **Runtime conflicts**: Avoid `get_runtime().block_on()` when already in Python context
- **Custom exceptions**: Each `-py` crate defines exceptions via `create_exception!` macro
