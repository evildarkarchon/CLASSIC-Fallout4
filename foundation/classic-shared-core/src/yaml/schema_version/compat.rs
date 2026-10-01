//! Schema compatibility checking.

use super::version::SchemaVersion;

/// Per-file client compatibility declaration.
///
/// A client build declares one `SchemaCompat` per shippable file family (e.g.,
/// `MAIN_YAML`, `GAME_FALLOUT4_YAML`). These values are compile-time constants
/// so that drift between bundled YAML schemas and client-accepted ranges can be
/// caught by a CI gate rather than at runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SchemaCompat {
    /// The single MAJOR the client is built to parse. Mismatch is an immediate
    /// incompatibility (the whole file is refused).
    pub accepted_major: u32,
    /// The lowest MINOR the client still supports at `accepted_major`. Files
    /// with a lower MINOR are assumed to predate a field the client now depends
    /// on; higher MINOR is always accepted (additive-only contract).
    pub minimum_minor: u32,
}

impl SchemaCompat {
    /// Construct a compatibility range. `const` so consumers can declare these
    /// as module-level constants.
    pub const fn new(accepted_major: u32, minimum_minor: u32) -> Self {
        Self {
            accepted_major,
            minimum_minor,
        }
    }
}

/// Outcome of comparing a file's [`SchemaVersion`] against a client's
/// [`SchemaCompat`] range.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Compatibility {
    /// File version fits the client's accepted range; safe to load.
    Compatible,
    /// File MAJOR differs from the client's `accepted_major`; incompatible
    /// regardless of MINOR.
    IncompatibleMajor {
        /// The MAJOR component declared by the file.
        file_major: u32,
        /// The MAJOR the client is built to accept.
        client_accepted_major: u32,
    },
    /// File MAJOR matches, but MINOR is below the client's `minimum_minor`.
    IncompatibleMinor {
        /// The MINOR component declared by the file.
        file_minor: u32,
        /// The MINOR floor the client requires.
        client_minimum_minor: u32,
    },
}

/// Decide whether a file's schema version is compatible with a client range.
///
/// Rule (restated for the reader):
/// `version.major == compat.accepted_major && version.minor >= compat.minimum_minor`.
pub fn schema_compat_check(version: &SchemaVersion, compat: &SchemaCompat) -> Compatibility {
    if version.major != compat.accepted_major {
        return Compatibility::IncompatibleMajor {
            file_major: version.major,
            client_accepted_major: compat.accepted_major,
        };
    }
    if version.minor < compat.minimum_minor {
        return Compatibility::IncompatibleMinor {
            file_minor: version.minor,
            client_minimum_minor: compat.minimum_minor,
        };
    }
    Compatibility::Compatible
}

#[cfg(test)]
#[path = "compat_tests.rs"]
mod tests;
