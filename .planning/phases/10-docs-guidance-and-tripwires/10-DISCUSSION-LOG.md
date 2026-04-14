# Phase 10: Docs, Guidance, and Tripwires - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 10-docs-guidance-and-tripwires
**Areas discussed:** Contributor docs, Agent guidance, Migration reference, Regression guard

---

## Contributor docs

| Option | Description | Selected |
|--------|-------------|----------|
| Active docs plus active API refs | Update onboarding/index/testing pages and the active `docs/api/*.md` pages they route contributors into. Skip archival/legacy docs. | x |
| Top-level docs only | Limit Phase 10 to main entrypoints like `README.md`, `docs/README.md`, `docs/RUST_DOCUMENTATION_INDEX.md`, `docs/testing/TESTING_GUIDE_INDEX.md`, and `docs/api/QUICK_START.md`. | |
| Nearly all docs/ | Treat almost every non-archival page under `docs/` as in scope, even if it is not a primary entrypoint today. | |

**User's choice:** Active docs plus active API refs.
**Notes:** Update the active onboarding, index, testing, and active API-reference surfaces; archival or legacy docs stay out of scope.

---

## Agent guidance

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on + skills + codebase maps | Treat `AGENTS.md`, the mirrored `classic-project-guide` skill files, and `.planning/codebase/*.md` as active agent guidance for this phase. | x |
| Always-on + skills only | Update `AGENTS.md` and the project skill copies, but leave `.planning/codebase/*.md` for a later mapping refresh. | |
| Only always-on guides | Limit Phase 10 agent guidance to top-level always-on files and defer deeper cleanup. | |

**User's choice:** Always-on + skills + codebase maps.
**Notes:** Agent-facing cleanup must include the always-on guide, mirrored project-skill files, and the codebase maps downstream agents use.

---

## Migration reference

### Primary artifact

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated matrix page | Create one explicit old-path/old-command to new-path/new-command matrix, then link to it from top-level docs and skills. | x |
| Narrative migration note | Create one prose guide with examples and checklists, but no primary mapping matrix. | |
| Distributed inline notes | Keep migration help embedded directly inside each top-level doc instead of introducing one shared artifact. | |

### Matrix contents

| Option | Description | Selected |
|--------|-------------|----------|
| Commands + paths + artifacts | Map old and new command forms, working directories/path roots, and key artifact/report locations that changed with the move. | x |
| Commands only | Focus strictly on build/test/validation commands; leave path and artifact translation to surrounding docs. | |
| Commands + roots only | Map commands and directory roots, but not artifact/report locations. | |

**User's choice:** Dedicated matrix page; commands + paths + artifacts.
**Notes:** The matrix becomes the shared source of truth that other active docs and skills should link to instead of duplicating migration guidance.

---

## Regression guard

### Guard type

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid guard | Keep a strict file-listed audit for must-read docs/skills/maps, and add a scoped stale-path sweep over active docs/guidance/tests with explicit exclusions for planning/history. | x |
| Curated file list only | Guard only a named set of key files. Lower maintenance, but stale guidance can survive outside the list. | |
| Broad sweep only | Rely on a wider pattern-based scan across active docs/guidance/tests. Highest coverage, but more exclusion tuning and false-positive risk. | |

### Acceptable `ClassicLib-rs` usage in active guidance

| Option | Description | Selected |
|--------|-------------|----------|
| Only labeled historical notes | Active guidance must not teach `ClassicLib-rs` as a live path or command. The string is allowed only inside clearly marked historical or migration context. | x |
| No mentions at all | Ban `ClassicLib-rs` entirely from active docs/guidance, even in historical notes. | |
| Allow source-path mentions | Permit `ClassicLib-rs` anywhere it is only pointing at old source locations, even if the page is otherwise active. | |

**User's choice:** Hybrid guard; only labeled historical notes.
**Notes:** The final guard should combine deterministic must-read audits with a scoped stale-path sweep, and active guidance cannot teach `ClassicLib-rs` as a live workspace root.

---

## the agent's Discretion

- Exact matrix page file name and placement.
- Exact must-read file list and scoped-sweep exclusion list.
- Exact split between `tests/planning/` and `tests/powershell/` for the final tripwires.

## Deferred Ideas

None — discussion stayed within phase scope.
