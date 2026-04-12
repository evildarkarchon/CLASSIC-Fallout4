<user_constraints>
## User Constraints

No phase-specific `*-CONTEXT.md` exists for Phase 05.

### Locked Decisions
- This is a cleanup phase, not a new feature phase.
- Focus on the safest repo-native reconciliation of stale planning/docs/test artifacts.
- Do not reopen already-satisfied milestone requirements.

### the agent's Discretion
- Choose the safest repo-native way to refresh stale documentation navigation, verification bookkeeping, and Node parity tripwire tracking.

### Deferred Ideas (OUT OF SCOPE)
- Any new feature work
- Any binding API redesign
- Any parity baseline refresh not required by actual live drift
- Re-litigating already satisfied consolidation requirements
</user_constraints>

# Phase 05: milestone-cleanup - Research

**Researched:** 2026-04-11
**Domain:** Repo-native cleanup of stale docs, verification artifacts, and parity tripwires
**Confidence:** HIGH

## Summary

Phase 05 should be executed as a narrow cleanup pass over three stale artifacts, not as another consolidation implementation phase. The live tree already shows the post-consolidation truth: `docs/api/README.md` routes contributors to surviving crate-owner docs, Phase 3 validation already says the previously escalated closure gaps were resolved, and the checked-in Node parity contract/report both show a live Tier-1 total of **705** with `tierDefinitions.tier2` already removed.

The safest repo-native approach is: (1) update `docs/RUST_DOCUMENTATION_INDEX.md` to route only to surviving owner docs, (2) refresh `03-VERIFICATION.md` in place so its frontmatter and evidence match the live tree plus `03-VALIDATION.md`, and (3) reconcile the Node floor tripwire to the live contract total **705** everywhere it is asserted or explained. Add a small planning audit test (`tests/planning/test_phase05_validation.py`) rather than relying on manual grep-only verification.

**Primary recommendation:** Use one plan with three sequential cleanup tasks plus a Wave 0 planning audit test; refresh stale artifacts in place, and use existing parity/test tooling instead of inventing new scripts or baselines.

## Project Constraints (from AGENTS.md)

- Prioritize active work in `classic-cli/`, `classic-gui/`, and `ClassicLib-rs/`.
- Keep business logic in Rust; non-interface layers stay thin.
- Maintain a single shared Tokio runtime from Rust core facilities.
- Keep docs synchronized with architecture/workflow changes.
- Never write to `NUL` or `nul` on Windows.
- Consult `docs/api/README.md` when changing contributor-facing API routing.
- Never run C++ tests directly; use `classic-cli/build_cli.ps1 -Test` or `classic-gui/build_gui.ps1 -Test` if native validation becomes necessary.
- For Node-binding follow-up, use the existing parity scripts in `ClassicLib-rs/node-bindings/classic-node/package.json`.

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Markdown planning/docs artifacts | repo-native | Source of truth for roadmap, verification, and contributor routing | This phase is primarily a tracked-artifact cleanup, not product-code work |
| Python `unittest` | stdlib (Python 3.14.3 installed) | Planning audit guard under `tests/planning/` | Existing phase audit tests use `unittest.TestCase` patterns |
| `pytest` | 9.0.3 installed; Context7 docs for pytest 9.0.0 | Test runner/collector for `tests/planning/test_phase05_validation.py` and parity tool tests | Repo already runs unittest-style planning audits through pytest |

### Supporting
| Library / Tool | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Bun | 1.3.10 | Run plain Node parity gate via package script | Use when validating the floor-tripwire reconciliation against the live contract |
| Node.js | v25.9.0 | Required by Bun/Node binding tooling | Use indirectly through `bun run parity:gate` / `bun run test:node` |
| Cargo | 1.94.0 | Optional cross-check for referenced verification evidence | Only if the planner chooses to re-prove a Rust claim, not for routine doc cleanup |
| Python `json` + `pathlib` | stdlib | Read parity contract/report and artifact text in audit tests | Use for exact, deterministic file-backed assertions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Refreshing `03-VERIFICATION.md` in place | Writing a new superseding note/file | In-place refresh is safer because the audit, roadmap, and phase directory all already point at `03-VERIFICATION.md` |
| Manual spot-checks only | New planning audit test | Manual-only verification is cheaper short-term but easier to regress later |
| Refreshing Node parity baselines again | Updating the stale floor literal/comment only | Baselines already reflect current truth (`705`); another refresh adds noise and risk with no evidence of drift |

