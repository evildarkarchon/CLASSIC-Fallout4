---
phase: 03-python-tier-collapse
plan: 09a
subsystem: binding-parity
tags: [python, pyo3, parity-gate, tier1-promotion, multi-owner, runtime-coverage]

# Dependency graph
requires:
  - phase: 03-python-tier-collapse
    provides: Plan 08 enrolled classic_shared (61) + classic_file_io (95) as tier1 owners; baseline at 505 tier1Mappings
  - phase: 03-python-tier-collapse
    provides: Plans 05-07 enrolled scanlog (227) + config (43) + version_registry (59) as tier1 owners
provides:
  - 14 new tier1-enrolled owner modules (scangame, path, constants, message, database, resource, xse, settings, yaml, registry, web, version, perf, update)
  - 593 net new tier1Mappings (505 pre-09a -> 1098 post-09a)
  - 4 scanlog method residuals promoted (CrashgenVersion.to_tuple, LogParser.find_errors, PatternMatcher.find_all, PatternMatcher.has_match)
  - 15 new runtime_coverage_registry selectors (14 owners + python-tier1-scanlog-wave10-residuals) with correct 64-char SHA-256 hashes via imported _stable_id_hash
  - python-tier2-scanlog-runtime retired (M12)
  - 3 Rule 2 inline stub additions (classic_settings validators) + 16 dunder stubs (__str__ / __repr__ for 8 enum classes)
  - 19 Rule 2 inline contract rows (dunder methods + settings validators) discovered after stub additions
  - _build_plan09a_rows.py reproducible multi-owner row builder with three-branch wrapper check (C1 fix) and imported _stable_id_hash (C2 fix)
  - _scaffold_plan09a_tests.py scaffold helper (M10 fix)
  - 154 hand-verified D-07 smoke tests in test_promoted_residuals_smoke.py
  - 03-09a-CONSTRUCTOR-INVENTORY.md, 03-09a-STUB-AUDIT.md, 03-09a-RESIDUAL-INVENTORY.md, 03-09a-DRY-RUN-PROJECTION.md (4 Task 0 artifacts)
affects: [plan-09b, plan-10, phase-06-cleanup]

# Tech tracking
tech-stack:
  added: [mypy (for --strict stub validation in verification chain)]
  patterns:
    - "Multi-owner enrollment via generalized row builder (_build_plan09a_rows.py); Plan 08 two-owner template scales to N owners"
    - "Three-branch wrapper check (rust_unmapped / method / top-level) with .pyi stub fallback for TypedDict-only exports"
    - "Imported _stable_id_hash from tools.binding_parity_runtime_coverage (NEVER reimplemented) for registry hash consistency"
    - "Same-row-dedup across all 14 owners (159 dedup savings where a Python class name matches its Rust anchor symbol)"
    - "@rust proxy row pairing with nearest Python anchor (class > sibling function > first surface export) for owners without classes (version)"
    - "Pitfall 2 submodule-anchor fallback: when Python wrapper function has no -core crate equivalent, anchor on nearest class in the same .rs source file"
    - "Parser-garbage exclusion for pre-existing generate_baseline.py comment-parser bug (2 path symbols)"

key-files:
  created:
    - .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
    - .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md
    - .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
    - .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md
    - .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py
    - .planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py
    - ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
  modified:
    - docs/implementation/python_api_parity/baseline/parity_contract.json (505 -> 1098 tier1Mappings)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (+15 selectors, -1 retired)
    - ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi (+6 dunder stubs)
    - ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi (+4 dunder stubs)
    - ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi (+4 dunder stubs)
    - ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi (+2 dunder stubs)
    - ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi (+3 validator function stubs)

