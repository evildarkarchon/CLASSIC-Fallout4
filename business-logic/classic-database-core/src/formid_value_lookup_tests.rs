use crate::{
    DatabasePool, FormIdValueLookup, FormIdValueLookupEntry, FormIdValueLookupInMemoryReply,
    FormIdValueLookupOutcome,
};
use sqlx::sqlite::SqlitePoolOptions;
use std::sync::Arc;
use std::time::Duration;
use tempfile::NamedTempFile;

/// Creates a real SQLite fixture from trusted, static setup statements.
async fn create_sqlite_fixture_from_statements(
    statements: &[&str],
) -> (NamedTempFile, std::path::PathBuf) {
    let file = NamedTempFile::new().expect("temporary SQLite file should be created");
    let path = file.path().to_path_buf();
    let connection = format!("sqlite://{}?mode=rwc", path.display());
    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect(&connection)
        .await
        .expect("SQLite fixture should open");
    for statement in statements {
        sqlx::query(sqlx::AssertSqlSafe((*statement).to_string()))
            .execute(&pool)
            .await
            .expect("SQLite fixture setup statement should succeed");
    }
    pool.close().await;
    (file, path)
}

/// Creates a real SQLite fixture with one canonical FormID value row.
async fn create_sqlite_fixture() -> (NamedTempFile, std::path::PathBuf) {
    create_sqlite_fixture_from_statements(&[
        "CREATE TABLE Fallout4 (formid TEXT NOT NULL, plugin TEXT NOT NULL, entry TEXT NOT NULL)",
        "INSERT INTO Fallout4 (formid, plugin, entry) \
         VALUES ('000804', 'SomeMod.esp', 'Railway Rifle')",
    ])
    .await
}

/// Creates a SQLite fixture whose table cannot satisfy a FormID value query.
async fn create_broken_sqlite_fixture() -> (NamedTempFile, std::path::PathBuf) {
    create_sqlite_fixture_from_statements(&[
        "CREATE TABLE Fallout4 (formid TEXT NOT NULL, plugin TEXT NOT NULL)",
    ])
    .await
}

/// Creates a SQLite fixture for a different supported game's FormID table.
async fn create_skyrim_sqlite_fixture() -> (NamedTempFile, std::path::PathBuf) {
    create_sqlite_fixture_from_statements(&[
        "CREATE TABLE Skyrim (formid TEXT NOT NULL, plugin TEXT NOT NULL, entry TEXT NOT NULL)",
    ])
    .await
}

#[test]
fn disabled_lookup_is_explicit_semantic_data() {
    let lookup = FormIdValueLookup::disabled();

    let outcome = classic_shared_core::get_runtime()
        .block_on(lookup.lookup("000800", "SomeMod.esp"))
        .expect("disabled lookup should complete successfully");

    assert_eq!(outcome, FormIdValueLookupOutcome::Disabled);
}

#[test]
fn in_memory_lookup_returns_an_owned_hit() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "000800",
        "SomeMod.esp",
        FormIdValueLookupInMemoryReply::Value(Some("Laser Musket".to_string())),
    )]);

    let outcome = classic_shared_core::get_runtime()
        .block_on(lookup.lookup("000800", "SOMEMOD.ESP"))
        .expect("in-memory hit should complete successfully");

    assert_eq!(
        outcome,
        FormIdValueLookupOutcome::Found("Laser Musket".to_string())
    );
}

#[test]
fn in_memory_lookup_returns_a_successful_miss_for_an_unknown_key() {
    let lookup = FormIdValueLookup::in_memory(Vec::new());

    let outcome = classic_shared_core::get_runtime()
        .block_on(lookup.lookup("000801", "SomeMod.esp"))
        .expect("in-memory miss should complete successfully");

    assert_eq!(outcome, FormIdValueLookupOutcome::Missing);
}

#[test]
fn in_memory_lookup_rejects_a_malformed_reply_distinctly() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "000802",
        "SomeMod.esp",
        FormIdValueLookupInMemoryReply::Value(Some(" \t ".to_string())),
    )]);

    let error = classic_shared_core::get_runtime()
        .block_on(lookup.lookup("000802", "SomeMod.esp"))
        .expect_err("blank adapter reply must be rejected as malformed");

    assert_eq!(error.code(), "malformed_result");
    assert!(error.to_string().contains("000802:SomeMod.esp"));
}

#[test]
fn in_memory_lookup_propagates_an_operational_failure_distinctly() {
    let lookup = FormIdValueLookup::in_memory(vec![FormIdValueLookupEntry::new(
        "000803",
        "SomeMod.esp",
        FormIdValueLookupInMemoryReply::OperationalFailure("fixture offline".to_string()),
    )]);

    let error = classic_shared_core::get_runtime()
        .block_on(lookup.lookup("000803", "SomeMod.esp"))
        .expect_err("scripted operational failure must remain an error");

    assert_eq!(error.code(), "operational_failure");
    assert!(error.message().contains("fixture offline"));
}

#[test]
fn shared_pool_adapter_returns_sqlite_hits() {
    classic_shared_core::get_runtime().block_on(async {
        let (_file, path) = create_sqlite_fixture().await;
        let pool = Arc::new(DatabasePool::new(
            Some(1),
            Duration::from_secs(60),
            "Fallout4".to_string(),
        ));
        pool.initialize(vec![path])
            .await
            .expect("shared pool should initialize");
        let lookup = FormIdValueLookup::shared_pool(Arc::clone(&pool));

        let outcome = lookup
            .lookup("000804", "SomeMod.esp")
            .await
            .expect("shared-pool lookup should succeed");

        assert_eq!(
            outcome,
            FormIdValueLookupOutcome::Found("Railway Rifle".to_string())
        );
        pool.close().await.expect("shared pool should close");
    });
}

