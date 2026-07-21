//! FormID database bridge for CXX FFI.
//!
//! Bridges the legacy cached `classic_database_core::DatabasePool` plus the
//! strict owned `FormIdValueLookup` adapters and typed outcome/error envelopes.
//! Async operations are wrapped through shared-runtime helpers.

use crate::runtime_support::{block_on, block_on_result};
use classic_database_core::{
    DatabasePool, FormIdValueLookup as CoreFormIdValueLookup,
    FormIdValueLookupEntry as CoreFormIdValueLookupEntry,
    FormIdValueLookupError as CoreFormIdValueLookupError,
    FormIdValueLookupInMemoryReply as CoreFormIdValueLookupInMemoryReply,
    FormIdValueLookupOutcome as CoreFormIdValueLookupOutcome,
};
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

/// Opaque wrapper around `DatabasePool` for CXX FFI.
pub struct DbPool {
    inner: Arc<DatabasePool>,
}

/// Opaque owned FormID Value Lookup handle for CXX FFI.
///
/// SQLite construction failures remain attached to the handle so callers can
/// inspect a typed `OperationalFailure` instead of parsing a CXX exception.
/// Successful handles contain only immutable core state and may be reused.
pub struct FormIdValueLookup {
    inner: Result<CoreFormIdValueLookup, CoreFormIdValueLookupError>,
}

fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool> {
    let max_conn = if max_connections > 0 {
        Some(max_connections as usize)
    } else {
        None
    };
    Box::new(DbPool {
        inner: Arc::new(DatabasePool::new(
            max_conn,
            Duration::from_secs(cache_ttl_secs),
            game_table.to_string(),
        )),
    })
}

fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<(), String> {
    let paths: Vec<PathBuf> = db_paths.iter().map(PathBuf::from).collect();
    block_on_result(pool.inner.initialize(paths))
}

fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String {
    match block_on(pool.inner.get_entry(formid, plugin, None)) {
        Ok(Some(entry)) => entry,
        Ok(None) => String::new(),
        Err(_) => String::new(),
    }
}

fn db_pool_get_entries_batch(pool: &DbPool, formids: &[String], plugins: &[String]) -> Vec<String> {
    let pairs: Vec<(String, String)> = formids
        .iter()
        .zip(plugins.iter())
        .map(|(f, p)| (f.clone(), p.clone()))
        .collect();
    let result = block_on(pool.inner.get_entries_batch(pairs, None, 50));
    match result {
        Ok(map) => {
            // Return as "formid\tvalue" pairs for C++ to parse
            map.into_iter().map(|(k, v)| format!("{k}\t{v}")).collect()
        }
        Err(_) => Vec::new(),
    }
}

fn db_pool_is_available(pool: &DbPool) -> bool {
    pool.inner.is_available()
}

fn db_pool_cache_size(pool: &DbPool) -> usize {
    pool.inner.cache_size()
}

fn db_pool_clear_cache(pool: &DbPool, expired_only: bool) -> usize {
    pool.inner.clear_cache(expired_only)
}

fn db_pool_close(pool: &DbPool) -> Result<(), String> {
    block_on_result(pool.inner.close())
}

fn db_pool_game_table(pool: &DbPool) -> String {
    pool.inner.get_game_table()
}

// ── Strict FormID Value Lookup facade ────────────────────────────────

/// Creates an explicitly disabled owned lookup handle.
fn formid_value_lookup_disabled_new() -> Box<FormIdValueLookup> {
    Box::new(FormIdValueLookup {
        inner: Ok(CoreFormIdValueLookup::disabled()),
    })
}

/// Creates an owned deterministic lookup from CXX-scripted replies.
///
/// The adapter copies every key and reply into Rust-owned storage. A `Found`
/// reply with blank content is intentionally preserved so lookup can report the
/// core `MalformedResult` error; no foreign callback crosses this boundary.
fn formid_value_lookup_in_memory_new(
    configuration: ffi::FormIdValueLookupInMemoryConfigurationDto,
) -> Box<FormIdValueLookup> {
    let entries = configuration
        .entries
        .into_iter()
        .map(|entry| {
            let reply = match entry.reply_kind {
                ffi::FormIdValueLookupReplyKind::Missing => {
                    CoreFormIdValueLookupInMemoryReply::Value(None)
                }
                ffi::FormIdValueLookupReplyKind::Found => {
                    CoreFormIdValueLookupInMemoryReply::Value(Some(entry.value))
                }
                ffi::FormIdValueLookupReplyKind::OperationalFailure => {
                    CoreFormIdValueLookupInMemoryReply::OperationalFailure(entry.error_message)
                }
                _ => CoreFormIdValueLookupInMemoryReply::OperationalFailure(
                    "unsupported CXX in-memory reply kind".to_string(),
                ),
            };
            CoreFormIdValueLookupEntry::new(entry.formid, entry.plugin, reply)
        })
        .collect();

    Box::new(FormIdValueLookup {
        inner: Ok(CoreFormIdValueLookup::in_memory(entries)),
    })
}

