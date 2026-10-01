//! YAML setting validators and type coercion.

mod coerce;
mod types;

pub use coerce::{coerce_setting_value, validate_setting_value};
pub use types::{CoercedValue, SettingType};
