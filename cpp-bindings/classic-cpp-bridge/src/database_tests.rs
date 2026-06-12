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
