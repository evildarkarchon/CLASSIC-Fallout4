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

use classic_settings_core::SchemaCompat;

/// Schema range the client accepts for `CLASSIC Main.yaml` (and any future
/// global metadata file under `CLASSIC Data/databases/CLASSIC Main.yaml`).
pub const MAIN_YAML: SchemaCompat = SchemaCompat::new(1, 0);

/// Schema range the client accepts for `CLASSIC Fallout4.yaml` (and any
/// parallel per-game shippable file under
/// `CLASSIC Data/databases/CLASSIC <Game>.yaml`).
pub const GAME_FALLOUT4_YAML: SchemaCompat = SchemaCompat::new(1, 0);
