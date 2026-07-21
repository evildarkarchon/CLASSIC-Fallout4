//! Strict, owned FormID Value Lookup facade.

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use thiserror::Error;

use crate::{DEFAULT_CACHE_TTL_SECS, DatabasePool};

const DEFAULT_LOOKUP_BATCH_SIZE: usize = 128;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
struct LookupKey {
    formid: String,
    normalized_plugin: String,
}

impl LookupKey {
    fn new(formid: &str, plugin: &str) -> Self {
        Self {
            formid: formid.to_string(),
            normalized_plugin: plugin.to_lowercase(),
        }
    }
}

/// One deterministic reply supplied to the owned in-memory adapter.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FormIdValueLookupInMemoryReply {
    /// Successful adapter reply; `Some` is a hit and `None` is a miss.
    Value(Option<String>),
    /// Deterministic operational failure used without a callback boundary.
    OperationalFailure(String),
}

/// One owned FormID/plugin reply supplied to the in-memory adapter.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FormIdValueLookupEntry {
    key: LookupKey,
    reply: FormIdValueLookupInMemoryReply,
}

impl FormIdValueLookupEntry {
    /// Creates one deterministic in-memory adapter entry.
    pub fn new(
        formid: impl AsRef<str>,
        plugin: impl AsRef<str>,
        reply: FormIdValueLookupInMemoryReply,
    ) -> Self {
        Self {
            key: LookupKey::new(formid.as_ref(), plugin.as_ref()),
            reply,
        }
    }
}

/// Semantic result of one successful FormID Value Lookup operation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum FormIdValueLookupOutcome {
    /// Value Lookup was explicitly disabled for this operation.
    Disabled,
    /// The adapter completed successfully without finding a matching value.
    Missing,
    /// The adapter returned an owned human-readable FormID value.
    Found(String),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum FormIdValueLookupErrorKind {
    MalformedResult,
    OperationalFailure,
}

/// Strict failure returned by a FormID Value Lookup adapter.
#[derive(Clone, Debug, Error, PartialEq, Eq)]
#[error("{message}")]
pub struct FormIdValueLookupError {
    kind: FormIdValueLookupErrorKind,
    formid: Option<String>,
    plugin: Option<String>,
    message: String,
}

impl FormIdValueLookupError {
    fn malformed_result(formid: &str, plugin: &str) -> Self {
        Self {
            kind: FormIdValueLookupErrorKind::MalformedResult,
            formid: Some(formid.to_string()),
            plugin: Some(plugin.to_string()),
            message: format!("FormID Value Lookup returned a blank value for {formid}:{plugin}"),
        }
    }

    fn operational_failure(formid: &str, plugin: &str, detail: impl AsRef<str>) -> Self {
        Self {
            kind: FormIdValueLookupErrorKind::OperationalFailure,
            formid: Some(formid.to_string()),
            plugin: Some(plugin.to_string()),
            message: format!(
                "FormID Value Lookup failed for {formid}:{plugin}: {}",
                detail.as_ref()
            ),
        }
    }

    fn initialization_failure(detail: impl AsRef<str>) -> Self {
        Self {
            kind: FormIdValueLookupErrorKind::OperationalFailure,
            formid: None,
            plugin: None,
            message: format!(
                "FormID Value Lookup adapter initialization failed: {}",
                detail.as_ref()
            ),
        }
    }

    /// Returns the stable machine-readable failure code.
    pub const fn code(&self) -> &'static str {
        match self.kind {
            FormIdValueLookupErrorKind::MalformedResult => "malformed_result",
            FormIdValueLookupErrorKind::OperationalFailure => "operational_failure",
        }
    }

    /// Returns the FormID suffix associated with this failure, when lookup had started.
    pub fn formid(&self) -> Option<&str> {
        self.formid.as_deref()
    }

    /// Returns the plugin associated with this failure, when lookup had started.
    pub fn plugin(&self) -> Option<&str> {
        self.plugin.as_deref()
    }

    /// Returns the readable diagnostic associated with this failure.
    pub fn message(&self) -> &str {
        &self.message
    }
}

#[derive(Clone)]
enum FormIdValueLookupAdapter {
    Disabled,
    InMemory(Arc<HashMap<LookupKey, FormIdValueLookupInMemoryReply>>),
    Sqlite(Box<DatabasePool>),
    SharedPool(Arc<DatabasePool>),
}

impl FormIdValueLookupAdapter {
    /// Returns the common database seam for either owned or shared-pool adapters.
    fn database_pool(&self) -> Option<&DatabasePool> {
        match self {
            Self::Sqlite(pool) => Some(pool.as_ref()),
            Self::SharedPool(pool) => Some(pool.as_ref()),
            Self::Disabled | Self::InMemory(_) => None,
        }
    }
}

/// Opaque owned facade for FormID Value Lookup adapters.
#[derive(Clone)]
pub struct FormIdValueLookup {
    adapter: FormIdValueLookupAdapter,
}

impl std::fmt::Debug for FormIdValueLookup {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter
            .debug_struct("FormIdValueLookup")
            .finish_non_exhaustive()
    }
}

impl Default for FormIdValueLookup {
    fn default() -> Self {
        Self::disabled()
    }
}

impl FormIdValueLookup {
    /// Creates a lookup that explicitly performs no value resolution.
    pub const fn disabled() -> Self {
        Self {
            adapter: FormIdValueLookupAdapter::Disabled,
        }
    }

    /// Creates a deterministic lookup from fully owned in-memory replies.
    pub fn in_memory(entries: Vec<FormIdValueLookupEntry>) -> Self {
        let replies = entries
            .into_iter()
            .map(|entry| (entry.key, entry.reply))
            .collect();
        Self {
            adapter: FormIdValueLookupAdapter::InMemory(Arc::new(replies)),
        }
    }

