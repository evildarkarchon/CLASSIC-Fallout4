//! The app-notification shape rules, ported from the retired Python
//! validator, which mirrored `classic_update_core::notification`.
//!
//! Digits are ASCII only and `$` does not match before a trailing newline, as
//! in the Rust client. Python's `re` accepted Unicode digits and a trailing
//! `\n`; neither can be parsed by the client, so rejecting them here is the
//! intended delta.

use std::cmp::Ordering;
use std::net::{Ipv4Addr, Ipv6Addr};
use std::sync::LazyLock;

use regex::Regex;

/// Strict SemVer (semver.org, what the `semver` crate parses): numeric
/// identifiers have no leading zero.
const SEMVER_BODY: &str = concat!(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)",
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*)?",
    r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?",
);

fn anchored(prefix: &str, body: &str) -> Regex {
    Regex::new(&format!("^{prefix}{body}$")).expect("app-notification patterns are valid regexes")
}

static SEMVER: LazyLock<Regex> = LazyLock::new(|| anchored("", SEMVER_BODY));
static RELEASE_TAG: LazyLock<Regex> = LazyLock::new(|| anchored("v", SEMVER_BODY));
static WORKFLOW_TAG: LazyLock<Regex> =
    LazyLock::new(|| anchored("app-notification-v", SEMVER_BODY));
static MANIFEST_VERSION: LazyLock<Regex> = LazyLock::new(|| anchored("", r"[0-9]+\.[0-9]+"));
/// Shape-only RFC 3339 with an explicit `Z` or `±HH:MM` offset; naive
/// timestamps are refused because the client's `is_rfc3339` refuses them.
static RFC3339: LazyLock<Regex> = LazyLock::new(|| {
    anchored(
        "",
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-9]{2})",
    )
});
static IPV_FUTURE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^v[a-fA-F0-9]+\..+$").expect("valid regex"));

/// `MAJOR.MINOR`, the `manifest_version` shape.
pub(crate) fn is_manifest_version(text: &str) -> bool {
    MANIFEST_VERSION.is_match(text)
}

/// Strict SemVer with no `v` prefix.
pub(crate) fn is_semver(text: &str) -> bool {
    SEMVER.is_match(text)
}

/// `v<SEMVER>`, the advertised binary release tag.
pub(crate) fn is_release_tag(text: &str) -> bool {
    RELEASE_TAG.is_match(text)
}

/// `app-notification-v<SEMVER>`, the tag that triggers the publish workflow.
/// The workflow trigger glob `app-notification-v*` cannot express SemVer, so
/// this is the load-bearing guard.
pub(crate) fn is_workflow_tag(text: &str) -> bool {
    WORKFLOW_TAG.is_match(text)
}

/// RFC 3339 with an explicit offset.
pub(crate) fn is_rfc3339(text: &str) -> bool {
    RFC3339.is_match(text)
}

/// SemVer precedence (semver.org rule 11) of two strings that already match
/// [`is_semver`]: build metadata is ignored, a version with no pre-release
/// outranks one with a pre-release, numeric pre-release identifiers sort
/// below alphanumeric ones and compare numerically, and a shorter identifier
/// list sorts first when the shared prefix is equal.
pub(crate) fn semver_precedence(left: &str, right: &str) -> Ordering {
    let (left_core, left_pre) = split_semver(left);
    let (right_core, right_pre) = split_semver(right);
    let core = left_core
        .iter()
        .zip(&right_core)
        .map(|(a, b)| compare_numeric(a, b))
        .find(|ordering| ordering.is_ne())
        .unwrap_or(Ordering::Equal);
    if core.is_ne() {
        return core;
    }
    match (left_pre, right_pre) {
        (None, None) => Ordering::Equal,
        (None, Some(_)) => Ordering::Greater,
        (Some(_), None) => Ordering::Less,
        (Some(left), Some(right)) => {
            let left: Vec<&str> = left.split('.').collect();
            let right: Vec<&str> = right.split('.').collect();
            for (a, b) in left.iter().zip(&right) {
                let numeric = |s: &str| s.bytes().all(|byte| byte.is_ascii_digit());
                let ordering = match (numeric(a), numeric(b)) {
                    (true, true) => compare_numeric(a, b),
                    (true, false) => Ordering::Less,
                    (false, true) => Ordering::Greater,
                    (false, false) => a.cmp(b),
                };
                if ordering.is_ne() {
                    return ordering;
                }
            }
            left.len().cmp(&right.len())
        }
    }
}

