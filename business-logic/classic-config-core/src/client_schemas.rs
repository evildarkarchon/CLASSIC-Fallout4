//! Client-side schema compatibility ranges for shippable YAML files.
//!
//! Every shippable CLASSIC YAML file (`CLASSIC Main.yaml`,
//! `CLASSIC Fallout4.yaml`, future per-game files) carries a root-level
//! `schema_version: "MAJOR.MINOR"` header. This module declares, per file
//! family, the [`SchemaCompat`] range the **current client binary** is built
//! to parse.
//!
//! # Bump rules (short form)
//!
//! - **MINOR bump** — a shippable YAML file added an optional key that
//!   existing clients can ignore. Raise [`SchemaCompat::minimum_minor`] on the
//!   client ONLY if the client is now requiring the new key; otherwise leave
//!   it alone.
//! - **MAJOR bump** — a shippable YAML file removed or reshaped a key an
//!   older client depended on. Raise [`SchemaCompat::accepted_major`] and
//!   reset `minimum_minor` to the lowest MINOR that still contains every key
//!   the client still reads.
//!
//! The drift-guard CI step (Section 13 of the yaml-update-delivery change)
//! will compare bundled YAML headers against these constants and fail the
//! build if a checked-in file would be refused at load time.
//!
//! # Migration history
//!
//! - **MAIN_YAML 1 → 2 (2026-04)** — `CLASSIC_Info.version` dropped the
//!   `CLASSIC v` display prefix and is now a bare SemVer string (e.g.,
//!   `v9.1.0`). Consumers that previously stripped the prefix read the
//!   value directly; the one consumer that needed the decorated form
//!   (scanlog report header) now prepends `CLASSIC ` at format time. See
//!   `openspec/changes/yaml-version-drop-classic-prefix/` for the full
//!   contract.
//! - **MAIN_YAML 2.0 → 2.1 (2026-07)** — `CLASSIC_Settings.Unsolved Logs
//!   Destination` was added as an optional default setting. Current clients
//!   still accept 2.0 because the key is not required to parse or scan.
//! - **MAIN_YAML 2.1 → 2.2 (2026-07)** — the embedded default-settings scalar
//!   became the complete Rust-generated compatibility mirror. Its added Game
//!   Setup and frontend fields remain optional to older 2.x clients.

use crate::shippable::ShippableFile;
use classic_settings_core::SchemaCompat;

/// Schema range the client accepts for `CLASSIC Main.yaml` (and any future
/// global metadata file under `CLASSIC Data/databases/CLASSIC Main.yaml`).
pub const MAIN_YAML: SchemaCompat = SchemaCompat::new(2, 0);

/// Schema range the client accepts for `CLASSIC Fallout4.yaml` (and any
/// parallel per-game shippable file under
/// `CLASSIC Data/databases/CLASSIC <Game>.yaml`).
pub const GAME_FALLOUT4_YAML: SchemaCompat = SchemaCompat::new(1, 0);

/// One canonical shippable YAML file name plus the schema range this client
/// accepts for it.
///
/// This is the metadata shape consumed by first-party YAML Data update checks:
/// the update channel needs the same file names and compatibility ranges that
/// runtime YAML loading uses, without native callers duplicating either value.
///
/// The entry carries only the canonical **file name**, never a resolvable
/// bundled or cache path. Selection is owned by
/// [`crate::installed_yaml_data`]; handing update callers a path here would let
/// them reopen an Installed YAML Data candidate under their own policy, which
/// is precisely what the unified selection contract forbids.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ShippableSchemaEntry {
    /// Canonical file name as it appears in the install tree and in the
    /// per-user YAML cache directory (e.g. `CLASSIC Main.yaml`).
    pub file_name: String,
    /// Schema range accepted by this client for `file_name`.
    pub accepted: SchemaCompat,
}

/// Returns the authoritative first-party shippable YAML file names and schema
/// ranges.
///
/// The order is stable for diagnostics and rollback summaries, but callers
/// should still treat the returned entries as a set keyed by `file_name`.
pub fn shippable_schema_entries() -> Vec<ShippableSchemaEntry> {
    vec![
        ShippableSchemaEntry {
            file_name: ShippableFile::main().file_name,
            accepted: MAIN_YAML,
        },
        ShippableSchemaEntry {
            file_name: ShippableFile::game("Fallout4").file_name,
            accepted: GAME_FALLOUT4_YAML,
        },
    ]
}
