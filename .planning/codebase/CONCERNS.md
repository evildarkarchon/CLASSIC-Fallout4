# Codebase Concerns

**Analysis Date:** 2026-04-14

## Tech Debt

**Monolithic orchestration and config modules:**
- Issue: Core behavior is concentrated in a small set of very large files, which makes review, isolation, and safe refactoring difficult.
- Files: `business-logic/classic-config-core/src/yamldata.rs`, `business-logic/classic-scanlog-core/src/orchestrator.rs`, `business-logic/classic-settings-core/src/yaml_ops.rs`, `business-logic/classic-database-core/src/pool_sqlx.rs`, `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `classic-gui/src/app/mainwindow.cpp`
- Impact: Small behavior changes can create broad regressions because parsing, orchestration, caching, DTO conversion, and UI coordination live in the same compilation units.
- Fix approach: Split by subdomain. Keep parsing, rule loading, report assembly, cache policy, and UI wiring in separate modules with narrow interfaces and targeted tests.

**Manual multi-language binding duplication:**
- Issue: Python, Node, and C++ bindings manually mirror large Rust surfaces and DTO conversions instead of sharing generated adapters.
- Files: `python-bindings/classic-config-py/src/lib.rs`, `python-bindings/classic-scanlog-py/src/orchestrator.rs`, `node-bindings/classic-node/src/config.rs`, `node-bindings/classic-node/src/fileio.rs`, `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `cpp-bindings/classic-cpp-bridge/src/files.rs`
- Impact: Parity drift remains an ongoing maintenance cost. Every API change must be repeated in multiple wrappers, which raises the chance of inconsistent behavior and stale docs.
- Fix approach: Centralize DTO conversion and expose smaller shared helper layers per domain. Prefer generation for repetitive getter/setter surfaces where possible.

**GUI tests coupled to source text instead of runtime behavior:**
- Issue: Multiple GUI tests read production source files and assert on string or regex matches rather than exercising compiled behavior.
- Files: `classic-gui/tests/test_scan_settings_wiring.cpp`, `classic-gui/tests/test_mainwindow_geometry.cpp`, `classic-gui/src/app/mainwindow.cpp`, `classic-gui/src/controllers/scancontroller.cpp`, `classic-gui/src/workers/scanworker.cpp`
- Impact: Safe refactors can fail tests even when behavior stays correct, and behavior can still break if the expected text remains present but runtime wiring changes elsewhere.
- Fix approach: Replace text-inspection assertions with object-level tests that instantiate controllers, emit signals, and verify observable state transitions.

## Known Bugs

**Node batch file reads collapse failures into empty strings:**
- Symptoms: A missing or unreadable file becomes indistinguishable from a real empty file when using the Node batch file API.
- Files: `node-bindings/classic-node/src/fileio.rs`, `business-logic/classic-file-io-core/src/core.rs`
- Trigger: Call `read_multiple_files()` on one or more unreadable, missing, or locked paths.
- Workaround: Use per-file `read_file()` calls when the caller must distinguish I/O failure from empty content.

**Database lookup path degrades silently on per-database failures:**
- Symptoms: FormID lookup can return incomplete results while only logging query failures, which makes bad data look like a legitimate miss.
- Files: `business-logic/classic-database-core/src/pool_sqlx.rs`
- Trigger: One of the configured SQLite databases is missing, locked, malformed, or otherwise query-failing during `get_entry()` or batch lookup.
- Workaround: Inspect logs and database health when lookup quality suddenly drops; current API behavior does not surface partial-failure state to callers.

## Security Considerations

**Bindings expose unrestricted filesystem access:**
- Risk: Public Node, Python, and C++ file APIs accept arbitrary caller-provided paths for reads and writes without root scoping or canonical-path allowlisting.
- Files: `business-logic/classic-file-io-core/src/core.rs`, `node-bindings/classic-node/src/fileio.rs`, `python-bindings/classic-file-io-py/src/lib.rs`, `cpp-bindings/classic-cpp-bridge/src/files.rs`
- Current mitigation: Errors rely on OS filesystem permissions and per-call error handling.
- Recommendations: Add optional root-directory confinement, canonicalization checks, and explicit "unsafe arbitrary path" APIs so embedded consumers cannot accidentally expose the full host filesystem.

**Updater library reads ambient `.env` from current working directory:**
- Risk: Library construction has side effects and may pick up a `GITHUB_TOKEN` from whatever directory the host process happens to run in.
- Files: `business-logic/classic-update-core/src/github.rs`
- Current mitigation: Token use is optional and only attached to GitHub requests when present.
- Recommendations: Remove automatic cwd `.env` loading from library code. Require explicit token injection from the application layer or a controlled config path.

## Performance Bottlenecks

**Crash-log orchestration duplicates large amounts of string data per scan:**
- Problem: The scan pipeline materializes multiple derived copies of the same log data (`processed_lines`, `combined_crash_lines`, `combined_crash_text`, lowercased copies, plugin lists, system lists) before analysis completes.
- Files: `business-logic/classic-scanlog-core/src/orchestrator.rs`
- Cause: `ScanAnalysisContext` stores several owned `Vec<String>` and derived `String` snapshots for convenience instead of reusing shared slices or lazy views.
- Improvement path: Keep shared `Arc<str>`/slice-based representations longer, lowercase lazily, and let analyzers consume borrowed views instead of whole duplicated collections.

