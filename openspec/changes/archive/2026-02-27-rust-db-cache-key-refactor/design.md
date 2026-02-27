## Context

Hot-path lookups in `classic-database-core` currently build string-based cache keys with repeated formatting and plugin lowercasing. This introduces avoidable allocation and normalization work in both single and batch lookup paths.

The refactor should improve efficiency while preserving key-equivalence behavior.

## Goals / Non-Goals

**Goals:**
- Move cache key handling toward typed normalized representation.
- Eliminate repeated formatted composite key construction in hot loops.
- Preserve existing case-insensitive plugin behavior and lookup parity.
- Keep API behavior unchanged for callers.

**Non-Goals:**
- Major redesign of database query planning.
- Behavioral changes to value resolution or report formatting.
- New external dependencies unless clearly justified.

## Decisions

1. **Typed key over ad hoc string composition**
   - Use a normalized key path that captures table, formid, plugin equivalence directly.
   - Keep hashing fast and deterministic.

2. **Normalize once at ingestion boundary**
   - Normalize plugin casing at key construction time and avoid repeated lowercasing downstream.
   - Ensure single and batch paths share the same normalization semantics.

3. **Parity-focused migration**
   - Transition internal key handling without altering public function signatures.
   - Keep cache behavior contract stable (hit/miss equivalence from caller view).

4. **Validation-first approach**
   - Add targeted tests for equivalence, distinctness, and duplicate normalization handling.

## Risks / Trade-offs

- **[Risk] Key-equivalence bug causes silent cache misses/hits** → **Mitigation:** add explicit parity tests across case and path variants.
- **[Risk] Migration leaves mixed key styles in code paths** → **Mitigation:** enforce single key-construction helper used by all lookup paths.
- **[Risk] Over-optimization harms maintainability** → **Mitigation:** keep key type minimal and document normalization rules.

## Migration Plan

1. Introduce typed normalized key representation and helper constructors.
2. Refactor single lookup path to use typed keys.
3. Refactor batch lookup path to use typed keys consistently.
4. Run parity tests and benchmark comparisons against baseline.

## Open Questions

- Should key type retain optional precomputed hash or rely on standard hash impl only?
- Is any compatibility path needed for previously inserted legacy string keys during transition?
