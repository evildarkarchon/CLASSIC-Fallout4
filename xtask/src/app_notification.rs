//! `cargo xtask app-notification <step>`: the app-update notification
//! (`app-notification-v*`) publish tooling, run by
//! `.github/workflows/publish-app-notification.yml` and by the `xtask-linux`
//! CI job.
//!
//! Steps, in workflow order:
//!
//! - `validate`: the workflow tag is `app-notification-v<SEMVER>`, and the
//!   source `CLASSIC Data/app-notification.yaml` satisfies the notification
//!   rules the Rust client enforces (see `rules`).
//! - `manifest`: projects the source into `manifest.json` (byte-compatible
//!   with the retired Python tool: fixed key order, two-space indent,
//!   non-ASCII written as-is, LF, trailing newline). There is no `.sha256`.
//! - `verify-asset`: polls the release's `manifest.json` asset anonymously
//!   until it serves the staged bytes.
//! - `smoke-pages`: polls the GitHub Pages manifest until it serves the staged
//!   bytes.
//! - `dry-run`: runs the source-only steps above in-process against a
//!   localhost server, so a maintainer can rehearse a publish without a tag.
//!
//! The source is parsed with `yaml-rust2`'s `YamlLoader`, which keeps no node
//! positions: findings point at the line of the key they concern, found by a
//! text search, and otherwise at line 1. Messages keep the retired tool's
//! wording, including Python `repr` renderings of offending values.

pub mod dry_run;
pub mod manifest;
pub(crate) mod rules;
pub mod smoke_pages;
pub mod validate;
pub mod verify_asset;

use std::path::Path;

use anyhow::Result;
use clap::Subcommand;
use yaml_rust2::{Yaml, YamlLoader};

use crate::{Finding, Outcome, RepoRoot};

/// `cargo xtask app-notification` arguments.
#[derive(Debug, Clone, clap::Args)]
pub struct Args {
    /// The publish step to run.
    #[command(subcommand)]
    pub step: Step,
}

/// One app-notification publish step.
#[derive(Debug, Clone, Subcommand)]
pub enum Step {
    /// Validate the workflow tag and/or the app-notification.yaml source.
    Validate(validate::Args),
    /// Generate manifest.json from the app-notification.yaml source.
    Manifest(manifest::Args),
    /// Poll until the release's manifest.json asset is anonymously reachable
    /// (and, with --expected-body-path, serves the staged bytes).
    VerifyAsset(verify_asset::Args),
    /// Poll until the GitHub Pages manifest serves the staged manifest.json bytes.
    SmokePages(smoke_pages::Args),
    /// Rehearse the publish locally: validate, generate, then verify and
    /// smoke-test the staged bytes against a localhost server.
    DryRun(dry_run::Args),
}

/// Runs one step and discards its progress lines; see [`run_with_progress`].
///
/// # Errors
///
/// An operational failure (unwritable output, unreadable expected body,
/// a dry run whose tag timestamp cannot be resolved).
pub fn run(root: &RepoRoot, args: Args) -> Result<Outcome> {
    run_with_progress(root, args, &mut |_| {})
}

/// Runs one step. The polling steps report each retry, and `dry-run` each of
/// its numbered stages, through `progress`, one line per call; this module
/// never prints.
///
/// # Errors
///
/// An operational failure (unwritable output, unreadable expected body,
/// a dry run whose tag timestamp cannot be resolved).
pub fn run_with_progress(
    root: &RepoRoot,
    args: Args,
    progress: &mut dyn FnMut(&str),
) -> Result<Outcome> {
    match args.step {
        Step::Validate(args) => validate::run(root, args),
        Step::Manifest(args) => manifest::run(root, args),
        Step::VerifyAsset(args) => verify_asset::run(root, args, progress),
        Step::SmokePages(args) => smoke_pages::run(root, args, progress),
        Step::DryRun(args) => dry_run::run(root, args, progress),
    }
}

/// The parsed source document and its text (for locating lines).
struct Source {
    text: String,
    document: Yaml,
}

