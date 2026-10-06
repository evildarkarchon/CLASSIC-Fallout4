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

pub mod atomic_install;
pub mod client_schemas;
pub mod crashgen_expectation_parser;
pub(crate) mod crashgen_registry_yaml;
pub mod crashgen_rules;
pub mod explicit_yaml_data;
pub(crate) mod game_data;
pub mod game_local;
pub mod generation;
pub mod installed_yaml_data;
// Private: shippable selection is implementation machinery owned by
// `installed_yaml_data`. Its public diagnostics and the version reader for
// `CLASSIC Main.yaml` are re-exported below.
pub(crate) mod shippable;
pub mod yaml_cache;
pub mod yaml_source;
pub mod yamldata;

// YAML Data install, one-step rollback, and read-path self-heal (#248). These
// write into the YAML cache location owned below and are what the YAML Data
// Update Channel and the shippable loader drive.
pub use atomic_install::{
    InstallOutcome, RollbackOutcome, SelfHealOutcome, install_atomic, rollback, self_heal,
};
pub use crashgen_expectation_parser::{
    CrashgenExpectationParseDiagnostic, CrashgenExpectationParseResult, parse_crashgen_expectations,
};
pub use crashgen_rules::*;
pub use explicit_yaml_data::{
    ExplicitYamlDataLoadError, ExplicitYamlDataRequest, ExplicitYamlDataRole,
    ExplicitYamlDataSnapshot, GameDataRole, YamlDataContentIdentity, load_explicit_yaml_data,
    load_explicit_yaml_data_in_version_registry_scope,
};

pub use game_local::{
    GameLocalFacts, game_local_yaml_path, persist_game_local_paths, read_game_local_facts,
    read_game_local_facts_in_yaml_file_cache_scope,
};
// Ignore/Local YAML first-run generation (#248).
pub use generation::{
    FileGenerator, FileGeneratorConfig, generate_ignore_file, generate_local_yaml,
};
pub use installed_yaml_data::{
    InspectedYamlDataFile, InstalledYamlDataDiagnostic, InstalledYamlDataDiagnosticKind,
    InstalledYamlDataInspection, InstalledYamlDataInspectionError,
    InstalledYamlDataInspectionRequest, InstalledYamlDataLoadError, InstalledYamlDataLoadOutcome,
    InstalledYamlDataLoadRequest, InstalledYamlDataProvenance, InstalledYamlDataRole,
    InstalledYamlDataSnapshot, LocalIgnoreRecoveryPlan, LocalIgnoreResetConflict,
    LocalIgnoreResetDurabilityReceipt, LocalIgnoreResetError, LocalIgnoreResetOutcome,
    LocalIgnoreResetPublicationStage, LocalIgnoreResetResult, LocalIgnoreYamlDataState,
    inspect_installed_yaml_data, inspect_installed_yaml_data_with_env, load_installed_yaml_data,
    load_installed_yaml_data_in_version_registry_scope, load_installed_yaml_data_with_env,
};
// Only diagnostics and the typed version reader escape `shippable`. Its
// low-level selection entry points, and the file-identity and
// compatibility-range types a caller would need to drive them, are all
// crate-private, so no consumer can select Installed YAML Data outside
// `installed_yaml_data`'s policy. The compliance suite's `forbiddenExports`
// audit asserts those names never reappear on this surface.
pub use shippable::{
    CandidateRejection, MainYamlVersionError, YamlLoadError, load_main_yaml_version,
    load_main_yaml_version_with_bundled_dir, load_main_yaml_version_with_env,
};
// Per-user YAML cache location: where YAML Data updates are installed and
// where Installed YAML Data selection looks for update candidates.
pub use yaml_cache::{
    ensure_yaml_cache_dir, ensure_yaml_cache_dir_with_env, yaml_cache_dir, yaml_cache_dir_with_env,
};
pub use yaml_source::YamlSource;
pub use yamldata::{
    ConfigError, CoreModEntry, CoreModExclude, CrashgenEntryRaw, ModConflictEntry,
    ModSolutionCriteria, ModSolutionEntry, SuspectErrorRule, SuspectStackCountRule,
    SuspectStackRule, YamlDataCore, format_registry_game_version, resolve_registry_version_info,
    resolve_registry_version_info_in,
};

// Re-export get_runtime from classic-shared-core for convenience
pub use classic_shared_core::get_runtime;

// Re-export YAML cache management from its classic-shared-core owner for
// testing. This clears the default YAML-file cache scope that config's own
// `YamlOperations::new()` loaders use.
pub use classic_shared_core::yaml::clear_global_yaml_cache;
