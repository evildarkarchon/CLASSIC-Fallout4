# `classic-vocabulary` Internal API Guide

Contributor-facing architecture notes for [`foundation/classic-vocabulary/`](../../foundation/classic-vocabulary).

This `publish = false` foundation crate owns the **Vocabulary naming contract**: the rule that the Rust core crate defining a domain concept also owns what that concept is called. It holds one trait, one token lookup, and one reusable conformance assertion. It does not own any enum, any casing convention, or any error shape.

## Why it exists

CLASSIC presents the same facts through three frontends and three binding surfaces. Before this contract, every one of those surfaces wrote its own strings for the same variant, and they had already diverged silently: each copy was independently exhaustive, so every compiler was satisfied, and the binding parity gates compare symbol names and arity rather than values. A wrong string passed CI.

The fix is ownership, not another gate. One definition site, projected everywhere.

## Public workspace API

- `trait Vocabulary: Copy + 'static` — implemented by the core crate that owns a domain enum.
  - `const VARIANTS: &'static [Self]` — every variant, for exhaustive iteration by tests and adapters.
  - `fn as_str(self) -> &'static str` — the frozen adapter-facing **Vocabulary Token**, snake_case.
  - `fn label(self) -> &'static str` — the human-facing **Display Label**, glossary capitalization.
- `from_token<T: Vocabulary>(token: &str) -> Option<T>` — resolves the variant whose token is exactly `token`. A scan over `VARIANTS` rather than a reverse table, so the forward and parse directions cannot disagree.
- `display_label<T, U>(value: U, project: fn(T) -> U) -> &'static str` — resolves the Display Label for a value an adapter already projected, by running that adapter's *existing* forward projection over `VARIANTS`. Same reasoning as `from_token`, applied to a binding's mirror enum instead of a string: a reverse `match` would be a second variant mapping able to disagree with the forward one. Returns `""` for a value the projection cannot produce, so no adapter invents a label or borrows another variant's. It lives here rather than per-binding because nothing about it is surface-specific — the contrasting case is the Node casing transform, which encodes a JavaScript identifier convention and therefore belongs to the surface that has the convention.
- `assert_vocabulary_conformance<T: Vocabulary>()` — the reusable conformance assertion, called once per adopting enum from that crate's sibling test module.
- `assert_twin_vocabulary_conformance<Twin, Source>(source_of, locally_owned_tokens)` — the same, for a **delegating twin**: an enum one crate declares so another crate's type does not leak into its contract, and which mirrors that other enum. Called *instead of* the plain assertion, since it runs the base contract first. `source_of` is the twin-to-source direction of the mapping, returning `None` for a variant the source has no counterpart for; `locally_owned_tokens` names exactly those. It additionally checks that every paired variant agrees with its counterpart on **both** forms, that the unpaired set is exactly the declared one in both directions, and that every *source* variant is reachable from some twin variant — the clause that catches a variant added to the source and not to the twin.

## The two stability guarantees

These are the whole point of carrying two forms rather than deriving one from the other.

- **Vocabulary Tokens are frozen.** They are parsed by binding consumers, so respelling one is a breaking change across all three surfaces at once. Adding a variant is additive; changing an existing token is not. Both parity baselines and every consumer's code depend on the exact bytes.
- **Display Labels may be reworded freely.** They are presentation only and are never parsed. A wording fix reaches every frontend at once, which is why the labels live here rather than in each frontend.

Neither form is derived from the other. A mechanical transform turns `field_transition` into `Field transition` correctly, and turns `local_ignore_reset` into `Local ignore reset` — wrong, because the glossary capitalizes `Local Ignore` as a domain term. Deriving the label would therefore be right for the easy variants and quietly wrong for exactly the ones that name domain concepts.

## Contracts