    /// Creates an adapter over an existing shared database pool.
    pub fn shared_pool(pool: Arc<DatabasePool>) -> Self {
        Self {
            adapter: FormIdValueLookupAdapter::SharedPool(pool),
        }
    }

    /// Opens one owned SQLite adapter on the caller's current async runtime.
    ///
    /// No runtime is created by this constructor. The database path must exist,
    /// and initialization failures remain typed operational lookup failures.
    pub async fn sqlite(
        database_path: PathBuf,
        game_table: String,
    ) -> Result<Self, FormIdValueLookupError> {
        if !database_path.is_file() {
            return Err(FormIdValueLookupError::initialization_failure(format!(
                "database file not found: {}",
                database_path.display()
            )));
        }

        let pool = DatabasePool::new(
            Some(1),
            Duration::from_secs(DEFAULT_CACHE_TTL_SECS),
            game_table,
        );
        pool.initialize(vec![database_path])
            .await
            .map_err(|error| FormIdValueLookupError::initialization_failure(error.to_string()))?;
        Ok(Self {
            adapter: FormIdValueLookupAdapter::Sqlite(Box::new(pool)),
        })
    }

    /// Looks up one FormID/plugin pair through the configured adapter.
    pub async fn lookup(
        &self,
        formid: &str,
        plugin: &str,
    ) -> Result<FormIdValueLookupOutcome, FormIdValueLookupError> {
        if let Some(pool) = self.adapter.database_pool() {
            return lookup_database(pool, formid, plugin).await;
        }

        match &self.adapter {
            FormIdValueLookupAdapter::Disabled => Ok(FormIdValueLookupOutcome::Disabled),
            FormIdValueLookupAdapter::InMemory(replies) => {
                let reply = replies.get(&LookupKey::new(formid, plugin));
                match reply {
                    Some(FormIdValueLookupInMemoryReply::Value(Some(value)))
                        if value.trim().is_empty() =>
                    {
                        Err(FormIdValueLookupError::malformed_result(formid, plugin))
                    }
                    Some(FormIdValueLookupInMemoryReply::Value(Some(value))) => {
                        Ok(FormIdValueLookupOutcome::Found(value.clone()))
                    }
                    Some(FormIdValueLookupInMemoryReply::Value(None)) | None => {
                        Ok(FormIdValueLookupOutcome::Missing)
                    }
                    Some(FormIdValueLookupInMemoryReply::OperationalFailure(message)) => Err(
                        FormIdValueLookupError::operational_failure(formid, plugin, message),
                    ),
                }
            }
            _ => {
                unreachable!("database-backed adapters return through the common pool seam")
            }
        }
    }

    /// Looks up an owned batch and returns one positional outcome per input pair.
    ///
    /// Any malformed reply or operational failure fails the whole operation so
    /// callers cannot mistake partial results for a completed batch.
    pub async fn lookup_batch(
        &self,
        pairs: Vec<(String, String)>,
    ) -> Result<Vec<FormIdValueLookupOutcome>, FormIdValueLookupError> {
        if let Some(pool) = self.adapter.database_pool() {
            return lookup_database_batch(pool, pairs).await;
        }

        match &self.adapter {
            FormIdValueLookupAdapter::Disabled | FormIdValueLookupAdapter::InMemory(_) => {
                let mut outcomes = Vec::with_capacity(pairs.len());
                for (formid, plugin) in pairs {
                    outcomes.push(self.lookup(&formid, &plugin).await?);
                }
                Ok(outcomes)
            }
            _ => {
                unreachable!("database-backed adapters return through the common pool seam")
            }
        }
    }
}

/// Resolves one database-backed reply without collapsing failures into misses.
async fn lookup_database(
    pool: &DatabasePool,
    formid: &str,
    plugin: &str,
) -> Result<FormIdValueLookupOutcome, FormIdValueLookupError> {
    pool.get_entry_strict(formid, plugin, None)
        .await
        .map_err(|error| {
            FormIdValueLookupError::operational_failure(formid, plugin, error.to_string())
        })
        .and_then(|value| match value {
            Some(value) if value.trim().is_empty() => {
                Err(FormIdValueLookupError::malformed_result(formid, plugin))
            }
            Some(value) => Ok(FormIdValueLookupOutcome::Found(value)),
            None => Ok(FormIdValueLookupOutcome::Missing),
        })
}

/// Resolves a positional database batch with all-or-error semantics.
async fn lookup_database_batch(
    pool: &DatabasePool,
    pairs: Vec<(String, String)>,
) -> Result<Vec<FormIdValueLookupOutcome>, FormIdValueLookupError> {
    if pairs.is_empty() {
        return Ok(Vec::new());
    }
    let Some(first_pair) = pairs.first().cloned() else {
        return Ok(Vec::new());
    };
    let results = pool
        .get_entries_batch_strict(pairs.clone(), None, DEFAULT_LOOKUP_BATCH_SIZE)
        .await
        .map_err(|error| {
            FormIdValueLookupError::operational_failure(
                &first_pair.0,
                &first_pair.1,
                error.to_string(),
            )
        })?;

    pairs
        .into_iter()
        .map(|(formid, plugin)| {
            let key = format!("{formid}:{plugin}");
            match results.get(&key) {
                Some(value) if value.trim().is_empty() => {
                    Err(FormIdValueLookupError::malformed_result(&formid, &plugin))
                }
                Some(value) => Ok(FormIdValueLookupOutcome::Found(value.clone())),
                None => Ok(FormIdValueLookupOutcome::Missing),
            }
        })
        .collect()
}

// Keep the repository's required sibling-test declaration intact under rustfmt.
#[rustfmt::skip]
#[cfg(test)] #[path = "formid_value_lookup_tests.rs"] mod tests;
