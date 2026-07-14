//! Deterministic, side-effect-free planning for explicit User Settings migrations.

use crate::{DocumentClassification, Revision, SourceLocation, UserSettings};
use classic_settings_core::{Yaml, YamlOperations, parse_yaml_content};
use sha2::{Digest, Sha256};
use std::fmt;

const CANONICAL_RELATIVE_PATH: &str = "CLASSIC Settings.yaml";
const LEGACY_RELATIVE_PATH: &str = "CLASSIC Data/CLASSIC Settings.yaml";

/// The current User Settings schema understood by this client.
pub const CURRENT_USER_SETTINGS_SCHEMA_VERSION: UserSettingsSchemaVersion =
    UserSettingsSchemaVersion::new(1, 0);

/// Explicit major/minor User Settings schema version.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct UserSettingsSchemaVersion {
    major: u32,
    minor: u32,
}

impl UserSettingsSchemaVersion {
    /// Creates a schema version from its compatibility components.
    pub const fn new(major: u32, minor: u32) -> Self {
        Self { major, minor }
    }

    /// Returns the breaking-change component.
    pub const fn major(self) -> u32 {
        self.major
    }

    /// Returns the additive-change component.
    pub const fn minor(self) -> u32 {
        self.minor
    }
}

impl fmt::Display for UserSettingsSchemaVersion {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}.{}", self.major, self.minor)
    }
}

/// One endpoint in a proposed User Settings version/location transition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MigrationEndpoint {
    location: SourceLocation,
    schema_version: Option<UserSettingsSchemaVersion>,
}

impl MigrationEndpoint {
    /// Returns the root-relative document location.
    pub const fn location(&self) -> SourceLocation {
        self.location
    }

    /// Returns the explicit schema version, or `None` for a legacy unversioned form.
    pub const fn schema_version(&self) -> Option<UserSettingsSchemaVersion> {
        self.schema_version
    }
}

/// Stable category for one reviewable migration change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MigrationChangeKind {
    /// Move the document between supported root-relative locations.
    LocationTransition,
    /// Add or change the explicit major/minor schema version.
    SchemaVersionTransition,
    /// Move a field from a legacy document shape to its canonical path.
    FieldTransition,
    /// Replace a compatibility key alias with its canonical key.
    AliasCanonicalization,
    /// Replace a supported scalar spelling with its canonical spelling.
    KnownValueCanonicalization,
}

/// One ordered, reversible change in a User Settings migration plan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MigrationChange {
    kind: MigrationChangeKind,
    source_path: Option<String>,
    target_path: Option<String>,
    before: Option<String>,
    after: Option<String>,
}

impl MigrationChange {
    /// Returns the stable change category.
    pub const fn kind(&self) -> MigrationChangeKind {
        self.kind
    }

    /// Returns the source pointer or relative path, when applicable.
    pub fn source_path(&self) -> Option<&str> {
        self.source_path.as_deref()
    }

    /// Returns the target pointer or relative path, when applicable.
    pub fn target_path(&self) -> Option<&str> {
        self.target_path.as_deref()
    }

    /// Returns a deterministic YAML/text representation of the value before the change.
    pub fn before(&self) -> Option<&str> {
        self.before.as_deref()
    }

    /// Returns a deterministic YAML/text representation of the value after the change.
    pub fn after(&self) -> Option<&str> {
        self.after.as_deref()
    }

    /// Returns the inverse review row without changing either document.
    fn reversed(&self) -> Self {
        Self {
            kind: self.kind,
            source_path: self.target_path.clone(),
            target_path: self.source_path.clone(),
            before: self.after.clone(),
            after: self.before.clone(),
        }
    }
}

/// Structured reason that a migration plan cannot be produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MigrationDiagnostic {
    code: &'static str,
    message: String,
}

impl MigrationDiagnostic {
    /// Creates one stable planning diagnostic.
    fn new(code: &'static str, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    /// Returns the stable programmatic diagnostic code.
    pub const fn code(&self) -> &'static str {
        self.code
    }