- `VARIANTS` lists every variant exactly once. Nothing at runtime can verify that completeness — no Rust construct reports how many variants an enum has — so treat the constant as part of the variant definition. Adopting enums pin `VARIANTS.len()` in their own sibling test so that adding a variant lands a contributor on the line that says so.
- Tokens and labels are non-empty, and each form is unique *within* an enum. Uniqueness is deliberately not workspace-wide: two unrelated enums may each have a `missing` variant, and the owning type disambiguates them.
- `as_str` and `label` are written as exhaustive `match` expressions. That exhaustiveness is the enforcement mechanism — a contributor adding a variant cannot ship it without supplying both forms, because the crate will not compile.
- The canonical spelling is snake_case. The C++ and Python surfaces consume the core token unchanged. The Node surface applies one shared camelCase transform in [`node-bindings/classic-node/src/vocabulary.rs`](../../node-bindings/classic-node/src/vocabulary.rs), which lives there rather than here because it implements that surface's documented JavaScript identifier convention, not the naming contract.
- This crate is workspace-internal and has no C++, Node, or Python surface. It is deliberately absent from the binding parity matrix and from the Python, Node, and CXX parity baseline generators. Only the enums cross a binding seam; the trait never does.

## Adopting an enum

1. Implement `Vocabulary` in the core crate that owns the enum, next to its definition.
2. Call `assert_vocabulary_conformance::<YourEnum>()` from that module's sibling test file, and pin `VARIANTS.len()` alongside it.
3. Replace each binding's hand-written token function with `kind.as_str()`, and each parse counterpart with `classic_vocabulary::from_token` — or, on the Node surface, with `crate::vocabulary::js_token` and `crate::vocabulary::from_js_token`.
4. Confirm the three committed parity baselines are byte-identical. A moved baseline means the token projection is wrong, not that the baseline needs regenerating.

   The exception is an enum a frontend renders, which also needs a Display Label projection on each surface. Those projections are new public adapter symbols, so they *do* move all three baselines and invalidate `contractIdsHash`/`contractCount` in both runtime coverage registries. Regenerate with the [per-gate refresh commands](binding-parity-policy.md) and hand-edit the two registry fixtures — the baseline generators normalize those fields in memory only and never write them back.

## Current adopters

### From [`classic-user-settings-core`](classic-user-settings-core.md)

None of these five is rendered by a frontend, so no Display Label of theirs crosses a binding seam. That kept the parity cost at zero for every adoption up to and including them.

| Enum | Notes |
| --- | --- |
| `MigrationChangeKind` | The tracer. Chosen first because its Node token already diverged to camelCase, so it exercises the casing transform for real. |
| `SourceLocation` | Every token is a single word, so the Node transform is an identity. Its reverse-parse path on the CXX and Node surfaces derives from `VARIANTS`. |
| `DocumentClassification` | Three multi-word tokens reach JavaScript as `newerCompatible`, `futureMajor`, and `legacyFlat`. |
| `CommitEligibility` | Two multi-word tokens reach JavaScript as `requiresMigration` and `blockedUntrusted`. |
| `PreferenceOrigin` | One multi-word token reaches JavaScript as `degradedFallback`. Projected at more call sites than any other adopter, since every typed preference carries one. |

Two of the four later adopters are reachable exhaustively through a binding-safe constructor (`DocumentClassification` through the legacy-import outcome, `SourceLocation` through a review-only migration plan), so their per-binding projection tests drive the real conversion functions. `CommitEligibility` and `PreferenceOrigin` only exist inside a `UserSettings` that was opened from a real document; rather than add a test-only constructor for a path production never takes, their exhaustive check sits at the pure projection rule instead. After adoption there is no per-enum projection code left for a production path to exercise differently, so the two seams cover the same ground.

### From [`classic-config-core`](classic-config-core.md)

These three are the first adopters whose Display Labels cross a binding seam, and the first adoption to move a parity baseline. Each surface gained a label projection, so a moved baseline here is expected churn rather than a defect — the opposite of the rule that applied to the User Settings enums.

