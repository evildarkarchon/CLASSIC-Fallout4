---
phase: 03-python-tier-collapse
plan: 06
purpose: Pre-task inventory of classic-config-core + classic-config-py surface, verified against source before authoring contract rows or tests
created: 2026-04-08
---

# Plan 06 Config Promotion — Constructor & Source Inventory

## Verification Method

All signatures below were read directly from source (not guessed). Each entry cites the file:line.

---

## classic-config-core surface (lib.rs re-exports)

Verified from `ClassicLib-rs/business-logic/classic-config-core/src/lib.rs:16-21` and `:17-21`:

```rust
pub use config::{ClassicConfig, PathConfig, YamlSource};
pub use yamldata::{
    ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, ModConflictEntry,
    ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackCountRule,
    SuspectStackRule, YamlDataCore, format_registry_game_version, resolve_registry_version_info,
};
```

Per A3: every deferred config symbol is already `pub use`d at lib.rs. **No new re-exports needed.**

Additional module markers visible at lib.rs root: `config` (sub-module), `yamldata` (sub-module) — both parsed as `rustSymbol` by `generate_baseline.py::parse_rust_surface()`. `get_runtime` re-export exists at lib.rs:24.

---

## classic-config-py surface (pyclass inventory)

Verified from `ClassicLib-rs/python-bindings/classic-config-py/src/lib.rs` (full read):

| Python name (via `#[pyclass(name=...)]`) | Rust struct | Core type wrapped | Constructor |
|---|---|---|---|
| `PathConfig` | `PyPathConfig` (line 279) | `PathConfig` (core) | `__init__(ini_folder=None, scan_custom=None, mods_folder=None, game_root=None, docs_root=None)` — 5 Optional args (line 292) |
| `YamlSource` | `PyYamlSource` (line 371) | `YamlSource` (core enum) | No `__init__`; uses 7 `#[classattr]` constants (MAIN, SETTINGS, IGNORE, GAME, GAME_LOCAL, TEST, CACHE) |
| `ClassicConfig` | `PyClassicConfig` (line 481) | `ClassicConfig` (core) | `__new__` with no args; factories: `load_from_yaml(path)`, `load_or_default()` |
| `YamlData` | `PyYamlData` (line 688) | `YamlDataCore` | `__init__(yaml_dirs: Vec<PathBuf>, game: String, game_version: String)` (line 697); also `from_yaml_content(main_content, game_content, ignore_content, game, game_version)` staticmethod (line 735) |

**Top-level functions (visible to Python surface parser):**
- `create_yamldata(yaml_dirs, game, game_version) -> PyYamlData` (line 1064) — factory wrapper
- `clear_yaml_cache()` (line 1079)
- `set_application_dir(path: String)` (line 1098)
- `get_application_dir() -> Option<String>` (line 1107)

**Exception classes (registered in `#[pymodule]`):**
- `RustConfigError`, `RustConfigIOError`, `RustConfigParseError` (via `define_exceptions!` macro at line 198) — already in existing tier1 row `config-clear-yaml-cache`? No, not yet in tier1Mappings. These are typically excluded as dynamic exceptions.

**PyO3 #[pymodule] registration (`classic_config` function, line 1113-1131):**
- 4 classes: `PyYamlData`, `PyPathConfig`, `PyYamlSource`, `PyClassicConfig`
- 4 functions: `create_yamldata`, `clear_yaml_cache`, `set_application_dir`, `get_application_dir`
- 3 exceptions: `RustConfigError`, `RustConfigIOError`, `RustConfigParseError`

---

## CRITICAL DISCOVERY: No PyO3 wrappers for CrashgenEntryRaw/ModConflictEntry/SuspectErrorRule/etc.

The plan's `<interfaces>` block assumes `CrashgenEntryRaw`, `CoreModEntry`, `CoreModExclude`, `ModConflictEntry`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackRule`, `SuspectStackCountRule` are all promoted `#[pyclass]` types.

**Reality:** NONE of these types have `#[pyclass]` wrappers in `classic-config-py`. Instead they are converted to `dict`/`list` structures inside `PyYamlData` getters (`suspect_error_rules`, `game_mods_conf`, etc.). See `classic-config-py/src/lib.rs:894-1014` for the conversion patterns.

**Consequence:** These types cannot be contract rows with `pythonKind="class"` pointing at a Python class name. They must use the **@rust-suffixed proxy row pattern** established by Wave 1 / Wave 3a, pairing the rust symbol with the nearest Python class (`YamlData`).

---

## Deferred backlog — 26 config entries verified

Verified from `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json` filtered to `ownerModule == "config"`:

### Rust-only entries (15) → @rust-suffixed proxy rows