    /// Returns human-readable diagnostic context.
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Immutable, revision-anchored proposal for an explicit User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UserSettingsMigrationPlan {
    required: bool,
    base_revision: Revision,
    source: MigrationEndpoint,
    target: MigrationEndpoint,
    changes: Vec<MigrationChange>,
    original_bytes: Vec<u8>,
    proposed_bytes: Vec<u8>,
    pub(crate) persistence_attested: bool,
}

impl UserSettingsMigrationPlan {
    /// Returns whether version or location compatibility requires this plan before ordinary commits.
    pub const fn required(&self) -> bool {
        self.required
    }

    /// Returns the exact content revision against which the plan was produced.
    pub fn base_revision(&self) -> &Revision {
        &self.base_revision
    }

    /// Returns the current version/location endpoint.
    pub const fn source(&self) -> &MigrationEndpoint {
        &self.source
    }

    /// Returns the proposed version/location endpoint.
    pub const fn target(&self) -> &MigrationEndpoint {
        &self.target
    }

    /// Returns ordered review rows describing every proposed transition.
    pub fn changes(&self) -> &[MigrationChange] {
        &self.changes
    }

    /// Returns the exact opened bytes retained for reversal and later backup verification.
    pub fn original_bytes(&self) -> &[u8] {
        &self.original_bytes
    }

    /// Returns the deterministic proposed document bytes without publishing them.
    pub fn proposed_bytes(&self) -> &[u8] {
        &self.proposed_bytes
    }

    /// Builds the exact inverse plan entirely in memory.
    ///
    /// The returned plan swaps endpoints and byte payloads and reverses the ordered review rows;
    /// it performs no filesystem access and is involutive.
    pub fn reverse_in_memory(&self) -> Self {
        Self {
            required: self.required,
            base_revision: Revision::ContentSha256(Sha256::digest(&self.proposed_bytes).into()),
            source: self.target,
            target: self.source,
            changes: self
                .changes
                .iter()
                .rev()
                .map(MigrationChange::reversed)
                .collect(),
            original_bytes: self.proposed_bytes.clone(),
            proposed_bytes: self.original_bytes.clone(),
            persistence_attested: self.persistence_attested,
        }
    }
}

/// Reconstructs a review-only plan from binding-safe domain components.
///
/// This conversion lets thin language adapters delegate exact reversal semantics to the core
/// after flattening a plan for callers. Reconstructed plans are deliberately unattested and
/// therefore cannot authorize filesystem persistence through [`UserSettingsMigrationPlan::apply`].
impl
    From<(
        bool,
        (SourceLocation, Option<UserSettingsSchemaVersion>),
        (SourceLocation, Option<UserSettingsSchemaVersion>),
        Vec<(
            MigrationChangeKind,
            Option<String>,
            Option<String>,
            Option<String>,
            Option<String>,
        )>,
        Vec<u8>,
        Vec<u8>,
    )> for UserSettingsMigrationPlan
{
    fn from(
        (required, source, target, changes, original_bytes, proposed_bytes): (
            bool,
            (SourceLocation, Option<UserSettingsSchemaVersion>),
            (SourceLocation, Option<UserSettingsSchemaVersion>),
            Vec<(
                MigrationChangeKind,
                Option<String>,
                Option<String>,
                Option<String>,
                Option<String>,
            )>,
            Vec<u8>,
            Vec<u8>,
        ),
    ) -> Self {
        Self {
            required,
            base_revision: Revision::ContentSha256(Sha256::digest(&original_bytes).into()),
            source: MigrationEndpoint {
                location: source.0,
                schema_version: source.1,
            },
            target: MigrationEndpoint {
                location: target.0,
                schema_version: target.1,
            },
            changes: changes
                .into_iter()
                .map(
                    |(kind, source_path, target_path, before, after)| MigrationChange {
                        kind,
                        source_path,
                        target_path,
                        before,
                        after,
                    },
                )
                .collect(),
            original_bytes,
            proposed_bytes,
            persistence_attested: false,
        }
    }
}

/// Result of planning an explicit User Settings migration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MigrationPlanningOutcome {
    /// The snapshot is missing or already current with no explicit cleanup to propose.
    NotRequired,
    /// A deterministic required migration or optional canonicalization plan is available.
    Planned(UserSettingsMigrationPlan),
    /// The source remains read-only because no trusted migration edge is available.
    Unsupported(Vec<MigrationDiagnostic>),
}

