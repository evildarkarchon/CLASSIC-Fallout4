# PRD: Rename `rust/` Directory to `ClassicLib-rs/`

**Version**: 1.0
**Date**: 2026-02-13
**Status**: Draft
**Goal**: Rename the top-level `rust/` directory to `ClassicLib-rs/` for naming consistency with `ClassicLib/`, and update all consumers across the codebase

---

## 1. Executive Summary

The Rust workspace currently lives at `rust/` while the Python library lives at `ClassicLib/`. This PRD defines the rename of `rust/` to `ClassicLib-rs/` to establish a symmetric naming convention: `ClassicLib/` (Python) and `ClassicLib-rs/` (Rust). The rename is purely organizational -- no code logic, APIs, or crate names change.

### Why Rename?

- **Naming symmetry**: `ClassicLib/` and `ClassicLib-rs/` immediately communicate that these are the Python and Rust halves of the same library
- **Convention**: The `-rs` suffix is a well-established Rust ecosystem convention (e.g., `ripgrep` → `rg`, `foo-rs`)
- **Disambiguation**: `rust/` is a generic name that could conflict with tooling expectations (e.g., `rust-analyzer` workspace detection heuristics)

### Scope & Risk

| Metric | Value |
|--------|-------|
| Directory renamed | 1 (`rust/` → `ClassicLib-rs/`) |
| Files with functional path references | ~20 files |
| Total functional `rust/` path occurrences | ~55 |
| Documentation files with references | ~225 files, ~2,035 occurrences |
| Internal Cargo.toml paths affected | 0 (all relative within workspace) |
| Crate names changed | 0 |
| API changes | 0 |
| Risk level | Low (purely mechanical find-and-replace) |

---

## 2. What Does NOT Change

These items are critical to understand -- the rename is shallow:

- **No Cargo crate names change** -- `classic-scanlog-core`, `classic-yaml-py`, etc. all keep their names
- **No Python import names change** -- `import classic_yaml`, `import classic_scanlog`, etc. are unaffected
- **No internal Cargo.toml `path = "..."` dependencies change** -- all ~80+ path dependencies use relative paths within the workspace (e.g., `path = "../../foundation/classic-shared-core"`) which remain correct after the parent directory rename
- **No `.cargo/config.toml` files change** -- they move with the directory automatically
- **No Rust source code changes** -- zero `.rs` files reference the parent directory name
- **No `pyproject.toml` maturin manifest-path** -- confirmed not present; maturin discovers manifests via the build scripts

---

## 3. Inventory of Changes Required

### 3.1 TIER 1: Build-Critical (Would Break CI/Builds)

#### 3.1.1 CI Workflows

**`.github/workflows/ci.yml`** (~20 occurrences)
| Pattern | Example | Count |
|---------|---------|-------|
| `--manifest-path rust/Cargo.toml` | cargo build/test/fmt/clippy commands | 5 |
| `path: rust/target` | GitHub Actions cache paths | 5 |
| `hashFiles('rust/**/*.rs')` | Cache key hash inputs | 5 |
| `working-directory: rust/node-bindings/classic-node` | Bun/NAPI-RS build steps | 4 |
| `rust/target/release/*.dll` | Artifact upload paths | 1+ |
| `rust/python-bindings/*/dist/*.whl` | Wheel artifact paths | 1+ |
| `rust/foundation/*/dist/*.whl` | Wheel artifact paths | 1+ |

**`.github/workflows/benchmarks.yml`** (~4 occurrences)
| Pattern | Example | Count |
|---------|---------|-------|
| `path: rust/target` | Cache path | 1 |
| `hashFiles('rust/**/*.rs')` | Cache key | 1 |
| `path: rust/target/criterion/baseline` | Criterion cache | 2 |

#### 3.1.2 Build Scripts (Root Level)

**`rebuild_rust.ps1`**
- Line 54: `$searchPaths = @("rust/foundation", "rust/python-bindings")`
- → Change to: `@("ClassicLib-rs/foundation", "ClassicLib-rs/python-bindings")`

