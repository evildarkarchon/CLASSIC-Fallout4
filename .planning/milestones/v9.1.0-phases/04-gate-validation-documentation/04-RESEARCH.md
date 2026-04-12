# Phase 4: Gate Validation & Documentation - Research

**Researched:** 2026-04-11
**Domain:** Milestone closure validation, parity-gate refresh workflow, and active-doc topology audit
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
## Implementation Decisions

### Gate refresh policy
- **D-01:** Start Phase 4 with plain parity verification. Refresh baselines only when drift is intentional and source-backed, then rerun the plain gates to prove zero drift.
- **D-02:** Treat the Node refresh flow as an explicit two-step sequence: `bun run parity:gate:update-baseline` only when needed, followed by `bun run parity:gate`. Do not treat `parity:gate:local` as the canonical audit path for this phase.
- **D-03:** If a gate fails only because checked-in artifacts are stale while live source is correct, Phase 4 fixes that in-phase instead of deferring it.
- **D-04:** After any intentional refresh, rerun all three gates without refresh flags before calling the milestone closed.

### Closure evidence
- **D-05:** Produce a dedicated Phase 4 verification artifact rather than relying only on scattered gate outputs.
- **D-06:** Organize the proof as one milestone-closure checklist covering workspace Rust tests, all three parity gates, required docs updates, and the final doc audit.
- **D-07:** Final success requires all checks green plus explicit doc-audit evidence. Command exit codes alone are not sufficient closure proof.
- **D-08:** Add a targeted Phase 4 audit guard test only if execution uncovers a real closure gap that existing gates and doc sweeps do not already catch.

### Documentation closure
- **D-09:** Run a broad active-doc audit across live contributor docs, including `CLAUDE.md`, `docs/api/`, `.planning/PROJECT.md`, and `.planning/codebase/*.md`, while continuing to skip archived milestone/history snapshots.
- **D-10:** Keep brief phase-history notes in surviving docs where they help contributors find moved or absorbed surfaces, but do not turn active docs into detailed migration narratives.
- **D-11:** `CLAUDE.md` should state the current 16-crate topology explicitly and retain only a short Phase 1-3 history summary.
- **D-12:** Retired crate names may remain only when clearly marked as historical or migration context; otherwise active docs should use present-day owners and names.

### Execution order
- **D-13:** Sequence Phase 4 for fast failure: run cheap doc/parity audits first, then heavier workspace/native validation after cheap closure issues are resolved.
- **D-14:** Run the source-only parity gates before C++ native validation so stale baselines or doc drift fail before bridge, CLI, and GUI build time is paid.
- **D-15:** Run `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` after cheap cleanup, then finish with the full end-to-end milestone suite if the early audits are green.

### Carried-forward constraints
- **D-16:** Active docs only. Do not edit archived milestone plans, historical docs, or snapshot artifacts just to match the new topology.
- **D-17:** Retired API docs stay consolidated into surviving `docs/api/` pages. Phase 4 validates and polishes that end state rather than recreating retired pages.
- **D-18:** One-tier parity remains the acceptance bar: final state must be zero drift across C++, Python, and Node.

### the agent's Discretion
- Whether a new targeted audit guard test is needed at all. Add one only if existing checks leave a real closure gap.
- Exact wording and layout of the verification checklist artifact.
- Exact composition of the final full-suite command, as long as it preserves the chosen fast-fail order and ends with plain gate reruns plus full-suite proof.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within Phase 4 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | `cargo test --workspace` passes with no failures after all merges | Fast-fail sequence, workspace manifest path, and full-suite validation order are defined below. |
| GATE-02 | CXX parity gate baseline regenerated and exits 0 | Use source-only CXX gate first; refresh only with `--update-baseline`; rerun plain gate after refresh. |
| GATE-03 | Python parity gate exits 0 with `deferred_total == 0` | Current Python gate is one-tier; operational closure is plain gate exit 0 with zero coverage gaps/stale artifacts after any needed rebuild and refresh. |
| GATE-04 | Node parity gate exits 0 | Use explicit `parity:gate:update-baseline` only when drift is intentional, then plain `parity:gate`; do not use `parity:gate:local` as milestone evidence. |
| GATE-05 | API docs under `docs/api/` updated for merged crates | Audit only active docs, keep absorbed-crate history brief, and verify no active docs recreate retired pages. |
| GATE-06 | `CLAUDE.md` technology stack section updated to reflect 16 business-logic crates | Audit `CLAUDE.md`, `.planning/PROJECT.md`, and `.planning/codebase/*.md` together so crate counts and topology language stay aligned. |
</phase_requirements>

