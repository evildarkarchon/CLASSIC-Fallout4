//! `cargo xtask cxx-bridge-gate`: every CXX bridge export must have a
//! production caller.
//!
//! The gate checks one direction only, no orphan exports; a frontend calling a
//! missing export is already caught by the CLI and GUI builds.
//!
//! - Every `#[cxx::bridge]` module under `cpp-bindings/classic-cpp-bridge/src`
//!   is parsed with `syn`. Its namespace comes from the attribute's
//!   `namespace = "..."` argument, never from the file name.
//! - A function export survives when a `.cpp`/`.h`/`.hpp` file under
//!   `classic-cli/src` or `classic-gui/src` names it as
//!   `classic::<module>::name`, or as `<alias>::name` after
//!   `namespace <alias> = classic::<module>;` in the same file. Comments and
//!   string literals are blanked first. Tests, benches and conformance runners
//!   live outside those `src` trees and never count.
//! - A struct, enum or opaque type survives only when a surviving function's
//!   signature, or a field of a surviving struct, reaches it. Naming a type in
//!   frontend code does not keep it. `extern "C++"` items are not exports, but
//!   the types in their signatures are reachability roots.
//! - Any other reference to a bridge namespace (`using namespace`, `using`
//!   declarations, aliases of aliases, relative `<module>::name` lookup) fails
//!   as an unsupported reference form, so the matcher never silently misses a
//!   caller.
//!
//! There is no baseline and no waiver list. Per-item `cxx_name`/`namespace`
//! overrides and methods are not modelled; such an export is reported as an
//! orphan (fail closed) until the matcher is widened in a reviewed change.

use std::collections::{BTreeSet, HashMap, HashSet};

use anyhow::{Context, Result, bail};

use crate::{Finding, Outcome, RepoRoot};

mod bridge;
mod cpp;

use bridge::{Bridge, ExportKind};

/// Repo-relative source directory of the CXX bridge crate.
const BRIDGE_SRC: &str = "cpp-bindings/classic-cpp-bridge/src";
/// Repo-relative production source trees whose references count as callers.
const FRONTEND_SRCS: [&str; 2] = ["classic-cli/src", "classic-gui/src"];
/// C++ source extensions the caller matcher reads.
const CPP_EXTENSIONS: [&str; 3] = ["cpp", "h", "hpp"];

/// Arguments for `cxx-bridge-gate` (none today).
#[derive(Debug, Default, Clone, clap::Args)]
pub struct Args {}

/// A parsed bridge plus the repo-relative file it came from.
struct LocatedBridge {
    file: String,
    bridge: Bridge,
}

