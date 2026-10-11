//! Never-exposed boundary for the opaque `StringMap` / `StringVecMap` types.
//!
//! The bridge hands these maps to C++ strictly read-only: C++ may receive a
//! `&StringMap` / `&StringVecMap` and query it, but no `#[cxx::bridge]` in this
//! crate may expose
//!
//! - a **producer** (any bridge function returning one, boxed or not),
//! - a **mutator** (any parameter other than a shared `&StringMap`, e.g.
//!   `&mut`, `Pin<&mut ..>`, `Box<..>`), or
//! - an **alias** (a `type X = ..;` re-declaration, an `extern "C++"`
//!   reference, a shared struct field, or an `impl Box<StringMap> {}`).
//!
//! The CXX bridge gate only rejects exports with no production caller, so a
//! frontend that started calling a new mutator would pass it; this test is the
//! separate guard (ADR-0010, #297). It replaces the Python
//! `cxx_opaque_map_reachability.py` proof and deliberately does not pin the
//! accessor count: the size of the surface belongs to the bridge gate.

use proc_macro2::{TokenStream, TokenTree};
use quote::ToTokens;
use std::path::{Path, PathBuf};
use syn::{FnArg, ForeignItem, Item, ReturnType, Type};

/// The opaque map type names that must stay read-only across the bridge.
const OPAQUE_MAPS: [&str; 2] = ["StringMap", "StringVecMap"];

/// Counts identifier tokens naming an opaque map anywhere inside `tokens`,
/// descending into delimited groups. Doc comments arrive as string literals and
/// so never count.
fn opaque_mentions(tokens: TokenStream) -> usize {
    tokens
        .into_iter()
        .map(|tree| match tree {
            TokenTree::Ident(ident) => usize::from(OPAQUE_MAPS.iter().any(|name| ident == name)),
            TokenTree::Group(group) => opaque_mentions(group.stream()),
            TokenTree::Punct(_) | TokenTree::Literal(_) => 0,
        })
        .sum()
}

/// Whether `ty` is exactly a shared reference to an opaque map (`&StringMap`,
/// optionally with a lifetime), the one parameter shape C++ may receive.
fn is_shared_opaque_ref(ty: &Type) -> bool {
    let Type::Reference(reference) = ty else {
        return false;
    };
    if reference.mutability.is_some() {
        return false;
    }
    let Type::Path(path) = reference.elem.as_ref() else {
        return false;
    };
    path.qself.is_none()
        && path.path.segments.len() == 1
        && path.path.segments[0].arguments.is_none()
        && OPAQUE_MAPS
            .iter()
            .any(|name| path.path.segments[0].ident == name)
}

/// Whether `module` carries a `#[cxx::bridge]` (or `#[cxx::bridge(..)]`)
/// attribute.
fn is_cxx_bridge(module: &syn::ItemMod) -> bool {
    module.attrs.iter().any(|attr| {
        let segments: Vec<String> = attr
            .path()
            .segments
            .iter()
            .map(|segment| segment.ident.to_string())
            .collect();
        segments == ["cxx", "bridge"]
    })
}

/// Checks one `extern "Rust"` item, returning a finding when it mentions an
/// opaque map in any position other than an unaliased `type StringMap;` or a
/// `&StringMap` parameter.
fn check_extern_rust_item(item: &ForeignItem) -> Option<String> {
    match item {
        ForeignItem::Type(ty) => {
            // `type StringMap;` is the opaque declaration itself; anything with
            // generics or a different name is not an opaque map mention.
            let mentions = opaque_mentions(ty.to_token_stream());
            let declared = usize::from(OPAQUE_MAPS.iter().any(|name| ty.ident == name));
            (mentions > declared).then(|| format!("alias: `type {}`", ty.ident))
        }
        ForeignItem::Fn(function) => {
            let name = &function.sig.ident;
            if let ReturnType::Type(_, output) = &function.sig.output
                && opaque_mentions(output.to_token_stream()) > 0
            {
                return Some(format!("producer: `fn {name}` returns an opaque map"));
            }
            let mutating = function.sig.inputs.iter().any(|input| match input {
                FnArg::Typed(arg) => {
                    opaque_mentions(arg.ty.to_token_stream()) > 0 && !is_shared_opaque_ref(&arg.ty)
                }
                FnArg::Receiver(receiver) => {
                    opaque_mentions(receiver.ty.to_token_stream()) > 0
                        && !is_shared_opaque_ref(&receiver.ty)
                }
            });
            mutating.then(|| {
                format!("mutator: `fn {name}` takes an opaque map other than by shared reference")
            })
        }
        // `type StringMap = crate::types::StringMap;` and other unparsed CXX
        // forms land here.
        other => (opaque_mentions(other.to_token_stream()) > 0)
            .then(|| "alias: re-declared opaque map in an `extern \"Rust\"` block".to_string()),
    }
}

