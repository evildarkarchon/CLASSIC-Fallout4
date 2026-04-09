# Plan 07 Constructor Inventory — classic-version-registry-py

**Verified:** 2026-04-09 (before any code written)
**Purpose:** Catch plan-scaffold divergences before Task 1/3 authoring. Pattern-match Plan 06's success: inventory first, implement second.

## Ground-truth row count

| Source | Count |
|--------|-------|
| `deferred_runtime_backlog.json::entries[ownerModule=version_registry]` | **34** |
| Tier-2 runtime-verified migration (`python-tier2-version-registry-runtime`) | **1** binding (`GameVersion.semantic_distance`) |
| **Total net new tier1 rows** | **35** |

Plan scaffold target: 35. Matches.

Plan scaffold target for tier1Mappings length: **347**. **WRONG** — current contract is at 314 (not 312), so after 35 new rows: **314 + 35 = 349**. (Plan 06 came in at 28 new rows for 314 total, not 26 for 312 as the scaffold expected.)

## A3 verification — lib.rs re-exports

`classic-version-registry-core/src/lib.rs` lines 47-62:

```rust
mod defaults;
mod error;
mod matching;
mod models;
mod registry;
mod version;

// Re-export public API
pub use error::VersionRegistryError;
pub use matching::{MatchConfidence, MatchResult, VersionMatcher};
pub use models::{
    AddressLibFormat, AddressLibraryConfig, CompatibleRange, CrashgenConfig, LogLevel,
    UnknownVersionHandling, UnknownVersionStrategy, VersionInfo, XseConfig,
};
pub use registry::{VersionRegistry, get_version_registry};
pub use version::GameVersion;
```

**All 13 named symbols are re-exported.** Plus the `Result<T>` type alias at line 65 and a `pub type` declaration.

**Zero `pub use` additions required** for Plan 07. The parser's `parse_rust_surface()` already sees every version_registry symbol we need.

Parsed `rust_api_surface.json` shows **17 classic-version-registry-core symbols**:
- tier1 (7): `GameVersion`, `MatchConfidence`, `MatchResult`, `UnknownVersionHandling`, `VersionInfo`, `VersionRegistry`, `get_version_registry`
- tier2 (10 — the rust-only deferred entries): `AddressLibFormat`, `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `LogLevel`, `Result`, `UnknownVersionStrategy`, `VersionMatcher`, `VersionRegistryError`, `XseConfig`

## CRITICAL R1 — Distinct types verified

**`UnknownVersionStrategy`** (models.rs:532-541) is an **enum**:
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
pub enum UnknownVersionStrategy {
    #[default]
    NearestMatch,
    Strict,
    DefaultOnly,
}
```
Variants: `NearestMatch`, `Strict`, `DefaultOnly` (NOT "Reject/Accept/Warn/Error/Fallback" as the plan scaffold guessed).

**`UnknownVersionHandling`** (models.rs:591-599) is a **struct**:
```rust
#[derive(Debug, Clone, Default)]
pub struct UnknownVersionHandling {
    pub strategy: UnknownVersionStrategy,
    pub defaults: HashMap<String, String>,
    pub log_level: LogLevel,
}
```

**PLAN-SCAFFOLD CORRECTION (R1):** The plan scaffold says "both `UnknownVersionStrategy` (enum) AND `UnknownVersionHandling` (struct) are verified as distinct types... each gets its own contract row with a distinct ID."

**Reality:** `UnknownVersionHandling` is **already a Tier-1 row** (`version-registry-unknown-version-handling-class`, promoted in a prior phase). It's NOT in the deferred backlog. Only `UnknownVersionStrategy` is deferred — and it has NO PyO3 wrapper. It will be a @rust-suffixed proxy row.

**Net:** Plan 07 adds 1 new row for `UnknownVersionStrategy` (@rust proxy). `UnknownVersionHandling` stays as-is.

## PyO3 wrapper inventory — classic-version-registry-py

Sources read (full file):
- `src/lib.rs` — `#[pymodule] fn classic_version_registry` calls `version::register`, `models::register`, `matching::register`, `registry::register`
- `src/version.rs` — `PyGameVersion` (`#[pyclass(name = "GameVersion")]`)
- `src/models.rs` — 6 pyclass wrappers: `PyAddressLibraryConfig`, `PyXseConfig`, `PyCompatibleRange`, `PyCrashgenConfig`, `PyUnknownVersionHandling`, `PyVersionInfo`
- `src/matching.rs` — 2 pyclass wrappers: `PyMatchConfidence`, `PyMatchResult`
- `src/registry.rs` — 1 pyclass wrapper: `PyVersionRegistry`, plus 2 module-level free functions: `match_version_string`, `get_version_registry`

