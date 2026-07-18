//! Deterministic loading of caller-selected YAML Data files.

use crate::client_schemas;
use crate::yamldata::{YamlDataCore, parse_and_merge_yaml_content};
use classic_settings_core::{
    Compatibility, SchemaCompat, extract_schema_version, schema_compat_check,
};
use classic_shared_core::GameId;
use sha2::{Digest, Sha256};
use std::path::{Path, PathBuf};
use thiserror::Error;
use yaml_rust2::Yaml;

/// The supported game-data role selected by a typed game identity.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameDataRole {
    /// The shared Fallout 4 YAML Data role used by flat-screen and VR editions.
    Fallout4,
}

/// The role of one file in an explicit YAML Data request.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExplicitYamlDataRole {
    /// Global Main YAML Data.
    Main,
    /// Game-specific YAML Data.
    Game,
    /// User-local Ignore YAML Data.
    LocalIgnore,
}

impl std::fmt::Display for ExplicitYamlDataRole {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Main => formatter.write_str("Main"),
            Self::Game => formatter.write_str("game"),
            Self::LocalIgnore => formatter.write_str("Local Ignore"),
        }
    }
}

/// Exact caller-selected files and typed game facts for deterministic loading.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExplicitYamlDataRequest {
    /// Exact Main YAML Data file to read.
    pub main_path: PathBuf,
    /// Exact game YAML Data file to read.
    pub game_path: PathBuf,
    /// Exact Local Ignore YAML Data file to read.
    pub ignore_path: PathBuf,
    /// Typed game identity that determines the registered game-data role.
    pub game: GameId,
    /// Existing game-version mode used only for Version Registry metadata selection.
    pub selected_game_version: String,
}

/// Content identity calculated from the exact bytes retained by a snapshot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct YamlDataContentIdentity {
    sha256: [u8; 32],
    byte_len: u64,
}

impl YamlDataContentIdentity {
    pub(crate) fn from_bytes(bytes: &[u8]) -> Self {
        Self {
            sha256: Sha256::digest(bytes).into(),
            byte_len: bytes.len() as u64,
        }
    }

    /// Return the lowercase hexadecimal SHA-256 digest.
    #[must_use]
    pub fn sha256_hex(&self) -> String {
        let mut encoded = String::with_capacity(64);
        for byte in self.sha256 {
            use std::fmt::Write as _;
            write!(&mut encoded, "{byte:02x}").expect("writing to a String cannot fail");
        }
        encoded
    }

    /// Return the number of retained bytes represented by this identity.
    #[must_use]
    pub const fn byte_len(&self) -> u64 {
        self.byte_len
    }
}

#[derive(Debug)]
struct OwnedExplicitYamlFile {
    bytes: Box<[u8]>,
    identity: YamlDataContentIdentity,
}

impl OwnedExplicitYamlFile {
    fn new(bytes: Vec<u8>) -> Self {
        let identity = YamlDataContentIdentity::from_bytes(&bytes);
        Self {
            bytes: bytes.into_boxed_slice(),
            identity,
        }
    }

    fn utf8<'a>(
        &'a self,
        role: ExplicitYamlDataRole,
        path: &Path,
    ) -> Result<&'a str, ExplicitYamlDataLoadError> {
        std::str::from_utf8(&self.bytes).map_err(|source| ExplicitYamlDataLoadError::InvalidUtf8 {
            role,
            path: path.to_path_buf(),
            source,
        })
    }
}

/// Immutable parsed YAML Data plus identities backed by the exact retained file bytes.
#[derive(Debug)]
pub struct ExplicitYamlDataSnapshot {
    yaml_data: YamlDataCore,
    requested_game: GameId,
    game_data_role: GameDataRole,
    main: OwnedExplicitYamlFile,
    game_file: OwnedExplicitYamlFile,
    ignore: OwnedExplicitYamlFile,
}

impl ExplicitYamlDataSnapshot {
    /// Return the parsed YAML Data derived from the retained bytes.
    #[must_use]
    pub const fn yaml_data(&self) -> &YamlDataCore {
        &self.yaml_data
    }

    /// Return the caller's typed game identity.
    #[must_use]
    pub const fn game(&self) -> GameId {
        self.requested_game
    }

    /// Return the registered game-data role used for parsing and validation.
    #[must_use]
    pub const fn game_data_role(&self) -> GameDataRole {
        self.game_data_role
    }

