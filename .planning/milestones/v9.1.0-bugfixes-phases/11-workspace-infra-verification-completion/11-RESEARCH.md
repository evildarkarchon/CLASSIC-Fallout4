# Phase 11: Workspace/Infra Verification Completion - Research

**Researched:** 2026-04-06
**Domain:** Verification-closure for Phase 8 workspace and infrastructure work
**Confidence:** HIGH

<user_constraints>
## User Constraints

No phase-specific `CONTEXT.md` exists for Phase 11.

Phase 11 is constrained by the already-accepted Phase 8 implementation history, Phase 8 validation contract, and the milestone audit gap: close missing verification coverage without reopening implementation scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Promote `winreg` to `[workspace.dependencies]` in root `Cargo.toml` | Verify against current `ClassicLib-rs/Cargo.toml` and `classic-path-core/Cargo.toml`; record workspace inheritance evidence in `08-VERIFICATION.md` |
| INFRA-02 | Promote `phf` to `[workspace.dependencies]` in root `Cargo.toml` | Verify against current `ClassicLib-rs/Cargo.toml` and `classic-constants-core/Cargo.toml`; record workspace inheritance evidence in `08-VERIFICATION.md` |
| INFRA-03 | Wire `construct_proton_docs_path` into Linux docs-path discovery workflow with unit tests using mock Proton prefix | Verify against `classic-path-core/src/docs_path.rs`, `linux_proton_docs_path.rs`, and targeted Proton test commands |
| INFRA-04 | Document or resolve `zerovec` workaround dependency in `classic-shared-core` (check if Slint 1.15+ resolved it) | Verify current manifest/docs state and retain the Phase 8 proof story that the workaround was removed and `gui-bridge` remains validated |
| INFRA-05 | Commit generated `index.d.ts` snapshot for Node bindings with CI freshness check | Verify tracked artifact, `.gitignore`, `package.json`, freshness script, and CI workflow together; treat them as one evidence bundle |
| TEST-03 | Add integration test for Linux Proton docs-path discovery with mock Proton prefix structure | Verify directly from `linux_proton_docs_path.rs` plus focused and crate-level cargo test commands |
</phase_requirements>

## Summary

Phase 11 is a verification-closure phase, not an implementation phase. The Phase 8 code and docs already landed, Phase 8 summaries already claim all six requirements complete, and `08-VALIDATION.md` already defines the relevant proof commands. The actual gap is narrower: there is no authoritative `.planning/phases/08-workspace-and-infrastructure/08-VERIFICATION.md`, so the milestone audit still treats all six Phase 8 requirements as orphaned.

The repo’s established pattern for this kind of closure is clear from Phases 7, 9, and 10: the authoritative artifact must live in the original phase directory, must use the repo-standard verification-report structure, must promote validation-map commands into explicit evidence, and must synchronize `.planning/REQUIREMENTS.md` so audit traceability stops reporting orphaned requirements. For Phase 11 specifically, the missing artifact is an **initial** Phase 8 verification report, not a re-verification of an existing `08-VERIFICATION.md`.

The highest-risk mistake is writing the wrong artifact or using the wrong authority model: a new Phase 11-only verification note, summary prose as evidence, or incomplete requirement mapping will fail the milestone audit again. The safe approach is to create `08-VERIFICATION.md` in repo-standard form, use `08-VALIDATION.md` as the command source of truth, use Phase 8 summaries as provenance only, and close requirement traceability in the same change.

**Primary recommendation:** Create `.planning/phases/08-workspace-and-infrastructure/08-VERIFICATION.md` as the single authoritative Phase 8 verification report, back it with the existing Phase 8 validation commands and current source/doc evidence, then update `.planning/REQUIREMENTS.md` so all six Phase 8 requirements map to that report.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep all business logic in Rust core crates.
- Keep non-interface layers thin; C++, Python, Node, and other bindings should wrap Rust APIs rather than reimplementing logic.
- Maintain a single shared Tokio runtime from Rust core runtime facilities; do not introduce another runtime.
- Keep docs synchronized with architecture or workflow changes, especially `README.md` and `AGENTS.md`.
- Never write to `NUL` or `nul` as a file path on Windows.
- Consult `docs/api/README.md` before changing public Rust, bridge, GUI-consumer, or binding-facing APIs; if contract-shaping behavior changes, update affected `docs/api/` pages in the same change.
- Never run C++ tests via raw binaries or raw `ctest`; use the repo PowerShell wrappers.
- For Rust workspace changes, use repo-standard `cargo fmt`, `cargo clippy`, and `cargo test` commands from `ClassicLib-rs/Cargo.toml`.
- For Node binding changes, treat parity artifacts and binding tests as part of the same change.
- For Linux/cloud validation, prefer portable Rust-only subsets when Windows-native surfaces are impractical.