key-decisions:
  - "PATHLESS OWNERS: for function-only owners (version, registry, settings) the @rust proxy falls back to first function row or first surface export; no synthetic anchor classes invented"
  - "ROW-BUILDER FALLBACK CHAIN: find_rust_anchor_for_class prefers same-name core symbol > submodule anchor in same .rs file > any submodule class in core (eliminates Pitfall 2 false negatives)"
  - "DUNDER STUB ADDITIONS SURFACE 19 NEW GAPS: stub completeness fix created follow-on parity gaps that must be picked up in the same plan via Rule 2 inline fixup (contract row addition)"
  - "SETTINGS VALIDATOR FUNCTIONS anchor on `validators` module (the matching -core module name, not a class)"
  - "PARSER-GARBAGE EXCLUSION for 2 pre-existing classic-path-core symbols where generate_baseline.py's pub-use block parser picks up inline Rust comments; filed as known generate_baseline.py bug for later fix"
  - "154 SMOKE TESTS (vs plan's 80-130 range) — comprehensive per-class + per-enum-variant coverage at ~1 test per residual class"

patterns-established:
  - "N-owner enrollment: Plan 08's two-owner template generalizes to N owners via OWNER_ORDER + single already_covered_rust_symbols set tracked across all owners"
  - "Three-branch wrapper check (C1 fix): gap_type=='rust_unmapped' skip wrapper check; '.' in export_path verify class wrapper; else top-level search + .pyi fallback"
  - "Imported _stable_id_hash (C2 fix): sys.path insert 'tools', 'from binding_parity_runtime_coverage import _stable_id_hash', never reimplement"
  - "Rule 2 inline fixup for stub-discovery cascades: when adding stubs surfaces new contract row gaps, run an inline fixup script that anchors the new rows on the canonical parent class / sibling function and commits atomically with the stub additions"

requirements-completed: [PYT-02, PYT-04, PYT-05, PYT-06]

# Metrics
duration: 2h 15m
completed: 2026-04-09
---

# Phase 03 Plan 09a: A10 Residual Promotion Summary

**Final binding-enrollment plan for Phase 3: promoted 593 net tier1 rows across 14 new owner modules + 4 scanlog method residuals in one atomic plan, raising the Python tier1 contract from 505 to 1098 rows with zero parity drift and zero runtime coverage mismatches.**

## Performance

- **Duration:** ~2h 15m (including Python rebuild cycles and iterative row-builder refinement)
- **Started:** 2026-04-09T04:00:00Z (approximate)
- **Completed:** 2026-04-09T06:15:00Z (approximate)
- **Tasks:** 4 (inventory/audit, row authoring, test authoring, verification)
- **Files modified:** 15+ (7 new artifacts, 1 contract, 1 registry, 5 stubs, 1 smoke test, 1 helper, baseline/mirror refreshes)

## Accomplishments

- **593 net new tier1Mappings enrolled** across 14 newly-supported owner modules plus 4 scanlog method residuals, bringing Python tier1 contract total from 505 to 1098.
- **733 live residuals classified and routed** via a generalized multi-owner row builder with three-branch wrapper check; 735 original residuals minus 2 parser-garbage entries classified cleanly without landing in BLOCKERS.md.
- **15 new runtime_coverage_registry selectors** authored with full 64-char SHA-256 hashes via `_stable_id_hash` imported directly from `tools/binding_parity_runtime_coverage.py`; `registry_mismatch_total == 0` at plan close.
- **Plan 08 integrity preserved**: `file_io=95` and `shared=61` selector counts and 64-char hashes unchanged.
- **python-tier2-scanlog-runtime retired** (M12): stale Tier-2 entry deleted because its 4 method bindings are now covered by `python-tier1-scanlog-wave10-residuals`.
- **154 hand-verified D-07 smoke tests** added in `test_promoted_residuals_smoke.py`, each constructing an instance (or referencing an enum variant) and calling at least one real method; 154/154 pass.
- **Plan 09b starting point recorded**: `deferred_total = 1008` post-09a (matches dry-run projection). Plan 09b empties `deferred_runtime_backlog.json::entries` to drive `deferred_total` to 0.
- **Full 5-step verification chain green**: parity gate pass, validate_stubs 18/18 crates clean, rebuild_rust 19/19 wheels, pytest 391/391, mypy --strict 15/15 stubs.

## Task Commits

Each task was committed atomically using `--no-verify` (parallel executor convention):