impl UserSettings {
    /// Produces a deterministic, reversible migration plan from this opened snapshot.
    ///
    /// Planning reparses only the exact retained bytes and performs no filesystem reads, writes,
    /// directory creation, relocation, timestamp changes, or backup work. Current documents may
    /// yield an optional plan when known compatibility aliases can be canonicalized explicitly.
    pub fn plan_migration(&self) -> MigrationPlanningOutcome {
        match self.classification() {
            DocumentClassification::Missing => return MigrationPlanningOutcome::NotRequired,
            DocumentClassification::Older => {
                let version = self.schema_version().map_or_else(
                    || "unknown".to_string(),
                    |(major, minor)| format!("{major}.{minor}"),
                );
                return unsupported(
                    "unsupported_schema_version_gap",
                    format!(
                        "User Settings schema {version} has no registered migration edge to {}",
                        CURRENT_USER_SETTINGS_SCHEMA_VERSION
                    ),
                );
            }
            DocumentClassification::FutureMajor => {
                return unsupported(
                    "future_major_schema_read_only",
                    "Future-major User Settings remain degraded and read-only",
                );
            }
            DocumentClassification::Malformed => {
                return unsupported(
                    "migration_source_untrusted",
                    "Malformed or unreadable User Settings cannot be migrated safely",
                );
            }
            DocumentClassification::Current
            | DocumentClassification::NewerCompatible
            | DocumentClassification::Unversioned
            | DocumentClassification::LegacyFlat => {}
        }

        let Some(original_bytes) = self.original_bytes() else {
            return unsupported(
                "migration_source_unavailable",
                "The opened User Settings snapshot has no retained source bytes",
            );
        };
        let mut document = match parse_retained_document(original_bytes) {
            Ok(document) => document,
            Err(message) => return unsupported("migration_source_untrusted", message),
        };

        let source_version = self
            .schema_version()
            .map(|(major, minor)| UserSettingsSchemaVersion::new(major, minor));
        let target_version = source_version.or(Some(CURRENT_USER_SETTINGS_SCHEMA_VERSION));
        let source = MigrationEndpoint {
            location: self.source().location(),
            schema_version: source_version,
        };
        let target = MigrationEndpoint {
            location: SourceLocation::Canonical,
            schema_version: target_version,
        };
        let required = self.source().location() == SourceLocation::Legacy
            || matches!(
                self.classification(),
                DocumentClassification::Unversioned | DocumentClassification::LegacyFlat
            );
        let mut changes = Vec::new();

        if source.location != target.location {
            changes.push(MigrationChange {
                kind: MigrationChangeKind::LocationTransition,
                source_path: Some(relative_path(source.location).to_string()),
                target_path: Some(CANONICAL_RELATIVE_PATH.to_string()),
                before: None,
                after: None,
            });
        }

        let changed_document = if self.classification() == DocumentClassification::LegacyFlat {
            document = match migrate_flat_document(&document, &mut changes) {
                Ok(document) => document,
                Err(message) => return unsupported("migration_plan_failed", message),
            };
            true
        } else {
            match migrate_nested_document(
                &mut document,
                self,
                source_version,
                target_version.expect("trusted documents always have a target version"),
                &mut changes,
            ) {
                Ok(changed) => changed,
                Err(message) => return unsupported("migration_plan_failed", message),
            }
        };

        if changes.is_empty() {
            return MigrationPlanningOutcome::NotRequired;
        }
        let proposed_bytes = if changed_document {
            match serialize_document(&document) {
                Ok(bytes) => bytes,
                Err(message) => return unsupported("migration_plan_failed", message),
            }
        } else {
            original_bytes.to_vec()
        };

        MigrationPlanningOutcome::Planned(UserSettingsMigrationPlan {
            required,
            base_revision: self.revision().clone(),
            source,
            target,
            changes,
            original_bytes: original_bytes.to_vec(),
            proposed_bytes,
            persistence_attested: true,
        })
    }
}

