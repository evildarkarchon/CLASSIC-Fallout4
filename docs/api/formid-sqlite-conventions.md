# FormID SQLite Schema And Path Conventions

Contributor-facing notes for creating, loading, and debugging FormID SQLite databases in current CLASSIC source.

This page is narrower than the full crate guides in [`classic-database-core.md`](classic-database-core.md), [`classic-config-core.md`](classic-config-core.md), and [`classic-scanlog-core.md`](classic-scanlog-core.md). It focuses on the concrete schema, path, and lookup assumptions contributors need when building fixtures or tracing missing FormID descriptions. For the separate settings-shape mismatch between config serialization and scan startup, see [`formid-settings-boundary.md`](formid-settings-boundary.md).

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this page when you need to:

- create SQLite fixtures for `classic-database-core` or downstream scanlog tests
- understand which table and columns current Rust code expects
- trace how multiple FormID database files are assembled at scan startup
- debug why a `(formid, plugin)` lookup did or did not resolve

This page documents behavior visible in active source today. Where the repo only implies behavior, the text calls that out as implementation-defined rather than a stable contract.

---

## Current SQLite Lookup Shape

`classic-database-core` does not ship migrations or a schema builder, but its source and tests make the current lookup shape clear.

Expected table shape:

- table name: caller-provided game table such as `Fallout4` or `Skyrim`
- required columns: `formid`, `plugin`, `entry`
- current query code reads all three columns as `String`

The test fixture shape used in both crate-local and integration tests is:

```sql
CREATE TABLE IF NOT EXISTS Fallout4 (
    formid TEXT NOT NULL,
    plugin TEXT NOT NULL,
    entry TEXT NOT NULL,
    PRIMARY KEY (formid, plugin)
)
```

Source-backed notes:

- `get_entry()` issues `SELECT entry FROM {table} WHERE formid=? AND plugin=?`, then retries with `COLLATE nocase` on `plugin`
- `get_entries_batch()` issues repeated `SELECT formid, plugin, entry FROM {table} WHERE formid=? AND plugin=?` clauses joined by `UNION ALL`, then does the same `COLLATE nocase` fallback for unresolved pairs
- current code is optimized around `(formid, plugin)` lookups; the composite primary key used in tests matches that access pattern
- `FormIdValueLookup` uses private strict variants of those single and batch queries so SQL and row-decoding failures remain errors rather than missing values

Implementation-defined caveat:

- the code requires those column names and string-compatible values, but it does not formally validate the schema up front; a malformed table fails only when queried

---

## Lookup Keys And Matching Rules

At the database-core layer, the lookup key is `(table, formid, plugin)`.

Current matching behavior:

- `formid` is matched exactly as passed
- `plugin` is tried twice: exact case first, then `COLLATE nocase`
- cache keys normalize `plugin` to lowercase, so `Fallout4.esm` and `FALLOUT4.ESM` share cache entries
- batch results are returned as `HashMap<String, String>` keyed by `"{formid}:{plugin}"`

Important downstream detail from [`business-logic/classic-scanlog-core/src/formid_analyzer.rs`](../../business-logic/classic-scanlog-core/src/formid_analyzer.rs): scanlog does not query the full raw crash-log FormID. It strips the load-order prefix first.

- regular plugins: first 2 hex characters are treated as the plugin prefix
- light plugins: first 5 hex characters (`FE` plus 3-digit light index) are treated as the plugin prefix
- the remaining suffix is what gets passed to `DatabasePool::get_entry()` / `get_entries_batch()`

Grounded example from current scanlog behavior:

- crash log FormID `02000800` with plugin prefix `02 -> SomeMod.esp`
- database lookup pair becomes `(000800, SomeMod.esp)`

That suffix-only rule is not a generic `classic-database-core` requirement. It is the current `classic-scanlog-core` integration behavior.

---

## Table Selection Rules

`DatabasePool` always queries one table name at a time.

Current rules:

- `DatabasePool::new(..., game_table)` sets the default table name
- `get_entry(..., table)` and `get_entries_batch(..., table, ...)` use the explicit `table` argument when provided
- otherwise they use the pool's current `game_table`
- `set_game_table()` changes that default for later calls

Contributor caveat:

- table names are interpolated directly into SQL strings; current code assumes trusted internal table names, not arbitrary untrusted input

---

## How Multiple Database Paths Are Configured

`classic-user-settings-core` exclusively owns the persisted per-game path map at `CLASSIC_Settings.FormID Databases`. Maintained frontends select the active game's ordered strings and pass them into scan startup as explicit facts; scan-time code does not reopen or interpret User Settings.

## Active scan-time path assembly in `classic-cpp-bridge`

The current C++ bridge is what actually assembles DB paths for production scan startup.

[`cpp-bindings/classic-cpp-bridge/src/scanner.rs`](../../cpp-bindings/classic-cpp-bridge/src/scanner.rs) receives the frontend-selected configured entries as explicit request facts and resolves paths in this order:

1. main DB: `CLASSIC Data/databases/{game-data-identity} FormIDs Main.db` (`Fallout4VR` shares `Fallout4 FormIDs Main.db`)
2. hardcoded extras from `hardcoded_formid_db_relpaths(game)`
3. caller-projected configured entries from `CrashLogScanFacts.formid_database_paths`
4. de-duplicate while preserving first occurrence

Current hardcoded extras:

- `Fallout4` and `Fallout4VR` automatically add `databases/FOLON FormIDs.db`
- other games currently add no hardcoded extra DBs

This means an explicitly empty user list for `Fallout4` still resolves to:

- `CLASSIC Data/databases/Fallout4 FormIDs Main.db`
- `CLASSIC Data/databases/FOLON FormIDs.db`

That behavior is covered by bridge tests.

---

## Path Resolution Rules

Current scan-time path handling in `classic-cpp-bridge`:

- user-configured absolute DB paths are used as-is after normalization
- user-configured relative DB paths are resolved against `yaml_dir_data` (the `CLASSIC Data` directory), not the User Settings directory or repo root
- path normalization is component-based (`path.components().collect()`), mainly for de-duplication and path-shape cleanup

Grounded example from bridge tests:

```yaml
CLASSIC_Settings:
  FormID Databases:
    Fallout4:
      - databases/FOLON FormIDs.db
      - databases/custom.db
```

With `yaml_dir_data = <root>/CLASSIC Data`, that resolves to:

- `<root>/CLASSIC Data/databases/Fallout4 FormIDs Main.db`
- `<root>/CLASSIC Data/databases/FOLON FormIDs.db`
- `<root>/CLASSIC Data/databases/custom.db`

Source-backed caveats:

- de-duplication is path-based, not content-based
- normalization does not canonicalize case or resolve symlinks
- existence is not checked during bridge path assembly
- missing files are filtered later by `DatabasePool::initialize()` with a warning instead of an error

---

## How Downstream Code Uses The Databases

The active Rust path is:

1. A final-contract request supplies typed scan facts; Rust-owned Crash Log Scan
   Intake builds the private analysis configuration and resolves DB file paths.
2. If `show_formid_values` is `true`, it creates a `DatabasePool` and calls `initialize(resolved_paths)`.
3. The private scan-run engine attaches that pool before analyzing admitted logs.
4. `FormIDFindingAnalyzer::analyze()` batches resolved `(formid_suffix, plugin)` pairs through the strict `FormIdValueLookup` facade.
5. Report lines include the description only when a lookup succeeds.

Fail-soft behavior visible in source:

- if `show_formid_values` is `false`, no DB pool is attached
- if no DB pool is attached, scanlog still reports FormIDs without descriptions
- if some DB files are missing, initialization still succeeds if at least one usable file remains
- if per-database queries fail, lookup continues against other pools and unresolved rows simply render without descriptions

The owned `FormIdValueLookup` facade consumed by semantic FormID Finding Analysis does not use that fail-soft rule. Its disabled, missing, and found states are semantic outcomes; malformed values and database failures have distinct typed error codes that the analyzer projects into the shared analyzer error envelope.

---

## Limits And Non-Contract Behavior

These details are visible in source today, but contributors should treat them carefully.

- cross-database precedence is not a documented contract; the first row encountered wins
- because lookups iterate `DashMap` pool entries, contributors should not rely on a stable precedence order between separate DB files when duplicate `(formid, plugin)` rows exist
- `DatabasePool::initialize()` sorts and de-duplicates the requested path list for connection-allocation planning, but lookup iteration order should still be treated as implementation-defined
- uninitialized or closed pools return `Ok(None)` for lookups instead of a hard error
- a strict facade over such a pool can still represent a genuine no-row result as `Missing`, but any SQL or row-decode failure encountered by the strict query becomes `operational_failure`
- missing DB files do not surface `DatabaseError::NotFound` in the normal initialization path; they are logged and skipped
- `optimize()` currently runs `ANALYZE` only; `VACUUM` is not attempted because pools are opened read-only
- scan-time DB opening uses read-only SQLite connections with `synchronous=NORMAL`, `cache_size=10000`, `temp_store=MEMORY`, and `mmap_size=30000000`

Practical fixture rule: if you need deterministic tests across multiple DB files, avoid storing the same `(formid, plugin)` in more than one database unless the test is explicitly about duplicate handling.

---

## Fixture Checklist

When building a new FormID fixture, use this checklist:

- create a table whose name matches the pool's `game_table` or the explicit table override you will query
- include `formid TEXT`, `plugin TEXT`, and `entry TEXT`
- prefer a composite primary key on `(formid, plugin)` to match current query/index assumptions
- store the same `plugin` spelling you expect from the caller, even though runtime has a `nocase` fallback
- for scanlog-driven tests, store the FormID suffix that remains after load-order prefix stripping, not the full crash-log value
- if testing multi-DB behavior, remember that missing files are skipped and duplicate row precedence is not a stable contract

---

## Related Docs

- [`classic-database-core.md`](classic-database-core.md) - full pool API, cache behavior, and query flow
- [`classic-config-core.md`](classic-config-core.md) - runtime config and YAML loading surface
- [`classic-scanlog-core.md`](classic-scanlog-core.md) - downstream scan pipeline and FormID analysis path
