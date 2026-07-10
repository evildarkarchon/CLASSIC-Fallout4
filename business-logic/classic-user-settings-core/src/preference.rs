use crate::document::{Diagnostic, PreferenceOrigin};
use classic_settings_core::Yaml;

/// One typed preference together with its source provenance.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Preference<T> {
    pub(crate) value: T,
    pub(crate) origin: PreferenceOrigin,
}

impl<T> Preference<T> {
    /// Creates a typed preference with its source provenance.
    pub(crate) fn new(value: T, origin: PreferenceOrigin) -> Self {
        Self { value, origin }
    }
}

/// Stable labels and diagnostics for one optional absolute-path field.
#[derive(Debug, Clone, Copy)]
pub(crate) struct OptionalPathField {
    label: &'static str,
    invalid_type_code: &'static str,
    invalid_path_code: &'static str,
}

impl OptionalPathField {
    /// Describes how one published or compatibility path label is diagnosed.
    pub(crate) const fn new(
        label: &'static str,
        invalid_type_code: &'static str,
        invalid_path_code: &'static str,
    ) -> Self {
        Self {
            label,
            invalid_type_code,
            invalid_path_code,
        }
    }
}

/// Canonical resolution plus the separately typed compatibility-alias value.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct AliasedOptionalPathPreference {
    pub(crate) resolved: Preference<Option<String>>,
    pub(crate) alias: Preference<Option<String>>,
}

/// Projects one optional absolute path without changing valid path spelling.
pub(crate) fn optional_absolute_path_preference(
    node: &Yaml,
    field: OptionalPathField,
    diagnostics: &mut Vec<Diagnostic>,
) -> Preference<Option<String>> {
    let classified = classify_optional_absolute_path(node);
    push_optional_path_diagnostic(&classified, field, diagnostics);
    classified.preference()
}

/// Resolves a canonical optional path ahead of one compatibility alias.
///
/// A valid canonical value, including explicit null or an empty string, wins.
/// Invalid canonical values may fall back to a valid alias while retaining the
/// canonical diagnostic. Invalid aliases are ignored when the canonical value is valid.
pub(crate) fn aliased_optional_absolute_path_preference(
    canonical_node: &Yaml,
    alias_node: &Yaml,
    canonical_field: OptionalPathField,
    alias_field: OptionalPathField,
    conflict_code: &'static str,
    conflict_message: &'static str,
    diagnostics: &mut Vec<Diagnostic>,
) -> AliasedOptionalPathPreference {
    let canonical = classify_optional_absolute_path(canonical_node);
    let alias = classify_optional_absolute_path(alias_node);
    let alias_preference = alias.preference();

    let resolved = match (&canonical, &alias) {
        (OptionalPathNode::Valid(canonical), OptionalPathNode::Valid(alias)) => {
            if canonical != alias {
                diagnostics.push(Diagnostic::new(conflict_code, conflict_message));
            }
            Preference::new(canonical.clone(), PreferenceOrigin::Document)
        }
        (OptionalPathNode::Valid(canonical), _) => {
            Preference::new(canonical.clone(), PreferenceOrigin::Document)
        }
        (OptionalPathNode::Missing, OptionalPathNode::Valid(alias)) => {
            Preference::new(alias.clone(), PreferenceOrigin::Document)
        }
        (
            invalid @ (OptionalPathNode::InvalidType | OptionalPathNode::InvalidPath),
            OptionalPathNode::Valid(alias),
        ) => {
            push_optional_path_diagnostic(invalid, canonical_field, diagnostics);
            Preference::new(alias.clone(), PreferenceOrigin::Document)
        }
        (OptionalPathNode::Missing, OptionalPathNode::Missing) => {
            Preference::new(None, PreferenceOrigin::Default)
        }
        (OptionalPathNode::Missing, invalid) => {
            push_optional_path_diagnostic(invalid, alias_field, diagnostics);
            Preference::new(None, PreferenceOrigin::DegradedFallback)
        }
        (invalid, _) => {
            push_optional_path_diagnostic(invalid, canonical_field, diagnostics);
            Preference::new(None, PreferenceOrigin::DegradedFallback)
        }
    };

    AliasedOptionalPathPreference {
        resolved,
        alias: alias_preference,
    }
}

/// Accepts native, Unix/Proton, Windows drive, and UNC absolute paths on every platform.
pub(crate) fn is_absolute_user_path(path: &str) -> bool {
    let bytes = path.as_bytes();
    std::path::Path::new(path).is_absolute()
        // User Settings may be inspected off-device, so Unix/Proton paths must
        // remain valid even when CLASSIC itself is running on Windows.
        || path.starts_with('/')
        || matches!(bytes, [drive, b':', slash, ..] if drive.is_ascii_alphabetic() && matches!(slash, b'/' | b'\\'))
        || path.starts_with("\\\\")
        || path.starts_with("//")
}

/// Parsed state of one optional absolute-path YAML node.
#[derive(Debug, Clone, PartialEq, Eq)]
enum OptionalPathNode {
    Missing,
    Valid(Option<String>),
    InvalidType,
    InvalidPath,
}

impl OptionalPathNode {
    /// Projects the classified node into its typed value and provenance.
    fn preference(&self) -> Preference<Option<String>> {
        match self {
            Self::Missing => Preference::new(None, PreferenceOrigin::Default),
            Self::Valid(value) => Preference::new(value.clone(), PreferenceOrigin::Document),
            Self::InvalidType | Self::InvalidPath => {
                Preference::new(None, PreferenceOrigin::DegradedFallback)
            }
        }
    }
}

/// Classifies one optional absolute-path node without changing valid spelling.
fn classify_optional_absolute_path(node: &Yaml) -> OptionalPathNode {
    match node {
        Yaml::String(value) if value.is_empty() => OptionalPathNode::Valid(None),
        Yaml::String(value) if is_absolute_user_path(value) => {
            OptionalPathNode::Valid(Some(value.clone()))
        }
        Yaml::String(_) => OptionalPathNode::InvalidPath,
        Yaml::Null => OptionalPathNode::Valid(None),
        Yaml::BadValue => OptionalPathNode::Missing,
        _ => OptionalPathNode::InvalidType,
    }
}

/// Appends the stable diagnostic for one invalid optional path node.
fn push_optional_path_diagnostic(
    node: &OptionalPathNode,
    field: OptionalPathField,
    diagnostics: &mut Vec<Diagnostic>,
) {
    match node {
        OptionalPathNode::InvalidType => diagnostics.push(Diagnostic::new(
            field.invalid_type_code,
            format!("{} must be a string or null", field.label),
        )),
        OptionalPathNode::InvalidPath => diagnostics.push(Diagnostic::new(
            field.invalid_path_code,
            format!("{} must be empty or an absolute path", field.label),
        )),
        OptionalPathNode::Missing | OptionalPathNode::Valid(_) => {}
    }
}