**`build_all.ps1`**
- Line 181: `if (Test-Path "rust/python-bindings") {`
- Line 192: `$searchPaths = @("rust/foundation", "rust/python-bindings")`
- Line 459: `Write-Host "  cd rust\ui-applications\classic-tui && cargo build --release"`
- → Update all three to `ClassicLib-rs/...`
- Note: Line 257 references `dist-rust\` (output directory, separate concern)

#### 3.1.3 `.gitignore`

7 references across lines 58, 118-120, 149-151, 315:
```
rust/target/                              → ClassicLib-rs/target/
!rust/.cargo/config.toml                  → !ClassicLib-rs/.cargo/config.toml
!rust/ui-applications/classic-gui/.cargo/ → !ClassicLib-rs/ui-applications/classic-gui/.cargo/
rust/clippy_full_report.txt               → ClassicLib-rs/clippy_full_report.txt
rust/clippy_report.txt                    → ClassicLib-rs/clippy_report.txt
rust/CLASSIC_Settings.yaml                → ClassicLib-rs/CLASSIC_Settings.yaml
rust/ui-applications/classic-gui/CLASSIC Data → ClassicLib-rs/ui-applications/classic-gui/CLASSIC Data
```

Also **remove** line 58 `classic-rust/target/` -- this is a stale legacy entry (the `classic-rust/` directory no longer exists).

#### 3.1.4 CMake (C++ Qt 6 GUI)

**`classic-gui-qt6-c++/CMakeLists.txt`** (line 24):
```cmake
# Before:
MANIFEST_PATH ${CMAKE_SOURCE_DIR}/../rust/Cargo.toml
# After:
MANIFEST_PATH ${CMAKE_SOURCE_DIR}/../ClassicLib-rs/Cargo.toml
```

#### 3.1.5 Test Files with Hardcoded Paths

**`tests/test_rust_stubs_unit.py`** (4 occurrences):
```python
# Before:
Path("rust/python-bindings/classic-config-py/classic_config.pyi")
Path("rust/python-bindings/classic-scanlog-py/classic_scanlog.pyi")
# After:
Path("ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi")
Path("ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi")
```

### 3.2 TIER 2: Tooling Scripts (Would Break Developer Workflows)

#### 3.2.1 Profiling Scripts

**`scripts/profile/run_pyspy.ps1`** (line 228):
- `$outputDir = Join-Path $projectRoot "rust/target/profiling/pyspy"`

**`scripts/profile/run_flamegraph.ps1`** (line 121):
- Error message referencing `rust/` directory

#### 3.2.2 Benchmark Scripts

**`scripts/bench/run_benchmarks.ps1`** (lines 70, 115):
- Comment and error message referencing `rust/`

**`scripts/bench/compare_baselines.ps1`** (lines 41, 94, 313):
- Comment, and two `Join-Path` calls: `"../../rust/target/criterion"`

**`scripts/bench/extract_percentiles.py`** (lines 248-249):
- `default=Path("rust/target/criterion")`

**`scripts/bench/cleanup_baselines.py`** (lines 203-204):
- `default=Path("rust/target/criterion")`

#### 3.2.3 Stub Validation Script (Moves with Directory)

**`rust/validate_stubs.py`** → becomes `ClassicLib-rs/validate_stubs.py`
- 3 docstring references to `python rust/validate_stubs.py`
- 1 `--rust-dir` arg help text reference
- These should be updated to reflect the new path

### 3.3 TIER 3: Agent/AI Configuration Files

These files guide AI coding assistants and must be accurate:

| File | Occurrences |
|------|-------------|
| `CLAUDE.md` | 18 |
| `GEMINI.md` | 17 |
| `AGENTS.md` | 17 |
| `.claude/skills/tdd/SKILL.md` | 3 |
| `.claude/skills/rust-crate/SKILL.md` | 12 |
| `.claude/skills/ci-check/SKILL.md` | 9 |
| `.agent/skills/tdd/SKILL.md` | 3 |
| `.agent/skills/rust-crate/SKILL.md` | 12 |
| `.agent/skills/ci-check/SKILL.md` | 9 |
| `.gemini/skills/tdd/SKILL.md` | 3 |
| `.gemini/skills/rust-crate/SKILL.md` | 12 |
| `.gemini/skills/ci-check/SKILL.md` | 9 |
| `.kilocode/skills/tdd/SKILL.md` | 3 |
| `.kilocode/skills/rust-crate/SKILL.md` | 12 |
| `.kilocode/skills/ci-check/SKILL.md` | 9 |
| `.specify/memory/constitution.md` | 7 |

### 3.4 TIER 4: Documentation (Historical/Reference)

~200+ documentation files across `docs/` and `.planning/` contain `rust/` path references. These are historical records (phase plans, audit reports, summaries, verification docs).

**Decision needed**: Update these or leave as historical records?

**Recommendation**: Batch find-and-replace for accuracy, but prioritize only the active documentation:

| Priority | Directory | Files | Est. Occurrences |
|----------|-----------|-------|------------------|
| High | `docs/development/` | ~10 | ~80 |
| High | `docs/guides/` | 3 | ~50 |
| High | `docs/rust/` | 4 | ~30 |
| High | `docs/architecture/` | 3 | ~30 |
| Medium | `docs/prd/` | 2 | ~10 |
| Medium | `docs/audit-reports/` | ~15 | ~80 |
| Low | `.planning/phases/` | ~130 | ~1,500 |
| Low | `.planning/codebase/` | 4 | ~15 |
| Low | `docs/implementation/` | ~8 | ~40 |
| Low | `docs/plans/` | 3 | ~70 |

### 3.5 TIER 5: Python Comments/Docstrings (Non-Breaking)

These reference `rust/` in comments or docstrings but don't affect functionality:

| File | Line | Context |
|------|------|---------|
| `ClassicLib/integration/factory.py` | 9 | Comment: `integration/rust/` |
| `vulture_whitelist.py` | 10 | Comment: `integration/rust/report/` |
| `tests/fixtures/singleton_fixtures.py` | 182 | Docstring: `integration/rust/report/` |
| `tests/rust_integration/parity/test_yaml_parity.py` | 5 | Docstring: `classic-rust/tests/` |
| `tests/rust_integration/parity/test_pattern_matcher_parity.py` | 5 | Docstring: `classic-rust/tests/` |
| `tests/rust_integration/parity/test_mod_detector_parity.py` | 5 | Docstring: `classic-rust/tests/` |
| `tests/rust_integration/parity/test_record_scanner_parity.py` | 5 | Docstring: `classic-rust/tests/` |

Note: These reference `integration/rust/` (a Python subpackage) and `classic-rust/` (a legacy name), NOT the `rust/` top-level directory. They should be reviewed but are a separate concern from this rename.

### 3.6 NOT IN SCOPE

| Item | Reason |
|------|--------|
| `dist-rust/` directory (build output) | Different directory, separate naming concern |
| `rust_extensions/` directory | PyInstaller artifact directory, not the source workspace |
| `ClassicLib/integration/rust/` Python subpackage | Python module path, not the workspace directory |
| `"rust"` as a string value (parser type, test values) | Semantic values, not path references |
| Cargo crate names containing "rust" | Crate identity, not directory paths |
| `pyinstaller_rust_helper.py` filename | Script name, not a path into `rust/` |

---

## 4. Implementation Plan

### Phase 1: Directory Rename (Git Move)

```powershell
git mv rust ClassicLib-rs
```

This single command preserves full git history for all files. Git tracks content, not paths, so `git log --follow` will trace history across the rename.

### Phase 2: Build-Critical Updates (Tier 1)

Update in this order to restore a green build as quickly as possible:

1. `.github/workflows/ci.yml` — all ~20 occurrences
2. `.github/workflows/benchmarks.yml` — all ~4 occurrences
3. `rebuild_rust.ps1` — 1 occurrence
4. `build_all.ps1` — 3 occurrences
5. `.gitignore` — 7 occurrences updated + 1 stale entry removed (`classic-rust/target/`)
6. `classic-gui-qt6-c++/CMakeLists.txt` — 1 occurrence
7. `tests/test_rust_stubs_unit.py` — 4 occurrences

**Verification**: Run `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` and `uv run pytest tests/test_rust_stubs_unit.py` to confirm.

### Phase 3: Tooling Updates (Tier 2)

Update developer workflow scripts:

1. `scripts/profile/run_pyspy.ps1`
2. `scripts/profile/run_flamegraph.ps1`
3. `scripts/bench/run_benchmarks.ps1`
4. `scripts/bench/compare_baselines.ps1`
5. `scripts/bench/extract_percentiles.py`
6. `scripts/bench/cleanup_baselines.py`
7. `ClassicLib-rs/validate_stubs.py` (already moved, update internal references)

### Phase 4: AI/Agent Config Updates (Tier 3)

Update all AI assistant configuration files:

1. `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
2. All skill files across `.claude/`, `.agent/`, `.gemini/`, `.kilocode/`
3. `.specify/memory/constitution.md`
4. Auto-memory files (`C:\Users\evild\.claude\projects\J--CLASSIC-Fallout4\memory\MEMORY.md`)