## Standard Stack

> This is a verification-only phase. Use the repo-pinned implementation and existing validation workflow; do not upgrade dependencies in this phase.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Cargo / Rust test harness | cargo `1.94.0`, rustc `1.94.0` | Manifest, crate, and workspace proof for `INFRA-01` to `INFRA-04` and `TEST-03` | Official Rust workspace/testing tooling; already declared in `08-VALIDATION.md` |
| Bun | `1.3.10` | Runs Node parity, freshness, and Bun runtime tests | Current repo-standard Node workflow in `classic-node/package.json` and `ci-typescript.yml` |
| Node.js | `25.9.0` | Runs `bun run test:node` runtime smoke coverage | Required by the repo’s Node acceptance path for `INFRA-05` |
| Python | `3.14.3` | Executes `check_dts_freshness.py` and parity helpers used by Bun scripts | The Node freshness gate is Python-backed in this repo |
| Git | `2.53.0.windows.2` | Provides `git diff` for declaration freshness detection | `check_dts_freshness.py` uses `git diff -- index.d.ts`; no git means no freshness check |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@napi-rs/cli` / NAPI-RS build flow | package.json `^3.0.0`; official docs queried via Context7 | Owns generation of `.node`, `index.js`, and `index.d.ts` | Cite for `INFRA-05` evidence; do not replace with handwritten declarations |
| `ripgrep` (`rg`) | `15.1.0` | Fast source/doc audit for verification tables | Use for evidence gathering and doc/source cross-links |
| PowerShell | `7.6.0` | Repo wrapper entrypoint for Windows/MSVC-sensitive commands | Use when Phase 8 all-features proof needs the repo’s VS-dev-shell wrappers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Creating `08-VERIFICATION.md` in the Phase 8 folder | Creating a new Phase 11-only closure report | Bad tradeoff; duplicates authority and leaves Phase 8 itself without the required artifact |
| Reusing `08-VALIDATION.md` commands as evidence inputs | Inventing new ad hoc proof commands | Bad tradeoff; weakens traceability and risks mismatch with the existing validation contract |
| Treating `index.d.ts` as generated-but-tracked | Hand-editing or regenerating without freshness proof | Bad tradeoff; conflicts with NAPI-RS ownership and repo gate policy |
| Verifying current code/docs/tests directly | Trusting Phase 8 summaries alone | Bad tradeoff; summaries are provenance, not proof |

**Installation:**
```bash
# No new installation work is recommended for Phase 11.
# Use the repo's existing Rust, Bun, Node, Python, and Git tooling.
```

**Version verification:**
- Local environment probes confirmed: `cargo 1.94.0`, `rustc 1.94.0`, `bun 1.3.10`, `node 25.9.0`, `python 3.14.3`, `git 2.53.0.windows.2`, `rg 15.1.0`, `pwsh 7.6.0`
- Repo-pinned implementation targets confirmed from source: `winreg 0.52`, `phf 0.13.1`, `slint 1.15.0`

## Architecture Patterns

### Recommended Project Structure
```text
.planning/
├── REQUIREMENTS.md                                             # checklist + phase traceability closure
├── ROADMAP.md                                                  # phase goal and success criteria provenance
├── v1.0-MILESTONE-AUDIT.md                                     # current blocker narrative to close
└── phases/
    ├── 08-workspace-and-infrastructure/
    │   ├── 08-VALIDATION.md                                    # command source of truth
    │   ├── 08-01-SUMMARY.md                                    # provenance only
    │   ├── 08-02-SUMMARY.md                                    # provenance only
    │   ├── 08-03-SUMMARY.md                                    # provenance only
    │   └── 08-VERIFICATION.md                                  # authoritative artifact to create
    └── 11-workspace-infra-verification-completion/
        └── 11-RESEARCH.md                                      # this research