## Summary

Phase 4 is not a feature-build phase; it is a closure phase. The established pattern in this repo is to treat parity and documentation as tracked contract artifacts, not as ad hoc checks. The strongest implementation shape is: cheap source-only audits first, selective artifact refresh only when drift is intentional, plain gate reruns to prove zero drift, then the expensive native/workspace suite, and finally a single milestone-closure checklist artifact that records the green state.

The stack is already standardized inside the repo: `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` for Rust, Python parity via `tools/python_api_parity/check_parity_gate.py`, Node parity via `tools/node_api_parity/check_parity_gate.py` exposed through Bun scripts, CXX parity via `tools/cxx_api_parity/check_parity_gate.py`, and C++ validation only through the PowerShell wrapper scripts. The main planning risk is not missing tooling; it is using the wrong workflow shape and accidentally masking stale artifacts, editing archived docs, or paying for heavy native validation before cheap source-only drift checks fail.

One subtle but important current-state finding: Phase 4 requirement language still says `deferred_total == 0`, but the active Python and Node gate scripts are already one-tier and no longer emit deferred-tier fields in live tooling. For planning, treat the requirement operationally as: plain gate exits 0, no runtime-coverage gaps, no registry mismatches, and no stale checked-in artifacts.

**Primary recommendation:** Plan Phase 4 as a fast-fail closure pipeline: doc audit + plain parity gates first, refresh only intentional drift, rerun plain gates, then workspace/native validation, and capture all results in one dedicated verification checklist artifact.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust; non-interface layers stay thin wrappers.
- Maintain a single shared Tokio runtime from Rust core facilities; do not introduce independent runtimes.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; update affected `docs/api/` pages in the same change if contracts change.
- Never run C++ tests by invoking test binaries or raw `ctest` directly; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test`.
- Native C++ targets are Windows-focused and MSVC-based.
- From Git Bash, source `tools/use_msvc_from_git_bash.sh` before Rust or MSVC-targeted C++ commands.
- Python and Node bindings must stay in sync with Rust core logic.

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo workspace | Rust 1.94.0 toolchain locally; manifest at `ClassicLib-rs/Cargo.toml` | Canonical Rust build/test entrypoint | Repo docs and validation files consistently use `--manifest-path ClassicLib-rs/Cargo.toml`. |
| Python parity gate | repo script (`tools/python_api_parity/check_parity_gate.py`) on Python 3.12+ | Source+artifact parity validation for Python bindings | It detects drift, missing runtime metadata, registry mismatches, newly uncovered surfaces, and stale checked-in artifacts. |
| Node parity gate | repo script via `bun run parity:gate` / `bun run parity:gate:update-baseline` | Source+artifact parity validation for Node bindings | Package scripts are the canonical interface; Phase 4 explicitly locks the two-step refresh flow. |
| CXX parity gate | repo script (`tools/cxx_api_parity/check_parity_gate.py`) | Source-only bridge contract validation | It runs without Cargo/MSVC and is intentionally the cheapest native-surface gate. |
| PowerShell build wrappers | `classic-cli/build_cli.ps1`, `classic-gui/build_gui.ps1` | Canonical native validation path | AGENTS.md forbids raw `ctest`; wrappers are repo policy. |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bun | 1.3.10 local; package scripts in `classic-node/package.json` | Node parity/test orchestration and `index.d.ts` freshness flow | Use for Node gate and runtime tests only after cheap source audits are ready. |
| Node.js | v25.9.0 local | Runs `test:node` runtime suite | Use after Bun parity/build steps succeed. |
| uv + bindings venv | uv 0.11.6; `.venv` exists | Python env/bootstrap for parity and pytest | Use bindings-local venv only; do not assume a repo-root venv. |
| PyO3 | 0.27.2 workspace dep | Python binding contract source of truth | Relevant when parity failure traces back to wrapper/stub ownership. |
| NAPI-RS | 3.x (`@napi-rs/cli` ^3.0.0) | Node binding generation and `index.d.ts` refresh | Relevant when Node gate failure traces back to stale generated contract. |
| CXX | 1.0 | C++ bridge contract surface | Relevant for CXX baseline regeneration and bridge/native validation ordering. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain gate → selective refresh → plain rerun | Always use refresh helpers first | Faster locally, but it masks whether drift was intentional and weakens closure evidence. |
| Repo wrapper scripts for C++ | Raw `ctest` / direct test binaries | Forbidden by AGENTS.md and bypasses repo-specific setup. |
| One milestone closure artifact | Scattered command logs only | Easier short-term, but fails D-05/D-07 and makes final audit ambiguous. |

**Version verification:**
- Local toolchain probe: `cargo 1.94.0`, `python 3.14.3`, `uv 0.11.6`, `bun 1.3.10`, `node v25.9.0`, `pwsh 7.6.0`
- Workspace/package sources: `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`

## Architecture Patterns

### Recommended Project Structure
```text
.planning/phases/04-gate-validation-documentation/
├── 04-RESEARCH.md               # This document
├── 04-PLAN*.md                  # Execution plans
├── 04-VALIDATION.md             # Per-phase validation contract
└── 04-VERIFICATION.md           # Single milestone-closure checklist artifact

