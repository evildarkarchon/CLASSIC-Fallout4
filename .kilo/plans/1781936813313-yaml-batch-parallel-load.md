# Plan: Parallelize `load_yaml_files_batch` with rayon

## Context

`YamlOperations::load_yaml_files_batch` in
`business-logic/classic-settings-core/src/yaml_ops/operations.rs` documents that it
"loads multiple YAML files **in parallel**" (lines 348-349) but the implementation
(lines 377-381) iterates sequentially with a `for` loop over `self.load_yaml_file`.

**Finding status: VALID** — doc/impl mismatch.

**Chosen direction:** Parallelize the implementation with `rayon` so behavior matches
the existing documentation (instead of rewriting the doc to say "sequential").

### Why this is safe to parallelize
- `YamlOperations` holds only `cache_enabled: bool`, so `&self` is `Sync`.
- `load_yaml_file` is already concurrency-safe: the global cache is
  `quick_cache::sync::Cache` (`yaml_ops/cache.rs:15`), hit/miss counters are atomics
  (`Ordering::Relaxed`), and it uses `std::fs` + `YamlLoader`.
- `yaml_rust2::Yaml` is `Send + Sync`, so values can be collected across threads.
- `rayon = "1.12.0"` already exists in the workspace dependency table
  (`Cargo.toml:70`); sibling crates use `rayon = { workspace = true }`
  (`classic-file-io-core`, `classic-scangame-core`, `classic-scanlog-core`).

## Tasks

1. **Add the dependency.**
   In `business-logic/classic-settings-core/Cargo.toml`, under `[dependencies]`
   (the "Performance" / thread-safety area near `parking_lot` / `dashmap`), add:
   ```toml
   # Data parallelism
   rayon = { workspace = true }
   ```

2. **Add the rayon prelude import** to
   `business-logic/classic-settings-core/src/yaml_ops/operations.rs` (top-level `use`
   block, near the other `use` statements):
   ```rust
   use rayon::prelude::*;
   ```

3. **Rewrite `load_yaml_files_batch`** (current body at lines 374-384) to use a
   parallel iterator:
   ```rust
   pub fn load_yaml_files_batch(&self, paths: &[&Path]) -> HashMap<String, Yaml> {
       paths
           .par_iter()
           .filter_map(|path| {
               self.load_yaml_file(path)
                   .ok()
                   .map(|yaml| (path.to_string_lossy().into_owned(), yaml))
           })
           .collect()
   }
   ```
   - Files that fail to load are dropped via `filter_map` (same contract as today).
   - Result is a `HashMap`, so the unordered parallel collection is functionally
     equivalent to the sequential version.

4. **Keep the doc comment** (lines 346-350). It is now accurate. Optional minor polish:
   note that the speedup applies to larger batches; not required.

5. **(Optional) Add a larger-batch test** in
   `business-logic/classic-settings-core/src/yaml_ops/operations_tests.rs` that loads
   ~8 temp files and asserts `results.len() == 8` and a couple of `contains_key`
   checks. Per AGENTS.md rule #10, tests stay in this sibling file (already wired via
   `#[path = "operations_tests.rs"] mod tests;`). Mark `#[serial_test::serial]` to match
   the existing batch/cache tests.

## Edge cases / notes

- **Duplicate input paths:** parallel `collect` into `HashMap` keeps one entry
  arbitrarily on key collision, vs. sequential last-wins. Since duplicates resolve to
  the same file (identical value), there is no observable difference. Note only — no
  handling required.
- **Existing tests remain valid:** `test_load_yaml_files_batch`
  (`operations_tests.rs:183`) and `test_load_yaml_files_batch_with_missing`
  (`operations_tests.rs:202`) assert via `.len()` / `.contains_key()` — order
  independent — so they pass unchanged under parallel collection.
- **Small batches:** rayon thread-pool overhead can make tiny batches no faster (or
  marginally slower) than sequential. Acceptable; the goal is matching the documented
  parallel behavior, and config batches here are small.

## Validation

Run from repo root (pure business-logic crate, no pyo3 in its subgraph, so no
`PYO3_PYTHON` setup needed for these `-p`-scoped commands):

- `cargo build -p classic-settings-core`
- `cargo clippy -p classic-settings-core --all-targets` (crate denies `unused` /
  `deprecated` — confirm the new `use` is actually used and warning-free)
- `cargo test -p classic-settings-core` (runs the sibling unit tests, incl. both batch
  tests + any new one)
- `cargo test -p classic-settings-core --doc` (the method's `rust,no_run` doc example)

## Rollback

Single-crate, two-file change. Revert the `Cargo.toml` dependency line and restore the
sequential `for` loop in `load_yaml_files_batch` to fully undo.

## Open questions

None blocking. Optional: whether to include task 5 (larger-batch test) — recommended
but not required for correctness.