| coverageId | rustSymbol | Disposition |
|---|---|---|
| python-deferred-config-001 | `ConfigError` | @rust proxy, pair with `YamlData` |
| python-deferred-config-002 | `CoreModEntry` | @rust proxy, pair with `YamlData` |
| python-deferred-config-003 | `CoreModExclude` | @rust proxy, pair with `YamlData` |
| python-deferred-config-004 | `CrashgenEntryRaw` | @rust proxy, pair with `YamlData` |
| python-deferred-config-005 | `ModConflictEntry` | @rust proxy, pair with `YamlData` |
| python-deferred-config-006 | `ModSolutionCriteria` | @rust proxy, pair with `YamlData` |
| python-deferred-config-007 | `ModSolutionEntry` | @rust proxy, pair with `YamlData` |
| python-deferred-config-008 | `SuspectErrorRule` | @rust proxy, pair with `YamlData` |
| python-deferred-config-009 | `SuspectStackCountRule` | @rust proxy, pair with `YamlData` |
| python-deferred-config-010 | `SuspectStackRule` | @rust proxy, pair with `YamlData` |
| python-deferred-config-011 | `config` (module marker) | @rust proxy, pair with `ClassicConfig` (the class named after the module) |
| python-deferred-config-012 | `format_registry_game_version` | @rust proxy, function kind, pair with `create_yamldata` proxy |
| python-deferred-config-013 | `get_runtime` | @rust proxy, function kind, pair with `clear_yaml_cache` proxy |
| python-deferred-config-014 | `resolve_registry_version_info` | @rust proxy, function kind, pair with `create_yamldata` proxy |
| python-deferred-config-015 | `yamldata` (module marker) | @rust proxy, pair with `YamlData` |

### Python-only entries (11) → regular python rows

| coverageId | bindingIdentifier | → pythonExportPath | Disposition |
|---|---|---|---|
| python-deferred-config-479 | `classic_config.ClassicConfig.__init__` | `ClassicConfig.__init__` | method, rust=`ClassicConfig` |
| python-deferred-config-480 | `classic_config.ClassicConfig.__repr__` | `ClassicConfig.__repr__` | method, rust=`ClassicConfig` |
| python-deferred-config-481 | `classic_config.PathConfig.__init__` | `PathConfig.__init__` | method, rust=`PathConfig` |
| python-deferred-config-482 | `classic_config.PathConfig.__repr__` | `PathConfig.__repr__` | method, rust=`PathConfig` |
| python-deferred-config-483 | `classic_config.YamlData.__init__` | `YamlData.__init__` | method, rust=`YamlDataCore` |
| python-deferred-config-484 | `classic_config.YamlData.__repr__` | `YamlData.__repr__` | method, rust=`YamlDataCore` |
| python-deferred-config-485 | `classic_config.YamlSource.__eq__` | `YamlSource.__eq__` | method, rust=`YamlSource` |
| python-deferred-config-486 | `classic_config.YamlSource.__hash__` | `YamlSource.__hash__` | method, rust=`YamlSource` |
| python-deferred-config-487 | `classic_config.YamlSource.__repr__` | `YamlSource.__repr__` | method, rust=`YamlSource` |
| python-deferred-config-488 | `classic_config.YamlSource.__str__` | `YamlSource.__str__` | method, rust=`YamlSource` |
| python-deferred-config-489 | `classic_config.create_yamldata` | `create_yamldata` | function, rust=`create_yamldata` (free fn in -py only — pair via proxy) |

**Note:** `create_yamldata` is a -py convenience function with no matching -core symbol. Per Wave 3a precedent for `CancellationToken` (pure -py wrapper), pair with the closest -core symbol `YamlDataCore`.

---

## Tier-2 runtime-verified migration analysis (per Task 4)

Verified from `ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json`:

| coverageId | bindingIdentifiers | Surface-visible? | Disposition |
|---|---|---|---|
| `python-tier2-config-runtime` | `classic_config.YamlData.classic_version`, `classic_config.YamlData.warn_outdated` | **NO** — both are `@property` methods; Python surface parser skips `@property` (see `generate_baseline.py::_is_property_decorator` line 378) | **PRESERVE entry** — cannot become tier1 rows. Deleting would orphan runtime coverage per Wave 3a precedent |
| `python-tier2-config-application-dir-runtime` | `classic_config.get_application_dir`, `classic_config.set_application_dir` | **YES** — both are top-level `#[pyfunction]`s, visible as `function` kind in Python surface | **PROMOTE** — delete tier-2 entry, add 2 new tier1Mapping rows |