**Installation:**
```bash
# None — use existing repo tooling
```

**Version verification:** Tool versions were verified from the local environment with `python --version`, `pytest --version`, `bun --version`, `node --version`, and `cargo --version`. No new third-party package installation is recommended for this phase.

## Architecture Patterns

### Recommended Project Structure
```text
.planning/phases/05-milestone-cleanup/
├── 05-RESEARCH.md              # this file
└── 05-01-PLAN.md               # cleanup execution plan

tests/planning/
└── test_phase05_validation.py  # new audit guard for this cleanup phase

docs/
└── RUST_DOCUMENTATION_INDEX.md # contributor entrypoint routing

.planning/phases/03-constants-version-registry-merge/
└── 03-VERIFICATION.md          # stale artifact to refresh in place

tools/node_api_parity/tests/
└── test_check_parity_gate.py   # floor tripwire to reconcile
```

### Pattern 1: Source-of-Truth-Driven Cleanup
**What:** Derive each edit from the current live source of truth before changing the stale artifact.
**When to use:** For stale docs, stale verification bookkeeping, and stale test comments/assertions.
**Example:**
```python
# Source: tests/planning/test_phase03_validation.py
from pathlib import Path
import json

repo_root = Path(__file__).resolve().parents[2]
contract = json.loads(
    (repo_root / "docs/implementation/node_api_parity/baseline/parity_contract.json")
    .read_text(encoding="utf-8")
)

assert len(contract["tier1Mappings"]) == 705
```

### Pattern 2: Refresh Existing Verification Artifacts In Place
**What:** Keep the existing `*-VERIFICATION.md` path, but update frontmatter, observable truths, required artifacts, and gaps summary so the file matches current reality.
**When to use:** When the stale artifact is already the canonical path referenced by roadmap/audit files.
**Example:**
```markdown
---
phase: 03-constants-version-registry-merge
verified: 2026-04-11T..
status: passed
score: 9/9 must-haves verified
---

**Re-verification:** Yes — refreshed during Phase 05 cleanup against the live tree and `03-VALIDATION.md`.
```

### Pattern 3: Planning Audit Tests Use `unittest`, Run With `pytest`
**What:** Follow the existing `tests/planning/test_phase03_validation.py` and `test_phase04_validation.py` pattern.
**When to use:** For doc/planning cleanup phases with deterministic file-backed assertions.
**Example:**
```python
# Source pattern: tests/planning/test_phase04_validation.py
import unittest
from pathlib import Path

class Phase05ValidationAuditTests(unittest.TestCase):
    def test_node_floor_matches_live_contract(self) -> None:
        ...

if __name__ == "__main__":
    unittest.main()
```

### Anti-Patterns to Avoid
- **Do not treat the milestone audit as the source of truth.** It identifies debt; the live tree and current validation artifacts define what is true now.
- **Do not regenerate parity baselines just because a comment/assertion is stale.** The current checked-in Node artifacts already show `705` and zero gaps.
- **Do not append a tiny note to `03-VERIFICATION.md` while leaving stale frontmatter/body sections intact.** Refresh the full artifact coherently.
- **Do not remove broken index links without rerouting contributors to surviving owner docs.** Use `docs/api/README.md` as the canonical routing map.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Owner-doc routing | New ad hoc doc taxonomy | `docs/api/README.md` as canonical surviving-owner index | The repo already defines the active contributor-facing routing there |
| Verification refresh | New bespoke checklist or one-off note | Existing structured `*-VERIFICATION.md` format used by Phases 2-4 | Keeps planner/verifier expectations consistent |
| Contract truth | Manual row recounts from comments | Read `parity_contract.json` and `parity_diff_report.md` | The live contract/report already encode the current floor (`705`) |
| Cleanup regression guard | Shell-only manual grep ritual | `tests/planning/test_phase05_validation.py` run under pytest | Deterministic, repo-native, and repeatable in later audits |

**Key insight:** This phase should reuse existing repo formats and evidence paths. The debt is stale bookkeeping, not missing infrastructure.

## Common Pitfalls

### Pitfall 1: Fixing the Broken Index by Deleting Lines Only
**What goes wrong:** `docs/RUST_DOCUMENTATION_INDEX.md` loses broken links but also stops routing users to the surviving owners of absorbed surfaces.
**Why it happens:** The stale lines are easy to delete without checking `docs/api/README.md` for the intended owner pages.
**How to avoid:** Replace absorbed-crate routing with surviving-owner descriptions: YAML -> `classic-settings-core`; constants -> `classic-version-registry-core`, `classic-settings-core`, and existing `classic-shared-core` coverage.
**Warning signs:** The top-level index no longer mentions where former constants/YAML contributors should go.

