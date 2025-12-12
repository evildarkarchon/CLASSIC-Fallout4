# Code Quality Standards

## File Organization
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** (use dict mapping, match statements, or extract methods)
- **Complete type annotations** (Python 3.12+ syntax)

## Development Rules
1. **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
2. **Use pathlib.Path** - Never string paths
3. **UTF-8 encoding** with `errors="ignore"` for file ops
4. **Async-first** - Use AsyncBridge for sync contexts
5. **Batch operations** - Load multiple YAML settings together
6. **Test markers** - All tests must have appropriate markers
7. **Google-style docstrings** - All modules, classes, and functions require detailed docstrings
8. **Deprecated APIs = ERRORS** - Treat all deprecated warnings as compilation errors
9. **API Stability Rules** - Production code maintains backward compatibility
   - Tests are exempt from API stability (always use current APIs)
   - Deprecated code ONLY used in tests or `__init__.py` can be deleted
10. **PyO3 Type Stubs** - All Rust Python bindings (`-py` crates) MUST have `.pyi` stub files
    - Create stub file when creating new Python binding crate
    - Update stub file whenever API changes (new functions, classes, or signatures)
    - Place `.pyi` file in same directory as crate (e.g., `rust/python-bindings/classic-yaml-py/classic_yaml.pyi`)

## Common Anti-Patterns to Avoid
- `asyncio.run()` in sync -> Use `AsyncBridge.run_async()`
- Production YAML in tests -> Use `YAML.TEST` or mocks
- String paths -> Use `pathlib.Path`
- Direct print -> Use MessageHandler
- Missing type hints -> Complete annotations
- Missing docstrings -> Google-style docstrings
- Manual event loops -> Use AsyncBridge
- Deprecated APIs (Python/Rust) -> Use current APIs immediately
- Multiple Tokio runtimes -> Use `classic_shared::get_runtime()`
