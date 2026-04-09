---
phase: 03-python-tier-collapse
plan: 07
subsystem: python-parity
tags: [python, parity-gate, pyo3, version-registry, tier-collapse]

# Dependency graph
requires:
  - phase: 03-python-tier-collapse
    provides: Plan 06 landed the first non-scanlog (config) promotion track with 28 new tier1 rows; tier1Mappings was at 314 at plan open
provides:
  - 35 new Tier-1 contract rows for classic-version-registry-core promotion (10 rust-only @rust-suffixed + 24 python-only + 1 Tier-2 runtime-verified migration)
  - parity_contract.json::tier1Mappings grows from 314 to 349 entries
  - python-tier1-version-registry runtime selector contractCount bumped from 24 to 59 with recomputed contractIdsHash (e8a323336b6cc84fcce161284b5a0f984727a82970a10b7c8ac6f3195272a89d)
  - python-tier1-version-registry-plan07-promoted aux runtime entry with 25 explicit bindingIdentifiers pointing at test_promoted_version_registry_smoke.py
  - python-tier2-version-registry-runtime DELETED (its only binding GameVersion.semantic_distance is now tier1)
  - test_promoted_version_registry_smoke.py with 13 per-class fixture-backed tests (420 lines)
  - 03-07-CONSTRUCTOR-INVENTORY.md documenting verified classic-version-registry-py surface
  - _build_version_registry_rows.py helper for reproducibility
  - Second non-scanlog promotion plan lands clean — confirms the Wave 1/Plan 06 pattern generalizes robustly
affects: [03-08, 03-09a, 03-09b]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plan 07 reuses the Wave 1/Plan 06 @rust-suffix pattern for rust-only symbols paired with the nearest Python class (AddressLibraryConfig/CompatibleRange/CrashgenConfig/XseConfig for models.rs types; MatchResult for VersionMatcher; VersionRegistry for Result type alias and VersionRegistryError; UnknownVersionHandling for LogLevel and UnknownVersionStrategy enums)"
    - "Dotted ID scheme continues: version_registry.<submodule>.<symbol> (version_registry.version.*, .models.*, .matching.*, .registry.*, .error.*, .lib.*) with @rust suffix for rust-only proxy rows"
    - "Minimal .pyi update: Task 2 was a verified no-op (like Plan 06) — all 35 promoted Python identifiers already exist in classic_version_registry.pyi from prior phase work. mypy --strict clean. No commit created"
    - "Tier-2 migration outright deletion precedent: python-tier2-version-registry-runtime had exactly 1 binding (GameVersion.semantic_distance) — the entry was safely DELETED in Task 4 (contrast Plan 06/Wave 3a where Tier-2 entries were PRESERVED because their bindings could not be promoted)"

