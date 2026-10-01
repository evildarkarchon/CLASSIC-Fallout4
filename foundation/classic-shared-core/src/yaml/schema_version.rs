//! YAML schema versioning for shippable CLASSIC data files.

mod compat;
mod extract;
mod version;

pub use compat::{Compatibility, SchemaCompat, schema_compat_check};
pub use extract::{SCHEMA_VERSION_KEY, YamlSchemaError, extract_schema_version};
pub use version::{SchemaParseError, SchemaVersion};