1. **Task 0 Step 2: Constructor inventory** — `627044d1` (docs)
2. **Task 0 Step 3: Pre-task stub audit** — `b2369a7a` (docs)
3. **Task 0 Step 4: Helper scaffold + residual inventory** — `45fb5b19` (docs)
4. **Task 0 Step 5: Baseline refresh + artifacts mirror** — `99f25698` (chore)
5. **Task 0 Step 6: Dry-run projection** — `d99a6c34` (docs)
6. **Task 1: 574 residual rows + 4 scanlog method residuals + 5 Rule 2 stub additions** — `0d1d3705` (feat)
7. **Task 2: 154 per-class smoke tests (D-07)** — `6987a1bd` (test)
8. **Task 3: 15 runtime_coverage_registry selectors + Rule 2 inline fixup for 19 dunder/validator rows** — `5c18dc19` (feat)
9. **Task 4: Final baseline refresh** — `1528e596` (feat)

## Files Created/Modified

### Created (Plan 09a artifacts)

- `.planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md` — Per-owner PyClass inventory with verified `#[new]` constructor signatures (source of truth for smoke test arguments)
- `.planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md` — Pre-task Rule 2 audit documenting M11 validate_stubs scope caveat (foundation/classic-shared-py excluded)
- `.planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md` — 733 residuals classified by owner with wrapper-check reasons
- `.planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md` — Empirical post-09a/post-09b `deferred_total` projection documenting Plan 09b ownership of the backlog emptying step (C3 outcome)
- `.planning/phases/03-python-tier-collapse/_build_plan09a_rows.py` — Reproducible multi-owner row builder with three-branch wrapper check, imported `_stable_id_hash`, submodule anchor fallback, parser-garbage filter
- `.planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py` — Scaffold helper header (M10 fix)
- `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` — 154 D-07 smoke tests across 14 owners + 4 scanlog method residuals

### Modified (contract + stubs)

- `docs/implementation/python_api_parity/baseline/parity_contract.json` — 505 -> 1098 tier1Mappings
- `docs/implementation/python_api_parity/baseline/parity_diff_report.{json,md}` — regenerated
- `docs/implementation/python_api_parity/baseline/python_api_surface.json` — regenerated (picks up new stubs)
- `docs/implementation/python_api_parity/baseline/rust_api_surface.json` — regenerated
- `docs/implementation/python_api_parity/baseline/runtime_coverage_summary.{json,md}` — regenerated
- `ClassicLib-rs/python-bindings/parity-artifacts/*` — mirror refresh (9 files)
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — +15 selectors, -1 retired entry
- `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi` — +3 validator function stubs (`validate_settings_structure`, `validate_setting_value`, `coerce_setting_value`)
- `ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi` — +6 `__str__`/`__repr__` stub pairs (YamlFile, GameId, Fallout4Version)
- `ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi` — +4 dunder stubs (ResourceType, ResourceInfo)
- `ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi` — +4 dunder stubs (XseType, XseInfo)
- `ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi` — +2 dunder stubs (ModSite)

## Per-owner row breakdown (Task 1 + Task 3 Rule 2 fixup)

| Owner | Rows added | Of which @rust proxies | Notes |
|-------|-----------:|----------------------:|-------|
| scangame | 172 | ~36 | Largest owner; 43 classes + 73 methods + 18 functions + same-row dedup |
| path | 72 | ~20 | 7 classes + 33 methods + 1 function + rust-only re-exports; 2 parser-garbage filtered |
| constants | 46 | ~24 | 3 classes + 24 methods + 1 function + 30 rust-only (16 deduped with class anchors) + 6 dunder stubs |
| message | 46 | ~8 | 4 classes + 32 methods + 3 functions + rust-only re-exports |
| database | 44 | ~10 | 1 class + 22 methods + 6 functions + rust-only constants (BATCH_CACHE_TTL_SECS, etc.) |
| resource | 36 | ~10 | 2 classes + 18 methods + 6 functions + 4 dunder stubs |
| xse | 36 | ~10 | 2 classes + 17 methods + 4 functions + 4 dunder stubs |
| yaml | 31 | ~25 | 2 classes + 12 methods + 23 rust-only (most deduped on YamlOperations) |
| settings | 28 | ~20 | 1 class + 12 functions + 25 rust-only (mostly deduped) + 3 Rule 2 validator stubs |
| web | 23 | ~13 | 1 class + 6 methods + 7 functions + 15 rust-only + 2 dunder stubs |
| registry | 20 | ~18 | 1 class + 18 functions + 18 rust-only (heavy dedup) |
| version | 15 | ~4 | 0 classes + 11 functions + 16 rust-only (heavy dedup; anchored on first function) |
| perf | 10 | ~3 | 2 classes + 3 methods + 5 functions + 6 rust-only |
| update | 10 | ~6 | 3 classes + 5 methods + 6 rust-only |
| scanlog (method residuals) | 4 | 0 | CrashgenVersion.to_tuple, LogParser.find_errors, PatternMatcher.find_all/has_match |
| **TOTAL** | **593** | — | 574 from Task 1 + 4 scanlog methods + 19 from Task 3 Rule 2 fixup = 593 |

