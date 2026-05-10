# Phase 9: Clean Validation and CI Refresh - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `09-CONTEXT.md` - this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 09-clean-validation-and-ci-refresh
**Areas discussed:** Clean-run rigor, CI closure surface, Package-sensitive proof surface, Artifact refresh, Legacy residue

---

## Clean-run rigor

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted clean | Quarantine the highest-risk outputs before proof: legacy `ClassicLib-rs/target`, repo-root `target`, binding `.venv`, Node build outputs, and binding/parity working artifacts touched by the validated flows. | x |
| Full scrub | Wipe every generated repo output we can identify before proof. | |
| Minimal clean | Only quarantine known legacy outputs and rely on current workflows for the rest. | |

**User's choice:** Targeted clean
**Notes:** The user wants stronger proof than Phase 6's legacy-target-only quarantine, but not a full machine scrub.

---

## CI closure surface

| Option | Description | Selected |
|--------|-------------|----------|
| Core CI + benchmark + one package flow | Refresh all active PR CI workflows plus `benchmarks.yml`, and require one native package-sensitive proof surface. | x |
| Core CI only | Limit Phase 9 to the active PR CI workflows. | |
| Everything package-sensitive | Make core CI, benchmark, and full native package or install flows all blocking evidence. | |

**User's choice:** Core CI + benchmark + one package flow
**Notes:** Benchmarks are part of Phase 9 closure. One native package-sensitive proof must also be required.

---

## Package-sensitive proof surface

| Option | Description | Selected |
|--------|-------------|----------|
| GUI package flow | Use `classic-gui/build_gui.ps1` as the required native package-sensitive proof surface. | x |
| CLI package flow | Use `classic-cli/build_cli.ps1` packaging as the required proof surface. | |
| Either one | Let planning choose the cheaper package-sensitive flow. | |

**User's choice:** GUI package flow
**Notes:** The user wants the heavier GUI packaging surface to be the required native proof.

---

## Artifact refresh

| Option | Description | Selected |
|--------|-------------|----------|
| CI-owned artifacts only | Regenerate the path-bearing artifacts directly used by the required CI and package proof surfaces. | x |
| All path-bearing artifacts | Regenerate any artifact in the repo that encodes workspace paths. | |
| Refresh only on failure | Audit first and regenerate only if a workflow proves an artifact is stale. | |

**User's choice:** CI-owned artifacts only
**Notes:** The user wants clean proof for live CI surfaces without broad unrelated artifact churn.

---

## Legacy residue

| Option | Description | Selected |
|--------|-------------|----------|
| Any new generated output | Fail Phase 9 if validation recreates generated outputs under `ClassicLib-rs/`. | x |
| Only build outputs | Fail only on recreated live build outputs such as `ClassicLib-rs/target`. | |
| Full zero-residue tree | Treat any remaining `ClassicLib-rs` filesystem residue as a Phase 9 failure. | |

**User's choice:** Any new generated output
**Notes:** Historical docs and planning references stay deferred to Phase 10 unless they break live validation.

---

## the agent's Discretion

- Exact targeted-clean mechanics.
- Exact CI-owned artifact list derived from the required proof surfaces.
- Exact orchestration of audits, workflow changes, and live proof commands.

## Deferred Ideas

None.
