//! Content identity for bytes that were published or verified.

use sha2::{Digest, Sha256};

/// Identity of an exact byte sequence handled by a durable publication.
///
/// The digest is retained in binary form and rendered on demand, so a caller
/// that only needs the byte length never pays for a hex allocation. Callers
/// embed this in their own receipts; this crate never persists it.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ContentIdentity {
    sha256: [u8; 32],
    byte_len: u64,
}

impl ContentIdentity {
    /// Calculate the canonical identity of an exact byte sequence.
    #[must_use]
    pub fn from_bytes(bytes: &[u8]) -> Self {
        Self {
            sha256: Sha256::digest(bytes).into(),
            byte_len: bytes.len() as u64,
        }
    }

    /// Return the lowercase hexadecimal SHA-256 digest.
    #[must_use]
    pub fn sha256_hex(&self) -> String {
        use std::fmt::Write as _;

        let mut encoded = String::with_capacity(64);
        for byte in self.sha256 {
            write!(&mut encoded, "{byte:02x}").expect("writing to a String cannot fail");
        }
        encoded
    }

    /// Return the number of bytes covered by this identity.
    #[must_use]
    pub const fn byte_len(&self) -> u64 {
        self.byte_len
    }
}

#[cfg(test)]
#[path = "identity_tests.rs"]
mod tests;