/// Returns one unsupported planning result with a stable diagnostic.
fn unsupported(code: &'static str, message: impl Into<String>) -> MigrationPlanningOutcome {
    MigrationPlanningOutcome::Unsupported(vec![MigrationDiagnostic::new(code, message)])
}

/// Parses exactly one retained User Settings YAML document.
fn parse_retained_document(bytes: &[u8]) -> Result<Yaml, String> {
    let content = std::str::from_utf8(bytes).map_err(|error| error.to_string())?;
    let mut documents = parse_yaml_content("retained User Settings migration source", content)
        .map_err(|error| error.to_string())?;
    if documents.len() != 1 {
        return Err(format!(
            "expected one retained User Settings document, found {}",
            documents.len()
        ));
    }
    Ok(documents.remove(0))
}

/// Plans migration of the recognized flat ClassicConfig shape into the current nested schema.
fn migrate_flat_document(
    source: &Yaml,
    changes: &mut Vec<MigrationChange>,
) -> Result<Yaml, String> {
    let operations = YamlOperations::new();
    let mut target = Yaml::Hash(Default::default());
    target = operations
        .set_setting(
            &target,
            "schema_version",
            Yaml::String(CURRENT_USER_SETTINGS_SCHEMA_VERSION.to_string()),
        )
        .map_err(|error| error.to_string())?;
    changes.push(MigrationChange {
        kind: MigrationChangeKind::SchemaVersionTransition,
        source_path: None,
        target_path: Some("/schema_version".to_string()),
        before: None,
        after: Some(CURRENT_USER_SETTINGS_SCHEMA_VERSION.to_string()),
    });

    let mappings: &[(&[&str], &str, &str)] = &[
        (&["fcx_mode"], "/fcx_mode", "CLASSIC_Settings.FCX Mode"),
        (
            &["show_formid_values"],
            "/show_formid_values",
            "CLASSIC_Settings.Show FormID Values",
        ),
        (
            &["stat_logging"],
            "/stat_logging",
            "CLASSIC_Settings.Show Statistics",
        ),
        (
            &["move_unsolved_logs"],
            "/move_unsolved_logs",
            "CLASSIC_Settings.Move Unsolved Logs",
        ),
        (
            &["unsolved_logs_destination"],
            "/unsolved_logs_destination",
            "CLASSIC_Settings.Unsolved Logs Destination",
        ),
        (
            &["simplify_logs"],
            "/simplify_logs",
            "CLASSIC_Settings.Simplify Logs",
        ),
        (
            &["update_check"],
            "/update_check",
            "CLASSIC_Settings.Update Check",
        ),
        (
            &["game_version"],
            "/game_version",
            "CLASSIC_Settings.Game Version",
        ),
        (
            &["update_source"],
            "/update_source",
            "CLASSIC_Settings.Update Source",
        ),
        (
            &["paths", "ini_folder"],
            "/paths/ini_folder",
            "CLASSIC_Settings.INI Folder Path",
        ),
        (
            &["paths", "docs_root"],
            "/paths/docs_root",
            "CLASSIC_Settings.Documents Folder Path",
        ),
        (
            &["paths", "scan_custom"],
            "/paths/scan_custom",
            "CLASSIC_Settings.SCAN Custom Path",
        ),
        (
            &["paths", "mods_folder"],
            "/paths/mods_folder",
            "CLASSIC_Settings.MODS Folder Path",
        ),
        (
            &["paths", "game_root"],
            "/paths/game_root",
            "CLASSIC_Settings.Game Folder Path",
        ),
        (
            &["formid_databases"],
            "/formid_databases",
            "CLASSIC_Settings.FormID Databases",
        ),
        (
            &["auto_switch_to_results"],
            "/auto_switch_to_results",
            "UI.preferences.auto_switch_after_scan",
        ),
        (
            &["auto_refresh_interval_ms"],
            "/auto_refresh_interval_ms",
            "UI.preferences.auto_refresh_interval_ms",
        ),
    ];

    for (source_segments, source_pointer, target_path) in mappings {
        let Some(value) = get_path(source, source_segments) else {
            continue;
        };
        let migrated = canonical_flat_value(source_segments, value);
        target = operations
            .set_setting(&target, target_path, migrated.clone())
            .map_err(|error| error.to_string())?;
        changes.push(MigrationChange {
            kind: MigrationChangeKind::FieldTransition,
            source_path: Some((*source_pointer).to_string()),
            target_path: Some(format!("/{}", target_path.replace('.', "/"))),
            before: yaml_fragment(value),
            after: yaml_fragment(&migrated),
        });
    }

    // Known flat leaves are removed from the preserved remainder so they cannot shadow the
    // canonical nested projection; unrelated third-party content remains semantically intact.
    let mut remainder = source.clone();
    for (segments, _, _) in mappings {
        remove_path(&mut remainder, segments);
    }
    remove_empty_mapping(&mut remainder, &["paths"]);
    merge_unrecognized_root(&mut target, remainder);
    Ok(target)
}

