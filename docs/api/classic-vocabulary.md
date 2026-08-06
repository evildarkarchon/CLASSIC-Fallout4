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

### From [`classic-durable-publication`](classic-durable-publication.md)

One enum, and the only adopter that is itself a workspace-internal crate with no binding surface. It adopts the contract not because anything renders it directly, but because two other crates mirror it as their own type and needed something to delegate *to*.

| Enum | Notes |
| --- | --- |
| `PublicationStage` | Every label equals its own token, for the same reason as `InstalledYamlDataProvenance`: all three frontends already render exactly `create`, `write`, `flush`, `sync`, and `publish` for a reset publication failure, and these name ordinary steps rather than domain terms. A test pins the equality so that a contributor who wants prose has to read why first. Its inherent `as_str` was replaced by the trait method, and `Display` now renders through it. |

This is the crate that documents itself as *the* stage vocabulary for the whole workspace. Before this adoption two mirrors — `classic-config-py`'s Python token table and the Crash Log Scan Run contract's `LocalIgnoreResetFailureStage` — each restated the five strings, which made the claim untrue. Both now delegate.

### From [`classic-scanlog-core`](classic-scanlog-core.md)

Six enums, in two groups.

Three are **delegating twins**. The Crash Log Scan Run contract declares its own types so that the types it mirrors do not leak into it — an architectural decision this adoption preserves rather than works around — and those types obtain both naming forms by delegating through the near-identity mapping instead of restating them. Restating would have opened a new divergence axis inside the change that closes an old one.

| Enum | Notes |
| --- | --- |
| `InstalledYamlDataRunDiagnosticKind` | A true identity mapping: all ten variants delegate, and the twin owns no vocabulary of its own. It had no token method at all before; three binding surfaces each wrote the ten strings out. |
| `LocalIgnoreRunState` | Identity-plus-one. `RecoveryRequired` has no configuration counterpart — a run can pause for a caller decision and a stored snapshot cannot — so it supplies `recovery_required` and `recovery required` locally. Its inherent `as_str` was replaced by the trait method rather than kept alongside it. |
| `LocalIgnoreResetFailureStage` | A true identity mapping onto [`classic-durable-publication`](classic-durable-publication.md)'s `PublicationStage` — not a configuration enum, unlike the other two. The sharpest case for delegating: its source documents itself as *the* stage vocabulary for the whole workspace, and the five byte-identical strings restated here made that claim untrue. |

The asymmetry is asserted rather than assumed: `assert_twin_vocabulary_conformance` is told which tokens are locally owned and checks that set in both directions, so a twin that quietly stopped delegating a variant reads as a failure and not as one more locally owned variant.

Rust cannot invert a `match`, so each twin carries both halves of its mapping as separate functions, and a round-trip test pins them against each other. That is the one place a twin could still go wrong that no single-direction check would see: a variant delegating to the *wrong* counterpart inherits the wrong prose while both halves stay exhaustive.

Three the run crate **owns outright**. Nothing mirrors them, so the plain `assert_vocabulary_conformance` is the whole check and the labels are authored here rather than inherited.

| Enum | Notes |
| --- | --- |
| `LogDisposition` | Three variants. The only label that differs from its token does so by the word separator alone. |
| `LogFailureStage` | Three variants. `Unsolved Logs finalization` keeps the glossary capitalization of a domain term — the case that shows why a label is not derivable from a token. |
| `InfrastructureErrorStage` | Six variants. `FormID database access` capitalizes a domain term and `internal invariant validation` reads as the failure rather than the noun. Its `Display` impl renders the **token**, not the label, and is unchanged. |

Adopting all six deleted every remaining hand-written token table in `classic-scanlog-py` — including the run status and reset stage projections, which the parent issue had not counted — and replaced the remaining hardcoded expectation arrays in the Node and Python projection tests with `VARIANTS` loops.

## Testing

Expected values are derived from the core wherever the thing under test is a projection of the core. A test that restated the vocabulary would be another copy that can drift, and would pass just as happily against a binding that had already diverged. The one legitimate restatement is in the owning crate, where the literal token strings *are* the specification of the frozen identifiers, and in `node-bindings/classic-node/src/vocabulary_tests.rs`, where the published camelCase spellings are pinned and the table is separately checked for completeness against `VARIANTS`.

A frontend gets a **source audit** rather than a behavior test, because the failure mode is invisible to behavior: a newly written duplicate table produces correct strings on the day it is written and only diverges later, so it is behaviorally perfect at exactly the moment it should be rejected. All three exist — `classic-cli/tests/test_display_label_audit.cpp`, `classic-gui/tests/test_display_label_audit.cpp`, and the naming-table half of `ui-applications/classic-tui/tests/shared_runtime_audit.rs` — each reading its own frontend's `src/` as text and asserting that no file matches on one of the seven rendered enums and returns a string literal, catching the `match`/`switch` form, the single-line expression form, and the shape-based form together.

