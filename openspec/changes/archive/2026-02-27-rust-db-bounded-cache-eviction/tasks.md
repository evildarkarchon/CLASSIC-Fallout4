## 1. Cache Policy and Lifecycle Design

- [x] 1.1 Define cache capacity configuration and default bounds for Rust database query cache.
- [x] 1.2 Select and document deterministic eviction policy behavior for over-capacity inserts.
- [x] 1.3 Define cleanup trigger strategy for expired entries (timer, threshold, or hybrid).

## 2. Core Implementation

- [x] 2.1 Implement bounded capacity enforcement in query cache insertion paths.
- [x] 2.2 Implement eviction accounting and integrate it with cache statistics.
- [x] 2.3 Implement proactive expired-entry cleanup path alongside existing on-access expiration behavior.

## 3. Validation and Benchmarking

- [x] 3.1 Add/extend tests for capacity enforcement, eviction behavior, and expiration cleanup correctness.
- [x] 3.2 Add/extend tests to ensure lookup behavior parity (hit/miss semantics unchanged).
- [x] 3.3 Compare memory and performance behavior against benchmark baseline and record deltas.

## 4. Documentation and Tuning Guidance

- [x] 4.1 Document new cache lifecycle metrics and tuning guidance for capacity/cleanup parameters.
- [x] 4.2 Document expected trade-offs and safe defaults for long-running scan workloads.
