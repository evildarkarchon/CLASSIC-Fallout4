use super::*;

#[test]
fn test_db_pool_new() {
    let pool = db_pool_new("Fallout4", 4, 300);
    assert_eq!(db_pool_game_table(&pool), "Fallout4");
}

#[test]
fn test_db_pool_not_available_before_init() {
    let pool = db_pool_new("Fallout4", 4, 300);
    assert!(!db_pool_is_available(&pool));
}

#[test]
fn test_db_pool_cache_operations() {
    let pool = db_pool_new("Fallout4", 4, 300);
    assert_eq!(db_pool_cache_size(&pool), 0);
    let cleared = db_pool_clear_cache(&pool, false);
    assert_eq!(cleared, 0);
}

#[test]
fn test_db_pool_get_entry_before_init() {
    let pool = db_pool_new("Fallout4", 4, 300);
    let entry = db_pool_get_entry(&pool, "00000001", "Fallout4.esm");
    assert!(entry.is_empty());
}

// ── CXXS-05 typed FormID lookup tests ──────────────────────────────

#[test]
fn test_db_pool_get_entry_typed_uninitialized_returns_not_found() {
    let pool = db_pool_new("Fallout4", 4, 60);
    let result = db_pool_get_entry_typed(&pool, "0x000ABCDE", "Fallout4.esm");
    assert!(
        !result.found,
        "uninitialized pool should return found: false"
    );
    assert_eq!(result.formid, "0x000ABCDE", "formid must be echoed back");
    assert_eq!(result.plugin, "Fallout4.esm", "plugin must be echoed back");
    assert!(result.value.is_empty(), "value should be empty on miss");
}

#[test]
fn test_db_pool_get_entries_batch_typed_empty_returns_empty() {
    let pool = db_pool_new("Fallout4", 4, 60);
    let result = db_pool_get_entries_batch_typed(&pool, &[], &[]);
    assert!(result.is_empty(), "empty input must return empty Vec");
}

#[test]
fn test_db_pool_get_entries_batch_typed_length_mismatch_returns_empty() {
    let pool = db_pool_new("Fallout4", 4, 60);
    // formids has 1 entry, plugins has 0 — length mismatch → fail-soft
    let result = db_pool_get_entries_batch_typed(&pool, &["0x000ABCDE".to_string()], &[]);
    assert!(
        result.is_empty(),
        "length mismatch must return empty Vec (fail-soft)"
    );
}

#[test]
fn test_db_pool_get_entries_batch_typed_positional_repackaging() {
    // Positional repackaging contract: result[i] corresponds to (formids[i], plugins[i]).
    // On an uninitialized pool all entries are misses, but the positional mapping must hold.
    let pool = db_pool_new("Fallout4", 4, 60);
    let result = db_pool_get_entries_batch_typed(
        &pool,
        &["0x000ABCDE".to_string(), "0x000FEDCB".to_string()],
        &["Fallout4.esm".to_string(), "DLC01.esm".to_string()],
    );
    assert_eq!(
        result.len(),
        2,
        "one DTO per input pair (positional repackaging)"
    );
    assert_eq!(result[0].formid, "0x000ABCDE");
    assert_eq!(result[0].plugin, "Fallout4.esm");
    assert!(!result[0].found);
    assert_eq!(result[1].formid, "0x000FEDCB");
    assert_eq!(result[1].plugin, "DLC01.esm");
    assert!(!result[1].found);
}

#[test]
fn test_db_pool_get_entry_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    let pool = db_pool_new("Fallout4", 4, 300);
    let entry = db_pool_get_entry(&pool, "00000001", "Fallout4.esm");
    assert!(
        entry.is_empty(),
        "db_pool_get_entry must still return empty string on miss (D-08)"
    );
}

#[test]
fn test_db_pool_get_entries_batch_still_works_d08_regression() {
    // D-08 regression: existing fn must remain unchanged
    let pool = db_pool_new("Fallout4", 4, 300);
    let result = db_pool_get_entries_batch(
        &pool,
        &["00000001".to_string()],
        &["Fallout4.esm".to_string()],
    );
    // On uninitialized pool returns empty Vec (no tab-delimited hit entries)
    assert!(
        result.is_empty(),
        "db_pool_get_entries_batch must still work (D-08)"
    );
}

