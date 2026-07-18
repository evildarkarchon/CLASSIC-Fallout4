//! Installed YAML Data selection and side-effect-limited inspection.

use crate::client_schemas;
use crate::explicit_yaml_data::{
    ExplicitYamlDataLoadError, GameDataRole, YamlDataContentIdentity, registered_game_data_role,
    validate_game, validate_main,
};
use crate::yamldata::parse_and_merge_yaml_content;
use classic_path_core::yaml_cache_dir_with_env;
use classic_settings_core::{
    Compatibility, SchemaCompat, SchemaVersion, extract_schema_version, schema_compat_check,
};
use classic_shared_core::GameId;
use std::path::{Path, PathBuf};
use thiserror::Error;
use yaml_rust2::Yaml;

/// The update-eligible role being inspected.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataRole {
    /// Global Main YAML Data.
    Main,
    /// Selected-game YAML Data.
    Game,
}

impl std::fmt::Display for InstalledYamlDataRole {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Main => formatter.write_str("Main"),
            Self::Game => formatter.write_str("game"),
        }
    }
}

/// The installed candidate that supplied a selected YAML Data file.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataProvenance {
    /// Canonical per-user updated candidate.
    Updated,
    /// Previous updated sibling used read-only because the canonical file was absent.
    Previous,
    /// Install-tree bundled candidate.
    Bundled,
}

/// Stable category for an inspection diagnostic.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstalledYamlDataDiagnosticKind {
    /// The per-user update cache could not be resolved.
    CacheUnavailable,
    /// A candidate was absent when it was required as the final fallback.
    Missing,
    /// A present candidate could not be read.
    Read,
    /// Candidate bytes were not valid UTF-8.
    InvalidUtf8,
    /// Candidate text was not valid YAML Data.
    Parse,
    /// A parsed candidate omitted or malformed its schema version.
    InvalidSchema,
    /// A candidate schema was outside the client-owned compatibility range.
    IncompatibleSchema,
    /// A candidate failed role-specific semantic validation.
    InvalidRoleData,
}

/// Structured attribution for a cache-resolution or candidate-rejection event.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataDiagnostic {
    role: Option<InstalledYamlDataRole>,
    candidate: Option<InstalledYamlDataProvenance>,
    path: Option<PathBuf>,
    kind: InstalledYamlDataDiagnosticKind,
    message: String,
}

impl InstalledYamlDataDiagnostic {
    /// Return the affected file role, or `None` for installation-wide diagnostics.
    #[must_use]
    pub const fn role(&self) -> Option<InstalledYamlDataRole> {
        self.role
    }

    /// Return the rejected candidate kind, or `None` when no candidate path was available.
    #[must_use]
    pub const fn candidate(&self) -> Option<InstalledYamlDataProvenance> {
        self.candidate
    }

    /// Return the candidate path when the diagnostic is path-attributable.
    #[must_use]
    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }

    /// Return the stable diagnostic category.
    #[must_use]
    pub const fn kind(&self) -> InstalledYamlDataDiagnosticKind {
        self.kind
    }

    /// Return an actionable human-readable explanation.
    #[must_use]
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// One selected update-eligible YAML Data file.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InspectedYamlDataFile {
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    schema_version: SchemaVersion,
    identity: YamlDataContentIdentity,
}

impl InspectedYamlDataFile {
    /// Return whether this is the Main or selected-game file.
    #[must_use]
    pub const fn role(&self) -> InstalledYamlDataRole {
        self.role
    }

    /// Return which installed candidate supplied the selected bytes.
    #[must_use]
    pub const fn provenance(&self) -> InstalledYamlDataProvenance {
        self.provenance
    }

    /// Return the compatible schema version parsed from the selected bytes.
    #[must_use]
    pub const fn schema_version(&self) -> SchemaVersion {
        self.schema_version
    }

    /// Return the SHA-256 and byte length derived from the selected bytes.
    #[must_use]
    pub const fn identity(&self) -> &YamlDataContentIdentity {
        &self.identity
    }
}

/// One installation root and typed game identity to inspect.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataInspectionRequest {
    /// CLASSIC installation root containing `CLASSIC Data/databases`.
    pub installation_root: PathBuf,
    /// Typed game identity used to select registered game YAML Data.
    pub game: GameId,
}

/// Selected update-eligible YAML Data facts from one inspection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledYamlDataInspection {
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: InspectedYamlDataFile,
    game_file: InspectedYamlDataFile,
    diagnostics: Vec<InstalledYamlDataDiagnostic>,
}

impl InstalledYamlDataInspection {
    /// Return the typed game requested by the caller.
    #[must_use]
    pub const fn game(&self) -> GameId {
        self.requested_game
    }

    /// Return the registered data role used for the selected game file.
    #[must_use]
    pub const fn game_data_role(&self) -> GameDataRole {
        self.game_data_role
    }

    /// Return the independently selected Main file facts.
    #[must_use]
    pub const fn main(&self) -> &InspectedYamlDataFile {
        &self.main
    }

    /// Return the independently selected game file facts.
    #[must_use]
    pub const fn game_file(&self) -> &InspectedYamlDataFile {
        &self.game_file
    }

