# Phase 5: CI Enforcement - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all three parity gates (CXX, Python, Node) into CI so every PR is blocked on parity failure. Add the CXX parity gate as a new lightweight job in `ci-cpp.yml` that gates the heavy MSVC build jobs. Prove the triple-gate invariant with a local test script that injects a canary function into `classic-shared-core` and asserts all three gates detect it. Verify that all three parity gate jobs are listed as required status checks in branch protection. The CXX baseline freshness check (CI-06) is satisfied by the existing `check_parity_gate.py` stale-artifact detection (Phase 1 D-14) without committing generated CXX headers.

**In scope:**
- `.github/workflows/ci-cpp.yml` — add `cxx-parity-gate` job before `cli-tests` / `gui-tests`
- `tools/test_triple_gate_failure.py` — local assertion script proving triple-gate failure on canary function injection (CI-05)
- Branch protection verification for all three parity gate jobs (Python, Node, CXX) as required status checks
- Verification that Python and Node gates remain green in CI after Phase 3 and Phase 4 changes (CI-01, CI-02)

**Out of scope:**
- Modifications to `ci-python-bindings.yml` or `ci-typescript.yml` (already working and green)
- Modifications to `ci-rust.yml`
- Any parity gate script changes (gates are complete from Phases 1, 3, 4)
- Committing CXX-generated headers (`include/classic_cxx_bridge/*.h`) — these are build artifacts, not contract files
- Documentation reset (Phase 6)
- Error-contract documentation (Phase 6, HARM-05)
- Tier-2 governance file deletion (Phase 6)

</domain>

<decisions>
## Implementation Decisions

### CXX Gate Job Placement (CI-03)

- **D-01:** The CXX parity gate runs as a new `cxx-parity-gate` job in `.github/workflows/ci-cpp.yml`. It runs BEFORE `cli-tests` and `gui-tests` — both existing jobs gain `needs: [cxx-parity-gate]` so parity drift blocks the expensive MSVC builds. This mirrors how Python and Node gates are the gatekeeper jobs in their respective workflow files.
- **D-02:** The job is lightweight: only requires `actions/checkout@v6` + `actions/setup-python@v6` (Python 3.12) + one `run:` step. No Rust toolchain, no MSVC, no vcpkg. Target timeout: 10 minutes.
- **D-03:** The job runs only `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` — CXX-only, no Python stub validation (that stays in `ci-python-bindings.yml`).
- **D-04:** No modifications to `ci-python-bindings.yml`, `ci-typescript.yml`, or `ci-rust.yml`. Those workflows are already working and green after Phases 3 and 4.

### CXX Artifact Freshness (CI-06)

- **D-05:** CI-06 is satisfied by the existing `check_parity_gate.py` stale-artifact detection (Phase 1 D-14). The script already re-scans all bridge source files, compares against the committed baseline JSON, and exits non-zero if the baseline is stale. No separate freshness step or script needed.
- **D-06:** CXX-generated headers (`include/classic_cxx_bridge/*.h`) are NOT committed and do NOT get a freshness gate. They are build artifacts in `target/` that `cxx_build` generates deterministically from the same source the gate parses. Committing them would create merge conflicts without adding contract value beyond what the baseline JSON already provides.
- **D-07:** The single CI step (`check_parity_gate.py --repo-root .`) covers both CI-03 (drift detection) and CI-06 (freshness) in one invocation.

### Triple-Gate Assertion Test (CI-05)

- **D-08:** A checked-in Python script at `tools/test_triple_gate_failure.py` proves the triple-gate invariant. The script: (1) temporarily injects a `pub fn _ci05_canary() {}` into `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs`, (2) runs all three gate scripts locally, (3) asserts all three exit non-zero, (4) reverts the injection. Outputs a PASS/FAIL summary.
- **D-09:** The canary function is injected into `classic-shared-core` because it is the foundation crate tracked by all three gates — a `pub fn` added here is visible to the CXX gate (via `classic-cpp-bridge`), Python gate (via `classic-shared-py`), and Node gate (via `classic-node`).
- **D-10:** The script is local-only — no CI workflow dispatch job. The three individual gate jobs already enforce the invariant on every PR; this script just proves they work together. Run once during Phase 5 verification and on-demand by maintainers. Passing output is committed as evidence.

### Branch Protection (CI-04)

- **D-11:** Branch protection is configured manually via GitHub Settings > Branches > main > Edit. The PR description includes exact step-by-step instructions. No `gh api` automation or PAT-based scripting.
- **D-12:** All three parity gate jobs are verified as required status checks in branch protection: "Python Parity Gates" (`ci-python-bindings.yml`), "Node Parity Gates" (`ci-typescript.yml`), and "CXX Parity Gate" (`ci-cpp.yml`). If Python or Node are missing from branch protection, they are added alongside CXX.
- **D-13:** The CXX gate check is added to branch protection AFTER the first successful CI run (when the PR that adds the job runs CI for the first time). GitHub requires a status check to have completed at least once before it can be registered as required. The merge of the CI job PR and the branch protection update happen as one deployment action — no window where the gate exists but does not block.

### CI-01 / CI-02 Verification