/// Builds one owned scripted reply for strict lookup bridge tests.
fn scripted_reply(
    formid: &str,
    plugin: &str,
    reply_kind: ffi::FormIdValueLookupReplyKind,
    value: &str,
    error_message: &str,
) -> ffi::FormIdValueLookupInMemoryEntryDto {
    ffi::FormIdValueLookupInMemoryEntryDto {
        formid: formid.to_string(),
        plugin: plugin.to_string(),
        reply_kind,
        value: value.to_string(),
        error_message: error_message.to_string(),
    }
}

#[test]
fn strict_lookup_disabled_outcome_remains_distinct() {
    let lookup = formid_value_lookup_disabled_new();
    let construction = formid_value_lookup_construction_result(&lookup);
    assert!(construction.has_lookup);
    assert!(!construction.has_error);

    let result = formid_value_lookup_lookup(&lookup, "000800", "SomeMod.esp");
    assert!(result.has_outcome);
    assert!(!result.has_error);
    assert_eq!(
        result.outcome.kind,
        ffi::FormIdValueLookupOutcomeKind::Disabled
    );
    assert!(result.outcome.value.is_empty());
}

#[test]
fn strict_lookup_scripted_hit_and_miss_remain_distinct() {
    let lookup =
        formid_value_lookup_in_memory_new(ffi::FormIdValueLookupInMemoryConfigurationDto {
            entries: vec![scripted_reply(
                "000801",
                "SomeMod.esp",
                ffi::FormIdValueLookupReplyKind::Found,
                "Laser Musket",
                "",
            )],
        });

    let hit = formid_value_lookup_lookup(&lookup, "000801", "SOMEMOD.ESP");
    assert!(hit.has_outcome);
    assert_eq!(hit.outcome.kind, ffi::FormIdValueLookupOutcomeKind::Found);
    assert_eq!(hit.outcome.value, "Laser Musket");

    let miss = formid_value_lookup_lookup(&lookup, "000899", "SomeMod.esp");
    assert!(miss.has_outcome);
    assert_eq!(
        miss.outcome.kind,
        ffi::FormIdValueLookupOutcomeKind::Missing
    );
    assert!(miss.outcome.value.is_empty());
}

#[test]
fn strict_lookup_scripted_malformed_result_has_typed_error() {
    let lookup =
        formid_value_lookup_in_memory_new(ffi::FormIdValueLookupInMemoryConfigurationDto {
            entries: vec![scripted_reply(
                "000802",
                "SomeMod.esp",
                ffi::FormIdValueLookupReplyKind::Found,
                " \t ",
                "",
            )],
        });

    let result = formid_value_lookup_lookup(&lookup, "000802", "SomeMod.esp");
    assert!(!result.has_outcome);
    assert!(result.has_error);
    assert_eq!(
        result.error.code,
        ffi::FormIdValueLookupErrorCode::MalformedResult
    );
    assert!(result.error.has_formid);
    assert_eq!(result.error.formid, "000802");
}

#[test]
fn strict_lookup_scripted_operational_failure_has_typed_error() {
    let lookup =
        formid_value_lookup_in_memory_new(ffi::FormIdValueLookupInMemoryConfigurationDto {
            entries: vec![scripted_reply(
                "000803",
                "SomeMod.esp",
                ffi::FormIdValueLookupReplyKind::OperationalFailure,
                "",
                "fixture offline",
            )],
        });

    let result = formid_value_lookup_lookup(&lookup, "000803", "SomeMod.esp");
    assert!(!result.has_outcome);
    assert!(result.has_error);
    assert_eq!(
        result.error.code,
        ffi::FormIdValueLookupErrorCode::OperationalFailure
    );
    assert!(result.error.message.contains("fixture offline"));
}