```

### Pattern 1: Write the authoritative report in the original phase directory
**What:** Create `08-VERIFICATION.md` under the Phase 8 folder; do not create `11-VERIFICATION.md` as a substitute.

**When to use:** Audit-closure phases where implementation already landed but the original phase lacks authoritative verification coverage.

**Prescriptive rules:**
- The report title and frontmatter should identify Phase 8, not Phase 11.
- Phase 11 owns the closure work, but Phase 8 owns the implementation story.
- Because no `08-VERIFICATION.md` exists today, this should be an **initial verification** artifact, not a `re_verification:` refresh of an existing Phase 8 report.

**Example:**
```markdown
---
phase: 08-workspace-and-infrastructure
verified: 2026-04-06T00:00:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 08: Workspace and Infrastructure Verification Report
```

### Pattern 2: Promote `08-VALIDATION.md` entries into explicit requirement evidence
**What:** Use the Phase 8 validation map as the command source of truth, then restate the results in `08-VERIFICATION.md` with direct source/doc/file evidence.

**When to use:** Whenever the phase already has a Nyquist-compliant validation contract but lacks a proper verification artifact.

**Prescriptive rules:**
- Reuse the exact command families already declared in `08-VALIDATION.md`.
- Pair each command with the source file or doc line it proves.
- Keep summaries as provenance only.

**Example:**
```markdown
| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `INFRA-03` | `08-02-PLAN.md` | Linux docs-path prefers valid Proton path before local-share fallback | ✓ SATISFIED | `classic-path-core/src/docs_path.rs:178-225`; `tests/linux_proton_docs_path.rs:22-90`; `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton -- --nocapture` |
```

### Pattern 3: Treat overlapping commands as separate requirement coverage rows
**What:** One command may support multiple requirements, but `08-VERIFICATION.md` must still give each requirement its own explicit row.

**When to use:** `INFRA-03` and `TEST-03` share the Proton test surface; `INFRA-05` uses both freshness and runtime/parity gates.

**Prescriptive rules:**
- `INFRA-03` focuses on wiring and behavior.
- `TEST-03` focuses on the integration proof file and executed test commands.
- `INFRA-05` must cover tracked artifact, freshness script, and CI gate together.

### Pattern 4: Close traceability in the same change
**What:** The verification artifact alone is not enough; update `.planning/REQUIREMENTS.md` so the milestone can map each Phase 8 requirement to concrete verification coverage.

**When to use:** Any verification-backfill phase closing an audit-reported orphaned-requirement gap.

**Prescriptive rules:**
- Check off the six Phase 8 requirements in `.planning/REQUIREMENTS.md` once their Phase 8 verification report exists and is evidence-backed.
- Keep the traceability table aligned with Phase 11 completion.
- If the audit document is maintained manually in the same change, update its blocker language after the verification report exists; if not, at minimum ensure the new source artifact makes the next audit pass deterministic.

### Anti-Patterns to Avoid
- **Creating a Phase 11-only verification artifact:** fails the roadmap success criterion that explicitly names `08-VERIFICATION.md`.
- **Using summary files as proof:** they are claims, not evidence.
- **Collapsing six requirements into a vague single “Phase 8 passed” statement:** the audit needs one-to-one traceability.
- **Reopening implementation scope:** Phase 11 should not rewrite Phase 8 code unless fresh verification proves a real regression.
- **Omitting `.planning/REQUIREMENTS.md` sync:** leaves orphaned requirements even if `08-VERIFICATION.md` is good.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Phase 8 closure artifact | New ad hoc markdown report in the Phase 11 folder | `.planning/phases/08-workspace-and-infrastructure/08-VERIFICATION.md` | The roadmap and audit both require the original phase artifact |
| Proof command set | Fresh custom commands with no provenance | `08-VALIDATION.md` command map | Preserves Nyquist traceability and phase continuity |
| Node declarations | Handwritten `index.d.ts` or manual edits | NAPI-RS-generated `index.d.ts` plus freshness gate | Official NAPI-RS flow generates `.d.ts`; repo gate already enforces freshness |
| Phase 8 evidence | Summary frontmatter only | Source files + docs + targeted commands + CI workflow references | Avoids unverifiable closure claims |
| Proton integration proof | Binding-specific tests | `classic-path-core/tests/linux_proton_docs_path.rs` | Phase 8 decisions already fixed the shared-Rust ownership boundary |

**Key insight:** Phase 11 should compose existing proof assets into one authoritative verification artifact, not invent a new verification system.

## Common Pitfalls

### Pitfall 1: Writing the wrong file
**What goes wrong:** Work lands in `11-VERIFICATION.md` or a plan summary instead of `08-VERIFICATION.md`.
**Why it happens:** Phase 11 owns the gap closure, so it is easy to misplace the final artifact.
**How to avoid:** Anchor on `ROADMAP.md` success criterion 1: the required file is explicitly `08-VERIFICATION.md`.
**Warning signs:** The Phase 8 folder still has no verification report after the work is “done.”

### Pitfall 2: Treating `08-VALIDATION.md` or summaries as sufficient verification
**What goes wrong:** The new report paraphrases validation and summaries without direct evidence tables.
**Why it happens:** The validation doc already contains commands and green statuses.
**How to avoid:** Convert validation rows into report evidence; summaries stay provenance-only.
**Warning signs:** Requirement evidence columns mention only summary filenames or “see validation.”

### Pitfall 3: Failing to separate `INFRA-03` and `TEST-03`
**What goes wrong:** The Proton test file is cited once and both requirements are implicitly assumed covered.
**Why it happens:** They share the same crate and commands.
**How to avoid:** Give `INFRA-03` a behavior/wiring row and `TEST-03` an explicit integration-test row.
**Warning signs:** One of the two IDs is missing from the final requirements table.

### Pitfall 4: Closing the report but not the checklist
**What goes wrong:** `08-VERIFICATION.md` exists, but `.planning/REQUIREMENTS.md` still leaves the six Phase 8 rows pending.
**Why it happens:** Artifact-writing and traceability sync are treated as separate concerns.
**How to avoid:** Update `.planning/REQUIREMENTS.md` in the same change as the new verification report.
**Warning signs:** The next audit would still classify the six requirements as orphaned.

### Pitfall 5: Overstating fresh proof for `INFRA-04`
**What goes wrong:** The verification report claims a current full-workspace all-features rerun without accounting for Windows/MSVC environment constraints.
**Why it happens:** Phase 8 summary already recorded a VS-dev-shell workaround, and plain-shell reruns can fail.
**How to avoid:** If rerunning, use the repo-approved Windows/VS shell path; if not rerunning, clearly cite the prior Phase 8 proof as recorded evidence instead of pretending it was freshly rerun.
**Warning signs:** Plain-shell `cargo test --workspace --release --all-features` fails and the report still says “rerun passed.”

### Pitfall 6: Missing the full `INFRA-05` evidence bundle
**What goes wrong:** The report cites only `index.d.ts` or only the CI workflow.
**Why it happens:** The requirement spans tracked artifact policy, freshness checking, and runtime/parity enforcement.
**How to avoid:** Verify all of: tracked `index.d.ts`, `.gitignore`, `package.json` scripts, `check_dts_freshness.py`, and `ci-typescript.yml`.
**Warning signs:** The report mentions freshness but not how freshness is detected or enforced.

## Code Examples

Verified repo-standard patterns:

### Phase verification report frontmatter (initial verification)
```markdown
---
phase: 08-workspace-and-infrastructure
verified: 2026-04-06T00:00:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 08: Workspace and Infrastructure Verification Report
```

### Requirement coverage row for workspace dependency ownership
```markdown
| `INFRA-01` | `08-01-PLAN.md` | `winreg` is owned by `[workspace.dependencies]` and inherited only under `cfg(windows)` | ✓ SATISFIED | `ClassicLib-rs/Cargo.toml:178-180`; `classic-path-core/Cargo.toml:29-32`; `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` |
```

### Requirement coverage row for the Node freshness bundle
```markdown
| `INFRA-05` | `08-03-PLAN.md` | `classic-node/index.d.ts` is a tracked generated contract artifact with local and CI freshness enforcement | ✓ SATISFIED | `classic-node/.gitignore:1-4`; `classic-node/package.json:17-32`; `tools/node_api_parity/check_dts_freshness.py:25-115`; `.github/workflows/ci-typescript.yml:79-85`; `bun run dts:freshness:check`; `bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` |
```

### Repo-standard Node contract gate commands
```text
# Source: docs/implementation/node_api_parity/governance/gate_contract_baseline.md
bun run parity:gate:local
bun run test:bun
bun run test:node
bun run dts:freshness:check
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase summaries and validation doc imply completion | Phase-wide `*-VERIFICATION.md` explicitly maps requirements to evidence | Established by repo verification pattern visible in Phases 7, 9, and 10 | Audit and milestone closure depend on authoritative per-phase verification reports |
| Crate-local ownership of shared deps | Root `[workspace.dependencies]` with member `workspace = true` inheritance | Phase 8 | Verification should prove ownership wiring, not relitigate dependency choice |
| Linux local-share-only fallback | Cached path, then valid Proton path, then local-share fallback | Phase 8 | `INFRA-03` and `TEST-03` need shared-workflow and test-proof evidence |
| Generated Node declarations treated like disposable artifacts | `index.d.ts` is tracked, reviewed from git, and checked for freshness in CI | Phase 8 | `INFRA-05` verification must cover policy, scripts, and CI enforcement together |

