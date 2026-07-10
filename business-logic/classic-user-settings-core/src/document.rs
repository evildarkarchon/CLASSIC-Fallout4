use crate::scan_settings::CrashLogScanSettings;
use crate::{FrontendState, GameSetupSettings};
use classic_settings_core::{
    SchemaVersion, Yaml, YamlSchemaError, extract_schema_version, parse_yaml_content,
};
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};

const CANONICAL_RELATIVE_PATH: &str = "CLASSIC Settings.yaml";
const LEGACY_RELATIVE_PATH: &str = "CLASSIC Data/CLASSIC Settings.yaml";
const CURRENT_SCHEMA_VERSION: SchemaVersion = SchemaVersion::new(1, 0);

/// Root-relative location from which User Settings were opened.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceLocation {
    /// `<CLASSIC root>/CLASSIC Settings.yaml`.
    Canonical,
    /// `<CLASSIC root>/CLASSIC Data/CLASSIC Settings.yaml`.
    Legacy,
    /// Neither supported User Settings path exists.
    Missing,
}

/// Format and schema classification of the opened User Settings document.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocumentClassification {
    /// The current `1.0` nested document shape.
    Current,
    /// A nested document without a schema version.
    Unversioned,
    /// A versioned document older than the current schema.
    Older,
    /// A same-major document with additive fields newer than `1.0`.
    NewerCompatible,
    /// A document from a future, incompatible schema major.
    FutureMajor,
    /// The legacy flat `ClassicConfig` serialization shape.
    LegacyFlat,
    /// A source document exists but cannot be parsed or trusted.
    Malformed,
    /// No User Settings document exists.
    Missing,
}

/// Whether a later User Settings Update may be committed from this open view.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommitEligibility {
    /// The document is safe to use as the base of a later commit.
    Eligible,
    /// The recognized legacy source must be migrated before a commit is allowed.
    RequiresMigration,
    /// The source is untrusted or incompatible and cannot be committed.
    BlockedUntrusted,
}

/// Provenance of a typed preference value.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreferenceOrigin {
    /// A valid value was read from the source document.
    Document,
    /// The setting was absent, so the Rust-owned published default is used.
    Default,
    /// The source could not be trusted, so a safety-oriented fallback is used.
    DegradedFallback,
}

/// Content identity captured when the User Settings view was opened.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Revision {
    /// No source document existed at open time.
    Missing,
    /// A source was selected but its contents could not be read.
    Unavailable,
    /// SHA-256 of the exact source bytes.
    ContentSha256([u8; 32]),
}

/// Machine-readable diagnostic produced while opening User Settings.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Diagnostic {
    code: &'static str,
    message: String,
}

impl Diagnostic {
    /// Creates a structured diagnostic from a stable code and contextual message.
    pub(crate) fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    /// Returns the stable diagnostic code used for programmatic handling.
    pub fn code(&self) -> &'static str {
        self.code
    }

    /// Returns human-readable context for the diagnostic.
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Source metadata for an opened User Settings view.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SettingsSource {
    location: SourceLocation,
    path: Option<PathBuf>,
}

impl SettingsSource {
    /// Returns the root-relative source location classification.
    pub fn location(&self) -> SourceLocation {
        self.location
    }

    /// Returns the selected source path, or `None` when settings are missing.
    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }
}

/// Update-related User Settings consumed by update-check policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UpdatePreferences {
    update_check: bool,
    update_check_origin: PreferenceOrigin,
}

impl UpdatePreferences {
    /// Returns whether first-party update checks are enabled.
    pub fn update_check(&self) -> bool {
        self.update_check
    }

    /// Returns how the update-check value was obtained.
    pub fn update_check_origin(&self) -> PreferenceOrigin {
        self.update_check_origin
    }
}

/// Read-only, typed view of User Settings opened from a CLASSIC root.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserSettings {
    source: SettingsSource,
    classification: DocumentClassification,
    schema_version: Option<(u32, u32)>,
    revision: Revision,
    update_preferences: UpdatePreferences,
    crash_log_scan_settings: CrashLogScanSettings,
    game_setup_settings: GameSetupSettings,
    frontend_state: FrontendState,
    diagnostics: Vec<Diagnostic>,
    original_bytes: Option<Vec<u8>>,
    commit_eligibility: CommitEligibility,
}

