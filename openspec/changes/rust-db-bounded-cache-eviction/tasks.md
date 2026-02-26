## 1. Cache Policy and Lifecycle Design

- [ ] 1.1 Define cache capacity configuration and default bounds for Rust database query cache.
- [ ] 1.2 Select and document deterministic eviction policy behavior for over-capacity inserts.
- [ ] 1.3 Define cleanup trigger strategy for expired entries (timer, threshold, or hybrid).

## 2. Core Implementation

- [ ] 2.1 Implement bounded capacity enforcement in query cache insertion paths.
- [ ] 2.2 Implement eviction accounting and integrate it with cache statistics.
- [ ] 2.3 Implement proactive expired-entry cleanup path alongside existing on-access expiration behavior.

## 3. Validation and Benchmarking

- [ ] 3.1 Add/extend tests for capacity enforcement, eviction behavior, and expiration cleanup correctness.
- [ ] 3.2 Add/extend tests to ensure lookup behavior parity (hit/miss semantics unchanged).
- [ ] 3.3 Compare memory and performance behavior against benchmark baseline and record deltas.

## 4. Documentation and Tuning Guidance

- [ ] 4.1 Document new cache lifecycle metrics and tuning guidance for capacity/cleanup parameters.
- [ ] 4.2 Document expected trade-offs and safe defaults for long-running scan workloads.
