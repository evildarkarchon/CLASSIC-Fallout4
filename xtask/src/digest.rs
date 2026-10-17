//! Lowercase hexadecimal and SHA-256 digests, shared by the conformance
//! engine and the publish steps.
//!
//! Every digest xtask writes or compares (receipt hashes, run-plan ids,
//! manifest `sha256` fields, fixture pins) is lowercase hex, so there is one
//! encoder rather than one per caller.

use sha2::{Digest, Sha256};

/// Lowercase hexadecimal of `bytes`, two digits per byte.
pub(crate) fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

/// Lowercase hex SHA-256 of `bytes`.
pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}

#[cfg(test)]
#[path = "digest_tests.rs"]
mod tests;
