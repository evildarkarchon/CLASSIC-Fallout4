# Phase 4: Gate Validation & Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `04-CONTEXT.md` - this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 04-gate-validation-documentation
**Areas discussed:** Gate refresh policy, Proof bundle, Documentation closure, Execution order

---

## Gate refresh policy

**Question:** How should Phase 4 treat parity baselines at the start?

| Option | Description | Selected |
|--------|-------------|----------|
| Verify then refresh | Run plain gates first; refresh only for intentional, source-backed drift. | ✓ |
| Refresh up front | Use the local refresh commands immediately, then verify. | |
| Verify only | Never refresh in Phase 4; any drift blocks the phase. | |

**User's choice:** Verify then refresh

**Question:** For Node, which command style should Phase 4 treat as canonical?

| Option | Description | Selected |
|--------|-------------|----------|
| Two-step explicit | Use `parity:gate:update-baseline` only when needed, then `parity:gate`. | ✓ |
| parity:gate:local | Use the helper that refreshes `index.d.ts` and the baseline automatically. | |
| Agent decides | Leave the exact Node command choice flexible. | |

**User's choice:** Two-step explicit

**Question:** After any intentional refresh, what final proof do you want?

| Option | Description | Selected |
|--------|-------------|----------|
| Plain gate reruns | Rerun all three gates without refresh flags and require zero drift. | ✓ |
| Only touched gate | Rerun only the gate that refreshed. | |
| Rely on full suite | Let the later end-to-end suite stand in for isolated plain gate reruns. | |

**User's choice:** Plain gate reruns

**Question:** If a gate shows stale artifacts but the live source is correct, how should Phase 4 respond?

| Option | Description | Selected |
|--------|-------------|----------|
| Fix it in phase | Refresh artifacts and keep going; this closure phase owns stale cleanup. | ✓ |
| Stop and report | Treat it as a blocker and leave follow-up work. | |
| Case by case | Decide based on severity during execution. | |

**User's choice:** Fix it in phase
**Notes:** Phase 4 owns stale artifact cleanup and must end with plain zero-drift reruns.

---

## Proof bundle

**Question:** What deliverable should downstream create for Phase 4 closure?

| Option | Description | Selected |
|--------|-------------|----------|
| Verification file | Create a dedicated Phase 4 verification artifact summarizing commands, docs sweep, and gate results. | ✓ |
| Gate artifacts only | Rely on existing parity reports and raw command output. | |
| Context notes only | Capture proof expectations only in CONTEXT/STATE. | |

**User's choice:** Verification file

**Question:** How should the proof be organized?

| Option | Description | Selected |
|--------|-------------|----------|
| One checklist | One milestone-closure checklist covering cargo tests, three parity gates, docs/api, and CLAUDE. | ✓ |
| Per-surface sections | Separate CXX, Python, Node, Rust, and docs sections. | |
| One full command | Prefer one canonical full-suite command plus pass/fail criteria. | |

**User's choice:** One checklist

**Question:** Do you want a Phase 4 audit guard test if it adds real coverage for stale doc/artifact references?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, if needed | Allow a targeted planning/validation test only if existing checks miss a closure condition. | ✓ |
| No new tests | Use only existing gates and doc sweeps. | |
| Only after drift | Add one guard only if execution discovers a recurring stale-reference gap. | |

**User's choice:** Yes, if needed

**Question:** What should the final success bar be?

| Option | Description | Selected |
|--------|-------------|----------|
| Checks plus doc audit | Workspace tests, all three parity gates, and required docs must pass with explicit audit evidence. | ✓ |
| All commands green | If the suite exits 0, that is enough even without separate doc-audit evidence. | |
| Docs and parity only | Focus Phase 4 on docs + parity closure only. | |

**User's choice:** Checks plus doc audit
**Notes:** Closure proof should live in one dedicated checklist-style verification artifact.

---

## Documentation closure