**Verification evidence for property-skip:**
- `ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi:120-122` — `classic_version` declared with `@property` decorator
- `ClassicLib-rs/python-bindings/classic-config-py/classic_config.pyi:284-286` — `warn_outdated` same
- `docs/implementation/python_api_parity/baseline/python_api_surface.json` filtered to `classic_config.YamlData.*` produces only `__init__`, `__repr__`, `from_yaml_content` — no `classic_version` or `warn_outdated`
- `tools/python_api_parity/generate_baseline.py:378-385` — `_is_property_decorator` skips `@property`/`.setter`/`.deleter`

---

## Row count math reconciliation

Plan says: 22 deferred + 4 tier-2 = 26 new rows, final tier1Mappings = 312.

**Actual ground truth:**
- Deferred backlog has **26** config entries (plan regen in Plan 01 grew raw count from 22 → 26). The plan's "22" is from RESEARCH.md A4 using pre-regen counts.
- 4 tier-2 bindings: 2 are promotable (`get_application_dir`, `set_application_dir`), 2 are not (property-based `classic_version`, `warn_outdated`) per Wave 3a precedent.
- Net new tier1 rows: **26 + 2 = 28**
- Final tier1Mappings: **286 + 28 = 314**

The plan's numbers (22 + 4 = 26 → 312) reflect stale pre-Plan-01 backlog counts and an unverified assumption about property-based tier-2 bindings. Executor adopts ground truth per Wave 3a precedent documented as a Rule 1 deviation.

---

## Test fixture strategy — fixture-backed construction (R1)

**R1 HIGH constraint:** Smoke tests must construct real instances, not `hasattr`-only checks.

**Constructable #[pyclass] types (4):**
- `PathConfig()` — all-Optional args, constructs trivially
- `ClassicConfig()` — no-args constructor, constructs trivially
- `YamlData.from_yaml_content(main, game, ignore, game_id, version)` — deserialization path; real fixture route
- `YamlSource.MAIN`, etc. — classattr constants; test equality/display

**Rust-only types that have NO Python constructor:**
- `CrashgenEntryRaw`, `CoreModEntry`, `CoreModExclude`, `ModConflictEntry`, `ModSolutionCriteria`, `ModSolutionEntry`, `SuspectErrorRule`, `SuspectStackRule`, `SuspectStackCountRule`
- These are **only surfaced as dict items inside YamlData getters**. Cannot be constructed from Python.
- Smoke tests exercise them by loading a fixture YAML via `YamlData.from_yaml_content(...)` and asserting the relevant getter returns a list (even if empty, since the minimal fixture may not trigger all rule types).

**Fixture YAML baseline:**

The minimal YAML must satisfy `YamlDataCore::from_yaml_content` — which takes `main_content`, `game_content`, `ignore_content` as three separate strings (NOT a single merged YAML).

Required top-level keys (verified from `classic-config-core/src/yamldata.rs` full scan would take too long — use minimal valid strings and rely on from_yaml_content's lenient parser, or fall back to constructing individual classes where possible).

**Fallback strategy:** If `from_yaml_content` fails on minimal YAML, use the existing `PARITY_MAIN_YAML` / `PARITY_GAME_YAML` fixtures from `test_tier1_parity_smoke.py` which are already known-valid.

---

## Expected test count

Target: ~11 pytest functions covering:

1. `test_path_config_constructs_and_reprs` — direct construction + __repr__
2. `test_classic_config_default_constructs` — no-args constructor + __repr__
3. `test_yaml_source_classattrs_exist` — 7 classattr constants + __eq__/__hash__/__str__/__repr__
4. `test_yaml_source_path_and_display_name` — method calls
5. `test_yaml_data_from_yaml_content_fixture` — deserialization via real fixture
6. `test_yaml_data_getters_return_lists` — exercise the dict-backed rule getters (suspect_error_rules, game_mods_conf, etc.)
7. `test_create_yamldata_factory_function` — free function call
8. `test_clear_yaml_cache_call` — free function call
9. `test_get_set_application_dir_roundtrip` — tier-2 migration functions
10. `test_rust_only_symbols_in_core_surface` — Pitfall 2 guard: assert all 15 rust-only symbols exist in classic-config-core surface
11. `test_config_exception_classes_importable` — RustConfigError hierarchy

Each test exercises real behavior — no hasattr-only checks.

---

## Risks and open items

- **Plan's row math assumed 22 deferred, actual is 26.** Adopted ground truth; final tier1Mappings target will be 314 not 312.
- **Plan assumed property-based tier-2 bindings are promotable.** They are not; preserve `python-tier2-config-runtime`.
- **`from_yaml_content` minimum valid YAML** is not yet verified. Fallback plan: use known-working `PARITY_MAIN_YAML` fixture from `test_tier1_parity_smoke.py`.
- `CrashgenEntryRaw` etc. can only be exercised indirectly through YamlData getter output. This is structurally unavoidable — the executor follows Wave 3a precedent (rust-only symbols verified via `test_rust_only_symbols_in_core_surface` Pitfall 2 guard).