/// Creates an owned SQLite lookup on the process-wide shared Tokio runtime.
///
/// Initialization failures are retained in the returned handle and exposed by
/// `formid_value_lookup_construction_result`; this function never creates a
/// private runtime and never flattens the typed core error into an exception.
fn formid_value_lookup_sqlite_new(database_path: &str, game_table: &str) -> Box<FormIdValueLookup> {
    let inner = block_on(CoreFormIdValueLookup::sqlite(
        PathBuf::from(database_path),
        game_table.to_string(),
    ));
    Box::new(FormIdValueLookup { inner })
}

/// Creates an owned shared-pool lookup adapter over an existing `DbPool`.
fn formid_value_lookup_shared_pool_new(pool: &DbPool) -> Box<FormIdValueLookup> {
    Box::new(FormIdValueLookup {
        inner: Ok(CoreFormIdValueLookup::shared_pool(Arc::clone(&pool.inner))),
    })
}

/// Returns the explicit typed status captured during lookup construction.
fn formid_value_lookup_construction_result(
    lookup: &FormIdValueLookup,
) -> ffi::FormIdValueLookupConstructionResultDto {
    match &lookup.inner {
        Ok(_) => ffi::FormIdValueLookupConstructionResultDto {
            has_lookup: true,
            has_error: false,
            error: empty_formid_value_lookup_error(),
        },
        Err(error) => ffi::FormIdValueLookupConstructionResultDto {
            has_lookup: false,
            has_error: true,
            error: formid_value_lookup_error_to_dto(error),
        },
    }
}

/// Performs one strict lookup on the process-wide shared Tokio runtime.
fn formid_value_lookup_lookup(
    lookup: &FormIdValueLookup,
    formid: &str,
    plugin: &str,
) -> ffi::FormIdValueLookupExecutionResultDto {
    let core_lookup = match &lookup.inner {
        Ok(lookup) => lookup,
        Err(error) => return formid_value_lookup_error_result(error),
    };

    match block_on(core_lookup.lookup(formid, plugin)) {
        Ok(outcome) => ffi::FormIdValueLookupExecutionResultDto {
            has_outcome: true,
            outcome: formid_value_lookup_outcome_to_dto(formid, plugin, outcome),
            has_error: false,
            error: empty_formid_value_lookup_error(),
        },
        Err(error) => formid_value_lookup_error_result(&error),
    }
}

/// Performs one positional strict batch on the process-wide shared Tokio runtime.
///
/// The core batch is all-or-error. A successful DTO contains exactly one
/// outcome per input key in input order; a failed DTO contains no outcomes.
fn formid_value_lookup_lookup_batch(
    lookup: &FormIdValueLookup,
    input: ffi::FormIdValueLookupBatchInputDto,
) -> ffi::FormIdValueLookupBatchExecutionResultDto {
    let core_lookup = match &lookup.inner {
        Ok(lookup) => lookup,
        Err(error) => return formid_value_lookup_batch_error_result(error),
    };

    let pairs: Vec<(String, String)> = input
        .pairs
        .into_iter()
        .map(|pair| (pair.formid, pair.plugin))
        .collect();
    let projected_keys = pairs.clone();

    match block_on(core_lookup.lookup_batch(pairs)) {
        Ok(outcomes) => ffi::FormIdValueLookupBatchExecutionResultDto {
            has_outcomes: true,
            outcomes: projected_keys
                .into_iter()
                .zip(outcomes)
                .map(|((formid, plugin), outcome)| {
                    formid_value_lookup_outcome_to_dto(&formid, &plugin, outcome)
                })
                .collect(),
            has_error: false,
            error: empty_formid_value_lookup_error(),
        },
        Err(error) => formid_value_lookup_batch_error_result(&error),
    }
}

