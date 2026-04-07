# Pitfalls Research

**Domain:** Multi-binding Rust workspace parity collapse (PyO3 / NAPI-RS / CXX), CI gate enforcement
**Researched:** 2026-04-06
**Confidence:** HIGH — all pitfalls grounded in actual source code, existing parity scripts, and current tier governance docs from this repo. No speculative claims.

---

## Critical Pitfalls

### Pitfall 1: Deferred Runtime Backlog Survives Tier Collapse

**What goes wrong:**
When Tier-2 governance files (`deferred_runtime_backlog.json`, `tier2_wave_manifest.json`) are deleted, the `check_parity_gate.py` script for Python reads `--deferred-registry` at runtime. If the path argument still points to the now-deleted file, the script crashes with a `FileNotFoundError` before it can report any parity drift. The gate goes from "green" to "erroring" rather than "failing with drift count." CI may treat a script error as a different kind of failure than a gate fail, and conditional logic (`if tier1_drift_count > 0`) is never reached.

**Why it happens:**
The Python gate script passes the deferred-registry path as a CLI argument with a hard default pointing to `docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json`. After file deletion, the default is wrong. The same pattern exists for the Node gate at `docs/implementation/node_api_parity/governance/deferred_runtime_backlog.json`. Both scripts call `load_json_file()` unconditionally before reporting drift.

**How to avoid:**
Before deleting governance files, update both gate scripts to make the deferred-registry path optional (fall back to an empty entry list when the file is absent) or remove the deferred-registry concept entirely from the single-tier post-collapse contract. Update CI invocation arguments at the same time as the file deletions — in the same commit. Add a smoke test that runs the gate script with a missing deferred-registry path and verifies it exits cleanly rather than crashing.

**Warning signs:**
Gate CI job exits with a non-zero code but the reported reason is a Python traceback, not a drift count. The `Tier-1 parity gate passed.` or `Tier-1 drift detected.` lines never appear in CI output.

**Phase to address:**
The phase that deletes Tier-2 governance files (Documentation Reset phase). Must be addressed before or concurrent with those deletions.

---

### Pitfall 2: Regex-Based Rust Surface Parser Misses Promoted Entries

**What goes wrong:**
The Python and Node baseline generators (`generate_baseline.py`) parse `lib.rs` files using regex patterns that match `pub mod`, `pub fn`, `pub struct/enum/type/trait/const/static`, and `pub use` re-exports. Many Tier-2 entries that existed only in sub-modules (not re-exported at `lib.rs`) were deferred precisely because the regex couldn't see them. When those entries are promoted to Tier-1, contributors add them to `parity_contract.json` but the Rust-surface parser still returns `missing_rust` because the symbol isn't in `lib.rs`. The gate fails with `missing_rust` even though the implementation exists.

**Why it happens:**
`parse_rust_surface()` is hardcoded to read only the three `lib.rs` files in `RUST_TARGET_CRATES`. It does not recurse into sub-modules. Tier-2 items like `FormIdAnalyzer`, `StreamingLogParser`, `ReportComposer`, `PatternMatcher`, `MatchConfidence`, `MatchResult`, and `UnknownVersionHandling` are already implemented in sub-modules — they just aren't re-exported from `lib.rs`. Promotion without a corresponding `pub use` addition to `lib.rs` leaves them invisible to the parser.

**How to avoid:**
For each Tier-2 entry being promoted: (1) confirm whether the Rust symbol is already re-exported at `lib.rs`; if not, add the `pub use` statement first; (2) then add the parity contract row. Add a CI check that validates every contract row's `rustSymbol` appears in the parsed Rust surface before accepting a PR that adds contract rows. The `parse_rust_surface()` function's `RUST_TARGET_CRATES` scope is documented; treat it as a constraint on what can be added to the contract, not a bug.

**Warning signs:**
Gate reports `missing_rust` for a symbol that clearly exists in the crate. Grep for the symbol in `lib.rs` — if absent but present in a sub-module file, this is the pattern.

**Phase to address:**
Python Tier Collapse phase and Node Tier Collapse phase — both, since both parsers have this constraint.

---

### Pitfall 3: NAPI Camel-Case vs Rust snake_case Contract Row Mismatch

**What goes wrong:**
NAPI-RS automatically converts Rust `snake_case` function names to `camelCase` for JS consumers. The Node parity contract rows use `nodeExport` which must match the JS-side name (camelCase). If a Tier-2 entry's contract row is copied from Python (which uses `pythonExport` in snake_case) and the `nodeExport` field is left in snake_case, the gate reports `missing_node` even though the NAPI export exists in `index.d.ts` in camelCase. The `parse_node_surface()` function parses `index.d.ts` and builds a lookup by the TypeScript identifier, which is camelCase.