    /// Return the identity of the retained Main bytes.
    #[must_use]
    pub const fn main_identity(&self) -> &YamlDataContentIdentity {
        &self.main.identity
    }

    /// Return the identity of the retained game bytes.
    #[must_use]
    pub const fn game_identity(&self) -> &YamlDataContentIdentity {
        &self.game_file.identity
    }

    /// Return the identity of the retained Local Ignore bytes.
    #[must_use]
    pub const fn ignore_identity(&self) -> &YamlDataContentIdentity {
        &self.ignore.identity
    }
}

/// Failures from deterministic explicit YAML Data loading.
#[derive(Debug, Error)]
pub enum ExplicitYamlDataLoadError {
    /// The typed game has no registered YAML Data role in this client.
    #[error("unsupported game for explicit YAML Data loading: {game}")]
    UnsupportedGame {
        /// Unsupported typed game identity.
        game: GameId,
    },
    /// One explicitly identified file could not be read.
    #[error("failed to read explicit {role} YAML Data `{}`: {source}", path.display())]
    Read {
        /// Role whose file failed.
        role: ExplicitYamlDataRole,
        /// Exact caller-selected path.
        path: PathBuf,
        /// Underlying filesystem failure.
        #[source]
        source: std::io::Error,
    },
    /// One explicitly identified file was not valid UTF-8.
    #[error("explicit {role} YAML Data `{}` is not UTF-8: {source}", path.display())]
    InvalidUtf8 {
        /// Role whose bytes failed UTF-8 decoding.
        role: ExplicitYamlDataRole,
        /// Exact caller-selected path.
        path: PathBuf,
        /// Underlying UTF-8 failure.
        #[source]
        source: std::str::Utf8Error,
    },
    /// One explicitly identified file could not be parsed as a YAML document.
    #[error("failed to parse explicit {role} YAML Data `{}`: {message}", path.display())]
    Parse {
        /// Role whose file failed parsing.
        role: ExplicitYamlDataRole,
        /// Exact caller-selected path.
        path: PathBuf,
        /// Parser failure details.
        message: String,
    },
    /// A file parsed as YAML but did not satisfy its role contract.
    #[error("explicit {role} YAML Data `{}` is invalid: {reason}", path.display())]
    InvalidRoleData {
        /// Role whose contract failed.
        role: ExplicitYamlDataRole,
        /// Exact caller-selected path.
        path: PathBuf,
        /// Stable human-readable validation reason.
        reason: String,
    },
}

/// Read, validate, identify, and retain exactly the three caller-selected YAML Data files.
///
/// This operation never resolves installation paths or cache state and never generates,
/// repairs, resets, backs up, or falls back from any selected file.
pub async fn load_explicit_yaml_data(
    request: ExplicitYamlDataRequest,
) -> Result<ExplicitYamlDataSnapshot, ExplicitYamlDataLoadError> {
    let game_data_role = game_data_role(request.game)?;

    // Each path is read exactly once; every later operation borrows these owned bytes.
    let (main_bytes, game_bytes, ignore_bytes) = tokio::join!(
        read_role_file(ExplicitYamlDataRole::Main, &request.main_path),
        read_role_file(ExplicitYamlDataRole::Game, &request.game_path),
        read_role_file(ExplicitYamlDataRole::LocalIgnore, &request.ignore_path),
    );
    let main = OwnedExplicitYamlFile::new(main_bytes?);
    let game_file = OwnedExplicitYamlFile::new(game_bytes?);
    let ignore = OwnedExplicitYamlFile::new(ignore_bytes?);

    let main_content = main.utf8(ExplicitYamlDataRole::Main, &request.main_path)?;
    let game_content = game_file.utf8(ExplicitYamlDataRole::Game, &request.game_path)?;
    let ignore_content = ignore.utf8(ExplicitYamlDataRole::LocalIgnore, &request.ignore_path)?;
    let main_yaml = parse_role_content(
        ExplicitYamlDataRole::Main,
        &request.main_path,
        "main YAML",
        "Main YAML",
        main_content,
    )?;
    let game_yaml = parse_role_content(
        ExplicitYamlDataRole::Game,
        &request.game_path,
        "game YAML",
        "Game YAML",
        game_content,
    )?;
    let ignore_yaml = parse_role_content(
        ExplicitYamlDataRole::LocalIgnore,
        &request.ignore_path,
        "ignore YAML",
        "Ignore YAML",
        ignore_content,
    )?;

    validate_shippable_role(
        &main_yaml,
        client_schemas::MAIN_YAML,
        ExplicitYamlDataRole::Main,
        &request.main_path,
    )?;
    validate_shippable_role(
        &game_yaml,
        client_schemas::GAME_FALLOUT4_YAML,
        ExplicitYamlDataRole::Game,
        &request.game_path,
    )?;
    validate_main(&main_yaml, &request.main_path)?;
    validate_game(&game_yaml, &request.game_path)?;
    validate_ignore(&ignore_yaml, game_data_role, &request.ignore_path)?;

    let yaml_data = YamlDataCore::build_from_yaml_documents(
        &main_yaml,
        &game_yaml,
        &ignore_yaml,
        game_data_key(game_data_role),
        &request.selected_game_version,
    )
    .map_err(|source| ExplicitYamlDataLoadError::InvalidRoleData {
        role: ExplicitYamlDataRole::Game,
        path: request.game_path.clone(),
        reason: source.to_string(),
    })?;

    Ok(ExplicitYamlDataSnapshot {
        yaml_data,
        requested_game: request.game,
        game_data_role,
        main,
        game_file,
        ignore,
    })
}

