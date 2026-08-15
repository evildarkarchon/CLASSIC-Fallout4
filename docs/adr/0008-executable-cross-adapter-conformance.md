# Executable cross-adapter conformance

Binding parity uses executable, scenario-owned conformance as its behavioral evidence. Rust, CXX, Node, and Python execute the same versioned scenario packs and emit normalized observations that are compared with expectations owned by the scenario rather than with Rust output. CLI, GUI, and TUI participate separately as consumers: they prove that binding-owned facts and Rust-owned Display Content survive their presentation and layout seams without being treated as additional semantic adapters. The existing `tools/binding_compliance/` suite owns scenario discovery, receipt validation, comparison, coverage accounting, failure classification, and the combined report.

This decision deepens the existing compliance module instead of creating a second parity system. The CXX, Node, and Python surface parsers, declaration and stub validators, Rust inventory parser, and source audits remain specialized implementations behind that module. Domain-specific runners and normalizers also remain real seams. Crash Log Scan Run, User Settings, and later domains can have different actions and observation payloads while sharing scenario identity, applicability, execution, receipt, comparison, and reporting rules. Native CI jobs validate participant-scoped reports against the same oracle; only a run holding every required participant receipt may claim repository-wide conformance.

## Context

The source-level parity gates are valuable but do not prove behavior. CXX inventories `#[cxx::bridge]` declarations. Node and Python map Rust symbols to their public declarations and use runtime-coverage registries to enroll contract rows. The registries record selectors, hashes, test suite names, and claims such as `runtime_verified`; they do not prove that the referenced test executed in the compliance invocation or that all adapters observed the same semantics.

Crash Log Scan Run makes the locality problem concrete. Its shared manifest repeats the complete variant inventory for Rust, CXX, Node, and Python, and its evidence entries prove only that named source files contain expected strings. Four test suites separately load the manifest, construct equivalent filesystem fixtures, normalize paths, and compare overlapping subsets of the result. The checks are individually useful, but the evidence interface exposes test layout and source markers instead of hiding them behind executed observations.

Runtime testing cannot replace every parity check. A passing call cannot prove that an unused legacy export is absent, that a TypeScript discriminated union rejects an invalid program, that a Python stub has the right annotation, or that a frontend has not copied a Rust-owned wording table. Those facts remain structural or negative conformance evidence.

## Decision

### Evidence has three roles

The compliance report distinguishes three roles rather than treating all evidence as interchangeable:

1. **Semantic adapters** are Rust, CXX, Node, and Python. They execute a shared action and return normalized domain observations.
2. **Consumer participants** are CLI, GUI, and TUI. They prove presentation, routing, interaction, and Display Layout obligations at their actual frontend seams. They do not become alternative owners of binding semantics.
3. **Structural and negative analyzers** prove source/API shape, declaration and stub correctness, forbidden-export absence, type-level contracts, and ownership constraints that runtime observations cannot prove.

Every parity obligation must resolve to executed semantic or consumer evidence, a named structural or negative analyzer, or a documented parity-policy exception. A manual acknowledgement, source marker, test name, registry classification, or owner-module smoke test is not sufficient evidence by itself.

### Scenario packs own expectations

Conformance scenarios are versioned JSON committed with their fixtures. A scenario names stable canonical Rust capabilities and observation families, supplies deterministic inputs, declares any allowed normalization, and contains explicit expected normalized observations. The conformance engine materializes an input-only run plan for adapters; expected values are withheld from adapter runners and compared centrally.

Comparison is exact after normalization. Object fields, ordered sequences, stable tokens, structured errors, durable effects, and Display Content segments must match. Unordered collections and excluded nondeterministic fields are allowed only when the scenario schema names the exact paths and explains the reason. Extra observable facts fail just as missing or changed facts do. Timing, temporary-root prefixes, and unconstrained concurrent interleavings are excluded unless a scenario explicitly makes them contractual.

Expected observations are never generated from a Rust execution. Rust is one adapter subject to the same comparison as CXX, Node, and Python.

### Receipts prove execution

Adapter-native commands emit ephemeral, machine-readable receipts. Each receipt identifies the participant and execution instance, role, scenario and pack version, invocation and run-plan identity, current source identity, expectation digest, runner, executed capabilities, actual normalized observation, execution status, and any failure classification. The compliance suite derives observed fact identifiers from the validated action and observation rather than trusting runner-authored coverage claims. It rejects missing, duplicate, malformed, stale, skipped, or unexpected scenarios. A `not_applicable` result requires a specific documented policy exception; a required participant cannot report `unsupported`.

Only a receipt produced by an executed case can grant runtime coverage. Contract selectors and hashes remain useful generated diagnostics, but no human-editable `runtime_verified` field or test-case pointer can satisfy the gate.

Receipts and combined reports are CI artifacts, not committed passing snapshots. Scenario packs, independent expectations, deliberate structural baselines, and policy exceptions remain tracked. An exact schema version and expectation digest prevent a result against an earlier contract from satisfying the current gate.

### Coverage starts from canonical Rust capabilities

Scenario packs name canonical Rust capabilities and observation families once. The compliance module expands those names through the source-derived CXX, Node, and Python parity mappings and associates the resulting contract rows with executed receipts. Data types, fields, variants, and accessors receive transitive runtime coverage only through an executed public operation whose normalized observation exercises them. Broad owner-module enrollment is not enough.