**Why it happens:**
The 101 deferred Node Tier-2 entries span `scanlog` (64 items), `config` (18), `version_registry` (4), and `aux` (6). Many of these entries will be populated by referencing the Python governance files or the Rust symbol names. Contributors familiar with the Python parity format may use snake_case in the `nodeExport` field.

**How to avoid:**
Add a validation step in the Node parity contract JSON schema (or a linting script) that checks every `nodeExport` value: if the corresponding Rust symbol is a function or method, the `nodeExport` value must be camelCase. The Node gate's `parse_node_surface()` uses the `index.d.ts` TypeScript identifiers as the ground truth — check those first when writing contract rows. Name the Node contract file with a comment block at the top that makes the camelCase requirement explicit.

**Warning signs:**
Gate reports `missing_node` but `grep`-ing `index.d.ts` for the snake_case version finds the symbol in camelCase. The `nodeExport` value in the contract row contains an underscore that shouldn't be there.

**Phase to address:**
Node Tier Collapse phase — specifically when writing the 101 new parity contract rows.

---

### Pitfall 4: Python Test-Only Stub Hides Real Implementation Gap

**What goes wrong:**
Some Tier-2 Python entries exist in `.pyi` files but have no corresponding `#[pyclass]` / `#[pymethods]` implementation in the binding crate's `src/*.rs`. They were either stub-only entries added for documentation, or they refer to Rust types that PyO3 cannot expose directly (e.g., types that don't implement `Clone` or aren't `#[pyclass]`-annotated). The parity gate passes (the `.pyi` parser sees the stub), but at runtime `import classic_scanlog; classic_scanlog.FormIdAnalyzer()` raises `AttributeError`. The coverage registry check can catch this IF the entry has a runtime coverage row, but newly promoted entries without runtime coverage rows bypass that check.

**Why it happens:**
The `parse_python_surface()` function reads `.pyi` files, not compiled `.so` / `.pyd` modules. The Python gate has a `tier1_missing_runtime_total` check, but only for entries that appear in `runtime_coverage_registry.json`. Newly promoted entries that aren't in the registry yet — which is exactly what happens during mass Tier-2 promotion — don't trigger this check until the registry is updated.

**How to avoid:**
For every Tier-2 entry being promoted: (1) confirm the actual PyO3 binding implementation exists in `src/*.rs`, not just a `.pyi` entry; (2) add a runtime smoke test that imports the class/function and calls it with valid inputs; (3) add the runtime coverage row to `runtime_coverage_registry.json` before or concurrently with adding the parity contract row. Never add a contract row without an accompanying smoke test that calls the exported symbol at runtime.

**Warning signs:**
Gate passes all `tier1_*` checks but `pytest` failures appear on the new entries. The `.pyi` file contains the class but the `.so` module raises `AttributeError` or `ImportError` on the specific name.

**Phase to address:**
Python Tier Collapse phase — add a rule that every new contract row must have a corresponding pytest smoke test added in the same PR.

---

### Pitfall 5: CXX Header Generation Order Breaks Existing C++ Frontend Build

**What goes wrong:**
CXX generates C++ headers from `#[cxx::bridge]` blocks. When a new module is added to `classic-cpp-bridge/src/lib.rs` (e.g., `pub mod constants; pub mod web;`), CXX generates new headers in `include/classic_cxx_bridge/`. The CMakeLists.txt for `classic-cli` and `classic-gui` must reference the new headers or the `target_include_directories` for the new types. If the new module adds a new shared struct (e.g., `ConstantsDto`) that is used in an existing module's FFI block, CXX may reorder header includes internally, and MSVC can see an "incomplete type" error on the first use of the new struct in the existing module's generated header. This is because CXX header generation order follows `lib.rs` module declaration order, not include dependency order.

**Why it happens:**
CXX `#[cxx::bridge]` declarations in different modules can reference the same shared types only if those types are declared in a separate shared module that is included first. Adding a new module that introduces a new shared struct without coordinating include order in CMake causes MSVC to see a forward-declared but undefined type.

**How to avoid:**
When adding new CXX bridge modules, always declare shared DTOs in the module that is listed first in `lib.rs`. If a new module's struct needs to be used by an existing module, add it to the existing shared types module (`types.rs`) rather than the new module. After adding any new CXX module, run a clean CMake configure + build before committing — do not rely on incremental builds to validate header generation correctness. The `classic-cli/build_cli.ps1 -Clean -Test` and `classic-gui/build_gui.ps1 -Clean -Test` flags exist for this reason.

