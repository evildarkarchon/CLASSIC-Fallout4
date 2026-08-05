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
- `assert_vocabulary_conformance<T: Vocabulary>()` — the reusable conformance assertion, called once per adopting enum from that crate's sibling test module.

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

## Current adopters

`MigrationChangeKind` in `classic-user-settings-core` is the first, chosen as the tracer for two reasons: it is the enum whose Node token already diverges to camelCase, so it exercises the casing transform for real, and no frontend renders it, so no Display Label has to cross a binding seam yet. That keeps the parity cost at zero and makes the verification signal sharp — any baseline movement is a defect rather than expected churn.

## Testing

Expected values are derived from the core wherever the thing under test is a projection of the core. A test that restated the vocabulary would be another copy that can drift, and would pass just as happily against a binding that had already diverged. The one legitimate restatement is in the owning crate, where the literal token strings *are* the specification of the frozen identifiers, and in `node-bindings/classic-node/src/vocabulary_tests.rs`, where the published camelCase spellings are pinned and the table is separately checked for completeness against `VARIANTS`.