fn parse_role_content(
    role: ExplicitYamlDataRole,
    path: &Path,
    parse_label: &str,
    empty_label: &str,
    content: &str,
) -> Result<Yaml, ExplicitYamlDataLoadError> {
    parse_and_merge_yaml_content(parse_label, empty_label, content).map_err(|source| {
        ExplicitYamlDataLoadError::Parse {
            role,
            path: path.to_path_buf(),
            message: source.to_string(),
        }
    })
}

async fn read_role_file(
    role: ExplicitYamlDataRole,
    path: &Path,
) -> Result<Vec<u8>, ExplicitYamlDataLoadError> {
    tokio::fs::read(path)
        .await
        .map_err(|source| ExplicitYamlDataLoadError::Read {
            role,
            path: path.to_path_buf(),
            source,
        })
}

pub(crate) const fn registered_game_data_role(game: GameId) -> Option<GameDataRole> {
    match game {
        GameId::Fallout4 | GameId::Fallout4VR => Some(GameDataRole::Fallout4),
        GameId::Skyrim | GameId::Starfield => None,
    }
}

fn game_data_role(game: GameId) -> Result<GameDataRole, ExplicitYamlDataLoadError> {
    registered_game_data_role(game).ok_or(ExplicitYamlDataLoadError::UnsupportedGame { game })
}

const fn game_data_key(role: GameDataRole) -> &'static str {
    match role {
        GameDataRole::Fallout4 => "Fallout4",
    }
}

fn validate_shippable_role(
    yaml: &Yaml,
    accepted: SchemaCompat,
    role: ExplicitYamlDataRole,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let version = extract_schema_version(yaml).map_err(|source| {
        ExplicitYamlDataLoadError::InvalidRoleData {
            role,
            path: path.to_path_buf(),
            reason: source.to_string(),
        }
    })?;
    match schema_compat_check(&version, &accepted) {
        Compatibility::Compatible => Ok(()),
        incompatible => Err(ExplicitYamlDataLoadError::InvalidRoleData {
            role,
            path: path.to_path_buf(),
            reason: format!("incompatible schema version {version}: {incompatible:?}"),
        }),
    }
}

fn mapping_value<'a>(yaml: &'a Yaml, key: &str) -> Option<&'a Yaml> {
    yaml.as_hash()?
        .iter()
        .find_map(|(candidate, value)| (candidate.as_str() == Some(key)).then_some(value))
}

fn required_mapping<'a>(
    yaml: &'a Yaml,
    key: &str,
    role: ExplicitYamlDataRole,
    path: &Path,
) -> Result<&'a yaml_rust2::yaml::Hash, ExplicitYamlDataLoadError> {
    mapping_value(yaml, key)
        .and_then(Yaml::as_hash)
        .ok_or_else(|| ExplicitYamlDataLoadError::InvalidRoleData {
            role,
            path: path.to_path_buf(),
            reason: format!("required `{key}` mapping is missing or malformed"),
        })
}

