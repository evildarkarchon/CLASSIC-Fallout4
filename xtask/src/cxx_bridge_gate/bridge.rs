//! `syn` model of the `#[cxx::bridge]` modules in one Rust source file.

use std::collections::BTreeSet;

use anyhow::{Context, Result, bail};
use syn::visit::Visit;
use syn::{Attribute, ForeignItem, Item, ItemMod, LitStr};

/// What kind of item a bridge export is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum ExportKind {
    /// An `extern "Rust"` function.
    Function,
    /// A shared struct.
    Struct,
    /// A shared enum.
    Enum,
    /// An `extern "Rust"` opaque `type`.
    Opaque,
}

impl ExportKind {
    pub(super) fn label(self) -> &'static str {
        match self {
            ExportKind::Function => "function",
            ExportKind::Struct => "struct",
            ExportKind::Enum => "enum",
            ExportKind::Opaque => "opaque type",
        }
    }
}

/// One Rust-side item a bridge exposes to C++.
#[derive(Debug, Clone)]
pub(super) struct Export {
    pub name: String,
    pub kind: ExportKind,
    /// 1-based line of the item's name in the bridge file.
    pub line: usize,
    /// Every path segment named by the item's signature (functions) or field
    /// types (structs). Over-inclusive on purpose (`Vec`, `String`, ...): only
    /// names that match a type in the same bridge matter.
    pub mentions: BTreeSet<String>,
}

/// One `#[cxx::bridge]` module.
#[derive(Debug, Clone)]
pub(super) struct Bridge {
    /// The attribute's `namespace = "..."` value, e.g. `classic::scanner`.
    pub namespace: String,
    /// Rust-side exports (`extern "Rust"` items and shared types).
    pub exports: Vec<Export>,
    /// Type names mentioned by `extern "C++"` function signatures. The C++
    /// items themselves are not exports (frontends implement them and the
    /// compiler enforces them), but the shared types their signatures carry
    /// are needed by production, so they are reachability roots.
    pub cxx_roots: BTreeSet<String>,
}

/// Parses `source` (the file at repo-relative `display_path`) and returns every
/// `#[cxx::bridge]` module in it, including bridges nested in inline modules.
/// Text such as `#[cxx::bridge]` inside a doc comment is not an attribute and
/// is never matched.
///
/// # Errors
///
/// Fails when the file is not valid Rust or a bridge attribute has no
/// `namespace = "..."` argument.
pub(super) fn parse_bridges(display_path: &str, source: &str) -> Result<Vec<Bridge>> {
    let file = syn::parse_file(source).map_err(|error| {
        let line = error.span().start().line;
        anyhow::anyhow!("{display_path}:{line}: cannot parse Rust source: {error}")
    })?;
    let mut bridges = Vec::new();
    collect(&file.items, display_path, &mut bridges)?;
    Ok(bridges)
}

fn collect(items: &[Item], display_path: &str, bridges: &mut Vec<Bridge>) -> Result<()> {
    for item in items {
        let Item::Mod(module) = item else { continue };
        match module.attrs.iter().find(|attr| is_cxx_bridge(attr)) {
            Some(attr) => bridges.push(parse_bridge(module, attr, display_path)?),
            None => {
                if let Some((_, nested)) = &module.content {
                    collect(nested, display_path, bridges)?;
                }
            }
        }
    }
    Ok(())
}

fn is_cxx_bridge(attr: &Attribute) -> bool {
    let segments: Vec<String> = attr
        .path()
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    segments == ["cxx", "bridge"]
}

/// Reads `namespace = "..."` from the bridge attribute's arguments.
fn bridge_namespace(attr: &Attribute) -> syn::Result<Option<String>> {
    if matches!(attr.meta, syn::Meta::Path(_)) {
        return Ok(None);
    }
    let mut namespace = None;
    attr.parse_nested_meta(|meta| {
        if meta.path.is_ident("namespace") {
            namespace = Some(meta.value()?.parse::<LitStr>()?.value());
        } else if meta.input.peek(syn::Token![=]) {
            // Other cxx arguments are irrelevant here; consume their values.
            meta.value()?.parse::<syn::Expr>()?;
        }
        Ok(())
    })?;
    Ok(namespace)
}

fn parse_bridge(module: &ItemMod, attr: &Attribute, display_path: &str) -> Result<Bridge> {
    let line = module.ident.span().start().line;
    let namespace = bridge_namespace(attr)
        .with_context(|| format!("{display_path}:{line}: malformed #[cxx::bridge] arguments"))?;
    let Some(namespace) = namespace else {
        bail!(
            "{display_path}:{line}: #[cxx::bridge] module `{}` has no namespace = \"...\" argument",
            module.ident
        );
    };
    let mut bridge = Bridge {
        namespace,
        exports: Vec::new(),
        cxx_roots: BTreeSet::new(),
    };
    let Some((_, items)) = &module.content else {
        return Ok(bridge);
    };
    for item in items {
        match item {
            Item::ForeignMod(block) => {
                let is_rust = block
                    .abi
                    .name
                    .as_ref()
                    .is_some_and(|name| name.value() == "Rust");
                for foreign in &block.items {
                    match (foreign, is_rust) {
                        (ForeignItem::Fn(function), true) => bridge.exports.push(Export {
                            name: function.sig.ident.to_string(),
                            kind: ExportKind::Function,
                            line: function.sig.ident.span().start().line,
                            mentions: mentions(|visitor| visitor.visit_signature(&function.sig)),
                        }),
                        (ForeignItem::Type(opaque), true) => bridge.exports.push(Export {
                            name: opaque.ident.to_string(),
                            kind: ExportKind::Opaque,
                            line: opaque.ident.span().start().line,
                            mentions: BTreeSet::new(),
                        }),
                        (ForeignItem::Fn(function), false) => bridge
                            .cxx_roots
                            .extend(mentions(|visitor| visitor.visit_signature(&function.sig))),
                        _ => {}
                    }
                }
            }
            Item::Struct(shared) => bridge.exports.push(Export {
                name: shared.ident.to_string(),
                kind: ExportKind::Struct,
                line: shared.ident.span().start().line,
                mentions: mentions(|visitor| visitor.visit_fields(&shared.fields)),
            }),
            Item::Enum(shared) => bridge.exports.push(Export {
                name: shared.ident.to_string(),
                kind: ExportKind::Enum,
                line: shared.ident.span().start().line,
                mentions: BTreeSet::new(),
            }),
            _ => {}
        }
    }
    Ok(bridge)
}

/// Collects every path segment identifier the `walk` closure visits.
fn mentions(walk: impl FnOnce(&mut Mentions)) -> BTreeSet<String> {
    let mut visitor = Mentions::default();
    walk(&mut visitor);
    visitor.0
}

#[derive(Default)]
struct Mentions(BTreeSet<String>);

impl<'ast> Visit<'ast> for Mentions {
    fn visit_path_segment(&mut self, segment: &'ast syn::PathSegment) {
        self.0.insert(segment.ident.to_string());
        syn::visit::visit_path_segment(self, segment);
    }
}