### Phase 5: Documentation Updates (Tier 4)

Batch find-and-replace across **active** documentation only (`docs/`). Historical `.planning/` phase docs are left as-is -- they are archival records of past work.

```powershell
# Active docs only (NOT .planning/)
Get-ChildItem -Recurse -Include *.md -Path docs/ |
  ForEach-Object { (Get-Content $_) -replace '(?<![a-zA-Z-])rust/(?!extensions)', 'ClassicLib-rs/' | Set-Content $_ }
```

**Caution**: The naive `rust/` replacement will also match strings like `integration/rust/` and `classic-rust/` which are NOT the directory being renamed. The regex above uses a negative-lookbehind `(?<![a-zA-Z-])` and negative-lookahead `(?!extensions)` to avoid these false matches.

### Phase 6: Comments/Docstrings (Tier 5)

Update Python comments and docstrings referencing the directory path. Low priority since these don't affect functionality.

---

## 5. Verification Checklist

After all changes are applied:

- [ ] `cargo build --workspace --manifest-path ClassicLib-rs/Cargo.toml` succeeds
- [ ] `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` passes (303 tests)
- [ ] `cargo clippy --workspace --all-targets --all-features --manifest-path ClassicLib-rs/Cargo.toml` clean
- [ ] `cargo fmt --all --manifest-path ClassicLib-rs/Cargo.toml -- --check` clean
- [ ] `uv run pytest` passes (3,545 tests)
- [ ] `uv run ruff check .` clean
- [ ] `uv run ruff format --check .` clean
- [ ] `.\rebuild_rust.ps1` completes successfully
- [ ] GitHub Actions CI passes on a PR branch
- [ ] `cmake --preset default` in `classic-gui-qt6-c++/` configures correctly
- [ ] No remaining references to bare `rust/` as a top-level directory path (verified by grep)