fn required_non_empty_string(
    mapping: &yaml_rust2::yaml::Hash,
    key: &str,
    context: &str,
    role: ExplicitYamlDataRole,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let valid = mapping.iter().any(|(candidate, value)| {
        candidate.as_str() == Some(key)
            && value.as_str().is_some_and(|value| !value.trim().is_empty())
    });
    if valid {
        Ok(())
    } else {
        Err(ExplicitYamlDataLoadError::InvalidRoleData {
            role,
            path: path.to_path_buf(),
            reason: format!("required `{context}.{key}` string is missing or empty"),
        })
    }
}

pub(crate) fn validate_main(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let info = required_mapping(yaml, "CLASSIC_Info", ExplicitYamlDataRole::Main, path)?;
    required_non_empty_string(
        info,
        "version",
        "CLASSIC_Info",
        ExplicitYamlDataRole::Main,
        path,
    )?;
    let version = info
        .iter()
        .find_map(|(candidate, value)| {
            (candidate.as_str() == Some("version"))
                .then(|| value.as_str())
                .flatten()
        })
        .expect("the required non-empty string was validated above")
        .trim();
    crate::shippable::validate_release_semver_shape(version).map_err(|reason| {
        ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::Main,
            path: path.to_path_buf(),
            reason: format!("`CLASSIC_Info.version` is not a valid release SemVer: {reason}"),
        }
    })?;

    validate_optional_main_string(info, "version_date", "CLASSIC_Info", path)?;
    if let Some(interface) = mapping_value(yaml, "CLASSIC_Interface") {
        let interface = interface
            .as_hash()
            .ok_or_else(|| main_validation_error(path, "`CLASSIC_Interface` must be a mapping"))?;
        validate_optional_main_string(
            interface,
            "autoscan_text_Fallout4",
            "CLASSIC_Interface",
            path,
        )?;
    }
    if let Some(records) = mapping_value(yaml, "catch_log_records") {
        let entries = records.as_vec().ok_or_else(|| {
            main_validation_error(path, "`catch_log_records` must be a sequence of strings")
        })?;
        if !entries.iter().all(|entry| entry.as_str().is_some()) {
            return Err(main_validation_error(
                path,
                "`catch_log_records` must contain only strings",
            ));
        }
    }
    Ok(())
}

pub(crate) fn validate_game(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let info = required_mapping(yaml, "Game_Info", ExplicitYamlDataRole::Game, path)?;
    required_non_empty_string(
        info,
        "Main_Root_Name",
        "Game_Info",
        ExplicitYamlDataRole::Game,
        path,
    )?;
    let root_name = info
        .iter()
        .find_map(|(candidate, value)| {
            (candidate.as_str() == Some("Main_Root_Name"))
                .then(|| value.as_str())
                .flatten()
        })
        .expect("the required non-empty string was validated above");
    // Checked-in and legacy fixtures use both `Fallout 4` and `Fallout4`.
    let normalized: String = root_name
        .chars()
        .filter(|character| character.is_ascii_alphanumeric())
        .map(|character| character.to_ascii_lowercase())
        .collect();
    if normalized != "fallout4" {
        return Err(ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::Game,
            path: path.to_path_buf(),
            reason: format!(
                "`Game_Info.Main_Root_Name` identifies `{root_name}`, expected the Fallout 4 data role"
            ),
        });
    }

    for key in [
        "CRASHGEN_LogName",
        "CRASHGEN_LatestVer",
        "XSE_Acronym",
        "GameVersion",
    ] {
        validate_optional_entry_string(info, key, "Game_Info", path)?;
    }
    validate_optional_string_sequence_in_mapping(info, "CRASHGEN_Ignore", "Game_Info", path)?;
    if let Some(warnings) = mapping_value(yaml, "Warnings_CRASHGEN") {
        let warnings = warnings
            .as_hash()
            .ok_or_else(|| game_validation_error(path, "`Warnings_CRASHGEN` must be a mapping"))?;
        validate_optional_entry_string(warnings, "Warn_NOPlugins", "Warnings_CRASHGEN", path)?;
        validate_optional_entry_string(warnings, "Warn_Outdated", "Warnings_CRASHGEN", path)?;
    }
    for section in [
        "Game_Hints",
        "Crashlog_Plugins_Exclude",
        "Crashlog_Records_Exclude",
    ] {
        validate_optional_string_sequence(yaml, section, path)?;
    }
    validate_mod_conf(yaml, path)?;
    validate_mods_core(yaml, path)?;
    validate_mod_solution_section(yaml, "Mods_FREQ", path)?;
    validate_mod_solution_section(yaml, "Mods_SOLU", path)?;
    validate_suspect_error_rules(yaml, path)?;
    validate_suspect_stack_rules(yaml, path)?;
    crate::crashgen_registry_yaml::validate_crashgen_registry(yaml)
        .map_err(|reason| game_validation_error(path, reason))
}

