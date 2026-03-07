//! Deterministic SQLite fixture generation for Rust DB benchmarks.
//!
//! This module is opt-in and intended for benchmarks that need local, reproducible
//! SQLite datasets. It avoids random input generation and keeps fixture data scoped
//! to temporary files.

#![allow(dead_code)]

use sqlx::sqlite::SqlitePoolOptions;
use std::path::PathBuf;
use tempfile::NamedTempFile;

/// Default table name used by benchmark fixtures.
pub const DEFAULT_TABLE_NAME: &str = "Fallout4";

/// Fixed plugin/prefix map used for deterministic FormID generation.
#[derive(Clone, Copy, Debug)]
pub struct PluginSpec {
    pub plugin: &'static str,
    pub prefix: &'static str,
}

/// Canonical plugin catalog for generated fixture records.
pub const PLUGIN_SPECS: [PluginSpec; 6] = [
    PluginSpec {
        plugin: "Fallout4.esm",
        prefix: "01",
    },
    PluginSpec {
        plugin: "DLCRobot.esm",
        prefix: "02",
    },
    PluginSpec {
        plugin: "DLCWorkshop01.esm",
        prefix: "03",
    },
    PluginSpec {
        plugin: "BenchmarkPatch.esp",
        prefix: "04",
    },
    PluginSpec {
        plugin: "BenchmarkWeapons.esp",
        prefix: "05",
    },
    PluginSpec {
        plugin: "BenchmarkArmor.esp",
        prefix: "06",
    },
];

/// Deterministic benchmark fixture generation settings.
#[derive(Clone, Copy, Debug)]
pub struct FixtureConfig {
    /// Number of records inserted into each SQLite file.
    pub records_per_db: usize,
    /// Number of SQLite files to generate.
    pub database_count: usize,
    /// Table name that stores `(formid, plugin, entry)` tuples.
    pub table_name: &'static str,
}

impl Default for FixtureConfig {
    fn default() -> Self {
        Self {
            records_per_db: 4_096,
            database_count: 2,
            table_name: DEFAULT_TABLE_NAME,
        }
    }
}

#[derive(Debug, Clone)]
struct FixtureRecord {
    suffix: String,
    plugin: String,
    entry: String,
}

/// Generated deterministic DB fixture.
pub struct DeterministicDbFixture {
    _temp_files: Vec<NamedTempFile>,
    pub db_paths: Vec<PathBuf>,
    pub table_name: String,
    records_per_db: usize,
}

impl DeterministicDbFixture {
    /// Create fixture databases with deterministic record content.
    pub async fn create(config: FixtureConfig) -> Result<Self, String> {
        if config.database_count == 0 {
            return Err("database_count must be greater than 0".to_string());
        }
        if config.records_per_db == 0 {
            return Err("records_per_db must be greater than 0".to_string());
        }

        let mut temp_files = Vec::with_capacity(config.database_count);
        let mut db_paths = Vec::with_capacity(config.database_count);

        for db_index in 0..config.database_count {
            let temp_file = NamedTempFile::with_suffix(".db")
                .map_err(|err| format!("create temp db: {err}"))?;
            let db_path = temp_file.path().to_path_buf();
            let conn_str = format!("sqlite://{}?mode=rwc", db_path.display());

            let pool = SqlitePoolOptions::new()
                .max_connections(1)
                .connect(&conn_str)
                .await
                .map_err(|err| format!("connect sqlite fixture: {err}"))?;

            let create_table_sql = format!(
                "CREATE TABLE IF NOT EXISTS {} (
                    formid TEXT NOT NULL,
                    plugin TEXT NOT NULL,
                    entry TEXT NOT NULL,
                    PRIMARY KEY (formid, plugin)
                )",
                config.table_name
            );
            sqlx::query(&create_table_sql)
                .execute(&pool)
                .await
                .map_err(|err| format!("create benchmark table: {err}"))?;

            let create_index_sql = format!(
                "CREATE INDEX IF NOT EXISTS idx_{0}_lookup ON {0} (formid, plugin)",
                config.table_name
            );
            sqlx::query(&create_index_sql)
                .execute(&pool)
                .await
                .map_err(|err| format!("create benchmark index: {err}"))?;

            let insert_sql = format!(
                "INSERT OR REPLACE INTO {} (formid, plugin, entry) VALUES (?, ?, ?)",
                config.table_name
            );
            let mut tx = pool
                .begin()
                .await
                .map_err(|err| format!("begin insert transaction: {err}"))?;

            for local_index in 0..config.records_per_db {
                let global_index = db_index * config.records_per_db + local_index;
                let record = record_for_index(global_index);

                sqlx::query(&insert_sql)
                    .bind(record.suffix)
                    .bind(record.plugin)
                    .bind(record.entry)
                    .execute(&mut *tx)
                    .await
                    .map_err(|err| format!("insert benchmark record: {err}"))?;
            }

            tx.commit()
                .await
                .map_err(|err| format!("commit insert transaction: {err}"))?;
            pool.close().await;

            db_paths.push(db_path);
            temp_files.push(temp_file);
        }

