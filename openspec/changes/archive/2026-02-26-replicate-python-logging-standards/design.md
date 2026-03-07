## Context

CLASSIC currently has stronger operational logging quality in Python paths than in Rust, C++, and Node integration surfaces. Operators and contributors troubleshoot multi-language failures through mixed outputs, but current non-Python logs do not consistently provide equivalent level semantics, event naming, contextual fields, or actionable diagnostics. This creates avoidable triage time and inconsistent support outcomes.

Constraints:
- Preserve existing runtime behavior while improving observability.
- Keep language-idiomatic logging libraries, but align emitted contract.
- Protect sensitive information via explicit redaction rules.
- Keep CI and local developer workflows practical (no heavy telemetry backends required for validation).

## Goals / Non-Goals

**Goals:**
- Define and enforce a shared logging contract across Python, Rust, C++, and Node paths.
- Ensure parity for level mapping, event taxonomy, and required context fields.
- Provide consistent startup/health diagnostics for bindings and cross-language bridges.
- Make parity objectively testable in language-specific test suites and CI.

**Non-Goals:**
- Replacing each language's logging backend with a single shared implementation.
- Building a new centralized log ingestion platform.
- Refactoring unrelated business logic solely for logging style cleanup.
- Backfilling historical log files generated before this change.

## Decisions

1. **Contract-first logging parity**
   - Decision: Define a canonical cross-language log contract (level mapping, event naming, required fields, and redaction behavior) and adapt each language implementation to it.
   - Rationale: Preserves language-native tooling while converging operational signal quality.
   - Alternatives considered:
     - Single global logging backend: rejected due to high integration cost and lower language ergonomics.
     - Best-effort conventions without contract: rejected because parity becomes unverifiable.

2. **Structured fields with stable minimal schema**
   - Decision: Require a stable core field set for key events (component, event, correlation/request id when available, actionable context, outcome status).
   - Rationale: Enables consistent triage and future tooling without forcing complete field uniformity.
   - Alternatives considered:
     - Fully free-form messages only: rejected due to inconsistent diagnostics quality.
     - Fully rigid schema for all messages: rejected as overly restrictive for incremental adoption.

3. **Deterministic level translation matrix**
   - Decision: Define explicit Python-to-Rust/C++/Node severity translations and test for equivalence on representative events.
   - Rationale: Prevents silent drift (for example, warning downgraded to info in one stack).
   - Alternatives considered:
     - Manual reviewer judgment: rejected as error-prone and non-scalable.

4. **Redaction-first diagnostics**
   - Decision: Require sensitive-value redaction in contract rules and include negative tests for leakage.
   - Rationale: Logging parity must not increase exposure risk.
   - Alternatives considered:
     - Defer redaction policy: rejected because adoption would spread unsafe defaults.

5. **Incremental rollout with parity gates**
   - Decision: Implement adapters and tests incrementally by surface area (Rust core/bindings, C++ CLI/GUI bridges, Node binding entry points) while gating each stage with parity tests.
   - Rationale: Reduces migration risk and keeps change set reviewable.
   - Alternatives considered:
     - Big-bang rollout: rejected due to higher regression risk and harder rollback.

## Risks / Trade-offs

- **[Risk] Over-standardization reduces language ergonomics** -> **Mitigation:** Keep contract minimal and focused on operationally critical events/fields only.
- **[Risk] Increased log volume/noise** -> **Mitigation:** Define event allowlist and severity guidance; validate signal-to-noise during rollout.
- **[Risk] Partial adoption leaves mixed-quality logs** -> **Mitigation:** Add explicit parity tasks and CI checks per language surface.
- **[Risk] Sensitive data leakage during migration** -> **Mitigation:** Add redaction tests and secure defaults before broad rollout.
- **[Risk] Performance overhead in hot paths** -> **Mitigation:** Measure overhead in representative paths and avoid expensive formatting unless level is enabled.

## Migration Plan

1. Baseline: inventory Python logging patterns that define target quality and contract requirements.
2. Define contract artifacts and level/field/redaction matrices.
3. Implement language adapters and mapped event helpers in Rust, C++, and Node binding layers.
4. Add parity tests for representative cross-language flows and failure diagnostics.
5. Enable CI checks for parity and redaction safety.
6. Roll out in stages; monitor diagnostic quality and adjust non-breaking mappings as needed.

Rollback strategy:
- Keep adapter integration points isolated so individual language surfaces can temporarily fall back to previous emitters if regressions appear.
- Retain parity tests to quickly identify the failing surface and revert only affected components.

## Open Questions

- Which concrete Python logger/event families should be the canonical baseline set for parity v1?
- Should parity checks run in every CI lane or only in targeted language workflows initially?
- Do we require a single correlation-id propagation mechanism across all bridges in v1, or allow per-surface availability with common naming?
