//! YAML operations absorbed from classic-yaml-core (D-01).
//!
//! This facade keeps the public YAML operations surface stable while the
//! implementation lives in focused submodules. Its error type, [`YamlError`],
//! is owned by `classic_shared_core::yaml` alongside the generic merge rules
//! that also report it.

mod accessors;
mod cache;
mod operations;

pub use cache::{
    YamlCacheStats, clear_global_yaml_cache, reset_yaml_cache_stats, yaml_cache_stats,
};
pub use classic_shared_core::yaml::YamlError;
pub use operations::YamlOperations;
