## 1. Key Model and Normalization Strategy

- [ ] 1.1 Define typed normalized cache key representation for table, FormID, and plugin components.
- [ ] 1.2 Define shared normalization helpers (especially plugin case normalization) used by single and batch lookup paths.
- [ ] 1.3 Define compatibility expectations for key equivalence and distinctness behavior.

## 2. Hot-Path Refactor

- [ ] 2.1 Refactor single lookup cache access paths to use typed normalized keys instead of formatted composite strings.
- [ ] 2.2 Refactor batch lookup cache access paths to use the same typed key path and normalization rules.
- [ ] 2.3 Remove redundant formatted key assembly and repeated normalization churn from hot loops.

## 3. Correctness and Parity Tests

- [ ] 3.1 Add/extend tests for case-insensitive plugin equivalence in cache key matching.
- [ ] 3.2 Add/extend tests for non-equivalent key separation and collision-sensitive behavior.
- [ ] 3.3 Validate single and batch lookup parity for cache hit/miss behavior after refactor.

## 4. Performance Validation and Documentation

- [ ] 4.1 Measure allocation and throughput impact against baseline for single and batch lookup scenarios.
- [ ] 4.2 Document key normalization rules and expected performance trade-offs for future contributors.