/// Collects opaque-map findings for every `#[cxx::bridge]` module in one Rust
/// source text. `label` prefixes each finding. Returns `(bridges_seen,
/// findings)` so callers can tell an empty scan from a clean one.
fn check_source(label: &str, source: &str) -> (usize, Vec<String>) {
    let file = syn::parse_file(source).unwrap_or_else(|error| panic!("{label}: {error}"));
    let mut bridges = 0;
    let mut findings = Vec::new();
    let mut pending: Vec<&Item> = file.items.iter().collect();
    while let Some(item) = pending.pop() {
        let Item::Mod(module) = item else {
            continue;
        };
        let Some((_, content)) = &module.content else {
            continue;
        };
        if !is_cxx_bridge(module) {
            pending.extend(content.iter());
            continue;
        }
        bridges += 1;
        for bridge_item in content {
            match bridge_item {
                Item::ForeignMod(block) => {
                    let abi = block.abi.name.as_ref().map(syn::LitStr::value);
                    for foreign in &block.items {
                        let finding = if abi.as_deref() == Some("Rust") {
                            check_extern_rust_item(foreign)
                        } else {
                            (opaque_mentions(foreign.to_token_stream()) > 0).then(|| {
                                "alias: opaque map referenced from an `extern \"C++\"` block"
                                    .to_string()
                            })
                        };
                        findings.extend(finding.map(|finding| format!("{label}: {finding}")));
                    }
                }
                other if opaque_mentions(other.to_token_stream()) > 0 => findings.push(format!(
                    "{label}: alias: opaque map referenced by a shared item or impl in the bridge"
                )),
                _ => {}
            }
        }
    }
    (bridges, findings)
}

/// Production `.rs` sources of this crate, excluding sibling `*_tests.rs`
/// modules, which never compile into the bridge.
fn production_sources(dir: &Path, out: &mut Vec<PathBuf>) {
    for entry in std::fs::read_dir(dir).expect("read src dir") {
        let path = entry.expect("dir entry").path();
        if path.is_dir() {
            production_sources(&path, out);
        } else if path.extension().is_some_and(|ext| ext == "rs")
            && !path
                .file_stem()
                .is_some_and(|stem| stem.to_string_lossy().ends_with("_tests"))
        {
            out.push(path);
        }
    }
}

#[test]
fn opaque_maps_have_no_producer_mutator_or_alias_across_the_bridge() {
    let src = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut sources = Vec::new();
    production_sources(&src, &mut sources);
    sources.sort();

    let mut bridges = 0;
    let mut findings = Vec::new();
    for path in &sources {
        let text = std::fs::read_to_string(path).expect("read source");
        let label = path
            .strip_prefix(env!("CARGO_MANIFEST_DIR"))
            .unwrap_or(path)
            .display()
            .to_string()
            .replace('\\', "/");
        let (seen, mut found) = check_source(&label, &text);
        bridges += seen;
        findings.append(&mut found);
    }

    // Guards against a parse or discovery regression that would make the scan
    // pass vacuously.
    assert!(
        bridges > 0,
        "no #[cxx::bridge] modules found under {}",
        src.display()
    );
    assert!(
        findings.is_empty(),
        "opaque map read-only boundary broken:\n{}",
        findings.join("\n")
    );
}

/// Wraps bridge `extern "Rust"` declarations in a minimal bridge module.
fn bridge(body: &str) -> String {
    format!(
        "#[cxx::bridge(namespace = \"classic::types\")]\nmod ffi {{\n    extern \"Rust\" {{\n        type StringMap;\n        type StringVecMap;\n{body}\n    }}\n}}\n"
    )
}

#[test]
fn read_only_accessors_pass() {
    let source = bridge(
        "        fn string_map_get(map: &StringMap, key: &str) -> String;\n        fn string_vec_map_len<'a>(map: &'a StringVecMap) -> usize;",
    );
    assert_eq!(check_source("fixture.rs", &source), (1, Vec::new()));
}

#[test]
fn seeded_violations_are_each_reported() {
    let cases = [
        (
            bridge("        fn string_map_new() -> Box<StringMap>;"),
            "fixture.rs: producer: `fn string_map_new` returns an opaque map",
        ),
        (
            bridge("        fn string_vec_map_ref(key: &str) -> &'static StringVecMap;"),
            "fixture.rs: producer: `fn string_vec_map_ref` returns an opaque map",
        ),
        (
            bridge("        fn string_map_insert(map: &mut StringMap, key: &str, value: &str);"),
            "fixture.rs: mutator: `fn string_map_insert` takes an opaque map other than by shared reference",
        ),
        (
            bridge("        fn string_map_take(map: Box<StringMap>);"),
            "fixture.rs: mutator: `fn string_map_take` takes an opaque map other than by shared reference",
        ),
        (
            "#[cxx::bridge]\nmod ffi {\n    unsafe extern \"C++\" {\n        type StringMap = crate::types::StringMap;\n    }\n}\n"
                .to_string(),
            "fixture.rs: alias: opaque map referenced from an `extern \"C++\"` block",
        ),
        (
            "#[cxx::bridge]\nmod ffi {\n    extern \"Rust\" {\n        type StringMap;\n    }\n    impl Box<StringMap> {}\n}\n"
                .to_string(),
            "fixture.rs: alias: opaque map referenced by a shared item or impl in the bridge",
        ),
    ];
    for (source, expected) in cases {
        let (_, findings) = check_source("fixture.rs", &source);
        assert_eq!(findings, vec![expected.to_string()], "source:\n{source}");
    }
}

#[test]
fn opaque_maps_outside_a_bridge_are_not_bridge_exposure() {
    // Rust-side constructors such as `StringMap::new` are crate API, not
    // something C++ can call; only `#[cxx::bridge]` modules are inspected.
    let source =
        "pub fn build() -> Box<StringMap> { todo!() }\nmod inner { fn f(m: &mut StringMap) {} }\n";
    assert_eq!(check_source("fixture.rs", source), (0, Vec::new()));
}