| Enum | Notes |
| --- | --- |
| `InstalledYamlDataProvenance` | Every label equals its own token. All three frontends already rendered exactly `updated`, `previous`, and `bundled`, and inventing prose to force a difference would make the labels worse. The contract permits this: the two forms are governed separately, not required to differ. |
| `InstalledYamlDataDiagnosticKind` | Four labels settle a CLI/GUI-versus-TUI wording divergence in favor of the descriptive form. Two more carry glossary capitalization (`Local Ignore generated`, `Local Ignore reset`) — the exemplar of why a label cannot be derived from its token. |
| `LocalIgnoreYamlDataState` | `generated` becomes `generated from selected Main defaults`. Python published its tokens from a match inlined in the snapshot getter rather than a named table, so adopting the contract deleted the getter's body rather than a helper. |

Adopting these also deleted two Python restatements of the same vocabulary — `classic-config-py` and `classic-scanlog-py` each wrote out the provenance tokens — and replaced `classic-config-py`'s copy of the five durable-publication stage tokens with delegation to the crate that owns them.

The CXX and Node label projections resolve a variant through the shared `display_label`, which runs that surface's *existing* forward projection over `VARIANTS` rather than matching on the binding-side enum. A reverse `match` would be a second variant mapping that could disagree with the forward one; derived from it, the two cannot. This is the same reasoning `from_token` applies to strings.

### From [`classic-scanlog-core`](classic-scanlog-core.md)

Both are **delegating twins** of the configuration enums above. The Crash Log Scan Run contract declares its own types so that configuration types do not leak into it — an architectural decision this adoption preserves rather than works around — and those types obtain both naming forms by delegating through the near-identity mapping instead of restating them. Restating would have opened a new divergence axis inside the change that closes an old one.

| Enum | Notes |
| --- | --- |
| `InstalledYamlDataRunDiagnosticKind` | A true identity mapping: all ten variants delegate, and the twin owns no vocabulary of its own. It had no token method at all before; three binding surfaces each wrote the ten strings out. |
| `LocalIgnoreRunState` | Identity-plus-one. `RecoveryRequired` has no configuration counterpart — a run can pause for a caller decision and a stored snapshot cannot — so it supplies `recovery_required` and `recovery required` locally. Its inherent `as_str` was replaced by the trait method rather than kept alongside it. |

The asymmetry is asserted rather than assumed: `assert_twin_vocabulary_conformance` is told which tokens are locally owned and checks that set in both directions, so a twin that quietly stopped delegating a variant reads as a failure and not as one more locally owned variant.

Rust cannot invert a `match`, so each twin carries both halves of its mapping as separate functions, and a round-trip test pins them against each other. That is the one place a twin could still go wrong that no single-direction check would see: a variant delegating to the *wrong* counterpart inherits the wrong prose while both halves stay exhaustive.

Adopting these deleted the two remaining hand-written token tables in `classic-scanlog-py` and replaced the last two hardcoded expectation arrays in its projection tests with `VARIANTS` loops.

## Testing

Expected values are derived from the core wherever the thing under test is a projection of the core. A test that restated the vocabulary would be another copy that can drift, and would pass just as happily against a binding that had already diverged. The one legitimate restatement is in the owning crate, where the literal token strings *are* the specification of the frozen identifiers, and in `node-bindings/classic-node/src/vocabulary_tests.rs`, where the published camelCase spellings are pinned and the table is separately checked for completeness against `VARIANTS`.

The scripted per-binding suites — `__test__/*.spec.ts` and `python-bindings/tests/test_*.py` — do quote a handful of settled Display Labels as literals. That is deliberate and narrow: neither language can see `VARIANTS`, so the exhaustive check has to live in the Rust sibling module, and what is left for these to prove is that the projection survives the binding boundary and that a settled wording reached it. Keep them to the wordings a ticket actually decided, and prefer comparing two surfaces to each other over quoting a literal where both publish the same vocabulary — as the Crash Log Scan Run suites do against their configuration counterparts.
