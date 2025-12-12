# Testing Standards

## Test Organization
- **Structure**: Domain-driven directories in `tests/`
- **File Naming**: `test_<component>_<type>.py` (unit/integration/e2e)
- **Markers**: Required - `@pytest.mark.unit`, `.integration`, `.asyncio`, `.slow`, `.gui`, `.performance`
- **Rust tests**: Place in `tests/rust_integration/` directory (no special marker needed)

## Critical Rules
1. **NEVER modify production YAML** in tests (use `YAML.TEST` or mocks)
2. **NEVER add backward compatibility** to fix tests (update tests to match new API)
3. **Always clear singletons** between tests (GlobalRegistry, MessageHandler)
4. **Use proper async mocking** to avoid unawaited coroutine warnings
5. **Tests are exempt from API stability** - Always use current APIs, never deprecated ones

## Testing Guides
See `docs/` for detailed guides:
- `testing/testing_async_bridge.md` - Async/sync mocking
- `testing/testing_global_registry.md` - Singleton isolation
- `testing/testing_yaml_cache.md` - Config testing
- `testing/test_pollution_guide.md` - Master pollution prevention guide

## Test Anti-Patterns
- Production YAML in tests -> Use `YAML.TEST` or mocks
- Adding backward compatibility to fix tests -> Update tests to match new API
- Missing singleton cleanup -> Always clear GlobalRegistry, MessageHandler between tests
- Unawaited coroutines -> Use proper async mocking patterns