/// Projects one successful core lookup outcome into its CXX semantic DTO.
fn formid_value_lookup_outcome_to_dto(
    formid: &str,
    plugin: &str,
    outcome: CoreFormIdValueLookupOutcome,
) -> ffi::FormIdValueLookupOutcomeDto {
    let (kind, value) = match outcome {
        CoreFormIdValueLookupOutcome::Disabled => {
            (ffi::FormIdValueLookupOutcomeKind::Disabled, String::new())
        }
        CoreFormIdValueLookupOutcome::Missing => {
            (ffi::FormIdValueLookupOutcomeKind::Missing, String::new())
        }
        CoreFormIdValueLookupOutcome::Found(value) => {
            (ffi::FormIdValueLookupOutcomeKind::Found, value)
        }
    };
    ffi::FormIdValueLookupOutcomeDto {
        formid: formid.to_string(),
        plugin: plugin.to_string(),
        kind,
        value,
    }
}

/// Projects the stable core error code and optional lookup key into CXX data.
fn formid_value_lookup_error_to_dto(
    error: &CoreFormIdValueLookupError,
) -> ffi::FormIdValueLookupErrorDto {
    let code = match error.code() {
        "malformed_result" => ffi::FormIdValueLookupErrorCode::MalformedResult,
        "operational_failure" => ffi::FormIdValueLookupErrorCode::OperationalFailure,
        _ => ffi::FormIdValueLookupErrorCode::OperationalFailure,
    };
    ffi::FormIdValueLookupErrorDto {
        code,
        message: error.message().to_string(),
        has_formid: error.formid().is_some(),
        formid: error.formid().unwrap_or_default().to_string(),
        has_plugin: error.plugin().is_some(),
        plugin: error.plugin().unwrap_or_default().to_string(),
    }
}

/// Builds the ignored placeholder for an absent CXX error branch.
fn empty_formid_value_lookup_error() -> ffi::FormIdValueLookupErrorDto {
    ffi::FormIdValueLookupErrorDto {
        code: ffi::FormIdValueLookupErrorCode::OperationalFailure,
        message: String::new(),
        has_formid: false,
        formid: String::new(),
        has_plugin: false,
        plugin: String::new(),
    }
}

/// Builds the error branch of one strict lookup execution envelope.
fn formid_value_lookup_error_result(
    error: &CoreFormIdValueLookupError,
) -> ffi::FormIdValueLookupExecutionResultDto {
    ffi::FormIdValueLookupExecutionResultDto {
        has_outcome: false,
        outcome: ffi::FormIdValueLookupOutcomeDto {
            formid: String::new(),
            plugin: String::new(),
            kind: ffi::FormIdValueLookupOutcomeKind::Missing,
            value: String::new(),
        },
        has_error: true,
        error: formid_value_lookup_error_to_dto(error),
    }
}

/// Builds the error branch of one strict batch execution envelope.
fn formid_value_lookup_batch_error_result(
    error: &CoreFormIdValueLookupError,
) -> ffi::FormIdValueLookupBatchExecutionResultDto {
    ffi::FormIdValueLookupBatchExecutionResultDto {
        has_outcomes: false,
        outcomes: Vec::new(),
        has_error: true,
        error: formid_value_lookup_error_to_dto(error),
    }
}

// ── Typed FormID accessors (CXXS-05) ───────────────────────────────
// Additive per D-08 — existing db_pool_get_entry (returns "") and
// db_pool_get_entries_batch (returns Vec<String> tab-delimited) are UNCHANGED.

/// Typed single-entry FormID lookup.
///
/// Returns a `FormIdEntryDto` with `found: true` if the entry exists in the
/// database (or cache), or `found: false` for misses or errors. The input
/// `formid` and `plugin` are echoed back in the result so C++ callers do not
/// have to track the input separately.
///
/// Bridge contract: this is the typed complement to `db_pool_get_entry`
/// (which returns `""` on miss). Both fns coexist per D-08 (additive, not
/// replacing). The `found` flag is derived from whether the core returned
/// `Ok(Some(_))` — so an `Ok(None)` miss or any `Err` both produce
/// `found: false`.
fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> ffi::FormIdEntryDto {
    let result = block_on(pool.inner.get_entry(formid, plugin, None));
    let (value, found) = match result {
        Ok(Some(v)) => (v, true),
        Ok(None) => (String::new(), false),
        Err(_) => (String::new(), false),
    };
    ffi::FormIdEntryDto {
        formid: formid.to_string(),
        plugin: plugin.to_string(),
        value,
        found,
    }
}

