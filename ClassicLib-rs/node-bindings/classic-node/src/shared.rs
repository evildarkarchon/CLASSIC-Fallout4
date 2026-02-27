//! Shared utilities bindings (classic-shared-core + classic-perf-core + classic-registry-core)
//!
//! Provides path utilities, string interning, performance metrics, registry access,
//! and runtime diagnostics to JavaScript/TypeScript.

use crate::logging_contract;
use classic_perf_core::{clear_metrics, get_summary, record_timing};
use classic_registry_core::{clear_all, register, unregister};
use classic_shared_core::path_core::PathHandler;
use classic_shared_core::strings_core::StringProcessor;
use napi::bindgen_prelude::*;
use std::collections::HashMap;
use std::sync::LazyLock;

/// Convert any Display error to a napi::Error
fn to_napi_err(err: impl std::fmt::Display) -> napi::Error {
    napi::Error::from_reason(format!("{err}"))
}

/// Module-level PathHandler with default cache settings (5-minute TTL).
static PATH_HANDLER: LazyLock<PathHandler> = LazyLock::new(PathHandler::default);

/// Module-level StringProcessor for string interning.
static STRING_PROCESSOR: LazyLock<StringProcessor> = LazyLock::new(StringProcessor::default);

// ============================================================================
// 1. Path Utilities (from classic-shared-core::path_core)
// ============================================================================

/// Normalize a file path, resolving symlinks and cleaning redundant components.
///
/// Uses a cached PathHandler for efficient repeated lookups.
#[napi]
pub fn normalize_path(path: String) -> Result<String> {
    PATH_HANDLER.normalize_path(&path).map_err(to_napi_err)
}

/// Safely join path parts together.
///
/// The first element is used as the base path, and subsequent elements are
/// appended as path components. Returns the joined path string.
#[napi]
pub fn join_paths(parts: Vec<String>) -> Result<String> {
    if parts.is_empty() {
        return Err(napi::Error::from_reason(
            "join_paths requires at least one path part",
        ));
    }
    let base = &parts[0];
    let components: Vec<String> = parts[1..].to_vec();
    Ok(PATH_HANDLER.join_paths(base, &components))
}

/// Validate multiple paths for existence in batch.
///
/// Returns an object mapping each path to a boolean indicating whether it exists.
#[napi]
pub fn validate_paths_batch(paths: Vec<String>) -> HashMap<String, bool> {
    let results = PATH_HANDLER.validate_paths_batch(&paths);
    results
        .into_iter()
        .map(|(path, is_valid, _msg)| (path, is_valid))
        .collect()
}

// ============================================================================
// 2. String Utilities (from classic-shared-core::strings_core)
// ============================================================================

/// Intern a string for memory-efficient deduplication.
///
/// Returns the interned string (content-identical, but stored in a shared pool).
#[napi]
pub fn intern_string(value: String) -> String {
    STRING_PROCESSOR.intern(&value)
}

/// Process a batch of strings with normalization (trim, lowercase, collapse whitespace).
#[napi]
pub fn process_string_batch(values: Vec<String>) -> Vec<String> {
    let refs: Vec<&str> = values.iter().map(|s| s.as_str()).collect();
    STRING_PROCESSOR.process_batch(
        &refs,
        classic_shared_core::strings_core::StringOperation::Normalize,
    )
}

/// Normalize a single string (trim, lowercase, collapse extra whitespace).
#[napi]
pub fn normalize_string(value: String) -> String {
    STRING_PROCESSOR.normalize_string(&value)
}

// ============================================================================
// 3. Performance Metrics (from classic-perf-core)
// ============================================================================

/// Timing statistics for a single operation.
#[napi(object)]
pub struct TimingStats {
    /// Number of timing samples recorded
    pub count: u32,
    /// Total time across all samples (milliseconds)
    pub total_ms: f64,
    /// Average time per sample (milliseconds)
    pub avg_ms: f64,
    /// Minimum sample time (milliseconds)
    pub min_ms: f64,
    /// Maximum sample time (milliseconds)
    pub max_ms: f64,
}

/// Aggregate metrics summary containing timings for all recorded operations.
#[napi(object)]
pub struct MetricsSummaryResult {
    /// Map of operation name to timing statistics
    pub timings: HashMap<String, TimingStats>,
}

/// Record a timing measurement for an operation.
///
/// The duration should be provided in milliseconds. It is stored internally
/// in seconds and converted back to milliseconds when retrieved via getMetricsSummary.
#[napi]
pub fn record_timing_metric(label: String, duration_ms: f64) {
    // Core crate stores in seconds
    record_timing(&label, duration_ms / 1000.0);
}

/// Get aggregate statistics for all recorded performance metrics.
///
/// Returns an object with a `timings` field mapping operation names to their
/// count, totalMs, avgMs, minMs, and maxMs.
#[napi]
pub fn get_metrics_summary() -> MetricsSummaryResult {
    let summary = get_summary();
    let timings = summary
        .into_iter()
        .map(|(name, stats)| {
            (
                name,
                TimingStats {
                    count: stats.count as u32,
                    total_ms: stats.total * 1000.0,
                    avg_ms: stats.average * 1000.0,
                    min_ms: stats.min * 1000.0,
                    max_ms: stats.max * 1000.0,
                },
            )
        })
        .collect();
    MetricsSummaryResult { timings }
}

/// Clear all recorded performance metrics.
#[napi]
pub fn clear_all_metrics() {
    clear_metrics();
}

// ============================================================================
// 4. Registry (from classic-registry-core)
// ============================================================================

