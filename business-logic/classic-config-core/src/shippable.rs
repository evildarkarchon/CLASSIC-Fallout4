//! Public facade for shippable YAML loading and `CLASSIC Main.yaml` version extraction.

mod loader;
mod main_version;

pub use loader::{
    CandidateRejection, LoadSource, LoadedShippable, ShippableFile, YamlLoadError,
    load_shippable_yaml, load_shippable_yaml_with_env,
};
pub use main_version::{
    MainYamlVersionError, load_main_yaml_version, load_main_yaml_version_with_bundled_dir,
    load_main_yaml_version_with_env,
};