Same-row dedup savings: **159 rows** skipped via `already_covered_rust_symbols` (Python class name matches Rust anchor symbol; both gap types satisfied by one row).

## Runtime coverage selectors (14 new + 1 wave10 + 1 updated)

| Selector | contractCount | contractIdsHash (first 16 chars) |
|----------|-------------:|----------------------------------|
| `python-tier1-scangame` | 172 | `9a2359a3aba879bf...` |
| `python-tier1-path` | 72 | `b38945a95f98447f...` |
| `python-tier1-constants` | 46 | `cfce5b356c3aaa78...` |
| `python-tier1-message` | 46 | `7697bca357a98b64...` |
| `python-tier1-database` | 44 | `5cc9a223e7f0758a...` |
| `python-tier1-resource` | 36 | `35c75f90d701dafc...` |
| `python-tier1-xse` | 36 | `140099c34d2148b8...` |
| `python-tier1-settings` | 28 | `e3ebdf7fb76fe709...` |
| `python-tier1-yaml` | 31 | `8423af086b9308df...` |
| `python-tier1-registry` | 20 | `ea1cd78a10bd6405...` |
| `python-tier1-web` | 23 | `f0813870fa267200...` |
| `python-tier1-version` | 15 | `81a3f22383497f2e...` |
| `python-tier1-perf` | 10 | `787637e8ae3e680f...` |
| `python-tier1-update` | 10 | `b22849974bb596d0...` |
| `python-tier1-scanlog-wave10-residuals` | 4 | `42c5d63ff1695bd4...` |
| `python-tier1-scanlog` (updated) | 251 | `8012b970e781c186...` |

All hashes are 64-char lowercase SHA-256 via imported `_stable_id_hash` (C2 fix verified: `registry_mismatch_total == 0`).

## Plan 08 integrity preserved

| Selector | Pre-09a | Post-09a | Hash Change |
|----------|--------:|---------:|:-----------:|
| `python-tier1-file_io` | 95 | 95 | unchanged |
| `python-tier1-shared` | 61 | 61 | unchanged |

## 5-step verification chain

| Step | Command | Result |
|------|---------|:------:|
| 1 | `check_parity_gate.py --repo-root .` | PASS |
| 2 | `validate_stubs.py --fail-on-warnings` | PASS (18/18 crates, 0 errors, 0 warnings) |
| 3 | `rebuild_rust.ps1 -Target python` | PASS (19/19 wheels) |
| 4 | `pytest ClassicLib-rs/python-bindings/tests -q` | PASS (391/391 tests) |
| 5 | `mypy --strict` on 15 touched stubs | PASS (no issues found) |

## Post-09a metrics (recorded for Plan 09b cross-check)

```json
{
  "tracked_surface_total": 2272,
  "runtime_verified_total": 1264,
  "contract_mapped_total": 0,
  "deferred_total": 1008,
  "newly_uncovered_total": 0,
  "tier1_contract_total": 1098,
  "tier1_missing_runtime_total": 0,
  "registry_mismatch_total": 0
}
```

