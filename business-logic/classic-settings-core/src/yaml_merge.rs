//! YAML Merge Key Extension Support
//!
//! This module implements the YAML Merge Key extension (<http://yaml.org/type/merge.html>).
//!
//! The merge key (`<<`) is a YAML 1.1 extension that allows dictionaries to be merged
//! together. Since yaml-rust2 parses the `<<` key but doesn't resolve it automatically,
//! this module provides functions to process a parsed YAML document and resolve all
//! merge keys.
//!
//! # Example
//!
//! ```rust
//! use classic_settings_core::{YamlOperations, merge_keys};
//!
//! let ops = YamlOperations::new();
//! let yaml_str = r#"
//! defaults: &defaults
//!   adapter: postgres
//!   host: localhost
//!
//! development:
//!   <<: *defaults
//!   database: dev_db
//! "#;
//!
//! let yaml = ops.parse_yaml(yaml_str).unwrap();
//! let merged = merge_keys(yaml).unwrap();
//!
//! // Now development.adapter and development.host are accessible
//! assert_eq!(
//!     ops.get_string_value(&merged, "development.adapter", ""),
//!     "postgres"
//! );
//! ```
//!
//! # Merge Key Semantics
//!
//! - The `<<` key can reference a single mapping or a sequence of mappings
//! - Keys from the current mapping take precedence over merged keys
//! - When merging multiple mappings, earlier ones in the sequence take precedence
//! - The `<<` key is removed from the result after merging
//! - Merge keys are resolved recursively (a merged mapping can itself have merge keys)

use crate::YamlError;
use yaml_rust2::Yaml;

/// Resolve YAML merge keys (`<<`) in a parsed YAML document.
///
/// The YAML Merge Key extension (<http://yaml.org/type/merge.html>) allows
/// dictionaries to be merged together using the `<<` key. This function
/// implements the extension by recursively processing the YAML tree and
/// resolving all merge keys.
///
/// # Arguments
///
/// * `yaml` - The parsed YAML document to process
///
/// # Returns
///
/// A new YAML document with all merge keys resolved, or an error if the
/// merge key value is not a valid mapping or sequence of mappings.
///
/// # Example
///
/// ```rust
/// use classic_settings_core::{YamlOperations, merge_keys};
///
/// let ops = YamlOperations::new();
/// let yaml_str = r#"
/// defaults: &defaults
///   adapter: postgres
///   host: localhost
///
/// development:
///   <<: *defaults
///   database: dev_db
/// "#;
///
/// let yaml = ops.parse_yaml(yaml_str).unwrap();
/// let merged = merge_keys(yaml).unwrap();
///
/// // Now development.adapter and development.host are accessible
/// assert_eq!(
///     ops.get_string_value(&merged, "development.adapter", ""),
///     "postgres"
/// );
/// assert_eq!(
///     ops.get_string_value(&merged, "development.database", ""),
///     "dev_db"
/// );
/// ```
///
/// # Errors
///
/// Returns `YamlError::InvalidValue` if a merge key's value is not:
/// - A mapping (hash), or
/// - A sequence (array) of mappings
pub fn merge_keys(yaml: Yaml) -> Result<Yaml, YamlError> {
    merge_keys_recursive(yaml)
}

/// Internal recursive implementation of merge key resolution.
///
/// This function walks the YAML tree and resolves merge keys at each level:
///
/// 1. For Hash nodes:
///    - Extract and remove any `<<` key
///    - Recursively process all other values
///    - If a `<<` key was found, merge its referenced mappings
///    - Merged values are processed recursively to handle nested merge keys
///
/// 2. For Array nodes:
///    - Recursively process each element
///
/// 3. For other types:
///    - Pass through unchanged
fn merge_keys_recursive(yaml: Yaml) -> Result<Yaml, YamlError> {
    match yaml {
        Yaml::Hash(hash) => {
            let merge_key = Yaml::String("<<".to_string());
            let mut result = yaml_rust2::yaml::Hash::new();
            let mut merge_value = None;

            // First pass: separate merge key from other keys and process nested values
            for (key, value) in hash {
                if key == merge_key {
                    merge_value = Some(value);
                } else {
                    // Recursively process nested values
                    let processed_value = merge_keys_recursive(value)?;
                    result.insert(key, processed_value);
                }
            }

            // Second pass: apply merge if present
            if let Some(to_merge) = merge_value {
                // Merge can be a single hash or an array of hashes
                // IMPORTANT: Process each merged hash through merge_keys_recursive first
                // to handle nested merge keys (e.g., level3 merges level2 which merges level1)
                let hashes_to_merge = match to_merge {
                    Yaml::Hash(h) => {
                        // Recursively resolve merge keys in the source hash first
                        let processed = merge_keys_recursive(Yaml::Hash(h))?;
                        match processed {
                            Yaml::Hash(resolved_h) => vec![resolved_h],
                            _ => unreachable!("Hash should remain Hash after merge"),
                        }
                    }
                    Yaml::Array(arr) => {
                        let mut hashes = Vec::new();
                        for item in arr {
                            match item {
                                Yaml::Hash(h) => {
                                    // Recursively resolve merge keys in each source hash
                                    let processed = merge_keys_recursive(Yaml::Hash(h))?;
                                    match processed {
                                        Yaml::Hash(resolved_h) => hashes.push(resolved_h),
                                        _ => unreachable!("Hash should remain Hash after merge"),
                                    }
                                }
                                _ => {
                                    return Err(YamlError::InvalidValue(
                                        "Merge key value must be a mapping or sequence of mappings"
                                            .to_string(),
                                    ));
                                }
                            }
                        }
                        hashes
                    }
                    _ => {
                        return Err(YamlError::InvalidValue(
                            "Merge key value must be a mapping or sequence of mappings".to_string(),
                        ));
                    }
                };

                // Apply merges - current values take precedence, so we insert
                // merged values only if the key doesn't already exist
                for merge_hash in hashes_to_merge {
                    for (key, value) in merge_hash {
                        // Only insert if key doesn't exist (current values take precedence)
                        if !result.contains_key(&key) {
                            result.insert(key, value);
                        }
                    }
                }
            }

            Ok(Yaml::Hash(result))
        }
        Yaml::Array(arr) => {
            // Recursively process array elements
            let processed: Result<Vec<Yaml>, YamlError> =
                arr.into_iter().map(merge_keys_recursive).collect();
            Ok(Yaml::Array(processed?))
        }
        // Other types pass through unchanged
        other => Ok(other),
    }
}

#[cfg(test)]
#[path = "yaml_merge_tests.rs"]
mod tests;