**Total PyO3 wrappers: 10 classes + 2 free functions**

### Classes WITH PyO3 wrapper (Python-facing names)
| Wrapper | Rust type (`-core`) | Python name | Has `#[new]`? |
|---------|---------------------|-------------|---------------|
| `PyGameVersion` | `GameVersion` | `GameVersion` | YES — `new(version_str)` |
| `PyAddressLibraryConfig` | `AddressLibraryConfig` | `AddressLibraryConfig` | NO — factory-only via `From<core::...>` |
| `PyXseConfig` | `XseConfig` | `XseConfig` | NO — factory-only |
| `PyCompatibleRange` | `CompatibleRange` | `CompatibleRange` | NO — factory-only |
| `PyCrashgenConfig` | `CrashgenConfig` | `CrashgenConfig` | NO — factory-only |
| `PyUnknownVersionHandling` | `UnknownVersionHandling` | `UnknownVersionHandling` | NO — factory-only |
| `PyVersionInfo` | `VersionInfo` | `VersionInfo` | NO — factory-only |
| `PyMatchConfidence` | `MatchConfidence` | `MatchConfidence` | NO — factory-only (has `classattr` strings `EXACT`/`RANGE`/`NEAREST`/`DEFAULT`/`UNKNOWN`) |
| `PyMatchResult` | `MatchResult` | `MatchResult` | NO — factory-only |
| `PyVersionRegistry` | (singleton handle) | `VersionRegistry` | YES — `new()` (no args) |

### Rust-only symbols (NO PyO3 wrapper)
| Rust type | Kind | Why no wrapper |
|-----------|------|----------------|
| `AddressLibFormat` | enum | Used internally; `.extension()` string form surfaced via `PyAddressLibraryConfig.format` getter |
| `LogLevel` | enum | Used internally; string form surfaced via `PyUnknownVersionHandling.log_level` getter |
| `UnknownVersionStrategy` | enum | Used internally; string form surfaced via `PyUnknownVersionHandling.strategy` getter |
| `VersionMatcher` | struct | Pure-Rust matching helper in `matching.rs`; Python matching lives on `PyVersionRegistry.match_version()` |
| `VersionRegistryError` | error enum | Python errors surface as `PyValueError` or `PyRuntimeError` (no dedicated exception class) |
| `Result<T>` | type alias | Type aliases never surface to Python |

**All 10 rust-only deferred symbols** (`AddressLibFormat`, `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `LogLevel`, `Result`, `UnknownVersionStrategy`, `VersionMatcher`, `VersionRegistryError`, `XseConfig`) will be routed through `@rust`-suffixed proxy contract rows. Note that 4 of these (`AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `XseConfig`) DO have PyO3 wrappers — their rust-only deferred entries are redundant with their python-side deferred entries but still need explicit contract coverage to satisfy the raw backlog counter.

**Wave 1/3a/06 precedent:** Rust-only symbols get `@rust`-suffixed proxy rows paired with the nearest Python class. This is the established pattern.

## Python surface inventory (from `python_api_surface.json`)

Total `classic_version_registry` exports: **49**
- tier1: 24 (matches existing contract)
- tier2: 25 (24 in deferred backlog + 1 tier-2 runtime-verified migration = `GameVersion.semantic_distance`)

### 24 python-only deferred bindings (per `deferred_runtime_backlog.json`):

| Binding identifier | Python kind | Notes |
|--------------------|-------------|-------|
| `AddressLibraryConfig` | class | No `__init__` constructor; factory-only |
| `CompatibleRange` | class | No constructor; factory-only |
| `CompatibleRange.contains(version_str)` | method | Returns bool |
| `CrashgenConfig` | class | No constructor; factory-only |
| `CrashgenConfig.is_compatible_with(version_str)` | method | Returns bool |
| `GameVersion.__eq__` / `__hash__` / `__init__` / `__lt__` / `__le__` / `__gt__` / `__ge__` | dunder methods | `GameVersion` has a real constructor |
| `GameVersion.same_major(other)` | method | Returns bool |
| `MatchConfidence.__eq__` / `__hash__` | dunder methods | Accepts string comparison |
| `MatchConfidence.is_high_confidence()` | method | Returns bool |
| `VersionInfo.__eq__` / `__hash__` | dunder methods | Compares by id |
| `VersionInfo.get_compatible_crashgens(game_version_str=None)` | method | Returns list |
| `VersionInfo.get_crashgen_for_version(crashgen_version)` | method | Returns Optional |
| `VersionInfo.get_crashgen_version_strings()` | method | Returns list[str] |
| `VersionInfo.is_compatible_with(version_str)` | method | Returns bool |
| `VersionRegistry.__init__` | dunder method | No args |
| `XseConfig` | class | No constructor; factory-only |

