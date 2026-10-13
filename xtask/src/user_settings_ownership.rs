//! `cargo xtask user-settings-ownership`: User Settings has exactly one Rust
//! owner, `business-logic/classic-user-settings-core`.
//!
//! The gate reads production `.rs`, `.cpp`, `.h` and `.hpp` files under the
//! surviving source roots ([`SOURCE_ROOTS`]). It skips test, build and
//! dependency directories ([`EXCLUDED_DIRS`], plus directories named
//! `install*` or `build-*`) and `*_tests.rs` sibling test modules. `xtask/`
//! is not a source root, so this gate never audits its own patterns.
//!
//! Comments are blanked before matching (C++ through
//! [`crate::cpp_source::blank_comments`], Rust through a small local lexer),
//! but string literals are kept: the banned patterns include string keys
//! such as `"CLASSIC_Settings"`. Rules:
//!
//! - `legacy-user-settings-type`: a `struct`/`enum`/`type`/`trait` named
//!   `ClassicConfig` or `PathConfig` anywhere, owner included; outside the
//!   owner, any mention of either name.
//! - `legacy-generic-settings-owner`: a generic YAML enum (`YamlSource`,
//!   `CoreYamlSource`, `YamlFile`, `CoreYamlFile`) declaring a `Settings`
//!   variant anywhere; outside the owner, `<that enum>::Settings`,
//!   `SETTINGS_IGNORE_NONE` or `must_not_be_none`.
//! - `raw-user-settings-key`: `CLASSIC_Settings` outside the owner.
//! - `compatibility-mirror-runtime-use`: `"default_settings"` /
//!   `'default_settings'` or `CLASSIC_Info.default_settings` anywhere except
//!   the mirror generator (`src/bin/generate-user-settings-default-mirror`),
//!   so the owner too must bootstrap from its Rust registry.
//!
//! Each finding's message is the offending code line with comments removed.
//! One line may trip several rules; identical findings are reported once.

use std::sync::LazyLock;

use anyhow::{Context, Result};
use regex::Regex;

use crate::cpp_source::blank_comments;
use crate::{Finding, Outcome, RepoRoot};

/// Repo-relative source roots the gate audits; every one must exist.
const SOURCE_ROOTS: [&str; 6] = [
    "foundation",
    "business-logic",
    "cpp-bindings",
    "classic-cli",
    "classic-gui",
    "ui-applications",
];
/// Audited source extensions.
const EXTENSIONS: [&str; 4] = ["rs", "cpp", "h", "hpp"];
/// Directory names whose whole subtree is test, build or dependency output.
const EXCLUDED_DIRS: [&str; 8] = [
    "target",
    "tests",
    "__test__",
    "__tests__",
    "node_modules",
    ".venv",
    "build",
    "dist",
];
/// Directory-name prefixes for build and install staging trees
/// (`build-msvc`, `installer-staging`, ...). Applied to directories only: a
/// file such as `installation_root.rs` is production code.
const EXCLUDED_DIR_PREFIXES: [&str; 2] = ["install", "build-"];
/// The User Settings owner crate, as a repo-relative path prefix.
const OWNER: &str = "business-logic/classic-user-settings-core/";
/// The compatibility-mirror generator, the only code that may read the mirror.
const MIRROR_GENERATOR: &str =
    "business-logic/classic-user-settings-core/src/bin/generate-user-settings-default-mirror/";

/// Compiles one of this module's fixed patterns.
fn pattern(source: &str) -> Regex {
    Regex::new(source).expect("ownership patterns are valid regexes")
}

/// Declarations matched over a whole file, owner included.
static STRUCTURAL_RULES: LazyLock<[(&str, Regex); 2]> = LazyLock::new(|| {
    [
        (
            "legacy-user-settings-type",
            pattern(r"\b(?:struct|enum|type|trait)\s+(?:ClassicConfig|PathConfig)\b"),
        ),
        (
            "legacy-generic-settings-owner",
            // `[^{]*` and `[^}]*` span newlines, so a multi-line enum body is
            // matched as one declaration.
            pattern(
                r"\benum\s+(?:YamlSource|CoreYamlSource|YamlFile|CoreYamlFile)\b[^{]*\{[^}]*\bSettings\b",
            ),
        ),
    ]
});

