# Stack Research: Codebase Cleanup & Consolidation Tooling

**Domain:** Hybrid Python-Rust codebase cleanup, dead code removal, and abstraction consolidation
**Researched:** 2026-02-01
**Confidence:** MEDIUM (versions verified from local install; some tool capabilities from training data)

## Context

This research covers tooling for cleaning up a mature hybrid Python 3.12+ / Rust codebase with PyO3 bindings. The goal is removing dead code, duplicate logic, overlapping abstractions, and preparing for progressive Rust migration. This is NOT about building new features -- it is about reducing what exists.

## Already Installed (Verified)

These tools are already in the project and their versions are confirmed from `uv pip list`:

| Tool | Installed Version | Relevant Cleanup Capabilities |
|------|-------------------|-------------------------------|
| ruff | 0.14.14 | F401 (unused imports), F841 (unused variables), ARG (unused arguments), UP (modernization) |
| pyright | 1.1.408 | Unreachable code detection, type narrowing reveals dead branches |
| coverage | 7.13.2 | Branch coverage identifies untouched code paths |
| pytest-cov | 7.0.0 | Coverage integration with test suite |
| mypy | (in dev deps) | Cross-reference with pyright for dead code via type errors |
| pylint | (in dev deps) | Additional dead code checks (unused-wildcard-import, etc.) |

**Rust workspace** already has `[workspace.lints.rust] unused = "deny"` which catches unused functions, imports, variables at compile time.

## Recommended Stack

### Tier 1: Python Dead Code Detection (Use These)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| ruff (F-rules + ARG) | 0.14.14 (installed) | Unused imports, variables, arguments | Already configured and running. F401, F841, ARG rules catch surface-level dead code. Project already has these active in production code. | HIGH |
| vulture | 2.14+ | Deep dead code detection | Dedicated dead code finder. Unlike ruff, vulture performs whole-program analysis -- it tracks which functions/classes/variables are DEFINED but never USED across the entire codebase. Ruff only catches unused within a single file. Vulture finds unused functions, methods, classes, attributes, and unreachable code. | MEDIUM (version from training) |
| coverage (branch mode) | 7.13.2 (installed) | Identify untested/unreachable code | Already configured with `branch = true`. Run a comprehensive test suite, then examine uncovered lines. Code that is never covered by any test is a candidate for dead code. The `--cov-report=html` output makes visual identification easy. | HIGH |
| pyright (strict mode) | 1.1.408 (installed) | Unreachable code warnings | Already in strict mode. `reportUnreachable` diagnostic flags code after early returns, impossible type narrowings, etc. This catches dead BRANCHES that static analysis alone misses. | HIGH |

### Tier 2: Rust Dead Code & Dependency Detection (Use These)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| cargo clippy | (bundled with rustup) | Lint warnings including dead code | Already available. Key lints: `dead_code`, `unused_imports`, `unused_variables`. The workspace `unused = "deny"` already enforces this. Add `clippy::all` and `clippy::pedantic` for deeper analysis. | HIGH |
| cargo-machete | 0.7+ | Find unused Cargo dependencies | Fast, heuristic-based approach that greps source files for dependency usage. Does NOT require nightly. Runs in seconds even on large workspaces. Better choice than cargo-udeps for this project because it works on stable Rust. | MEDIUM (version from training) |
| cargo-udeps | 0.1.x | Find unused Cargo dependencies (precise) | More accurate than cargo-machete because it uses actual compiler data, but REQUIRES nightly Rust. Use as a secondary verification tool, not primary. Run occasionally for validation. | MEDIUM (version from training) |

### Tier 3: Cross-Language Duplicate Detection (Manual + Scripted)

| Approach | Purpose | Why Recommended | Confidence |
|----------|---------|-----------------|------------|
| Coverage-guided audit | Find Python code that has Rust equivalents | Run tests with coverage. Python modules that have Rust `-core` equivalents but still show as "covered" indicate the Python fallback is still the active path. Python code with 0% coverage in modules that have Rust equivalents is dead fallback code. | HIGH |
| Import graph analysis (custom script) | Map which Python modules import which | Use `importlib` or AST parsing to build a dependency graph. Nodes with zero incoming edges (except entry points) are dead modules. Several small Python scripts can do this with `ast.parse()`. | HIGH |
| grep-based cross-reference | Find Python functions duplicated in Rust | For each Rust `-core` crate, list its public API. Then grep the Python codebase for equivalent function names. Where both exist and the Rust version is active, the Python version is dead code. | HIGH |

### Tier 4: Structural Analysis Tools (Supporting)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| pytest --dead-fixtures | (built into pytest) | Find unused test fixtures | `pytest --collect-only -q` can reveal fixtures that no test uses. Important because this project has centralized fixtures in `tests/fixtures/` that may have accumulated dead entries. | HIGH |
| pylint | (installed) | Additional dead code checks | Catches some patterns vulture misses: unused-wildcard-import, pointless-statement, unnecessary-pass. Overlaps with ruff but provides a second opinion. | HIGH |
| pipdeptree / uv tree | (available via uv) | Python dependency tree | `uv pip tree` shows the full dependency graph. Identifies unused Python packages in `[project.dependencies]`. | HIGH |

## Installation

```bash
# New tools to add (not currently in project)
uv add --dev vulture

# Rust tools (install globally via cargo)
cargo install cargo-machete

# Optional: for precise Rust dep checking (needs nightly)
cargo install cargo-udeps
```

## Recommended Ruff Configuration Changes for Cleanup

The project already has an extensive ruff config. For the cleanup phase, temporarily enable additional rules:

```toml
# Add to extend-select during cleanup phase:
extend-select = [
    # ... existing rules ...
    "F811",   # Redefinition of unused name (find shadowed dead code)
    "ERA",    # Commented-out code detection (eradicate)
]
```