/// Typed batch FormID lookup with positional repackaging.
///
/// Bridge contract (Codex review MEDIUM correction):
/// - The core `get_entries_batch` returns a HIT-ONLY HashMap keyed by
///   `"formid:plugin"`. Misses are ABSENT from the map — not present with
///   empty or null value. This is a MAJOR contract distinction C++ callers
///   must understand.
/// - This wrapper repackages the result into ONE `FormIdEntryDto` PER INPUT
///   PAIR so that `result[i]` corresponds to `(formids[i], plugins[i])`.
///   Misses get `found: false` and `value: ""`.
/// - Length mismatch between `formids` and `plugins` returns an empty Vec
///   (fail-soft, NOT an error). This matches the existing tab-delimited
///   wrapper philosophy.
/// - Empty input returns empty Vec immediately (no runtime cost).
/// - The internal `batch_size` is set to 100 — a balance between SQL query
///   overhead and UI thread responsiveness. C++ callers requesting more than
///   ~1000 entries in one call should chunk on their side to avoid blocking
///   the Qt event loop; this wrapper does NOT chunk on behalf of the caller.
fn db_pool_get_entries_batch_typed(
    pool: &DbPool,
    formids: &[String],
    plugins: &[String],
) -> Vec<ffi::FormIdEntryDto> {
    if formids.len() != plugins.len() || formids.is_empty() {
        return Vec::new();
    }

    let pairs: Vec<(String, String)> = formids
        .iter()
        .zip(plugins.iter())
        .map(|(f, p)| (f.clone(), p.clone()))
        .collect();

    // Core API: get_entries_batch(formid_plugin_pairs, table, batch_size)
    // Returns HashMap<String, String> keyed by "formid:plugin", hit-only.
    let map = block_on(pool.inner.get_entries_batch(pairs.clone(), None, 100)).unwrap_or_default();

    // Positional repackaging — one DTO per input pair, result[i] == (formids[i], plugins[i]).
    // Misses (absent from hit-only map) get found: false.
    pairs
        .into_iter()
        .map(|(formid, plugin)| {
            let lookup_key = format!("{}:{}", formid, plugin);
            match map.get(&lookup_key) {
                Some(v) => ffi::FormIdEntryDto {
                    formid,
                    plugin,
                    value: v.clone(),
                    found: true,
                },
                None => ffi::FormIdEntryDto {
                    formid,
                    plugin,
                    value: String::new(),
                    found: false,
                },
            }
        })
        .collect()
}

