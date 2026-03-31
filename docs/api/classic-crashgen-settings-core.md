# `classic-crashgen-settings-core` API Guide

Contributor-facing API documentation for [`ClassicLib-rs/business-logic/classic-crashgen-settings-core/`](../../ClassicLib-rs/business-logic/classic-crashgen-settings-core).

Crate metadata:

- Crate: `classic-crashgen-settings-core`
- Description: `Shared crashgen settings rule model and evaluator`

This crate defines the shared Rust rule model used for crashgen settings validation and exposes the core evaluator that higher layers call.

It is a pure Rust business-logic crate. It does not own YAML loading, report formatting policy, a UI surface, FFI, or a Tokio runtime.

Reference: [`AGENTS.md`](../../AGENTS.md).

---

## Purpose And Scope

Use this crate when you need to:

- represent crashgen settings rules as typed Rust data
- evaluate those rules against installed plugins, flattened settings, config layout facts, and optional crashgen version data
- share one rule model across config loading, scanlog analysis, TOML/config validation, and bindings
- build or transform `CrashgenSettingsRules` values in tests, registry builders, or binding adapters

Do not use this crate for:

- parsing YAML files directly
- reading TOML or INI files directly
- formatting final autoscan reports for end users
- deciding game-version family ownership for scan-time config building
- creating or owning a Tokio runtime

Those concerns live in related crates such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core), [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core), and [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core).

---

## Module And API Map

This crate has a single public module: `src/lib.rs`.

The whole public API is defined there.

## Rule model types

- `CrashgenSettingsRules` - top-level rules block with `version`, `preflight`, and `checks`
- `PreflightRule` and `PreflightAction` - early rules that emit notices/issues before setting checks run
- `CheckRule` - one setting expectation with target metadata, predicate, and messages
- `RuleTarget` - section/key/value-type metadata for a setting check
- `RuleMessages` - fail/fix/pass message templates
- `Predicate` - condition tree used by both preflight and check rules
- `ExpectedValue` and `TargetValueType` - typed expectation model

## Evaluation types

- `EvaluationContext` - caller-provided facts used during evaluation
- `EvaluationOutcome` - one emitted notice, issue, or success
- `EvaluationResult` - ordered outcomes plus `skip_remaining`
- `OutcomeKind` - `Notice`, `Issue`, or `Success`

## Supporting enums

- `RuleSeverity` - `Info`, `Warning`, `Error`
- `PreflightActionKind` - `NoticeAndSkipRemaining`, `Notice`, `Issue`
- `ConfigLayout` - `Og`, `Vr`, `Unknown`

## Main function

- `evaluate_rules(rules, context) -> EvaluationResult`

---

## Public API Surface

## `CrashgenSettingsRules`

`CrashgenSettingsRules` is the top-level model shared between config loading and validation layers.

Fields:

- `version: u32`
- `preflight: Vec<PreflightRule>`
- `checks: Vec<CheckRule>`

The crate itself does not interpret `version` beyond storing it. Today it is mainly schema metadata carried from upstream loaders.

## `Predicate`

`Predicate` is the condition tree used to decide whether a rule applies.

Variants:

- `Always`
- `PluginAny(Vec<String>)`
- `ConfigLayoutIs(ConfigLayout)`
- `CrashgenVersionLt((u32, u32, u32))`
- `All(Vec<Predicate>)`
- `Any(Vec<Predicate>)`
- `Not(Box<Predicate>)`

Behavior worth knowing from the source:

- `PluginAny` compares against `EvaluationContext.installed_plugins` after trimming and lowercasing the predicate entries at evaluation time
- `ConfigLayoutIs` is strict equality against the caller-provided `ConfigLayout`
- `CrashgenVersionLt` returns `true` when `crashgen_version` is `None`; the implementation uses `Option::is_none_or(...)`
- `All`, `Any`, and `Not` compose recursively

## `EvaluationContext`

`EvaluationContext` is the only input to the evaluator besides the rules.

Fields:

- `crashgen_name: String`
- `display_section: String`
- `installed_plugins: HashSet<String>`
- `settings: HashMap<String, String>`
- `config_layout: ConfigLayout`
- `crashgen_version: Option<(u32, u32, u32)>`

Contributor notes:

- `installed_plugins` is expected to contain lowercase DLL/plugin names; downstream callers such as scanlog build it that way
- `settings` is a flattened key-to-value map; `evaluate_rules()` looks up by `RuleTarget.key` only
- `RuleTarget.section` is reported back in outcomes, but it is not used to look up the current value

That last point matters if a caller ever flattens two different sections that share the same key name.

## `PreflightRule` and `PreflightAction`

Preflight rules run before check rules.

Fields:

- `PreflightRule`: `id`, `when`, `action`
- `PreflightAction`: `kind`, `bucket`, `severity`, `message`, `fix`

`RuleReportBucket` meanings:

- `Settings` - default settings-related destination used by ordinary checks and preflight notices
- `ErrorInformation` - promoted destination for notices or issues that callers want to render under `Error Information`

