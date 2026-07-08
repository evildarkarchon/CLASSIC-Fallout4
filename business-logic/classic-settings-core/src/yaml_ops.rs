//! YAML operations absorbed from classic-yaml-core (D-01).
//!
//! This facade keeps the public YAML operations surface stable while the
//! implementation lives in focused submodules.

mod accessors;
mod cache;
mod error;
mod operations;

pub use cache::{
    YamlCacheStats, clear_global_yaml_cache, reset_yaml_cache_stats, yaml_cache_stats,
};
pub use error::YamlError;
pub use operations::YamlOperations;