    /// Return structured fallback and cache-resolution diagnostics.
    #[must_use]
    pub fn diagnostics(&self) -> &[InstalledYamlDataDiagnostic] {
        &self.diagnostics
    }
}

/// Failures that prevent inspection from selecting both required files.
#[derive(Debug, Error)]
pub enum InstalledYamlDataInspectionError {
    /// The typed game has no registered YAML Data role in this client.
    #[error("unsupported game for Installed YAML Data inspection: {game}")]
    UnsupportedGame {
        /// Unsupported typed game identity.
        game: GameId,
    },
    /// Neither updated nor bundled data was usable for one required role.
    #[error("no usable Installed YAML Data source for {role}")]
    NoUsableSource {
        /// Required role that could not be selected.
        role: InstalledYamlDataRole,
        /// Every actionable diagnostic observed before selection failed.
        diagnostics: Vec<InstalledYamlDataDiagnostic>,
    },
}

/// Inspect installed Main and game YAML Data without reading or modifying Local Ignore.
///
/// Candidate files are read at most once. Parsing, semantic validation, schema extraction,
/// and content identity all borrow the exact owned bytes from that read. Inspection never
/// creates the cache or promotes, deletes, rewrites, or repairs any candidate.
pub fn inspect_installed_yaml_data(
    request: InstalledYamlDataInspectionRequest,
) -> Result<InstalledYamlDataInspection, InstalledYamlDataInspectionError> {
    inspect_installed_yaml_data_with_env(request, |name| match std::env::var(name) {
        Ok(value) if !value.is_empty() => Some(value),
        _ => None,
    })
}

/// Testable form of [`inspect_installed_yaml_data`] with injected cache environment lookup.
///
/// The environment callback controls only per-user cache resolution. Bundled candidates are
/// always resolved from the request's explicit installation root.
pub fn inspect_installed_yaml_data_with_env<F>(
    request: InstalledYamlDataInspectionRequest,
    env: F,
) -> Result<InstalledYamlDataInspection, InstalledYamlDataInspectionError>
where
    F: Fn(&str) -> Option<String>,
{
    let game_data_role = registered_game_data_role(request.game)
        .ok_or(InstalledYamlDataInspectionError::UnsupportedGame { game: request.game })?;
    let bundled_dir = request
        .installation_root
        .join("CLASSIC Data")
        .join("databases");
    let mut diagnostics = Vec::new();
    let cache_dir = match yaml_cache_dir_with_env(env) {
        Ok(path) => Some(path),
        Err(source) => {
            diagnostics.push(InstalledYamlDataDiagnostic {
                role: None,
                candidate: None,
                path: None,
                kind: InstalledYamlDataDiagnosticKind::CacheUnavailable,
                message: format!(
                    "updated YAML Data cache is unavailable: {source}; bundled candidates remain eligible"
                ),
            });
            None
        }
    };

    let main = select_file(
        InstalledYamlDataRole::Main,
        "CLASSIC Main.yaml",
        client_schemas::MAIN_YAML,
        cache_dir.as_deref(),
        &bundled_dir,
        &mut diagnostics,
    )?;
    let game_file = select_file(
        InstalledYamlDataRole::Game,
        game_file_name(game_data_role),
        client_schemas::GAME_FALLOUT4_YAML,
        cache_dir.as_deref(),
        &bundled_dir,
        &mut diagnostics,
    )?;

    Ok(InstalledYamlDataInspection {
        requested_game: request.game,
        game_data_role,
        main,
        game_file,
        diagnostics,
    })
}

const fn game_file_name(role: GameDataRole) -> &'static str {
    match role {
        GameDataRole::Fallout4 => "CLASSIC Fallout4.yaml",
    }
}

/// Select one installed role using canonical, absent-only previous, then bundled precedence.
///
/// Rejected candidates are appended to `diagnostics`; the function never mutates a candidate.
fn select_file(
    role: InstalledYamlDataRole,
    file_name: &str,
    accepted: SchemaCompat,
    cache_dir: Option<&Path>,
    bundled_dir: &Path,
    diagnostics: &mut Vec<InstalledYamlDataDiagnostic>,
) -> Result<InspectedYamlDataFile, InstalledYamlDataInspectionError> {
    if let Some(cache_dir) = cache_dir {
        let canonical = cache_dir.join(file_name);
        match inspect_candidate(
            role,
            InstalledYamlDataProvenance::Updated,
            &canonical,
            accepted,
        ) {
            CandidateAttempt::Selected(selected) => return Ok(selected),
            CandidateAttempt::Missing => {
                let previous = cache_dir.join(format!("{file_name}.prev"));
                match inspect_candidate(
                    role,
                    InstalledYamlDataProvenance::Previous,
                    &previous,
                    accepted,
                ) {
                    CandidateAttempt::Selected(selected) => return Ok(selected),
                    CandidateAttempt::Rejected(diagnostic) => diagnostics.push(diagnostic),
                    CandidateAttempt::Missing => {}
                }
            }
            CandidateAttempt::Rejected(diagnostic) => diagnostics.push(diagnostic),
        }
    }

    let bundled = bundled_dir.join(file_name);
    match inspect_candidate(
        role,
        InstalledYamlDataProvenance::Bundled,
        &bundled,
        accepted,
    ) {
        CandidateAttempt::Selected(selected) => Ok(selected),
        CandidateAttempt::Rejected(diagnostic) => {
            diagnostics.push(diagnostic);
            Err(InstalledYamlDataInspectionError::NoUsableSource {
                role,
                diagnostics: diagnostics.clone(),
            })
        }
        CandidateAttempt::Missing => {
            diagnostics.push(candidate_diagnostic(
                role,
                InstalledYamlDataProvenance::Bundled,
                &bundled,
                InstalledYamlDataDiagnosticKind::Missing,
                "bundled YAML Data candidate is missing",
            ));
            Err(InstalledYamlDataInspectionError::NoUsableSource {
                role,
                diagnostics: diagnostics.clone(),
            })
        }
    }
}

