# Phase 7: Crate Relocation and Path Rewire - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `07-CONTEXT.md`.

**Date:** 2026-04-12
**Phase:** 07-Crate Relocation and Path Rewire
**Areas discussed:** Moved Layout, Manifest Paths, Legacy Shell, Done Proof

---

## Moved Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Six layer dirs | Move the six existing Rust layer directories intact to repo root. | ✓ |
| Crates only | Move only individual crate folders and re-home the surrounding layer structure separately. | |
| Hybrid move | Leave a mixed old/new tree temporarily while relocating in stages. | |
| You decide | Defer the exact layout choice to implementation. | |

**User's choice:** Six layer dirs
**Notes:** Preserve the current layer topology and ownership boundaries at repo root.

---

## Manifest Paths

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal rewrites | Keep existing `path =` entries wherever the preserved topology still makes them correct. | ✓ |
| Normalize all paths | Rewrite every local `path =` entry during the move. | |
| Modernize manifests | Use the move for broader dependency-style cleanup. | |
| You decide | Defer the manifest policy to implementation. | |

**User's choice:** Minimal rewrites
**Notes:** Only workspace member paths and truly broken manifest edges should change in Phase 7.

---

## Legacy Shell

| Option | Description | Selected |
|--------|-------------|----------|
| No live Rust content | `ClassicLib-rs/` may not keep live crates or workspace-owned Rust files after Phase 7. | ✓ |
| Remove it entirely | Delete `ClassicLib-rs/` completely in Phase 7. | |
| Keep a shell | Leave an intentional compatibility shell under `ClassicLib-rs/`. | |
| You decide | Defer the legacy-tree end state to implementation. | |

**User's choice:** No live Rust content
**Notes:** Any remaining residue under `ClassicLib-rs/` must be clearly non-authoritative and outside the live build graph.

---

## Done Proof

| Option | Description | Selected |
|--------|-------------|----------|
| Cargo + audit matrix | Use Cargo root/member proof plus an explicit relocation audit and stale-path sweep. | ✓ |
| Cargo checks only | Treat Cargo root/member resolution alone as enough closure evidence. | |
| Pull integrations forward | Also require wrapper/parity smoke in Phase 7. | |
| You decide | Defer closure-evidence policy to implementation. | |

**User's choice:** Cargo + audit matrix
**Notes:** Phase 7 should stay cargo-and-layout focused, but it must leave an explicit old-to-new mapping and stale-path audit trail.

---

## the agent's Discretion

- Exact move sequencing.
- Exact mechanical rewrite method.
- Exact audit/report script shape, as long as it satisfies the locked proof requirements.

## Deferred Ideas

None.