tests/planning/
└── test_phase04_validation.py   # Add only if a real closure gap is found
```

### Pattern 1: Fast-Fail Closure Sequence
**What:** Run active-doc audit and source-only parity gates before expensive native validation.
**When to use:** Always for this phase.
**Example:**
```powershell
# Source: 04-CONTEXT.md D-13..D-15, docs/api/binding-parity-policy.md
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root .
pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"

cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

### Pattern 2: Verify First, Refresh Only on Intentional Drift
**What:** Use plain gate runs to detect drift, refresh tracked artifacts only when the source-backed change is intentional, then rerun the plain gate.
**When to use:** For CXX, Python, and Node baselines in this phase.
**Example:**
```powershell
# Source: binding-parity-policy.md, cxx-parity-gate.md, 04-CONTEXT.md D-01..D-04
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root .
pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"

# Only if drift is intentional:
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline
pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate:update-baseline; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run parity:gate"
```

### Pattern 3: Active-Docs-Only Audit
**What:** Audit `CLAUDE.md`, `docs/api/`, `.planning/PROJECT.md`, and `.planning/codebase/*.md`, but skip archived milestone history.
**When to use:** All documentation closure tasks.
**Example:**
```text
Audit targets:
- CLAUDE.md
- docs/api/README.md and surviving crate pages
- docs/api/binding-parity-overview.md
- .planning/PROJECT.md
- .planning/codebase/ARCHITECTURE.md
- .planning/codebase/STRUCTURE.md
- .planning/codebase/STACK.md
```

### Pattern 4: Single Closure Artifact
**What:** Store final milestone proof in one checklist-style verification file.
**When to use:** End of phase, after all plain reruns are green.
**Example:**
```markdown
- [x] Docs audit complete
- [x] CXX plain gate exits 0
- [x] Python plain gate exits 0
- [x] Node plain gate exits 0
- [x] cargo test --workspace exits 0
- [x] classic-cli/build_cli.ps1 -Test exits 0
- [x] classic-gui/build_gui.ps1 -Test exits 0
```

### Anti-Patterns to Avoid
- **Using `parity:gate:local` as final Node milestone evidence:** convenient, but Phase 4 explicitly rejects it as the canonical audit path.
- **Refreshing baselines before a plain verification run:** hides whether drift was intentional.
- **Running native wrappers before source-only parity gates:** wastes time and obscures root cause.
- **Editing archived docs to make search results look clean:** violates D-16.
- **Treating crate-count edits as isolated:** `CLAUDE.md`, `.planning/PROJECT.md`, and `.planning/codebase/*.md` must stay aligned together.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CXX API drift detection | Manual bridge-file diff or ad hoc grep sweep | `tools/cxx_api_parity/check_parity_gate.py` | It already tracks baseline freshness and semantic contract comparison. |
| Python parity validation | Manual `.pyi`/wrapper/core comparison | `tools/python_api_parity/check_parity_gate.py` + `ClassicLib-rs/validate_stubs.py` when needed | The gate already catches missing Rust/Python rows, runtime metadata gaps, and stale checked-in artifacts. |
| Node parity validation | Manual `index.d.ts` diffing | `bun run parity:gate` and `bun run parity:gate:update-baseline` | The script already validates exports, runtime coverage registry, and tracked artifact freshness. |
| Native C++ verification | Raw `ctest` or direct test binaries | `classic-cli/build_cli.ps1 -Test` / `classic-gui/build_gui.ps1 -Test` | Repo policy; wrappers own environment setup and supported subsets. |
| Final closure evidence | Copy-pasted shell output spread across summaries | One dedicated `04-VERIFICATION.md` checklist | This phase requires explicit audit evidence, not just exit codes. |