impl UserSettings {
    /// Opens User Settings relative to `classic_root` without creating, moving,
    /// repairing, or otherwise modifying either supported source file.
    pub fn open(classic_root: impl AsRef<Path>) -> Self {
        let canonical_path = classic_root.as_ref().join(CANONICAL_RELATIVE_PATH);
        let legacy_path = classic_root.as_ref().join(LEGACY_RELATIVE_PATH);
        let (path, location, bytes) = match std::fs::read(&canonical_path) {
            Ok(bytes) => (canonical_path, SourceLocation::Canonical, bytes),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                match std::fs::read(&legacy_path) {
                    Ok(bytes) => (legacy_path, SourceLocation::Legacy, bytes),
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                        return Self::missing();
                    }
                    Err(error) => {
                        return Self::unreadable(legacy_path, SourceLocation::Legacy, error);
                    }
                }
            }
            Err(error) => {
                return Self::unreadable(canonical_path, SourceLocation::Canonical, error);
            }
        };

        let content = match std::str::from_utf8(&bytes) {
            Ok(content) => content,
            Err(error) => {
                return Self::malformed(
                    path,
                    location,
                    bytes,
                    format!("User Settings are not valid UTF-8: {error}"),
                );
            }
        };
        let mut documents = match parse_yaml_content(path.display().to_string(), content) {
            Ok(documents) if documents.len() == 1 => documents,
            Ok(documents) => {
                return Self::malformed(
                    path,
                    location,
                    bytes,
                    format!(
                        "User Settings must contain exactly one YAML document, found {}",
                        documents.len()
                    ),
                );
            }
            Err(error) => {
                return Self::malformed(path, location, bytes, error.to_string());
            }
        };
        let document = documents.remove(0);
        if !matches!(document, Yaml::Hash(_)) {
            return Self::malformed(
                path,
                location,
                bytes,
                "User Settings root must be a mapping",
            );
        }
        if let Some(group) = invalid_nested_group(&document) {
            return Self::malformed(
                path,
                location,
                bytes,
                format!("User Settings {group} group must be a mapping"),
            );
        }

        // The shared schema extractor intentionally treats YAML null like an
        // absent key. User Settings must distinguish those cases because a
        // present but unusable version cannot be trusted as legacy input.
        let schema_version_present = !matches!(&document["schema_version"], Yaml::BadValue);
        let (classification, schema_version) = match extract_schema_version(&document) {
            Ok(version) if version == CURRENT_SCHEMA_VERSION => (
                DocumentClassification::Current,
                Some((version.major, version.minor)),
            ),
            Ok(version) if version.major == CURRENT_SCHEMA_VERSION.major => (
                DocumentClassification::NewerCompatible,
                Some((version.major, version.minor)),
            ),
            Ok(version) if version.major < CURRENT_SCHEMA_VERSION.major => {
                return Self::incompatible(
                    path,
                    location,
                    bytes,
                    DocumentClassification::Older,
                    Some((version.major, version.minor)),
                    "unsupported_older_schema",
                    format!(
                        "User Settings schema {version} is older than supported schema {CURRENT_SCHEMA_VERSION}"
                    ),
                );
            }
            Ok(version) => {
                return Self::incompatible(
                    path,
                    location,
                    bytes,
                    DocumentClassification::FutureMajor,
                    Some((version.major, version.minor)),
                    "unsupported_future_major_schema",
                    format!(
                        "User Settings schema {version} has a newer major than supported schema {CURRENT_SCHEMA_VERSION}"
                    ),
                );
            }
            Err(YamlSchemaError::Missing) if schema_version_present => {
                return Self::incompatible(
                    path,
                    location,
                    bytes,
                    DocumentClassification::Malformed,
                    None,
                    "invalid_schema_version",
                    "User Settings schema_version must be a quoted MAJOR.MINOR value",
                );
            }
            Err(YamlSchemaError::Missing) if is_legacy_flat_document(&document) => {
                (DocumentClassification::LegacyFlat, None)
            }
            Err(YamlSchemaError::Missing) if is_recognized_nested_document(&document) => {
                (DocumentClassification::Unversioned, None)
            }
            Err(YamlSchemaError::Missing) => {
                return Self::malformed(
                    path,
                    location,
                    bytes,
                    "User Settings do not contain a recognized settings group",
                );
            }
            Err(error) => {
                return Self::incompatible(
                    path,
                    location,
                    bytes,
                    DocumentClassification::Malformed,
                    None,
                    "invalid_schema_version",
                    error.to_string(),
                );
            }
        };
        let update_check_node = if classification == DocumentClassification::LegacyFlat {
            Some(&document["update_check"])
        } else {
            match &document["CLASSIC_Settings"] {
                Yaml::Hash(_) => Some(&document["CLASSIC_Settings"]["Update Check"]),
                Yaml::BadValue => None,
                _ => unreachable!("nested group shapes were validated before classification"),
            }
        };
        let (update_check, update_check_origin, update_diagnostic) = match update_check_node {
            Some(Yaml::Boolean(value)) => (*value, PreferenceOrigin::Document, None),
            None | Some(Yaml::BadValue) => (true, PreferenceOrigin::Default, None),
            _ => (
                false,
                PreferenceOrigin::DegradedFallback,
                Some(Diagnostic::new(
                    "invalid_type_update_check",
                    "CLASSIC_Settings.Update Check must be a boolean",
                )),
            ),
        };
        let (crash_log_scan_settings, scan_diagnostics) =
            if classification == DocumentClassification::LegacyFlat {
                CrashLogScanSettings::from_legacy_flat_document(&document)
            } else {
                CrashLogScanSettings::from_nested_document(&document)
            };
        let (game_setup_settings, game_setup_diagnostics) =
            if classification == DocumentClassification::LegacyFlat {
                GameSetupSettings::from_legacy_flat_document(&document, &crash_log_scan_settings)
            } else {
                GameSetupSettings::from_nested_document(&document, &crash_log_scan_settings)
            };
        let (frontend_state, frontend_diagnostics) =
            if classification == DocumentClassification::LegacyFlat {
                FrontendState::from_legacy_flat_document(&document)
            } else {
                FrontendState::from_nested_document(&document)
            };
        let requires_migration = location == SourceLocation::Legacy
            || matches!(
                classification,
                DocumentClassification::Unversioned | DocumentClassification::LegacyFlat
            );
        let mut diagnostics = if classification == DocumentClassification::LegacyFlat {
            vec![Diagnostic::new(
                "migration_required_flat_classic_config",
                "User Settings use the legacy flat ClassicConfig shape",
            )]
        } else if location == SourceLocation::Legacy {
            vec![Diagnostic::new(
                "migration_required_previous_location",
                "User Settings were opened from the previous CLASSIC Data location",
            )]
        } else if requires_migration {
            vec![Diagnostic::new(
                "migration_required_unversioned_document",
                "User Settings have no schema version and require migration",
            )]
        } else {
            Vec::new()
        };
        diagnostics.extend(update_diagnostic);
        diagnostics.extend(game_setup_diagnostics);
        diagnostics.extend(scan_diagnostics);
        diagnostics.extend(frontend_diagnostics);

        Self {
            source: SettingsSource {
                location,
                path: Some(path),
            },
            classification,
            schema_version,
            revision: Revision::ContentSha256(Sha256::digest(&bytes).into()),
            update_preferences: UpdatePreferences {
                update_check,
                update_check_origin,
            },
            crash_log_scan_settings,
            game_setup_settings,
            frontend_state,
            diagnostics,
            original_bytes: Some(bytes),
            commit_eligibility: if requires_migration {
                CommitEligibility::RequiresMigration
            } else {
                CommitEligibility::Eligible
            },
        }
    }

    /// Builds the no-source view with published Rust-owned defaults.
    fn missing() -> Self {
        Self {
            source: SettingsSource {
                location: SourceLocation::Missing,
                path: None,
            },
            classification: DocumentClassification::Missing,
            schema_version: None,
            revision: Revision::Missing,
            update_preferences: UpdatePreferences {
                update_check: true,
                update_check_origin: PreferenceOrigin::Default,
            },
            crash_log_scan_settings: CrashLogScanSettings::published_defaults(),
            game_setup_settings: GameSetupSettings::published_defaults(),
            frontend_state: FrontendState::published_defaults(),
            diagnostics: Vec::new(),
            original_bytes: None,
            commit_eligibility: CommitEligibility::Eligible,
        }
    }

    /// Builds a degraded view when the selected source cannot be read.
    fn unreadable(path: PathBuf, location: SourceLocation, error: std::io::Error) -> Self {
        Self {
            source: SettingsSource {
                location,
                path: Some(path),
            },
            classification: DocumentClassification::Malformed,
            schema_version: None,
            revision: Revision::Unavailable,
            update_preferences: UpdatePreferences {
                update_check: false,
                update_check_origin: PreferenceOrigin::DegradedFallback,
            },
            crash_log_scan_settings: CrashLogScanSettings::degraded_fallbacks(),
            game_setup_settings: GameSetupSettings::degraded_fallbacks(),
            frontend_state: FrontendState::degraded_fallbacks(),
            diagnostics: vec![
                Diagnostic::new("unreadable_document", error.to_string()),
                Diagnostic::new(
                    "commit_blocked_untrusted_document",
                    "Unreadable User Settings cannot be used as the base of a commit",
                ),
            ],
            original_bytes: None,
            commit_eligibility: CommitEligibility::BlockedUntrusted,
        }
    }

    /// Builds a degraded view while retaining the exact malformed source bytes.
    fn malformed(
        path: PathBuf,
        location: SourceLocation,
        bytes: Vec<u8>,
        message: impl Into<String>,
    ) -> Self {
        Self {
            source: SettingsSource {
                location,
                path: Some(path),
            },
            classification: DocumentClassification::Malformed,
            schema_version: None,
            revision: Revision::ContentSha256(Sha256::digest(&bytes).into()),
            update_preferences: UpdatePreferences {
                update_check: false,
                update_check_origin: PreferenceOrigin::DegradedFallback,
            },
            crash_log_scan_settings: CrashLogScanSettings::degraded_fallbacks(),
            game_setup_settings: GameSetupSettings::degraded_fallbacks(),
            frontend_state: FrontendState::degraded_fallbacks(),
            diagnostics: vec![
                Diagnostic::new("malformed_document", message),
                Diagnostic::new(
                    "commit_blocked_untrusted_document",
                    "Malformed User Settings cannot be used as the base of a commit",
                ),
            ],
            original_bytes: Some(bytes),
            commit_eligibility: CommitEligibility::BlockedUntrusted,
        }
    }

    /// Builds a degraded view for a parsed but incompatible document.
    fn incompatible(
        path: PathBuf,
        location: SourceLocation,
        bytes: Vec<u8>,
        classification: DocumentClassification,
        schema_version: Option<(u32, u32)>,
        code: &'static str,
        message: impl Into<String>,
    ) -> Self {
        Self {
            source: SettingsSource {
                location,
                path: Some(path),
            },
            classification,
            schema_version,
            revision: Revision::ContentSha256(Sha256::digest(&bytes).into()),
            update_preferences: UpdatePreferences {
                update_check: false,
                update_check_origin: PreferenceOrigin::DegradedFallback,
            },
            crash_log_scan_settings: CrashLogScanSettings::degraded_fallbacks(),
            game_setup_settings: GameSetupSettings::degraded_fallbacks(),
            frontend_state: FrontendState::degraded_fallbacks(),
            diagnostics: vec![
                Diagnostic::new(code, message),
                Diagnostic::new(
                    "commit_blocked_untrusted_document",
                    "Incompatible User Settings cannot be used as the base of a commit",
                ),
            ],
            original_bytes: Some(bytes),
            commit_eligibility: CommitEligibility::BlockedUntrusted,
        }
    }

    /// Returns the selected settings source and path.
    pub fn source(&self) -> &SettingsSource {
        &self.source
    }

    /// Returns the source document's format/schema classification.
    pub fn classification(&self) -> DocumentClassification {
        self.classification
    }

    /// Returns the parsed `(major, minor)` schema version when one was present and valid.
    pub fn schema_version(&self) -> Option<(u32, u32)> {
        self.schema_version
    }

    /// Returns the content-derived revision captured by this open.
    pub fn revision(&self) -> &Revision {
        &self.revision
    }

    /// Returns the typed update-preferences group.
    pub fn update_preferences(&self) -> &UpdatePreferences {
        &self.update_preferences
    }

    /// Returns the typed Crash Log Scan settings group.
    pub fn crash_log_scan_settings(&self) -> &CrashLogScanSettings {
        &self.crash_log_scan_settings
    }

    /// Returns the typed Game Setup settings group.
    pub fn game_setup_settings(&self) -> &GameSetupSettings {
        &self.game_setup_settings
    }

    /// Returns the typed, namespaced frontend-state group.
    pub fn frontend_state(&self) -> &FrontendState {
        &self.frontend_state
    }

    /// Returns structured diagnostics in discovery and validation order.
    pub fn diagnostics(&self) -> &[Diagnostic] {
        &self.diagnostics
    }

    /// Returns the exact source bytes retained for semantic preservation.
    pub fn original_bytes(&self) -> Option<&[u8]> {
        self.original_bytes.as_deref()
    }

    /// Returns whether a later explicit User Settings Update may be committed.
    pub fn commit_eligibility(&self) -> CommitEligibility {
        self.commit_eligibility
    }
}

/// Returns whether an unversioned document uses the recognized flat ClassicConfig shape.
fn is_legacy_flat_document(document: &Yaml) -> bool {
    [
        "update_check",
        "fcx_mode",
        "game_version",
        "move_unsolved_logs",
        "paths",
        "formid_databases",
    ]
    .iter()
    .any(|key| !matches!(&document[*key], Yaml::BadValue))
}

/// Returns the first known nested group whose value is not a mapping.
fn invalid_nested_group(document: &Yaml) -> Option<&'static str> {
    ["CLASSIC_Settings", "UI"]
        .into_iter()
        .find(|key| !matches!(&document[*key], Yaml::BadValue | Yaml::Hash(_)))
}

/// Returns whether an unversioned document contains a recognized nested group.
fn is_recognized_nested_document(document: &Yaml) -> bool {
    ["CLASSIC_Settings", "UI"]
        .into_iter()
        .any(|key| matches!(&document[key], Yaml::Hash(_)))
}