**Deprecated/outdated:**
- Summary-only closure for Phase 8: outdated; the milestone audit explicitly rejects it because there is no `08-VERIFICATION.md`.
- Treating `.gitignore` as authoritative for `index.d.ts`: outdated; Phase 8 removed the contradiction and documented tracked-snapshot governance.

## Open Questions

1. **Should Phase 11 rerun every underlying Phase 8 command or rely partly on recorded Phase 8 evidence?**
   - What we know: `08-VALIDATION.md` already records the command set, and the Phase 8 summaries record successful proof. `INFRA-04` previously required a VS developer environment.
   - What's unclear: Whether the execution plan should require fresh reruns for all six requirements or permit the report to cite Phase 8 recorded evidence where reruns are environment-sensitive.
   - Recommendation: Plan for fresh reruns of the targeted Rust and Node commands that are cheap and available; for MSVC-sensitive full-workspace proof, either use the repo-approved VS shell path or explicitly cite prior recorded evidence rather than overstating freshness.

2. **Should `v1.0-MILESTONE-AUDIT.md` be updated in the same change?**
   - What we know: Success criterion 3 only requires traceability to map all six requirements to a concrete verification report.
   - What's unclear: Whether the audit file is maintained manually per closure phase or regenerated later.
   - Recommendation: Treat `08-VERIFICATION.md` plus `.planning/REQUIREMENTS.md` as mandatory; update the audit in the same change if the workflow expects a hand-maintained blocker narrative, otherwise leave it to the next audit pass.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Cargo | `INFRA-01` to `INFRA-04`, `TEST-03` verification commands | ✓ | `1.94.0` | — |