key-files:
  created:
    - .planning/phases/03-python-tier-collapse/03-07-CONSTRUCTOR-INVENTORY.md
    - .planning/phases/03-python-tier-collapse/_build_version_registry_rows.py
    - ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py
  modified:
    - docs/implementation/python_api_parity/baseline/parity_contract.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.json
    - docs/implementation/python_api_parity/baseline/parity_diff_report.md
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json
    - docs/implementation/python_api_parity/baseline/python_api_surface.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    - ClassicLib-rs/python-bindings/parity-artifacts/* (regenerated via check_parity_gate.py --update-baseline)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json

key-decisions:
  - "Plan-scaffold tier1Mappings target correction: plan claimed 347 (312 + 35) but current contract was at 314 (Plan 06 came in 2 rows over its own scaffold target of 312). Adopted ground truth 349 (314 + 35). Matches the plan-decay pattern that every prior plan encountered"
  - "R1 distinct-types verification: UnknownVersionStrategy (enum at models.rs:532-541) and UnknownVersionHandling (struct at models.rs:591-599) are indeed distinct types — BUT only UnknownVersionStrategy is in the deferred backlog. UnknownVersionHandling is already a pre-existing Tier-1 row (version-registry-unknown-version-handling-class). Plan 07 only adds one new contract row for UnknownVersionStrategy (@rust-suffixed proxy pairing with UnknownVersionHandling class) — not two rows as the plan scaffold implied"
  - "Enum variant corrections: UnknownVersionStrategy variants are NearestMatch/Strict/DefaultOnly (NOT Reject/Accept/Warn/Error/Fallback as the plan scaffold guessed). LogLevel variants are Debug/Warning/Error (NOT DEBUG/INFO/WARN/ERROR/TRACE). Verified from classic-version-registry-core/src/models.rs:532-585. None of these enums have PyO3 wrappers — they surface as string getters on PyUnknownVersionHandling/PyAddressLibraryConfig"
  - "No VersionMatcher Python class exists: the plan scaffold assumed classic_version_registry.VersionMatcher could be constructed and match_version() called on it. Reality: VersionMatcher is a pure-Rust type in matching.rs with NO PyO3 wrapper. Python matching lives on PyVersionRegistry.match_version() via the singleton. VersionMatcher@rust proxy row pairs with MatchResult as its Python anchor"
  - "No VersionRegistryError Python exception: unlike Wave 2's create_exception! pattern for FcxResetError, classic-version-registry-py does not expose an exception class. Errors surface as PyValueError/PyRuntimeError. The @rust-suffix proxy row for VersionRegistryError pairs with VersionRegistry class as its Python anchor"
  - "Factory-only PyO3 classes: 8 of 10 PyO3 wrappers in classic-version-registry-py have NO #[new] constructor — they are obtained only via the VersionRegistry singleton (get_by_id(), get_by_version(), etc.) or from MatchResult returned by match_version(). Only GameVersion (has #[new(version_str)]) and VersionRegistry (has #[new()]) are directly constructable from Python. Smoke tests use the singleton fetch pattern throughout"
  - "Tier-2 migration outright deletion: python-tier2-version-registry-runtime had exactly 1 binding (GameVersion.semantic_distance). After promoting that binding to a tier1 contract row, the registry entry was safely DELETED (not preserved). This is the FIRST outright tier-2 deletion in Phase 3 — contrast Wave 3a and Plan 06 where tier-2 entries were PRESERVED because their bindings could not be promoted as contract rows"
  - "8 rust-only deferred backlog entries remain after Plan 07 (AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel, UnknownVersionStrategy, VersionMatcher, XseConfig). These are registry_only tracked entries — they don't produce tier1 gaps, and the Plan 07 contract rows cover their rustSymbol values. The residual backlog entries themselves will be cleaned up by Plan 09a (A10 residual cleanup). Matches Plan 06's behavior where 15 config rust-only entries also remain as registry_only until Plan 09a"
  - "Test discipline: Task 3 marked tdd='true' but all PyO3 wrappers already exist in the built wheel — tests authored directly (not via RED/GREEN/REFACTOR) since there is no production code to write. Committed as Test: prefix per Wave 1/3a/06 precedent. 13/13 tests passed on first run (third consecutive first-run-clean plan, matches Wave 3b and Plan 06)"
  - "Task 2 .pyi update was a verified no-op: existing classic_version_registry.pyi (748 lines) already contains every Python identifier referenced by the 35 new rows (verified via automated cross-check against python_api_surface.json — 0 missing). mypy --strict passes. No commit created per no-empty-commits protocol (Wave 1/2/3b/06 precedent)"

patterns-established:
  - "Pattern: Tier-2 outright deletion vs preservation. If a Tier-2 registry entry's binding(s) can all be promoted as tier1 contract rows (i.e., they are visible in python_api_surface and resolvable to rust symbols), the entry is safely DELETED. If any binding cannot be promoted (e.g. @property methods invisible to the surface parser), the entry must be PRESERVED to avoid orphaning runtime-verified coverage. Plan 07 demonstrates outright deletion; Plan 06 and Wave 3a demonstrate preservation"
  - "Pattern: Singleton-fetched factory classes for smoke tests. When PyO3 wrappers have no #[new] constructor, smoke tests fetch instances via the module's singleton accessor (e.g., get_version_registry().get_by_id('FO4_OG') returns a real VersionInfo; og.address_library returns a real AddressLibraryConfig). This gives R1 compliance without needing Python constructors"
  - "Pattern: Enum-to-string conversion via getter. Rust enums without PyO3 wrappers (AddressLibFormat, LogLevel, UnknownVersionStrategy) are surfaced to Python as string getters on their parent struct's wrapper (e.g., PyUnknownVersionHandling.strategy returns 'nearest_match'/'strict'/'default_only'). The @rust proxy row pairs the enum with its struct parent's PyO3 wrapper"

requirements-completed: [PYT-02, PYT-04, PYT-05]

# Metrics
duration: 11min
completed: 2026-04-09
---

# Phase 3 Plan 07: classic-version-registry-core Promotion Summary

**Promoted 35 version_registry parity entries (34 deferred + 1 Tier-2 migration) to enforced Tier-1; tier1Mappings grew 314 -> 349; the Wave 1 @rust-suffix pattern generalized cleanly to a second non-scanlog domain; first outright Tier-2 registry entry deletion (vs prior preservation pattern); 13-test fixture-backed smoke suite passed on first run; full 5-step verification chain green.**

## Performance

- **Duration:** 11 minutes (10m 36s)
- **Started:** 2026-04-09T00:09:52Z
- **Completed:** 2026-04-09T00:20:28Z
- **Tasks:** 4 (Task 0 inventory + Tasks 1, 3, 4 implementation; Task 2 verified no-op)
- **Files modified:** 17 (3 created + 14 modified)

## Accomplishments

- **Constructor inventory (Task 0):** Read `classic-version-registry-core/src/lib.rs` (full 65 lines), `classic-version-registry-core/src/models.rs` (the UnknownVersionStrategy/UnknownVersionHandling split at lines 532/591), `classic-version-registry-py/src/lib.rs`, and all 5 -py submodule source files (lib.rs, version.rs, models.rs, matching.rs, registry.rs) before any row authoring. Verified A3 — all 13 named symbols plus the Result<T> type alias are already `pub use`d at classic-version-registry-core/src/lib.rs lines 47-65 (zero re-exports needed). Discovered and documented 5 critical plan-scaffold divergences:
  1. **tier1Mappings target math was wrong** — plan claimed 347 (312 + 35) but current contract was at 314 (Plan 06 came in 2 rows over its own scaffold target). Ground truth: 349.
  2. **UnknownVersionHandling is NOT in the deferred backlog** — it's already a pre-existing Tier-1 row. Only UnknownVersionStrategy (enum) is deferred. Plan scaffold implied both needed new rows; actually only one.
  3. **Enum variants were guessed wrong** — plan scaffold listed `Reject/Accept/Warn/Error/Fallback` for UnknownVersionStrategy and `DEBUG/INFO/WARN/ERROR/TRACE` for LogLevel. Real variants: `NearestMatch/Strict/DefaultOnly` and `Debug/Warning/Error`.
  4. **No VersionMatcher Python class** — plan scaffold assumed `classic_version_registry.VersionMatcher().match_version()` worked. Reality: VersionMatcher is a pure-Rust type with NO PyO3 wrapper. Python matching lives on `VersionRegistry.match_version()` via singleton.
  5. **No VersionRegistryError exception** — plan scaffold had `issubclass(..., Exception)`. Reality: no `create_exception!` in classic-version-registry-py; errors surface as PyValueError/PyRuntimeError.

- **35 contract rows authored (Task 1):** Built `_build_version_registry_rows.py` helper that splits the 34 version_registry backlog entries (10 rust-only + 24 python-only) and adds 1 Tier-2 migration (GameVersion.semantic_distance). Every row has `ownerModule='version_registry'`, `tier='tier1'`, non-empty `rustSymbol` + `pythonExportPath` resolvable through the parsed surfaces. Per-submodule counts:
  - `version_registry.version.*`: 9 rows (GameVersion dunders + same_major + semantic_distance)
  - `version_registry.models.*`: 19 rows (4 rust-only @rust class proxies + 4 enum @rust proxies + 11 python-only VersionInfo/AddressLibraryConfig/CompatibleRange/CrashgenConfig/XseConfig classes and methods)
  - `version_registry.matching.*`: 4 rows (VersionMatcher@rust + 3 MatchConfidence dunders/methods)
  - `version_registry.registry.*`: 1 row (VersionRegistry.__init__)
  - `version_registry.error.*`: 1 row (VersionRegistryError@rust proxy)
  - `version_registry.lib.*`: 1 row (Result@rust type alias proxy)
  
  Helper script asserts 35 total rows with no duplicate IDs and verifies every `pythonExportPath` exists in `python_api_surface.json` and every @rust rustSymbol exists in `rust_api_surface.json` (Pitfall 2 pre-check). Final tier1Mappings = 349 (314 + 35).

- **Verified no-op .pyi update (Task 2):** Verified by automated cross-check that the existing `classic_version_registry.pyi` (748 lines) already contains every Python identifier referenced by the 35 new contract rows (extracted from python_api_surface.json — 0 missing). `mypy --strict` already passes. Skipped Task 2 commit since there's nothing to change. Documented the no-op here.

- **13-test smoke suite (Task 3):** Authored `test_promoted_version_registry_smoke.py` (420 lines) with per-class fixture-backed construction tests. Tests use exact constructor signatures and method names verified from the constructor inventory:
  - `test_version_registry_construct_and_basic_lookups` (VersionRegistry.__init__ + get_by_id + get_version_registry free fn)
  - `test_game_version_construct_and_field_access` (GameVersion(version_str) + major/minor/patch/build)
  - `test_game_version_comparison_dunders` (all 6 dunders + same_major)
  - `test_game_version_semantic_distance` (Tier-2 runtime-verified migration)
  - `test_version_info_fields_and_crashgen_methods` (VersionInfo fetched via registry; __eq__/__hash__ + get_crashgen_version_strings/get_crashgen_for_version/get_compatible_crashgens/is_compatible_with)
  - `test_address_library_config_field_access` (fetched via og.address_library; filename/format/nexus_url)
  - `test_xse_config_field_access` (fetched via og.xse; acronym/full_name/compatible_version/loader/file_count/script_hashes)
  - `test_crashgen_config_field_access_and_is_compatible_with` (fetched via og.crashgen_versions[0]; 6 field getters + is_compatible_with method call)
  - `test_compatible_range_field_access_and_contains` (fetched via crashgen.compatible_range; min_version/max_version/contains)
  - `test_unknown_version_handling_field_access` (fetched via registry.unknown_version_handling; strategy/log_level/defaults/get_default)
  - `test_match_confidence_classattrs_and_dunders` (EXACT/RANGE/NEAREST/DEFAULT/UNKNOWN classattrs + is_high_confidence + __eq__/__hash__ via MatchResult.confidence_enum)
  - `test_match_result_via_match_version` (MatchResult via registry.match_version; 9 field accessors)
  - `test_rust_only_symbols_in_core_surface` (Pitfall 2 guard asserting all 10 rust-only symbols exist in classic-version-registry-core)
  
  Runs in 0.07s; 13/13 passed on first run with zero fix iterations (third consecutive first-run-clean plan, matching Wave 3b and Plan 06).

- **Runtime registry update (Task 4):**
  - `python-tier1-version-registry` selector entry: `contractCount` 24 → 59 (24 existing + 35 new), `contractIdsHash` recomputed to `e8a323336b6cc84fcce161284b5a0f984727a82970a10b7c8ac6f3195272a89d` (sha256 of 59 sorted version_registry tier1 IDs).
  - `python-tier2-version-registry-runtime` DELETED outright — its only binding (`GameVersion.semantic_distance`) is now a tier1 contract row. First outright tier-2 deletion in Phase 3.
  - `python-tier1-version-registry-plan07-promoted` aux entry added with 25 explicit `bindingIdentifiers` pointing at `test_promoted_version_registry_smoke.py`.

- **Baseline refresh (Task 4):** Regenerated all baseline + parity-artifacts files via `generate_baseline.py --output-dir docs/implementation/python_api_parity/baseline` and `check_parity_gate.py --update-baseline`. All baseline JSON/MD artifacts in lockstep with the 349-row contract.

- **Gate green:** `check_parity_gate.py` exits 0 with `Tier-1 parity gate passed.`; `tier1_contract_total = 349`, `tier1_missing_runtime_total = 0`, `registry_mismatch_total = 0`, `deferred_total = 1042` (down from 1070).

## Task Commits

Each task was committed atomically:

1. **Task 0: Constructor inventory** — `5ca13799` (Docs)
2. **Task 1: 35 version_registry contract rows + helper script** — `816d68d4` (Feat)
3. **Task 2: .pyi update** — *no commit, verified no-op (all identifiers already in stub from prior phases; mypy --strict clean)*
4. **Task 3: version_registry smoke test suite** — `cf6a0051` (Test)
5. **Task 4: Runtime registry + baseline refresh** — `cc2ad4cf` (Feat)

## Files Created/Modified

### Created

- `.planning/phases/03-python-tier-collapse/03-07-CONSTRUCTOR-INVENTORY.md` — Verified classic-version-registry-py surface inventory; documents PyClass wrappers (factory-only vs direct-construct), rust-only symbol map, the UnknownVersionStrategy/UnknownVersionHandling split, enum variant corrections
- `.planning/phases/03-python-tier-collapse/_build_version_registry_rows.py` — Reproducible helper script that generates the 35 contract rows from the deferred backlog (modeled after `_build_config_rows.py`)
- `ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py` — 13 pytest functions covering the 35 promoted version_registry rows with R1-compliant fixture-backed singleton usage (420 lines)

### Modified

- `docs/implementation/python_api_parity/baseline/parity_contract.json` — `tier1Mappings` grew from 314 to 349 entries; 35 new version_registry rows added with dotted `version_registry.<submodule>.<symbol>` IDs
- `docs/implementation/python_api_parity/baseline/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary}.{json,md}` — All baseline artifacts regenerated to reflect the 349-row contract
- `ClassicLib-rs/python-bindings/parity-artifacts/{rust_api_surface,python_api_surface,parity_diff_report,runtime_coverage_summary,tier1_gate_report}.{json,md}` — Tracked generated artifacts mirror the baseline
- `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json` — Bumped `python-tier1-version-registry` (24→59, new hash); DELETED `python-tier2-version-registry-runtime`; added `python-tier1-version-registry-plan07-promoted` aux entry with 25 binding identifiers

## Decisions Made

- **Plan scaffold tier1Mappings target correction**: Plan claimed `tier1Mappings.length == 347` (312 + 35), but the current contract was at 314 at plan open (Plan 06 landed 28 new rows, not 26 — plan-decay pattern that every prior plan encountered). Ground truth: final tier1Mappings = 349. Documented as Rule 1 deviation.

- **R1 distinct-types verification — only ONE new row, not two**: Plan scaffold instructed adding contract rows for both `UnknownVersionStrategy` and `UnknownVersionHandling` as distinct types. Reality: `UnknownVersionHandling` is already a pre-existing Tier-1 row (`version-registry-unknown-version-handling-class`). Only `UnknownVersionStrategy` (the enum) is in the deferred backlog. Plan 07 adds one new @rust-suffixed proxy row for `UnknownVersionStrategy` — not two rows as implied. Both types remain distinctly represented in the contract (existing + new).

- **Enum variant corrections**: Verified from `classic-version-registry-core/src/models.rs`:
  - `UnknownVersionStrategy`: `NearestMatch`, `Strict`, `DefaultOnly` (plan scaffold guessed `Reject/Accept/Warn/Error/Fallback`)
  - `LogLevel`: `Debug`, `Warning`, `Error` (plan scaffold guessed `DEBUG/INFO/WARN/ERROR/TRACE`)
  - None of these enums have PyO3 wrappers. They surface as string getters on parent structs (`PyUnknownVersionHandling.strategy` returns `'nearest_match'` etc.).

- **VersionMatcher has no Python class**: Plan scaffold's Task 3 test `test_version_matcher_construct_and_match` assumed `classic_version_registry.VersionMatcher()` worked. Verified from `classic-version-registry-py/src/matching.rs` (full file) and `lib.rs` (no `m.add_class::<PyVersionMatcher>()`): NO PyO3 wrapper for VersionMatcher. Python matching lives on `PyVersionRegistry.match_version()` via the singleton. VersionMatcher@rust proxy row pairs with MatchResult as its Python anchor (nearest class in matching.rs).

- **VersionRegistryError has no Python exception class**: Plan scaffold's Task 3 test `test_version_registry_error_is_exception_class` assumed `classic_version_registry.VersionRegistryError` is an Exception subclass. Verified by grep: no `create_exception!` invocation in `classic-version-registry-py/`. Errors surface as `PyValueError`/`PyRuntimeError`. VersionRegistryError@rust proxy row pairs with VersionRegistry class as its Python anchor.

- **Factory-only class pattern for smoke tests**: 8 of 10 PyO3 wrappers (AddressLibraryConfig, XseConfig, CompatibleRange, CrashgenConfig, UnknownVersionHandling, VersionInfo, MatchConfidence, MatchResult) have NO `#[new]` constructor. They can only be obtained via `From<core::...>` conversions from the singleton-backed `VersionRegistry` methods or `MatchResult`. The smoke test suite uses `registry.get_by_id("FO4_OG")` as the entrypoint and exercises the factory chain (`og.address_library`, `og.xse`, `og.crashgen_versions[0]`, etc.). This is the **singleton-fetched factory pattern**.

- **Tier-2 outright deletion (first in Phase 3)**: `python-tier2-version-registry-runtime` had exactly 1 binding (`classic_version_registry.GameVersion.semantic_distance`). After promoting that binding to a tier1 contract row via the Tier-2 migration, the registry entry was safely DELETED. This is the FIRST outright tier-2 deletion in Phase 3 — contrast Wave 3a (`python-tier2-scanlog-runtime` preserved) and Plan 06 (`python-tier2-config-runtime` preserved). Deletion criteria: ALL of the entry's bindings can be promoted (visible to surface parser, resolvable rust symbol). `GameVersion.semantic_distance` is a regular `#[pymethods]` function on `PyGameVersion` — fully visible.

- **Plan math reconciliation**: 34 deferred + 1 Tier-2 migration = 35 new tier1 rows → tier1Mappings = 314 + 35 = 349 (not 347 as plan scaffold said). Accepted; the plan's denominator was wrong by 2 (inherited from Plan 06's similar drift).

- **Task 2 .pyi update was a verified no-op**: Like Plan 06 precedent, the existing `classic_version_registry.pyi` (748 lines) already contained every Python identifier referenced by the 35 new contract rows. No commit created per no-empty-commits protocol. Documented in this summary.

- **Test discipline (Wave 1/3b/06 precedent)**: Test file authored directly without RED/GREEN/REFACTOR cycle because all PyO3 wrappers already exist in the built wheel. Committed as `Test:` prefix. 13/13 tests passed on first run (third consecutive first-run-clean plan — Wave 3b, Plan 06, Plan 07).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan-scaffold tier1Mappings target off by 2 (347 vs 349)**

- **Found during:** Task 1 (contract row authoring, pre-write verification)
- **Issue:** Plan's `must_haves` and `verify` steps asserted `tier1Mappings.length == 347` (312 + 35), but the current contract was at 314 (Plan 06 landed at 314 not 312 — Plan 06's own scaffold was off by the same delta).
- **Root cause:** Plan 07 was authored before Plan 06 ran; its denominator was based on the stale pre-Plan-06 value. This is the plan-decay pattern every Phase 3 plan has encountered.
- **Fix:** Adopted ground truth (314 + 35 = 349) from the disk state. Helper script asserts `len(rows) == 35` and verifies no ID collisions with existing rows. Final tier1Mappings = 349.
- **Files modified:** `_build_version_registry_rows.py` (assertion `len == 35`), `parity_contract.json`
- **Verification:** Gate exits 0 with 349 tier1 rows; summary `tier1_contract_total == 349`
- **Committed in:** `816d68d4`

**2. [Rule 1 - Bug] Plan assumption that UnknownVersionStrategy AND UnknownVersionHandling both need new contract rows**

- **Found during:** Task 0 (Constructor inventory)
- **Issue:** Plan's `must_haves` explicitly says "R1: both UnknownVersionStrategy (enum) AND UnknownVersionHandling (struct) are verified as distinct types... each gets its own contract row with a distinct ID".
- **Root cause:** Reading `parity_contract.json` showed `UnknownVersionHandling` is ALREADY a pre-existing Tier-1 row (`version-registry-unknown-version-handling-class` — pythonExportPath `UnknownVersionHandling`, rustSymbol `UnknownVersionHandling`). Only `UnknownVersionStrategy` is in the deferred backlog (`python-deferred-version_registry-420` with `rustSymbols=['UnknownVersionStrategy']`). The R1 warning about "distinct types" is still correct — they ARE distinct — but only one of them needs a new row.
- **Fix:** Added one @rust-suffixed proxy row for `UnknownVersionStrategy` pairing with `UnknownVersionHandling` class as its Python anchor. The existing 2 `UnknownVersionHandling` rows remain untouched.
- **Files modified:** `_build_version_registry_rows.py` (rust_only_map), `03-07-CONSTRUCTOR-INVENTORY.md`
- **Verification:** Gate passes; both `UnknownVersionStrategy` (1 row) and `UnknownVersionHandling` (2 existing rows) are distinctly represented; diff report shows 0 missing_rust
- **Committed in:** `816d68d4`

**3. [Rule 1 - Bug] Plan scaffold's enum variant names were guessed wrong**

- **Found during:** Task 0 (Constructor inventory, models.rs line reading)
- **Issue:** Plan's Task 3 test scaffold included these expected enum variants:
  - `UnknownVersionStrategy`: `["Reject", "Accept", "Warn", "Error", "Fallback"]`
  - `LogLevel`: `["DEBUG", "INFO", "WARN", "ERROR", "TRACE"]`
  - `MatchConfidence`: `["EXACT", "HIGH", "LOW", "NONE", "NoMatch"]`
  - `AddressLibFormat`: `["AE", "SE", "VR", "NG"]`
- **Root cause:** Verified from `classic-version-registry-core/src/models.rs` (lines 532-585):
  - `UnknownVersionStrategy`: `NearestMatch`, `Strict`, `DefaultOnly` (3 variants, not 5)
  - `LogLevel`: `Debug`, `Warning`, `Error` (3 variants, not 5)
  - `MatchConfidence` is in `matching.rs` with classattr string constants: `EXACT="exact"`, `RANGE="range"`, `NEAREST="nearest"`, `DEFAULT="default"`, `UNKNOWN="unknown"` (NOT "HIGH/LOW/NONE/NoMatch")
  - `AddressLibFormat` has NO PyO3 wrapper — it's used internally; `.extension()` returns "bin"/"csv"
- **Fix:** Rewrote the smoke test suite to use real enum surface. `MatchConfidence` classattrs use the documented `"exact"/"range"/"nearest"/"default"/"unknown"` string values. `UnknownVersionStrategy`/`LogLevel`/`AddressLibFormat` don't get variant tests because they have no Python wrapper — their presence is verified via the Pitfall 2 guard against `rust_api_surface.json`.
- **Files modified:** `test_promoted_version_registry_smoke.py`, `03-07-CONSTRUCTOR-INVENTORY.md`
- **Verification:** All 13 tests passed on first run
- **Committed in:** `cf6a0051`

**4. [Rule 1 - Bug] Plan scaffold assumed VersionMatcher Python class exists**

- **Found during:** Task 0 (Constructor inventory, -py source reading)
- **Issue:** Plan's Task 3 scaffold showed `matcher = classic_version_registry.VersionMatcher(); matcher.match_version("/dev/null")` and the `<interfaces>` block listed `VersionMatcher` as a promoted class with `rustKind='struct'`, `pythonKind='class'`.
- **Root cause:** Read `classic-version-registry-py/src/matching.rs` (full file, 226 lines) — it only contains `PyMatchConfidence` and `PyMatchResult`, NO `PyVersionMatcher`. Read `classic-version-registry-py/src/lib.rs` — `m.add_class::<PyVersionMatcher>()` is not called. VersionMatcher is purely a Rust-side type in `classic-version-registry-core/src/matching.rs`. Python matching lives on `PyVersionRegistry.match_version()` via the singleton (`registry.rs` line 187).
- **Fix:** Routed VersionMatcher@rust as a @rust-suffixed proxy row pairing with `MatchResult` (nearest Python class in matching.rs). Smoke test exercises the real matching path via `registry.match_version("1.10.163.0", "Fallout4", False)` which returns a real `PyMatchResult`. The Pitfall 2 guard asserts VersionMatcher exists in `rust_api_surface.json`.
- **Files modified:** `_build_version_registry_rows.py` (rust_only_map — VersionMatcher -> MatchResult pairing), `test_promoted_version_registry_smoke.py` (test_match_result_via_match_version instead of test_version_matcher_construct)
- **Verification:** Gate passes; test_match_result_via_match_version passes; test_rust_only_symbols_in_core_surface confirms VersionMatcher symbol present
- **Committed in:** `816d68d4`, `cf6a0051`

**5. [Rule 1 - Bug] Plan scaffold assumed VersionRegistryError is a Python Exception class**

- **Found during:** Task 0 (Constructor inventory, -py grep)
- **Issue:** Plan's Task 3 scaffold had `test_version_registry_error_is_exception_class` with `assert issubclass(classic_version_registry.VersionRegistryError, Exception)`. Plan's Task 2 stub scaffold had `class VersionRegistryError(Exception): ...`.
- **Root cause:** Grep for `VersionRegistryError` in `classic-version-registry-py/` returned NO matches. No `create_exception!` macro is used (contrast Wave 2's FcxResetError). Errors from the core surface as `PyValueError` or `PyRuntimeError` via `.map_err()` calls in the wrapper methods.
- **Fix:** Routed `VersionRegistryError@rust` as a proxy row pairing with `VersionRegistry` class (nearest Python anchor in error.rs). Removed the Exception subclass test. Task 2 .pyi update was already a no-op; no new stub text needed. Pitfall 2 guard asserts VersionRegistryError exists in `rust_api_surface.json`.
- **Files modified:** `_build_version_registry_rows.py`, `test_promoted_version_registry_smoke.py`
- **Verification:** Gate passes; test_rust_only_symbols_in_core_surface confirms VersionRegistryError symbol present
- **Committed in:** `816d68d4`, `cf6a0051`

**6. [Rule 1 - Bug] Plan scaffold's sample tests were mostly placeholder hasattr guards**

- **Found during:** Task 3 (test authoring)
- **Issue:** The plan's Task 3 `<action>` block contained test scaffolds with many `try/except (TypeError, AttributeError): pass` patterns (see `test_address_library_config_construct_or_factory`, `test_compatible_range_construct`, `test_crashgen_config_field_access`, `test_xse_config_field_access` in the plan scaffold). These violate R1's anti-hasattr rule — they test nothing when the exception path is taken.
- **Root cause:** The plan scaffold was written speculatively; many factory-only classes were treated as possibly-constructable with `try/except` fallbacks. Reality: they are uniformly factory-only via the registry singleton.
- **Fix:** Rewrote all 13 tests to use the singleton-fetched factory pattern. Every test fetches a real instance via `registry.get_by_id("FO4_OG")` and exercises real fields and methods. Zero hasattr-only paths. Zero try/except pass fallbacks. Each test has assertions on real values.
- **Files modified:** `test_promoted_version_registry_smoke.py`
- **Verification:** 13/13 tests pass; coverage includes real method invocations on AddressLibraryConfig, XseConfig, CrashgenConfig, CompatibleRange, CrashgenConfig.is_compatible_with, CompatibleRange.contains, MatchResult.confidence_enum, etc.
- **Committed in:** `cf6a0051`

---

**Total deviations:** 6 Rule 1 auto-fixes. All corrected wrong assumptions in the plan scaffold about (a) tier1Mappings target math, (b) UnknownVersionStrategy vs UnknownVersionHandling row count, (c) enum variant names, (d) VersionMatcher Python wrapper existence, (e) VersionRegistryError Python exception existence, (f) factory-only class test strategy. None changed the plan's intent or output shape beyond verifying reality.

## Authentication Gates

None — all work is internal to Python parity tooling and registry.

## Issues Encountered

- **8 rust-only deferred backlog entries remain after Plan 07**: AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel, UnknownVersionStrategy, VersionMatcher, XseConfig. These produce `registry_only` tracked entries classified as `deferred`, but they produce ZERO tier1 gaps (all their rust symbols are now in contract rows). The residual deferred backlog entries themselves will be cleaned up by Plan 09a (A10 residual cleanup). This matches Plan 06's behavior where 15 config rust-only entries also remained as registry_only until Plan 09a. Not a Plan 07 scope issue — documented in the constructor inventory.

## User Setup Required

None — no external service configuration required.

## Verification Results (5-Step Chain)

| Step | Command | Result |
|---|---|---|
| 1 | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | **PASS** (`Tier-1 parity gate passed.`; 349/349 matched, 0 drift, 0 newly_uncovered, 0 registry mismatches, 0 tier1_missing_runtime) |
| 2 | `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/.../parity_contract.json --fail-on-warnings` | **PASS** (3/3 crates passed, 0 errors, 0 warnings) |
| 3 | `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python -Crates classic_version_registry` | **PASS** (wheel built + installed + verified) |
| 4 | `pytest ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py -q` | **PASS** (13/13 in 0.07s) |
| 5 | `mypy --strict ClassicLib-rs/python-bindings/classic-version-registry-py/classic_version_registry.pyi` | **PASS** (`Success: no issues found in 1 source file`) |

## Next Phase Readiness

- **Plan 08 (classic_shared + file-io aux wiring) is ready to execute.** The Wave 1/Plan 06/Plan 07 pattern is now well-established across three non-scanlog promotion targets. Plan 08's scope is different (classic_shared wiring + file_io aux enrollment) but uses the same 5-step verification chain.
- **Reusable helper:** `_build_version_registry_rows.py` is a template for any future promotion plan — change the owner module filter, the rust_only_map/python_only_map, and the sub-module routing.
- **Tier-2 deletion precedent:** Plan 07 is the first outright Tier-2 deletion in Phase 3. Plan 09b's final Tier-2 cleanup can reference this plan as evidence that outright deletion works when all bindings are promoted.
- **Tier-1 floor:** current snapshot is 349. Plan 08 + Plan 09a + Plan 09b will push toward the final Phase 3 target.

## Self-Check: PASSED

Verification performed after SUMMARY.md draft:

**Files created check:**
- `.planning/phases/03-python-tier-collapse/03-07-CONSTRUCTOR-INVENTORY.md` — FOUND
- `.planning/phases/03-python-tier-collapse/_build_version_registry_rows.py` — FOUND
- `ClassicLib-rs/python-bindings/tests/test_promoted_version_registry_smoke.py` — FOUND

**Commits check:**
- `5ca13799` Docs(03-07): Add version_registry promotion constructor inventory artifact — FOUND
- `816d68d4` Feat(03-07): Add 35 version_registry tier1 contract rows for Plan 07 promotion — FOUND
- `cf6a0051` Test(03-07): Add fixture-backed smoke tests for Plan 07 version_registry promotions — FOUND
- `cc2ad4cf` Feat(03-07): Refresh parity baseline and runtime registry for version_registry promotion — FOUND

**Verification commands:**
- `check_parity_gate.py --repo-root .` — EXIT 0 (Tier-1 parity gate passed)
- `validate_stubs.py --fail-on-warnings` — EXIT 0 (3/3 crates, 0 errors)
- `rebuild_rust.ps1 -Target python -Crates classic_version_registry` — EXIT 0 (wheel installed)
- `pytest test_promoted_version_registry_smoke.py -q` — EXIT 0 (13 passed)
- `mypy --strict classic_version_registry.pyi` — EXIT 0 (no issues)

---
*Phase: 03-python-tier-collapse*
*Completed: 2026-04-09*