The `ERA` (eradicate) ruleset is particularly valuable for cleanup -- it finds commented-out code blocks that should be deleted rather than left rotting in the codebase. After cleanup is complete, you can decide whether to keep ERA active permanently.

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| vulture | dead (Python package) | dead is unmaintained since ~2020. Vulture is actively maintained and more accurate. |
| vulture | pylint dead-code checks | pylint catches some dead code but not whole-program unused analysis. Use both -- they are complementary. |
| cargo-machete (primary) | cargo-udeps (primary) | cargo-udeps requires nightly which adds friction to the workflow. cargo-machete works on stable and is faster. Use udeps as occasional validation. |
| Custom scripts for cross-lang | No automated tool exists | There is no off-the-shelf tool that finds duplicate Python/Rust implementations in a PyO3 project. This is a manual audit aided by coverage data and grep. |
| ruff ERA | manual grep for comments | ERA is automated and integrated into the existing ruff workflow. Manual grep is error-prone. |
| pipdeptree/uv tree | pip-autoremove | pip-autoremove modifies the environment. uv tree is read-only and safer. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| autoflake | Superseded by ruff. Ruff's F401 and F841 do exactly what autoflake does, faster, and is already configured. | ruff (F401, F841) |
| pyflakes standalone | Ruff includes pyflakes rules (the F prefix). Running pyflakes separately is redundant. | ruff |
| isort standalone | Ruff includes isort rules (I prefix). Already configured. | ruff (I rules) |
| black | Ruff includes formatting. Already configured with `ruff format`. | ruff format |
| flake8 | Ruff is a drop-in replacement for flake8 with better performance. | ruff |
| bandit standalone | If you want security checks, use ruff S rules. Not needed for cleanup milestone. | Defer; enable ruff S-rules later |
| Large-scale automated refactoring tools (rope, bowler) | These rewrite code automatically. For a cleanup milestone, MANUAL review of each removal is safer. Automated refactoring risks breaking the Python-Rust boundary. | Manual removal with test verification |
| cargo-bloat | Measures binary size, not dead code. Different concern. | clippy + cargo-machete for dead code |

## Workflow: How to Use These Tools Together

The cleanup stack works in layers, from broadest to most specific:

### Layer 1: Static Analysis (find candidates)
```bash
# Python dead code candidates
uv run vulture ClassicLib/ CLASSIC_*.py --min-confidence 80
uv run ruff check . --select F401,F841,ARG,ERA

# Rust dead code candidates
cargo clippy --workspace -- -W clippy::all
cargo machete
```

### Layer 2: Coverage Analysis (confirm dead code)
```bash
# Run full test suite with coverage
uv run pytest -n auto --cov --cov-report=html

# Examine htmlcov/ -- modules with 0% coverage are prime deletion candidates
# Modules with partial coverage need line-by-line review
```

### Layer 3: Cross-Language Audit (find duplicates)
```bash
# For each Rust -core crate, check if Python equivalent still exists and is used
# Compare: rust/business-logic/classic-yaml-core/ vs ClassicLib/yaml_operations.py (or equivalent)
# If Rust version is active (imported and tested), Python version may be dead fallback code

# Dependency tree analysis
uv pip tree --depth 2
```

### Layer 4: Validate Removals (test after each removal)
```bash
# After removing dead code, run full test suite
uv run pytest -n auto
# Type check
uv run pyright
# Lint
uv run ruff check .
```

## Version Compatibility

| Tool | Compatible With | Notes |
|------|-----------------|-------|
| ruff 0.14.x | Python 3.12-3.14, pyproject.toml | Fully integrated already |
| vulture 2.x | Python 3.8+ | Add as dev dependency, no config conflicts |
| pyright 1.1.x | Python 3.12+ strict mode | Already configured |
| coverage 7.x | Python 3.12+, pytest-cov 7.x | Already configured with branch coverage |
| cargo-machete | Stable Rust, Cargo workspaces | Works with workspace Cargo.toml |
| cargo-udeps | Nightly Rust only | Optional; do not add to CI unless nightly is available |

## Confidence Notes

| Area | Confidence | Reasoning |
|------|------------|-----------|
| Already-installed tools (ruff, pyright, coverage) | HIGH | Versions verified from `uv pip list` output; configs read from pyproject.toml |
| Ruff rule capabilities (F401, F841, ARG, ERA) | HIGH | Rules are documented in project config and standard ruff behavior |
| Vulture capabilities | MEDIUM | Known from training data. Version may have advanced since. Core functionality (whole-program dead code detection) is stable and well-established. |
| cargo-machete vs cargo-udeps tradeoffs | MEDIUM | Known from training data. Machete's stable-Rust advantage and speed are well-documented in the Rust ecosystem. |
| Cross-language audit approach | HIGH | This is methodology, not tool-dependent. Coverage data and grep are reliable regardless of versions. |
| "What NOT to use" recommendations | HIGH | Tool supersession (autoflake->ruff, pyflakes->ruff) is well-established and unlikely to have changed. |

## Key Insight for Roadmap

The project already has 80% of the cleanup tooling installed and configured. The main gaps are:

1. **vulture** -- needs to be added as a dev dependency (one command)
2. **cargo-machete** -- needs to be installed (one command)
3. **Cross-language audit process** -- no tool exists; needs custom scripted workflow
4. **ERA rules in ruff** -- just a config change to enable commented-out code detection

The cleanup milestone is primarily a PROCESS problem (which code to remove, in what order, with what validation), not a TOOLING problem. The tools are mature and available.

---
*Stack research for: Hybrid Python-Rust codebase cleanup and consolidation*
*Researched: 2026-02-01*