| Rust compiler | Cargo build/test execution | ✓ | `1.94.0` | — |
| Bun | `INFRA-05` parity/freshness/runtime commands | ✓ | `1.3.10` | — |
| Node.js | `bun run test:node` | ✓ | `25.9.0` | — |
| Python | `check_dts_freshness.py` and parity helpers | ✓ | `3.14.3` | — |
| Git | `check_dts_freshness.py` uses `git diff` | ✓ | `2.53.0.windows.2` | — |
| ripgrep | Source/doc audit while assembling evidence | ✓ | `15.1.0` | Use `grep` tool reads if necessary |
| PowerShell | Repo wrapper entrypoint and VS-shell fallback | ✓ | `7.6.0` | — |
| MSVC toolchain in current shell (`cl`) | Full Windows native/all-features reruns, especially prior `INFRA-04` proof shape | ✗ in current shell | — | Use repo-approved VS developer shell wrapper if Visual Studio is installed |

**Missing dependencies with no fallback:**
- None for the basic Phase 11 verification/report-writing workflow.

**Missing dependencies with fallback:**
- MSVC toolchain is not available in the current shell. Use the repo PowerShell/VS-dev-shell wrapper path for any full native/all-features reruns instead of assuming plain-shell availability.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Rust built-in test harness plus Bun/Node parity and freshness scripts |
| Config file | `.planning/phases/08-workspace-and-infrastructure/08-VALIDATION.md`, `ClassicLib-rs/Cargo.toml`, `ClassicLib-rs/node-bindings/classic-node/package.json`, `.github/workflows/ci-typescript.yml` |
| Quick run command | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton && cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check` |
| Full suite command | `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | `winreg` is workspace-owned and target-gated in `classic-path-core` | build/config | `cargo check -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-02 | `phf` is workspace-owned in `classic-constants-core` | build/config | `cargo check -p classic-constants-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-03 | Shared Linux docs-path workflow prefers valid Proton path then falls back correctly | integration | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton -- --nocapture` | ✅ |
| INFRA-04 | `classic-shared-core` no longer depends on the `zerovec` workaround and `gui-bridge` remains validated | crate-test | `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |
| INFRA-05 | `index.d.ts` is tracked, fresh, and enforced by local + CI Node gates | contract/freshness/runtime | `cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check` | ✅ |
| TEST-03 | Proton integration test file covers happy path and fallback cases | integration | `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton && cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml` | ✅ |