**Batch scan concurrency can oversubscribe low-core machines:**
- Problem: Default batch concurrency bottoms out at 4 when log count exceeds CPU count, even on systems with fewer than 4 cores.
- Files: `business-logic/classic-scanlog-core/src/orchestrator.rs`
- Cause: `resolve_batch_concurrency()` uses `num_cpus.max(4)` for the default path.
- Improvement path: Cap default concurrency at detected CPU count unless the caller explicitly opts into a higher value.

**Database cache eviction scales with full-cache scans and sort passes:**
- Problem: Cache maintenance work grows sharply as query cache size increases.
- Files: `business-logic/classic-database-core/src/pool_sqlx.rs`
- Cause: `evict_to_target()` retains over the full `DashMap`, then builds and sorts eviction candidates to remove oldest entries.
- Improvement path: Replace bulk retain-and-sort eviction with segmented LRU/FIFO structures or background maintenance that does not require full-map ordering work on hot paths.

## Fragile Areas

**`MainWindow` remains a high-blast-radius integration point:**
- Files: `classic-gui/src/app/mainwindow.cpp`, `classic-gui/src/app/mainwindow.h`, `classic-gui/tests/test_scan_settings_wiring.cpp`, `classic-gui/tests/test_mainwindow_geometry.cpp`
- Why fragile: Startup migration, settings bootstrap, path detection, controller wiring, status updates, tab behavior, and file creation are all coordinated from the same class.
- Safe modification: Treat `MainWindow` as orchestration-only. Move path/bootstrap/report logic into dedicated controllers or helpers before adding more behavior.
- Test coverage: Coverage exists, but much of it is source-text inspection rather than compiled end-to-end behavior.

**Synchronous bridge wrappers sit on top of async Rust services:**
- Files: `cpp-bindings/classic-cpp-bridge/src/scanner.rs`, `cpp-bindings/classic-cpp-bridge/src/files.rs`, `cpp-bindings/classic-cpp-bridge/src/config.rs`, `cpp-bindings/classic-cpp-bridge/src/settings.rs`, `python-bindings/classic-config-py/src/lib.rs`
- Why fragile: Many public sync entry points call `classic_shared_core::get_runtime().block_on(...)`. That keeps interface layers simple, but it can stall caller threads and complicate nested async usage.
- Safe modification: Keep heavy calls off UI threads, prefer explicit worker boundaries, and introduce native async surfaces where the host language can use them directly.
- Test coverage: No dedicated stress coverage for nested-caller, re-entrancy, or UI-freeze scenarios was detected.

**Database APIs favor availability over correctness signaling:**
- Files: `business-logic/classic-database-core/src/pool_sqlx.rs`
- Why fragile: Query failures are logged and skipped during single and batch lookups, so callers receive partial success without structured degradation metadata.
- Safe modification: Preserve the current best-effort mode only behind an explicit policy flag; otherwise surface partial-failure state in return values.
- Test coverage: `business-logic/classic-database-core/tests/integration_tests.rs` covers integration behavior, but no dedicated fault-injection layer was detected for multi-database partial failure reporting.

## Scaling Limits

**Native surfaces are still strongly Windows-bound:**
- Current capacity: Windows desktop workflows are the first-class target across GUI, CLI, and Node packaging.
- Limit: Cross-platform native delivery is limited by Windows/MSVC assumptions in build and packaging surfaces.
- Scaling path: Expand targets and CI coverage only after build scripts, packaging, and path assumptions are separated from Windows-only flows.
- Files: `classic-cli/CMakeLists.txt`, `classic-gui/src/CMakeLists.txt`, `classic-gui/tests/CMakeLists.txt`, `node-bindings/classic-node/package.json`

## Dependencies at Risk

**`bun-types` is intentionally unpinned:**
- Risk: Development and CI behavior can change without a repository-controlled version bump because the package is declared as `latest`.
- Impact: Type or tooling regressions can appear unexpectedly in Node binding workflows.
- Migration plan: Pin `bun-types` in `node-bindings/classic-node/package.json` to a known-good version and upgrade deliberately.

## Missing Critical Features

**Structured partial-failure reporting for batch and multi-database operations is missing:**
- Problem: Several APIs keep processing after localized failures but do not return structured degraded-state metadata to the caller.
- Blocks: Reliable UX messaging, telemetry, and retry policy for `classic-database-core` and some binding-layer batch helpers.
- Files: `business-logic/classic-database-core/src/pool_sqlx.rs`, `node-bindings/classic-node/src/fileio.rs`

## Test Coverage Gaps

**Updater networking lacks integration-level verification:**
- What's not tested: Real HTTP behavior, timeout handling, API error mapping, and token-driven authenticated requests.
- Files: `business-logic/classic-update-core/src/github.rs`
- Risk: Regressions in live GitHub API handling can slip past serialization-heavy unit tests.
- Priority: Medium

**GUI scan wiring relies heavily on source-inspection tests instead of runtime flows:**
- What's not tested: Full compiled controller/worker/UI interactions for path resolution, settings propagation, and scan lifecycle behavior.
- Files: `classic-gui/tests/test_scan_settings_wiring.cpp`, `classic-gui/tests/test_mainwindow_geometry.cpp`, `classic-gui/src/app/mainwindow.cpp`
- Risk: Signal wiring and runtime object behavior can regress while regex/string-based tests remain green.
- Priority: High

**No dedicated fault-injection coverage for partial database outages was detected:**
- What's not tested: Observable caller behavior when one database in a multi-database pool errors while others succeed.
- Files: `business-logic/classic-database-core/src/pool_sqlx.rs`, `business-logic/classic-database-core/tests/integration_tests.rs`
- Risk: Silent data-quality degradation can remain unnoticed until users compare output against known-good scans.
- Priority: High

---

*Concerns audit: 2026-04-14*