/// Reads and parses the source at `path`. A read or parse failure becomes an
/// `unreadable-source` / `unparseable-yaml` finding with the retired tool's
/// message. Duplicate mapping keys and multiple documents are parse failures,
/// as they were under ruamel.
fn load_source(root: &RepoRoot, path: &Path) -> Result<Source, Finding> {
    let finding = |line, rule, message| Finding {
        path: root.relative(path),
        line,
        rule,
        message,
    };
    let text = std::fs::read_to_string(path).map_err(|error| {
        finding(
            1,
            "unreadable-source",
            format!("cannot read {}: {error}", path.display()),
        )
    })?;
    let unparseable = |line, detail: String| {
        finding(
            line,
            "unparseable-yaml",
            format!("{} does not parse as YAML: {detail}", path.display()),
        )
    };
    let mut documents = YamlLoader::load_from_str(&text)
        .map_err(|error| unparseable(error.marker().line().max(1), error.to_string()))?;
    let document = match documents.len() {
        0 => Yaml::Null,
        1 => documents.remove(0),
        count => {
            return Err(unparseable(
                1,
                format!("expected a single document in the stream, found {count}"),
            ));
        }
    };
    Ok(Source { text, document })
}

/// `map[key]`, treating a missing key as null (Python's `dict.get`).
fn field<'a>(map: &'a Yaml, key: &str) -> &'a Yaml {
    static NULL: Yaml = Yaml::Null;
    match map {
        Yaml::Hash(hash) => hash.get(&Yaml::String(key.to_owned())).unwrap_or(&NULL),
        _ => &NULL,
    }
}

/// The value as a string, if it is one.
fn as_str(value: &Yaml) -> Option<&str> {
    match value {
        Yaml::String(text) => Some(text),
        _ => None,
    }
}

/// Whether a line, with its indentation already removed, declares `key`
/// (plain, single- or double-quoted).
fn declares(line: &str, key: &str) -> bool {
    [key.to_owned(), format!("\"{key}\""), format!("'{key}'")]
        .iter()
        .any(|form| {
            line.strip_prefix(form.as_str())
                .is_some_and(|rest| rest.trim_start().starts_with(':'))
        })
}

/// The 1-based line declaring the top-level `key` (no indentation), if any.
fn top_level_line(text: &str, key: &str) -> Option<usize> {
    text.lines()
        .position(|line| declares(line, key))
        .map(|index| index + 1)
}

/// The 1-based line declaring `key` inside the top-level `display` mapping:
/// the first indented line after `display:` that declares it, before the next
/// top-level line. Falls back to the `display:` line, then to 1.
fn display_line(text: &str, key: &str) -> usize {
    let Some(start) = top_level_line(text, "display") else {
        return 1;
    };
    text.lines()
        .enumerate()
        .skip(start)
        .take_while(|(_, line)| {
            line.is_empty()
                || line.starts_with(' ')
                || line.starts_with('\t')
                || line.starts_with('#')
        })
        .find(|(_, line)| declares(line.trim_start(), key))
        .map_or(start, |(index, _)| index + 1)
}

