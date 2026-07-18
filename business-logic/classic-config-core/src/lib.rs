//! classic-config-core: Pure Rust configuration loading business logic
//!
//! This crate provides high-performance YAML configuration loading with:
//! - yaml-rust2 for parsing (pure Rust, YAML 1.2 compliant)
//! - Parallel file I/O with Tokio
//! - Efficient memory representation
//! - NO PyO3 dependency - pure Rust business logic only
//!
//! ## ONE RUNTIME RULE
//! This crate uses the shared global Tokio runtime from classic-shared-core.
//! All async operations use `classic_shared_core::get_runtime().block_on()`.

pub mod client_schemas;
pub mod crashgen_expectation_parser;
pub(crate) mod crashgen_registry_yaml;
pub mod crashgen_rules;
pub mod explicit_yaml_data;
pub(crate) mod game_data;
pub mod game_local;
pub mod installed_yaml_data;
pub mod shippable;
pub mod yaml_source;
pub mod yamldata;

pub use crashgen_expectation_parser::{
    CrashgenExpectationParseDiagnostic, CrashgenExpectationParseResult, parse_crashgen_expectations,
};
pub use crashgen_rules::*;
pub use explicit_yaml_data::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    ExplicitYamlDataSnapshot, GameDataRole, YamlDataContentIdentity, load_explicit_yaml_data,
};

pub use game_local::persist_game_local_paths;
pub use installed_yaml_data::{
    InspectedYamlDataFile, InstalledYamlDataDiagnostic, InstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspection, InstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataProvenance, InstalledYamlDataRole,
    inspect_installed_yaml_data, inspect_installed_yaml_data_with_env,
};
pub use shippable::{
    CandidateRejection, LoadSource, LoadedShippable, MainYamlVersionError, ShippableFile,
    YamlLoadError, load_main_yaml_version, load_main_yaml_version_with_bundled_dir,
    load_main_yaml_version_with_env, load_shippable_yaml, load_shippable_yaml_with_env,
};
pub use yaml_source::YamlSource;
pub use yamldata::{
    ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, ModConflictEntry,
    ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackCountRule,
    SuspectStackRule, YamlDataCore, format_registry_game_version, resolve_registry_version_info,
};

// Re-export get_runtime from classic-shared-core for convenience
pub use classic_shared_core::get_runtime;

// Re-export YAML cache management from classic-settings-core for testing
pub use classic_settings_core::clear_global_yaml_cache;