/// Canonicalizes aliases in an otherwise nested document and adds a missing version.
fn migrate_nested_document(
    document: &mut Yaml,
    settings: &UserSettings,
    source_version: Option<UserSettingsSchemaVersion>,
    target_version: UserSettingsSchemaVersion,
    changes: &mut Vec<MigrationChange>,
) -> Result<bool, String> {
    let operations = YamlOperations::new();
    let mut changed = false;
    if source_version.is_none() {
        *document = operations
            .set_setting(
                document,
                "schema_version",
                Yaml::String(target_version.to_string()),
            )
            .map_err(|error| error.to_string())?;
        changes.push(MigrationChange {
            kind: MigrationChangeKind::SchemaVersionTransition,
            source_path: None,
            target_path: Some("/schema_version".to_string()),
            before: None,
            after: Some(target_version.to_string()),
        });
        changed = true;
    }

    changed |= canonicalize_key_alias(
        document,
        &["CLASSIC_Settings", "Staging Mods Folder"],
        &["CLASSIC_Settings", "MODS Folder Path"],
        optional_string_yaml(settings.game_setup_settings().mods_root()),
        changes,
    )?;
    changed |= canonicalize_key_alias(
        document,
        &["CLASSIC_Settings", "Custom Scan Folder"],
        &["CLASSIC_Settings", "SCAN Custom Path"],
        optional_string_yaml(settings.game_setup_settings().custom_scan_input()),
        changes,
    )?;
    changed |= canonicalize_key_alias(
        document,
        &["CLASSIC_Settings", "Auto Switch After Scan"],
        &["UI", "preferences", "auto_switch_after_scan"],
        Yaml::Boolean(
            settings
                .frontend_state()
                .preferences()
                .auto_switch_after_scan(),
        ),
        changes,
    )?;
    changed |= canonicalize_scalar_alias(
        document,
        &["CLASSIC_Settings", "Game Version"],
        &[("Auto", "auto"), ("AE", "AnniversaryEdition")],
        changes,
    )?;
    changed |= canonicalize_scalar_alias(
        document,
        &["CLASSIC_Settings", "Managed Game"],
        &[
            ("Fallout4", "Fallout 4"),
            ("Fallout4VR", "Fallout 4 VR"),
            ("Skyrim", "Skyrim SE"),
        ],
        changes,
    )?;
    Ok(changed)
}

/// Replaces one key alias with the canonical path while respecting canonical precedence.
fn canonicalize_key_alias(
    document: &mut Yaml,
    alias_path: &[&str],
    canonical_path: &[&str],
    effective_value: Yaml,
    changes: &mut Vec<MigrationChange>,
) -> Result<bool, String> {
    let Some(alias_value) = get_path(document, alias_path).cloned() else {
        return Ok(false);
    };
    let operations = YamlOperations::new();
    *document = operations
        .set_setting(document, &canonical_path.join("."), effective_value.clone())
        .map_err(|error| error.to_string())?;
    remove_path(document, alias_path);
    changes.push(MigrationChange {
        kind: MigrationChangeKind::AliasCanonicalization,
        source_path: Some(pointer(alias_path)),
        target_path: Some(pointer(canonical_path)),
        before: yaml_fragment(&alias_value),
        after: yaml_fragment(&effective_value),
    });
    Ok(true)
}

