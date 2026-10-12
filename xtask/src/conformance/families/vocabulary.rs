//! Input hook for the vocabulary families: `config-vocabulary` and
//! `scan-run-vocabulary`.
//!
//! Each scenario exercises one public label resolver. Its input must be
//! exactly `{operation, tokens}`, where `tokens` is every token the Rust owner
//! declares, in variant order, followed by `not_a_real_token`. Only tokens are
//! read from Rust; the labels stay authored in the pack, so changing Rust
//! wording cannot silently regenerate a passing expectation.
//!
//! Tokens come from the `pub enum` variants and the literal
//! `Self::Variant => "token"` arms of `impl Vocabulary for <Enum> { fn as_str
//! }`. A delegating twin reuses its source enum's tokens for variants of the
//! same name, and a single unpaired variant may take the `None => CONST`
//! fallback's string constant.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{Value, json};
use syn::visit::Visit;

use super::{InputContext, issue};
use crate::RepoRoot;
use crate::conformance::Issue;

const CONFIG: &str = "business-logic/classic-config-core/src/installed_yaml_data.rs";
const SCAN: &str = "business-logic/classic-scanlog-core/src/scan_run/contract.rs";
const PUBLICATION: &str = "business-logic/classic-durable-publication/src/error.rs";

/// The token every resolver must reject.
const UNKNOWN: &str = "not_a_real_token";

/// One public resolver and the Rust enum that owns its tokens.
struct Operation {
    /// The resolver's public name, the scenario input `operation`.
    name: &'static str,
    /// The owning `pub enum`.
    symbol: &'static str,
    /// Repo-relative Rust source declaring the enum.
    source: &'static str,
    /// The source enum a delegating twin reuses: (source, symbol).
    delegate: Option<(&'static str, &'static str)>,
}

const fn op(name: &'static str, symbol: &'static str, source: &'static str) -> Operation {
    Operation {
        name,
        symbol,
        source,
        delegate: None,
    }
}

const fn twin(
    name: &'static str,
    symbol: &'static str,
    source: &'static str,
    delegate: (&'static str, &'static str),
) -> Operation {
    Operation {
        name,
        symbol,
        source,
        delegate: Some(delegate),
    }
}

const CONFIG_OPERATIONS: [Operation; 4] = [
    op("installed_yaml_data_provenance_label", "InstalledYamlDataProvenance", CONFIG),
    op("scan_run_installed_yaml_data_provenance_label", "InstalledYamlDataProvenance", CONFIG),
    op("installed_yaml_data_diagnostic_kind_label", "InstalledYamlDataDiagnosticKind", CONFIG),
    op("local_ignore_yaml_data_state_label", "LocalIgnoreYamlDataState", CONFIG),
];

const SCAN_OPERATIONS: [Operation; 6] = [
    twin(
        "scan_run_installed_yaml_data_diagnostic_kind_label",
        "InstalledYamlDataRunDiagnosticKind",
        SCAN,
        (CONFIG, "InstalledYamlDataDiagnosticKind"),
    ),
    twin(
        "scan_run_local_ignore_yaml_data_state_label",
        "LocalIgnoreRunState",
        SCAN,
        (CONFIG, "LocalIgnoreYamlDataState"),
    ),
    op("scan_run_log_disposition_label", "LogDisposition", SCAN),
    op("scan_run_log_failure_stage_label", "LogFailureStage", SCAN),
    op("scan_run_infrastructure_error_stage_label", "InfrastructureErrorStage", SCAN),
    twin(
        "scan_run_local_ignore_reset_failure_stage_label",
        "LocalIgnoreResetFailureStage",
        SCAN,
        (PUBLICATION, "PublicationStage"),
    ),
];

