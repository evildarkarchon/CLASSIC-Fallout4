# Task Completion Checklist for CLASSIC-Fallout4

## Before Committing Any Changes

### 1. Code Quality Checks
```bash
# Format code with Ruff
uv run ruff format .

# Check and fix linting issues
uv run ruff check . --fix

# Run type checking
uv run mypy .
uv run pyright
```

### 2. Test Execution
```bash
# Run quick unit tests first
uv run python -m pytest -n 4 -m "unit and not slow" --maxfail=3

# If changes affect core functionality
uv run python -m pytest tests/core/ -n 4

# For async changes
uv run python -m pytest -n 4 -m "async_test"

# Full test suite before major commits
uv run python -m pytest tests/ -n 4
```

### 3. Documentation Updates
- Update docstrings for new/modified functions
- Update CLAUDE.md if architecture changes
- Add type hints for all new code
- Update test documentation if test patterns change

### 4. Specific Checks by Change Type

#### For New Features
- [ ] Write tests FIRST (TDD approach)
- [ ] Add comprehensive unit tests
- [ ] Add integration tests if applicable
- [ ] Ensure MessageHandler is used for all output
- [ ] Use AsyncBridge for any sync/async bridging
- [ ] Follow one-class-per-file rule

#### For Bug Fixes
- [ ] Write a test that reproduces the bug
- [ ] Fix the bug
- [ ] Verify test now passes
- [ ] Check for similar issues elsewhere
- [ ] Add regression test marker

#### For Refactoring
- [ ] Maintain backward compatibility
- [ ] Add deprecation warnings if needed
- [ ] Update re-exports in __init__.py
- [ ] Ensure all existing tests pass
- [ ] Check file size limits (500 lines soft, 550 hard)

#### For Async Code
- [ ] Use FileIOCore for file operations
- [ ] Use AsyncBridge.get_instance().run_async()
- [ ] Never use asyncio.run() directly
- [ ] Add async test markers
- [ ] Test concurrent operations

#### For Test Changes
- [ ] Keep test files under 300 lines
- [ ] Place in appropriate subdirectory
- [ ] Never modify production YAML
- [ ] Use tmp_path for test files
- [ ] Add appropriate markers

### 5. Performance Considerations
- [ ] Use batch operations for multiple YAML settings
- [ ] Add performance monitoring for critical paths
- [ ] Use connection pooling for database operations
- [ ] Profile if adding new async operations

### 6. Final Validation
```bash
# Run pre-commit hooks
uv run pre-commit run

# Check test coverage
uv run python -m pytest --cov=. --cov-report=term

# Verify no print statements added
grep -r "print(" ClassicLib/ --include="*.py"
```

### 7. Git Operations
```bash
# Check status
git status

# Review changes
git diff

# Stage changes
git add -p  # Interactive staging

# Commit with descriptive message
git commit -m "type: Brief description

Detailed explanation if needed"
```

## Common Issues to Check

- ❌ No print() statements (use MessageHandler)
- ❌ No string paths (use pathlib.Path)
- ❌ No missing type annotations
- ❌ No unused imports
- ❌ No direct asyncio.run() calls
- ❌ No modifications to production YAML in tests
- ❌ No files over 550 lines
- ❌ No test files over 300 lines

## Notes
- Always run tests in terminal (VS Code test tool has issues)
- Use -n 4 or -n auto for parallel test execution
- If adding to MainWindow, consider using Mixin instead
- API compatibility is critical - provide deprecation paths
