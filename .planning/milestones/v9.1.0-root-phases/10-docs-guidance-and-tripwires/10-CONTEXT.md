# Phase 10: Docs, Guidance, and Tripwires - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Refresh the active contributor docs and active agent guidance so they teach the repo-root workspace layout correctly, add one shared migration reference for translating old `ClassicLib-rs` workflows to repo-root workflows, and add regression guards that prevent active guidance from reintroducing `ClassicLib-rs` as the live workspace root. Archival or explicitly legacy docs stay out of scope unless they are still used as active guidance.

</domain>

<decisions>
## Implementation Decisions

### Contributor Documentation
- **D-01:** Phase 10 updates the active onboarding, index, and testing pages plus the active `docs/api/*.md` reference pages those entrypoints route contributors into. Archival or legacy docs remain out of scope.
- **D-02:** Active contributor docs should route through a small maintained set of source-of-truth pages and link to one shared migration reference instead of duplicating old/new path translations page-by-page.

### Agent Guidance
- **D-03:** Treat `AGENTS.md`, the mirrored `classic-project-guide` skill files, and `.planning/codebase/*.md` as active agent guidance that must be corrected and kept synchronized in this phase.

### Migration Reference
- **D-04:** Publish one dedicated migration matrix page as the primary old-to-new workspace translation artifact for Phase 10.
- **D-05:** The matrix must map changed commands, path roots, and key artifact/report locations, then be linked from active docs and skills rather than re-explained separately in each page.

### Regression Guards
- **D-06:** Add hybrid regression protection: keep a strict file-listed audit for must-read docs, skills, and codebase maps, and add a scoped stale-path sweep across active docs, guidance, scripts, and tests with explicit exclusions for planning/history surfaces.
- **D-07:** In active docs and agent guidance, `ClassicLib-rs` is allowed only inside clearly labeled historical or migration notes. It must never be taught as a live workspace root, command root, or active path instruction.

### the agent's Discretion
- Exact matrix file name and placement, as long as it is easy to discover from the top-level docs and skills.
- Exact must-read file list and scoped-sweep exclusion list, as long as the hybrid guard and historical-note policy above are preserved.
- Exact split between `tests/planning/` and `tests/powershell/`, as long as the tripwires stay deterministic and file-backed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope And Requirements
- `.planning/ROADMAP.md` — Phase 10 goal, success criteria, and the requirement to update active docs/guidance and add regression protection.
- `.planning/REQUIREMENTS.md` — `DOCS-01`, `DOCS-02`, and `DOCS-03`, including the migration-reference requirement and regression-guard requirement.
- `.planning/PROJECT.md` — milestone goal, active requirements, and the expectation that docs, skills, and agent context files move to the repo-root contract.
- `.planning/STATE.md` — current milestone position and carry-forward sequencing into Phase 10.

### Prior Locked Decisions
- `.planning/phases/06-repo-root-workspace-cutover/06-CONTEXT.md` — repo root is the only live Cargo workspace root; no `ClassicLib-rs/Cargo.toml` compatibility path.
- `.planning/phases/07-crate-relocation-and-path-rewire/07-CONTEXT.md` — root-level layer directories are the live locations and `ClassicLib-rs/` is no longer a live Rust workspace home.
- `.planning/phases/08-wrapper-and-parity-rewire/08-CONTEXT.md` — legacy `ClassicLib-rs/...` operational paths are regressions and should teach the repo-root replacement instead of remaining supported.
- `.planning/phases/09-clean-validation-and-ci-refresh/09-CONTEXT.md` — historical docs/planning references were deferred into Phase 10; active validation remains file-backed and root-path-first.

### Research Guidance
- `.planning/research/SUMMARY.md` — Phase 10 is the milestone closeout for docs, skills, planning cleanup, and path-regression tripwires.

### Active Contributor Guidance
- `README.md` — top-level contributor entrypoint and repo layout summary that still needs repo-root-path cleanup.
- `docs/README.md` — active documentation hub, command map, and maintenance-routing page.
- `docs/RUST_DOCUMENTATION_INDEX.md` — active Rust-centric documentation index with stale workspace-root commands and links.
- `docs/testing/TESTING_GUIDE_INDEX.md` — active testing/workflow guide with stale path-root commands and maintained-surface routing.
- `docs/api/README.md` — active API guide index that determines which `docs/api/*.md` pages count as current contributor references.
- `docs/api/QUICK_START.md` — active contributor quick-start page that still routes some readers through old moved paths.
- `docs/api/binding-contract-refresh-note.md` — active binding-maintenance guide with command, path, and artifact references that need repo-root translation.