`PreflightActionKind` meanings:

- `NoticeAndSkipRemaining` - emit a notice and stop before all remaining checks
- `Notice` - emit a notice and continue
- `Issue` - emit an issue and continue

## `CheckRule`

`CheckRule` models one expected setting value.

Fields:

- `id`
- `target: RuleTarget`
- `when: Predicate`
- `expect: ExpectedValue`
- `messages: RuleMessages`
- `severity: RuleSeverity`

Important behavior:

- a check rule only runs when its predicate is true
- if the target key is missing from `context.settings`, the rule is skipped silently
- a failed expectation emits an `Issue`
- a passing expectation emits a `Success` only when `messages.pass` is present

## `ExpectedValue`, `TargetValueType`, and value matching

Supported expected values:

- `ExpectedValue::Bool(bool)`
- `ExpectedValue::Int(i64)`
- `ExpectedValue::String(String)`

Supported target types:

- `TargetValueType::Bool`
- `TargetValueType::Int`
- `TargetValueType::String`

Matching behavior from `value_matches()`:

- bool parsing accepts `true/1/yes/on` and `false/0/no/off`
- int parsing trims and parses as `i64`
- string comparisons compare trimmed current values to the expected string
- if `target.value_type` and `expect` differ, the evaluator still falls back to matching on the `ExpectedValue` variant instead of erroring

## `EvaluationOutcome` and `EvaluationResult`

`EvaluationOutcome` is the emitted result unit.

Fields:

- `id`, `kind`, `bucket`, `severity`, `message`, `fix`
- `section`, `setting`, `expected`, `actual`

`EvaluationResult` contains:

- `outcomes: Vec<EvaluationOutcome>` in evaluation order
- `skip_remaining: bool`

There is no separate summary or error channel. Callers are expected to interpret `outcomes` directly.

## Parse helpers on enums

The crate exposes string parsers for several enums:

- `RuleSeverity::parse(&str) -> Option<RuleSeverity>`
- `ConfigLayout::parse(&str) -> Option<ConfigLayout>`
- `TargetValueType::parse(&str) -> Option<TargetValueType>`
- `PreflightActionKind::parse(&str) -> Option<PreflightActionKind>`
- `RuleReportBucket::parse(&str) -> Option<RuleReportBucket>`

These return `None` for unsupported strings. They are useful in loaders and binding adapters, but they do not report detailed parse errors.

---

## Rule Evaluation Flow

The source-visible evaluation order is:

1. Start with an empty `EvaluationResult`.
2. Evaluate all `preflight` rules in declaration order.
3. For each matching preflight rule:
   - render `message` and optional `fix`
   - emit a `Notice` or `Issue` outcome based on `PreflightActionKind`
   - copy `PreflightAction.bucket` into the emitted `EvaluationOutcome`
4. If a preflight action is `NoticeAndSkipRemaining`, set `skip_remaining = true` and return immediately.
5. Evaluate all `checks` in declaration order.
6. For each matching check rule:
   - look up `context.settings[rule.target.key]`
   - skip the rule if the key is absent
   - compare the current value to `expect`
   - emit an `Issue` on mismatch
   - emit a `Success` on match only when `messages.pass` exists
   - emit `RuleReportBucket::Settings` for those check outcomes
7. Return the ordered `EvaluationResult`.

Template rendering is intentionally small in scope. `apply_template()` only replaces:

- `{crashgen_name}`
- `{display_section}`
- `{setting}`

If `display_section` is empty, the evaluator substitutes `[Compatibility]`.

---

## Error Handling Model

This crate does not expose a dedicated error enum and `evaluate_rules()` is intentionally infallible.

Contributor-facing implications:

- enum parse helpers return `Option<_>`, not `Result<_>`
- malformed or incomplete rule YAML is expected to be filtered or defaulted by upstream loaders such as [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core)
- missing settings do not produce an evaluator error; the corresponding check is skipped
- unsupported template tokens remain unchanged because only three placeholders are recognized

If you need richer diagnostics for malformed rule definitions, that work belongs in the loader/binding layer rather than in this evaluator.

---

## Current Ownership Boundaries

This crate is shared infrastructure. It owns the typed rule model and evaluator, but not the higher-level meaning of every fact.

## `ConfigLayout`

`ConfigLayout` still includes `Vr`, and the evaluator fully supports `Predicate::ConfigLayoutIs(ConfigLayout::Vr)`.

Current source-backed usage differs by downstream crate:

- in [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core), `derive_scanlog_config_layout()` currently returns `Og` when a detected game version parses and `Unknown` otherwise; it does not use `Vr` as the primary OG/VR selector
- that means scanlog currently treats `ConfigLayout` mostly as a coarse valid/invalid fact for settings evaluation
- OG/VR selection for scanlog is handled earlier during Version Registry-backed config building, not inside this crate's evaluator
- in [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core), TOML validation still infers `Og` vs `Vr` from the config file path and passes that fact into `EvaluationContext`

