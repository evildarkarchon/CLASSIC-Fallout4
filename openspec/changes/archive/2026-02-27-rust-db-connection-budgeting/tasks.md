## 1. Budget Policy Definition

- [x] 1.1 Define the global connection budget model and default auto-calculation policy.
- [x] 1.2 Define deterministic per-pool distribution logic with minimum allocation rules.
- [x] 1.3 Define fallback behavior for low-budget/high-pool-count edge cases.

## 2. Core Allocation Implementation

- [x] 2.1 Implement global-budget allocation logic in `classic-database-core` pool initialization flow.
- [x] 2.2 Apply effective per-pool limits when creating sqlx SQLite pools across active database files.
- [x] 2.3 Implement allocation recalculation behavior for database path topology changes and runtime budget updates.

## 3. Stats and Compatibility Validation

- [x] 3.1 Expose effective allocation details and global budget information through pool statistics surfaces.
- [x] 3.2 Add/extend tests for allocation correctness with single-db and multi-db configurations.
- [x] 3.3 Validate that public lookup APIs remain behavior-compatible for existing bindings and consumers.

## 4. Performance and Operational Validation

- [x] 4.1 Run benchmark baseline comparisons with multi-db scenarios to measure resource and throughput impact.
- [x] 4.2 Document tuning recommendations for global budget settings on different hardware profiles.