**Warning signs:**
MSVC error `C2027: use of undefined type` or `C2079: uses undefined struct` referencing a CXX-generated header. The error appears in a pre-existing `.cpp` file that was not modified, pointing to a generated include.

**Phase to address:**
CXX Bridge Expansion phase — every new `pub mod` addition to `lib.rs` must be followed by a clean build of both `classic-cli` and `classic-gui`.

---

### Pitfall 6: `rust::Vec<T>` ABI Type Restriction Breaks New Bridge DTOs

**What goes wrong:**
CXX has strict rules about which types can cross the FFI boundary in `Vec` form. `rust::Vec<T>` can only be used when `T` is a CXX-shareable type (a shared struct, a primitive, or `String`). If a new bridge module tries to return `Vec<NewComplexDto>` where `NewComplexDto` contains a nested `Vec<String>`, CXX will reject this at compile time with an opaque error about `T` not satisfying trait bounds. This shows up immediately at `cargo build` time, but the error message from CXX is not always clear about which type is non-shareable.

**Why it happens:**
New C++ bridge parity work (e.g., exposing `classic-scangame-core` fully, or `classic-constants-core` for the first time) requires new DTOs. Contributors familiar with NAPI-RS (where `Vec<ComplexObject>` works via `#[napi(object)]`) may assume CXX has similar flexibility.

**How to avoid:**
Before designing a new CXX bridge DTO, verify every field type against CXX's shared struct rules: only primitive types, `String`, and other shared structs are allowed. Nested collections (`Vec<Vec<String>>`, `Vec<StructWithVec>`) require flattening. Use the existing bridge patterns as templates: `TargetedResolutionDto` (parallel `Vec<String>` pairs instead of `Vec<RejectedInput>`), tab-delimited batch results, and `CacheStats` (five flat scalar fields). Document the flattening decision for each new DTO in the bridge source file.

**Warning signs:**
`cargo build` on the bridge crate produces an error referencing `cxx::private` or a missing `ExternType` impl. The CXX error points to a new shared struct, not to Rust business logic.

**Phase to address:**
CXX Bridge Expansion phase — design review of new DTOs before writing `#[cxx::bridge]` blocks.

---

### Pitfall 7: Cross-Binding Error-Contract Standardization Breaks FFI Ergonomics

**What goes wrong:**
The three bindings have intentionally different error shapes: C++ returns `""` or `false` (fail-soft primitives), Node returns `null` for optional helpers but throws `NapiError` with a `code` field for validation-heavy calls, and Python raises typed exception classes (`RustConfigParseError`, `RustConfigIOError`). When documenting the "per-binding error-contract conventions" (an Active requirement), a contributor who documents this as "inconsistency to fix" and then normalizes all three to one shape (e.g., always throw, never return null) breaks C++ callers that rely on `db_pool_get_entry()` returning `""` on miss — callers that cannot use C++ exceptions in their calling context (Qt signal handlers, for instance).

**Why it happens:**
The fail-soft primitives in C++ (empty string, false, 0) are intentional design choices for the Qt frontend, where exception propagation across thread boundaries is problematic. Node's mixed null/throw pattern is intentional for JS consumers who expect `null` for optional data but exceptions for programmer errors. The three shapes are not bugs — they reflect the ergonomic norms of each binding consumer.

**How to avoid:**
The Active requirement says "per-binding error-contract conventions documented" — the goal is documentation, not standardization. Write one doc page that names each binding's pattern, explains why that pattern fits its consumer (Qt/thread safety for C++, JS null-checking norms for Node, Python exception hierarchy for Python), and explicitly states that cross-binding normalization is out of scope. Add a note to the parity gate contract format that error shape is not a parity dimension — only symbol presence and call arity are checked.

**Warning signs:**
A PR description that says "standardize error handling across bindings" or "make C++ throw instead of returning empty string." Any change to `db_pool_get_entry()` that makes it return a `Result` instead of a plain `String` at the CXX boundary.

**Phase to address:**
Error Contract Documentation phase — write documentation that immunizes against future normalization attempts.

---

### Pitfall 8: CI Gate Cascade — Build Artifact Dependency Order