So contributors should keep `Vr` support intact unless the downstream callers and rule schema are changed together.

## YAML ownership

The rule schema is consumed upstream, not here.

- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) parses `Crashgen_Registry.*.settings_rules` YAML into `CrashgenSettingsRules`
- Node and Python binding layers also convert their own transport shapes into the same core types
- this crate should stay focused on typed evaluation, not schema-specific file parsing

---

## Related Crates And Integration Points

- [`classic-config-core`](../../ClassicLib-rs/business-logic/classic-config-core) - loads `Crashgen_Registry` YAML and produces `CrashgenSettingsRules` inside `CrashgenEntryRaw`
- [`classic-scanlog-core`](../../ClassicLib-rs/business-logic/classic-scanlog-core) - uses `evaluate_rules()` inside `SettingsValidator` and falls back to legacy named checks for uncovered settings
- [`classic-scangame-core`](../../ClassicLib-rs/business-logic/classic-scangame-core) - reuses the same rule model for TOML/config scanning outside crash-log analysis
- [`classic-node`](../../ClassicLib-rs/node-bindings/classic-node) - maps JS-facing rule objects to and from these core types
- maintained Python bindings under [`ClassicLib-rs/python-bindings/`](../../ClassicLib-rs/python-bindings) - parse and serialize the same rule model for Python-facing workflows

In practice, this crate sits between rule-definition sources and report-producing consumers.

---

## Usage Example

This example matches the real public API: construct rules, provide an `EvaluationContext`, and call `evaluate_rules()`.

```rust
use classic_crashgen_settings_core::{
    CheckRule, ConfigLayout, CrashgenSettingsRules, EvaluationContext, ExpectedValue,
    Predicate, PreflightAction, PreflightActionKind, PreflightRule, RuleMessages,
    RuleSeverity, RuleTarget, TargetValueType, evaluate_rules,
};
use std::collections::{HashMap, HashSet};

let rules = CrashgenSettingsRules {
    version: 1,
    preflight: vec![PreflightRule {
        id: "addictol_skip".to_string(),
        when: Predicate::PluginAny(vec!["addictol.dll".to_string()]),
        action: PreflightAction {
            kind: PreflightActionKind::NoticeAndSkipRemaining,
            severity: RuleSeverity::Info,
            message: "Addictol detected - skipping {crashgen_name} checks".to_string(),
            fix: None,
        },
    }],
    checks: vec![CheckRule {
        id: "f4ee_enabled".to_string(),
        target: RuleTarget {
            section: "Compatibility".to_string(),
            key: "F4EE".to_string(),
            value_type: TargetValueType::Bool,
        },
        when: Predicate::PluginAny(vec!["f4ee.dll".to_string()]),
        expect: ExpectedValue::Bool(true),
        messages: RuleMessages {
            fail: "{setting} is disabled".to_string(),
            fix: Some("Enable the compatibility toggle.".to_string()),
            pass: Some("{setting} is enabled".to_string()),
        },
        severity: RuleSeverity::Warning,
    }],
};

let mut installed_plugins = HashSet::new();
installed_plugins.insert("f4ee.dll".to_string());

let mut settings = HashMap::new();
settings.insert("F4EE".to_string(), "false".to_string());

let context = EvaluationContext {
    crashgen_name: "Buffout 4".to_string(),
    display_section: "[Compatibility]".to_string(),
    installed_plugins,
    settings,
    config_layout: ConfigLayout::Og,
    crashgen_version: Some((1, 28, 6)),
};

let result = evaluate_rules(&rules, &context);

assert!(!result.skip_remaining);
assert_eq!(result.outcomes.len(), 1);
assert_eq!(result.outcomes[0].message, "F4EE is disabled");
assert_eq!(result.outcomes[0].expected.as_deref(), Some("true"));
assert_eq!(result.outcomes[0].actual.as_deref(), Some("false"));
```

The crate's own tests also show the preflight short-circuit path and pass/fail outcome behavior.

---

## Contributor Notes And Known Limits

- This crate's public surface is whatever stays `pub` in `src/lib.rs`; there are no facade modules or selective re-exports.
- The evaluator is synchronous and runtime-agnostic.
- `RuleTarget.section` is descriptive output metadata today, not part of the lookup key.
- `CrashgenVersionLt` treats a missing crashgen version as matching; if you change that, update downstream callers and docs together.
- Only `{crashgen_name}`, `{display_section}`, and `{setting}` are recognized in message templates.
- There is no built-in loader validation API; schema validation currently happens upstream.
- `classic-scanlog-core` still depends on this crate even though its current `ConfigLayout` use is mostly `Og` vs `Unknown`, not `Og` vs `Vr` selection.

If you extend this crate, update this document when you change:

- public types or enum variants in `src/lib.rs`
- predicate semantics or evaluation order
- value-coercion rules in `value_matches()`
- template placeholder behavior
- `ConfigLayout` ownership expectations across config, scanlog, and scangame layers