### 1 Tier-2 runtime-verified migration (to be promoted):

`classic_version_registry.GameVersion.semantic_distance` — the `python-tier2-version-registry-runtime` registry entry has exactly this 1 binding, so the entry can be **DELETED outright** after promotion.

## ID scheme

Matches Plan 06 dotted form: `version_registry.<sub_module>.<symbol>` for python rows, `@rust` suffix for rust-only proxy rows.

Sub-module routing based on source file inside `classic-version-registry-core`:
- `version.rs` → `version` sub-module → `GameVersion`, `semantic_distance`
- `models.rs` → `models` sub-module → `AddressLibraryConfig`, `CompatibleRange`, `CrashgenConfig`, `XseConfig`, `VersionInfo`, `UnknownVersionStrategy`, `AddressLibFormat`, `LogLevel`
- `matching.rs` → `matching` sub-module → `MatchConfidence`, `MatchResult`, `VersionMatcher`
- `registry.rs` → `registry` sub-module → `VersionRegistry.__init__`
- `error.rs` → `error` sub-module → `VersionRegistryError`
- `lib.rs` → `lib` sub-module → `Result` (type alias at lib.rs line 65)

## Row plan (35 total)

### 10 rust-only @rust-suffixed proxy rows

Pair with the nearest Python class (or `GameVersion` as fallback for the type-alias `Result`):

| Rust symbol | @rust ID | Python proxy | pythonKind |
|-------------|----------|--------------|------------|
| `AddressLibFormat` | `version_registry.models.AddressLibFormat@rust` | `AddressLibraryConfig` | class |
| `AddressLibraryConfig` | `version_registry.models.AddressLibraryConfig@rust` | `AddressLibraryConfig` | class |
| `CompatibleRange` | `version_registry.models.CompatibleRange@rust` | `CompatibleRange` | class |
| `CrashgenConfig` | `version_registry.models.CrashgenConfig@rust` | `CrashgenConfig` | class |
| `LogLevel` | `version_registry.models.LogLevel@rust` | `UnknownVersionHandling` | class |
| `Result` | `version_registry.lib.Result@rust` | `VersionRegistry` | class |
| `UnknownVersionStrategy` | `version_registry.models.UnknownVersionStrategy@rust` | `UnknownVersionHandling` | class |
| `VersionMatcher` | `version_registry.matching.VersionMatcher@rust` | `MatchResult` | class |
| `VersionRegistryError` | `version_registry.error.VersionRegistryError@rust` | `VersionRegistry` | class |
| `XseConfig` | `version_registry.models.XseConfig@rust` | `XseConfig` | class |

### 24 python-only deferred rows

| Python path | ID | rustSymbol | pythonKind |
|-------------|----|-----------:|------------|
| `AddressLibraryConfig` | `version_registry.models.AddressLibraryConfig` | `AddressLibraryConfig` | class |
| `CompatibleRange` | `version_registry.models.CompatibleRange` | `CompatibleRange` | class |
| `CompatibleRange.contains` | `version_registry.models.CompatibleRange.contains` | `CompatibleRange` | method |
| `CrashgenConfig` | `version_registry.models.CrashgenConfig` | `CrashgenConfig` | class |
| `CrashgenConfig.is_compatible_with` | `version_registry.models.CrashgenConfig.is_compatible_with` | `CrashgenConfig` | method |
| `GameVersion.__eq__` | `version_registry.version.GameVersion.__eq__` | `GameVersion` | method |
| `GameVersion.__ge__` | `version_registry.version.GameVersion.__ge__` | `GameVersion` | method |
| `GameVersion.__gt__` | `version_registry.version.GameVersion.__gt__` | `GameVersion` | method |
| `GameVersion.__hash__` | `version_registry.version.GameVersion.__hash__` | `GameVersion` | method |
| `GameVersion.__init__` | `version_registry.version.GameVersion.__init__` | `GameVersion` | method |
| `GameVersion.__le__` | `version_registry.version.GameVersion.__le__` | `GameVersion` | method |
| `GameVersion.__lt__` | `version_registry.version.GameVersion.__lt__` | `GameVersion` | method |
| `GameVersion.same_major` | `version_registry.version.GameVersion.same_major` | `GameVersion` | method |
| `MatchConfidence.__eq__` | `version_registry.matching.MatchConfidence.__eq__` | `MatchConfidence` | method |
| `MatchConfidence.__hash__` | `version_registry.matching.MatchConfidence.__hash__` | `MatchConfidence` | method |
| `MatchConfidence.is_high_confidence` | `version_registry.matching.MatchConfidence.is_high_confidence` | `MatchConfidence` | method |
| `VersionInfo.__eq__` | `version_registry.models.VersionInfo.__eq__` | `VersionInfo` | method |
| `VersionInfo.__hash__` | `version_registry.models.VersionInfo.__hash__` | `VersionInfo` | method |
| `VersionInfo.get_compatible_crashgens` | `version_registry.models.VersionInfo.get_compatible_crashgens` | `VersionInfo` | method |
| `VersionInfo.get_crashgen_for_version` | `version_registry.models.VersionInfo.get_crashgen_for_version` | `VersionInfo` | method |
| `VersionInfo.get_crashgen_version_strings` | `version_registry.models.VersionInfo.get_crashgen_version_strings` | `VersionInfo` | method |
| `VersionInfo.is_compatible_with` | `version_registry.models.VersionInfo.is_compatible_with` | `VersionInfo` | method |
| `VersionRegistry.__init__` | `version_registry.registry.VersionRegistry.__init__` | `VersionRegistry` | method |
| `XseConfig` | `version_registry.models.XseConfig` | `XseConfig` | class |

