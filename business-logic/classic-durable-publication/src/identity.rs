//! Content identity for bytes that were published or verified.

use std::io::Read;

use sha2::{Digest, Sha256};

/// Bytes read per digest round when identifying a file rather than a buffer.
///
/// Sized to match the workspace's existing file hasher so that streaming an
/// already-staged file costs the same as it did before this crate owned the
/// verification.
const DIGEST_CHUNK_SIZE: usize = 64 * 1024;

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

    /// Calculate the identity of bytes that are already on disk.
    ///
    /// Streams `reader` in fixed rounds rather than materializing it, because
    /// the caller this exists for — verifying a staged file it did not write —
    /// has no reason to hold the whole payload in memory.
    ///
    /// # Errors
    ///
    /// Returns the first read failure encountered. Nothing is retried,
    /// including [`std::io::ErrorKind::Interrupted`].
    pub fn from_reader(mut reader: impl Read) -> std::io::Result<Self> {
        let mut hasher = Sha256::new();
        let mut buffer = vec![0u8; DIGEST_CHUNK_SIZE];
        let mut byte_len: u64 = 0;
        loop {
            let read = reader.read(&mut buffer)?;
            if read == 0 {
                break;
            }
            hasher.update(&buffer[..read]);
            byte_len += read as u64;
        }
        Ok(Self {
            sha256: hasher.finalize().into(),
            byte_len,
        })
    }

    /// Return whether this identity's digest equals `expected`, ignoring case.
    ///
    /// Case insensitivity is not a convenience: an expected digest usually
    /// arrives from a manifest that a publisher may have rendered in either
    /// case, and rejecting an otherwise-identical payload over letter case
    /// would be an integrity failure that is not one.
    #[must_use]
    pub fn matches_sha256_hex(&self, expected: &str) -> bool {
        let rendered = self.sha256_hex();
        rendered.len() == expected.len()
            && rendered
                .bytes()
                .zip(expected.bytes())
                .all(|(rendered, expected)| rendered.eq_ignore_ascii_case(&expected))
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

#[rustfmt::skip]
#[cfg(test)] #[path = "identity_tests.rs"] mod tests;