### Active Agent Guidance
- `AGENTS.md` — always-on repo guidance for agent routing, command policy, and workflow rules.
- `.agents/skills/classic-project-guide/SKILL.md` — primary project skill entrypoint for repo-specific agent guidance.
- `.agents/skills/classic-project-guide/references/repo-guide.md` — detailed project skill reference with path, command, and parity workflow guidance.
- `.opencode/skills/classic-project-guide/SKILL.md` — mirrored project-skill entrypoint used by another agent environment.
- `.opencode/skills/classic-project-guide/references/repo-guide.md` — mirrored project-skill reference used by another agent environment.
- `.claude/skills/classic-project-guide/SKILL.md` — mirrored project-skill entrypoint used by another agent environment.
- `.claude/skills/classic-project-guide/references/repo-guide.md` — mirrored project-skill reference used by another agent environment.
- `.planning/codebase/STRUCTURE.md` — agent-consumed codebase map that still describes the pre-move workspace layout.
- `.planning/codebase/CONVENTIONS.md` — agent-consumed conventions map with stale path-root examples.
- `.planning/codebase/TESTING.md` — agent-consumed testing map with stale workspace-root commands and binding paths.

### Existing Validation Patterns
- `tests/planning/test_phase06_validation.py` — reusable must-read audit pattern for docs and skills plus repo-root command assertions.
- `tests/planning/test_phase09_validation.py` — current file-backed validation style for scoped audits, proof-surface coverage, and explicit exclusion boundaries.
- `tests/powershell/rebuild_rust.general_target.test.ps1` — targeted stale-guidance tripwire pattern for script text and repo-root path expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/planning/test_phase06_validation.py`: existing file-listed audit that already names `README.md`, `AGENTS.md`, `docs/README.md`, `docs/api/QUICK_START.md`, and the project-skill files as synchronization-critical surfaces.
- `tests/powershell/rebuild_rust.general_target.test.ps1`: existing PowerShell AST/text-based tripwire that already fails on stale `ClassicLib-rs/...` guidance in active scripts.
- `tests/planning/test_phase09_validation.py`: modern scoped-audit pattern for combining explicit file assertions with policy-based validation.
- `docs/README.md` and `docs/testing/TESTING_GUIDE_INDEX.md`: current command/workflow map pages that can route readers to the dedicated migration matrix instead of duplicating translations.
- `AGENTS.md` and `.agents/skills/classic-project-guide/**`: existing centralized agent-entrypoint surfaces for repo policy and path guidance.

### Established Patterns
- Validation in this repo is file-backed and deterministic (`unittest` content assertions plus PowerShell script checks), not prose-only audit notes.
- Repo-root workspace paths are canonical after Phases 6-9; stale `ClassicLib-rs/...` operational guidance is already treated as a regression in wrappers, parity tooling, and CI.
- Contributor docs and agent guidance are maintained in-repo and expected to change alongside architecture/workflow changes.
- Historical mentions are acceptable only when explicitly labeled; active guidance should teach current flows, not preserve dual-layout ambiguity.

### Integration Points
- `README.md`, `docs/README.md`, `docs/RUST_DOCUMENTATION_INDEX.md`, `docs/testing/TESTING_GUIDE_INDEX.md`, `docs/api/README.md`, `docs/api/QUICK_START.md`, and routed `docs/api/*.md` pages.
- `AGENTS.md`, the mirrored `classic-project-guide` skill files under `.agents/`, `.opencode/`, and `.claude/`, and `.planning/codebase/*.md`.
- `tests/planning/` and `tests/powershell/` for regression-guard implementation.

</code_context>

<specifics>
## Specific Ideas

- Phase 10 should cover active docs plus active API references, not just a small top-level doc subset.
- The migration reference should be a dedicated matrix that maps commands, path roots, and artifact/report locations.
- Active guidance may mention `ClassicLib-rs` only in clearly labeled historical or migration context, never as a live instruction surface.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-docs-guidance-and-tripwires*
*Context gathered: 2026-04-13*
