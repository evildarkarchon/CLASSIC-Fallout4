//! Independently useful FormID extraction and validation batch utilities.

use std::sync::LazyLock;

use rayon::prelude::*;
use regex::Regex;

/// Precompiled pattern shared by semantic batch extraction.
static FORMID_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)Form\s*ID:?\s*0x([0-9A-F]{8})\b")
        .expect("the static FormID extraction pattern must compile")
});

/// Extracts FormIDs from multiple callstack segments in parallel.
///
/// Each inner result preserves source order, excludes `FF` plugin-limit
/// identifiers, and retains null identifiers as crash evidence.
pub fn extract_formids_batch(callstack_segments: Vec<Vec<String>>) -> Vec<Vec<String>> {
    callstack_segments
        .par_iter()
        .map(|segment| {
            segment
                .iter()
                .filter_map(|line| {
                    let identifier = FORMID_PATTERN
                        .captures(line)?
                        .get(1)?
                        .as_str()
                        .to_uppercase();
                    (!identifier.starts_with("FF")).then(|| format!("Form ID: {identifier}"))
                })
                .collect()
        })
        .collect()
}

/// Returns whether a string contains a non-null FormID with at most eight hex digits.
///
/// Optional `Form ID:` and `0x` prefixes are accepted. This validates syntax,
/// not whether the identifier exists in game data.
pub fn is_valid_formid(formid: &str) -> bool {
    let cleaned = formid.trim();
    let cleaned = cleaned.strip_prefix("Form ID:").unwrap_or(cleaned).trim();
    let cleaned = cleaned
        .strip_prefix("0x")
        .or_else(|| cleaned.strip_prefix("0X"))
        .unwrap_or(cleaned);
    !cleaned.is_empty()
        && cleaned.len() <= 8
        && cleaned.bytes().all(|byte| byte.is_ascii_hexdigit())
        && u32::from_str_radix(cleaned, 16).is_ok_and(|value| value > 0)
}

/// Validates an owned FormID batch in input order using Rayon.
pub fn validate_formids_batch(formids: Vec<String>) -> Vec<bool> {
    formids
        .par_iter()
        .map(|formid| is_valid_formid(formid))
        .collect()
}

#[cfg(test)]
#[path = "formid_analyzer_tests.rs"]
mod tests;
