# Development Standards

## Code Organization

- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** - Use dict mapping, match statements, or extract methods
- **Complete type annotations** - Python 3.12+ syntax

## Python Rules

1. **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
2. **Use pathlib.Path** - Never string paths
3. **UTF-8 encoding** with `errors="ignore"` for file ops
4. **Async-first** - Use AsyncBridge only for same-thread GUI contexts
5. **Google-style docstrings** - Use `/python-docstrings` skill for format
6. **Deprecated APIs = ERRORS** - Use current APIs immediately

## Rust Rules

1. **ONE RUNTIME** - Use `classic_shared::get_runtime()` for Tokio
2. **Business logic separation** - `-core` crates (pure Rust), `-py` crates (PyO3 only)
3. **PyO3 module registration** - `#[pyclass]` only in standalone cdylib modules
4. **Full documentation** - All `pub` items need `///` doc comments
5. **Type stubs required** - All `-py` crates need `.pyi` files

Use `/rust-crate` skill when creating new Rust crates.

## Documentation Requirements

### Python
- Module-level docstring at top of every file
- All public classes, functions, methods documented
- Args, Returns, Raises sections required
- Use `/python-docstrings` skill for complete format

### Rust
- Crate-level `//!` docs in `lib.rs`/`main.rs`
- `///` doc comments on all public items
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/documentation.html)

## Anti-Patterns

| Don't | Do |
|-------|-----|
| `asyncio.run()` in sync code | `AsyncBridge.run_async()` (GUI only) |
| String paths | `pathlib.Path` |
| `print()` | MessageHandler |
| Missing docstrings | Google-style docstrings |
| Multiple Tokio runtimes | `classic_shared::get_runtime()` |
| Mixed business/PyO3 crates | Separate `-core` and `-py` crates |

## References

- `/python-docstrings` skill - Docstring format and templates
- `/rust-crate` skill - Creating new Rust crates
- `/ci-check` skill - Run local CI checks
- `docs/development/` - Detailed development guides