### Final Grep Verification

```powershell
# Should return ZERO results for the top-level rust/ directory
# (excluding legitimate uses like integration/rust/, classic-rust/, rust_extensions/)
rg '(?<![a-zA-Z_-])rust/' --glob '!ClassicLib-rs/**' --glob '!*.lock' --glob '!target/**'
```

---

## 6. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed reference breaks CI | Low | High | Comprehensive grep verification before merge |
| Git history lost for files | None | N/A | `git mv` preserves history; `--follow` works |
| Developers have local branches referencing old path | Medium | Low | Announce in PR; rebase resolves naturally |
| Third-party tools hardcode `rust/` path | Low | Medium | `rust-analyzer` uses `Cargo.toml` discovery, not directory name |
| Naive find-replace corrupts unrelated strings | Medium | Medium | Use targeted regex (Section 4, Phase 5) |
| Cache invalidation in CI | Certain | Low | Expected: first CI run after merge will rebuild caches |

---

## 7. Commit Strategy

**Single atomic commit** containing:
1. The `git mv rust ClassicLib-rs`
2. All Tier 1-3 path updates
3. AI config updates (Tier 3)
4. Documentation updates (Tier 4-5)

Rationale: A single commit ensures no intermediate state has a broken build. The rename and all consumer updates must land together.

---

## 8. Resolved Decisions

1. **`.planning/` phase docs**: Leave as-is. These are historical records of past work; updating ~1,500 occurrences across ~130 files adds unnecessary churn with no functional benefit.

2. **`dist-rust/` output directory**: Leave as-is. This is a separate naming concern for a build artifact directory and can be addressed independently if desired.

3. **`classic-rust/target/` gitignore entry (line 58)**: **Remove it.** The `classic-rust/` directory no longer exists -- this is a stale legacy entry.