/// Build a Main-role validation error tied to the exact requested path.
fn main_validation_error(path: &Path, reason: impl Into<String>) -> ExplicitYamlDataLoadError {
    ExplicitYamlDataLoadError::InvalidRoleData {
        role: ExplicitYamlDataRole::Main,
        path: path.to_path_buf(),
        reason: reason.into(),
    }
}

/// Validate an optional consumed Main string field when present.
fn validate_optional_main_string(
    mapping: &yaml_rust2::yaml::Hash,
    key: &str,
    context: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    match hash_value(mapping, key) {
        None => Ok(()),
        Some(value) if value.as_str().is_some() => Ok(()),
        Some(_) => Err(main_validation_error(
            path,
            format!("`{context}.{key}` must be a string when present"),
        )),
    }
}

/// Build a game-role validation error tied to the exact requested path.
fn game_validation_error(path: &Path, reason: impl Into<String>) -> ExplicitYamlDataLoadError {
    ExplicitYamlDataLoadError::InvalidRoleData {
        role: ExplicitYamlDataRole::Game,
        path: path.to_path_buf(),
        reason: reason.into(),
    }
}

/// Look up a string-keyed value in a parsed YAML mapping.
fn hash_value<'a>(mapping: &'a yaml_rust2::yaml::Hash, key: &str) -> Option<&'a Yaml> {
    mapping
        .iter()
        .find_map(|(candidate, value)| (candidate.as_str() == Some(key)).then_some(value))
}

/// Require one consumed YAML value to be a sequence of non-empty strings.
fn validate_string_sequence_value(
    value: &Yaml,
    context: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let entries = value.as_vec().ok_or_else(|| {
        game_validation_error(
            path,
            format!("`{context}` must be a YAML sequence of strings"),
        )
    })?;
    if entries
        .iter()
        .all(|entry| entry.as_str().is_some_and(|entry| !entry.trim().is_empty()))
    {
        Ok(())
    } else {
        Err(game_validation_error(
            path,
            format!("`{context}` must contain only non-empty strings"),
        ))
    }
}

/// Validate an optional top-level string-sequence field without making it required.
fn validate_optional_string_sequence(
    yaml: &Yaml,
    key: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    mapping_value(yaml, key).map_or(Ok(()), |value| {
        validate_string_sequence_value(value, key, path)
    })
}

/// Validate an optional string-sequence field nested in a known mapping.
fn validate_optional_string_sequence_in_mapping(
    mapping: &yaml_rust2::yaml::Hash,
    key: &str,
    parent: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    hash_value(mapping, key).map_or(Ok(()), |value| {
        validate_string_sequence_value(value, &format!("{parent}.{key}"), path)
    })
}

/// Return an optional structured section after enforcing its sequence shape.
fn optional_mapping_sequence<'a>(
    yaml: &'a Yaml,
    section: &str,
    path: &Path,
) -> Result<Option<&'a Vec<Yaml>>, ExplicitYamlDataLoadError> {
    let Some(value) = mapping_value(yaml, section) else {
        return Ok(None);
    };
    let entries = value.as_vec().ok_or_else(|| {
        game_validation_error(
            path,
            format!("`{section}` must be a YAML sequence of mappings"),
        )
    })?;
    Ok(Some(entries))
}

/// Require one indexed structured-section entry to be a mapping.
fn require_entry_mapping<'a>(
    entry: &'a Yaml,
    section: &str,
    index: usize,
    path: &Path,
) -> Result<&'a yaml_rust2::yaml::Hash, ExplicitYamlDataLoadError> {
    entry.as_hash().ok_or_else(|| {
        game_validation_error(path, format!("`{section}[{index}]` must be a mapping"))
    })
}

