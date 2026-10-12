//! Loader for `CLASSIC Data/databases/client-schema-ranges.yaml`.
//!
//! That file is publish metadata for the `yaml-data-v*` release channel: it
//! lists every shippable YAML file and the `[min_client_schema,
//! max_client_schema]` range the publisher advertises for it in
//! `manifest.json`. The client reads those ranges back out of the manifest
//! and parses them with [`SchemaVersion`]; this loader applies the same parse
//! to the source file, so a range that every client would refuse is caught
//! before it is published.
//!
//! The rules (all enforced, first failure wins):
//!
//! - the file holds exactly one YAML document whose root mapping has a
//!   `files` sequence;
//! - every entry is a mapping with a string `name`;
//! - `client_schemas_const`, when present, is a string;
//! - `min_client_schema` and `max_client_schema` are present, are quoted
//!   strings (an unquoted `1.0` is a YAML real and is refused), and parse as
//!   [`SchemaVersion`] (`MAJOR.MINOR`, ASCII digits, each part a `u32`);
//! - `min_client_schema <= max_client_schema` in numeric order, so
//!   `1.10 > 1.9`.
//!
//! The cache-basename and duplicate-name rules for `name` are the update
//! channel's and live in `classic-update-core`
//! (`yaml_update::validate_cache_file_name`). The repository's publish tooling
//! (`cargo xtask yaml-data`) mirrors both rule sets and an agreement test pins
//! the mirror to this loader. This is a Rust-only API; it is not on the C++
//! bridge.

use std::path::{Path, PathBuf};

use classic_shared_core::yaml::{SchemaParseError, SchemaVersion};
use yaml_rust2::{Yaml, YamlLoader};

/// One `files[]` entry of `client-schema-ranges.yaml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientSchemaRange {
    /// Shippable file name, exactly as authored (e.g. `CLASSIC Main.yaml`).
    pub name: String,
    /// Name of the `client_schemas` constant that governs this file, when the
    /// entry declares one (e.g. `MAIN_YAML`).
    pub client_schemas_const: Option<String>,
    /// Lowest client schema the published file supports.
    pub min_client_schema: SchemaVersion,
    /// Highest client schema the published file supports.
    pub max_client_schema: SchemaVersion,
}

/// Why `client-schema-ranges.yaml` was refused. Entry indexes are 0-based.
#[derive(Debug, thiserror::Error)]
pub enum ClientSchemaRangesError {
    /// The file could not be read.
    #[error("cannot read {}: {source}", path.display())]
    Io {
        /// The path that failed.
        path: PathBuf,
        /// The underlying I/O error.
        source: std::io::Error,
    },
    /// The text is not valid YAML.
    #[error("invalid YAML: {0}")]
    Parse(String),
    /// The text holds no document, or more than one.
    #[error("expected one YAML document, found {0}")]
    DocumentCount(usize),
    /// The root is not a mapping with a `files` sequence.
    #[error("missing top-level `files` list")]
    MissingFilesList,
    /// A `files[]` entry is not a mapping.
    #[error("entry {index} is not a mapping")]
    EntryNotMapping {
        /// Entry index.
        index: usize,
    },
    /// A `files[]` entry has no string `name`.
    #[error("entry {index} has no string `name`")]
    MissingName {
        /// Entry index.
        index: usize,
    },
    /// `client_schemas_const` is present but not a string.
    #[error("entry {name:?}: `client_schemas_const` must be a string")]
    ConstNotString {
        /// Entry name.
        name: String,
    },
    /// A range bound is missing.
    #[error("entry {name:?}: missing `{field}`")]
    MissingBound {
        /// Entry name.
        name: String,
        /// `min_client_schema` or `max_client_schema`.
        field: &'static str,
    },
    /// A range bound is not a quoted string.
    #[error("entry {name:?}: `{field}` must be a quoted string")]
    BoundNotString {
        /// Entry name.
        name: String,
        /// `min_client_schema` or `max_client_schema`.
        field: &'static str,
    },
    /// A range bound does not parse as [`SchemaVersion`].
    #[error("entry {name:?}: `{field}` {value:?} is malformed: {reason}")]
    MalformedBound {
        /// Entry name.
        name: String,
        /// `min_client_schema` or `max_client_schema`.
        field: &'static str,
        /// The authored string.
        value: String,
        /// The parse failure.
        reason: SchemaParseError,
    },
    /// `min_client_schema > max_client_schema`.
    #[error("entry {name:?}: min_client_schema {min} > max_client_schema {max} (empty range)")]
    EmptyRange {
        /// Entry name.
        name: String,
        /// Parsed lower bound.
        min: SchemaVersion,
        /// Parsed upper bound.
        max: SchemaVersion,
    },
}