### 1 Tier-2 runtime-verified migration

| Python path | ID | rustSymbol | pythonKind |
|-------------|----|-----------:|------------|
| `GameVersion.semantic_distance` | `version_registry.version.GameVersion.semantic_distance` | `GameVersion` | method |

Source: `python-tier2-version-registry-runtime` registry entry — 1 binding. **Entry is DELETED outright** in Task 4 since all its bindings are promoted.

## Smoke test planning (Task 3)

Target: ~12 tests. Match Plan 06 style — fixture-backed via `get_version_registry()` singleton since most PyO3 wrappers have NO `#[new]` constructor.

Approach:
1. **VersionRegistry construction** — trivial, has `#[new]`
2. **GameVersion construction + dunders** — `GameVersion("1.10.163.0")` works directly; exercise `__eq__`, `__lt__`, `__hash__`, `same_major`, `semantic_distance`
3. **MatchConfidence classattrs + `is_high_confidence`** — access `MatchConfidence.EXACT == "exact"` etc.
4. **Fetch real VersionInfo via singleton** — `registry.get_by_id("FO4_OG")` returns a real `VersionInfo` — exercise `id`, `version`, `display_name`, `__eq__`, `__hash__`, `get_crashgen_version_strings()`, `is_compatible_with()`, `get_compatible_crashgens()`, `get_crashgen_for_version()`
5. **Fetch real AddressLibraryConfig** — `og.address_library` returns `AddressLibraryConfig` — exercise `filename`, `format`, `nexus_url`
6. **Fetch real XseConfig** — `og.xse` returns `XseConfig` — exercise `acronym`, `full_name`, `script_hashes`
7. **Fetch real CrashgenConfig** — `og.crashgen_versions[0]` returns `CrashgenConfig` — exercise `version`, `name`, `is_compatible_with()`
8. **Fetch real CompatibleRange** — `og.compatible_range` returns `CompatibleRange` — exercise `min_version`, `max_version`, `contains()`
9. **Fetch real UnknownVersionHandling** — `registry.unknown_version_handling` returns `UnknownVersionHandling` — exercise `strategy` (string), `log_level` (string), `defaults` (dict), `get_default()`
10. **MatchResult via matcher call** — `registry.match_version("1.10.163.0", "Fallout4", False)` returns `MatchResult` — exercise `version_info`, `confidence`, `is_exact`, `is_valid`
11. **Pitfall 2 guard** — assert all 10 rust-only symbols present in `rust_api_surface.json`
12. **VersionRegistryError existence check** — verify the symbol exists in `rust_api_surface.json` (not a Python-side Exception class, since no `create_exception!` is used in -py)

## Runtime registry updates (Task 4)

1. `python-tier1-version-registry` selector: bump `contractCount` from 24 to **59** (24 + 35) and recompute `contractIdsHash`.
2. `python-tier2-version-registry-runtime`: **DELETE** (1 binding, now promoted).
3. Add `python-tier1-version-registry-plan07-promoted` aux entry with 12 `bindingIdentifiers` pointing at `test_promoted_version_registry_smoke.py` (matches Plan 06 pattern).

## Final tier1Mappings count

- Before: 314
- +35 Plan 07 rows
- **After: 349** (NOT 347 as plan scaffold says — the scaffold math was based on Plan 06's expected 312, but Plan 06 actually landed at 314)

This will be documented as a Rule 1 deviation in the SUMMARY (counted drift matches Plan 06's precedent).