/// Require one entry field to be a non-empty string.
fn require_entry_string(
    mapping: &yaml_rust2::yaml::Hash,
    key: &str,
    context: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    if hash_value(mapping, key)
        .and_then(Yaml::as_str)
        .is_some_and(|value| !value.trim().is_empty())
    {
        Ok(())
    } else {
        Err(game_validation_error(
            path,
            format!("`{context}.{key}` must be a non-empty string"),
        ))
    }
}

/// Validate an optional entry string when the field is present.
fn validate_optional_entry_string(
    mapping: &yaml_rust2::yaml::Hash,
    key: &str,
    context: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    match hash_value(mapping, key) {
        None => Ok(()),
        Some(value) if value.as_str().is_some_and(|value| !value.trim().is_empty()) => Ok(()),
        Some(_) => Err(game_validation_error(
            path,
            format!("`{context}.{key}` must be a non-empty string when present"),
        )),
    }
}

/// Strictly validate every `Mods_CONF` entry consumed by the combined model.
fn validate_mod_conf(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let Some(entries) = optional_mapping_sequence(yaml, "Mods_CONF", path)? else {
        return Ok(());
    };
    for (index, entry) in entries.iter().enumerate() {
        let context = format!("Mods_CONF[{index}]");
        let mapping = require_entry_mapping(entry, "Mods_CONF", index, path)?;
        for key in ["mod_a", "mod_b", "name_a", "name_b", "description", "fix"] {
            require_entry_string(mapping, key, &context, path)?;
        }
        validate_optional_entry_string(mapping, "link", &context, path)?;
    }
    Ok(())
}

/// Strictly validate every `Mods_CORE` entry and its optional exclusion rule.
fn validate_mods_core(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let Some(entries) = optional_mapping_sequence(yaml, "Mods_CORE", path)? else {
        return Ok(());
    };
    for (index, entry) in entries.iter().enumerate() {
        let context = format!("Mods_CORE[{index}]");
        let mapping = require_entry_mapping(entry, "Mods_CORE", index, path)?;
        for key in ["detect", "name", "description"] {
            require_entry_string(mapping, key, &context, path)?;
        }
        validate_optional_entry_string(mapping, "gpu", &context, path)?;
        validate_optional_entry_string(mapping, "gpu_mismatch_warning", &context, path)?;
        if let Some(exclude_when) = hash_value(mapping, "exclude_when") {
            let exclude_mapping = exclude_when.as_hash().ok_or_else(|| {
                game_validation_error(path, format!("`{context}.exclude_when` must be a mapping"))
            })?;
            validate_optional_string_sequence_in_mapping(
                exclude_mapping,
                "plugin_any",
                &format!("{context}.exclude_when"),
                path,
            )?;
        }
    }
    Ok(())
}

/// Strictly validate one structured mod-solution section.
fn validate_mod_solution_section(
    yaml: &Yaml,
    section: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let Some(entries) = optional_mapping_sequence(yaml, section, path)? else {
        return Ok(());
    };
    for (index, entry) in entries.iter().enumerate() {
        let context = format!("{section}[{index}]");
        let mapping = require_entry_mapping(entry, section, index, path)?;
        for key in ["id", "name", "description"] {
            require_entry_string(mapping, key, &context, path)?;
        }
        let criteria = hash_value(mapping, "criteria")
            .and_then(Yaml::as_hash)
            .ok_or_else(|| {
                game_validation_error(path, format!("`{context}.criteria` must be a mapping"))
            })?;
        let any = hash_value(criteria, "any");
        let all = hash_value(criteria, "all");
        match (any, all) {
            (Some(value), None) => {
                validate_string_sequence_value(value, &format!("{context}.criteria.any"), path)?
            }
            (None, Some(value)) => {
                validate_string_sequence_value(value, &format!("{context}.criteria.all"), path)?
            }
            _ => {
                return Err(game_validation_error(
                    path,
                    format!("`{context}.criteria` must define exactly one of `any` or `all`"),
                ));
            }
        }
        if let Some(exceptions) = hash_value(mapping, "exceptions") {
            validate_string_sequence_value(exceptions, &format!("{context}.exceptions"), path)?;
        }
    }
    Ok(())
}

/// Require the rule severity field to fit the model's signed 32-bit contract.
fn validate_severity(
    mapping: &yaml_rust2::yaml::Hash,
    context: &str,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let valid = match hash_value(mapping, "severity") {
        Some(Yaml::Integer(value)) => i32::try_from(*value).is_ok(),
        Some(Yaml::String(value)) => value.trim().parse::<i32>().is_ok(),
        _ => false,
    };
    if valid {
        Ok(())
    } else {
        Err(game_validation_error(
            path,
            format!("`{context}.severity` must be a 32-bit integer"),
        ))
    }
}