#[test]
fn shared_pool_batch_skips_databases_without_the_active_game_table() {
    classic_shared_core::get_runtime().block_on(async {
        let (_fallout_file, fallout_path) = create_sqlite_fixture().await;
        let (_skyrim_file, skyrim_path) = create_skyrim_sqlite_fixture().await;
        let pool = Arc::new(DatabasePool::new(
            Some(2),
            Duration::from_secs(60),
            "Fallout4".to_string(),
        ));
        pool.initialize(vec![skyrim_path, fallout_path])
            .await
            .expect("mixed-game shared pool should initialize");
        let lookup = FormIdValueLookup::shared_pool(Arc::clone(&pool));

        let outcomes = lookup
            .lookup_batch(vec![
                ("000804".to_string(), "SomeMod.esp".to_string()),
                ("000899".to_string(), "SomeMod.esp".to_string()),
            ])
            .await
            .expect("databases without Fallout4 should not fail a Fallout4 batch lookup");

        assert_eq!(
            outcomes,
            vec![
                FormIdValueLookupOutcome::Found("Railway Rifle".to_string()),
                FormIdValueLookupOutcome::Missing,
            ]
        );
        pool.close().await.expect("shared pool should close");
    });
}

#[test]
fn shared_pool_adapter_never_converts_query_failure_to_a_miss() {
    classic_shared_core::get_runtime().block_on(async {
        let (_file, path) = create_broken_sqlite_fixture().await;
        let pool = Arc::new(DatabasePool::new(
            Some(1),
            Duration::from_secs(60),
            "Fallout4".to_string(),
        ));
        pool.initialize(vec![path])
            .await
            .expect("shared pool should initialize before its malformed schema is queried");
        let lookup = FormIdValueLookup::shared_pool(Arc::clone(&pool));

        let error = lookup
            .lookup("000805", "SomeMod.esp")
            .await
            .expect_err("query failure must not be reported as a successful miss");

        assert_eq!(error.code(), "operational_failure");
        assert!(error.message().contains("no such column: entry"));
        pool.close().await.expect("shared pool should close");
    });
}

#[test]
fn owned_sqlite_adapter_returns_hits_without_a_private_runtime() {
    classic_shared_core::get_runtime().block_on(async {
        let (_file, path) = create_sqlite_fixture().await;
        let lookup = FormIdValueLookup::sqlite(path, "Fallout4".to_string())
            .await
            .expect("owned SQLite adapter should initialize");

        let outcome = lookup
            .lookup("000804", "SomeMod.esp")
            .await
            .expect("owned SQLite lookup should succeed");

        assert_eq!(
            outcome,
            FormIdValueLookupOutcome::Found("Railway Rifle".to_string())
        );
    });
}

#[test]
fn owned_sqlite_batch_preserves_hit_and_miss_positions() {
    classic_shared_core::get_runtime().block_on(async {
        let (_file, path) = create_sqlite_fixture().await;
        let lookup = FormIdValueLookup::sqlite(path, "Fallout4".to_string())
            .await
            .expect("owned SQLite adapter should initialize");

        let outcomes = lookup
            .lookup_batch(vec![
                ("000804".to_string(), "SomeMod.esp".to_string()),
                ("000899".to_string(), "SomeMod.esp".to_string()),
            ])
            .await
            .expect("owned SQLite batch should succeed");

        assert_eq!(
            outcomes,
            vec![
                FormIdValueLookupOutcome::Found("Railway Rifle".to_string()),
                FormIdValueLookupOutcome::Missing,
            ]
        );
    });
}

#[test]
fn strict_database_batch_never_returns_partial_misses_after_query_failure() {
    classic_shared_core::get_runtime().block_on(async {
        let (_file, path) = create_broken_sqlite_fixture().await;
        let lookup = FormIdValueLookup::sqlite(path, "Fallout4".to_string())
            .await
            .expect("owned SQLite adapter should open before querying its malformed schema");

        let error = lookup
            .lookup_batch(vec![
                ("000805".to_string(), "SomeMod.esp".to_string()),
                ("000806".to_string(), "OtherMod.esp".to_string()),
            ])
            .await
            .expect_err("strict batch query failure must not become partial misses");

        assert_eq!(error.code(), "operational_failure");
        assert!(error.message().contains("no such column: entry"));
    });
}

#[test]
fn sqlite_adapter_rejects_a_missing_database_as_an_operational_failure() {
    let error = classic_shared_core::get_runtime()
        .block_on(FormIdValueLookup::sqlite(
            std::path::PathBuf::from("missing-formid-values.db"),
            "Fallout4".to_string(),
        ))
        .expect_err("missing SQLite database must not create an empty lookup adapter");

    assert_eq!(error.code(), "operational_failure");
    assert!(error.message().contains("database file not found"));
    assert_eq!(error.formid(), None);
}

#[test]
fn lookup_handle_is_cloneable_send_and_sync_for_concurrent_reuse() {
    fn assert_clone_send_sync<T: Clone + Send + Sync>() {}

    assert_clone_send_sync::<FormIdValueLookup>();
}
