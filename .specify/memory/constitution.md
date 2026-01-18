<!--
Sync Impact Report
==================
Version change: 0.0.0 → 1.0.0 (Initial ratification)
Modified principles: N/A (initial version)
Added sections:
  - Core Principles (7 principles derived from CLAUDE.md rules)
  - Architecture Standards (hybrid Python-Rust requirements)
  - Development Workflow (TDD, async patterns, documentation)
  - Governance
Removed sections: N/A (initial version)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ (Constitution Check section already present)
  - .specify/templates/spec-template.md ✅ (User scenarios and requirements aligned)
  - .specify/templates/tasks-template.md ✅ (TDD workflow and phase structure compatible)
Follow-up TODOs: None
-->

# CLASSIC Constitution

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

All new features and bug fixes MUST follow TDD methodology using the Red-Green-Refactor cycle:

1. **Red**: Write a failing test first that defines expected behavior
2. **Green**: Write minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green

**Enforcement**:
- Tests MUST be written before implementation code
- Tests MUST fail initially (proving they test something)
- Tests MUST pass both individually and in the full test suite
- Production YAML MUST NEVER be modified in tests (use `YAML.TEST` or mocks)
- Singletons (GlobalRegistry, MessageHandler) MUST be cleared between tests

**Rationale**: TDD ensures code correctness, prevents regressions, and serves as living documentation. The hybrid Python-Rust architecture makes testing even more critical to verify FFI boundaries.

### II. Hybrid Architecture Integrity

CLASSIC uses a three-layer modular Rust architecture delivering 10-150x performance gains:

1. **Foundation Layer**: `classic-shared` (runtime, errors, utilities)
2. **Business Logic Layer**: `-core` crates (Pure Rust - NO PyO3)
3. **Python Bindings Layer**: `-py` crates (PyO3 adapters only)

**Non-Negotiable Rules**:
- **ONE RUNTIME RULE**: All Rust crates MUST use `classic_shared::get_runtime()` to share the global Tokio runtime
- **SEPARATION OF CONCERNS**: Business logic MUST reside in `-core` crates; PyO3 bindings MUST reside in `-py` crates
- **NO MIXED CRATES**: Never combine business logic with PyO3 bindings in the same crate
- All `-py` crates MUST have corresponding `.pyi` stub files for type hints

**Rationale**: Separation enables independent testing, clear dependency graphs, and maintainable PyO3 module registration. Mixing concerns creates circular dependencies and testing nightmares.

### III. Async-First Development

The codebase follows an async-first pattern with clear boundaries:

- **Production CLI code** MUST use async-first pattern with single `asyncio.run()` at entry point
- **AsyncBridge** is ONLY for same-thread GUI contexts and testing
- **Cross-thread workers** (QRunnable, QThread) MUST use `asyncio.run()` (not AsyncBridge)

**Three-Tier Import Classification**:
- **Tier 1 (Core)**: AsyncBridge.py, bridge_helpers.py - Never refactor
- **Tier 2 (Legitimate)**: Same-thread GUI callbacks, test files - Keep as-is
- **Tier 3 (Violation)**: Production CLI using AsyncBridge - MUST be refactored

**Rationale**: AsyncBridge is thread-local and cannot cross thread boundaries. Mixing patterns causes deadlocks and event loop conflicts.

### IV. Code Quality Standards

**Mandatory Requirements**:
- **No print()** - Use MessageHandler (`msg_info()`, `msg_warning()`, `msg_error()`)
- **Use pathlib.Path** - Never string paths
- **UTF-8 encoding** with `errors="ignore"` for file operations
- **Complete type annotations** using Python 3.12+ syntax
- **One class per file** (exceptions: small related helpers)
- **Max 12 branches per function** - Extract methods or use dict mapping

**Documentation**:
- Google-style docstrings MUST be present on all modules, classes, and public functions
- All Rust `pub` items MUST have `///` doc comments
- Missing documentation warnings are treated as errors

**Rationale**: Consistent code quality reduces cognitive load and enables effective code review. MessageHandler ensures proper output handling across GUI/CLI/TUI modes.

### V. API Stability and Deprecation

**Production Code Rules**:
- Maintain API compatibility with deprecation warnings
- Deprecated APIs in production code MUST emit warnings before removal
- Breaking changes require MAJOR version bumps

**Test Code Rules**:
- Tests are EXEMPT from API stability requirements
- Tests MUST always use current APIs, never deprecated ones
- Deprecated code used ONLY in tests or `__init__.py` can be deleted immediately

**Rationale**: Production users need migration paths; tests should validate current behavior, not legacy compatibility shims.

### VI. Simplicity and YAGNI

Avoid over-engineering. Only make changes that are directly requested or clearly necessary:

- **Don't add features** beyond what was asked
- **Don't refactor** surrounding code when fixing a bug
- **Don't add docstrings/comments** to unchanged code
- **Don't add error handling** for impossible scenarios
- **Don't create abstractions** for one-time operations
- **Don't design** for hypothetical future requirements

**Anti-patterns**:
- Backward-compatibility hacks (renaming unused `_vars`, re-exporting types)
- Feature flags or shims when direct changes suffice
- Three similar lines of code is better than a premature abstraction

**Rationale**: Complexity has compound costs. Each unnecessary abstraction increases maintenance burden, obscures intent, and slows onboarding.

### VII. Security-Conscious Development

**OWASP Top 10 Awareness**:
- Be careful not to introduce command injection, XSS, SQL injection vulnerabilities
- Validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees

**Data Handling**:
- Never commit secrets (.env, credentials.json)
- Production YAML files MUST NOT be modified by tests
- FCX mode operates read-only (detects issues but never modifies files)

**Rationale**: CLASSIC analyzes user crash logs which may contain system paths and configuration data. Security-conscious defaults protect user systems.

## Architecture Standards

### Directory Structure

All Rust crates are organized in `rust/` with subdirectories by layer:

```
rust/
├── Cargo.toml                    # Workspace manifest (authoritative)
├── foundation/                   # Foundation Layer
│   ├── classic-shared-core/     # Core runtime, errors, utilities
│   └── classic-shared-py/       # PyO3 bindings for shared
├── business-logic/               # Business Logic Layer (NO PyO3)
│   └── classic-*-core/          # All business logic crates
├── python-bindings/              # Python Bindings Layer
│   └── classic-*-py/            # All binding crates (with .pyi stubs)
└── ui-applications/              # Native Applications
    ├── classic-cli/             # Command-line interface
    ├── classic-tui/             # Terminal UI (Ratatui)
    └── classic-gui-slint/       # Slint GUI
```

### Creating New Crates

1. **Business Logic** (`-core`): Create in `rust/business-logic/`
   - Pure Rust, NO PyO3 dependencies
   - Add to workspace under `# Business Logic` comment

2. **Python Bindings** (`-py`): Create in `rust/python-bindings/`
   - Depends on corresponding `-core` crate
   - MUST create `.pyi` stub file
   - Add to `rebuild_rust.ps1` and `build_all.ps1`

3. **UI Applications**: Create in `rust/ui-applications/`

## Development Workflow

### TDD Workflow

```bash
# 1. Write failing test
uv run pytest tests/path/to/test.py::test_new_feature -v  # MUST fail

# 2. Implement minimal code
# ... write just enough to pass

# 3. Verify test passes
uv run pytest tests/path/to/test.py::test_new_feature -v  # MUST pass

# 4. Verify full test suite (sequential)
uv run pytest  # MUST pass

# 5. Refactor with tests as safety net
```

### Pre-Commit Checklist

Before any commit:
- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run pytest` passes (full test suite)
- [ ] No TODO comments introduced without tracking issue
- [ ] Google-style docstrings on all new code

### Rust Development

```bash
# Lint
cargo fmt --all --manifest-path rust/Cargo.toml -- --check
cargo clippy --workspace --all-targets --manifest-path rust/Cargo.toml -- -D warnings

# Build
./rebuild_rust.ps1              # All crates
./rebuild_rust.ps1 yaml         # Specific crate

# Verify Python integration
uv run python -c "import classic_yaml; print(classic_yaml.__version__)"
```

## Governance

### Constitution Authority

This constitution supersedes all other development practices. When conflicts arise between this document and other guidance, this constitution takes precedence.

### Amendment Process

1. **Proposal**: Document proposed change with rationale
2. **Review**: Evaluate impact on existing code and templates
3. **Migration**: Create migration plan for affected code
4. **Approval**: Obtain maintainer approval
5. **Update**: Increment version per semantic versioning:
   - **MAJOR**: Principle removal or incompatible redefinition
   - **MINOR**: New principle or materially expanded guidance
   - **PATCH**: Clarifications, wording, non-semantic refinements

### Compliance Review

All PRs and code reviews MUST verify:
- TDD workflow followed (failing test → implementation → pass)
- Architecture rules respected (layer separation, runtime sharing)
- Code quality standards met (no print, pathlib usage, type hints)
- Documentation present (Google-style docstrings, Rust doc comments)

### Reference Documents

- `.claude/rules/` - Detailed rules by topic
- `.claude/skills/tdd/SKILL.md` - TDD patterns and examples
- `docs/development/` - Technical guides

**Version**: 1.0.0 | **Ratified**: 2025-01-18 | **Last Amended**: 2025-01-18