/// Per-line rules that apply outside the owner.
static OUTSIDE_OWNER_RULES: LazyLock<[(&str, Regex); 3]> = LazyLock::new(|| {
    [
        (
            "legacy-user-settings-type",
            pattern(r"\b(?:ClassicConfig|PathConfig)\b"),
        ),
        (
            "legacy-generic-settings-owner",
            pattern(
                r"(?:YamlSource|CoreYamlSource|YamlFile|CoreYamlFile)::Settings|\bSETTINGS_IGNORE_NONE\b|\bmust_not_be_none\b",
            ),
        ),
        ("raw-user-settings-key", pattern(r"\bCLASSIC_Settings\b")),
    ]
});

/// The per-line rule that applies everywhere except the mirror generator.
static MIRROR_RULE: LazyLock<(&str, Regex)> = LazyLock::new(|| {
    (
        "compatibility-mirror-runtime-use",
        pattern(r#"["']default_settings["']|\bCLASSIC_Info\.default_settings\b"#),
    )
});

/// Arguments for `user-settings-ownership` (none today).
#[derive(Debug, Default, Clone, clap::Args)]
pub struct Args {}

/// Runs the ownership audit over the repository at `root`.
///
/// Returns `Outcome::Fail` with every finding (see the module docs for the
/// rules), or `Outcome::Pass` naming how many production files were audited.
///
/// # Errors
///
/// Fails when a source root is missing or a file cannot be read; the gate
/// must not pass over a tree it could not inspect.
pub fn run(root: &RepoRoot, _args: Args) -> Result<Outcome> {
    let mut findings = Vec::new();
    let mut audited = 0;
    for source_root in SOURCE_ROOTS {
        for path in root.walk_files_pruned(source_root, &EXTENSIONS, is_excluded_dir)? {
            let relative = root.relative(&path);
            if relative.ends_with("_tests.rs") {
                continue;
            }
            let bytes = std::fs::read(&path).with_context(|| format!("reading {relative}"))?;
            let source = String::from_utf8_lossy(&bytes);
            let code = if relative.ends_with(".rs") {
                blank_rust_comments(&source)
            } else {
                blank_comments(&source)
            };
            findings.extend(audit_file(&relative, &code));
            audited += 1;
        }
    }
    findings.sort();
    findings.dedup();
    let count = findings.len();
    Ok(Outcome::from_findings(
        findings,
        format!(
            "user-settings-ownership: User Settings has one owner ({audited} production files audited)"
        ),
        format!("user-settings-ownership: {count} finding(s) ({audited} production files audited)"),
    ))
}

/// Whether the walk must not descend into a directory named `name`.
fn is_excluded_dir(name: &str) -> bool {
    EXCLUDED_DIRS.contains(&name)
        || EXCLUDED_DIR_PREFIXES
            .iter()
            .any(|prefix| name.starts_with(prefix))
}

/// Applies every rule that covers `relative` to its comment-blanked `code`.
fn audit_file(relative: &str, code: &str) -> Vec<Finding> {
    let lines: Vec<&str> = code.lines().collect();
    let finding = |line: usize, rule: &'static str| {
        Finding::new(relative, line, rule, lines[line - 1].trim().to_owned())
    };
    let mut findings = Vec::new();

    for (rule, regex) in STRUCTURAL_RULES.iter() {
        for found in regex.find_iter(code) {
            let line = code[..found.start()].matches('\n').count() + 1;
            findings.push(finding(line, rule));
        }
    }

    let mut line_rules: Vec<&(&'static str, Regex)> = Vec::new();
    if !relative.starts_with(OWNER) {
        line_rules.extend(OUTSIDE_OWNER_RULES.iter());
    }
    // The generator is the only production code allowed to inspect the
    // checked-in mirror; the owner itself must bootstrap from its registry.
    if !relative.starts_with(MIRROR_GENERATOR) {
        line_rules.push(&MIRROR_RULE);
    }
    for (index, text) in lines.iter().enumerate() {
        for (rule, regex) in &line_rules {
            if regex.is_match(text) {
                findings.push(finding(index + 1, rule));
            }
        }
    }
    findings
}

/// Replaces every Rust comment in `source` with spaces, keeping newlines and
/// copying literals through unchanged.
///
/// Literals are lexed so that comment markers inside them do not start a
/// comment: `"..."` strings (which may span lines), raw strings
/// `r#"..."#` (also `br`/`cr`), and character literals, which are told apart
/// from lifetimes and labels (`'a`) by their closing quote. Block comments
/// nest, as in Rust. An unterminated literal runs to the end of the file.
fn blank_rust_comments(source: &str) -> String {
    let chars: Vec<char> = source.chars().collect();
    let at = |index: usize| chars.get(index).copied();
    let mut out = String::with_capacity(source.len());
    let blank =
        |out: &mut String, ch: char| out.push(if ch == '\n' || ch == '\r' { ch } else { ' ' });
    let mut i = 0;
    while i < chars.len() {
        let ch = chars[i];
        if ch == '/' && at(i + 1) == Some('/') {
            while i < chars.len() && chars[i] != '\n' {
                blank(&mut out, chars[i]);
                i += 1;
            }
        } else if ch == '/' && at(i + 1) == Some('*') {
            let mut depth = 0usize;
            while i < chars.len() {
                if chars[i] == '/' && at(i + 1) == Some('*') {
                    depth += 1;
                    out.push_str("  ");
                    i += 2;
                } else if chars[i] == '*' && at(i + 1) == Some('/') {
                    depth -= 1;
                    out.push_str("  ");
                    i += 2;
                    if depth == 0 {
                        break;
                    }
                } else {
                    blank(&mut out, chars[i]);
                    i += 1;
                }
            }
        } else if ch.is_alphabetic() || ch == '_' {
            let start = i;
            while i < chars.len() && (chars[i].is_alphanumeric() || chars[i] == '_') {
                i += 1;
            }
            let word: String = chars[start..i].iter().collect();
            out.push_str(&word);
            if matches!(word.as_str(), "r" | "br" | "cr") {
                let mut hashes = 0;
                while at(i + hashes) == Some('#') {
                    hashes += 1;
                }
                if at(i + hashes) == Some('"') {
                    // Raw string: it ends at a `"` followed by as many `#`.
                    let mut j = i + hashes + 1;
                    while j < chars.len()
                        && !(chars[j] == '"' && (1..=hashes).all(|k| at(j + k) == Some('#')))
                    {
                        j += 1;
                    }
                    let end = (j + 1 + hashes).min(chars.len());
                    out.extend(&chars[i..end]);
                    i = end;
                }
            }
        } else if ch == '"' {
            let mut j = i + 1;
            while j < chars.len() && chars[j] != '"' {
                j += if chars[j] == '\\' { 2 } else { 1 };
            }
            let end = (j + 1).min(chars.len());
            out.extend(&chars[i..end]);
            i = end;
        } else if ch == '\'' && (at(i + 1) == Some('\\') || at(i + 2) == Some('\'')) {
            // `'x'` or an escape such as `'\n'` / `'\u{1F600}'`; a lone `'`
            // (lifetime or label) is ordinary punctuation.
            let mut j = i + 1;
            if at(j) == Some('\\') {
                j += 2;
            } else {
                j += 1;
            }
            while j < chars.len() && chars[j] != '\'' && chars[j] != '\n' {
                j += 1;
            }
            let end = (j + 1).min(chars.len());
            out.extend(&chars[i..end]);
            i = end;
        } else {
            out.push(ch);
            i += 1;
        }
    }
    out
}