### Pitfall 2: Partial Refresh of `03-VERIFICATION.md`
**What goes wrong:** Frontmatter says `passed` but body tables still list failed truths/gaps, or vice versa.
**Why it happens:** Editing only the header or only the narrative summary.
**How to avoid:** Refresh frontmatter, observable truths, required artifacts, anti-patterns, and gaps summary together, using `03-VALIDATION.md` and the live tree as evidence.
**Warning signs:** `status: passed` appears alongside `✗ FAILED` rows or old timestamps from 2026-04-10.

### Pitfall 3: Updating the Floor Literal but Not the Explanation
**What goes wrong:** `711` changes to `705` in the assert, but comments, failure message, or deferred-item narrative still describe a 6-row regression.
**Why it happens:** The tripwire spans both test code and planning markdown.
**How to avoid:** Update the assert threshold, explanatory comment, failure wording, and Phase 2 deferred-items text together.
**Warning signs:** The test passes locally but docs still say `705 < 711` is an unresolved regression.

### Pitfall 4: Reopening Milestone Closure Work
**What goes wrong:** The cleanup phase starts re-running heavy consolidation work or changing parity artifacts without live drift.
**Why it happens:** Stale bookkeeping can look like stale implementation.
**How to avoid:** Treat this as artifact reconciliation only. Use plain parity checks to confirm current truth; do not refresh baselines unless the gate proves drift.
**Warning signs:** Planner starts adding `--update-baseline` or wide code edits unrelated to the three cleanup targets.

## Code Examples

Verified repo-native patterns:

### File-backed Planning Audit Test
```python
# Source: tests/planning/test_phase03_validation.py
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PARITY_CONTRACT = (
    REPO_ROOT / "docs/implementation/node_api_parity/baseline/parity_contract.json"
)


class Phase05ValidationAuditTests(unittest.TestCase):
    def test_node_floor_matches_contract(self) -> None:
        contract = json.loads(PARITY_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(len(contract["tier1Mappings"]), 705)
```

### Repo-standard Node Parity Gate Invocation
```json
// Source: ClassicLib-rs/node-bindings/classic-node/package.json
{
  "scripts": {
    "parity:gate": "python ../../../tools/node_api_parity/check_parity_gate.py --repo-root ../../..",
    "parity:gate:update-baseline": "python ../../../tools/node_api_parity/check_parity_gate.py --repo-root ../../.. --update-baseline"
  }
}
```

