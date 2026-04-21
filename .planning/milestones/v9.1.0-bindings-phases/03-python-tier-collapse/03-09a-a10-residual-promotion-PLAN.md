---
phase: 03-python-tier-collapse
plan: 09a
type: execute
wave: 9
depends_on: [03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08]
files_modified:
  - .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
  - .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
  - .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md
  - .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md
  - .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py
  - .planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py
  - docs/implementation/python_api_parity/baseline/parity_contract.json
  - docs/implementation/python_api_parity/baseline/parity_contract.md
  - docs/implementation/python_api_parity/baseline/parity_diff_report.json
  - docs/implementation/python_api_parity/baseline/parity_diff_report.md
  - docs/implementation/python_api_parity/baseline/rust_api_surface.json
  - docs/implementation/python_api_parity/baseline/python_api_surface.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
  - docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
  - docs/implementation/python_api_parity/baseline/tier1_gate_report.md
  - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json
  - ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md
  - ClassicLib-rs/python-bindings/parity-artifacts/python_api_surface.json
  - ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
  - ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
  - ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md
  - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  - ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
  - ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi
  - ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
  - ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi
  - ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi
  - ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi
  - ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi
  - ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi
  - ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
  - ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi
  - ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
  - ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi
  - ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi
  - ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi
  - ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi
  - ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
autonomous: true
requirements: [PYT-02, PYT-04, PYT-05, PYT-06]
must_haves:
  truths:
    - "Residual inventory is sourced FRESH from docs/implementation/python_api_parity/baseline/parity_diff_report.json::gaps AFTER an in-task baseline regeneration via generate_baseline.py --write-baseline. No hardcoded counts: every residual count referenced by downstream tasks is read from the regenerated artifact, not from the frontmatter or STATE.md."
    - "Residual inventory filters gaps where tier == 'tier2' AND owner_module NOT IN {'file_io', 'shared'} (R3; Plan 08 owns those) AND NOT (gap_type == 'rust_unmapped' AND rust_symbol == 'GLOBAL_FCX_HANDLER') (R9; LazyLock static not tier1-promotable). Live verification 2026-04-08: 735 residuals across 15 owners (scangame 213, path 83, constants 58, message 53, database 46, resource 40, xse 40, settings 38, yaml 37, registry 37, web 29, version 27, perf 16, update 14, scanlog 4). This count is EMPIRICAL not hardcoded; Task 0 re-verifies after baseline refresh."
    - "03-09a-CONSTRUCTOR-INVENTORY.md is produced as a dedicated Task 0 artifact (not inline in Task 1) before any row authoring begins — this matches the Plans 02-08 precedent and prevents the constructor-guessing failure mode at the 80-120-class scale of Plan 09a."
    - "FAIL-CLOSED wrapper-existence helper uses THREE BRANCHES keyed on gap shape: (1) gap_type == 'rust_unmapped' -> skip wrapper check entirely and emit @rust proxy row paired with nearest Python anchor class (Plan 08 precedent _build_plan08_rows.py:261-283); (2) python_export_path contains '.' (method residual) -> verify the OUTER class wrapper exists via #[pyclass] search, NOT the bare method name; (3) top-level python_unmapped -> verify the #[pyclass]/#[pyfunction] wrapper exists. Empirical test on live diff_report: at least one rust_unmapped residual AND at least one method residual AND at least one top-level residual must each be CLASSIFIED CORRECTLY without landing in 03-09a-BLOCKERS.md."
    - "Dry-run projection helper (Task 0 Step 6) empirically validates the post-09a endgame BEFORE any row authoring: reads deferred_runtime_backlog.json::entries, tier1_rust_symbols pre-Plan-09a, and the residual inventory. Projects post-09a deferred_total using the build_coverage_summary semantics empirically verified in the revision write-up: after 09a, parity_diff_report.json::gaps drops to 1 (GLOBAL_FCX_HANDLER) BUT deferred_total stays high (~1008) because registry_only fallback in build_coverage_summary (L264-292) picks up deferred backlog entries even after their gap rows disappear. The projection MUST document this: Plan 09b explicitly empties the deferred backlog to drive deferred_total to 0. If the projection differs from expectations (e.g., fewer residuals than projected) the helper prints a warning but does NOT fail closed — the projection is diagnostic, not a gate."
    - "The 14 new runtime_coverage_registry.json selectors compute contractIdsHash by IMPORTING tools.binding_parity_runtime_coverage._stable_id_hash directly, NOT by reimplementing. _stable_id_hash is a full 64-character lowercase hex SHA-256 over newline-joined sorted IDs (verified via live read of tools/binding_parity_runtime_coverage.py L57-59: 'joined = \"\\n\".join(sorted(values)); return hashlib.sha256(joined.encode(\"utf-8\")).hexdigest()'). Any 16-character hash or comma-joined hash input is WRONG and will produce registry_mismatch_total > 0 at gate time."
    - "Pre-task Rule 2 stub audit runs validate_stubs.py --fail-on-warnings BEFORE row authoring (Plan 08 Rule 2 precedent) and writes 03-09a-STUB-AUDIT.md with pre-existing stub holes for currently-enrolled owners (config/scanlog/version_registry/file_io/shared). Note: validate_stubs.py only walks ClassicLib-rs/python-bindings/ crates ending in '-py'; it does NOT discover ClassicLib-rs/foundation/classic-shared-py/ (validator source: validate_stubs.py L318, L333-352). classic_shared coverage is provided by the explicit mypy --strict step in Plan 09b Task 4 Step 1, not by validate_stubs."
    - "Per-class smoke tests in test_promoted_residuals_smoke.py are SCAFFOLDED by _scaffold_plan09a_tests.py which reads the routing maps from _build_plan09a_rows.py and the constructor inventory from 03-09a-CONSTRUCTOR-INVENTORY.md. Each test constructs an instance using verified argument signatures and calls at least one real method (D-07: construct + call one real method, NEVER hasattr-only). The scaffold helper enumerates expected tests (projected 80-130 tests at 6-10 tests per class across 14 classes + 4 scanlog method residuals + rust-only proxy guards) and writes hand-verifiable skeletons; the author fills in expected return-value assertions per-test."
    - "Two-owner-in-one-plan template from Plan 08 generalizes to N owners: a single _build_plan09a_rows.py helper authors all 14 owner row sets in one atomic Task 1 commit using the same same-row-dedup rule (already_covered_rust_symbols tracked across ALL owners) that saved 14 duplicates in Plan 08."
    - "5-step verification chain at plan close (parity gate + validate_stubs + rebuild_rust + pytest + mypy --strict on touched stubs) exits 0; the full 19-stub mypy --strict sweep is deferred to Plan 09b Task 4 Step 1."
  artifacts:
    - path: "docs/implementation/python_api_parity/baseline/parity_contract.json"
      provides: "tier1Mappings grown from 505 (Plan 08 close) to 505 + (post-dedup residual count from Task 1 commit log)."
    - path: "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py"
      provides: "Per-class smoke tests for every promoted residual #[pyclass] across 14 owner modules, plus 4 scanlog method tests, plus rust-only proxy guards per owner."
      min_lines: 400
    - path: ".planning/phases/03-python-tier-collapse/_build_plan09a_rows.py"
      provides: "Reproducible multi-owner row-builder generalizing _build_plan08_rows.py with three-branch fail-closed wrapper check, EXCLUDED_RUST_SYMBOLS for R9, EXCLUDED_OWNERS for R3, and _stable_id_hash import from the live tooling module."
    - path: ".planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py"
      provides: "Test scaffolding helper that reads routing maps and constructor inventory to emit hand-verifiable test skeletons; prevents the Rule-1 test-assumption bug class that Plan 08 hit 6 times at 49-test scale."
    - path: ".planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md"
      provides: "Per-owner #[pymethods] impl Py<Class> { #[new] fn new } signature catalog; the source of truth for smoke test constructor arguments."
    - path: ".planning/phases/03-09a-RESIDUAL-INVENTORY.md"
      provides: "Per-owner residual catalog with (rust_symbol, python_export, kind, wrapper_path, gap_type) for every promoted row; the input contract for _build_plan09a_rows.py."
    - path: ".planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md"
      provides: "Empirical projection of post-09a deferred_total, per-owner row counts, and expected gate state; documents that 09b owns the final backlog emptying step per C3 investigation."
  key_links:
    - from: "_build_plan09a_rows.py"
      to: "docs/implementation/python_api_parity/baseline/parity_diff_report.json::gaps"
      via: "filter tier=='tier2' AND owner_module NOT IN {'file_io','shared'} AND NOT (gap_type=='rust_unmapped' AND rust_symbol=='GLOBAL_FCX_HANDLER')"
      pattern: "gaps.*tier.*tier2"
    - from: "_build_plan09a_rows.py"
      to: "tools.binding_parity_runtime_coverage._stable_id_hash"
      via: "import and call (NOT reimplement) — hashes must be 64-char full SHA-256"
      pattern: "from binding_parity_runtime_coverage import _stable_id_hash"
    - from: "test_promoted_residuals_smoke.py"
      to: "newly-promoted residual #[pyclass] wrappers"
      via: "import classic_<owner>; obj = ClassName(verified_args); obj.method() per D-07"
      pattern: "import classic_(scangame|path|constants|message|database|resource|xse|settings|registry|yaml|web|version|perf|update|scanlog)"
    - from: "runtime_coverage_registry.json"
      to: "parity_contract.json::tier1Mappings"
      via: "contractSelector { ownerModule, tier: tier1 } with full-length contractIdsHash from _stable_id_hash"
      pattern: "python-tier1-(scangame|path|constants|message|database|resource|xse|settings|registry|yaml|web|version|perf|update)"
---

<objective>
Promote every live tier-2 residual gap surfaced by the Plan 01 `RUST_TARGET_CRATES` expansion (15 owners, post-Plan-08 ground truth from regenerated baseline) to enforced tier-1 contract rows in a single atomic plan. Plan 09a is the final binding-enrollment plan in Phase 3 — after it commits, every public Python binding symbol has a tier-1 contract row, a stub entry, and a runtime smoke test.

**This is the second revision** of Plan 09a. The first revision (committed earlier today in this session) was critiqued by cross-AI peer review (`03-REVIEWS.md` Round 2) which surfaced four HARD-BLOCKING CRITICAL findings and several HIGH/MEDIUM findings that the original plan-checker missed. This revision addresses each finding structurally:

- **C1 (wrapper check broken)**: The `find_wrapper` helper now uses three branches keyed on gap shape (`rust_unmapped` skip, method residual class-wrapper check, top-level bare-name check) instead of the old single-branch logic that false-closed on method residuals and rust-only residuals. Empirical verification: at least one residual from each branch type passes without landing in BLOCKERS.
- **C2 (hash algorithm mismatch)**: Plan 09a Task 3 now imports `_stable_id_hash` directly from the live `tools.binding_parity_runtime_coverage` module (L57-59, verified via live read) instead of reimplementing. Hash length = 64 chars (full SHA-256), not 16. Verified against Plan 08's committed hashes in `runtime_coverage_registry.json` which are both 64 chars.
- **C3 (deferred_total path)**: Investigated empirically on live code via Python REPL (see deep_work_rules and revision summary). Outcome A: fixable in Phase 3. Plan 09a promotes residuals and reduces the gap-row count to 1 (GLOBAL_FCX_HANDLER), but `deferred_total` stays at ~1008 after 09a because `build_coverage_summary` (L264-292) uses a `registry_only` fallback that picks up deferred backlog entries even when their gap rows disappear. Plan 09b explicitly empties `deferred_runtime_backlog.json::entries` to drive `deferred_total` to 0. Both reviewer traces are captured in the dry-run projection artifact so Plan 09b can cross-check.
- **H5 (constructor inventory)**: Dedicated Task 0 step emits `03-09a-CONSTRUCTOR-INVENTORY.md` as a standalone artifact matching Plans 02-08 precedent.
- **H6 (dry-run projection)**: Dedicated Task 0 Step 6 emits `03-09a-DRY-RUN-PROJECTION.md` before any row authoring.
- **M9 (count discrepancy)**: Task 0 Step 1 regenerates the baseline in-task; all downstream counts are read from the regenerated artifact.
- **M10 (test scaffolding)**: New `_scaffold_plan09a_tests.py` helper enumerates expected tests before hand authoring.
- **M11 (validate_stubs scope)**: Documented explicitly that classic_shared is not covered by validate_stubs (only by explicit mypy in 09b).
- **M12 (python-tier2-scanlog-runtime retirement)**: Task 3 Step 4 retires this entry by deleting it outright (all 4 methods are now covered by the bumped python-tier1-scanlog selector; same-owner tier-2 entry is stale).
- **L14 (exact tier1Mappings count in SUMMARY)**: Task 4 SUMMARY explicitly records the post-09a count.
- **L15 (testSuite R8 precedent)**: A separate `python-tier1-scanlog-wave10-residuals` selector is created for the 4 scanlog method residuals instead of mutating the existing `python-tier1-scanlog` testSuite pointer.

Output:
- Regenerated baseline (Task 0 Step 1)
- `03-09a-CONSTRUCTOR-INVENTORY.md` (Task 0 Step 2)
- `03-09a-STUB-AUDIT.md` (Task 0 Step 3)
- `03-09a-RESIDUAL-INVENTORY.md` OR `03-09a-BLOCKERS.md` from the three-branch wrapper check (Task 0 Step 4)
- `03-09a-DRY-RUN-PROJECTION.md` (Task 0 Step 5)
- `_build_plan09a_rows.py` reproducible helper (Task 0 Step 4 + Task 1)
- `_scaffold_plan09a_tests.py` scaffolding helper (Task 2 Step 1)
- Atomic commits per task; contract rows + 14 stub updates + smoke test file + registry selectors
- 5-step verification chain green at plan close; SUMMARY records post-09a `tier1Mappings.length` and `deferred_total` for 09b cross-check
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-python-tier-collapse/03-CONTEXT.md
@.planning/phases/03-python-tier-collapse/03-RESEARCH.md
@.planning/phases/03-python-tier-collapse/03-VALIDATION.md
@.planning/phases/03-python-tier-collapse/03-REVIEWS.md
@.planning/phases/03-python-tier-collapse/03-08-classic-shared-and-file-io-aux-SUMMARY.md
@.planning/phases/03-python-tier-collapse/_build_plan08_rows.py
@./CLAUDE.md
@./AGENTS.md

<interfaces>
<!-- ============================================================================ -->
<!-- LIVE CODE CITATIONS — re-verified 2026-04-08 via Python REPL and source read -->
<!-- ============================================================================ -->

<!-- C2 FIX: hash algorithm contract from tools/binding_parity_runtime_coverage.py -->
<!-- File: tools/binding_parity_runtime_coverage.py lines 57-59 (full function body) -->
```python
def _stable_id_hash(values: list[str]) -> str:
    joined = "\n".join(sorted(values))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
```
The hexdigest() call with NO slice returns the FULL 64-character lowercase hex SHA-256.
Sort is on the full list before join. Separator is newline ("\n").
Encoding is UTF-8.

Verification against live Plan 08 selectors:
- python-tier1-shared: contractIdsHash = "c535a162a400bd935c8255425cb44dae07b738cf781fccddac414123a041b24f" (64 chars)
- python-tier1-file_io: contractIdsHash = "4bb08d07639ba26f99842fe935cbf20088bb72ad05ba2c954b6dc1296ead465d" (64 chars)

Any Plan 09a hash shorter than 64 characters will produce registry_mismatch_total > 0 at check_parity_gate.py time and fail the gate.

<!-- C3 FIX: deferred_total computation path from tools/binding_parity_runtime_coverage.py -->
<!-- File: tools/binding_parity_runtime_coverage.py L221-330 (build_coverage_summary) -->

The `deferred_total` metric is computed as:
```python
deferred_total = classification_counts.get("deferred", 0)
```
where classification_counts counts the `classification` field of every item in `tracked_surface`.

An item gets `classification = "deferred"` ONLY if it comes from one of these three paths:
1. A `contract_row` whose contract_id is in a runtime_registry entry with `classification: "deferred"` (rare in practice — runtime registry entries are mostly `runtime_verified`)
2. A `gap` whose binding_identifier or rust_symbol matches a `deferred_registry` entry (L147-163, L256-261)
3. A `registry_only` fallback from `deferred_registry.entries` whose bindingIdentifiers or rustSymbols are NOT already tracked (L264-292)

Path (3) is the critical one for Plan 09b's endgame. Empirically verified against the current live tree (2026-04-08):
- Current state: 1040 deferred items (732 gap + 308 registry_only)
- Scenario A (Plan 09b tier2 deletion only, baseline refreshed): deferred_total = 1008 (the 732 gap items drop to 0, but registry_only stays at 1008)
- Scenario B (09b tier2 deletion + emptied deferred registry): deferred_total = 0

Therefore Plan 09a alone (row promotion + baseline refresh) CANNOT drive deferred_total to 0. Plan 09b MUST empty `deferred_runtime_backlog.json::entries` as an explicit task step. This is legitimate Phase 3 scope because the Phase 6 boundary (DOC-02/DOC-04) is about DELETING the governance directory entirely, not about editing its contents — editing the backlog to reflect the promoted state is Phase 3 hygiene, not a cross-phase writethrough.

Plan 09a's Task 4 post-condition records the post-09a deferred_total so Plan 09b knows what number it must drive to 0.

<!-- C1 FIX: three-branch wrapper check driven by gap shape -->

The find_wrapper helper MUST have exactly three branches:

```python
def find_wrapper(owner: str, residual: dict) -> tuple[bool, str]:
    """
    Returns (found, reason).

    BRANCH 1: rust_unmapped -> skip wrapper check entirely.
      Rust-only residuals use @rust proxy rows paired with a Python anchor class.
      Precedent: Plan 08 _build_plan08_rows.py L261-283. No -py wrapper is expected.

    BRANCH 2: python_unmapped with '.' in python_export_path -> verify CLASS wrapper.
      For PatternMatcher.has_match, the wrapper to check is PatternMatcher, not has_match.
      Search for #[pyclass(... name = "PatternMatcher")] or struct PyPatternMatcher.
      PyO3 #[pymethods] bodies use bare 'fn method()' not 'pub fn method()', so searching
      for 'pub fn has_match' would always miss. The class wrapper existence is sufficient
      to prove the method can be exposed.

    BRANCH 3: python_unmapped with no dot in python_export_path -> verify top-level wrapper.
      For a top-level class/function residual like Fallout4Version, search for
      #[pyclass(... name = "Fallout4Version")] or #[pyfunction] that produces this name.
    """
    gap_type = residual.get("gap_type")
    owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
    if not owner_dir.exists():
        return (False, "no_py_crate_dir")

    # BRANCH 1: rust_unmapped
    if gap_type == "rust_unmapped":
        # Rust-only residuals don't need a -py wrapper; they use @rust proxy rows.
        # Precedent: _build_plan08_rows.py L261-283 (SHARED_RUST_ONLY dict).
        return (True, "rust_unmapped_uses_rust_proxy")

    py_export_path = residual.get("python_export_path") or ""
    # BRANCH 2: method residual
    if "." in py_export_path:
        class_name = py_export_path.split(".")[0]
        # Search for the class wrapper (may be PyClassName or ClassName with name=)
        candidates = [
            f'name = "{class_name}"',
            f"pub struct Py{class_name}",
            f"pub struct {class_name}",
            f"pub enum Py{class_name}",
            f"pub enum {class_name}",
        ]
        for rs in owner_dir.rglob("*.rs"):
            text = rs.read_text(encoding="utf-8", errors="ignore")
            if any(c in text for c in candidates):
                return (True, f"class_wrapper_found:{rs.name}")
        return (False, f"class_wrapper_not_found:{class_name}")

    # BRANCH 3: top-level residual (class or function)
    top_level = py_export_path or residual.get("python_export") or residual.get("rust_symbol") or ""
    top_level_bare = top_level.split(".")[-1]
    candidates = [
        f'name = "{top_level_bare}"',
        f"pub struct Py{top_level_bare}",
        f"pub struct {top_level_bare}",
        f"pub enum Py{top_level_bare}",
        f"pub enum {top_level_bare}",
        f"#[pyfunction]",  # must be followed by fn <top_level_bare> — checked separately
    ]
    for rs in owner_dir.rglob("*.rs"):
        text = rs.read_text(encoding="utf-8", errors="ignore")
        if any(c in text for c in candidates[:5]):
            return (True, f"top_level_wrapper_found:{rs.name}")
        # Function fallback: find "fn <name>" after a #[pyfunction] attribute
        if "#[pyfunction]" in text and f"fn {top_level_bare}" in text:
            return (True, f"top_level_fn_found:{rs.name}")
    return (False, f"top_level_wrapper_not_found:{top_level_bare}")
```

Empirical test (MUST be part of acceptance criteria): load the live parity_diff_report.json, pick the first rust_unmapped residual (owner=constants, rust_symbol=Fallout4Version), the first method residual (owner=constants, python_export_path=Fallout4Version.__eq__), and the first top-level residual (owner=constants, python_export_path=Fallout4Version class). All three MUST return (True, reason) without landing in 03-09a-BLOCKERS.md.

<!-- Residual source filter expression (same as first revision) -->
```python
residuals = [
    g for g in diff["gaps"]
    if g["tier"] == "tier2"
    and g["owner_module"] not in EXCLUDED_OWNERS  # R3
    and not (g["gap_type"] == "rust_unmapped" and g.get("rust_symbol") in EXCLUDED_RUST_SYMBOLS)  # R9
]
EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}  # Phase 3 R9
EXCLUDED_OWNERS = {"file_io", "shared"}  # Phase 3 R3 — Plan 08 owns these
```
Live 2026-04-08 count = 735 residuals across 15 owners (scangame 213, path 83, constants 58, message 53, database 46, resource 40, xse 40, settings 38, yaml 37, registry 37, web 29, version 27, perf 16, update 14, scanlog 4). This count is verified fresh by Task 0 after baseline regeneration; the frontmatter does NOT hardcode the number downstream tasks depend on.

<!-- Plan 08 SUMMARY ground truth that 09a must preserve -->
- Plan 08 enrolled 156 rows (61 shared + 95 file_io). Post-Plan-08 tier1Mappings = 505.
- `python-tier1-shared` selector count=61, hash length=64 (verified live).
- `python-tier1-file_io` selector count=95, hash length=64 (verified live).
- Plan 08 DELETED `python-tier2-aux-cache-runtime` (the 3 FileHasher cache bindings became tier1 rows).
- Plan 09a MUST preserve Plan 08's shared and file_io rows and selector hashes exactly.