        Ok(Self {
            _temp_files: temp_files,
            db_paths,
            table_name: config.table_name.to_string(),
            records_per_db: config.records_per_db,
        })
    }

    /// Deterministic single-hit lookup pair (suffix, plugin).
    pub fn single_hit_pair(&self) -> (String, String) {
        let record = record_for_index(0);
        (record.suffix, record.plugin)
    }

    /// Pair that only exists in a secondary fixture DB.
    pub fn secondary_only_hit_pair(&self) -> (String, String) {
        let global_index = self.records_per_db + 17;
        let record = record_for_index(global_index);
        (record.suffix, record.plugin)
    }

    /// Deterministic lookup miss pair.
    pub fn miss_pair(&self) -> (String, String) {
        (
            "FFFFFF".to_string(),
            "MissingBenchmarkPlugin.esp".to_string(),
        )
    }

    /// Deterministic hit-only lookup pairs of requested size.
    pub fn hit_pairs(&self, size: usize) -> Vec<(String, String)> {
        (0..size)
            .map(|idx| {
                let record = record_for_index(idx);
                (record.suffix, record.plugin)
            })
            .collect()
    }

    /// Deterministic mixed lookup pairs where every `miss_every`-th item is a miss.
    pub fn mixed_pairs(&self, size: usize, miss_every: usize) -> Vec<(String, String)> {
        if miss_every == 0 {
            return self.hit_pairs(size);
        }

        (0..size)
            .map(|idx| {
                if idx % miss_every == 0 {
                    self.miss_pair()
                } else {
                    let record = record_for_index(idx);
                    (record.suffix, record.plugin)
                }
            })
            .collect()
    }

    /// Deterministic callstack lines that include resolvable `Form ID: 0x...` values.
    pub fn formid_callstack_lines(&self, count: usize) -> Vec<String> {
        self.hit_pairs(count)
            .into_iter()
            .enumerate()
            .map(|(idx, (suffix, plugin))| {
                let prefix = prefix_for_plugin(&plugin).unwrap_or("00");
                format!("\t[{idx:03}] BenchmarkFrame -> Form ID: 0x{prefix}{suffix} ({plugin})")
            })
            .collect()
    }

    /// Plugin/load-order map represented as `(plugin_name, prefix)` tuples.
    pub fn plugin_prefix_pairs(&self) -> Vec<(String, String)> {
        PLUGIN_SPECS
            .iter()
            .map(|spec| (spec.plugin.to_string(), spec.prefix.to_string()))
            .collect()
    }
}

/// Resolve canonical two-character load-order prefix for a plugin.
pub fn prefix_for_plugin(plugin_name: &str) -> Option<&'static str> {
    PLUGIN_SPECS
        .iter()
        .find(|spec| spec.plugin.eq_ignore_ascii_case(plugin_name))
        .map(|spec| spec.prefix)
}

fn record_for_index(index: usize) -> FixtureRecord {
    let plugin_spec = PLUGIN_SPECS[index % PLUGIN_SPECS.len()];
    let suffix_value = ((index as u64 * 97) % 0xFF_FFFF) + 1;
    let suffix = format!("{suffix_value:06X}");

    FixtureRecord {
        suffix: suffix.clone(),
        plugin: plugin_spec.plugin.to_string(),
        entry: format!(
            "BenchmarkEntry_{index:06}_{}_{}",
            plugin_spec.prefix, suffix
        ),
    }
}