- **D-14:** Phase 5 verifies that the Python parity gate (`ci-python-bindings.yml::parity-gates`) and Node parity gate (`ci-typescript.yml::parity-gates`) remain green in CI after Phase 3 (Python Tier Collapse) and Phase 4 (Node Tier Collapse) changes. Verification is observational: confirm the jobs pass on a recent CI run, no code changes needed.

### Claude's Discretion

- The exact wording of the PR description's branch protection checklist
- Whether to add a diagnostic upload step (artifact) to the CXX gate job on failure (mirrors the pattern in Python/Node gate jobs)
- The exact structure and CLI flags of `test_triple_gate_failure.py` (e.g., `--repo-root`, `--verbose`, output format)
- Whether the triple-gate test script saves its output to a file or just prints to stdout

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/REQUIREMENTS.md` SS"CI Enforcement (CI)" -- CI-01..CI-06 are this phase's complete requirement set
- `.planning/ROADMAP.md` SS"Phase 5: CI Enforcement" -- phase goal + 5 success criteria
- `.planning/phases/01-cxx-parity-gate-tooling/01-CONTEXT.md` -- Phase 1 decisions D-14 (stale artifact detection), D-16 (local invocation convention)

### Existing CI Workflows (must-read before editing)
- `.github/workflows/ci-cpp.yml` -- the file being modified; currently has `cli-tests` and `gui-tests` jobs; new `cxx-parity-gate` job goes here
- `.github/workflows/ci-python-bindings.yml` -- Python gate job structure to mirror (parity-gates -> build-and-test dependency pattern)
- `.github/workflows/ci-typescript.yml` -- Node gate job structure; NOT modified in Phase 5
- `.github/workflows/ci-rust.yml` -- Rust lint/build/test; NOT modified in Phase 5

### Gate Scripts (invoked by CI, not modified)
- `tools/cxx_api_parity/check_parity_gate.py` -- the CXX gate script the new CI job runs; already handles drift + stale artifact detection
- `tools/python_api_parity/check_parity_gate.py` -- Python gate; invoked by triple-gate test script
- `tools/node_api_parity/check_parity_gate.py` -- Node gate; invoked by triple-gate test script

### Canary Injection Target
- `ClassicLib-rs/foundation/classic-shared-core/src/lib.rs` -- the file the triple-gate test script temporarily modifies to inject `_ci05_canary()`

### Existing Node Freshness Pattern (reference for CI-06 design rationale)
- `tools/node_api_parity/check_dts_freshness.py` -- the Node index.d.ts freshness gate; CXX uses baseline JSON freshness instead of committed header freshness

### Architectural rules
- `AGENTS.md` SS"Always-On Repository Rules" -- single Tokio runtime, never write to nul, never raw ctest
- `CLAUDE.md` SS"Build Commands" -- not needed for this phase (no Rust/C++ builds), listed for cross-reference

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ci-python-bindings.yml::parity-gates` job** -- working example of a source-only parity gate CI job (Python + checkout only, ~30min timeout). The CXX gate job follows this structure but is even simpler (no stub validation step).
- **`ci-typescript.yml::parity-gates` job** -- working example of a gate-before-build pattern. The CXX gate mirrors this by adding `needs: [cxx-parity-gate]` to the MSVC build jobs.
- **`check_parity_gate.py` (all three gates)** -- all three scripts share the same CLI convention (`--repo-root .`) and exit-code semantics (0 = pass, 1 = drift). The triple-gate test script can invoke them uniformly.

### Established Patterns
- **Gate-before-build dependency:** Both Python and Node workflows use `needs:` to block expensive build jobs on parity gate success. The CXX gate follows this by making `cli-tests` and `gui-tests` depend on `cxx-parity-gate`.
- **Artifact upload on failure:** Both existing gate jobs upload diagnostic artifacts on failure. The CXX gate may optionally follow this pattern for `parity-artifacts/`.
- **Windows-latest runners:** All CI jobs run on `windows-latest`. The CXX gate continues this even though it's pure Python (keeps the runner consistent with the rest of ci-cpp.yml).

### Integration Points
- **`ci-cpp.yml` job dependency graph:** Currently `cli-tests` and `gui-tests` are independent. After Phase 5, both depend on `cxx-parity-gate`. The gate adds ~5-10 minutes to the critical path but saves 90-120 minutes of MSVC build time when parity is broken.
- **Branch protection settings:** GitHub Settings > Branches > main. Currently may or may not list Python/Node gate jobs. Phase 5 ensures all three are listed.
- **`tools/test_triple_gate_failure.py`** -- new file; invokes all three existing gate scripts without modification.

</code_context>

<specifics>
## Specific Ideas

- The CXX gate job is intentionally lightweight (~5-10min) compared to the existing MSVC build jobs (~90-120min). It acts as a fast fail-first check that saves expensive build minutes when the bridge contract is broken.
- The triple-gate test script (`test_triple_gate_failure.py`) must cleanly revert the canary injection even if a gate script crashes — use a `try/finally` block or `atexit` handler to guarantee `lib.rs` is restored.
- The "same PR" requirement (CI-04) is satisfied by the timing: merge the CI job PR, then immediately configure branch protection. There is no practical window where the gate exists but does not block, because the protection is applied as part of the same deployment action.
- All three gate scripts share exit-code 0/1 semantics, so the triple-gate test can use `subprocess.run(...).returncode != 0` uniformly.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 05-ci-enforcement*
*Context gathered: 2026-04-09*