**Question:** For the final doc pass, how broad should the active-doc sweep be?

| Option | Description | Selected |
|--------|-------------|----------|
| Broad active-doc audit | Check CLAUDE, docs/api, PROJECT, codebase maps, and other active contributor docs for stale topology language. | ✓ |
| Requirements-only docs | Update only docs explicitly named by GATE-05/GATE-06 unless a failure forces more. | |
| Agent decides | Keep the exact sweep scope flexible. | |

**User's choice:** Broad active-doc audit

**Question:** How much merge history should remain visible in the surviving docs?

| Option | Description | Selected |
|--------|-------------|----------|
| Brief phase notes | Keep short "moved/absorbed in Phase X" notes where they help contributors. | ✓ |
| Current state only | Strip most milestone history and describe only present owners. | |
| Detailed history | Preserve more narrative about phase-by-phase moves in active docs. | |

**User's choice:** Brief phase notes

**Question:** How should `CLAUDE.md` reflect the 16-crate topology?

| Option | Description | Selected |
|--------|-------------|----------|
| Count plus short history | State the current 16-crate count and summarize Phases 1-3 in one concise sentence. | ✓ |
| Count only | Update the number but remove milestone history from the guidance. | |
| Indirect only | Avoid explicit counts and describe the topology without a numeric total. | |

**User's choice:** Count plus short history

**Question:** If docs are semantically correct but a few references still mention retired names for historical context, should Phase 4 keep them?

| Option | Description | Selected |
|--------|-------------|----------|
| Only helpful history | Keep retired names only when clearly marked as historical or migration context. | ✓ |
| Remove them all | Hard-clean every active contributor doc to present-day names only. | |
| Leave them if fine | Prefer minimal churn even if some historical wording remains. | |

**User's choice:** Only helpful history
**Notes:** Active docs should stay concise and present-day, with retired names kept only when they clearly aid contributor understanding.

---

## Execution order

**Question:** How should the phase sequence work?

| Option | Description | Selected |
|--------|-------------|----------|
| Cheap audits first | Start with doc/parity sanity checks, then run heavier workspace/native suites. | ✓ |
| Heavy suites first | Start with workspace and native builds before cleaning up docs/artifacts. | |
| Reuse Phase 3 order | Carry forward the exact full-suite order from `03-VALIDATION.md`. | |

**User's choice:** Cheap audits first

**Question:** When should C++ validation run relative to the source-only parity gates?

| Option | Description | Selected |
|--------|-------------|----------|
| After parity gates | Let cheap source-only drift checks fail first, then pay for bridge/CLI/GUI builds. | ✓ |
| Before parity gates | Prioritize native integration proof early. | |
| Interleave it | Mix native validation into the Rust/binding verification flow. | |

**User's choice:** After parity gates

**Question:** How should workspace Rust verification fit?

| Option | Description | Selected |
|--------|-------------|----------|
| After cheap cleanup | Run `cargo test --workspace` once the cheap closure issues are resolved. | ✓ |
| First command | Use workspace green/red as the first signal. | |
| Early and late | Run it once near the start and again at the end. | |

**User's choice:** After cheap cleanup

**Question:** If the early cheap audits are green, what next?

| Option | Description | Selected |
|--------|-------------|----------|
| Run full suite | Follow with the full milestone proof, including native and binding workflows. | ✓ |
| Targeted checks only | Only run the surfaces directly touched by remaining cleanup work. | |
| Agent decides | Leave the follow-up depth flexible. | |

**User's choice:** Run full suite
**Notes:** The plan should optimize for cheap early failure but still end with full milestone proof.

---

## the agent's Discretion

- Whether a new targeted audit guard test is needed at all.
- Exact wording and layout of the final verification checklist artifact.
- Exact composition of the final full-suite command, as long as it preserves the chosen ordering and final zero-drift reruns.

## Deferred Ideas

None.
