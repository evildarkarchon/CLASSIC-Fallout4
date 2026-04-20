use super::*;
use sqlx::sqlite::SqlitePoolOptions;
use std::path::PathBuf;
use std::time::Duration;
use tempfile::NamedTempFile;

async fn create_formid_test_database(
    table_name: &str,
    entries: &[(&str, &str, &str)],
) -> (NamedTempFile, PathBuf) {
    let temp_file =
        NamedTempFile::with_suffix(".db").expect("failed to create temp sqlite file");
    let db_path = temp_file.path().to_path_buf();
    let conn_str = format!("sqlite://{}?mode=rwc", db_path.display());

    let pool = SqlitePoolOptions::new()
        .max_connections(1)
        .connect(&conn_str)
        .await
        .expect("failed to connect to temp sqlite database");

    let create_table_sql = format!(
        "CREATE TABLE IF NOT EXISTS {} (
            formid TEXT NOT NULL,
            plugin TEXT NOT NULL,
            entry TEXT NOT NULL,
            PRIMARY KEY (formid, plugin)
        )",
        table_name
    );
    sqlx::query(&create_table_sql)
        .execute(&pool)
        .await
        .expect("failed to create test table");

    for (formid, plugin, entry) in entries {
        let insert_sql = format!(
            "INSERT OR REPLACE INTO {} (formid, plugin, entry) VALUES (?, ?, ?)",
            table_name
        );
        sqlx::query(&insert_sql)
            .bind(*formid)
            .bind(*plugin)
            .bind(*entry)
            .execute(&pool)
            .await
            .expect("failed to insert test entry");
    }

    pool.close().await;
    (temp_file, db_path)
}

async fn create_test_pool_with_entries(
    entries: &[(&str, &str, &str)],
) -> (Arc<DatabasePool>, NamedTempFile) {
    let table_name = "Fallout4";
    let (temp_file, db_path) = create_formid_test_database(table_name, entries).await;

    let db_pool = Arc::new(DatabasePool::new(
        Some(4),
        Duration::from_secs(60),
        table_name.to_string(),
    ));
    db_pool
        .initialize(vec![db_path])
        .await
        .expect("failed to initialize database pool");
    (db_pool, temp_file)
}

fn build_test_analyzer(
    db_pool: Option<Arc<DatabasePool>>,
    show_formid_values: bool,
) -> FormIDAnalyzerCore {
    FormIDAnalyzerCore::new(
        db_pool,
        show_formid_values,
        "Buffout 4".to_string(),
        Vec::new(),
        Vec::new(),
        Vec::new(),
    )
    .expect("failed to build test analyzer")
}

fn report_rows(lines: &[String]) -> Vec<&str> {
    lines
        .iter()
        .map(String::as_str)
        .filter(|line| line.starts_with("- "))
        .collect()
}

#[tokio::test]
async fn formid_match_resolves_mixed_case_plugin_with_batch_lookup() {
    let (db_pool, _temp_file) =
        create_test_pool_with_entries(&[("123456", "TestMod.esp", "Case Match Entry")]).await;
    let analyzer = build_test_analyzer(Some(db_pool), true);

    let formids = vec!["Form ID: 01123456".to_string()];
    let mut crashlog_plugins = IndexMap::new();
    crashlog_plugins.insert("TESTMOD.ESP".to_string(), "01".to_string());

    let lines = analyzer
        .formid_match(formids, &crashlog_plugins)
        .await
        .expect("formid_match should succeed");

    assert!(
        lines.contains(&"- TESTMOD.ESP | 01123456 | Case Match Entry | 1\n".to_string()),
        "Expected mixed-case plugin lookup to resolve through batched path"
    );
}

