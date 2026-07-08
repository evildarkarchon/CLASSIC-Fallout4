//! YAML document stream merge helpers.

use crate::error::{Result, SettingsError, SettingsSource};
use yaml_rust2::Yaml;

/// Merge a YAML document stream into a single mapping.
pub fn merge_yaml_documents(source: impl Into<String>, docs: &[Yaml]) -> Result<Yaml> {
    merge_yaml_documents_with_source(SettingsSource::from(source.into()), docs)
}

pub(crate) fn merge_yaml_documents_with_source(
    source: impl Into<SettingsSource>,
    docs: &[Yaml],
) -> Result<Yaml> {
    let source = source.into();

    if docs.is_empty() || docs.iter().all(Yaml::is_badvalue) {
        return Err(SettingsError::EmptyDocument { source });
    }

    let mut merged = None;

    for (index, doc) in docs.iter().enumerate() {
        let Yaml::Hash(_) = doc else {
            return Err(SettingsError::InvalidYamlStructure {
                source,
                index,
                found: yaml_kind(doc),
            });
        };

        merged = Some(match merged {
            Some(current) => merge_yaml_values(current, doc.clone()),
            None => doc.clone(),
        });
    }

    merged.ok_or(SettingsError::EmptyDocument { source })
}

fn merge_yaml_values(base: Yaml, overlay: Yaml) -> Yaml {
    match (base, overlay) {
        (Yaml::Hash(mut left), Yaml::Hash(right)) => {
            for (key, right_value) in right {
                let merged = match left.remove(&key) {
                    Some(left_value) => merge_yaml_values(left_value, right_value),
                    None => right_value,
                };
                left.insert(key, merged);
            }
            Yaml::Hash(left)
        }
        (_, replacement) => replacement,
    }
}

fn yaml_kind(value: &Yaml) -> String {
    match value {
        Yaml::Array(_) => "sequence",
        Yaml::BadValue => "bad value",
        Yaml::Boolean(_) => "boolean",
        Yaml::Hash(_) => "mapping",
        Yaml::Integer(_) => "integer",
        Yaml::Null => "null",
        Yaml::Real(_) => "real",
        Yaml::String(_) => "string",
        Yaml::Alias(_) => "alias",
    }
    .to_string()
}

#[cfg(test)]
#[path = "documents_tests.rs"]
mod tests;
