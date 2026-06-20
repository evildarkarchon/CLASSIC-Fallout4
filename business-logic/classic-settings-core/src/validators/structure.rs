//! YAML settings structure validation.

use yaml_rust2::Yaml;

/// An issue found during settings structure validation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationIssue {
    /// The severity of the issue.
    pub severity: IssueSeverity,
    /// A human-readable description of the issue.
    pub message: String,
}

/// Severity level for validation issues.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IssueSeverity {
    /// The issue is informational (e.g., empty data).
    Warning,
    /// The issue is a structural error.
    Error,
}

/// Validate the structure of a YAML settings document.
///
/// Checks for common structural issues:
/// - Document is not a Hash/mapping (expected top-level structure)
/// - Settings file is missing the `CLASSIC_Settings` root key
/// - Document is empty
///
/// # Arguments
///
/// * `yaml` - The parsed YAML document to validate
///
/// # Returns
///
/// A vector of `ValidationIssue`s found. An empty vector means the document is valid.
///
/// # Examples
///
/// ```rust
/// use yaml_rust2::YamlLoader;
/// use classic_settings_core::validators::{validate_settings_structure, IssueSeverity};
///
/// let docs = YamlLoader::load_from_str("CLASSIC_Settings:\n  VR Mode: false\n").unwrap();
/// let issues = validate_settings_structure(&docs[0]);
/// assert!(issues.is_empty());
///
/// let bad_docs = YamlLoader::load_from_str("42").unwrap();
/// let issues = validate_settings_structure(&bad_docs[0]);
/// assert!(issues.iter().any(|i| i.severity == IssueSeverity::Error));
/// ```
#[must_use]
pub fn validate_settings_structure(yaml: &Yaml) -> Vec<ValidationIssue> {
    let mut issues = Vec::new();

    match yaml {
        Yaml::Hash(map) => {
            if map.is_empty() {
                issues.push(ValidationIssue {
                    severity: IssueSeverity::Warning,
                    message: "Settings document is empty".to_string(),
                });
            }

            // Check for CLASSIC_Settings root key (expected in Settings files)
            let settings_key = Yaml::String("CLASSIC_Settings".to_string());
            if !map.contains_key(&settings_key) {
                issues.push(ValidationIssue {
                    severity: IssueSeverity::Warning,
                    message: "Settings document missing 'CLASSIC_Settings' root key".to_string(),
                });
            }
        }
        Yaml::BadValue | Yaml::Null => {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Error,
                message: "Settings document is null or invalid".to_string(),
            });
        }
        _ => {
            issues.push(ValidationIssue {
                severity: IssueSeverity::Error,
                message: format!(
                    "Expected a YAML mapping at root, found: {}",
                    yaml_type_name(yaml)
                ),
            });
        }
    }

    issues
}

/// Get a human-readable name for a YAML value type.
fn yaml_type_name(yaml: &Yaml) -> &'static str {
    match yaml {
        Yaml::Real(_) => "float",
        Yaml::Integer(_) => "integer",
        Yaml::String(_) => "string",
        Yaml::Boolean(_) => "boolean",
        Yaml::Array(_) => "array",
        Yaml::Hash(_) => "mapping",
        Yaml::Alias(_) => "alias",
        Yaml::Null => "null",
        Yaml::BadValue => "bad value",
    }
}

#[cfg(test)]
#[path = "structure_tests.rs"]
mod tests;