/// Runs the gate over the repository at `root`.
///
/// Returns `Outcome::Fail` with one `orphan-export` finding per export that
/// has no production caller (pointing at the export in the bridge source) and
/// one `unsupported-reference-form` finding per refused reference (pointing at
/// the frontend source).
///
/// # Errors
///
/// Fails when a required directory is missing, a file cannot be read, a
/// bridge file does not parse, a bridge has no namespace, or no bridge is
/// found at all.
pub fn run(root: &RepoRoot, _args: Args) -> Result<Outcome> {
    let bridges = load_bridges(root)?;
    let namespaces: Vec<String> = bridges
        .iter()
        .map(|located| located.bridge.namespace.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    let namespace_segments: Vec<Vec<String>> = namespaces
        .iter()
        .map(|namespace| namespace.split("::").map(str::to_owned).collect())
        .collect();

    let mut findings = Vec::new();
    let mut called: HashSet<(String, String)> = HashSet::new();
    let mut files_scanned = 0;
    for dir in FRONTEND_SRCS {
        for path in root.walk_files(dir, &CPP_EXTENSIONS)? {
            let bytes = std::fs::read(&path)
                .with_context(|| format!("reading {}", root.relative(&path)))?;
            let scan = cpp::scan(&String::from_utf8_lossy(&bytes), &namespace_segments);
            files_scanned += 1;
            for reference in scan.references {
                called.insert((namespaces[reference.namespace].clone(), reference.name));
            }
            for unsupported in scan.unsupported {
                findings.push(Finding::new(
                    root.relative(&path),
                    unsupported.line,
                    "unsupported-reference-form",
                    format!(
                        "unsupported reference form `{}`; reference bridge exports only as \
                         classic::<module>::name or <alias>::name with `namespace <alias> = classic::<module>;`",
                        unsupported.form
                    ),
                ));
            }
        }
    }
    let unsupported_count = findings.len();

    let mut export_count = 0;
    for located in &bridges {
        export_count += located.bridge.exports.len();
        findings.extend(orphans(located, &called));
    }
    let orphan_count = findings.len() - unsupported_count;

    let scope = format!(
        "{export_count} exports in {} bridge modules, {files_scanned} frontend files scanned",
        bridges.len()
    );
    Ok(Outcome::from_findings(
        findings,
        format!("cxx-bridge-gate: every export has a production caller ({scope})"),
        format!(
            "cxx-bridge-gate: {orphan_count} orphan export(s), {unsupported_count} unsupported reference form(s) ({scope})"
        ),
    ))
}

/// Parses every `#[cxx::bridge]` module under [`BRIDGE_SRC`].
fn load_bridges(root: &RepoRoot) -> Result<Vec<LocatedBridge>> {
    let mut bridges = Vec::new();
    for path in root.walk_files(BRIDGE_SRC, &["rs"])? {
        let file = root.relative(&path);
        let source = std::fs::read_to_string(&path).with_context(|| format!("reading {file}"))?;
        for bridge in bridge::parse_bridges(&file, &source)? {
            bridges.push(LocatedBridge {
                file: file.clone(),
                bridge,
            });
        }
    }
    if bridges.is_empty() {
        bail!("no #[cxx::bridge] modules found under {BRIDGE_SRC}");
    }
    Ok(bridges)
}

/// Returns an `orphan-export` finding for every export of `located` that has no
/// production caller: functions not in `called`, and types not reachable from
/// a surviving function or an `extern "C++"` signature.
fn orphans(located: &LocatedBridge, called: &HashSet<(String, String)>) -> Vec<Finding> {
    let bridge = &located.bridge;
    let types: HashMap<&str, &bridge::Export> = bridge
        .exports
        .iter()
        .filter(|export| export.kind != ExportKind::Function)
        .map(|export| (export.name.as_str(), export))
        .collect();
    let survives = |name: &str| called.contains(&(bridge.namespace.clone(), name.to_owned()));

    // Breadth-first walk from surviving signatures through struct fields.
    let mut pending: Vec<&str> = bridge
        .exports
        .iter()
        .filter(|export| export.kind == ExportKind::Function && survives(&export.name))
        .flat_map(|export| export.mentions.iter().map(String::as_str))
        .chain(bridge.cxx_roots.iter().map(String::as_str))
        .collect();
    let mut reachable: HashSet<&str> = HashSet::new();
    while let Some(name) = pending.pop() {
        let Some(export) = types.get(name) else {
            continue;
        };
        if reachable.insert(export.name.as_str()) {
            pending.extend(export.mentions.iter().map(String::as_str));
        }
    }

    bridge
        .exports
        .iter()
        .filter_map(|export| {
            let qualified = format!("{}::{}", bridge.namespace, export.name);
            let message = match export.kind {
                ExportKind::Function if !survives(&export.name) => format!(
                    "function {qualified} has no caller in {}",
                    FRONTEND_SRCS.join(" or ")
                ),
                ExportKind::Function => return None,
                kind if !reachable.contains(export.name.as_str()) => format!(
                    "{} {qualified} is not reachable from any surviving function",
                    kind.label()
                ),
                _ => return None,
            };
            Some(Finding::new(
                located.file.clone(),
                export.line,
                "orphan-export",
                message,
            ))
        })
        .collect()
}