### Pytest Running `unittest.TestCase` Suites
```bash
# Source: Context7 /pytest-dev/pytest, unittest docs
pytest tests/planning/test_phase05_validation.py -q
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Top-level Rust doc index linked absorbed crate pages directly | Top-level index should route only to surviving owner docs; absorbed names survive only as historical notes | Consolidation Phases 1-4; audit caught remaining stale links on 2026-04-11 | Contributor navigation stays aligned with the live 16-crate topology |
| Phase closure could remain in a stale verification artifact after later fixes landed | Verification artifacts are expected to reflect current live status, with re-verification if needed | Explicitly demonstrated by structured Phase 4 verifier artifact on 2026-04-12 | Planner should refresh stale verification in place rather than leave contradictory bookkeeping |
| Node parity governance used tiered/deferred-era tripwires and floor comments | Current live Node contract is one-tier, `tier2` removed, and checked-in diff report shows 705 Tier-1 rows | Node contract/baseline state verified in current tree (`generated_at_utc` 2026-04-12) | The tripwire should protect the live one-tier contract, not an outdated 711-row story |

**Deprecated/outdated:**
- `docs/RUST_DOCUMENTATION_INDEX.md` links to deleted `classic-yaml-core.md` / `classic-constants-core.md` pages.
- `03-VERIFICATION.md` overall `gaps_found` status is outdated relative to the live tree and `03-VALIDATION.md`.
- The `711` Node floor narrative is outdated relative to the live contract/report (`705`).

## Open Questions

1. **Refresh `03-VERIFICATION.md` in place or supersede it with a new note?**
   - What we know: the roadmap, milestone audit, and phase directory all point to `03-VERIFICATION.md` as the canonical artifact.
   - What's unclear: whether the planner wants a separate historical breadcrumb for the stale version.
   - Recommendation: refresh `03-VERIFICATION.md` in place; mention re-verification explicitly in the body.

2. **Should Phase 05 add a dedicated planning audit test?**
   - What we know: Phase 3 and Phase 4 both use `tests/planning/test_phaseXX_validation.py` as durable regression guards.
   - What's unclear: none at the repo-pattern level.
   - Recommendation: yes — add `tests/planning/test_phase05_validation.py` as Wave 0.

3. **Does the top-level doc index need new lines, or only line replacement/removal?**
   - What we know: the index already has `classic-shared-core`, `classic-settings-core`, and `classic-version-registry-core` entries.
   - What's unclear: whether the cleanup is best as pure removal or as small wording updates to mention absorbed ownership.
   - Recommendation: prefer minimal edits that preserve routing clarity; do not add new pages or duplicate `docs/api/README.md`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | planning audit tests, parity tooling | ✓ | 3.14.3 | — |
| pytest | `tests/planning/test_phase05_validation.py`, parity tool tests | ✓ | 9.0.3 | `python -m pytest ...` |
| Bun | plain Node parity gate | ✓ | 1.3.10 | none for Node gate |
| Node.js | Bun/Node runtime tests | ✓ | v25.9.0 | none for Node gate |
| Cargo | optional Rust proof reruns | ✓ | 1.94.0 | skip if not needed for touched files |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.0.3 collecting `unittest.TestCase` planning audits |
| Config file | none detected for repo-root pytest; Node scripts in `ClassicLib-rs/node-bindings/classic-node/package.json` |
| Quick run command | `python -m pytest tests/planning/test_phase05_validation.py -q` |
| Full suite command | `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-05-01 | `docs/RUST_DOCUMENTATION_INDEX.md` routes only to surviving owner docs | unit/doc audit | `python -m pytest tests/planning/test_phase05_validation.py -q` | ❌ Wave 0 |
| SC-05-02 | `03-VERIFICATION.md` status/evidence match live tree and `03-VALIDATION.md` | unit/artifact audit | `python -m pytest tests/planning/test_phase05_validation.py -q` | ❌ Wave 0 |
| SC-05-03 | Node floor tripwire and deferred-items note agree with live contract floor | unit + touched-surface parity | `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"` | ❌ / ✅ |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/planning/test_phase05_validation.py -q`
- **Per wave merge:** `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q`
- **Phase gate:** `python -m pytest tests/planning/test_phase05_validation.py tools/node_api_parity/tests/test_check_parity_gate.py -q && pwsh -Command "Set-Location 'ClassicLib-rs/node-bindings/classic-node'; bun run parity:gate"`

### Wave 0 Gaps
- [ ] `tests/planning/test_phase05_validation.py` — audit guard for the three cleanup success criteria

## Sources

### Primary (HIGH confidence)
- `AGENTS.md` — repo constraints and doc/API update rules
- `.planning/ROADMAP.md` — Phase 05 goal, success criteria, and scope
- `.planning/v9.1.0-MILESTONE-AUDIT.md` — exact cleanup debt to close
- `docs/api/README.md` — canonical surviving-owner documentation routing
- `docs/RUST_DOCUMENTATION_INDEX.md` — current broken contributor entrypoint
- `.planning/phases/03-constants-version-registry-merge/03-VERIFICATION.md` — stale artifact to refresh
- `.planning/phases/03-constants-version-registry-merge/03-VALIDATION.md` — proof that prior Phase 3 closure gaps were resolved
- `tools/node_api_parity/tests/test_check_parity_gate.py` — stale Tier-1 floor tripwire
- `.planning/phases/02-crashgen-config-merge/deferred-items.md` — stale deferred note about `705 < 711`
- `docs/implementation/node_api_parity/baseline/parity_contract.json` — live contract count (`705`) and no `tier2`
- `docs/implementation/node_api_parity/baseline/parity_diff_report.md` — checked-in zero-drift Node gate summary (`705/705`)

### Secondary (MEDIUM confidence)
- `/pytest-dev/pytest` via Context7 — pytest collects `unittest.TestCase` tests and documents `xfail(strict=True)` semantics

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - phase uses existing repo tooling only; installed versions were verified locally and pytest behavior was checked via Context7.
- Architecture: HIGH - repo already demonstrates the exact cleanup pattern in earlier planning audit tests and structured verification artifacts.
- Pitfalls: HIGH - all major failure modes are visible in the current stale files and milestone audit.

**Research date:** 2026-04-11
**Valid until:** 2026-05-11