#[test]
fn strict_lookup_batch_preserves_input_positions() {
    let lookup =
        formid_value_lookup_in_memory_new(ffi::FormIdValueLookupInMemoryConfigurationDto {
            entries: vec![scripted_reply(
                "000804",
                "SomeMod.esp",
                ffi::FormIdValueLookupReplyKind::Found,
                "Railway Rifle",
                "",
            )],
        });

    let result = formid_value_lookup_lookup_batch(
        &lookup,
        ffi::FormIdValueLookupBatchInputDto {
            pairs: vec![
                ffi::FormIdValueLookupKeyDto {
                    formid: "000804".to_string(),
                    plugin: "SomeMod.esp".to_string(),
                },
                ffi::FormIdValueLookupKeyDto {
                    formid: "000899".to_string(),
                    plugin: "SomeMod.esp".to_string(),
                },
            ],
        },
    );

    assert!(result.has_outcomes);
    assert!(!result.has_error);
    assert_eq!(result.outcomes.len(), 2);
    assert_eq!(
        result.outcomes[0].kind,
        ffi::FormIdValueLookupOutcomeKind::Found
    );
    assert_eq!(result.outcomes[0].value, "Railway Rifle");
    assert_eq!(
        result.outcomes[1].kind,
        ffi::FormIdValueLookupOutcomeKind::Missing
    );
}

#[test]
fn strict_lookup_batch_failure_returns_no_partial_outcomes() {
    let lookup =
        formid_value_lookup_in_memory_new(ffi::FormIdValueLookupInMemoryConfigurationDto {
            entries: vec![
                scripted_reply(
                    "000804",
                    "SomeMod.esp",
                    ffi::FormIdValueLookupReplyKind::Found,
                    "Railway Rifle",
                    "",
                ),
                scripted_reply(
                    "000805",
                    "SomeMod.esp",
                    ffi::FormIdValueLookupReplyKind::OperationalFailure,
                    "",
                    "fixture offline",
                ),
            ],
        });

    let result = formid_value_lookup_lookup_batch(
        &lookup,
        ffi::FormIdValueLookupBatchInputDto {
            pairs: vec![
                ffi::FormIdValueLookupKeyDto {
                    formid: "000804".to_string(),
                    plugin: "SomeMod.esp".to_string(),
                },
                ffi::FormIdValueLookupKeyDto {
                    formid: "000805".to_string(),
                    plugin: "SomeMod.esp".to_string(),
                },
            ],
        },
    );

    assert!(!result.has_outcomes);
    assert!(result.outcomes.is_empty());
    assert!(result.has_error);
    assert_eq!(
        result.error.code,
        ffi::FormIdValueLookupErrorCode::OperationalFailure
    );
}

#[test]
fn strict_lookup_sqlite_construction_failure_remains_typed() {
    let directory = tempfile::tempdir().expect("temporary directory should be created");
    let missing_path = directory.path().join("missing-formid-values.db");
    let lookup = formid_value_lookup_sqlite_new(
        missing_path
            .to_str()
            .expect("temporary path should be valid UTF-8"),
        "Fallout4",
    );

    let construction = formid_value_lookup_construction_result(&lookup);
    assert!(!construction.has_lookup);
    assert!(construction.has_error);
    assert_eq!(
        construction.error.code,
        ffi::FormIdValueLookupErrorCode::OperationalFailure
    );
    assert!(
        construction
            .error
            .message
            .contains("database file not found")
    );

    let lookup_result = formid_value_lookup_lookup(&lookup, "000805", "SomeMod.esp");
    assert!(lookup_result.has_error);
    assert_eq!(
        lookup_result.error.code,
        ffi::FormIdValueLookupErrorCode::OperationalFailure
    );
}

#[test]
fn strict_lookup_existing_db_pool_adapter_preserves_operational_failure() {
    // An invalid table name fails strict validation before any SQLite query,
    // proving the adapter uses the existing shared pool without fail-soft collapse.
    let pool = db_pool_new("Fallout4;DROP", 1, 60);
    let lookup = formid_value_lookup_shared_pool_new(&pool);
    let construction = formid_value_lookup_construction_result(&lookup);
    assert!(construction.has_lookup);

    let result = formid_value_lookup_lookup(&lookup, "000806", "SomeMod.esp");
    assert!(result.has_error);
    assert_eq!(
        result.error.code,
        ffi::FormIdValueLookupErrorCode::OperationalFailure
    );
    assert!(
        result
            .error
            .message
            .contains("Invalid game table identifier")
    );
}