/// Converts a typed optional string into its canonical YAML scalar representation.
fn optional_string_yaml(value: Option<&str>) -> Yaml {
    value.map_or(Yaml::Null, |value| Yaml::String(value.to_string()))
}

/// Rewrites one recognized scalar alias without changing unrelated document content.
fn canonicalize_scalar_alias(
    document: &mut Yaml,
    path: &[&str],
    aliases: &[(&str, &str)],
    changes: &mut Vec<MigrationChange>,
) -> Result<bool, String> {
    let Some(value) = get_path(document, path).and_then(Yaml::as_str) else {
        return Ok(false);
    };
    let Some((_, canonical)) = aliases.iter().find(|(alias, _)| *alias == value) else {
        return Ok(false);
    };
    let before = value.to_string();
    let after = Yaml::String((*canonical).to_string());
    *document = YamlOperations::new()
        .set_setting(document, &path.join("."), after.clone())
        .map_err(|error| error.to_string())?;
    changes.push(MigrationChange {
        kind: MigrationChangeKind::KnownValueCanonicalization,
        source_path: Some(pointer(path)),
        target_path: Some(pointer(path)),
        before: Some(before),
        after: yaml_fragment(&after),
    });
    Ok(true)
}

/// Returns a nested YAML node by string-key path, excluding absent `BadValue` sentinels.
fn get_path<'a>(document: &'a Yaml, path: &[&str]) -> Option<&'a Yaml> {
    let mut current = document;
    for segment in path {
        let Yaml::Hash(mapping) = current else {
            return None;
        };
        current = mapping.get(&Yaml::String((*segment).to_string()))?;
    }
    (!matches!(current, Yaml::BadValue)).then_some(current)
}

/// Removes a nested YAML node and returns whether the complete path existed.
fn remove_path(document: &mut Yaml, path: &[&str]) -> bool {
    let Some((segment, remainder)) = path.split_first() else {
        return false;
    };
    let Yaml::Hash(mapping) = document else {
        return false;
    };
    let key = Yaml::String((*segment).to_string());
    if remainder.is_empty() {
        return mapping.remove(&key).is_some();
    }
    mapping
        .get_mut(&key)
        .is_some_and(|child| remove_path(child, remainder))
}

/// Removes an empty mapping left after extracting recognized legacy leaves.
fn remove_empty_mapping(document: &mut Yaml, path: &[&str]) {
    let is_empty =
        matches!(get_path(document, path), Some(Yaml::Hash(mapping)) if mapping.is_empty());
    if is_empty {
        remove_path(document, path);
    }
}

/// Adds preserved unrecognized root entries after canonical migration-owned groups.
fn merge_unrecognized_root(target: &mut Yaml, remainder: Yaml) {
    let (Yaml::Hash(target), Yaml::Hash(remainder)) = (target, remainder) else {
        return;
    };
    for (key, value) in remainder {
        target.entry(key).or_insert(value);
    }
}

/// Applies the one legacy scalar spelling transformation defined by the compatibility corpus.
fn canonical_flat_value(path: &[&str], value: &Yaml) -> Yaml {
    if path == ["update_source"] && value.as_str() == Some("github") {
        return Yaml::String("GitHub".to_string());
    }
    value.clone()
}

/// Serializes a planned YAML document deterministically with the shared emitter.
fn serialize_document(document: &Yaml) -> Result<Vec<u8>, String> {
    YamlOperations::new()
        .dump_yaml(document)
        .map(String::into_bytes)
        .map_err(|error| error.to_string())
}

/// Serializes one value for a compact review row.
fn yaml_fragment(value: &Yaml) -> Option<String> {
    YamlOperations::new()
        .dump_yaml(value)
        .ok()
        .map(|value| value.trim().to_string())
}

/// Builds an RFC 6901-style path for known labels without escape-sensitive characters.
fn pointer(path: &[&str]) -> String {
    format!("/{}", path.join("/"))
}

/// Returns the stable relative path for a source location endpoint.
fn relative_path(location: SourceLocation) -> &'static str {
    match location {
        SourceLocation::Canonical => CANONICAL_RELATIVE_PATH,
        SourceLocation::Legacy => LEGACY_RELATIVE_PATH,
        SourceLocation::Missing => "",
    }
}
