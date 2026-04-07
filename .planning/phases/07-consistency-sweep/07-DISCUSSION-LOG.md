# Phase 7: Consistency Sweep - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `07-CONTEXT.md` - this log preserves the alternatives considered.

**Date:** 2026-04-06
**Phase:** 07-consistency-sweep
**Areas discussed:** Sweep breadth, once_cell exit path, verification bar, churn style

---

## Sweep Breadth

| Option | Description | Selected |
|--------|-------------|----------|
| Code + manifests + API docs | Convert source, remove stale `once_cell` dependencies from touched crates and workspace manifests, and update affected `docs/api` pages that would become inaccurate. | ✓ |
| Code + manifests only | Finish the source and Cargo cleanup, but leave documentation follow-up for later. | |
| Code only | Do the narrowest possible source sweep and intentionally defer manifest and doc drift. | |

**User's choice:** Code + manifests + API docs
**Notes:** User wanted Phase 7 to finish the consistency sweep end-to-end instead of leaving stale dependency declarations or contributor docs behind.

---

## once_cell Exit Path

| Option | Description | Selected |
|--------|-------------|----------|
| Migrate it to OnceLock | Convert the remaining `OnceCell` usage in `record_scanner.rs` too, so `once_cell` can be removed entirely if no other APIs remain after the audit. | ✓ |
| Leave OnceCell in place | Keep Phase 7 strictly about `Lazy` -> `LazyLock`; retain `once_cell` because `RecordScanner` still uses `OnceCell`. | |
| Audit first, then decide | Treat full dependency removal as optional and migrate non-`Lazy` sites only if the remaining uses are trivial. | |

**User's choice:** Migrate it to OnceLock
**Notes:** User preferred treating full `once_cell` removal as part of the same phase rather than stopping at `Lazy` replacement.

---

## Verification Bar

| Option | Description | Selected |
|--------|-------------|----------|
| Targeted tests + workspace build | Run focused tests for touched crates with global/static behavior, then a workspace build to catch dependency and integration breakage. | ✓ |
| Full workspace test sweep | Run the widest available Rust test coverage even if it is slower. | |
| Minimal compile check | Rely mostly on build success, with little or no targeted runtime testing. | |

**User's choice:** Targeted tests + workspace build
**Notes:** User chose a balanced proof bar: targeted behavior checks where globals are involved, plus broader compile/build confidence for the manifest sweep.

---

## Churn Style

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical only | Keep Phase 7 strictly one-for-one: std replacements plus only the cleanup required to compile and keep docs/manifests accurate. | |
| Adjacent touched-file cleanup | Allow small cleanup in the same touched files or modules when it directly improves the migration result, but no broader crate-wide refactors. | ✓ |
| Same-crate cleanup | Allow broader cleanup anywhere in a touched crate while Phase 7 is underway. | |

**User's choice:** Adjacent touched-file cleanup
**Notes:** User revisited this area once, then confirmed the final boundary should allow small local cleanup only when it stays adjacent to the migrated files and directly supports the sweep.

---

## the agent's Discretion

- Exact ordering of file edits and manifest cleanup.
- Exact import and constructor shapes for `LazyLock` and `OnceLock`.
- Exact targeted test commands, as long as they cover the touched global-state crates plus a workspace-level build.

## Deferred Ideas

None.