/// Renders a YAML value the way Python's `repr` renders what ruamel loads
/// for it (`'text'`, `None`, `True`, `1.1`, `[1, 'x']`, `{'a': 1}`).
fn py_repr(value: &Yaml) -> String {
    match value {
        Yaml::String(text) => py_str_repr(text),
        Yaml::Integer(number) => number.to_string(),
        Yaml::Real(text) => py_float_repr(text),
        Yaml::Boolean(true) => "True".to_owned(),
        Yaml::Boolean(false) => "False".to_owned(),
        Yaml::Null | Yaml::BadValue | Yaml::Alias(_) => "None".to_owned(),
        Yaml::Array(items) => format!(
            "[{}]",
            items.iter().map(py_repr).collect::<Vec<_>>().join(", ")
        ),
        Yaml::Hash(hash) => format!(
            "{{{}}}",
            hash.iter()
                .map(|(key, value)| format!("{}: {}", py_repr(key), py_repr(value)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

/// Python's `repr(str)`: single quotes unless the text has a `'` and no `"`;
/// backslash, the quote, `\t`, `\n`, `\r` escaped; other non-printable
/// characters as `\xhh`, `\uhhhh` or `\Uhhhhhhhh`.
///
/// "Non-printable" covers control characters and the separator and format
/// characters Python's `str.isprintable` rejects that occur in practice; it
/// is not the full Unicode category table.
fn py_str_repr(text: &str) -> String {
    let quote = if text.contains('\'') && !text.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::with_capacity(text.len() + 2);
    out.push(quote);
    for ch in text.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '\t' => out.push_str("\\t"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            _ if ch == quote => {
                out.push('\\');
                out.push(ch);
            }
            _ if !is_printable(ch) => {
                let code = u32::from(ch);
                out.push_str(&if code < 0x100 {
                    format!("\\x{code:02x}")
                } else if code < 0x1_0000 {
                    format!("\\u{code:04x}")
                } else {
                    format!("\\U{code:08x}")
                });
            }
            _ => out.push(ch),
        }
    }
    out.push(quote);
    out
}

/// Approximates Python's `str.isprintable` for one character.
fn is_printable(ch: char) -> bool {
    !(ch.is_control()
        || matches!(
            ch,
            '\u{a0}'
                | '\u{ad}'
                | '\u{1680}'
                | '\u{2000}'..='\u{200f}'
                | '\u{2028}'..='\u{202f}'
                | '\u{205f}'..='\u{2064}'
                | '\u{2066}'..='\u{206f}'
                | '\u{3000}'
                | '\u{feff}'
                | '\u{e000}'..='\u{f8ff}'
        ))
}

/// Python's `repr(float)` of a YAML real: the shortest round-trip digits,
/// positional for exponents in `-4..16`, otherwise `d.ddde±XX`.
fn py_float_repr(text: &str) -> String {
    let lowered = text.to_ascii_lowercase();
    let value = match lowered.trim_start_matches('+') {
        ".inf" => f64::INFINITY,
        "-.inf" => f64::NEG_INFINITY,
        ".nan" => f64::NAN,
        other => match other.parse::<f64>() {
            Ok(value) => value,
            Err(_) => return text.to_owned(),
        },
    };
    if value.is_nan() {
        return "nan".to_owned();
    }
    if value.is_infinite() {
        return if value > 0.0 { "inf" } else { "-inf" }.to_owned();
    }
    if value == 0.0 {
        return if value.is_sign_negative() {
            "-0.0"
        } else {
            "0.0"
        }
        .to_owned();
    }
    // `{:e}` gives the shortest round-trip digits as `d.ddde<exp>`.
    let scientific = format!("{:e}", value.abs());
    let (mantissa, exponent) = scientific
        .split_once('e')
        .expect("`{:e}` always has an exponent");
    let exponent: i32 = exponent.parse().expect("`{:e}` exponent is an integer");
    let digits: String = mantissa.chars().filter(char::is_ascii_digit).collect();
    let sign = if value < 0.0 { "-" } else { "" };
    if (-4..16).contains(&exponent) {
        let positional = if exponent >= 0 {
            let point = usize::try_from(exponent).expect("non-negative") + 1;
            if digits.len() > point {
                format!("{}.{}", &digits[..point], &digits[point..])
            } else {
                format!("{digits}{}.0", "0".repeat(point - digits.len()))
            }
        } else {
            let zeros = usize::try_from(-exponent - 1).expect("non-negative");
            format!("0.{}{digits}", "0".repeat(zeros))
        };
        format!("{sign}{positional}")
    } else {
        let mantissa = if digits.len() > 1 {
            format!("{}.{}", &digits[..1], &digits[1..])
        } else {
            digits
        };
        let exponent_sign = if exponent < 0 { '-' } else { '+' };
        format!("{sign}{mantissa}e{exponent_sign}{:02}", exponent.abs())
    }
}

#[cfg(test)]
#[path = "app_notification_tests.rs"]
mod tests;