The CXX baseline currently inventories bridge declarations rather than mapping the complete public Rust core surface. It must gain canonical owner/core-symbol metadata before it can participate in this derivation. This is a prerequisite of retiring the CXX runtime-coverage gap, not a reason to pretend the source-only baseline already proves it.

A new runtime-verifiable public parity row fails unless the same change maps it to an executable capability or to a documented policy exception. A genuinely declaration-only, erased-type, or negative row must map to a named structural or negative analyzer; a policy exception cannot stand in for valid static evidence. Migration sequencing does not create a second tier or deferred backlog: existing evidence remains blocking until its replacement is blocking.

### Native execution stays with native adapters

Bindings keep their existing build and runtime ownership. Rust uses Cargo tests, Node uses its Bun/Node package commands, Python uses the uv-managed PyO3 build and pytest workflow, and CXX uses the approved C++ build wrapper. These commands write a common receipt format, after which `tools/binding_compliance/` validates and aggregates the results. A full local profile may orchestrate every available adapter as a convenience, but the common module does not absorb native build-system knowledge into its public interface.

CXX conformance begins in the first executable pack. A dedicated, test-only `classic-cxx-conformance` CTest target is hosted by `classic-cli/CMakeLists.txt`, links the generated CXX bridge directly, traverses the CXX DTOs and events in C++, and emits actual normalized observations. Rust may not serialize CXX observations on its behalf. A conformance-granting invocation runs only through `classic-cli/build_cli.ps1 -Test -CTestName classic-cxx-conformance` with a current input-only run plan and receipt destination; an ordinary full wrapper run skips this test when those inputs are absent. The target does not compile or link production CLI frontend sources and introduces no production CLI command, flag, or test mode. CI runs it in the existing Windows CLI matrix for both MSVC and clang-cl so the native build directory and caches are reused.

CLI, GUI, and TUI consumer receipts are separate from the CXX semantic receipt. Their existing frontend-specific request construction, streams, exit codes, recovery prompts, widgets, styling, path links, and Display Layout remain frontend concerns.

### Migration is a per-pack ratchet

Migration is part of the contract. Each domain pack passes through four states:

1. **Shadow** — new executable evidence runs without replacing an existing gate.
2. **Equivalent** — reports demonstrate equal or stronger obligation coverage and matching outcomes for every required participant.
3. **Blocking** — missing, stale, malformed, or mismatching receipts fail the applicable CI jobs.
4. **Retired** — only then are equivalent acknowledgement lists, positive source markers, registry claims, and duplicate adapter expectations removed.

The order is Crash Log Scan Run, User Settings, existing fixture-backed domains, remaining owner modules, and finally registry and historical-evidence cleanup. The implementation specification records objective entry, exit, deletion, and verification criteria for every phase. Existing checks may be removed only surface by surface; one migrated pack does not justify deleting evidence for an unmigrated pack.

## Checks that remain

The following stay independent even after all runtime-verifiable surfaces migrate:

- CXX, Node, and Python source/signature parity and generated Rust-surface inventories.
- Node `index.d.ts` freshness and compile-only TypeScript contract assertions.
- Python `.pyi` validation and type-surface checks.
- Forbidden-export contraction audits across source, declarations, stubs, and tracked contracts, plus public runtime-namespace absence probes where a binding can be loaded safely.
- Rust Vocabulary owner invariants.
- Negative Vocabulary and Display Content ownership audits that reject adapter-local naming, interpolation, pluralization, or copied Rust-owned prose.
- Rust core fault-injection and internal invariant tests that cannot safely be reached through a public binding seam.

Positive adapter assertions may be removed only when a receipt exercises and records the same variants, fields, labels, segment kinds, severities, and error behavior. Canonical Rust presentation goldens remain at the owning module seam; adapters prove lossless transport and consumer behavior without restating the prose.

## Consequences

Adding a scenario or normalized observation changes the shared contract once and automatically obligates every applicable adapter. Contributors no longer copy complete variant inventories, test names, or source markers into four evidence sections. A failed report identifies whether the problem is structural drift, missing execution, stale evidence, malformed output, applicability policy, normalization, semantic mismatch, command failure, or local toolchain setup.

The cost is real infrastructure. Every adapter needs an observation producer, the CXX parity artifact needs canonical mapping metadata, CI must retain and validate receipts, and domain packs need careful normalization. Exact comparison also makes contract changes deliberate. These costs buy behavioral evidence with a deletion test: removing the conformance module would force scenario materialization, coverage accounting, comparison, and failure classification back into each binding suite.

## Alternatives rejected

A universal domain payload was rejected because the domains do not share one honest result shape. Independent per-domain harnesses were rejected because they would repeat execution, applicability, receipt, and coverage machinery. Per-contract-row tests were rejected because DTO fields and accessors are rarely meaningful operations, while owner-module smoke tests were rejected as too coarse. Adapter-specific snapshots were rejected because they create four competing oracles. A central job that cold-builds every toolchain was rejected in favor of native workflow execution and common receipts. Runtime-only compliance was rejected because absence, declaration, erased-type, and ownership guarantees are not observable through successful calls.

This decision complements ADR-0002, ADR-0004, ADR-0006, and ADR-0007: Rust continues to own business behavior, User Settings, Installed YAML Data policy, and Crash Log Scan Run Display Content. It changes how those contracts are proved across bindings; it does not move their ownership or reopen their seams.

The executable schemas, CI topology, phased migration, and deletion gates are specified in the [Executable Cross-Adapter Conformance Specification](../implementation/executable_cross_adapter_conformance.md).
