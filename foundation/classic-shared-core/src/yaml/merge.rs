//! YAML document and merge-key merging helpers.

pub(crate) mod documents;
mod merge_keys;

pub use documents::merge_yaml_documents;
pub use merge_keys::merge_keys;