#[tokio::test]
async fn formid_match_aggregates_duplicate_formids_with_resolved_value() {
    let (db_pool, _temp_file) =
        create_test_pool_with_entries(&[("ABCDEF", "Duplicate.esp", "Duplicate Entry")]).await;
    let analyzer = build_test_analyzer(Some(db_pool), true);

    let formids = vec![
        "Form ID: 02ABCDEF".to_string(),
        "Form ID: 02ABCDEF".to_string(),
    ];
    let mut crashlog_plugins = IndexMap::new();
    crashlog_plugins.insert("Duplicate.esp".to_string(), "02".to_string());

    let lines = analyzer
        .formid_match(formids, &crashlog_plugins)
        .await
        .expect("formid_match should succeed");

    let rows = report_rows(&lines);
    assert_eq!(
        rows.len(),
        1,
        "Duplicate FormIDs should collapse to one output row"
    );
    assert_eq!(
        rows[0], "- Duplicate.esp | 02ABCDEF | Duplicate Entry | 2\n",
        "Collapsed duplicate row should preserve resolved value and aggregated count"
    );
}

#[tokio::test]
async fn formid_match_preserves_fallback_format_for_partial_misses() {
    let (db_pool, _temp_file) =
        create_test_pool_with_entries(&[("AAAAAA", "HasEntry.esp", "Found Entry")]).await;
    let analyzer = build_test_analyzer(Some(db_pool), true);

    let formids = vec![
        "Form ID: 03AAAAAA".to_string(),
        "Form ID: 04BBBBBB".to_string(),
    ];
    let mut crashlog_plugins = IndexMap::new();
    crashlog_plugins.insert("HasEntry.esp".to_string(), "03".to_string());
    crashlog_plugins.insert("MissingEntry.esp".to_string(), "04".to_string());

    let lines = analyzer
        .formid_match(formids, &crashlog_plugins)
        .await
        .expect("formid_match should succeed");

    assert!(
        lines.contains(&"- HasEntry.esp | 03AAAAAA | Found Entry | 1\n".to_string()),
        "Resolved candidates should keep four-column format"
    );
    assert!(
        lines.contains(&"- MissingEntry.esp | 04BBBBBB | 1\n".to_string()),
        "Unresolved candidates should keep existing fallback three-column format"
    );
}

#[tokio::test]
async fn formid_match_keeps_all_rows_when_candidates_exceed_batch_size() {
    let mut entries_owned = Vec::new();
    let mut formids = Vec::new();
    for i in 0..130 {
        let suffix = format!("{:06X}", i);
        let entry = format!("Entry {}", i);
        entries_owned.push((suffix, "LargeBatch.esp".to_string(), entry));
        formids.push(format!("Form ID: 05{}", entries_owned[i].0));
    }

    let entries_refs: Vec<(&str, &str, &str)> = entries_owned
        .iter()
        .map(|(formid, plugin, entry)| (formid.as_str(), plugin.as_str(), entry.as_str()))
        .collect();

    let (db_pool, _temp_file) = create_test_pool_with_entries(&entries_refs).await;
    let analyzer = build_test_analyzer(Some(db_pool), true);

    let mut crashlog_plugins = IndexMap::new();
    crashlog_plugins.insert("LargeBatch.esp".to_string(), "05".to_string());

    let lines = analyzer
        .formid_match(formids, &crashlog_plugins)
        .await
        .expect("formid_match should succeed");

    let rows = report_rows(&lines);
    assert_eq!(
        rows.len(),
        130,
        "All candidates should be rendered even across multiple batches"
    );
    assert!(
        rows.iter().any(|row| row.contains("Entry 0")),
        "Expected resolved output for the first candidate"
    );
    assert!(
        rows.iter().any(|row| row.contains("Entry 129")),
        "Expected resolved output for the last candidate"
    );
}

#[tokio::test]
async fn formid_match_with_crashgen_name_override_uses_effective_name() {
    let analyzer = build_test_analyzer(None, false);
    let formids = vec!["Form ID: 01123456".to_string()];
    let mut crashlog_plugins = IndexMap::new();
    crashlog_plugins.insert("TestMod.esp".to_string(), "01".to_string());

    let lines = analyzer
        .formid_match_with_crashgen_name(formids, &crashlog_plugins, "Addictol")
        .await
        .expect("formid_match should succeed");
    let output = lines.join("");

    assert!(output.contains("caught by Addictol"));
    assert!(!output.contains("caught by Buffout 4"));
}
