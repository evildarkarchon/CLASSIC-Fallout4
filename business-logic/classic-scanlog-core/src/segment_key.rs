//! Segment key constants for named segment map access.
//!
//! These constants prevent bare string literals at call sites and provide
//! compile-time verification of key names across the orchestrator, settings
//! validator, and PyO3 bindings.

/// Key for the crashgen settings section.
///
/// Contains all lines from the start of the log until `SYSTEM SPECS:` (exclusive).
pub const SETTINGS: &str = "settings";

/// Key for the system specifications section.
///
/// Contains lines between `SYSTEM SPECS:` and `PROBABLE CALL STACK:` (exclusive).
pub const SYSTEM: &str = "system";

/// Key for the probable call stack section.
///
/// Contains lines between `PROBABLE CALL STACK:` and `MODULES:` (exclusive).
pub const CALLSTACK: &str = "callstack";

/// Key for the loaded DLL modules section.
///
/// Contains lines within the `MODULES:` section before the XSE plugin sub-header.
pub const MODULES: &str = "modules";

/// Key for the XSE (Script Extender) plugin modules section.
///
/// Contains lines after the crashgen-owned sub-header within the `MODULES:` section.
/// If no sub-header is found, this key maps to an empty list.
pub const XSE_MODULES: &str = "xse_modules";

/// Key for the game plugins section.
///
/// Contains lines between `PLUGINS:` and `REGISTERS:` (exclusive).
pub const PLUGINS: &str = "plugins";

/// Key for the CPU registers section.
///
/// Contains lines between `REGISTERS:` and `STACK:` (exclusive).
pub const REGISTERS: &str = "registers";

/// Key for the stack dump section.
///
/// Contains lines from `STACK:` to the end of the log.
pub const STACK_DUMP: &str = "stack_dump";

/// All 8 named segment keys, in log order.
///
/// Guaranteed to always be present in the output of `parse_all_sections_arc`.
pub const ALL_KEYS: &[&str] = &[
    SETTINGS,
    SYSTEM,
    CALLSTACK,
    MODULES,
    XSE_MODULES,
    PLUGINS,
    REGISTERS,
    STACK_DUMP,
];