/// Checks that the pack exercises every resolver once with its source tokens.
pub(super) fn validate(context: &InputContext<'_>) -> Vec<Issue> {
    let operations: &[Operation] = if context.pack.family_id == "config-vocabulary" {
        &CONFIG_OPERATIONS
    } else {
        &SCAN_OPERATIONS
    };
    let mut issues = Vec::new();
    let mut by_name: BTreeMap<&str, usize> = BTreeMap::new();
    for (index, scenario) in context.pack.scenarios.iter().enumerate() {
        match scenario.input.get("operation").and_then(Value::as_str) {
            Some(name) if by_name.insert(name, index).is_none() => {}
            Some(name) => issues.push(issue(index, format!("resolver {name} is exercised more than once"))),
            None => issues.push(issue(index, "a vocabulary input must name its resolver operation")),
        }
    }
    let wanted: BTreeSet<&str> = operations.iter().map(|operation| operation.name).collect();
    let named: BTreeSet<&str> = by_name.keys().copied().collect();
    if named != wanted {
        issues.push(issue(
            0,
            format!("the pack must exercise every public resolver exactly once: expected {wanted:?}, found {named:?}"),
        ));
    }
    let mut sources = Sources::new(context.root);
    for operation in operations {
        let Some(&index) = by_name.get(operation.name) else { continue };
        match sources.tokens(operation) {
            Err(message) => issues.push(issue(index, message)),
            Ok(mut tokens) => {
                tokens.push(UNKNOWN.to_owned());
                let expected = json!({"operation": operation.name, "tokens": tokens});
                if Value::Object(context.pack.scenarios[index].input.clone()) != expected {
                    issues.push(issue(
                        index,
                        format!(
                            "{} input must be {{operation, tokens}} with the {} source tokens followed by {UNKNOWN}",
                            operation.name, operation.symbol
                        ),
                    ));
                }
            }
        }
    }
    issues
}

/// Parsed Rust sources, cached per path.
struct Sources<'a> {
    root: &'a RepoRoot,
    files: BTreeMap<&'static str, Result<syn::File, String>>,
}

impl<'a> Sources<'a> {
    fn new(root: &'a RepoRoot) -> Self {
        Self {
            root,
            files: BTreeMap::new(),
        }
    }

    fn file(&mut self, source: &'static str) -> Result<&syn::File, String> {
        let root = self.root;
        self.files
            .entry(source)
            .or_insert_with(|| {
                let text = std::fs::read_to_string(root.join(source))
                    .map_err(|error| format!("cannot read vocabulary source {source}: {error}"))?;
                crate::rust_source::parse_file(source, &text).map_err(|error| format!("{error:#}"))
            })
            .as_ref()
            .map_err(Clone::clone)
    }

    /// The operation's tokens in variant order, following its delegate.
    fn tokens(&mut self, operation: &Operation) -> Result<Vec<String>, String> {
        let delegated = match operation.delegate {
            Some((source, symbol)) => self.declared(source, symbol)?.tokens,
            None => BTreeMap::new(),
        };
        let owner = self.declared(operation.source, operation.symbol)?;
        let mut tokens: BTreeMap<String, String> = delegated
            .into_iter()
            .filter(|(variant, _)| owner.variants.contains(variant))
            .collect();
        tokens.extend(owner.tokens);
        let unpaired: Vec<&String> = owner.variants.iter().filter(|variant| !tokens.contains_key(*variant)).collect();
        if let ([variant], Some(constant)) = (unpaired.as_slice(), &owner.fallback) {
            let file = self.file(operation.source)?;
            if let Some(value) = string_const(file, constant) {
                tokens.insert((*variant).clone(), value);
            }
        }
        let complete = !owner.variants.is_empty()
            && owner.variants.iter().all(|variant| tokens.contains_key(variant))
            && tokens.len() == owner.variants.len();
        let distinct = tokens.values().collect::<BTreeSet<_>>().len() == tokens.len();
        if !complete || !distinct {
            return Err(format!(
                "vocabulary {} variants lack complete, unique source tokens in {}",
                operation.symbol, operation.source
            ));
        }
        Ok(owner.variants.iter().map(|variant| tokens[variant].clone()).collect())
    }