**What goes wrong:**
Three parity gates (Python, Node, C++) run in CI. The Node gate requires a built NAPI `.node` binary to run `bun run test:bun` and `bun run test:node`. The C++ gate requires a compiled `classic-cli` or `classic-gui` binary to verify that bridge headers are valid. If CI runs all three gates in parallel, and the Node build step fails, the Node parity gate job reports a build failure rather than a parity failure. The Python gate may still pass. Now the PR shows a mixed signal: Python green, Node red (build error, not parity), C++ red (MSVC link failure also unrelated to parity). A contributor focuses on the build errors and overlooks that Python parity is passing while Node and C++ parity are *untested* (not failing, untested).

**Why it happens:**
Gate-on-gate dependency in CI. The parity gate should logically run *after* the build succeeds, but if gates are set up as separate jobs with their own build steps, a build failure in one binding masquerades as a parity failure.

**How to avoid:**
Structure CI so that parity gate jobs depend on a successful build job, not an internal build step. Specifically: (1) Python gate can run independently (no binary needed — it reads `.pyi` files and Rust source); (2) Node gate must declare `needs: [node-build]`; (3) C++ gate must declare `needs: [cpp-build]`. The existing `ci-typescript.yml` already has NAPI-RS build + runtime tests separated from the parity check — preserve this separation and do not merge them. When adding the C++ gate, follow the same pattern.

**Warning signs:**
CI job log shows "build failed" inside a parity gate job. The parity gate script never produces its artifact files because the build step errored before the script ran.

**Phase to address:**
CI Enforcement phase — write CI job ordering as an explicit dependency graph, not a sequential script.

---

### Pitfall 9: Gate Disagreement When Binding Build Lags by Minutes

**What goes wrong:**
In a PR that touches both Rust core and all three binding surfaces, the Python gate (fast — no binary build) finishes and reports "passed" within 2 minutes. The Node gate takes 8 minutes to build the NAPI addon. The C++ gate takes 15 minutes to build `classic-cli` and `classic-gui` with MSVC. If the PR author sees the Python gate pass and merges (or re-queues), the slow gates are still running. If the C++ gate then fails, there is no merge protection because Python was already green. This is specifically a risk when the C++ gate is newly added and not yet in the branch protection required-check list.

**Why it happens:**
Adding a new required CI check (the C++ gate) to branch protection is a separate administrative step from writing the gate. Contributors often add the CI job first, verify it works, and forget to add it to required checks. During the window between "gate exists but not required" and "gate added to required checks," any merge that doesn't wait for the C++ gate can land a parity break.

**How to avoid:**
Add all three gates to the branch protection required-check list in the same PR that adds the C++ gate job. Do not merge the "add C++ gate" PR until the C++ gate has run successfully on that PR itself. Write the PR description for the CI Enforcement phase to include a checklist: "C++ gate added to required checks — verified green on this PR."

**Warning signs:**
Branch protection settings list Python and Node gates as required but not C++. A PR merges with only two green gates. The "required checks" list was not updated when the C++ gate job was added.

**Phase to address:**
CI Enforcement phase — the very first task is to define all three gates as required checks before any parity work starts.

---

### Pitfall 10: PE-Version Extraction Thread-Local Panic in NAPI Context

**What goes wrong:**
`classic-version-core`'s `extract_pe_version()` function uses `pelite` to memory-map and parse a Windows PE binary. When called from Node via NAPI-RS, it runs on a libuv thread pool thread. If `extract_pe_version()` internally panics (e.g., on a malformed PE header or an unexpected pelite error path), Rust panics are not caught by NAPI-RS's error handling machinery by default — they terminate the Node process. This is different from PyO3, where panics are caught by PyO3 and converted to Python `PanicException`.

**Why it happens:**
NAPI-RS `#[napi]` functions that call `unwrap()` or `expect()` on `pelite` parse results will terminate the Node process on any malformed binary. The C++ bridge wraps `extract_pe_version()` in a `Result`-returning function where CXX converts panics to exceptions. The Node binding, being new, may follow the same "just call the Rust function" pattern without wrapping in a `catch_unwind` or converting all error paths to `NapiError`.

**How to avoid:**
Wrap all `pelite` calls in the Node binding with `std::panic::catch_unwind` and convert panics to `NapiError`. Alternatively, ensure `extract_pe_version()` itself returns `Result<..., PeVersionError>` and never panics (use `?` instead of `unwrap()`). Add a Node test that passes a corrupted or zero-byte PE binary path and verifies that a `NapiError` is thrown rather than the process crashing. The `binding-parity-overview.md` notes that C++ has PE-version extraction but Node does not — this gap exists precisely because adding it safely requires this care.

