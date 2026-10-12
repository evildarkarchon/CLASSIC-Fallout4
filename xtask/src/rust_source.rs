//! `syn` helpers shared by the subcommands that read Rust source: the CXX
//! bridge parser (`cxx-bridge-gate`), the scan-run `rustEnums` inventory
//! (`scan-run-contract`) and the conformance vocabulary input hook.
//!
//! Line numbers come from `proc-macro2`'s `span-locations` feature, so they are
//! real 1-based source lines even though nothing here runs inside a proc macro.

use anyhow::Result;
use syn::{File, Item, ItemEnum};

/// Parses `source` as a Rust file. `display_path` is the repo-relative path
/// used in the error message.
///
/// # Errors
///
/// Fails with `<display_path>:<line>: cannot parse Rust source: <error>` when
/// the text is not valid Rust.
pub(crate) fn parse_file(display_path: &str, source: &str) -> Result<File> {
    syn::parse_file(source).map_err(|error| {
        let line = error.span().start().line;
        anyhow::anyhow!("{display_path}:{line}: cannot parse Rust source: {error}")
    })
}

/// Finds the first `enum` named `name` in `file`, searching inline modules
/// (`mod x { ... }`) depth-first in source order. Out-of-line modules live in
/// other files and are not followed.
pub(crate) fn find_enum<'a>(file: &'a File, name: &str) -> Option<&'a ItemEnum> {
    find_enum_in(&file.items, name)
}

fn find_enum_in<'a>(items: &'a [Item], name: &str) -> Option<&'a ItemEnum> {
    items.iter().find_map(|item| match item {
        Item::Enum(found) if found.ident == name => Some(found),
        Item::Mod(module) => module
            .content
            .as_ref()
            .and_then(|(_, nested)| find_enum_in(nested, name)),
        _ => None,
    })
}

#[cfg(test)]
#[path = "rust_source_tests.rs"]
mod tests;