    /// The enum's variants and its `as_str` literal arms and fallback.
    fn declared(&mut self, source: &'static str, symbol: &str) -> Result<Declared, String> {
        let file = self.file(source)?;
        let variants: Vec<String> = crate::rust_source::find_enum(file, symbol)
            .filter(|item| matches!(item.vis, syn::Visibility::Public(_)))
            .map(|item| item.variants.iter().map(|variant| variant.ident.to_string()).collect())
            .ok_or_else(|| format!("vocabulary source {source} declares no `pub enum {symbol}`"))?;
        let as_str = file
            .items
            .iter()
            .find_map(|item| match item {
                syn::Item::Impl(item) if implements_vocabulary_for(item, symbol) => {
                    item.items.iter().find_map(|member| match member {
                        syn::ImplItem::Fn(function) if function.sig.ident == "as_str" => Some(function),
                        _ => None,
                    })
                }
                _ => None,
            })
            .ok_or_else(|| format!("vocabulary source {source} has no `impl Vocabulary for {symbol}` with `as_str`"))?;
        let mut arms = Arms::default();
        arms.visit_block(&as_str.block);
        Ok(Declared {
            variants,
            tokens: arms.tokens,
            fallback: arms.fallback,
        })
    }
}

/// What one vocabulary enum declares.
struct Declared {
    /// Variant names in declaration order.
    variants: Vec<String>,
    /// `Self::Variant => "token"` arms of `as_str`.
    tokens: BTreeMap<String, String>,
    /// The constant named by a `None => CONST` arm, if any.
    fallback: Option<String>,
}

/// Collects literal token arms and the `None` fallback from `as_str`.
#[derive(Default)]
struct Arms {
    tokens: BTreeMap<String, String>,
    fallback: Option<String>,
}

impl<'ast> Visit<'ast> for Arms {
    fn visit_arm(&mut self, arm: &'ast syn::Arm) {
        let body = match &*arm.body {
            syn::Expr::Lit(syn::ExprLit {
                lit: syn::Lit::Str(text),
                ..
            }) => Some(Body::Token(text.value())),
            syn::Expr::Path(path) => path.path.get_ident().map(|ident| Body::Constant(ident.to_string())),
            _ => None,
        };
        match (&arm.pat, body) {
            (syn::Pat::Path(pattern), Some(Body::Token(token))) => {
                let segments: Vec<String> = pattern.path.segments.iter().map(|s| s.ident.to_string()).collect();
                if let [first, variant] = segments.as_slice()
                    && first == "Self"
                {
                    self.tokens.insert(variant.clone(), token);
                }
            }
            (syn::Pat::Ident(pattern), Some(Body::Constant(constant))) if pattern.ident == "None" => {
                self.fallback = Some(constant);
            }
            _ => {}
        }
        syn::visit::visit_arm(self, arm);
    }
}

enum Body {
    Token(String),
    Constant(String),
}

/// Whether `item` is `impl Vocabulary for <symbol>`.
fn implements_vocabulary_for(item: &syn::ItemImpl, symbol: &str) -> bool {
    let trait_is_vocabulary = item
        .trait_
        .as_ref()
        .and_then(|(_, path, _)| path.segments.last())
        .is_some_and(|segment| segment.ident == "Vocabulary");
    let self_is_symbol = match &*item.self_ty {
        syn::Type::Path(path) => path.path.segments.last().is_some_and(|segment| segment.ident == symbol),
        _ => false,
    };
    trait_is_vocabulary && self_is_symbol
}

/// The value of a top-level `const NAME: &str = "..."`.
fn string_const(file: &syn::File, name: &str) -> Option<String> {
    file.items.iter().find_map(|item| match item {
        syn::Item::Const(item) if item.ident == name => match &*item.expr {
            syn::Expr::Lit(syn::ExprLit {
                lit: syn::Lit::Str(text),
                ..
            }) => Some(text.value()),
            _ => None,
        },
        _ => None,
    })
}