/// Strictly validate every structured crash-log error rule.
fn validate_suspect_error_rules(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let Some(entries) = optional_mapping_sequence(yaml, "Crashlog_Error_Check", path)? else {
        return Ok(());
    };
    for (index, entry) in entries.iter().enumerate() {
        let context = format!("Crashlog_Error_Check[{index}]");
        let mapping = require_entry_mapping(entry, "Crashlog_Error_Check", index, path)?;
        require_entry_string(mapping, "id", &context, path)?;
        require_entry_string(mapping, "name", &context, path)?;
        validate_severity(mapping, &context, path)?;
        let values = hash_value(mapping, "main_error_contains_any").ok_or_else(|| {
            game_validation_error(
                path,
                format!("`{context}.main_error_contains_any` is required"),
            )
        })?;
        validate_string_sequence_value(
            values,
            &format!("{context}.main_error_contains_any"),
            path,
        )?;
    }
    Ok(())
}

/// Strictly validate every structured crash-log stack rule.
fn validate_suspect_stack_rules(yaml: &Yaml, path: &Path) -> Result<(), ExplicitYamlDataLoadError> {
    let Some(entries) = optional_mapping_sequence(yaml, "Crashlog_Stack_Check", path)? else {
        return Ok(());
    };
    for (index, entry) in entries.iter().enumerate() {
        let context = format!("Crashlog_Stack_Check[{index}]");
        let mapping = require_entry_mapping(entry, "Crashlog_Stack_Check", index, path)?;
        require_entry_string(mapping, "id", &context, path)?;
        require_entry_string(mapping, "name", &context, path)?;
        validate_severity(mapping, &context, path)?;
        for key in [
            "main_error_required_any",
            "main_error_optional_any",
            "stack_contains_any",
            "exclude_if_stack_contains_any",
        ] {
            if let Some(values) = hash_value(mapping, key) {
                validate_string_sequence_value(values, &format!("{context}.{key}"), path)?;
            }
        }
        if let Some(count_rules) = hash_value(mapping, "stack_contains_at_least") {
            let rules = count_rules.as_vec().ok_or_else(|| {
                game_validation_error(
                    path,
                    format!("`{context}.stack_contains_at_least` must be a sequence"),
                )
            })?;
            for (rule_index, rule) in rules.iter().enumerate() {
                let rule_context = format!("{context}.stack_contains_at_least[{rule_index}]");
                let rule_mapping = require_entry_mapping(
                    rule,
                    &format!("{context}.stack_contains_at_least"),
                    rule_index,
                    path,
                )?;
                require_entry_string(rule_mapping, "substring", &rule_context, path)?;
                let valid_count = match hash_value(rule_mapping, "count") {
                    Some(Yaml::Integer(value)) => *value > 0 && usize::try_from(*value).is_ok(),
                    Some(Yaml::String(value)) => {
                        value.trim().parse::<usize>().is_ok_and(|value| value > 0)
                    }
                    _ => false,
                };
                if !valid_count {
                    return Err(game_validation_error(
                        path,
                        format!("`{rule_context}.count` must be a positive integer"),
                    ));
                }
            }
        }
    }
    Ok(())
}

fn validate_ignore(
    yaml: &Yaml,
    role: GameDataRole,
    path: &Path,
) -> Result<(), ExplicitYamlDataLoadError> {
    let key = format!("CLASSIC_Ignore_{}", game_data_key(role));
    let Some(entries) = mapping_value(yaml, &key).and_then(Yaml::as_vec) else {
        return Err(ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::LocalIgnore,
            path: path.to_path_buf(),
            reason: format!("required `{key}` sequence is missing or malformed"),
        });
    };
    if entries.iter().all(|entry| entry.as_str().is_some()) {
        Ok(())
    } else {
        Err(ExplicitYamlDataLoadError::InvalidRoleData {
            role: ExplicitYamlDataRole::LocalIgnore,
            path: path.to_path_buf(),
            reason: format!("`{key}` must contain only strings"),
        })
    }
}

#[cfg(test)]
#[path = "explicit_yaml_data_tests.rs"]
mod tests;