Two properties are load-bearing. They come from the shared-runtime half of `ui-applications/classic-tui/tests/shared_runtime_audit.rs`, which established the shape and which the naming-table half now reuses in the same file. They count occurrences rather than naming functions, so a table added to an already-audited file is caught without anyone remembering to extend the audit. And each carries a meta-test that fails when its own file list goes stale — all three versions compare the declared list against a recursive directory listing, since a naming table is likelier to appear in a new file than an old one. A third case in the two C++ audits asserts the bridge label accessors are still *called*, so deleting a call site reads as a frontend that stopped saying what happened rather than as compliance.

The GUI audit is a port of the CLI's rather than a rewrite, but three differences are deliberate and matter to anyone porting it further. The shape-based detector's return-type allowlist gains `QString`; without it that detector — the only one that survives a `using` alias, a lookup container, or a bare `default:` return — matches nothing in a Qt frontend, since every label-shaped function there returns `QString` and never `std::string`. The `switch`-arm and single-line detectors look for a quote *after* a `return` rather than the adjacent `return "`, because a Qt table reads `return QStringLiteral("analysis");`. And offenders are accumulated into one assertion instead of one per file, because Qt Test has no non-fatal check to play the role Catch2's `CHECK` plays in the CLI version.

The GUI audits per-log disposition negatively but not positively, which is the one asymmetry between the two. The CLI renders a disposition label; the GUI has no disposition line at all, mapping the three variants onto booleans that select control flow and feed counts. Requiring the accessor there would have forced a results-view column into existence to justify the test. Keeping the enum in the negative half costs nothing and means a contributor who later adds that column cannot fill it with a table.

The TUI audit lives inside the file the other two were ported from rather than in a new one, and four things about it differ. It carries no positive half: the TUI links the core crates directly, so a Display Label reaches it as a plain `label()` method call with no accessor symbol to look for, and the behavior it would prove is already asserted by `src/scan_run_tests.rs` and `tests/local_ignore_recovery_tests.rs` against real rendered output. It audits the whole of `src/` rather than the modules that render a scan run today, because a hand-written subset would leave the next renderer unaudited from the day it lands. Its arm detector bounds a `match` arm by the next arm naming the same enum, since Rust arms have no `case` label to scan for. And it resolves `use path::Enum as Alias;` the way the GUI resolves C++ `using` aliases, plus rejects `use path::Enum::*;` outright — a Rust rename leaves no trace of the original spelling at the use site, and a variant glob would hide every later table from all three detectors.

That last point matters more here than in either C++ frontend, because after adoption the TUI names none of the seven enums anywhere in `src/` — `label()` resolves through the trait, so no type needs to be in scope. Every detector therefore runs over sources that mention nothing, and a broken detector would be indistinguishable from a compliant frontend. The Rust audit answers that with two self-tests that feed each detector a synthetic naming table and a synthetic non-table, proving it can both fire and stay quiet. A frontend porting this audit further should carry those across: the C++ versions do not have them, and their green is worth less for it.

`InfrastructureErrorStage` was the last surface still rendering a Vocabulary Token where prose belongs, and the TUI now renders its Display Label in both the status line and the failure overlay. Three stages change wording — `request validation`, `FormID database access`, `internal invariant validation` — and all three converge on what the CLI and the GUI already print, so this closes a divergence rather than opening one. The token still appears inside `InfrastructureError`'s own `Display`, which the run contract composes as `<token>: <message>`; that string is the error's stable rendering and is deliberately left alone.

Its coverage is the cautionary tale of this adoption in miniature. The TUI had one test naming an infrastructure stage, and it used `Intake` — whose token and label are the same word — so the suite stayed green for as long as the frontend printed identifiers. `every_infrastructure_stage_renders_its_display_label` replaces that with an exhaustive loop over `VARIANTS` whose load-bearing half is negative: for each stage where the two forms differ, it asserts the *token* is absent. An assertion that only checks the label is present passes just as happily against a frontend rendering both.

Test files are deliberately out of the audited set. They legitimately quote settled Display Labels, and `classic-cli/tests/test_scan_run_contract.cpp` keeps a table of Vocabulary Tokens, which are frozen manifest identifiers rather than prose. In the TUI that exclusion covers the sibling `*_tests.rs` modules, which the recursive listing skips by name.

A source audit is only half of what a frontend needs, and the GUI is the evidence. When it adopted these labels it was shipping six stale wordings, and its whole Qt suite was green over all six, because the only labels any test named were ones all three frontends already agreed about — the assertions were structurally incapable of catching the drift nearest to them. `classic-gui/tests/test_scanrunpresentation.cpp` therefore pins every variant of every enum the GUI renders a label for. A frontend adopting this contract should expect to add that coverage rather than assume its existing output assertions already carry it.

The scripted per-binding suites — `__test__/*.spec.ts` and `python-bindings/tests/test_*.py` — do quote a handful of settled Display Labels as literals. That is deliberate and narrow: neither language can see `VARIANTS`, so the exhaustive check has to live in the Rust sibling module, and what is left for these to prove is that the projection survives the binding boundary and that a settled wording reached it. Keep them to the wordings a ticket actually decided, and prefer comparing two surfaces to each other over quoting a literal where both publish the same vocabulary — as the Crash Log Scan Run suites do against their configuration counterparts.