### Sampling Rate
- **Per task commit:** `cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml proton` and/or `cd ClassicLib-rs/node-bindings/classic-node && bun run dts:freshness:check`, depending on the evidence block being assembled
- **Per wave merge:** `cargo test -p classic-shared-core --features gui-bridge --manifest-path ClassicLib-rs/Cargo.toml && cargo test -p classic-path-core --manifest-path ClassicLib-rs/Cargo.toml && cd ClassicLib-rs/node-bindings/classic-node && bun run parity:gate:local && bun run test:bun && bun run test:node && bun run dts:freshness:check`
- **Phase gate:** `08-VERIFICATION.md` exists, `.planning/REQUIREMENTS.md` is synchronized, and the targeted Rust/Node commands used as evidence are green or honestly recorded as prior evidence with rationale

### Wave 0 Gaps
None — existing Phase 8 validation infrastructure already covers the six requirements. Phase 11 needs artifact assembly and traceability closure, not new test scaffolding.

## Sources

### Primary (HIGH confidence)
- Cargo Book — workspaces: https://doc.rust-lang.org/cargo/reference/workspaces.html
- Cargo Book — inheriting dependencies from a workspace: https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#inheriting-a-dependency-from-a-workspace
- Context7 `/napi-rs/website` — NAPI-RS build flow generates `.node`, `.js`, and `.d.ts` artifacts
- `.planning/ROADMAP.md` — Phase 11 goal, requirements, and success criteria
- `.planning/v1.0-MILESTONE-AUDIT.md` — explicit statement that all six Phase 8 requirements are orphaned because `08-VERIFICATION.md` is missing
- `.planning/phases/08-workspace-and-infrastructure/08-VALIDATION.md` — canonical command map for Phase 8 proof
- `.planning/phases/08-workspace-and-infrastructure/08-01-SUMMARY.md`, `08-02-SUMMARY.md`, `08-03-SUMMARY.md` — provenance for what Phase 8 claimed complete
- `ClassicLib-rs/Cargo.toml`, `classic-path-core/Cargo.toml`, `classic-constants-core/Cargo.toml`, `classic-shared-core/Cargo.toml` — implementation-state evidence for `INFRA-01`, `INFRA-02`, and `INFRA-04`
- `ClassicLib-rs/business-logic/classic-path-core/src/docs_path.rs` and `tests/linux_proton_docs_path.rs` — implementation/test evidence for `INFRA-03` and `TEST-03`
- `ClassicLib-rs/node-bindings/classic-node/package.json`, `.gitignore`, `.github/workflows/ci-typescript.yml`, and `tools/node_api_parity/check_dts_freshness.py` — evidence bundle for `INFRA-05`
- Local environment probes run on 2026-04-06 for `cargo`, `rustc`, `bun`, `node`, `python`, `git`, `rg`, `pwsh`, and `cl`

### Secondary (MEDIUM confidence)
- `docs/implementation/node_api_parity/governance/gate_contract_baseline.md` — repo-governed accepted Node command sequence
- `docs/api/binding-contract-refresh-note.md` — contributor-facing Node/Python contract refresh workflow
- `.planning/phases/07-consistency-sweep/07-VERIFICATION.md` and `.planning/phases/09-deprecated-api-verification-closure/09-VERIFICATION.md` — repo-standard verification artifact patterns

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - based on current local environment probes, official Cargo docs, Context7 NAPI-RS docs, and repo package/workflow files
- Architecture: HIGH - based on roadmap/audit requirements plus strong in-repo precedent from Phases 7, 9, and 10
- Pitfalls: MEDIUM-HIGH - grounded in the current milestone audit failure mode and prior phase closure patterns, with only limited dependence on inference

**Research date:** 2026-04-06
**Valid until:** 2026-05-06