**Warning signs:**
Node process exits with code 1 and no JavaScript error is thrown when calling the PE-version function on a bad path. `process.on('uncaughtException')` is not triggered — it's a hard Rust panic termination, not a JavaScript exception.

**Phase to address:**
Cross-Binding Harmonization phase (Node gains PE-version extraction).

---

### Pitfall 11: Python `classic_shared` GIL Deadlock on Tokio Runtime Access

**What goes wrong:**
Adding explicit `classic_shared` runtime helpers to Python (an Active requirement) means exposing functions that call `classic_shared_core::get_runtime()` from a PyO3 context. If a PyO3 function holds the GIL and then calls an async Rust function via `block_on()`, and that async Rust function internally spawns a task that tries to re-acquire the GIL (e.g., to call back into Python, or to log via a Python logger), the result is a deadlock: the GIL is held by the outer call, the spawned task is waiting for the GIL, and `block_on()` is waiting for the spawned task.

**Why it happens:**
The existing PyO3 bindings use `py.allow_threads(|| ...)` (GIL release) before any long-running Rust async calls. But `classic_shared` runtime helpers are described as "utility" functions and may seem safe to call without GIL release. The Tokio runtime is shared and the threadpool threads have no GIL — but if any spawned task uses a PyO3 callback, this deadlock pattern triggers.

**How to avoid:**
All PyO3 functions that call into the shared Tokio runtime must use `py.allow_threads(|| runtime.block_on(...))` to release the GIL before blocking. Write this as a rule in the `classic-shared-py` module documentation. Add a test that calls the runtime helpers from a Python thread while another Python thread holds the GIL and verify no deadlock occurs. The test can use `threading.Thread` with a timeout assertion. Never expose a PyO3 function that calls `get_runtime().block_on()` without a `py.allow_threads` wrapper.

**Warning signs:**
Python test hangs indefinitely with no output. `py-spy` shows all threads in "waiting for GIL" state. The hang occurs specifically when `classic_shared` helpers are called from Python while other threads are active.

**Phase to address:**
Cross-Binding Harmonization phase (Python gains `classic_shared` runtime helpers).

---

### Pitfall 12: Stale `docs/api/` Links After Tier-2 Governance File Deletion

