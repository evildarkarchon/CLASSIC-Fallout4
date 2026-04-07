# Phase 4: Bounded Cache Replacement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 04-bounded-cache-replacement
**Areas discussed:** Stats Shape, Binding Scope, Behavior Parity, Test Isolation

---

## Stats Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Shared core + extras | Canonical `CacheStats` is the shared five-field contract; extra cache-specific details stay on separate helpers. | ✓ |
| One rich struct | Keep one typed stats struct with extra fields like `total_bytes` and `keys` embedded directly. | |
| Minimal five only | Standardize strictly on the five shared fields and drop extra public stats details. | |

**User's choice:** Shared core + extras
**Notes:** The canonical contract should stay exactly `hits`, `misses`, `hit_rate`, `size`, `capacity`. Any extra cache-specific detail belongs outside that shared struct.

---

## Binding Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Existing surfaces only | Update Rust core plus bindings that already expose cache stats, but do not broaden into brand-new cache APIs everywhere. | |
| Rust core only | Limit Phase 4 to Rust core and docs, leaving binding cache-stat contracts divergent for now. | |
| All bindings now | Align cache stats across every binding surface, including new cache-stat exposure where it does not exist today. | ✓ |

**User's choice:** All bindings now
**Notes:** The user wants Phase 4 to align all bindings in the same phase, not defer new cache-stat exposure for currently uncovered surfaces.

---

## Behavior Parity

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current behavior | Preserve current freshness/invalidation behavior for each cache and only change boundedness plus observability. | ✓ |
| Partial cleanup | Smooth a few inconsistencies while keeping cache semantics mostly distinct. | |
| Full harmonization | Make freshness and invalidation behavior consistent across all three caches in this phase. | |

**User's choice:** Keep current behavior
**Notes:** YAML stays mtime-aware, settings stays manual-invalidated, and the hash cache stays path-keyed/manual-clear. Phase 4 should not turn into cache-semantics redesign.

---

## Test Isolation

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse current APIs | Keep the current public clear/reset APIs as the supported test hooks and avoid new public test-only surface. | ✓ |
| Add internal helpers | Add crate-private or `#[cfg(test)]` helpers for deterministic reset/eviction while keeping public API stable. | |
| Add public reset API | Add explicit public `reset_for_tests()`-style APIs. | |

**User's choice:** Reuse current APIs
**Notes:** Tests should be rewritten around public behavior and stats. Internal test-only helpers are acceptable only if truly necessary.

---

## the agent's Discretion

- Exact `quick_cache` plumbing per crate.
- Exact internal accounting used to populate `size` and `capacity` consistently.
- Exact binding DTO/helper names for newly added cache-stat surfaces.

## Deferred Ideas

None.