/// Splits a SemVer string into its three core numbers and its pre-release,
/// dropping build metadata.
fn split_semver(text: &str) -> ([&str; 3], Option<&str>) {
    let body = text.split_once('+').map_or(text, |(body, _)| body);
    let (core, pre) = match body.split_once('-') {
        Some((core, pre)) => (core, Some(pre)),
        None => (body, None),
    };
    let mut parts = core.splitn(3, '.');
    let mut next = || parts.next().unwrap_or("0");
    ([next(), next(), next()], pre)
}

/// Compares ASCII digit strings with no leading zeros by numeric value, at
/// any length (Python compared arbitrary-precision ints).
fn compare_numeric(left: &str, right: &str) -> Ordering {
    left.len().cmp(&right.len()).then_with(|| left.cmp(right))
}

/// Whether `value` is an HTTPS URL by the retired tool's rule, which ran
/// Python's `urllib.parse.urlsplit`: the scheme is `https` (any case), the
/// port (if any) is ASCII digits in `0..=65535`, the authority and host are
/// non-empty, a bracketed host is an IPv6 address or IPvFuture literal, and
/// the authority holds no character at or below space or `0x7F`.
///
/// Like `urlsplit`, leading C0 controls and spaces are stripped and every
/// tab, CR and LF is removed before parsing. Python's NFKC check on
/// non-ASCII authorities is not reproduced.
pub(crate) fn is_https_cta_url(value: &str) -> bool {
    let url: String = value
        .trim_start_matches(|ch: char| ch <= ' ')
        .chars()
        .filter(|ch| !matches!(ch, '\t' | '\r' | '\n'))
        .collect();
    let (scheme, rest) = match url.find(':') {
        Some(colon)
            if colon > 0
                && url.as_bytes()[0].is_ascii_alphabetic()
                && url[..colon]
                    .chars()
                    .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '+' | '-' | '.')) =>
        {
            (url[..colon].to_ascii_lowercase(), &url[colon + 1..])
        }
        _ => (String::new(), url.as_str()),
    };
    let netloc = rest.strip_prefix("//").map_or("", |after| {
        let end = after.find(['/', '?', '#']).unwrap_or(after.len());
        &after[..end]
    });
    let (open, close) = (netloc.contains('['), netloc.contains(']'));
    if open != close || (open && !bracketed_netloc_is_valid(netloc)) {
        return false;
    }
    let (hostname, port) = host_and_port(netloc);
    if let Some(port) = port {
        let in_range = port.bytes().all(|byte| byte.is_ascii_digit())
            && port.parse::<u64>().is_ok_and(|number| number <= 65_535);
        if !in_range {
            return false;
        }
    }
    scheme == "https"
        && !netloc.is_empty()
        && !hostname.is_empty()
        && !netloc.chars().any(|ch| ch <= ' ' || ch == '\x7f')
}

/// `urlsplit`'s `_hostinfo`: the host and the non-empty port of `netloc`.
fn host_and_port(netloc: &str) -> (&str, Option<&str>) {
    let hostinfo = netloc.rsplit_once('@').map_or(netloc, |(_, host)| host);
    let (hostname, port) = match hostinfo.split_once('[') {
        Some((_, bracketed)) => {
            let (hostname, after) = bracketed.split_once(']').unwrap_or((bracketed, ""));
            (hostname, after.split_once(':').map_or("", |(_, port)| port))
        }
        None => hostinfo.split_once(':').unwrap_or((hostinfo, "")),
    };
    (hostname, (!port.is_empty()).then_some(port))
}

/// `urlsplit`'s `_check_bracketed_netloc`: nothing before `[`, only `:port`
/// after `]`, and the bracketed host is IPvFuture or IPv6 (not IPv4).
fn bracketed_netloc_is_valid(netloc: &str) -> bool {
    let host_and_port = netloc.rsplit_once('@').map_or(netloc, |(_, host)| host);
    let hostname = match host_and_port.split_once('[') {
        Some((before, bracketed)) => {
            if !before.is_empty() {
                return false;
            }
            let (hostname, after) = bracketed.split_once(']').unwrap_or((bracketed, ""));
            if !after.is_empty() && !after.starts_with(':') {
                return false;
            }
            hostname
        }
        None => host_and_port
            .split_once(':')
            .map_or(host_and_port, |(host, _)| host),
    };
    if hostname.starts_with('v') {
        return IPV_FUTURE.is_match(hostname);
    }
    if hostname.parse::<Ipv4Addr>().is_ok() {
        return false;
    }
    // `ipaddress.ip_address` accepts an IPv6 scope id: `addr%zone`, with a
    // non-empty zone that holds no further `%`.
    match hostname.split_once('%') {
        Some((address, zone)) => {
            !zone.is_empty() && !zone.contains('%') && address.parse::<Ipv6Addr>().is_ok()
        }
        None => hostname.parse::<Ipv6Addr>().is_ok(),
    }
}

#[cfg(test)]
#[path = "rules_tests.rs"]
mod tests;