**What goes wrong:**
`docs/api/binding-contract-refresh-note.md` contains explicit relative-path links to the governance files scheduled for deletion:
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md`
- `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md`
- `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md`

After these files are deleted, contributors who follow the links from `binding-contract-refresh-note.md` get 404s. The `binding-parity-overview.md` also references `docs/implementation/node_api_parity/` and `docs/implementation/python_api_parity/` as locations for parity gate artifacts. If the directory structure under `docs/implementation/` changes (e.g., the `governance/` subdirectory is removed entirely), these links break silently in local editors that don't check link validity.

**Why it happens:**
The documentation cross-reference network in this codebase is dense: `binding-contract-refresh-note.md` references governance files, `binding-parity-overview.md` references implementation directories, and `node-python-contract-map.md` references specific artifact files. Mass deletion of governance files without a link-sweep first creates a distributed documentation breakage that is hard to discover without following every link.

**How to avoid:**
Before deleting any file under `docs/implementation/*/governance/`, run a grep for its relative path across all Markdown files in `docs/`. Update or remove every link in the same commit as the deletion. Rewrite `binding-contract-refresh-note.md` entirely (not just update it) since the "when to refresh" guidance fundamentally changes after Tier-2 collapse — the concept of "Tier-2 deferral" no longer exists and the document will mislead if only partially updated. Add a CI step that checks for broken relative Markdown links (e.g., using `markdown-link-check` or a simple Python script) — this catches future drift too.

**Warning signs:**
A contributor opens `binding-contract-refresh-note.md` and clicks a governance link that returns 404. The `binding-parity-overview.md` "Practical Contributor Notes" section still references "Tier-2 backlog" rows.

**Phase to address:**
Documentation Reset phase — the link sweep must happen in the same commit as file deletions.

---

### Pitfall 13: Audit Trail Loss When Promoting Tier-2 Entries Without Rationale Capture

**What goes wrong:**
The Tier-2 backlog governance files (`deferred_runtime_backlog.json`, `tier2_wave_manifest.json`) contain per-entry `deferReason` fields and `wave` assignments that explain *why* each entry was deferred. When these files are deleted and all 285 Python + 101 Node entries are promoted to Tier-1, the historical rationale for each deferral is lost. Future contributors who ask "why was `StreamingLogParser` deferred before?" have no answer from the repo history unless the parity contract rows include a promotion rationale field.

**Why it happens:**
The deletion goal (Active requirement: "Delete governance files — single source of truth parity policy") treats the governance files as obstacles to clean policy. But the files also serve as audit artifacts. Their `deferReason` fields are the only place the rationale is recorded.

**How to avoid:**
Before deleting, extract the `deferReason` values from the deferred backlog JSONs and add a brief `"promotionNote"` field to each new Tier-1 contract row that was previously deferred. Alternatively, write a one-time migration summary doc (`docs/implementation/TIER2_PROMOTION_NOTES.md`) that records the promotion rationale in bulk ("all entries in wave2 were promoted because the milestone goal is one enforced tier — no entry-specific impediments remained"). This preserves the audit trail in `git log` without keeping the governance files themselves. The commit message for the promotion commit should include the entry count and migration summary.

**Warning signs:**
The new `parity_contract.json` has 385+ Tier-1 rows but no way to distinguish which rows were original Tier-1 entries versus promoted Tier-2 entries. A future contributor questions why a rarely-used API is in the enforced contract.

**Phase to address:**
Documentation Reset phase — capture rationale before deletion, not after.

---

### Pitfall 14: Phase Numbering Continuity — "Phase 8" Ambiguity in Docs

**What goes wrong:**
The PROJECT.md `Key Decisions` table confirms: "Continue phase numbering from v9.1.0-bugfixes (next phase = Phase 12)." However, several existing `docs/api/` pages were written during v9.1.0-bugfixes and contain inline references like "Phase 4 closes the cache stats gap," "Phase 3: FCX State Hardening," and "Phase 8 / Phase 11" (from `binding-parity-overview.md` lines 88-98). If the new milestone's phases are numbered 12+, these references remain unambiguous. But if a phase plan document is written that says "Phase 14: Documentation Reset" and then an `docs/api/` page says "Phase 8 FCX reset behavior" — a new contributor reading both sees two "Phase 8" references that refer to different milestones, with no milestone qualifier.

**Why it happens:**
Phase numbers in `docs/api/` files are milestone-relative references used to explain when a behavior was introduced. They are not absolute. But without a milestone qualifier, they look absolute. The confusion compounds when the new milestone's phase numbering continues sequentially from v9.1.0-bugfixes — so "Phase 12" in v9.1.0-bindings is adjacent to "Phase 11" from v9.1.0-bugfixes in git history.

**How to avoid:**
In any new `docs/api/` page or update written during v9.1.0-bindings, qualify phase references with the milestone: "v9.1.0-bugfixes Phase 4" or "v9.1.0-bindings Phase 12." Apply this rule retroactively when updating existing docs pages in the Documentation Reset phase. Add a contributor convention note to `docs/api/README.md` that says: "When referencing a phase in a doc page, always include the milestone label."

**Warning signs:**
A `docs/api/` page says "Phase X introduced ..." without naming the milestone. The number falls in the range 8-11 (v9.1.0-bugfixes range) but could be confused with new work in phases 12+.

**Phase to address:**
Documentation Reset phase — update the `docs/api/README.md` contributor convention and apply qualified labels when editing existing pages.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Add a parity contract row without an accompanying smoke test | Faster Tier-2 promotion — gate passes sooner | Test-only stub pattern emerges; runtime gaps invisible to the gate | Never for Tier-1 rows |
| Promote all 285 Python entries in one batch commit | One PR closes the milestone requirement | Reviewer cannot validate each entry; stub-only entries slip through | Only if each entry has a pre-verified runtime test |
| Copy Python contract row format for Node rows without case conversion | Saves typing | Gate reports `missing_node` for every copied row (snake_case vs camelCase) | Never |
| Use `unwrap()` in NAPI PE-version binding during initial implementation | Faster to write | Node process crashes on malformed input | Never in production NAPI code |
| Keep deferred-registry path hardcoded in gate scripts during transition | No script changes needed | Gate crashes with `FileNotFoundError` after governance file deletion | Never — update scripts before deleting files |
| Write C++ gate as a shell script that calls `ctest` directly | Simpler to implement | Violates AGENTS.md "never raw ctest" rule, breaks in CI Windows runner | Never — use PowerShell wrappers |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| CXX new module + MSVC | Add `pub mod constants;` to `lib.rs` but forget `#[cxx::bridge]` in the new file | Every module listed in `lib.rs` that exposes C++ types must have a `#[cxx::bridge]` block; otherwise MSVC sees an undefined namespace |
| Node `index.d.ts` freshness gate | Regenerate `index.d.ts` locally but forget to commit it before pushing | `bun run dts:freshness:check` compares the committed file against a fresh build; a stale committed file fails the gate even if local build was fresh |
| Python `.pyi` stub validation | Update the `.pyi` but not the PyO3 `src/*.rs` binding | `validate_stubs.py` checks stub consistency against the parity contract, not the compiled module; smoke tests catch the runtime gap |
| VCPKG + new CXX bridge types | New bridge DTO uses a type from a vcpkg dependency not yet in `vcpkg.json` | Run `vcpkg install` after adding dependencies; the build_cli.ps1 wrapper handles vcpkg integration but requires the manifest to be correct first |
| Three-gate CI + single PR | Touching Rust core in a way that breaks C++ ABI but not Python or Node parity | C++ gate must declare `cargo build --workspace` as a prerequisite, not just the parity script |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Running all three parity gates sequentially in CI on every PR | PRs take 30+ minutes to get a green signal; contributors bypass or ignore slow gates | Run Python gate in parallel with Node build; run C++ gate in parallel with Node gate; only final status aggregation is sequential | Immediately for a busy PR queue |
| Rebuilding NAPI addon from scratch on every gate run | Node gate CI job takes 10+ minutes even for doc-only PRs | Cache the NAPI build artifacts using `actions/cache` keyed on `Cargo.lock` + `bun.lockb` hash | Every PR |
| Regenerating all Python parity baseline artifacts on every gate run | Gate script rewrites unchanged JSON files, triggering stale-artifact check failures | The `artifacts_match()` function strips `generated_at_utc` before comparison — use `--update-baseline` only when content genuinely changed | During mass promotion — 285 entries changes mean real diffs, so the first run after promotion will always need `--update-baseline` |

---

## "Looks Done But Isn't" Checklist

- [ ] **Tier-2 governance files deleted:** Verify `deferred_runtime_backlog.json` and `tier2_wave_manifest.json` are gone from both `docs/implementation/node_api_parity/governance/` and `docs/implementation/python_api_parity/governance/`, AND that gate scripts no longer reference them at their old paths.
- [ ] **C++ gate running in CI:** Verify the gate job appears in GitHub Actions run output, not just that the YAML file exists. A CI YAML file that has a syntax error or wrong trigger will not appear in PR checks.
- [ ] **C++ gate in branch protection required checks:** Verify in repository Settings → Branches → main → Required status checks. The gate job name must exactly match the CI job name — a mismatch means the gate runs but does not block merges.
- [ ] **Node PE-version extraction smoke test:** Verify the test passes with both a valid PE binary and a deliberately corrupted one. Passing only with valid input does not catch the panic-on-bad-input failure mode.
- [ ] **Python `classic_shared` GIL test:** Verify there is a pytest test that calls runtime helpers from multiple threads and asserts no deadlock within a 5-second timeout.
- [ ] **`binding-parity-overview.md` rewritten:** Verify the page no longer contains "Tier-2" in any heading, sentence, or table. Search for "tier2" and "Tier-2" in the file.
- [ ] **All `docs/api/` links resolve:** Run a link checker across `docs/api/*.md` after the documentation reset — do not rely on manual review of 33 files.
- [ ] **`parity_contract.json` row count:** Python contract should have 285+ new rows; Node contract should have 101+ new rows. Verify by diffing the contract JSON against its pre-milestone state.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Deferred registry deleted, gate crashes | LOW | Restore the deleted file from git history (`git show HEAD~1:path/to/file > restored.json`) or update gate script to handle missing file; re-run gate |
| NAPI PE-version extraction panics in production | MEDIUM | Hotfix: wrap call in `catch_unwind` and return `NapiError`; release patch; the crash only affects Node consumers passing bad PE paths |
| CXX header generation breaks C++ build | MEDIUM | Revert the new `lib.rs` module declaration; design the new DTO layout with flattened types; re-add the module |
| C++ gate not in required checks, parity break lands | HIGH | Run C++ gate retroactively on the offending commit; if gate fails, file an issue and fix in a hotfix PR; add gate to required checks immediately |
| Governance files deleted, audit trail lost | LOW | Audit trail exists in `git log`; write a retroactive `docs/implementation/TIER2_PROMOTION_NOTES.md` summarizing the promotion; recovery is documentation work only |
| Python GIL deadlock in runtime helpers | MEDIUM | Add `py.allow_threads` wrapper to the specific binding function that deadlocks; the fix is surgical and does not require API changes |
| Phase number ambiguity in docs | LOW | Add milestone qualifiers to ambiguous doc references; documentation-only fix |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Deferred registry crash after file deletion | Documentation Reset phase | Gate scripts run successfully with governance files absent |
| Rust surface parser misses promoted entries | Python Tier Collapse + Node Tier Collapse | Every new contract row has `rustSymbol` visible in parsed `lib.rs` output |
| NAPI camelCase contract row mismatch | Node Tier Collapse | Zero `missing_node` gate failures caused by case errors; `nodeExport` values match `index.d.ts` identifiers |
| Test-only Python stub hides gap | Python Tier Collapse | Every new Tier-1 row has a pytest smoke test that runs the export at runtime |
| CXX header generation order break | CXX Bridge Expansion | Clean `-Clean -Test` build of both `classic-cli` and `classic-gui` passes after each new module addition |
| `rust::Vec<T>` ABI restriction | CXX Bridge Expansion | `cargo build` on `classic-cpp-bridge` succeeds with no CXX type errors; all new DTOs use flat types |
| Error contract normalization | Error Contract Documentation | Doc page explicitly states normalization is out of scope; no PR changes fail-soft C++ return conventions |
| CI gate cascade (build artifact dependency) | CI Enforcement phase | CI job graph shows explicit `needs:` declarations; parity gate jobs never run their own build step |
| Gate disagreement (slow C++ gate) | CI Enforcement phase | C++ gate is in branch protection required checks before any parity work merges |
| PE-version Node panic | Cross-Binding Harmonization (Node) | Node test passes with corrupted PE binary without process crash |
| Python `classic_shared` GIL deadlock | Cross-Binding Harmonization (Python) | Multi-threaded pytest passes within timeout; no hang on runtime helper calls |
| Stale `docs/api/` links after deletion | Documentation Reset phase | Link checker runs clean across all `docs/api/` files after governance file deletion |
| Audit trail loss on promotion | Documentation Reset phase | Promotion notes captured before deletion commit lands |
| Phase numbering ambiguity | Documentation Reset phase | All new `docs/api/` content qualifies phase references with milestone label |

---

## Sources

- Source-backed: `tools/python_api_parity/generate_baseline.py` — `parse_rust_surface()` scope constraint (reads only `lib.rs` files), `RUST_TARGET_CRATES` hardcoding, regex patterns for Rust symbol extraction
- Source-backed: `tools/python_api_parity/check_parity_gate.py` — `--deferred-registry` argument default path, `load_json_file()` unconditional call, `tier1_missing_runtime_total` check ordering
- Source-backed: `tools/node_api_parity/check_parity_gate.py` — identical deferred-registry path dependency, `parse_node_surface()` uses `index.d.ts` TypeScript identifiers as ground truth
- Source-backed: `docs/implementation/python_api_parity/governance/tier2_backlog_and_governance.md` — 282 deferred entries, `deferred_runtime_backlog.json` path, wave manifest
- Source-backed: `docs/implementation/node_api_parity/governance/tier2_backlog_and_governance.md` — 92 deferred entries, `gate_contract_baseline.md` reference, `tier2_wave_manifest.json`
- Source-backed: `docs/api/binding-contract-refresh-note.md` — explicit links to governance files at lines 28-29 that will break after deletion
- Source-backed: `docs/api/binding-parity-overview.md` — C++/Node/Python error shape differences (lines 163-170), PE-version gap (line 95), `classic-constants-core`/`classic-web-core` C++ absence (line 100)
- Source-backed: `docs/api/classic-cpp-bridge-data-entrypoints.md` — fail-soft primitive patterns (`db_pool_get_entry` returns `""` on miss/error), CXX DTO flattening patterns (`TargetedResolutionDto` parallel vectors, tab-delimited batch results)
- Source-backed: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/lib.rs` — `#[cfg(windows)]` module declarations, wave groupings, current 14-module structure
- Source-backed: `ClassicLib-rs/cpp-bindings/classic-cpp-bridge/src/game.rs` — `extract_pe_version()` usage, `VersionInfoDto` sentinel `found: false` pattern, CXX shared struct field types
- Source-backed: `.planning/PROJECT.md` Key Decisions table — "Continue phase numbering from v9.1.0-bugfixes (next phase = Phase 12)" decision, phase qualification rationale

---

*Pitfalls research for: v9.1.0-bindings Full Bindings Parity — multi-binding Rust workspace parity collapse*
*Researched: 2026-04-06*
