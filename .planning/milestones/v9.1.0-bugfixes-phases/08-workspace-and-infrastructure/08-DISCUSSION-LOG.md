# Phase 8: Workspace and Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 08-workspace-and-infrastructure
**Areas discussed:** Linux docs-path behavior, Linux proof strength, `zerovec` workaround policy, Node type freshness enforcement

---

## Linux docs-path behavior

### Question 1

| Option | Description | Selected |
|--------|-------------|----------|
| Prefer Proton | Use the Steam/Proton path when Steam metadata resolves. Best fit for the Proton goal and likely more accurate for actual Steam installs. | ✓ |
| Prefer local share | Keep the current Linux path as the first non-cached winner, and only use Proton as a later fallback. | |
| Ask caller to choose | Surface both candidates and let higher layers decide. | |

**User's choice:** Prefer Proton
**Notes:** Proton path should win when both candidates exist.

### Question 2

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back locally | Keep trying the existing `~/.local/share/<relative_path>` path before failing. | ✓ |
| Fail immediately | Treat missing/invalid Proton metadata as a hard miss. | |
| Only use cached path | After cached-path miss, require an explicit caller-provided path. | |

**User's choice:** Fall back locally
**Notes:** Preserve the existing Linux local-share path as fallback.

### Question 3

| Option | Description | Selected |
|--------|-------------|----------|
| Shared workflow | Make the existing Linux docs-path workflow Proton-aware without changing its public contract. | ✓ |
| Fallout4-only wrappers | Wire Proton support only through Fallout 4-specific helpers. | |
| Binding-specific only | Handle Proton lookup separately in individual bindings/frontends. | |

**User's choice:** Shared workflow
**Notes:** Reuse `classic-path-core` rather than duplicating behavior in wrappers.

### Question 4

| Option | Description | Selected |
|--------|-------------|----------|
| Version-aware | Use selected version metadata when already available. | |
| Original only | Handle the standard Fallout 4 Steam app first and leave VR-specific Proton support for later. | |
| Ignore version choice | Use one generic Fallout 4 Proton path regardless of selected version. | |

**User's choice:** Fallout 4 VR support for Linux is out of scope.
**Notes:** Phase 8 should target standard Fallout 4 Linux Proton docs-path support only.

---

## Linux proof strength

### Question 1

| Option | Description | Selected |
|--------|-------------|----------|
| Crate-level integration | Add end-to-end tests in `classic-path-core` using a mock Proton prefix and fallback cases. | ✓ |
| One consumer too | Shared workflow integration tests plus one higher-level caller smoke test. | |
| Shared workflow only | Limit proof to targeted helper-wiring tests. | |

**User's choice:** Crate-level integration
**Notes:** Proof should stay with the shared Rust workflow rather than spreading Linux-specific tests across bindings.

### Question 2

| Option | Description | Selected |
|--------|-------------|----------|
| Invalid Proton -> local fallback | Steam metadata resolves but Proton docs path is missing, so local-share fallback wins. | |
| Steam lookup fails -> local fallback | Steam metadata cannot be resolved at all, then local-share fallback wins. | |
| Both fallback cases | Lock both fallback branches as required proof. | ✓ |

**User's choice:** Both fallback cases
**Notes:** Both failure branches should be explicit required coverage.

### Question 3

| Option | Description | Selected |
|--------|-------------|----------|
| Yes | Keep an explicit test for the old non-Proton Linux path. | ✓ |
| No, implicit is enough | Rely on fallback tests to cover old behavior indirectly. | |

**User's choice:** Yes
**Notes:** Preserve explicit regression proof for the legacy Linux path.

---

## `zerovec` workaround policy

### Question 1

| Option | Description | Selected |
|--------|-------------|----------|
| Remove if proven | Remove only if an isolated proof build shows the workaround is unnecessary; otherwise keep it tracked. | |
| Keep and document | Leave the workaround in place with explicit tracking. | |
| Force removal | Delete it because the old Slint GUI is gone, even without proof-first validation. | ✓ |

**User's choice:** Force removal
**Notes:** The removed Slint GUI means the workaround should not survive by default.

### Question 2

| Option | Description | Selected |
|--------|-------------|----------|
| Allow blocker cleanup | Remove only the Slint/gui-bridge pieces directly blocking workaround removal. | ✓ |
| Stop at workaround | Remove `zerovec` only if it comes out cleanly; defer broader cleanup otherwise. | |

**User's choice:** Allow blocker cleanup
**Notes:** Adjacent stale Slint/gui-bridge code may be removed if it directly blocks workaround removal.

### Question 3

| Option | Description | Selected |
|--------|-------------|----------|
| Remove stale references | Delete or rewrite stale comments/docs so they match the post-removal state. | ✓ |
| Keep historical note | Leave a historical note explaining the old workaround. | |

**User's choice:** Remove stale references
**Notes:** Do not preserve obsolete workaround notes unless still needed for an active feature.

---

## Node type freshness enforcement

### Question 1

| Option | Description | Selected |
|--------|-------------|----------|
| Track it in git | Remove the gitignore rule and treat `index.d.ts` as a required committed contract artifact. | ✓ |
| Keep build-first model | Leave it gitignored and require local builds before types exist. | |
| Hybrid | Commit only for releases, not as a normal tracked artifact. | |

**User's choice:** Track it in git
**Notes:** The declaration snapshot should be a normal repo artifact.

### Question 2

| Option | Description | Selected |
|--------|-------------|----------|
| Same-change required | Regenerate and commit `index.d.ts`, then run the existing freshness/parity workflow in the same change. | ✓ |
| CI can catch later | Allow source changes first and rely on CI freshness failure later. | |
| Types only | Require declaration refresh but not parity-artifact refresh. | |

**User's choice:** Same-change required
**Notes:** No delayed follow-up for public Node contract changes.

### Question 3

| Option | Description | Selected |
|--------|-------------|----------|
| Yes | End the old build-first assumption; committed snapshot is first-class. | ✓ |
| No, keep both stories | Keep build-first as a normal contributor expectation. | |

**User's choice:** Yes
**Notes:** Builds should regenerate/verify declarations, not be required just to inspect them.

---

## the agent's Discretion

- Exact shared-helper factoring for Proton-aware Linux docs-path discovery.
- Exact test helper structure and environment injection for Linux docs-path tests.
- Exact freshness-command sequencing and doc wording for the Node declaration workflow.
- Exact adjacent blocker cleanup required to remove the `zerovec` workaround.

## Deferred Ideas

- Broader repo-wide removal of remaining Slint integration beyond the direct blockers tied to `zerovec` removal.
