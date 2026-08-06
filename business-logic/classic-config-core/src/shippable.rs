//! Crate-internal shippable YAML selection plus the public `CLASSIC Main.yaml`
//! version extractor built on top of it.
//!
//! Installed YAML Data selection is owned exclusively by
//! [`crate::installed_yaml_data`]. This module is the private machinery it (and
//! the narrow startup-path version reader) share; it is deliberately **not** a
//! public interface, because a caller that could name a [`ShippableFile`] and
//! supply its own [`classic_settings_core::SchemaCompat`] would be selecting
//! Installed YAML Data with a policy config core does not own.
//!
//! Only two things escape the crate:
//!
//! - [`YamlLoadError`] / [`CandidateRejection`] — *diagnostics*. They describe
//!   what selection saw and rejected; they cannot select anything themselves,
//!   and [`MainYamlVersionError`] carries them in its public error chain.
//! - The `load_main_yaml_version*` family — a typed, policy-free operation that
//!   builds its own file identity and applies `client_schemas::MAIN_YAML`
//!   internally, so no caller-supplied compatibility range reaches selection.

mod loader;
mod main_version;

// Selection machinery: crate-private. Nothing outside `classic-config-core`
// may name a shippable file or hand in its own compatibility range.
// `LoadSource`/`LoadedShippable`/`load_shippable_yaml_with_env` are reached
// through `super::loader` by the submodules that need them and are
// deliberately not re-exported even at crate scope.
pub(crate) use loader::{ShippableFile, load_shippable_yaml};
// Diagnostics: public, because `MainYamlVersionError::Load` exposes them and
// frontends render the per-candidate rejection reasons.
pub use loader::{CandidateRejection, YamlLoadError};
pub(crate) use main_version::validate_release_semver_shape;
pub use main_version::{
    MainYamlVersionError, load_main_yaml_version, load_main_yaml_version_with_bundled_dir,
    load_main_yaml_version_with_env,
};