enum CandidateAttempt {
    Selected(InspectedYamlDataFile),
    Missing,
    Rejected(InstalledYamlDataDiagnostic),
}

/// Read, parse, schema-gate, semantically validate, and identify one exact candidate.
///
/// `Missing` is reserved for `NotFound`; every other failure retains structured attribution.
fn inspect_candidate(
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    path: &Path,
    accepted: SchemaCompat,
) -> CandidateAttempt {
    let bytes = match std::fs::read(path) {
        Ok(bytes) => bytes,
        Err(source) if source.kind() == std::io::ErrorKind::NotFound => {
            return CandidateAttempt::Missing;
        }
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::Read,
                format!("failed to read candidate: {source}"),
            ));
        }
    };
    let content = match std::str::from_utf8(&bytes) {
        Ok(content) => content,
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::InvalidUtf8,
                format!("candidate is not UTF-8: {source}"),
            ));
        }
    };
    let yaml = match parse_candidate(role, provenance, path, content) {
        Ok(yaml) => yaml,
        Err(diagnostic) => return CandidateAttempt::Rejected(diagnostic),
    };
    let schema_version = match extract_schema_version(&yaml) {
        Ok(version) => version,
        Err(source) => {
            return CandidateAttempt::Rejected(candidate_diagnostic(
                role,
                provenance,
                path,
                InstalledYamlDataDiagnosticKind::InvalidSchema,
                format!("candidate schema version is invalid: {source}"),
            ));
        }
    };
    if let incompatible @ (Compatibility::IncompatibleMajor { .. }
    | Compatibility::IncompatibleMinor { .. }) = schema_compat_check(&schema_version, &accepted)
    {
        return CandidateAttempt::Rejected(candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::IncompatibleSchema,
            format!("candidate schema version {schema_version} is incompatible: {incompatible:?}"),
        ));
    }
    if let Err(source) = validate_candidate_role(role, &yaml, path) {
        return CandidateAttempt::Rejected(candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::InvalidRoleData,
            source,
        ));
    }

    CandidateAttempt::Selected(InspectedYamlDataFile {
        role,
        provenance,
        schema_version,
        identity: YamlDataContentIdentity::from_bytes(&bytes),
    })
}

/// Parse one candidate as the mergeable YAML stream required by its installed role.
fn parse_candidate(
    role: InstalledYamlDataRole,
    provenance: InstalledYamlDataProvenance,
    path: &Path,
    content: &str,
) -> Result<Yaml, InstalledYamlDataDiagnostic> {
    let (parse_label, empty_label) = match role {
        InstalledYamlDataRole::Main => ("installed Main YAML", "Installed Main YAML"),
        InstalledYamlDataRole::Game => ("installed game YAML", "Installed game YAML"),
    };
    parse_and_merge_yaml_content(parse_label, empty_label, content).map_err(|source| {
        candidate_diagnostic(
            role,
            provenance,
            path,
            InstalledYamlDataDiagnosticKind::Parse,
            format!("failed to parse candidate: {source}"),
        )
    })
}

/// Apply the strict explicit-loader semantic validator for an installed role.
fn validate_candidate_role(
    role: InstalledYamlDataRole,
    yaml: &Yaml,
    path: &Path,
) -> Result<(), String> {
    let result = match role {
        InstalledYamlDataRole::Main => validate_main(yaml, path),
        InstalledYamlDataRole::Game => validate_game(yaml, path),
    };
    result.map_err(|source| match source {
        ExplicitYamlDataLoadError::InvalidRoleData { reason, .. } => reason,
        other => other.to_string(),
    })
}

/// Build one path-attributed rejection diagnostic without changing the rejected file.
fn candidate_diagnostic(
    role: InstalledYamlDataRole,
    candidate: InstalledYamlDataProvenance,
    path: &Path,
    kind: InstalledYamlDataDiagnosticKind,
    message: impl Into<String>,
) -> InstalledYamlDataDiagnostic {
    InstalledYamlDataDiagnostic {
        role: Some(role),
        candidate: Some(candidate),
        path: Some(path.to_path_buf()),
        kind,
        message: message.into(),
    }
}

#[cfg(test)]
#[path = "installed_yaml_data_tests.rs"]
mod tests;