**Key insight:** The repo already treats parity reports, `index.d.ts`, runtime coverage summaries, and docs pages as contract artifacts. Custom spot checks are worse than the existing tooling because they usually miss stale committed artifacts.

## Common Pitfalls

### Pitfall 1: Using the Wrong Node Command
**What goes wrong:** The plan uses `bun run parity:gate:local` as the milestone audit step.
**Why it happens:** Older phase docs used it as the convenient local helper because it bundles `dts:freshness:local` and baseline refresh.
**How to avoid:** For Phase 4, use plain `bun run parity:gate` first; if drift is intentional, run `bun run parity:gate:update-baseline`, then rerun plain `bun run parity:gate`.
**Warning signs:** Evidence cannot show whether zero drift existed before refresh.

### Pitfall 2: Treating Python/Node `deferred_total` Literally
**What goes wrong:** The executor waits for a field that active gate scripts no longer emit.
**Why it happens:** Requirement wording and older milestone history still reference deferred-tier metrics.
**How to avoid:** Use current gate semantics: exit 0, zero coverage gaps, zero registry mismatch, zero newly uncovered surfaces, and no stale tracked artifacts.
**Warning signs:** Greps in active `tools/python_api_parity/`, `tools/node_api_parity/`, and `tools/binding_parity_runtime_coverage.py` do not show live deferred-tier logic.

### Pitfall 3: Skipping the Python Rebuild Path When Runtime Surface Changed
**What goes wrong:** Python parity fails against an installed stale extension even though source imports are correct.
**Why it happens:** The Python gate validates runtime-facing artifacts, not just source files.
**How to avoid:** Use the bindings-local `.venv` and rebuild Python bindings before concluding the gate failure is structural.
**Warning signs:** Import-path failures or stale module symbols after merge work already landed.

### Pitfall 4: Paying for Native Validation Too Early
**What goes wrong:** C++ wrapper runs fail after long build/setup time, but the true root cause was already detectable in source-only parity or docs.
**Why it happens:** Validation order is inverted.
**How to avoid:** Keep D-13..D-15 order: docs/parity first, workspace test second, native wrappers last.
**Warning signs:** First failing signal appears only after CLI/GUI build time.

### Pitfall 5: Over-Cleaning History Out of Docs
**What goes wrong:** Useful “absorbed from X” breadcrumbs get deleted, or retired pages are recreated.
**Why it happens:** The executor treats all historical references as bad.
**How to avoid:** Keep brief ownership notes in surviving pages; remove only active-name drift and retired standalone pages.
**Warning signs:** Docs lose migration context or reintroduce deleted crate pages.

### Pitfall 6: Missing Cross-Doc Topology Drift
**What goes wrong:** `CLAUDE.md` says 16 crates, but `.planning/codebase/ARCHITECTURE.md` or `STRUCTURE.md` still reflect intermediate topology.
**Why it happens:** Files are edited one at a time instead of as one audit set.
**How to avoid:** Audit the active-doc set together and verify crate-count language in one pass.
**Warning signs:** Different active docs disagree on crate count, Python binding count, or absorbed-crate ownership notes.

## Code Examples

Verified patterns from repo sources:

### Phase 4 Plain-Then-Refresh Gate Flow
```powershell
# Source: 04-CONTEXT.md D-01..D-04, binding-parity-policy.md, cxx-parity-gate.md
python tools/cxx_api_parity/check_parity_gate.py --repo-root .
python tools/python_api_parity/check_parity_gate.py --repo-root .
pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"

# If and only if the drift is intentional and source-backed:
python tools/cxx_api_parity/check_parity_gate.py --repo-root . --update-baseline
python tools/python_api_parity/check_parity_gate.py --repo-root . --update-baseline
pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate:update-baseline; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; bun run parity:gate"
```