**Key numbers for Plan 09b:**
- `tier1_contract_total = 1098` (exact post-09a figure for 09b's Task 1 cross-check)
- `deferred_total = 1008` (starting number Plan 09b Task 3 must drive to 0 by emptying `deferred_runtime_backlog.json::entries`)
- `newly_uncovered_total = 0` (Plan 09a Task 3 Rule 2 fixup closed the 19-item gap that appeared after stub additions)
- `registry_mismatch_total = 0` (C2 fix empirically validated — 64-char hashes match)

## Decisions Made

1. **Three-branch wrapper check with .pyi fallback** (C1 fix): The initial three-branch check (rust_unmapped/method/top-level) raised BLOCKERS.md with 2 entries — `SettingsCacheStats` and `YamlCacheStats`, which are declared as `TypedDict` in the `.pyi` stub files, NOT as `#[pyclass]` in `.rs` source. Added BRANCH 3b `.pyi` stub-class fallback to resolve. Empirically verified: 733/735 residuals classified without BLOCKERS, 2 parser-garbage excluded silently.

2. **Imported `_stable_id_hash` from live tooling** (C2 fix): `_build_plan09a_rows.py` does `sys.path.insert(0, 'tools')` + `from binding_parity_runtime_coverage import _stable_id_hash`. Generated 15 selectors all with 64-char hashes matching the live algorithm. `registry_mismatch_total == 0` at close.

3. **Submodule anchor fallback for Pitfall 2** (new pattern generalization): For free functions whose name isn't in the `-core` crate's rust_api_surface (e.g., scangame's `scan_all_ba2_archives`, `process_logs`, `parse_wrye_report` which are implemented only in `-py`), the row builder anchors on the nearest class in the same `.rs` source file that IS in core. This routes 40+ scangame wrapper functions to the right core type without requiring pub-use additions to the core crate.

4. **Pathless-owner fallback chain for @rust proxy rows**: For owners with NO Python classes (version, registry), @rust proxy rows fall back to (a) first function row > (b) first surface export > (c) rust symbol itself. This avoids the `version.lib.PeVersionError@rust` null pythonExportPath failure seen during iteration.

5. **Rule 2 inline fixup for stub-discovery cascade**: Adding `validate_settings_structure` etc. to the settings stub and adding `__str__`/`__repr__` to 8 enum classes caused the python_api_surface parser to pick up 19 new entries. Since these were added to close the first Rule 2 stub audit holes, they count as stub-cascade items that must be promoted in the same plan. Fixed inline in Task 3 via `_tmp_inline_fixup.py` which anchors each new row on the canonical parent class (for dunder methods) or the `validators` sibling (for settings functions). Rule 2 fix is atomic with the Task 3 registry update commit.

6. **154 smoke tests vs 80-130 plan estimate**: Comprehensive per-class + per-enum-variant coverage ended up at ~1 test per residual class plus additional enum-variant probes. All 154 pass; file is 989 lines. D-07 enforcement: every test constructs an instance or references an enum variant and calls at least one real method.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added 3 settings validator function stubs**
- **Found during:** Task 1 validate_stubs.py re-audit (after contract expansion)
- **Issue:** `classic_settings.pyi` was missing stub entries for `validate_settings_structure`, `validate_setting_value`, `coerce_setting_value` — these functions exist in the `-py` crate's `lib.rs` at L463/501/537 but had no Python type stubs, causing `validate_stubs.py --fail-on-warnings` to exit 1 with 3 ERRORS once the settings owner was enrolled as tier1.
- **Fix:** Added three `def` stub entries to `classic_settings.pyi` with full TSDoc comments mirroring the Rust docstrings.
- **Files modified:** `ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi`
- **Verification:** `validate_stubs.py --fail-on-warnings` 0 errors post-fix
- **Committed in:** `0d1d3705` (Task 1 commit)

**2. [Rule 2 - Missing Critical] Added 16 `__str__`/`__repr__` dunder stubs for 8 enum classes**
- **Found during:** Task 1 validate_stubs.py re-audit
- **Issue:** 8 classes across classic_constants (YamlFile/GameId/Fallout4Version), classic_resource (ResourceType/ResourceInfo), classic_xse (XseType/XseInfo), classic_web (ModSite) have `__str__` and `__repr__` implementations in their Rust `#[pymethods]` blocks but the .pyi stubs didn't declare them, causing 16 `validate_stubs.py --fail-on-warnings` WARNINGs.
- **Fix:** Added minimal `def __str__(self) -> str:` and `def __repr__(self) -> str:` stubs for each of the 8 classes (16 new stub entries total).
- **Files modified:** `classic_constants.pyi`, `classic_resource.pyi`, `classic_xse.pyi`, `classic_web.pyi`
- **Verification:** `validate_stubs.py --fail-on-warnings` 0 warnings post-fix
- **Committed in:** `0d1d3705` (Task 1 commit)

**3. [Rule 2 - Missing Critical] Added 19 tier1 contract rows for stub-cascade surface entries**
- **Found during:** Task 3 parity gate check (after runtime_coverage_registry update)
- **Issue:** Adding the 3 validator function stubs and 16 dunder method stubs in Deviations 1 and 2 caused the python_api_surface parser to pick up 19 new Python export entries during Task 3's baseline refresh. These had no corresponding tier1 contract rows, producing `newly_uncovered_total = 19` at the first post-Task-3 gate run.
- **Fix:** Inline Rule 2 fixup script added 19 new contract rows — 16 method rows anchoring on the parent class's rust_symbol (Fallout4Version, GameId, YamlFile, ResourceType, ResourceInfo, XseType, XseInfo, ModSite) and 3 function rows anchoring on `validators` (the classic-settings-core module the underlying functions live in).
- **Files modified:** `parity_contract.json`
- **Verification:** post-fix `newly_uncovered_total == 0`
- **Committed in:** `5c18dc19` (Task 3 commit, atomic with registry selector additions)

**4. [Rule 3 - Blocking] Excluded 2 parser-garbage rust symbols in path**
- **Found during:** Task 0 Step 4 helper run
- **Issue:** `generate_baseline.py`'s `pub use {...}` block parser picks up inline Rust comments as pseudo-symbols. `classic-path-core/src/lib.rs` L74-80 has two comment lines (`// Boolean convenience wrappers` and `// Permission and accessibility checks`) inside a `pub use validator::{...}` block; the parser concatenates each comment with the next symbol name, producing pathological "rust symbols" like `// Boolean convenience wrappers drive_exists`.
- **Fix:** Added `PARSER_GARBAGE_RUST_SYMBOLS = {...}` exclusion set in `_build_plan09a_rows.py` filtering these 2 entries silently. These remain as 2 tier2 gaps in the final diff report (legitimate exclusions).
- **Root cause:** Pre-existing `generate_baseline.py` parser bug, NOT caused by Plan 09a. Filed as deferred item for a future generate_baseline.py parser cleanup plan.
- **Verification:** residual count drops from 735 to 733; three-branch test still passes
- **Committed in:** `45fb5b19` (Task 0 Step 4 commit)

**5. [Rule 3 - Blocking] generate_baseline.py `--write-baseline` flag does not exist**
- **Found during:** Task 0 Step 1 initial baseline refresh
- **Issue:** Plan instructions called `python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline` but the actual CLI has no `--write-baseline` flag (it always writes).
- **Fix:** Dropped the flag; called `generate_baseline.py --repo-root .` directly. Output identical.
- **Impact:** Plan text was aspirational / stale; live tooling is the source of truth.
- **Committed in:** `99f25698` (Task 0 Step 5 commit)

**6. [Rule 1 - Bug] 5 smoke test API-assumption bugs fixed inline**
- **Found during:** Task 2 Step 3 pytest run
- **Issues:** My initial hand-authored tests made 5 wrong API assumptions that I had not probed:
  - `BackupManager.list_backups()` (doesn't exist — correct method is `list_versions()`)
  - `DocumentsChecker.has_documents_folder()` (doesn't exist — correct is `run_all_checks()`)
  - `XseVersion.version_string()` (doesn't exist — correct is `full_version()`)
  - `format_contract_event("event", {...})` (wrong arity — actual signature takes 5 args: component, event, severity, outcome, context)
  - `ModSite.nexus_mods().name() == "NexusMods"` (actual value is "Nexus Mods" with space)
- **Fix:** Probed each class at runtime via a scratch script (`_tmp_fix.py`), updated each test to use the verified API.
- **Verification:** pytest 154/154 green after fixes
- **Committed in:** `6987a1bd` (Task 2 commit)

---

**Total deviations:** 6 auto-fixed (3x Rule 2 missing critical, 1x Rule 1 bug, 2x Rule 3 blocking)
**Impact on plan:** All 6 deviations were necessary for correctness or to complete the plan. No scope creep. The Rule 2 stub additions were in-plan (Plan 08 precedent explicitly calls for Rule 2 inline fixes); the stub-cascade surface discovery was a new failure mode caught and fixed atomically.

## Issues Encountered

- **generate_baseline.py parser comment-in-pub-use bug**: Pre-existing issue that produces 2 garbage "rust symbols" from `classic-path-core/src/lib.rs` L74-80. Not in scope for this plan — excluded via `PARSER_GARBAGE_RUST_SYMBOLS`. File as deferred item for future generate_baseline.py cleanup.
- **mypy not installed in binding venv**: Task 4 Step 5 mypy --strict run initially failed with `No module named mypy`. Installed via `uv pip install --python .venv/... mypy` — not committed (local dev tool), but the install is required for the full 5-step chain. Plan 09b's Task 4 Step 1 should ensure mypy is present before the full 19-stub sweep.
- **Python rebuild cycles slowed iteration**: Each `rebuild_rust.ps1 -Target python` run takes ~2 min; Task 2 needed 2 rebuilds (initial + post-Task-1 stub additions). Manageable but a notable drag on iteration speed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

**Plan 09b starting conditions:**
- `tier1_contract_total = 1098` — Plan 09b Task 1 (delete `tierDefinitions.tier2` branches in `generate_baseline.py`) can verify post-delete count stays at 1098 (no tier-1 drift).
- `deferred_total = 1008` — Plan 09b Task 3 must drive this to 0 by emptying `deferred_runtime_backlog.json::entries` (explicit task step documented in DRY-RUN-PROJECTION.md).
- `newly_uncovered_total = 0` ✓ — locked at 0, Plan 09b's baseline refresh should preserve this.
- `registry_mismatch_total = 0` ✓ — C2 fix empirically validated; Plan 09b can trust `_stable_id_hash` for any new selectors it needs.
- **Parser-garbage items (2 path + GLOBAL_FCX_HANDLER = 3 total)** remain in diff report as legitimate tier2 exclusions. Plan 09b should not try to promote these.
- **Plan 09b re-verification of `generate_baseline.py` line numbers** — Task 0's plan referenced L672-708 for the rust_unmapped/python_unmapped branches; these line numbers may have drifted and must be re-grepped before editing (plan text says "may drift after each baseline refresh").
- **mypy --strict on the full 19-stub surface** — Plan 09b Task 4 Step 1; Plan 09a only exercised 15 stubs. `classic_shared.pyi` and the 3 remaining config/file_io/scanlog stubs are Plan 09b's responsibility.

**Carry-forward for Plan 10 / Phase 04:**
- Plan 08's two-owner-in-one-plan template now generalizes to N owners via `_build_plan09a_rows.py`. The Node parity phase (Phase 04) can reuse the same three-branch wrapper check and imported `_stable_id_hash` pattern.
- The submodule-anchor Pitfall 2 fallback is a new Plan 09a contribution — should be documented as a reusable routing strategy in `binding-parity-overview.md` when Phase 6 rewrites it.

## Self-Check: PASSED

**Files verified present:**
- `.planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md`
- `.planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md`
- `.planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md`
- `.planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md`
- `.planning/phases/03-python-tier-collapse/_build_plan09a_rows.py`
- `.planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py`
- `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py`

**Commits verified present:**
- `627044d1` — Task 0 Step 2 constructor inventory
- `b2369a7a` — Task 0 Step 3 stub audit
- `45fb5b19` — Task 0 Step 4 helper + residual inventory
- `99f25698` — Task 0 Step 5 baseline refresh
- `d99a6c34` — Task 0 Step 6 dry-run projection
- `0d1d3705` — Task 1 574 residual rows + Rule 2 stub fixes
- `6987a1bd` — Task 2 154 smoke tests
- `5c18dc19` — Task 3 15 selectors + Rule 2 inline fixup for 19 cascade rows
- `1528e596` — Task 4 final baseline refresh

---
*Phase: 03-python-tier-collapse*
*Plan: 09a*
*Completed: 2026-04-09*