/// Get a value from the global registry by key.
///
/// Values are stored as JSON-compatible values. Returns null if the key
/// does not exist or was stored with a non-JSON type.
#[napi]
pub fn registry_get(key: String) -> serde_json::Value {
    // Try to retrieve as serde_json::Value (what registrySet stores)
    let value: Option<serde_json::Value> = classic_registry_core::get(&key);
    if let Some(v) = value {
        return v;
    }

    // Fall back to common Rust types that may have been registered by other crates
    if let Some(s) = classic_registry_core::get::<_, String>(&key) {
        return serde_json::Value::String(s);
    }
    if let Some(b) = classic_registry_core::get::<_, bool>(&key) {
        return serde_json::Value::Bool(b);
    }
    if let Some(i) = classic_registry_core::get::<_, i64>(&key) {
        return serde_json::json!(i);
    }
    if let Some(i) = classic_registry_core::get::<_, i32>(&key) {
        return serde_json::json!(i);
    }
    if let Some(f) = classic_registry_core::get::<_, f64>(&key) {
        return serde_json::json!(f);
    }

    serde_json::Value::Null
}

/// Set a value in the global registry.
///
/// The value is stored as a JSON-compatible value and can be retrieved
/// with registryGet.
#[napi]
pub fn registry_set(key: String, value: serde_json::Value) {
    register(key, value);
}

/// Remove a key from the global registry.
///
/// Returns true if the key was found and removed, false otherwise.
#[napi]
pub fn registry_remove(key: String) -> bool {
    unregister(&key)
}

/// Clear all entries from the global registry.
#[napi]
pub fn registry_clear() {
    clear_all();
}

// ============================================================================
// 5. Diagnostics
// ============================================================================

/// Runtime diagnostic information.
#[napi(object)]
pub struct RuntimeInfo {
    /// Whether the Tokio runtime is available
    pub available: bool,
    /// Number of worker threads (0 if runtime is unavailable)
    pub thread_count: u32,
}

/// Check if the shared Tokio runtime is available.
///
/// This verifies that the ONE RUNTIME can be accessed without error.
#[napi]
pub fn is_runtime_available() -> bool {
    // Accessing the runtime through get_runtime() will lazily initialize it.
    // If it panics (which it shouldn't), this would fail - but LazyLock
    // makes it safe. We simply verify we can access it.
    let available = std::panic::catch_unwind(|| {
        let _ = classic_shared_core::get_runtime();
    })
    .is_ok();

    let thread_count = if available {
        std::thread::available_parallelism()
            .map(|n| n.get() as u32)
            .unwrap_or(4)
    } else {
        0
    };

    logging_contract::emit_node_runtime_startup_diagnostics(available, thread_count, None);
    available
}

/// Get runtime diagnostic information.
///
/// Returns an object with `available` (boolean) and `threadCount` (number).
#[napi]
pub fn get_runtime_info() -> RuntimeInfo {
    let available = std::panic::catch_unwind(|| {
        let _ = classic_shared_core::get_runtime();
    })
    .is_ok();

    let thread_count = if available {
        std::thread::available_parallelism()
            .map(|n| n.get() as u32)
            .unwrap_or(4)
    } else {
        0
    };

    logging_contract::emit_node_runtime_startup_diagnostics(available, thread_count, None);

    RuntimeInfo {
        available,
        thread_count,
    }
}

// ============================================================================
// 6. Registry Convenience Functions (well-known keys)
// ============================================================================

/// Set the current game name in the global registry.
///
/// Uses the well-known registry key "gamevars_game".
///
/// @param game - Game name (e.g., "Fallout4", "Skyrim").
#[napi]
pub fn registry_set_game(game: String) -> Result<()> {
    register(
        classic_registry_core::Keys::GAME.to_string(),
        serde_json::Value::String(game),
    );
    Ok(())
}

/// Get the current game name from the global registry.
///
/// Uses the well-known registry key "gamevars_game".
/// Returns `undefined` if no game has been set.
#[napi]
pub fn registry_get_game() -> Option<String> {
    let value: Option<serde_json::Value> =
        classic_registry_core::get(classic_registry_core::Keys::GAME);
    match value {
        Some(serde_json::Value::String(s)) => Some(s),
        _ => {
            // Fall back to raw String type (in case set by Rust code directly)
            classic_registry_core::get::<_, String>(classic_registry_core::Keys::GAME)
        }
    }
}

/// Get the current game version string from the global registry.
///
/// Uses the well-known registry key "gamevars_version".
/// Returns the version as a string (e.g., "Original", "NextGen", "Vr"),
/// or `undefined` if no version has been set.
#[napi]
pub fn registry_get_game_version() -> Option<String> {
    let value: Option<serde_json::Value> =
        classic_registry_core::get(classic_registry_core::Keys::GAME_VERSION);
    match value {
        Some(serde_json::Value::String(s)) => Some(s),
        _ => {
            // Try raw String type
            classic_registry_core::get::<_, String>(classic_registry_core::Keys::GAME_VERSION)
        }
    }
}

/// Check if the current game version is a VR version.
///
/// Reads the game version from the registry and checks if it represents
/// a VR variant. Returns `false` if no version is set.
#[napi]
pub fn registry_is_vr_version() -> bool {
    let value: Option<serde_json::Value> =
        classic_registry_core::get(classic_registry_core::Keys::GAME_VERSION);
    match value {
        Some(serde_json::Value::String(ref s)) => {
            let lower = s.to_lowercase();
            lower == "vr" || lower.contains("vr")
        }
        _ => {
            // Try raw String type
            if let Some(s) =
                classic_registry_core::get::<_, String>(classic_registry_core::Keys::GAME_VERSION)
            {
                let lower = s.to_lowercase();
                lower == "vr" || lower.contains("vr")
            } else {
                false
            }
        }
    }
}