/// Reads and parses the ranges file at `path`; see [`parse_client_schema_ranges`].
///
/// # Errors
///
/// [`ClientSchemaRangesError::Io`] when the file cannot be read as UTF-8, and
/// every error [`parse_client_schema_ranges`] returns.
pub fn load_client_schema_ranges(
    path: &Path,
) -> Result<Vec<ClientSchemaRange>, ClientSchemaRangesError> {
    let text = std::fs::read_to_string(path).map_err(|source| ClientSchemaRangesError::Io {
        path: path.to_path_buf(),
        source,
    })?;
    parse_client_schema_ranges(&text)
}

/// Parses ranges-file `text` and returns its entries in file order.
///
/// See the module documentation for the rules. Parsing stops at the first
/// violation.
///
/// # Errors
///
/// Returns the first [`ClientSchemaRangesError`] found.
pub fn parse_client_schema_ranges(
    text: &str,
) -> Result<Vec<ClientSchemaRange>, ClientSchemaRangesError> {
    let documents = YamlLoader::load_from_str(text)
        .map_err(|error| ClientSchemaRangesError::Parse(error.to_string()))?;
    let [document] = documents.as_slice() else {
        return Err(ClientSchemaRangesError::DocumentCount(documents.len()));
    };
    let entries = match document {
        Yaml::Hash(_) => document["files"]
            .as_vec()
            .ok_or(ClientSchemaRangesError::MissingFilesList)?,
        _ => return Err(ClientSchemaRangesError::MissingFilesList),
    };

    entries
        .iter()
        .enumerate()
        .map(|(index, entry)| parse_entry(index, entry))
        .collect()
}

/// Parses one `files[]` entry.
fn parse_entry(index: usize, entry: &Yaml) -> Result<ClientSchemaRange, ClientSchemaRangesError> {
    if !matches!(entry, Yaml::Hash(_)) {
        return Err(ClientSchemaRangesError::EntryNotMapping { index });
    }
    let name = entry["name"]
        .as_str()
        .ok_or(ClientSchemaRangesError::MissingName { index })?
        .to_owned();
    let client_schemas_const = match &entry["client_schemas_const"] {
        // Indexing a missing key yields `BadValue`.
        Yaml::BadValue => None,
        Yaml::String(value) => Some(value.clone()),
        _ => return Err(ClientSchemaRangesError::ConstNotString { name }),
    };
    let min_client_schema = parse_bound(&name, entry, "min_client_schema")?;
    let max_client_schema = parse_bound(&name, entry, "max_client_schema")?;
    if min_client_schema > max_client_schema {
        return Err(ClientSchemaRangesError::EmptyRange {
            name,
            min: min_client_schema,
            max: max_client_schema,
        });
    }
    Ok(ClientSchemaRange {
        name,
        client_schemas_const,
        min_client_schema,
        max_client_schema,
    })
}

/// Reads one range bound: present, a YAML string, and a valid [`SchemaVersion`].
fn parse_bound(
    name: &str,
    entry: &Yaml,
    field: &'static str,
) -> Result<SchemaVersion, ClientSchemaRangesError> {
    let value = match &entry[field] {
        Yaml::BadValue => {
            return Err(ClientSchemaRangesError::MissingBound {
                name: name.to_owned(),
                field,
            });
        }
        Yaml::String(value) => value,
        _ => {
            return Err(ClientSchemaRangesError::BoundNotString {
                name: name.to_owned(),
                field,
            });
        }
    };
    value
        .parse()
        .map_err(|reason| ClientSchemaRangesError::MalformedBound {
            name: name.to_owned(),
            field,
            value: value.clone(),
            reason,
        })
}

#[cfg(test)]
#[path = "client_schema_ranges_tests.rs"]
mod tests;
