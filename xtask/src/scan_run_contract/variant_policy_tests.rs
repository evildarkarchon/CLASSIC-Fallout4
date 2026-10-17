use std::collections::BTreeSet;

use super::*;

#[test]
fn every_variant_has_exactly_one_row() {
    let unique: BTreeSet<&str> = TARGETS.iter().map(|target| target.variant).collect();
    assert_eq!(unique.len(), TARGETS.len());
}

#[test]
fn rows_record_their_own_source_lines() {
    let source = include_str!("variant_policy.rs");
    let lines: Vec<&str> = source.lines().collect();
    for target in TARGETS {
        let line = lines[target.line as usize - 1];
        assert!(
            line.contains(&format!("\"{}\"", target.variant)),
            "{} recorded line {}: {line}",
            target.variant,
            target.line
        );
    }
}