### Canonical Rust and Native Validation Tail
```powershell
# Source: AGENTS.md, repo-guide.md, 03-VALIDATION.md
cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml
pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test
pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test
```

### Python Binding Validation Stack
```powershell
# Source: repo-guide.md, binding-contract-refresh-note.md
uv venv ClassicLib-rs/python-bindings/.venv
uv pip install --python ClassicLib-rs/python-bindings/.venv/Scripts/python.exe -r ClassicLib-rs/python-bindings/requirements-ci.txt
python tools/python_api_parity/check_parity_gate.py --repo-root .
python ClassicLib-rs/validate_stubs.py --rust-dir ClassicLib-rs --parity-contract docs/implementation/python_api_parity/baseline/parity_contract.json --json-out ClassicLib-rs/python-bindings/parity-artifacts/stub_validation_report.json --fail-on-warnings
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Node milestone verification through `parity:gate:local` | Phase 4 explicit verify-first flow: plain `parity:gate`, selective `parity:gate:update-baseline`, then plain rerun | Locked in 04-CONTEXT.md on 2026-04-11 | Better closure evidence; less chance of masked drift. |
| Tiered/deferred parity interpretation | One-tier enforced parity gates with no deferred-tier tooling in active Python/Node gate code | v9.1.0-bindings closure; reflected in active gate scripts today | Phase 4 should verify green gates, not wait for legacy tier fields. |
| Separate docs for retired crates | Surviving owner pages keep brief history notes | Phases 1-3 consolidation | Phase 4 should polish consolidated docs, not recreate retired pages. |

**Deprecated/outdated:**
- `bun run parity:gate:local` as the milestone-closure audit command for this phase — still useful locally, but not the canonical evidence path.
- Any plan that assumes a deferred-tier registry still exists in active Python/Node gate tooling.

## Open Questions

1. **Should Phase 4 add a new planning audit test at all?**
   - What we know: D-08 says only if a real closure gap appears.
   - What's unclear: Whether the existing gate suite plus doc sweep already covers every required closure check.
   - Recommendation: Start without a new test; add `tests/planning/test_phase04_validation.py` only after a concrete uncovered gap is observed.

2. **How should GATE-03’s `deferred_total == 0` wording be evidenced now that active scripts are one-tier?**
   - What we know: Active Python/Node gate scripts enforce zero drift and zero runtime-coverage issues, and active tooling no longer shows deferred-tier logic.
   - What's unclear: Whether the planner should record an explicit equivalence note in the verification artifact.
   - Recommendation: Yes — state in `04-VERIFICATION.md` that current green gate semantics are the operational successor to the old `deferred_total == 0` wording.

3. **Can GUI native validation run on this machine without additional Qt setup?**
   - What we know: MSVC tools and `VCPKG_ROOT` are present; `qtpaths6` was not found on PATH.
   - What's unclear: Whether the wrapper/CMake preset resolves Qt independently.
   - Recommendation: Treat GUI validation as available-but-at-risk; if wrapper detection fails, record it as an environment blocker rather than a code drift failure.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | GATE-01 workspace tests | ✓ | 1.94.0 | — |
| Python | All three parity tools / docs scripts | ✓ | 3.14.3 | — |
| uv | Python venv/bootstrap | ✓ | 0.11.6 | Use existing `.venv` if bootstrap not needed |
| Python bindings venv | Python parity + pytest | ✓ | 3.14.3 | Recreate with `uv venv` |
| Bun | Node parity + Bun tests | ✓ | 1.3.10 | None |
| Node.js | `test:node` runtime suite | ✓ | v25.9.0 | None |
| PowerShell | Native wrapper scripts | ✓ | 7.6.0 | None |
| MSVC build tools | CLI/GUI wrapper builds | ✓ | VS 18 Community detected | None |
| `VCPKG_ROOT` | C++ wrapper builds | ✓ | `C:\vcpkg` | None |
| Qt CLI probe (`qtpaths6`) | GUI validation confidence check | ✗ on PATH | — | Rely on wrapper/CMake preset if configured |

**Missing dependencies with no fallback:**
- None confirmed.

**Missing dependencies with fallback:**
- `qtpaths6` not on PATH. Fallback is to rely on the existing GUI wrapper/CMake preset discovery; if that fails, Phase 4 should record an environment blocker instead of treating it as code drift.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust `cargo test` + Python parity/stub validation + Bun/Node parity/runtime tests + CXX parity gate + repo PowerShell native wrappers |
| Config file | `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `ClassicLib-rs/python-bindings/requirements-ci.txt` |
| Quick run command | `python -m pytest tests/planning/test_phase04_validation.py -q` |
| Full suite command | `python tools/cxx_api_parity/check_parity_gate.py --repo-root . && python tools/python_api_parity/check_parity_gate.py --repo-root . && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate" && cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml && pwsh -ExecutionPolicy Bypass -File classic-cli/build_cli.ps1 -Test && pwsh -ExecutionPolicy Bypass -File classic-gui/build_gui.ps1 -Test && python -m pytest tests/planning/test_phase04_validation.py -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | Workspace Rust remains green across merged topology | integration | `cargo test --workspace --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| GATE-02 | CXX baseline and gate are green | integration | `python tools/cxx_api_parity/check_parity_gate.py --repo-root .` | ✅ |
| GATE-03 | Python parity is green under one-tier semantics | integration | `python tools/python_api_parity/check_parity_gate.py --repo-root .` | ✅ |
| GATE-04 | Node parity is green with explicit verify/refresh flow | integration | `pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ✅ |
| GATE-05 | Active docs reflect surviving crate owners only | audit | `python -m pytest tests/planning/test_phase04_validation.py -q` | ❌ Wave 0 |
| GATE-06 | `CLAUDE.md` and active topology docs agree on 16-crate workspace | audit | `python -m pytest tests/planning/test_phase04_validation.py -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Run the touched-surface command; for doc-audit tasks, run `python -m pytest tests/planning/test_phase04_validation.py -q` once it exists.
- **Per wave merge:** Run the full suite command.
- **Phase gate:** All plain parity gates green, workspace/native validation green, and verification artifact complete before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/planning/test_phase04_validation.py` — only create if execution reveals a real closure gap not already covered by gate outputs and doc sweeps

## Sources

### Primary (HIGH confidence)
- `J:\CLASSIC-Fallout4\.planning\phases\04-gate-validation-documentation\04-CONTEXT.md` - locked workflow, doc-audit scope, and execution order
- `J:\CLASSIC-Fallout4\AGENTS.md` - repo constraints and forbidden C++ test path
- `J:\CLASSIC-Fallout4\.agents\skills\classic-project-guide\references\repo-guide.md` - canonical repo commands and platform notes
- `J:\CLASSIC-Fallout4\docs\api\binding-parity-policy.md` - verify-then-refresh parity policy
- `J:\CLASSIC-Fallout4\docs\api\cxx-parity-gate.md` - CXX source-only gate behavior and refresh semantics
- `J:\CLASSIC-Fallout4\docs\api\binding-contract-refresh-note.md` - Node/Python contract refresh rules
- `J:\CLASSIC-Fallout4\ClassicLib-rs\node-bindings\classic-node\package.json` - canonical Node scripts
- `J:\CLASSIC-Fallout4\tools\cxx_api_parity\check_parity_gate.py` - current CXX gate implementation
- `J:\CLASSIC-Fallout4\tools\python_api_parity\check_parity_gate.py` - current Python gate implementation
- `J:\CLASSIC-Fallout4\tools\node_api_parity\check_parity_gate.py` - current Node gate implementation
- `J:\CLASSIC-Fallout4\docs\api\README.md`, `binding-parity-overview.md`, `CLAUDE.md`, `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/STACK.md` - active topology/doc state to audit

### Secondary (MEDIUM confidence)
- Local environment probes for tool/runtime availability (`cargo`, `python`, `uv`, `bun`, `node`, `pwsh`, MSVC, `VCPKG_ROOT`, `qtpaths6`)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - source-backed by repo scripts, manifests, and local environment probes
- Architecture: HIGH - directly locked by 04-CONTEXT.md and prior validation/docs artifacts
- Pitfalls: HIGH - derived from active scripts, locked decisions, and prior phase validation precedent

**Research date:** 2026-04-11
**Valid until:** 2026-05-11