#[cxx::bridge(namespace = "classic::database")]
mod ffi {
    /// One deterministic reply kind accepted by the owned in-memory adapter.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum FormIdValueLookupReplyKind {
        Missing = 0,
        Found = 1,
        OperationalFailure = 2,
    }

    /// Semantic category of one successful FormID Value Lookup outcome.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum FormIdValueLookupOutcomeKind {
        Disabled = 0,
        Missing = 1,
        Found = 2,
    }

    /// Stable typed category of one strict FormID Value Lookup failure.
    ///
    /// These variants project the core codes `malformed_result` and
    /// `operational_failure`, respectively.
    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    enum FormIdValueLookupErrorCode {
        MalformedResult = 0,
        OperationalFailure = 1,
    }

    /// One fully owned scripted reply for the in-memory lookup adapter.
    ///
    /// `value` is read only for `Found`; `error_message` is read only for
    /// `OperationalFailure`. A blank `Found` value produces `MalformedResult`
    /// when looked up.
    struct FormIdValueLookupInMemoryEntryDto {
        formid: String,
        plugin: String,
        reply_kind: FormIdValueLookupReplyKind,
        value: String,
        error_message: String,
    }

    /// Owned construction input for one deterministic in-memory adapter.
    struct FormIdValueLookupInMemoryConfigurationDto {
        entries: Vec<FormIdValueLookupInMemoryEntryDto>,
    }

    /// One owned key in a positional batch lookup request.
    struct FormIdValueLookupKeyDto {
        formid: String,
        plugin: String,
    }

    /// Owned positional input for a strict batch lookup.
    struct FormIdValueLookupBatchInputDto {
        pairs: Vec<FormIdValueLookupKeyDto>,
    }

    /// One typed successful outcome with its corresponding input key.
    struct FormIdValueLookupOutcomeDto {
        formid: String,
        plugin: String,
        kind: FormIdValueLookupOutcomeKind,
        value: String,
    }

    /// Typed strict lookup failure with optional input-key context.
    struct FormIdValueLookupErrorDto {
        code: FormIdValueLookupErrorCode,
        message: String,
        has_formid: bool,
        formid: String,
        has_plugin: bool,
        plugin: String,
    }

    /// Explicit status for an opaque FormID Value Lookup handle.
    ///
    /// Exactly one of `has_lookup` and `has_error` is true. The error field is
    /// a placeholder when `has_error` is false.
    struct FormIdValueLookupConstructionResultDto {
        has_lookup: bool,
        has_error: bool,
        error: FormIdValueLookupErrorDto,
    }

    /// Exactly one typed successful lookup outcome or typed lookup failure.
    struct FormIdValueLookupExecutionResultDto {
        has_outcome: bool,
        outcome: FormIdValueLookupOutcomeDto,
        has_error: bool,
        error: FormIdValueLookupErrorDto,
    }

    /// Exactly one positional outcome vector or one typed whole-batch failure.
    struct FormIdValueLookupBatchExecutionResultDto {
        has_outcomes: bool,
        outcomes: Vec<FormIdValueLookupOutcomeDto>,
        has_error: bool,
        error: FormIdValueLookupErrorDto,
    }

    // CXXS-05: Typed FormID lookup DTO (additive per D-08)

    /// Typed DTO for a single FormID database lookup result.
    ///
    /// C++ callers should check `found` before using `value`. An uninitialized
    /// pool, a cache miss, or a DB error all produce `found: false` with an
    /// empty `value`. The `formid` and `plugin` fields echo the input so
    /// callers do not have to track the input separately in batch scenarios.
    struct FormIdEntryDto {
        formid: String,
        plugin: String,
        value: String,
        found: bool,
    }

    extern "Rust" {
        type DbPool;
        type FormIdValueLookup;

        fn db_pool_new(game_table: &str, max_connections: u32, cache_ttl_secs: u64) -> Box<DbPool>;
        fn db_pool_initialize(pool: &DbPool, db_paths: &[String]) -> Result<()>;
        fn db_pool_get_entry(pool: &DbPool, formid: &str, plugin: &str) -> String;
        fn db_pool_get_entries_batch(
            pool: &DbPool,
            formids: &[String],
            plugins: &[String],
        ) -> Vec<String>;
        fn db_pool_is_available(pool: &DbPool) -> bool;
        fn db_pool_cache_size(pool: &DbPool) -> usize;
        fn db_pool_clear_cache(pool: &DbPool, expired_only: bool) -> usize;
        fn db_pool_close(pool: &DbPool) -> Result<()>;
        fn db_pool_game_table(pool: &DbPool) -> String;

        fn formid_value_lookup_disabled_new() -> Box<FormIdValueLookup>;
        fn formid_value_lookup_in_memory_new(
            configuration: FormIdValueLookupInMemoryConfigurationDto,
        ) -> Box<FormIdValueLookup>;
        fn formid_value_lookup_sqlite_new(
            database_path: &str,
            game_table: &str,
        ) -> Box<FormIdValueLookup>;
        fn formid_value_lookup_shared_pool_new(pool: &DbPool) -> Box<FormIdValueLookup>;
        fn formid_value_lookup_construction_result(
            lookup: &FormIdValueLookup,
        ) -> FormIdValueLookupConstructionResultDto;
        fn formid_value_lookup_lookup(
            lookup: &FormIdValueLookup,
            formid: &str,
            plugin: &str,
        ) -> FormIdValueLookupExecutionResultDto;
        fn formid_value_lookup_lookup_batch(
            lookup: &FormIdValueLookup,
            input: FormIdValueLookupBatchInputDto,
        ) -> FormIdValueLookupBatchExecutionResultDto;

        // CXXS-05: Typed FormID accessors (additive per D-08)
        fn db_pool_get_entry_typed(pool: &DbPool, formid: &str, plugin: &str) -> FormIdEntryDto;
        fn db_pool_get_entries_batch_typed(
            pool: &DbPool,
            formids: &[String],
            plugins: &[String],
        ) -> Vec<FormIdEntryDto>;
    }
}

#[cfg(test)]
#[path = "database_tests.rs"]
mod tests;
