//! YAML setting validators and type coercion.

mod coerce;
mod structure;
mod types;

pub use coerce::{coerce_setting_value, validate_setting_value};
pub use structure::{IssueSeverity, ValidationIssue, validate_settings_structure};
pub use types::{CoercedValue, SettingType};