<!-- Existing runtime_coverage_registry entries Plan 09a must handle -->
- `python-tier1-config` (count=43) — UNCHANGED
- `python-tier1-scanlog` (count=247) — BUMP to 247 (NOT 251 — the 4 method residuals go in a SEPARATE selector per L15 R8 precedent)
- `python-tier2-config-runtime` — PRESERVED (Plan 06 precedent)
- `python-tier2-scanlog-runtime` — DELETED (M12: all 4 methods become tier1 via `python-tier1-scanlog-wave10-residuals`; stale entry retired)
- `python-tier1-shared` (count=61, hash=c535a1...) — UNCHANGED
- `python-tier1-file_io` (count=95, hash=4bb08d...) — UNCHANGED
- 14 NEW selectors to ADD: `python-tier1-<owner>` for each of 14 untracked owners
- 1 NEW selector to ADD: `python-tier1-scanlog-wave10-residuals` (L15 R8 precedent — 4 scanlog method residuals get a separate selector with testSuite=test_promoted_residuals_smoke.py)

<!-- validate_stubs.py scope caveat (M11) -->
tools/python_api_parity/../validate_stubs.py at ClassicLib-rs/validate_stubs.py L318-336 walks ONLY `ClassicLib-rs/python-bindings/*-py/` directories. It does NOT walk `ClassicLib-rs/foundation/classic-shared-py/`. Therefore:
- Task 0 Step 3 stub audit covers config/scanlog/version_registry/file_io/shared (the current tier1 owners under python-bindings/) plus any of the 14 new owners that validate_stubs.py detects (it will find them because they're under python-bindings/).
- classic_shared stub coverage is guaranteed by explicit mypy --strict in Plan 09b Task 4 Step 1, NOT by validate_stubs.py.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 0: Baseline refresh + constructor inventory + stub audit + three-branch wrapper check + dry-run projection</name>
  <files>
    .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
    .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md
    .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
    .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md
    .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
  </files>
  <read_first>
    - tools/binding_parity_runtime_coverage.py (ENTIRE file — specifically L57-59 for _stable_id_hash, L221-330 for build_coverage_summary, L264-292 for the registry_only fallback that drives C3)
    - tools/python_api_parity/generate_baseline.py (re-verify lines 672-708 for the rust_unmapped/python_unmapped branches 09b will delete; line numbers may drift after each baseline refresh)
    - tools/python_api_parity/check_parity_gate.py (the gate exit conditions at L292-329: newly_uncovered_total, registry_mismatch_total, tier1_missing_runtime_total — these ARE asserted; deferred_total is NOT asserted by the gate directly, only by PYT-06 via runtime_coverage_summary.md reporting)
    - docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json (read a sample — 1,202 entries, all classification=deferred; Phase 9b will empty this)
    - ClassicLib-rs/validate_stubs.py (L318 bindings_dir resolution — confirms foundation/classic-shared-py is NOT in scope; informs M11 fix)
    - .planning/phases/03-python-tier-collapse/03-08-classic-shared-and-file-io-aux-SUMMARY.md (specifically the "Rule 2 stub completeness fix" and the selector hash values c535a1... / 4bb08d...)
    - .planning/phases/03-python-tier-collapse/_build_plan08_rows.py (L261-283 for the @rust proxy pattern, L46-78 for routing map shape)
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/lib.rs (to understand the module structure for the largest owner)
    - ClassicLib-rs/python-bindings/classic-scangame-py/src/ba2.rs (L8, L62 for #[pyclass(name = "BA2Issues")] / #[pyclass(name = "BA2Scanner")] pattern examples)
    - ClassicLib-rs/python-bindings/classic-constants-py/src/lib.rs (verifies that PyO3 #[pymethods] blocks use bare `fn method()` not `pub fn`, which is the root cause of C1)
  </read_first>
  <action>
    **Step 1 — Regenerate baseline so all residual counts are ground-truth-fresh** (M9 fix; never hardcode):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```
    After this command, read the regenerated `docs/implementation/python_api_parity/baseline/parity_diff_report.json` and store the residual count for the rest of the task. Do NOT use the frontmatter `735` literal anywhere.

    **Step 2 — Constructor inventory** (H5 fix; dedicated Task 0 artifact matching Plans 02-08 precedent):

    Read every `ClassicLib-rs/python-bindings/classic-*-py/src/*.rs` file across the 14 new owners AND the 4 scanlog method residual target files. For each file, extract every `#[pymethods] impl Py<ClassName> { ... }` block and capture every `#[new] fn new(...)` constructor signature with its argument list. Write `.planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md` with the format:

    ```markdown
    # Plan 09a — Constructor Inventory (authoritative source for smoke test argument lists)

    ## classic_scangame
    - `BA2Issues` — `fn new() -> Self` (no args)
    - `BA2Scanner` — `fn new(xse_dir: PyPath) -> Self` (1 arg)
    - `IntegrityConfig` — `fn new(game_exe: PyPath, old_hash: String, new_hash: String, game_name: String) -> Self` (4 args)
    ... etc, every PyClass with #[new] across classic-scangame-py/src/*.rs ...

    ## classic_path
    ... etc ...
    ```

    For PyClasses WITHOUT a `#[new]` constructor (e.g., factory-only classes, read-only data classes), explicitly note "NO CONSTRUCTOR — factory or data class". For method residuals whose parent class IS already tier1 (scanlog CrashgenVersion, LogParser, PatternMatcher), note the parent class and the method signature from the parent crate's source.

    This inventory is read by both `_build_plan09a_rows.py` (to decide @rust vs python anchor routing) AND by `_scaffold_plan09a_tests.py` (to emit correct constructor-call test skeletons in Task 2).

    Commit:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md
    git commit -m "Docs(03-09a): Plan 09a constructor inventory for 14 residual-promotion owners"
    ```

    **Step 3 — Pre-task Rule 2 stub audit** (Plan 08 Rule 2 lesson — M11 scope caveat documented):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    ```
    Capture every `[ERROR]` and `[WARNING]` line. Write `.planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md` with one section per crate containing the audit output. Add a note:
    > validate_stubs.py L318 sets `bindings_dir = rust_dir / "python-bindings"`. It does NOT walk `ClassicLib-rs/foundation/classic-shared-py/`. Therefore classic_shared stub coverage is guaranteed by the explicit `mypy --strict ClassicLib-rs/foundation/classic-shared-py/classic_shared.pyi` step in Plan 09b Task 4 Step 1, NOT by validate_stubs.

    If the audit surfaces ERRORS, document them under "Pre-existing stub holes to fix in Task 1". If only WARNINGS (or nothing), document "no blockers".

    Commit:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md
    git commit -m "Docs(03-09a): Pre-task Rule 2 stub audit (M11 scope caveat documented)"
    ```

    **Step 4 — Author `_build_plan09a_rows.py` scaffold WITH THREE-BRANCH wrapper check** (C1 fix):

    Create `.planning/phases/03-python-tier-collapse/_build_plan09a_rows.py`. The MINIMUM Task 0 scaffold must contain:

    ```python
    #!/usr/bin/env python3
    """Build Plan 09a residual promotion contract rows (multi-owner helper).

    C1 FIX: find_wrapper has three branches keyed on gap shape.
    C2 FIX: contractIdsHash is computed via imported _stable_id_hash (full 64-char SHA-256).
    R3: EXCLUDED_OWNERS = {"file_io", "shared"}.
    R9: EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}.
    """
    from __future__ import annotations

    import json
    import sys
    from collections import defaultdict
    from pathlib import Path

    REPO_ROOT = Path.cwd()
    PHASE_DIR = REPO_ROOT / ".planning/phases/03-python-tier-collapse"
    DIFF_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_diff_report.json"
    CONTRACT_PATH = REPO_ROOT / "docs/implementation/python_api_parity/baseline/parity_contract.json"

    # Import _stable_id_hash from live tooling (C2 fix — do NOT reimplement)
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from binding_parity_runtime_coverage import _stable_id_hash  # noqa: E402

    EXCLUDED_OWNERS = {"file_io", "shared"}          # R3: Plan 08 owns these
    EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}   # R9: LazyLock static, not tier1-promotable


    def find_wrapper(owner: str, residual: dict) -> tuple[bool, str]:
        """Three-branch wrapper check (C1 fix — see plan <interfaces> for details)."""
        gap_type = residual.get("gap_type")
        owner_dir = REPO_ROOT / f"ClassicLib-rs/python-bindings/classic-{owner.replace('_', '-')}-py/src"
        if not owner_dir.exists():
            return (False, "no_py_crate_dir")

        # BRANCH 1: rust_unmapped -> skip wrapper check entirely (uses @rust proxy)
        if gap_type == "rust_unmapped":
            return (True, "rust_unmapped_uses_rust_proxy")

        py_export_path = residual.get("python_export_path") or ""

        # BRANCH 2: method residual (has dot in export path) -> verify class wrapper
        if "." in py_export_path:
            class_name = py_export_path.split(".")[0]
            candidates = [
                f'name = "{class_name}"',
                f"pub struct Py{class_name}",
                f"pub struct {class_name}",
                f"pub enum Py{class_name}",
                f"pub enum {class_name}",
            ]
            for rs in owner_dir.rglob("*.rs"):
                text = rs.read_text(encoding="utf-8", errors="ignore")
                if any(c in text for c in candidates):
                    return (True, f"class_wrapper_found:{rs.name}")
            return (False, f"class_wrapper_not_found:{class_name}")

        # BRANCH 3: top-level residual (class or function) -> bare-name search
        top_level = py_export_path or residual.get("python_export") or residual.get("rust_symbol") or ""
        top_level_bare = top_level.split(".")[-1]
        candidates_sym = [
            f'name = "{top_level_bare}"',
            f"pub struct Py{top_level_bare}",
            f"pub struct {top_level_bare}",
            f"pub enum Py{top_level_bare}",
            f"pub enum {top_level_bare}",
        ]
        for rs in owner_dir.rglob("*.rs"):
            text = rs.read_text(encoding="utf-8", errors="ignore")
            if any(c in text for c in candidates_sym):
                return (True, f"top_level_wrapper_found:{rs.name}")
            # Function fallback: #[pyfunction] followed by fn <bare>
            if "#[pyfunction]" in text and f"fn {top_level_bare}" in text:
                return (True, f"top_level_fn_found:{rs.name}")
        return (False, f"top_level_wrapper_not_found:{top_level_bare}")


    def load_residuals() -> list[dict]:
        diff = json.loads(DIFF_PATH.read_text(encoding="utf-8"))
        return [
            g for g in diff["gaps"]
            if g["tier"] == "tier2"
            and g["owner_module"] not in EXCLUDED_OWNERS
            and not (g["gap_type"] == "rust_unmapped" and g.get("rust_symbol") in EXCLUDED_RUST_SYMBOLS)
        ]


    def classify_residuals(residuals: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
        """Partition residuals into {owner: [residuals]} inventory and blockers list."""
        inventory: dict[str, list[dict]] = defaultdict(list)
        blockers: list[dict] = []
        for r in residuals:
            owner = r["owner_module"]
            found, reason = find_wrapper(owner, r)
            if found:
                r = dict(r)
                r["_wrapper_reason"] = reason
                inventory[owner].append(r)
            else:
                blockers.append({**r, "_block_reason": reason})
        return dict(inventory), blockers


    def write_blockers(blockers: list[dict]) -> Path:
        out = PHASE_DIR / "03-09a-BLOCKERS.md"
        lines = [
            "# Plan 09a — Wrapper-less Residual Blockers",
            "",
            f"**{len(blockers)} residuals have no resolvable wrapper after the three-branch check.**",
            "",
            "## Blockers grouped by owner",
            "",
        ]
        by_owner: dict[str, list[dict]] = defaultdict(list)
        for b in blockers:
            by_owner[b["owner_module"]].append(b)
        for owner in sorted(by_owner):
            lines.append(f"### {owner} ({len(by_owner[owner])} residuals)")
            lines.append("")
            for b in by_owner[owner]:
                sym = b.get("rust_symbol") or b.get("python_export_path") or b.get("python_export") or "?"
                lines.append(f"- `{sym}` ({b['gap_type']}, kind={b.get('kind','?')}, reason={b['_block_reason']})")
            lines.append("")
        lines.extend([
            "## Remediation options",
            "",
            "1. **Add the missing -py wrapper manually** in the owner's src/ tree, then re-run Plan 09a Task 0.",
            "2. **Add the symbol to EXCLUDED_RUST_SYMBOLS** in _build_plan09a_rows.py IF genuinely internal; MUST cite a STATE.md / CONTEXT.md decision.",
            "3. **Split a wrapper-authoring subtask** into a new plan before Plan 09a resumes.",
            "",
            "Plan 09a will NOT proceed to Task 1 until either this file is empty OR every blocker is resolved.",
        ])
        out.write_text("\n".join(lines), encoding="utf-8")
        return out


    def write_inventory(inventory: dict[str, list[dict]]) -> Path:
        out = PHASE_DIR / "03-09a-RESIDUAL-INVENTORY.md"
        total = sum(len(v) for v in inventory.values())
        lines = [
            "# Plan 09a — Residual Promotion Inventory",
            "",
            f"**Source:** `parity_diff_report.json::gaps` after Task 0 Step 1 baseline refresh",
            f"**Total residuals:** {total} (after R9 GLOBAL_FCX_HANDLER exclusion + R3 file_io/shared exclusion)",
            f"**Owners:** {len(inventory)}",
            "",
            "## Per-owner counts",
            "",
        ]
        for owner in sorted(inventory):
            lines.append(f"- `{owner}` — {len(inventory[owner])} residuals")
        lines.extend(["", "## Per-owner residual lists", ""])
        for owner in sorted(inventory):
            lines.append(f"### {owner} ({len(inventory[owner])})")
            lines.append("")
            for r in inventory[owner]:
                sym = r.get("rust_symbol") or r.get("python_export_path") or r.get("python_export") or "?"
                lines.append(f"- `{sym}` ({r['gap_type']}, kind={r.get('kind','?')}, wrapper={r['_wrapper_reason']})")
            lines.append("")
        out.write_text("\n".join(lines), encoding="utf-8")
        return out


    # ------------------------------------------------------------------------
    # TASK 0 DRIVER
    # ------------------------------------------------------------------------

    def main_task0() -> int:
        residuals = load_residuals()
        print(f"Loaded {len(residuals)} residuals from live parity_diff_report.json::gaps")

        inventory, blockers = classify_residuals(residuals)
        if blockers:
            out = write_blockers(blockers)
            print(f"BLOCKED: wrote {out} with {len(blockers)} blockers. Stopping.")
            return 1

        out = write_inventory(inventory)
        total = sum(len(v) for v in inventory.values())
        print(f"OK: wrote {out} with {total} residuals across {len(inventory)} owners.")
        return 0


    if __name__ == "__main__":
        sys.exit(main_task0())
    ```

    Run the helper:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py
    ```
    Expected: exits 0 with `OK: wrote ... 735 residuals across 15 owners` (or the live fresh count after baseline refresh).
    If it exits non-zero, the blockers list must be reviewed and either (a) wrapper authored + helper re-run, or (b) human escalation.

    **Step 4b — Empirical three-branch test** (C1 acceptance evidence): run a one-off Python snippet that picks one residual from each branch and confirms find_wrapper returns (True, reason):
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "
import sys, json
sys.path.insert(0, str('.planning/phases/03-python-tier-collapse'))
sys.path.insert(0, 'tools')
from _build_plan09a_rows import find_wrapper
diff = json.loads(open('docs/implementation/python_api_parity/baseline/parity_diff_report.json', encoding='utf-8').read())
gaps = [g for g in diff['gaps'] if g['tier'] == 'tier2' and g['owner_module'] not in ('file_io', 'shared')]
rust_only = next((g for g in gaps if g['gap_type'] == 'rust_unmapped' and g.get('rust_symbol') != 'GLOBAL_FCX_HANDLER'), None)
method = next((g for g in gaps if g['gap_type'] == 'python_unmapped' and '.' in (g.get('python_export_path') or '')), None)
top_level = next((g for g in gaps if g['gap_type'] == 'python_unmapped' and '.' not in (g.get('python_export_path') or '')), None)
for label, g in [('rust_only', rust_only), ('method', method), ('top_level', top_level)]:
    assert g is not None, f'No sample for {label}'
    owner = g['owner_module']
    result = find_wrapper(owner, g)
    print(f'{label}: {result}')
    assert result[0], f'{label} SHOULD pass: {result}'
print('All three branches verified OK')
"
    ```
    Expected output:
    ```
    rust_only: (True, 'rust_unmapped_uses_rust_proxy')
    method: (True, 'class_wrapper_found:<file>.rs')
    top_level: (True, 'top_level_wrapper_found:<file>.rs')
    All three branches verified OK
    ```

    Commit (helper + inventory are committed together because the inventory depends on the helper's classification):
    ```powershell
    git add .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md
    git commit -m "Docs(03-09a): Plan 09a helper scaffold with three-branch wrapper check + residual inventory"
    ```

    **Step 5 — Refresh the parity-artifacts mirror** (Task 0 Step 1's generate_baseline only writes to docs/implementation/.../baseline/; the parity-artifacts mirror is refreshed via check_parity_gate --update-baseline):
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```

    Commit:
    ```powershell
    git add docs/implementation/python_api_parity/baseline/ ClassicLib-rs/python-bindings/parity-artifacts/
    git commit -m "Chore(03-09a): Refresh parity baseline + artifacts mirror before Task 1 row authoring"
    ```

    **Step 6 — Dry-run projection** (H6 fix; C3 diagnostic artifact):

    Write `.planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md` using data computed via a Python helper:

    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c "
import sys, json
sys.path.insert(0, 'tools')
from pathlib import Path
from binding_parity_runtime_coverage import build_coverage_summary, load_json_file

repo = Path('.')
contract = json.loads((repo / 'docs/implementation/python_api_parity/baseline/parity_contract.json').read_text(encoding='utf-8'))
diff = json.loads((repo / 'docs/implementation/python_api_parity/baseline/parity_diff_report.json').read_text(encoding='utf-8'))
runtime = load_json_file(repo / 'ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json')
deferred = load_json_file(repo / 'docs/implementation/python_api_parity/governance/deferred_runtime_backlog.json')

# Current state
now = build_coverage_summary(binding='python', contract=contract, diff_report=diff, runtime_registry=runtime, deferred_registry=deferred)['summary']
print(f'Current (pre-09a): deferred_total={now[\"deferred_total\"]}, tier1_contract_total={now[\"tier1_contract_total\"]}, tracked_total={now[\"tracked_surface_total\"]}')

# Post-09a simulation: Plan 09a promotes ~735 residuals to tier1. After baseline refresh,
# those gap rows disappear from gaps[] because their rust_symbols and python exports
# are now covered by tier1_rust_symbols / tier1_python_pairs filters in generate_diff_report.
# But the deferred_runtime_backlog entries remain; they appear in tracked_surface as
# registry_only items via the fallback at L264-292 and keep their 'deferred' classification.
import copy
post_09a_diff = copy.deepcopy(diff)
post_09a_diff['gaps'] = [g for g in diff['gaps'] if g['tier'] != 'tier2' or (g.get('gap_type') == 'rust_unmapped' and g.get('rust_symbol') == 'GLOBAL_FCX_HANDLER') or g['owner_module'] in ('file_io', 'shared')]
post_09a = build_coverage_summary(binding='python', contract=contract, diff_report=post_09a_diff, runtime_registry=runtime, deferred_registry=deferred)['summary']
print(f'Post-09a (contract unchanged in sim; gaps filtered): deferred_total={post_09a[\"deferred_total\"]}, newly_uncovered_total={post_09a[\"newly_uncovered_total\"]}')

# Post-09b simulation: 09b deletes tier2 branches AND empties deferred registry
empty = {'schemaVersion': '1.0', 'binding': 'python', 'entries': []}
post_09b = build_coverage_summary(binding='python', contract=contract, diff_report=post_09a_diff, runtime_registry=runtime, deferred_registry=empty)['summary']
print(f'Post-09b (gaps filtered + deferred registry empty): deferred_total={post_09b[\"deferred_total\"]}, newly_uncovered_total={post_09b[\"newly_uncovered_total\"]}')
" | Out-File -FilePath .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.txt -Encoding UTF8
    ```

    Then wrap that raw output into `.planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md` with framing:

    ```markdown
    # Plan 09a — Dry-Run Projection (REVIEWS.md Round 2 H6 fix)

    **Generated:** (Task 0 Step 6)
    **Purpose:** Empirically project post-09a and post-09b deferred_total BEFORE Task 1 commits any rows.

    ## Why this is not a gate

    Plan 09a alone cannot drive `deferred_total` to 0. The live `build_coverage_summary` in
    `tools/binding_parity_runtime_coverage.py` L264-292 contains a `registry_only` fallback
    that promotes every `deferred_runtime_backlog.json::entries` item into `tracked_surface`
    with classification="deferred" EVEN IF its gap row has disappeared from `parity_diff_report.json::gaps`.

    Therefore:
    - After Plan 09a row promotions + baseline refresh, the `gap` path contribution to `deferred_total`
      drops to ~0 (all promoted residuals no longer appear as gaps).
    - But the `registry_only` path contribution remains ~1008 because 1,202 deferred backlog
      entries still exist in the file.
    - Plan 09b explicitly EMPTIES `deferred_runtime_backlog.json::entries` to drive `deferred_total`
      to 0. This is legitimate Phase 3 hygiene (the file's contents no longer reflect the promoted state);
      it does NOT cross the Phase 6 DOC-02/DOC-04 boundary because Phase 6 owns DELETING the file,
      not editing its contents.

    ## Empirical projection

    <insert raw output from the one-liner above>

    ## Gate endgame (after 09a commits + 09b Task 2 + 09b empties backlog + final refresh)

    - `tier1_contract_total`: 505 + <post-09a row count>
    - `deferred_total`: 0
    - `newly_uncovered_total`: 0
    - `tier1_missing_runtime_total`: 0
    - `registry_mismatch_total`: 0 (only if _stable_id_hash is used correctly per C2 fix)
    ```

    Commit:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md
    git commit -m "Docs(03-09a): Dry-run projection for deferred_total endgame (C3 reviewer feedback)"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md)) { Write-Error 'CONSTRUCTOR-INVENTORY.md missing'; exit 1 }; if (-not (Test-Path .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md)) { Write-Error 'STUB-AUDIT.md missing'; exit 1 }; if (-not (Test-Path .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py)) { Write-Error 'helper missing'; exit 1 }; if (-not (Test-Path .planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md)) { Write-Error 'DRY-RUN-PROJECTION.md missing'; exit 1 }; $helper = Get-Content .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py -Raw; if ($helper -notmatch 'rust_unmapped_uses_rust_proxy') { Write-Error 'helper missing Branch 1 marker'; exit 1 }; if ($helper -notmatch 'class_wrapper_found|class_wrapper_not_found') { Write-Error 'helper missing Branch 2 marker'; exit 1 }; if ($helper -notmatch 'top_level_wrapper_found|top_level_fn_found|top_level_wrapper_not_found') { Write-Error 'helper missing Branch 3 marker'; exit 1 }; if ($helper -notmatch 'from binding_parity_runtime_coverage import _stable_id_hash') { Write-Error 'helper must import _stable_id_hash from live module (C2 fix)'; exit 1 }; $inventory_exists = Test-Path .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md; $blockers_exists = Test-Path .planning/phases/03-python-tier-collapse/03-09a-BLOCKERS.md; if (-not ($inventory_exists -or $blockers_exists)) { Write-Error 'Either RESIDUAL-INVENTORY.md or BLOCKERS.md MUST exist'; exit 1 }; if ($inventory_exists -and $blockers_exists) { Write-Error 'Cannot have both inventory and blockers'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -c \"import sys, json; sys.path.insert(0, str('.planning/phases/03-python-tier-collapse')); sys.path.insert(0, 'tools'); from _build_plan09a_rows import find_wrapper; diff = json.loads(open('docs/implementation/python_api_parity/baseline/parity_diff_report.json', encoding='utf-8').read()); gaps = [g for g in diff['gaps'] if g['tier'] == 'tier2' and g['owner_module'] not in ('file_io', 'shared')]; rust_only = next((g for g in gaps if g['gap_type'] == 'rust_unmapped' and g.get('rust_symbol') != 'GLOBAL_FCX_HANDLER'), None); method = next((g for g in gaps if g['gap_type'] == 'python_unmapped' and '.' in (g.get('python_export_path') or '')), None); top_level = next((g for g in gaps if g['gap_type'] == 'python_unmapped' and '.' not in (g.get('python_export_path') or '')), None); assert rust_only and method and top_level; assert find_wrapper(rust_only['owner_module'], rust_only)[0], 'rust_only wrapper check failed'; assert find_wrapper(method['owner_module'], method)[0], 'method wrapper check failed'; assert find_wrapper(top_level['owner_module'], top_level)[0], 'top_level wrapper check failed'; print('Three branches OK')\"; if ($LASTEXITCODE -ne 0) { exit 1 }; Write-Host 'Task 0 OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md` exists and contains at least 14 owner sections (one per new enrolled owner) plus a scanlog section for the 4 method residuals.
    - `.planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md` exists and contains a note about validate_stubs.py scope limitation (classic_shared not covered; covered by mypy in 09b).
    - `.planning/phases/03-python-tier-collapse/_build_plan09a_rows.py` exists with the literal markers `rust_unmapped_uses_rust_proxy`, `class_wrapper_found`, `top_level_wrapper_found` — proving all three wrapper-check branches are present (C1 acceptance).
    - `_build_plan09a_rows.py` contains the literal line `from binding_parity_runtime_coverage import _stable_id_hash` (C2 acceptance; NO reimplementation).
    - `_build_plan09a_rows.py` contains `EXCLUDED_RUST_SYMBOLS = {"GLOBAL_FCX_HANDLER"}` and `EXCLUDED_OWNERS = {"file_io", "shared"}`.
    - EITHER `03-09a-RESIDUAL-INVENTORY.md` exists (meaning all residuals passed the wrapper check) OR `03-09a-BLOCKERS.md` exists (meaning the helper fail-closed and the plan has stopped). Exactly one, not both.
    - Empirical three-branch test: loading one `rust_unmapped` residual, one method residual (python_export_path contains `.`), and one top-level residual from the live diff, calling `find_wrapper(owner, residual)` returns `(True, reason)` for all three without landing in BLOCKERS.
    - `.planning/phases/03-python-tier-collapse/03-09a-DRY-RUN-PROJECTION.md` exists and documents: (a) current `deferred_total`, (b) projected post-09a `deferred_total` (expected ~1008, NOT 0), (c) projected post-09b `deferred_total` (expected 0 only after 09b empties the backlog), (d) the explanation of the C3 registry_only fallback.
    - `parity_diff_report.json` has been regenerated in-task (Task 0 Step 1 mtime is newer than commit 35e28d05).
    - Commit messages follow convention: `Docs(03-09a): ...` and `Chore(03-09a): ...`.
  </acceptance_criteria>
  <done>Baseline regenerated; constructor inventory + stub audit + residual inventory + dry-run projection all committed; helper has verified three-branch wrapper check AND imports _stable_id_hash from live module; either proceed to Task 1 or fail-closed with blockers list.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1: Extend _build_plan09a_rows.py with multi-owner routing + same-row-dedup + @rust proxy pattern + scanlog method residuals; emit contract rows; apply Rule 2 stub fixes surfaced in Task 0 audit</name>
  <files>
    .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py
    docs/implementation/python_api_parity/baseline/parity_contract.json
    ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi
    ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi
    ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi
    ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi
    ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi
    ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi
    ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi
    ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi
    ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi
    ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi
    ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi
    ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi
    ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi
    ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi
    ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi
  </files>
  <behavior>
    - The helper produces a deterministic ordered list of contract rows for all 14 new owners + 4 scanlog method residuals.
    - Every Python class becomes an owner-level row with pythonExportPath=ClassName; class methods get rows with pythonExportPath=ClassName.method.
    - Every rust-only re-export becomes a `<owner>.<sub_module>.<symbol>@rust` proxy paired with the nearest Python anchor class (Plan 08 same-row-dedup precedent at _build_plan08_rows.py L261-283).
    - Same-row-dedup tracks `already_covered_rust_symbols` across ALL 14 owners in one pass.
    - GLOBAL_FCX_HANDLER is NEVER in the output rows.
    - file_io and shared owners are NEVER in the output rows; Plan 08's file_io=95 and shared=61 counts remain exactly.
    - Every contract ID is unique across new rows AND against existing 505 rows.
    - Every pythonExportPath resolves against python_api_surface.json::exports.
    - Every @rust rustSymbol resolves against rust_api_surface.json::symbols.
    - Rule 2 stub holes surfaced by validate_stubs.py AFTER row authoring get fixed inline in the same commit per Plan 08 precedent (TSDoc + accurate type signatures).
  </behavior>
  <read_first>
    - .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md (Task 0 output)
    - .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md (Task 0 output)
    - .planning/phases/03-python-tier-collapse/03-09a-STUB-AUDIT.md (Task 0 output)
    - .planning/phases/03-python-tier-collapse/_build_plan08_rows.py (template for multi-owner + @rust proxy pattern)
    - docs/implementation/python_api_parity/baseline/python_api_surface.json (the source of pythonExportPath strings)
    - docs/implementation/python_api_parity/baseline/rust_api_surface.json (the source of @rust rustSymbol strings)
    - For each of the 14 new owners: ClassicLib-rs/python-bindings/classic-<owner>-py/src/lib.rs to find m.add_class / wrap_pyfunction registrations
    - For each owner with class residuals: the relevant `-py/src/<sub_module>.rs` files for #[pymethods] #[new] constructor signatures (already captured in CONSTRUCTOR-INVENTORY.md)
  </read_first>
  <action>
    Step 1 — Extend `_build_plan09a_rows.py` with per-owner routing maps and a `main_task1()` driver. The routing maps follow the `_build_plan08_rows.py::SHARED_CLASS_ROUTING` and `::SHARED_RUST_ONLY` precedent. For each of the 14 owners:

    ```python
    # Example for constants (58 residuals)
    CONSTANTS_CLASS_ROUTING: dict[str, tuple[str, str]] = {
        # Python class name -> (sub_module name, rust symbol for class row)
        "YamlFile":        ("yaml_files",   "PyYamlFile"),
        "GameId":          ("games",        "PyGameId"),
        "Fallout4Version": ("fo4_version",  "PyFallout4Version"),
        # ... etc, one entry per #[pyclass] in classic-constants-py ...
    }
    CONSTANTS_RUST_ONLY: dict[str, tuple[str, str]] = {
        # Rust-only symbols -> (sub_module, anchor class from CONSTANTS_CLASS_ROUTING)
        "Fallout4Version": ("fo4_version",  "Fallout4Version"),  # classic-constants-core's enum; @rust proxy
        "GameId":          ("games",        "GameId"),            # same
        "YamlFile":        ("yaml_files",   "YamlFile"),          # same
        "NULL_VERSION":    ("fo4_version",  "Fallout4Version"),   # const re-export
        # ... every rust_unmapped residual for constants ...
    }
    CONSTANTS_MODULE_FUNCTIONS: dict[str, tuple[str, str]] = {
        # export_path -> (sub_module, rust_symbol)  — for free #[pyfunction] items
    }
    ```

    Repeat for each of the 14 owners, using the residual inventory to know which classes and rust symbols need routing. Classes are the primary anchor; rust-only symbols become @rust proxies paired with the nearest Python anchor class in the same sub_module. Module-level functions get their own rows without a class prefix.

    For the 4 scanlog method residuals, define:
    ```python
    SCANLOG_METHOD_RESIDUALS = [
        # (parent_class, method_name, arity, sub_module)
        ("CrashgenVersion", "to_tuple", 0, "version"),
        ("LogParser", "find_errors", 1, "parser"),
        ("PatternMatcher", "find_all", 1, "parser"),
        ("PatternMatcher", "has_match", 1, "parser"),
    ]
    ```
    Each becomes a new tier1 row under the existing scanlog owner with `id = "scanlog.<sub>.<Parent>.<method>"`, `pythonExportPath = "<Parent>.<method>"`, `rustSymbol = "<Parent>"` (inherited from parent class), NOT an @rust proxy.

    Step 2 — Add the main_task1() driver that walks owners in a deterministic order, applies the routing maps to inventory residuals, enforces same-row-dedup across ALL owners via `already_covered_rust_symbols`, and writes new rows to `parity_contract.json`:

    ```python
    def main_task1() -> int:
        inventory = load_inventory_from_file()  # from Task 0 output
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        existing_ids = {m["id"] for m in contract["tier1Mappings"]}
        existing_rust_symbols = {m["rustSymbol"] for m in contract["tier1Mappings"]}
        already_covered_rust_symbols = set(existing_rust_symbols)

        new_rows: list[dict] = []
        per_owner_count: dict[str, int] = {}
        dedup_savings = 0

        OWNER_ORDER = [
            "scangame", "path", "constants", "message", "database", "resource",
            "xse", "settings", "yaml", "registry", "web", "version", "perf", "update",
        ]
        for owner in OWNER_ORDER:
            owner_rows = build_owner_rows(
                owner=owner,
                inventory=inventory.get(owner, []),
                already_covered_rust_symbols=already_covered_rust_symbols,
            )
            per_owner_count[owner] = len(owner_rows)
            new_rows.extend(owner_rows)
            dedup_savings += (count_potential_rows(owner, inventory) - len(owner_rows))

        # 4 scanlog method residuals
        scanlog_method_rows = build_scanlog_method_rows()
        new_rows.extend(scanlog_method_rows)
        per_owner_count["scanlog_methods"] = len(scanlog_method_rows)

        # Assertions
        new_ids = {r["id"] for r in new_rows}
        assert len(new_ids) == len(new_rows), "Duplicate IDs inside new_rows"
        assert new_ids.isdisjoint(existing_ids), f"Conflict with existing IDs: {new_ids & existing_ids}"

        contract["tier1Mappings"].extend(new_rows)
        CONTRACT_PATH.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
        print(f"Added {len(new_rows)} new tier1 rows; dedup saved {dedup_savings} rows")
        print(f"Per-owner counts: {per_owner_count}")
        print(f"Total tier1Mappings: {len(contract['tier1Mappings'])}")
        return 0
    ```

    Run:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py --task 1
    ```
    (The helper's `__main__` block dispatches between `main_task0` and `main_task1` based on a `--task` argument.)

    Step 3 — Re-run validate_stubs.py to surface any Rule 2 stub holes that show up after enrollment:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    ```
    For every missing function/class reported, ADD the stub entry to the correct `.pyi` file with full TSDoc comments and accurate type signatures (Plan 08 precedent). These fixes are committed in the SAME atomic commit as the contract row additions.

    Step 4 — Atomic commit:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py docs/implementation/python_api_parity/baseline/parity_contract.json ClassicLib-rs/python-bindings/classic-*-py/*.pyi
    git commit -m "Feat(03-09a): Promote 735 residual tier2 rows to tier1 across 14 owners + 4 scanlog methods"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$contract = Get-Content docs/implementation/python_api_parity/baseline/parity_contract.json -Raw | ConvertFrom-Json; $count = $contract.tier1Mappings.Count; Write-Host \"tier1Mappings.Count = $count\"; if ($count -lt 1100) { Write-Error \"Expected at least 1100 tier1Mappings, got $count\"; exit 1 }; $fileIo = @($contract.tier1Mappings | Where-Object { $_.ownerModule -eq 'file_io' }).Count; $shared = @($contract.tier1Mappings | Where-Object { $_.ownerModule -eq 'shared' }).Count; if ($fileIo -ne 95) { Write-Error \"Plan 08 file_io count changed: expected 95, got $fileIo\"; exit 1 }; if ($shared -ne 61) { Write-Error \"Plan 08 shared count changed: expected 61, got $shared\"; exit 1 }; $fcx = @($contract.tier1Mappings | Where-Object { $_.rustSymbol -eq 'GLOBAL_FCX_HANDLER' }).Count; if ($fcx -ne 0) { Write-Error \"GLOBAL_FCX_HANDLER should not appear in tier1Mappings (R9 lock)\"; exit 1 }; $ids = $contract.tier1Mappings | ForEach-Object { $_.id }; $uniqueIds = $ids | Select-Object -Unique; if ($ids.Count -ne $uniqueIds.Count) { Write-Error 'Duplicate contract IDs detected'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { Write-Error 'validate_stubs.py failed'; exit 1 }; Write-Host 'Task 1 OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length` is at least 1100 (505 baseline + 595+ post-dedup residuals from Task 1).
    - `parity_contract.json::tier1Mappings` contains EXACTLY 95 rows with `ownerModule == "file_io"` (Plan 08 hard lock).
    - `parity_contract.json::tier1Mappings` contains EXACTLY 61 rows with `ownerModule == "shared"` (Plan 08 hard lock).
    - `parity_contract.json::tier1Mappings` contains ZERO rows with `rustSymbol == "GLOBAL_FCX_HANDLER"` (R9 lock).
    - All contract IDs are unique across the new rows AND the existing 505 rows.
    - Every new row's `pythonExportPath` exists in `python_api_surface.json::exports`.
    - Every new `@rust`-suffixed row's `rustSymbol` exists in `rust_api_surface.json::symbols`.
    - `validate_stubs.py --fail-on-warnings` exits 0 against the updated contract.
    - Commit message follows convention: `Feat(03-09a): Promote 735 residual tier2 rows to tier1 across 14 owners + 4 scanlog methods`.
  </acceptance_criteria>
  <done>All 14 owners + 4 scanlog method residuals promoted; parity_contract.json updated; stubs clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Scaffold + hand-author 80-130 per-class smoke tests via _scaffold_plan09a_tests.py + D-07 enforcement</name>
  <files>
    .planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py
    ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
  </files>
  <behavior>
    - The scaffolding helper reads _build_plan09a_rows.py's routing maps and 03-09a-CONSTRUCTOR-INVENTORY.md to emit hand-verifiable test skeletons.
    - Each promoted #[pyclass] gets at least one "construct + call one real method" test per D-07.
    - Each @rust proxy row gets a "rust-only presence guard" test (import-time only, since there's no Python wrapper to construct).
    - The 4 scanlog method residuals each get a dedicated test calling the method on a constructed parent instance.
    - Hand-verification passes: each scaffolded test uses verified constructor signatures from CONSTRUCTOR-INVENTORY.md; no hasattr-only assertions.
    - Total tests: expected 80-130 (14 owners × 6-10 classes + 4 scanlog methods + rust-only guards).
  </behavior>
  <read_first>
    - .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py (routing maps from Task 1)
    - .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md (Task 0 output)
    - .planning/phases/03-python-tier-collapse/03-09a-RESIDUAL-INVENTORY.md (Task 0 output)
    - ClassicLib-rs/python-bindings/tests/test_classic_shared_smoke.py (Plan 08 template for 20-test shape)
    - ClassicLib-rs/python-bindings/tests/test_promoted_file_io_aux_smoke.py (Plan 08 template for 29-test shape)
    - For each owner's parent class: the relevant `-py/src/<module>.rs` to verify method signatures (return type, PyResult shape)
  </read_first>
  <action>
    Step 1 — Author `.planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py`:

    ```python
    #!/usr/bin/env python3
    """Scaffold per-class smoke tests for Plan 09a from routing maps + constructor inventory.

    M10 fix: this helper prevents the Rule-1 test-assumption bug class that Plan 08 hit 6 times
    at 49-test scale. It emits TODO-marked skeletons that the author hand-verifies against
    CONSTRUCTOR-INVENTORY.md and the source code.
    """
    from __future__ import annotations
    import json
    import re
    from pathlib import Path

    REPO_ROOT = Path.cwd()
    PHASE_DIR = REPO_ROOT / ".planning/phases/03-python-tier-collapse"
    OUTPUT_TEST = REPO_ROOT / "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py"

    # Load constructor inventory as text (it's markdown; parse the class lines)
    INVENTORY = (PHASE_DIR / "03-09a-CONSTRUCTOR-INVENTORY.md").read_text(encoding="utf-8")

    # Minimal test template per class
    CLASS_TEST_TEMPLATE = """
def test_{owner}_{class_snake}_construct_and_method() -> None:
    \"\"\"D-07: construct {ClassName} and call one real method.\"\"\"
    import classic_{owner}
    # TODO: verify constructor args from 03-09a-CONSTRUCTOR-INVENTORY.md
    obj = classic_{owner}.{ClassName}({args})
    # TODO: replace with actual method call + assertion
    result = obj.{first_method}({method_args})
    assert result is not None  # TODO: strengthen assertion
"""

    RUST_ONLY_GUARD_TEMPLATE = """
def test_{owner}_rust_only_presence_{symbol_snake}() -> None:
    \"\"\"Rust-only proxy guard — {rust_symbol} is not directly constructable; verify module-level presence.\"\"\"
    import classic_{owner}
    # @rust proxy row — the rust_symbol is present via the anchor class:
    assert hasattr(classic_{owner}, '{anchor_class}')
"""

    SCANLOG_METHOD_TEMPLATE = """
def test_scanlog_{parent_snake}_{method}() -> None:
    \"\"\"Scanlog method residual: {ParentClass}.{method}.\"\"\"
    import classic_scanlog
    parent = classic_scanlog.{ParentClass}({parent_args})
    result = parent.{method}({method_args})
    # TODO: verify method return shape from classic-scanlog-py/src/{sub_module}.rs
    assert result is not None
"""

    def scaffold():
        lines = [
            '"""Plan 09a — Smoke tests for promoted residual rows (auto-scaffolded; hand-verified).',
            '',
            'Scaffold source: _scaffold_plan09a_tests.py',
            'Constructor source: .planning/phases/03-python-tier-collapse/03-09a-CONSTRUCTOR-INVENTORY.md',
            'D-07 rule: every test constructs an instance and calls at least one real method.',
            '"""',
            'from __future__ import annotations',
            '',
        ]
        # TODO: walk the INVENTORY markdown to extract (owner, class, constructor_args) triples
        # and emit one test per triple using CLASS_TEST_TEMPLATE. Same for rust-only guards
        # and scanlog method residuals.
        OUTPUT_TEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote scaffold to {OUTPUT_TEST}")

    if __name__ == "__main__":
        scaffold()
    ```

    Step 2 — Hand-author the fully-populated test file by running the scaffold and filling in each TODO against CONSTRUCTOR-INVENTORY.md. Expected: 80-130 tests. The file MUST:
    - `import classic_<owner>` for every owner module touched
    - Construct each promoted #[pyclass] using verified argument signatures
    - Call at least one real method per class (D-07; never `hasattr` alone)
    - For @rust proxy rows, verify the anchor class is present (which proves the module enrolled the re-export)
    - Handle the 4 scanlog method residuals: construct parent (CrashgenVersion, LogParser, PatternMatcher), call the method, assert return shape matches the rust signature from classic-scanlog-py source

    Step 3 — Run the authored tests:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q
    ```
    Expected: all tests pass. If any fail, fix the constructor args per CONSTRUCTOR-INVENTORY.md (likely a Rule-1 test assumption bug — adjust the args, re-run).

    Step 4 — Atomic commit:
    ```powershell
    git add .planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py
    git commit -m "Test(03-09a): Per-class smoke tests for 80-130 promoted residual rows (D-07)"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "if (-not (Test-Path .planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py)) { Write-Error 'scaffold helper missing'; exit 1 }; if (-not (Test-Path ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py)) { Write-Error 'smoke test file missing'; exit 1 }; $content = Get-Content ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -Raw; $testCount = ([regex]::Matches($content, '^def test_', 'Multiline')).Count; Write-Host \"test functions: $testCount\"; if ($testCount -lt 80) { Write-Error \"Expected at least 80 tests, got $testCount\"; exit 1 }; if ($content -notmatch 'import classic_scangame') { Write-Error 'missing classic_scangame import'; exit 1 }; if ($content -notmatch 'import classic_constants') { Write-Error 'missing classic_constants import'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q; if ($LASTEXITCODE -ne 0) { Write-Error 'smoke tests failed'; exit 1 }; Write-Host 'Task 2 OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/03-python-tier-collapse/_scaffold_plan09a_tests.py` exists.
    - `ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py` exists and contains at least 80 `def test_*` functions (expected 80-130).
    - The test file imports every one of the 14 new classic_* owner modules (at least one `import classic_<owner>` per owner).
    - Every test function either constructs an instance and calls a method OR (for @rust proxy rows) verifies the anchor class is present via hasattr — but NEVER ONLY uses hasattr for a promoted #[pyclass] row (D-07 enforcement).
    - Running `pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q` exits 0.
    - Commit message follows convention: `Test(03-09a): Per-class smoke tests for 80-130 promoted residual rows (D-07)`.
  </acceptance_criteria>
  <done>All promoted residual rows have D-07 smoke tests; scaffold helper committed; test suite green.</done>
</task>

<task type="auto">
  <name>Task 3: Add 14 runtime_coverage_registry selectors using imported _stable_id_hash (C2 fix) + retire python-tier2-scanlog-runtime + add python-tier1-scanlog-wave10-residuals (L15 R8 precedent)</name>
  <files>
    ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
  </files>
  <read_first>
    - tools/binding_parity_runtime_coverage.py L57-59 (the live _stable_id_hash definition — MUST be imported, NEVER reimplemented)
    - ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json (current state; specifically `python-tier1-shared`, `python-tier1-file_io`, `python-tier1-scanlog`, `python-tier1-config`, `python-tier2-config-runtime`, `python-tier2-scanlog-runtime`)
    - docs/implementation/python_api_parity/baseline/parity_contract.json (post-Task-1 state; walked to compute per-owner IDs for hash input)
  </read_first>
  <action>
    Step 1 — Extend `_build_plan09a_rows.py` with a `main_task3()` driver that computes each selector entry by calling the live `_stable_id_hash`:

    ```python
    def main_task3() -> int:
        import hashlib
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        registry_path = REPO_ROOT / "ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))

        # 14 new tier1 selectors (one per newly-enrolled owner)
        NEW_OWNERS = [
            "scangame", "path", "constants", "message", "database", "resource",
            "xse", "settings", "yaml", "registry", "web", "version", "perf", "update",
        ]
        for owner in NEW_OWNERS:
            ids = sorted(
                m["id"] for m in contract["tier1Mappings"] if m.get("ownerModule") == owner
            )
            if not ids:
                raise RuntimeError(f"Owner {owner} has no tier1Mappings after Task 1; check routing")
            computed_hash = _stable_id_hash(ids)  # Full 64-char SHA-256 (C2 fix)
            assert len(computed_hash) == 64, f"hash length must be 64, got {len(computed_hash)}"
            entry = {
                "coverageId": f"python-tier1-{owner}",
                "classification": "runtime_verified",
                "verificationMode": "direct_call",
                "ownerModule": owner,
                "tier": "tier1",
                "contractSelector": {"ownerModule": owner, "tier": "tier1"},
                "contractCount": len(ids),
                "contractIdsHash": computed_hash,
                "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py",
                "testCaseId": f"{owner}-residuals-smoke",
            }
            # Replace if exists, else append
            registry["entries"] = [e for e in registry["entries"] if e.get("coverageId") != entry["coverageId"]]
            registry["entries"].append(entry)

        # L15 R8 precedent: separate selector for scanlog method residuals (do NOT mutate python-tier1-scanlog's testSuite)
        scanlog_method_ids = sorted(
            m["id"] for m in contract["tier1Mappings"]
            if m.get("ownerModule") == "scanlog" and any(
                m["id"].endswith(suffix) for suffix in (".to_tuple", ".find_errors", ".find_all", ".has_match")
            )
        )
        if scanlog_method_ids:
            wave10_entry = {
                "coverageId": "python-tier1-scanlog-wave10-residuals",
                "classification": "runtime_verified",
                "verificationMode": "direct_call",
                "ownerModule": "scanlog",
                "tier": "tier1",
                "contractSelector": None,  # explicit list, not selector-based
                "contractCount": len(scanlog_method_ids),
                "contractIdsHash": _stable_id_hash(scanlog_method_ids),
                "testSuite": "ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py",
                "testCaseId": "scanlog-method-residuals",
                "contractIds": scanlog_method_ids,  # explicit IDs for the 4 methods
            }
            registry["entries"] = [e for e in registry["entries"] if e.get("coverageId") != wave10_entry["coverageId"]]
            registry["entries"].append(wave10_entry)

        # M12: Retire python-tier2-scanlog-runtime — all 4 methods are now tier1 via python-tier1-scanlog-wave10-residuals
        registry["entries"] = [e for e in registry["entries"] if e.get("coverageId") != "python-tier2-scanlog-runtime"]

        # Preserve Plan 08's python-tier1-shared and python-tier1-file_io UNCHANGED (integrity check)
        shared_entry = next((e for e in registry["entries"] if e.get("coverageId") == "python-tier1-shared"), None)
        fileio_entry = next((e for e in registry["entries"] if e.get("coverageId") == "python-tier1-file_io"), None)
        assert shared_entry is not None and shared_entry.get("contractCount") == 61, "python-tier1-shared must remain count=61"
        assert fileio_entry is not None and fileio_entry.get("contractCount") == 95, "python-tier1-file_io must remain count=95"
        assert len(shared_entry["contractIdsHash"]) == 64, "Plan 08 shared hash length must remain 64"
        assert len(fileio_entry["contractIdsHash"]) == 64, "Plan 08 file_io hash length must remain 64"

        # python-tier1-scanlog is NOT mutated here; its testSuite stays as-is (L15 R8 precedent).
        # NOTE: Its contractCount will naturally grow at baseline refresh time when the scanlog
        # selector re-expands to include the 4 new method residuals via contractSelector matching.
        # But the HASH will need recomputing because the ID set changes. Handle that here too:
        scanlog_ids = sorted(m["id"] for m in contract["tier1Mappings"] if m.get("ownerModule") == "scanlog")
        scanlog_entry = next((e for e in registry["entries"] if e.get("coverageId") == "python-tier1-scanlog"), None)
        if scanlog_entry is not None:
            scanlog_entry["contractCount"] = len(scanlog_ids)
            scanlog_entry["contractIdsHash"] = _stable_id_hash(scanlog_ids)
            assert len(scanlog_entry["contractIdsHash"]) == 64

        registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        print(f"Updated runtime_coverage_registry.json: added 14 + 1 selectors, retired python-tier2-scanlog-runtime")
        return 0
    ```

    Step 2 — Run:
    ```powershell
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python .planning/phases/03-python-tier-collapse/_build_plan09a_rows.py --task 3
    ```

    Step 3 — Atomic commit:
    ```powershell
    git add ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json
    git commit -m "Feat(03-09a): Add 14 python-tier1 residual selectors + python-tier1-scanlog-wave10-residuals; retire python-tier2-scanlog-runtime"
    ```
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "$registry = Get-Content ClassicLib-rs/python-bindings/tests/fixtures/runtime_coverage_registry.json -Raw | ConvertFrom-Json; $ids = $registry.entries | ForEach-Object { $_.coverageId }; $required = @('python-tier1-scangame','python-tier1-path','python-tier1-constants','python-tier1-message','python-tier1-database','python-tier1-resource','python-tier1-xse','python-tier1-settings','python-tier1-registry','python-tier1-yaml','python-tier1-web','python-tier1-version','python-tier1-perf','python-tier1-update','python-tier1-scanlog-wave10-residuals'); foreach ($r in $required) { if ($ids -notcontains $r) { Write-Error \"Missing required selector: $r\"; exit 1 } }; if ($ids -contains 'python-tier2-scanlog-runtime') { Write-Error 'python-tier2-scanlog-runtime must be retired (M12)'; exit 1 }; foreach ($r in $required) { $entry = $registry.entries | Where-Object { $_.coverageId -eq $r } | Select-Object -First 1; if ($entry.contractIdsHash.Length -ne 64) { Write-Error \"$r contractIdsHash length must be 64 (full SHA-256; C2 fix); got $($entry.contractIdsHash.Length)\"; exit 1 }; if ($entry.contractIdsHash -match '<' ) { Write-Error \"$r has placeholder hash\"; exit 1 } }; $shared = $registry.entries | Where-Object { $_.coverageId -eq 'python-tier1-shared' } | Select-Object -First 1; $fileio = $registry.entries | Where-Object { $_.coverageId -eq 'python-tier1-file_io' } | Select-Object -First 1; if ($shared.contractCount -ne 61) { Write-Error 'Plan 08 shared count drift'; exit 1 }; if ($fileio.contractCount -ne 95) { Write-Error 'Plan 08 file_io count drift'; exit 1 }; if ($shared.contractIdsHash.Length -ne 64 -or $fileio.contractIdsHash.Length -ne 64) { Write-Error 'Plan 08 hash length drift'; exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline; if ($LASTEXITCODE -ne 0) { Write-Error 'check_parity_gate.py failed; likely registry_mismatch_total > 0 from hash drift'; exit 1 }; $summary = Get-Content docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json -Raw | ConvertFrom-Json; if ($summary.summary.registry_mismatch_total -ne 0) { Write-Error \"registry_mismatch_total must be 0 (C2 fix); got $($summary.summary.registry_mismatch_total)\"; exit 1 }; Write-Host 'Task 3 OK'"</automated>
  </verify>
  <acceptance_criteria>
    - `runtime_coverage_registry.json::entries` contains all 14 new `python-tier1-<owner>` selectors (scangame, path, constants, message, database, resource, xse, settings, registry, yaml, web, version, perf, update).
    - `runtime_coverage_registry.json::entries` contains `python-tier1-scanlog-wave10-residuals` with `testSuite` pointing to `test_promoted_residuals_smoke.py` (L15 R8 precedent — separate selector, NOT a mutation of `python-tier1-scanlog`).
    - `runtime_coverage_registry.json::entries` does NOT contain `python-tier2-scanlog-runtime` (M12 retirement).
    - `python-tier1-shared` and `python-tier1-file_io` entries are UNCHANGED: `contractCount=61` and `contractCount=95` respectively; `contractIdsHash` length remains 64 (Plan 08 integrity check).
    - Every new selector entry has `contractIdsHash` that is exactly 64 characters lowercase hex (C2 fix — full SHA-256, NOT 16-char truncation).
    - NO entry has a placeholder `contractIdsHash` like `"<computed>"` or `"<recomputed>"`.
    - Running `check_parity_gate.py --repo-root . --update-baseline` exits 0 (meaning `registry_mismatch_total == 0`).
    - `runtime_coverage_summary.json::summary.registry_mismatch_total == 0`.
    - Commit message follows convention: `Feat(03-09a): Add 14 python-tier1 residual selectors + python-tier1-scanlog-wave10-residuals; retire python-tier2-scanlog-runtime`.
  </acceptance_criteria>
  <done>All 15 new selectors added with correct 64-char hashes; stale tier2 entry retired; Plan 08 hashes preserved.</done>
</task>

<task type="auto">
  <name>Task 4: Refresh full baseline + 5-step plan-close verification chain + SUMMARY recording post-09a deferred_total for 09b cross-check</name>
  <files>
    docs/implementation/python_api_parity/baseline/parity_contract.json
    docs/implementation/python_api_parity/baseline/parity_contract.md
    docs/implementation/python_api_parity/baseline/parity_diff_report.json
    docs/implementation/python_api_parity/baseline/parity_diff_report.md
    docs/implementation/python_api_parity/baseline/rust_api_surface.json
    docs/implementation/python_api_parity/baseline/python_api_surface.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json
    docs/implementation/python_api_parity/baseline/runtime_coverage_summary.md
    docs/implementation/python_api_parity/baseline/tier1_gate_report.md
    ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.json
    ClassicLib-rs/python-bindings/parity-artifacts/parity_diff_report.md
    ClassicLib-rs/python-bindings/parity-artifacts/python_api_surface.json
    ClassicLib-rs/python-bindings/parity-artifacts/rust_api_surface.json
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.json
    ClassicLib-rs/python-bindings/parity-artifacts/runtime_coverage_summary.md
    ClassicLib-rs/python-bindings/parity-artifacts/tier1_gate_report.md
  </files>
  <read_first>
    - tools/python_api_parity/generate_baseline.py (verify the --write-baseline behavior)
    - tools/python_api_parity/check_parity_gate.py (verify the --update-baseline behavior)
    - All 14 owner stub files (touched in Task 1)
    - classic_scanlog.pyi (may have been touched in Task 1 for the 4 method residual stub entries)
  </read_first>
  <action>
    Step 1 — Refresh main baseline:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/generate_baseline.py --repo-root . --write-baseline"
    ```

    Step 2 — Refresh runtime coverage summary + parity-artifacts mirror:
    ```powershell
    pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline"
    ```

    Step 3 — Run the 5-step plan-close verification chain:
    ```powershell
    python tools/python_api_parity/check_parity_gate.py --repo-root .
    if ($LASTEXITCODE -ne 0) { Write-Error "check_parity_gate.py failed"; exit 1 }

    python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings
    if ($LASTEXITCODE -ne 0) { Write-Error "validate_stubs.py failed"; exit 1 }

    pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python
    if ($LASTEXITCODE -ne 0) { Write-Error "rebuild_rust.ps1 failed"; exit 1 }

    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests -q
    if ($LASTEXITCODE -ne 0) { Write-Error "pytest failed"; exit 1 }

    # mypy --strict on ONLY the 15 touched stubs (full 19-stub sweep is 09b's job)
    $touched_stubs = @(
        "ClassicLib-rs/python-bindings/classic-scanlog-py/classic_scanlog.pyi",
        "ClassicLib-rs/python-bindings/classic-scangame-py/classic_scangame.pyi",
        "ClassicLib-rs/python-bindings/classic-path-py/classic_path.pyi",
        "ClassicLib-rs/python-bindings/classic-constants-py/classic_constants.pyi",
        "ClassicLib-rs/python-bindings/classic-message-py/classic_message.pyi",
        "ClassicLib-rs/python-bindings/classic-database-py/classic_database.pyi",
        "ClassicLib-rs/python-bindings/classic-resource-py/classic_resource.pyi",
        "ClassicLib-rs/python-bindings/classic-xse-py/classic_xse.pyi",
        "ClassicLib-rs/python-bindings/classic-settings-py/classic_settings.pyi",
        "ClassicLib-rs/python-bindings/classic-registry-py/classic_registry.pyi",
        "ClassicLib-rs/python-bindings/classic-yaml-py/classic_yaml.pyi",
        "ClassicLib-rs/python-bindings/classic-web-py/classic_web.pyi",
        "ClassicLib-rs/python-bindings/classic-version-py/classic_version.pyi",
        "ClassicLib-rs/python-bindings/classic-perf-py/classic_perf.pyi",
        "ClassicLib-rs/python-bindings/classic-update-py/classic_update.pyi"
    )
    uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe mypy --strict @touched_stubs
    if ($LASTEXITCODE -ne 0) { Write-Error "mypy --strict failed on touched stubs"; exit 1 }

    Write-Host "Plan 09a 5-step verification chain: ALL GREEN"
    ```

    Step 4 — Record post-09a state for Plan 09b cross-check (L14 fix):
    ```powershell
    $summary = Get-Content 'docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json' -Raw | ConvertFrom-Json
    Write-Host "POST-09a METRICS:"
    Write-Host "  tier1_contract_total: $($summary.summary.tier1_contract_total)"
    Write-Host "  deferred_total: $($summary.summary.deferred_total)  (09b will drive this to 0 by emptying deferred_runtime_backlog.json)"
    Write-Host "  newly_uncovered_total: $($summary.summary.newly_uncovered_total)  (must be 0)"
    Write-Host "  tier1_missing_runtime_total: $($summary.summary.tier1_missing_runtime_total)  (must be 0)"
    Write-Host "  registry_mismatch_total: $($summary.summary.registry_mismatch_total)  (must be 0)"
    if ($summary.summary.newly_uncovered_total -ne 0) { Write-Error "newly_uncovered_total != 0"; exit 1 }
    if ($summary.summary.tier1_missing_runtime_total -ne 0) { Write-Error "tier1_missing_runtime_total != 0"; exit 1 }
    if ($summary.summary.registry_mismatch_total -ne 0) { Write-Error "registry_mismatch_total != 0"; exit 1 }
    ```

    NOTE: Post-09a `deferred_total` is expected to be ~1008 (per Task 0 dry-run projection). It is NOT expected to be 0 — Plan 09b Task 3 empties the deferred registry to reach 0. Plan 09b must be able to read this exact post-09a value from the committed SUMMARY.md.

    Step 5 — Atomic commit for the baseline refresh:
    ```powershell
    git add docs/implementation/python_api_parity/baseline/ ClassicLib-rs/python-bindings/parity-artifacts/
    git commit -m "Feat(03-09a): Refresh parity baseline post-residual promotion (505 -> {tier1_contract_total} tier1Mappings)"
    ```

    Step 6 — Generate the SUMMARY.md per Phase 3 cadence; see <output>.
  </action>
  <verify>
    <automated>pwsh -ExecutionPolicy Bypass -Command "uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python tools/python_api_parity/check_parity_gate.py --repo-root .; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings; if ($LASTEXITCODE -ne 0) { exit 1 }; uv run --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe python -m pytest ClassicLib-rs/python-bindings/tests/test_promoted_residuals_smoke.py -q; if ($LASTEXITCODE -ne 0) { exit 1 }; $s = Get-Content docs/implementation/python_api_parity/baseline/runtime_coverage_summary.json -Raw | ConvertFrom-Json; Write-Host \"tier1_contract_total=$($s.summary.tier1_contract_total); deferred_total=$($s.summary.deferred_total); newly_uncovered_total=$($s.summary.newly_uncovered_total)\"; if ($s.summary.newly_uncovered_total -ne 0) { exit 1 }; if ($s.summary.tier1_missing_runtime_total -ne 0) { exit 1 }; if ($s.summary.registry_mismatch_total -ne 0) { exit 1 }; Write-Host 'Plan 09a GREEN'"</automated>
  </verify>
  <acceptance_criteria>
    - `parity_contract.json::tier1Mappings.length` is at least 1100 (L14: exact number recorded in SUMMARY.md).
    - `check_parity_gate.py --repo-root .` exits 0.
    - `validate_stubs.py --fail-on-warnings` exits 0.
    - `rebuild_rust.ps1 -Target python` exits 0 (all 19 wheels build cleanly).
    - `pytest ClassicLib-rs/python-bindings/tests -q` exits 0.
    - `mypy --strict` exits 0 on the 15 touched stubs (foundation/classic_shared.pyi sweep is deferred to Plan 09b Task 4 Step 1).
    - `runtime_coverage_summary.json::summary.newly_uncovered_total == 0`.
    - `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0`.
    - `runtime_coverage_summary.json::summary.registry_mismatch_total == 0` (C2 fix empirical verification — 64-char hashes match).
    - `runtime_coverage_summary.json::summary.deferred_total` is recorded (expected ~1008, NOT 0; Plan 09b owns the final empty-the-backlog step).
    - Both `docs/implementation/python_api_parity/baseline/` and `ClassicLib-rs/python-bindings/parity-artifacts/` refreshed.
    - Commit message follows convention: `Feat(03-09a): Refresh parity baseline post-residual promotion (505 -> N tier1Mappings)`.
  </acceptance_criteria>
  <done>Plan 09a closed: residuals promoted, baseline refreshed, 5-step chain green; post-09a deferred_total captured in SUMMARY for Plan 09b cross-check.</done>
</task>

</tasks>

<verification>
Plan 09a 5-step verification chain (Plan 09b owns the full 19-stub mypy sweep + PYT-06 deferred_total==0 final gate):

1. `python tools/python_api_parity/check_parity_gate.py --repo-root .` — exits 0 with 0 Tier-1 drift across all enrolled owners
2. `python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --fail-on-warnings` — exits 0
3. `pwsh -ExecutionPolicy Bypass -File rebuild_rust.ps1 -Target python` — exits 0 (all 19 wheels rebuild cleanly)
4. `uv run ... pytest ClassicLib-rs/python-bindings/tests -q` — exits 0 (existing 238 + new 80-130 residual smoke tests all pass)
5. `mypy --strict` over the 15 touched stubs — exits 0

Post-conditions verified by gate metrics:
- `runtime_coverage_summary.json::summary.tier1_missing_runtime_total == 0`
- `runtime_coverage_summary.json::summary.registry_mismatch_total == 0` (C2 fix: 64-char hashes)
- `runtime_coverage_summary.json::summary.newly_uncovered_total == 0`
- `parity_contract.json::tier1Mappings` contains EXACTLY 95 file_io rows AND 61 shared rows (Plan 08 ownership preserved)
- `parity_contract.json::tier1Mappings` contains ZERO rows with `rustSymbol == 'GLOBAL_FCX_HANDLER'` (R9 preserved)
- Post-09a `deferred_total` value recorded in SUMMARY.md for Plan 09b cross-check (expected ~1008)
</verification>

<success_criteria>
- Fresh residual inventory from live post-refresh `parity_diff_report.json::gaps`
- file_io and shared explicitly excluded; Plan 08 post-state (file_io=95, shared=61) preserved
- R9 GLOBAL_FCX_HANDLER exclusion preserved in EXCLUDED_RUST_SYMBOLS
- THREE-BRANCH wrapper check (C1 fix) empirically verified against at least one residual per branch
- contractIdsHash computed via IMPORTED `_stable_id_hash` (C2 fix) — NOT reimplemented; hash length == 64
- Dedicated 03-09a-CONSTRUCTOR-INVENTORY.md artifact (H5 fix)
- Dedicated 03-09a-DRY-RUN-PROJECTION.md artifact (H6 fix) documenting the C3 investigation outcome
- python-tier2-scanlog-runtime retired (M12)
- L15 R8 precedent: separate python-tier1-scanlog-wave10-residuals selector (not a mutation of existing scanlog selector)
- 5-step verification chain exits 0
- SUMMARY.md records post-09a deferred_total so Plan 09b has the exact starting number for the final gate (L14)
</success_criteria>

<output>
Create `.planning/phases/03-python-tier-collapse/03-09a-a10-residual-promotion-SUMMARY.md` containing:

- **Final `tier1Mappings.length`** — exact post-Task-1 number (L14 fix)
- **Per-owner row count breakdown** — 14 owners + 4 scanlog method residuals
- **Same-row dedup savings** — how many @rust proxies were skipped because their rustSymbol matched a Python class row
- **Wrapper-less BLOCKERS** — NONE expected, but if present, document resolution
- **Rule 2 stub holes fixed inline** — which .pyi files got new entries
- **Test count in test_promoted_residuals_smoke.py** — hand-verified final number
- **5-step verification chain** results table (check_parity_gate, validate_stubs, rebuild_rust, pytest, mypy --strict on 15 stubs)
- **14 new selectors added** with their contractCount and full 64-char contractIdsHash values
- **python-tier2-scanlog-runtime retirement confirmation** (M12)
- **python-tier1-scanlog-wave10-residuals selector added** (L15 R8 precedent)
- **Plan 08 integrity check**: file_io=95, shared=61, both selector hashes unchanged
- **POST-09a deferred_total** — exact number from runtime_coverage_summary.json (expected ~1008). This is the starting number Plan 09b must drive to 0 in Task 3 (empty deferred_runtime_backlog.json::entries).
- **Notes for Plan 09b**: re-verify line numbers in `generate_baseline.py` before editing (Task 2 re-grep step); carry 03-09a-DRY-RUN-PROJECTION.md forward for the final endgame comparison.
</output>
